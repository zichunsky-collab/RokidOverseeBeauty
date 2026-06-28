"""API路由 - 镜览山河"""
from fastapi import APIRouter, HTTPException
from ..models.schemas import (
    LocationRequest, NearbyResponse,
    NarrationRequest, NarrationResponse,
    QARequest, QAResponse,
    HealthResponse, NarrationLevel, UserPreference
)
from ..services.knowledge_base import knowledge_base
from ..services.location import location_service
from ..services.narration import generate_narration, answer_question
from ..core.config import settings

router = APIRouter(prefix="/api")


# ═══════════════════════════════════════════════════════════════
# 健康检查
# ═══════════════════════════════════════════════════════════════

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        scenic_spots_count=len(knowledge_base.get_all_spots())
    )


# ═══════════════════════════════════════════════════════════════
# 景区列表
# ═══════════════════════════════════════════════════════════════

@router.get("/scenic_spots")
async def list_scenic_spots():
    """列出所有景区"""
    spots = knowledge_base.get_all_spots()
    return {
        "count": len(spots),
        "spots": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "sub_spots_count": len(s.sub_spots),
                "location": {"lat": s.location.lat, "lng": s.location.lng}
            }
            for s in spots
        ]
    }


# ═══════════════════════════════════════════════════════════════
# GPS定位 → 附近景点
# ═══════════════════════════════════════════════════════════════

@router.get("/nearby")
async def find_nearby(lat: float, lng: float):
    """GPS查询附近景点"""
    result = location_service.find_nearby(lat, lng)
    return result


# ═══════════════════════════════════════════════════════════════
# 获取讲解词
# ═══════════════════════════════════════════════════════════════

@router.get("/narration")
async def get_narration(
    spot_id: str,
    sub_spot_id: str,
    level: str = "standard",
    style: str = "story",
    interest: str = "history",
    language: str = "zh",
    depth: str = "normal",
    accessibility: str = "none"
):
    """获取讲解词
    
    参数:
        - spot_id: 景区ID
        - sub_spot_id: 子景点ID
        - level: basic/standard/deep
        - style: story/professional/casual
        - interest: history/architecture/nature
        - language: zh/en/ja/ko
        - depth: quick/normal/deep
        - accessibility: none/subtitle/audio_only/visual_desc
    """
    spot = knowledge_base.get_spot(spot_id)
    if not spot:
        raise HTTPException(status_code=404, detail=f"景区 {spot_id} 不存在")

    sub_spot = knowledge_base.get_sub_spot(spot_id, sub_spot_id)
    if not sub_spot:
        raise HTTPException(status_code=404, detail=f"子景点 {sub_spot_id} 不存在")

    try:
        level_enum = NarrationLevel(level)
    except ValueError:
        level_enum = NarrationLevel.STANDARD

    preference = UserPreference(
        style=style,
        interest=interest,
        language=language,
        depth=depth,
        accessibility_mode=accessibility
    )

    result = await generate_narration(spot, sub_spot, level_enum, preference)
    return result


# ═══════════════════════════════════════════════════════════════
# 问答
# ═══════════════════════════════════════════════════════════════

@router.post("/qa")
async def qa_question(request: QARequest):
    """问答接口"""
    spot = knowledge_base.get_spot(request.spot_id)
    if not spot:
        raise HTTPException(status_code=404, detail=f"景区 {request.spot_id} 不存在")

    sub_spot = knowledge_base.get_sub_spot(request.spot_id, request.sub_spot_id)
    if not sub_spot:
        raise HTTPException(status_code=404, detail=f"子景点 {request.sub_spot_id} 不存在")

    result = await answer_question(spot, sub_spot, request.question, request.preference)
    return result


# ═══════════════════════════════════════════════════════════════
# 知识库管理
# ═══════════════════════════════════════════════════════════════

@router.post("/reload")
async def reload_knowledge_base():
    """重新加载知识库"""
    knowledge_base.reload()
    return {"status": "ok", "count": len(knowledge_base.get_all_spots())}
