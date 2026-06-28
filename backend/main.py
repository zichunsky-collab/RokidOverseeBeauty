"""镜览山河 - AI眼镜智能景区讲解系统 后端入口"""
import sys
import os

# 添加 backend 目录到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.config import settings
from app.services.knowledge_base import knowledge_base

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于AI大模型的智能景区讲解系统 - 乐奇AI眼镜大赛参赛作品"
)

# CORS 允许跨域（眼镜端/手机端调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router)


@app.on_event("startup")
async def startup():
    print("=" * 50)
    print(f"🏔️  {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"📍 已加载 {len(knowledge_base.get_all_spots())} 个景区")
    print("=" * 50)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api": {
            "health": "/api/health",
            "scenic_spots": "/api/scenic_spots",
            "nearby": "/api/nearby?lat=32.0456&lng=118.7942",
            "narration": "/api/narration?spot_id=zongtongfu&sub_spot_id=datang&level=standard",
            "qa": "POST /api/qa",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
