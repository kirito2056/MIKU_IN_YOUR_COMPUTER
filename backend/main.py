from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import sys

app = FastAPI(title="MIKU IN YOUR COMPUTER (Backend)")

# CORS 설정 (Frontend 접속 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포 시에는 구체적인 출처로 제한 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Miku Backend is running!", "platform": sys.platform}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # Echo for now
            await websocket.send_text(f"Miku received: {data}")
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
