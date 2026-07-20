"""Eye1 (Webcam) 행동 분석 서비스 — MediaPipe Tasks 기반.

백엔드가 로컬에서 돌기 때문에 프레임을 HTTP로 받지 않고 OpenCV로 웹캠을 직접
캡처한다. FaceLandmarker(표정·머리 각도) + GestureRecognizer(손 제스처) +
PoseLandmarker(자세)를 CPU에서 저fps로 돌리고, 최신 Eye1Schema 상태를
메모리에 유지한다. LLM에는 get_context_text()가 만든 한 줄만 들어간다.

모델 파일: backend/models/mediapipe/*.task
    (scripts/download_vision_models.py 로 다운로드)
"""

import math
import os
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Optional

import numpy as np

from schemas.vision import (
    EnvironmentInfo,
    EventsInfo,
    Eye1Schema,
    FaceExpression,
    FacesInfo,
    GestureInfo,
    PostureInfo,
    generate_eye1_summary,
)

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_DIR = BACKEND_DIR / "models" / "mediapipe"

MODEL_FILES = {
    "face": "face_landmarker.task",
    "gesture": "gesture_recognizer.task",
    "pose": "pose_landmarker_lite.task",
}

# 제스처 판정 파라미터 (웹캠·거리에 따라 튜닝 여지 있음)
OSC_WINDOW_SEC = 1.5        # 끄덕임/도리도리/손 흔들기 관측 창
NOD_MIN_AMPLITUDE = 0.015   # 코 y 진폭 (정규화 좌표)
WAVE_MIN_AMPLITUDE = 0.04   # 손 x 진폭
MIN_REVERSALS = 2           # 방향 전환 최소 횟수
GESTURE_COOLDOWN_SEC = 2.0  # 같은 제스처 재발화 쿨다운
SCREEN_COVER_AREA = 0.45    # 손 bbox가 화면에서 차지하는 비율
POSTURE_HOLD_SEC = 3.0      # 자세 이슈 지속 시간 (순간 오탐 방지)
FACE_DEBOUNCE_SEC = 1.0     # 얼굴 등장/이탈 디바운스

# MediaPipe 손 랜드마크(21점) 연결 정의 — 미리보기 스켈레톤용
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # 엄지
    (0, 5), (5, 6), (6, 7), (7, 8),          # 검지
    (5, 9), (9, 10), (10, 11), (11, 12),     # 중지
    (9, 13), (13, 14), (14, 15), (15, 16),   # 약지
    (13, 17), (17, 18), (18, 19), (19, 20),  # 새끼
    (0, 17),                                  # 손바닥
]
MIKU_TEAL_BGR = (187, 197, 57)  # #39C5BB


def _count_reversals(series: list, min_amplitude: float) -> int:
    """시계열에서 min_amplitude 이상 움직인 방향 전환 횟수."""
    reversals = 0
    direction = 0
    anchor = series[0] if series else 0.0
    for v in series[1:]:
        delta = v - anchor
        if abs(delta) < min_amplitude:
            continue
        d = 1 if delta > 0 else -1
        if direction != 0 and d != direction:
            reversals += 1
        direction = d
        anchor = v
    return reversals


def _rotation_to_pitch_deg(matrix: np.ndarray) -> float:
    """얼굴 변환 행렬(4x4) → pitch(도). 정면=0, 아래를 보면 음수."""
    r = matrix[:3, :3]
    pitch = math.degrees(math.atan2(r[2][1], r[2][2]))
    return pitch


class VisionServiceError(Exception):
    pass


def _open_capture(index: int):
    """카메라 열기 — Windows에서 MSMF 우선, 실패 시 DSHOW 폴백.

    같은 장치라도 백엔드에 따라 인덱스 매핑이 다르고, 열려도 프레임이 안 오는
    경우가 있어서 '실제로 읽히는지'까지 확인하고 반환한다.
    """
    import cv2

    if sys.platform == "win32":
        backends = [cv2.CAP_MSMF, cv2.CAP_DSHOW]
    else:
        backends = [cv2.CAP_ANY]

    for be in backends:
        cap = cv2.VideoCapture(index, be)
        if not cap.isOpened():
            cap.release()
            continue
        # 워밍업: 2초 안에 실제 프레임이 오는지 확인
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            ok, frame = cap.read()
            if ok and frame is not None:
                return cap
            time.sleep(0.1)
        cap.release()
    return None


def probe_cameras(max_index: int = 5) -> list:
    """사용 가능한 카메라를 훑어서 [{index, width, height, brightness, thumbnail_b64}] 반환.

    캡처가 실행 중이면 장치가 점유돼 있어 결과가 부정확하다 — 호출 전에 stop() 할 것.
    """
    import base64
    import cv2

    results = []
    for i in range(max_index):
        cap = _open_capture(i)
        if cap is None:
            continue
        frame = None
        for _ in range(10):  # 자동 노출 적응 대기
            ok, f = cap.read()
            if ok and f is not None:
                frame = f
            time.sleep(0.05)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        if frame is None:
            continue
        thumb = cv2.resize(frame, (240, max(1, int(240 * h / max(w, 1)))))
        ok, buf = cv2.imencode(".jpg", thumb, [cv2.IMWRITE_JPEG_QUALITY, 70])
        results.append({
            "index": i,
            "width": w,
            "height": h,
            "brightness": round(float(frame.mean()) / 255.0, 2),
            "thumbnail_b64": base64.b64encode(buf).decode("ascii") if ok else None,
        })
    return results


class VisionService:
    def __init__(
        self,
        camera_index: Optional[int] = None,
        fps: Optional[float] = None,
        model_dir: Optional[Path] = None,
    ):
        self.camera_index = camera_index if camera_index is not None else int(
            os.getenv("VISION_CAMERA_INDEX", "0")
        )
        # 720p 기준 추론 ~30ms/frame이라 30fps까지 가능하지만, CPU 여유를 위해 15 기본
        self.fps = fps if fps is not None else float(os.getenv("VISION_FPS", "15"))
        self.model_dir = Path(model_dir or os.getenv("VISION_MODEL_DIR", DEFAULT_MODEL_DIR))

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._state: Optional[Eye1Schema] = None
        self._state_at: float = 0.0
        self._error: Optional[str] = None

        # 시계열 버퍼 (제스처/모션 판정용)
        self._nose_hist: deque = deque()      # (t, x, y)
        self._hand_x_hist: deque = deque()    # (t, x) — open palm일 때만
        self._last_gesture: tuple = ("none", 0.0)  # (type, fired_at)
        self._posture_issue_since: dict = {}  # posture type -> first seen t
        self._face_present: bool = False
        self._face_changed_at: float = 0.0
        self._prev_gray_small: Optional[np.ndarray] = None
        self._frame_id: int = 0
        self._preview_jpeg: Optional[bytes] = None

    # ---------------------------------------------------------------- public

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def last_error(self) -> Optional[str]:
        return self._error

    def start(self, camera_index: Optional[int] = None) -> None:
        if self.is_running:
            if camera_index is None or camera_index == self.camera_index:
                return
            self.stop()  # 다른 카메라로 전환
        if camera_index is not None:
            self.camera_index = camera_index
        missing = [
            name for name, fname in MODEL_FILES.items()
            if not (self.model_dir / fname).exists()
        ]
        if missing:
            raise VisionServiceError(
                f"MediaPipe 모델 없음: {missing}. "
                f"`python scripts/download_vision_models.py` 먼저 실행 ({self.model_dir})"
            )
        self._error = None
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="vision-eye1")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def get_state(self) -> Optional[Eye1Schema]:
        with self._lock:
            return self._state

    def get_context_text(self, max_age_sec: float = 5.0) -> Optional[str]:
        """채팅 프롬프트에 넣을 '[시각] ...' 한 줄. 상태가 오래됐으면 None."""
        with self._lock:
            if self._state is None or time.time() - self._state_at > max_age_sec:
                return None
            return f"[시각] 웹캠: {self._state.summary}."

    def get_preview_jpeg(self) -> Optional[bytes]:
        """랜드마크 오버레이가 그려진 최신 프레임 (JPEG). MJPEG 스트림용."""
        with self._lock:
            return self._preview_jpeg

    # --------------------------------------------------------------- capture

    def _run(self) -> None:
        import cv2  # 서비스 미사용 시 import 비용 회피
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision

        try:
            face_lm = mp_vision.FaceLandmarker.create_from_options(
                mp_vision.FaceLandmarkerOptions(
                    base_options=mp_python.BaseOptions(
                        model_asset_path=str(self.model_dir / MODEL_FILES["face"])
                    ),
                    running_mode=mp_vision.RunningMode.VIDEO,
                    num_faces=3,
                    output_face_blendshapes=True,
                    output_facial_transformation_matrixes=True,
                )
            )
            gesture_rec = mp_vision.GestureRecognizer.create_from_options(
                mp_vision.GestureRecognizerOptions(
                    base_options=mp_python.BaseOptions(
                        model_asset_path=str(self.model_dir / MODEL_FILES["gesture"])
                    ),
                    running_mode=mp_vision.RunningMode.VIDEO,
                    num_hands=2,
                )
            )
            pose_lm = mp_vision.PoseLandmarker.create_from_options(
                mp_vision.PoseLandmarkerOptions(
                    base_options=mp_python.BaseOptions(
                        model_asset_path=str(self.model_dir / MODEL_FILES["pose"])
                    ),
                    running_mode=mp_vision.RunningMode.VIDEO,
                )
            )
        except Exception as e:
            self._error = f"MediaPipe 초기화 실패: {e}"
            return

        cap = _open_capture(self.camera_index)
        if cap is None:
            self._error = (
                f"웹캠 열기 실패 (index={self.camera_index}). "
                "다른 앱이 카메라를 쓰고 있거나 인덱스가 바뀌었을 수 있음 — "
                "모니터 페이지에서 카메라를 다시 선택해봐."
            )
            face_lm.close(); gesture_rec.close(); pose_lm.close()
            return

        interval = 1.0 / max(self.fps, 0.5)
        t0 = time.monotonic()
        try:
            while not self._stop_event.is_set():
                tick = time.monotonic()
                ok, frame_bgr = cap.read()
                if not ok:
                    self._error = "프레임 읽기 실패"
                    time.sleep(1.0)
                    continue

                ts_ms = int((time.monotonic() - t0) * 1000)
                rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

                face_res = face_lm.detect_for_video(mp_image, ts_ms)
                gesture_res = gesture_rec.recognize_for_video(mp_image, ts_ms)
                pose_res = pose_lm.detect_for_video(mp_image, ts_ms)

                state = self._build_state(frame_bgr, face_res, gesture_res, pose_res)
                preview = self._render_preview(
                    cv2, frame_bgr, face_res, gesture_res, pose_res, state
                )
                with self._lock:
                    self._state = state
                    self._state_at = time.time()
                    self._preview_jpeg = preview

                elapsed = time.monotonic() - tick
                if elapsed < interval:
                    self._stop_event.wait(interval - elapsed)
        finally:
            cap.release()
            face_lm.close()
            gesture_rec.close()
            pose_lm.close()

    # --------------------------------------------------------------- preview

    def _render_preview(
        self, cv2, frame_bgr, face_res, gesture_res, pose_res, state
    ) -> Optional[bytes]:
        """손 스켈레톤·얼굴 박스·어깨선 오버레이 → 미러 뷰 JPEG."""
        frame = cv2.flip(frame_bgr, 1)  # 셀피 미러. 이후 좌표는 x를 반전해서 사용
        h, w = frame.shape[:2]

        def pt(p):
            return int((1.0 - p.x) * w), int(p.y * h)

        # 손: 마디 연결선(흰색) + 관절 점(틸)
        for hand in gesture_res.hand_landmarks or []:
            pts = [pt(p) for p in hand]
            for a, b in HAND_CONNECTIONS:
                cv2.line(frame, pts[a], pts[b], (255, 255, 255), 2, cv2.LINE_AA)
            for x, y in pts:
                cv2.circle(frame, (x, y), 4, MIKU_TEAL_BGR, -1, cv2.LINE_AA)
                cv2.circle(frame, (x, y), 4, (40, 40, 40), 1, cv2.LINE_AA)

        # 얼굴: bbox + 표정 라벨 (bbox는 원본 좌표계라 x 반전)
        for expr in state.faces.expressions:
            bx, by, bw, bh = expr.bbox
            p1 = (int((1.0 - bx - bw) * w), int(by * h))
            p2 = (int((1.0 - bx) * w), int((by + bh) * h))
            cv2.rectangle(frame, p1, p2, MIKU_TEAL_BGR, 1, cv2.LINE_AA)
            cv2.putText(
                frame, expr.type, (p1[0], max(14, p1[1] - 6)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, MIKU_TEAL_BGR, 1, cv2.LINE_AA,
            )

        # 어깨선 (자세 판정 참고용)
        if pose_res.pose_landmarks:
            lm = pose_res.pose_landmarks[0]
            cv2.line(frame, pt(lm[11]), pt(lm[12]), (160, 160, 160), 2, cv2.LINE_AA)

        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        return bytes(buf) if ok else None

    # -------------------------------------------------------------- analysis

    def _build_state(self, frame_bgr, face_res, gesture_res, pose_res) -> Eye1Schema:
        import cv2

        now = time.monotonic()
        self._frame_id += 1

        faces = self._analyze_faces(face_res)
        environment = self._analyze_environment(frame_bgr, cv2)
        gesture = self._analyze_gesture(face_res, gesture_res, now)
        posture = self._analyze_posture(face_res, pose_res, now)
        events = self._analyze_events(faces, environment, now)

        eye1 = Eye1Schema(
            timestamp=time.time(),
            frame_id=self._frame_id,
            faces=faces,
            gesture=gesture,
            posture=posture,
            environment=environment,
            events=events,
            summary="",
        )
        eye1.summary = generate_eye1_summary(eye1)
        return eye1

    def _analyze_faces(self, face_res) -> FacesInfo:
        landmarks_list = face_res.face_landmarks or []
        count = len(landmarks_list)
        expressions = []

        for i, landmarks in enumerate(landmarks_list):
            xs = [p.x for p in landmarks]
            ys = [p.y for p in landmarks]
            bbox = [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]

            expr_type, expr_conf = "neutral", 0.5
            if face_res.face_blendshapes and i < len(face_res.face_blendshapes):
                scores = {
                    c.category_name: c.score for c in face_res.face_blendshapes[i]
                }
                expr_type, expr_conf = self._classify_expression(scores)
            expressions.append(
                FaceExpression(type=expr_type, confidence=round(expr_conf, 2), bbox=bbox)
            )

        return FacesInfo(
            count=min(count, 10),
            detected=count > 0,
            recognized_user=None,  # 얼굴 등록·인식(주인 판별)은 추후 단계
            confidence=None,
            expressions=expressions,
        )

    @staticmethod
    def _classify_expression(s: dict) -> tuple:
        smile = (s.get("mouthSmileLeft", 0) + s.get("mouthSmileRight", 0)) / 2
        frown = (s.get("mouthFrownLeft", 0) + s.get("mouthFrownRight", 0)) / 2
        brow_down = (s.get("browDownLeft", 0) + s.get("browDownRight", 0)) / 2
        brow_up = (
            s.get("browInnerUp", 0)
            + s.get("browOuterUpLeft", 0)
            + s.get("browOuterUpRight", 0)
        ) / 3
        jaw_open = s.get("jawOpen", 0)
        eyes_closed = (s.get("eyeBlinkLeft", 0) + s.get("eyeBlinkRight", 0)) / 2

        if jaw_open > 0.4 and brow_up > 0.25:
            return "surprised", min(1.0, (jaw_open + brow_up) / 2 + 0.3)
        if smile > 0.4:
            return "happy", min(1.0, smile + 0.3)
        if brow_down > 0.4:
            return "angry", min(1.0, brow_down + 0.3)
        if frown > 0.3:
            return "sad", min(1.0, frown + 0.4)
        if eyes_closed > 0.7:
            return "tired", min(1.0, eyes_closed)
        return "neutral", 0.6

    def _analyze_gesture(self, face_res, gesture_res, now: float) -> GestureInfo:
        hand_landmarks = gesture_res.hand_landmarks or []
        hand_count = min(len(hand_landmarks), 2)
        top_gestures = [g[0] for g in (gesture_res.gestures or []) if g]

        # 시계열 갱신: 코(끄덕임/도리도리), 손바닥 x(흔들기)
        cutoff = now - OSC_WINDOW_SEC
        if face_res.face_landmarks:
            nose = face_res.face_landmarks[0][1]  # landmark 1 = 코끝
            self._nose_hist.append((now, nose.x, nose.y))
        while self._nose_hist and self._nose_hist[0][0] < cutoff:
            self._nose_hist.popleft()

        open_palm = any(g.category_name == "Open_Palm" for g in top_gestures)
        if open_palm and hand_landmarks:
            cx = float(np.mean([p.x for p in hand_landmarks[0]]))
            self._hand_x_hist.append((now, cx))
        while self._hand_x_hist and self._hand_x_hist[0][0] < cutoff:
            self._hand_x_hist.popleft()

        detected, conf = "none", 0.0

        # 1) 화면 가리기: 손 bbox가 프레임 대부분을 덮음
        for lm in hand_landmarks:
            xs = [p.x for p in lm]
            ys = [p.y for p in lm]
            if (max(xs) - min(xs)) * (max(ys) - min(ys)) > SCREEN_COVER_AREA:
                detected, conf = "screen_cover", 0.8
                break

        # 2) 손 흔들기: open palm 상태에서 x 좌우 왕복
        if detected == "none" and len(self._hand_x_hist) >= 4:
            xs = [x for _, x in self._hand_x_hist]
            if _count_reversals(xs, WAVE_MIN_AMPLITUDE) >= MIN_REVERSALS:
                detected, conf = "wave", 0.85

        # 3) 정적 손 제스처
        if detected == "none":
            for g in top_gestures:
                if g.category_name == "Thumb_Up" and g.score > 0.5:
                    detected, conf = "thumbs_up", g.score
                    break
                if g.category_name == "Pointing_Up" and g.score > 0.5:
                    detected, conf = "point", g.score
                    break

        # 4) 고개 끄덕임/도리도리: 코 좌표 왕복
        if detected == "none" and len(self._nose_hist) >= 4:
            xs = [x for _, x, _ in self._nose_hist]
            ys = [y for _, _, y in self._nose_hist]
            nod_rev = _count_reversals(ys, NOD_MIN_AMPLITUDE)
            shake_rev = _count_reversals(xs, NOD_MIN_AMPLITUDE)
            if nod_rev >= MIN_REVERSALS and nod_rev >= shake_rev:
                detected, conf = "nod", 0.75
            elif shake_rev >= MIN_REVERSALS:
                detected, conf = "shake_head", 0.75

        # 같은 제스처 연속 발화 쿨다운 (wave 한 번에 스팸 방지)
        last_type, last_at = self._last_gesture
        if detected != "none":
            if detected == last_type and now - last_at < GESTURE_COOLDOWN_SEC:
                detected, conf = "none", 0.0
            else:
                self._last_gesture = (detected, now)
                if detected in ("nod", "shake_head"):
                    self._nose_hist.clear()
                if detected == "wave":
                    self._hand_x_hist.clear()

        return GestureInfo(type=detected, confidence=round(conf, 2), hand_count=hand_count)

    def _analyze_posture(self, face_res, pose_res, now: float) -> PostureInfo:
        head_angle = None
        if face_res.facial_transformation_matrixes:
            head_angle = round(
                _rotation_to_pitch_deg(
                    np.array(face_res.facial_transformation_matrixes[0])
                ),
                1,
            )

        shoulder_alignment = None
        candidate = "normal"
        pose_landmarks = pose_res.pose_landmarks or []
        if pose_landmarks:
            lm = pose_landmarks[0]
            l_sh, r_sh = lm[11], lm[12]
            l_ear, r_ear = lm[7], lm[8]
            nose = lm[0]

            # 어깨선 기울기 (사용자 기준 좌/우 — 웹캠은 미러가 아니므로 x 반전 주의)
            dx, dy = r_sh.x - l_sh.x, r_sh.y - l_sh.y
            if abs(dx) > 1e-6:
                shoulder_alignment = round(math.degrees(math.atan2(dy, dx)) - 180.0, 1)
                if shoulder_alignment < -180:
                    shoulder_alignment += 360

            shoulder_w = abs(dx)
            shoulder_mid_y = (l_sh.y + r_sh.y) / 2
            ear_z = (l_ear.z + r_ear.z) / 2
            shoulder_z = (l_sh.z + r_sh.z) / 2

            if shoulder_alignment is not None and abs(shoulder_alignment) > 10:
                candidate = "leaning_left" if shoulder_alignment > 0 else "leaning_right"
            # 거북목: 귀가 어깨보다 카메라 쪽으로 쏠림 + 고개가 아래로
            elif ear_z - shoulder_z < -0.25 and (head_angle is None or head_angle < -8):
                candidate = "forward_head"
            # 구부정: 머리가 어깨선에 파묻힘 (코-어깨 세로거리가 어깨너비 대비 짧음)
            elif shoulder_w > 1e-6 and (shoulder_mid_y - nose.y) / shoulder_w < 0.45:
                candidate = "slouching"

        # 순간 오탐 방지: 같은 이슈가 POSTURE_HOLD_SEC 이상 지속돼야 보고
        if candidate == "normal":
            self._posture_issue_since.clear()
            return PostureInfo(
                type="normal",
                head_angle=head_angle,
                shoulder_alignment=shoulder_alignment,
                confidence=0.8 if pose_landmarks else 0.3,
            )

        first_seen = self._posture_issue_since.setdefault(candidate, now)
        self._posture_issue_since = {candidate: first_seen}
        confirmed = now - first_seen >= POSTURE_HOLD_SEC
        return PostureInfo(
            type=candidate if confirmed else "normal",
            head_angle=head_angle,
            shoulder_alignment=shoulder_alignment,
            confidence=0.6 if confirmed else 0.4,
        )

    def _analyze_environment(self, frame_bgr, cv2) -> EnvironmentInfo:
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (64, 36))
        mean = float(np.mean(small))
        level = round(mean / 255.0, 2)
        if mean > 170:
            light = "bright"
        elif mean > 90:
            light = "normal"
        elif mean > 40:
            light = "dark"
        else:
            light = "very_dark"

        motion = False
        if self._prev_gray_small is not None:
            diff = float(np.mean(np.abs(small.astype(np.int16) - self._prev_gray_small)))
            motion = diff > 8.0
        self._prev_gray_small = small.astype(np.int16)

        return EnvironmentInfo(light=light, light_level=level, motion=motion)

    def _analyze_events(self, faces: FacesInfo, env: EnvironmentInfo, now: float) -> EventsInfo:
        appeared = disappeared = False
        if faces.detected != self._face_present:
            # 디바운스: 상태가 바뀐 지 FACE_DEBOUNCE_SEC 지나야 이벤트 발화
            if now - self._face_changed_at > FACE_DEBOUNCE_SEC:
                if faces.detected:
                    appeared = True
                else:
                    disappeared = True
                self._face_present = faces.detected
                self._face_changed_at = now
        else:
            self._face_changed_at = now

        return EventsInfo(
            # 유령: 캄캄한데 얼굴이 잡히면 미쿠가 놀라는 연출용
            ghost=faces.detected and env.light == "very_dark",
            multiple_faces=faces.count >= 2,
            face_appeared=appeared,
            face_disappeared=disappeared,
        )


_vision_service: Optional[VisionService] = None


def get_vision_service() -> VisionService:
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionService()
    return _vision_service
