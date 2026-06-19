"""
LLM 서비스 모듈
모델 로딩 및 추론을 담당합니다.
"""
import os
import torch
from pathlib import Path
from typing import Optional, List, Dict
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TextIteratorStreamer
from peft import PeftModel
from threading import Thread


class LLMService:
    """LLM 모델 서비스 클래스"""
    
    def __init__(
        self,
        model_path: str = "models/miku_Gemma4_12B_merged",
        lora_path: Optional[str] = None,
        use_4bit: bool = True,
        device: str = "auto"
    ):
        """
        LLM 서비스 초기화
        
        Args:
            model_path: 모델 경로 (기본값: "models/miku_Gemma4_12B_merged", backend/models/miku_Gemma4_12B_merged 폴더)
            lora_path: LoRA 어댑터 경로 (선택사항)
            use_4bit: 4-bit 양자화 사용 여부
            device: 디바이스 ("auto", "cuda", "cpu")
        """
        self.model_path = self._resolve_model_path(model_path)
        self.lora_path = lora_path
        self.use_4bit = use_4bit
        self.device = device
        
        self.model = None
        self.tokenizer = None
        self._is_loaded = False
    
    def _resolve_model_path(self, model_path: str) -> str:
        """모델 경로를 절대 경로로 변환"""
        if os.path.isabs(model_path) or model_path.startswith("google/") or model_path.startswith("microsoft/"):
            return model_path
        
        # 상대 경로인 경우 backend 디렉토리 기준으로 변환
        backend_dir = Path(__file__).parent.parent
        return str(backend_dir / model_path)
    
    def load_model(self):
        """모델과 토크나이저 로드"""
        if self._is_loaded:
            return
        
        print(f"📥 모델 로딩 중: {self.model_path}")
        
        # GPU 사용 가능 여부 확인
        has_gpu = torch.cuda.is_available()
        if not has_gpu:
            print("⚠️  GPU를 찾을 수 없습니다. CPU 모드로 실행됩니다.")
            self.use_4bit = False  # CPU에서는 4-bit 양자화 사용 불가
        
        # 양자화 설정
        bnb_config = None
        device_map = self.device if self.device != "auto" else ("auto" if has_gpu else "cpu")
        
        if self.use_4bit and has_gpu:
            print("   ✅ 4-bit 양자화 활성화 (GPU 전용)")
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
                llm_int8_enable_fp32_cpu_offload=False,
            )
            
        torch_dtype = torch.bfloat16 if has_gpu else torch.float32
        
        # 베이스 모델 로드
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                quantization_config=bnb_config,
                device_map=device_map,
                trust_remote_code=True,
                torch_dtype=torch_dtype,
            )
        except Exception as e:
            print(f"⚠️  모델 로드 중 오류 발생: {e}")
            raise
        
        # 토크나이저 로드
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # LoRA 어댑터 로드 (있는 경우)
        if self.lora_path:
            lora_full_path = self.lora_path
            if not os.path.isabs(lora_full_path):
                backend_dir = Path(__file__).parent.parent
                lora_full_path = str(backend_dir / lora_full_path)
            
            if os.path.exists(lora_full_path):
                print(f"📥 LoRA 어댑터 로딩: {lora_full_path}")
                self.model = PeftModel.from_pretrained(self.model, lora_full_path)
            else:
                print(f"⚠️  LoRA 경로를 찾을 수 없습니다: {lora_full_path}")
        
        self._is_loaded = True
        print("✅ 모델 로딩 완료!")
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: int = 512,  # RTX 5080 16GB에 맞게 기본값 증가 (안전한 범위)
        temperature: float = 0.7,
        top_p: float = 0.9,
        do_sample: bool = True
    ) -> str:
        """
        메시지 리스트를 받아 응답 생성
        
        Args:
            messages: [{"role": "user", "content": "..."}, ...] 형식의 메시지 리스트
            max_new_tokens: 최대 생성 토큰 수
            temperature: 샘플링 온도
            top_p: nucleus sampling 파라미터
            do_sample: 샘플링 사용 여부
        
        Returns:
            생성된 응답 텍스트
        """
        if not self._is_loaded:
            self.load_model()
        
        # Chat 템플릿 적용
        input_text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # 토크나이징
        inputs = self.tokenizer(input_text, return_tensors="pt")
        if torch.cuda.is_available() and self.device != "cpu":
            inputs = inputs.to("cuda")
        
        # 생성
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=do_sample,
                pad_token_id=self.tokenizer.eos_token_id,
                repetition_penalty=1.1,
                no_repeat_ngram_size=3
            )
        
        # 디코딩
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # 응답 부분만 추출 (assistant 응답 부분)
        if "assistant" in response.lower():
            # 마지막 assistant 응답 부분만 추출
            parts = response.split("assistant")
            if len(parts) > 1:
                response = parts[-1].strip()
        
        return response
    
    def chat(self, user_message: str, **kwargs) -> str:
        """
        간단한 채팅 인터페이스
        
        Args:
            user_message: 사용자 메시지
            **kwargs: generate 메서드에 전달할 추가 파라미터
        
        Returns:
            생성된 응답 텍스트
        """
        messages = [{"role": "user", "content": user_message}]
        return self.generate(messages, **kwargs)
    
    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        do_sample: bool = True
    ):
        """
        메시지 리스트를 받아 응답을 스트리밍으로 생성
        """
        if not self._is_loaded:
            self.load_model()
            
        # Chat 템플릿 적용
        input_text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # 토크나이징
        inputs = self.tokenizer(input_text, return_tensors="pt")
        if torch.cuda.is_available() and self.device != "cpu":
            inputs = inputs.to("cuda")
            
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
        
        generation_kwargs = dict(
            **inputs,
            streamer=streamer,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=do_sample,
            pad_token_id=self.tokenizer.eos_token_id,
            repetition_penalty=1.1,
            no_repeat_ngram_size=3
        )
        
        thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()
        
        for new_text in streamer:
            yield new_text

    def chat_stream(self, user_message: str, **kwargs):
        """
        간단한 스트리밍 채팅 인터페이스
        """
        # Chat 템플릿에 맞게 시스템 프롬프트를 제거하거나 user 메시지에 포함시킴
        # (Gemma 모델은 공식적으로 system role을 지원하지 않음)
        messages = [
            {"role": "user", "content": f"너의 이름은 미쿠야. 너는 나를 '마스터'라고 부르며, 때로는 츤데레 같지만 사실은 나를 아주 많이 좋아해. 대답은 한국어로 짧고 귀엽게 해줘.\n\n나: {user_message}"}
        ]
        
        for text in self.generate_stream(messages, **kwargs):
            yield text
    
    def unload_model(self):
        """모델 언로드 및 메모리 해제"""
        if self.model is not None:
            del self.model
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        self._is_loaded = False
        print("✅ 모델 언로드 완료")


# 전역 모델 인스턴스 (선택사항)
_llm_service: Optional[LLMService] = None


def get_llm_service(
    model_path: str = "models/miku_Gemma4_12B_merged",
    lora_path: Optional[str] = None,
    use_4bit: bool = True
) -> LLMService:
    """
    전역 LLM 서비스 인스턴스 가져오기 (싱글톤 패턴)
    
    Args:
        model_path: 모델 경로
        lora_path: LoRA 어댑터 경로
        use_4bit: 4-bit 양자화 사용 여부
    
    Returns:
        LLMService 인스턴스
    """
    global _llm_service
    
    if _llm_service is None:
        _llm_service = LLMService(
            model_path=model_path,
            lora_path=lora_path,
            use_4bit=use_4bit
        )
        _llm_service.load_model()
    
    return _llm_service
