from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sys
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# LLM 서비스 임포트
from services.llm_service import get_llm_service, LLMService

app = FastAPI(title="MIKU IN YOUR COMPUTER (Backend)")

# CORS 설정 (Frontend 접속 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포 시에는 구체적인 출처로 제한 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 LLM 서비스 인스턴스
llm_service: Optional[LLMService] = None


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 모델 로드"""
    global llm_service
    try:
        model_path = os.getenv("LLM_MODEL_PATH", "models/Gemma_12B")
        lora_path = os.getenv("LORA_PATH", None)
        use_4bit = os.getenv("USE_4BIT", "true").lower() == "true"
        
        print(f"🚀 LLM 서비스 초기화 중...")
        print(f"   모델 경로: {model_path}")
        if lora_path:
            print(f"   LoRA 경로: {lora_path}")
        
        llm_service = get_llm_service(
            model_path=model_path,
            lora_path=lora_path,
            use_4bit=use_4bit
        )
        print("✅ LLM 서비스 준비 완료!")
    except Exception as e:
        print(f"⚠️  모델 로딩 실패: {e}")
        print("   API는 모델 없이 실행됩니다. /chat 엔드포인트는 사용할 수 없습니다.")


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 모델 언로드"""
    global llm_service
    if llm_service is not None:
        llm_service.unload_model()
        llm_service = None


@app.get("/")
async def root():
    return {
        "message": "Miku Backend is running!",
        "platform": sys.platform,
        "model_loaded": llm_service is not None and llm_service._is_loaded
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model_loaded": llm_service is not None and llm_service._is_loaded
    }


class ChatRequest(BaseModel):
    """채팅 요청 모델"""
    message: str
    max_new_tokens: Optional[int] = 200
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9


class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    response: str
    model_loaded: bool


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """REST API 채팅 엔드포인트"""
    if llm_service is None or not llm_service._is_loaded:
        raise HTTPException(
            status_code=503,
            detail="모델이 로드되지 않았습니다. 서버 로그를 확인하세요."
        )
    
    try:
        response = llm_service.chat(
            request.message,
            max_new_tokens=request.max_new_tokens,
            temperature=request.temperature,
            top_p=request.top_p
        )
        return ChatResponse(
            response=response,
            model_loaded=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"응답 생성 실패: {str(e)}")


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 채팅 엔드포인트"""
    await websocket.accept()
    
    if llm_service is None or not llm_service._is_loaded:
        await websocket.send_json({
            "type": "error",
            "message": "모델이 로드되지 않았습니다."
        })
        await websocket.close()
        return
    
    try:
        while True:
            # 메시지 수신
            data = await websocket.receive_json()
            
            if data.get("type") == "chat":
                user_message = data.get("message", "")
                
                if not user_message:
                    await websocket.send_json({
                        "type": "error",
                        "message": "메시지가 비어있습니다."
                    })
                    continue
                
                # 응답 생성
                try:
                    response = llm_service.chat(
                        user_message,
                        max_new_tokens=data.get("max_new_tokens", 200),
                        temperature=data.get("temperature", 0.7),
                        top_p=data.get("top_p", 0.9)
                    )
                    
                    await websocket.send_json({
                        "type": "response",
                        "message": response
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"응답 생성 실패: {str(e)}"
                    })
            
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        print("WebSocket 연결 종료")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
