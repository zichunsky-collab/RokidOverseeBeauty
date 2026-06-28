"""数据模型定义"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


# ═══════════════════════════════════════════════════════════════
# 枚举类型
# ═══════════════════════════════════════════════════════════════

class NarrationLevel(str, Enum):
    """讲解深度层级"""
    BASIC = "basic"       # 基础层：10秒，30字以内
    STANDARD = "standard"  # 标准层：30秒，100-150字
    DEEP = "deep"          # 深度层：2分钟+，400字+

class Style(str, Enum):
    STORY = "story"
    PROFESSIONAL = "professional"
    CASUAL = "casual"

class Interest(str, Enum):
    HISTORY = "history"
    ARCHITECTURE = "architecture"
    NATURE = "nature"

class Language(str, Enum):
    ZH = "zh"
    EN = "en"
    JA = "ja"
    KO = "ko"

class Depth(str, Enum):
    QUICK = "quick"
    NORMAL = "normal"
    DEEP = "deep"


# ═══════════════════════════════════════════════════════════════
# 用户偏好
# ═══════════════════════════════════════════════════════════════

class UserPreference(BaseModel):
    """用户个性化偏好"""
    style: Style = Style.STORY
    interest: Interest = Interest.HISTORY
    language: Language = Language.ZH
    depth: Depth = Depth.NORMAL
    accessibility_mode: str = "none"  # none / subtitle / audio_only / visual_desc


# ═══════════════════════════════════════════════════════════════
# 景点数据
# ═══════════════════════════════════════════════════════════════

class GeoLocation(BaseModel):
    """地理坐标"""
    lat: float
    lng: float

class SubSpot(BaseModel):
    """子景点"""
    id: str
    name: str
    location: GeoLocation
    radius: int = 50  # 识别半径（米）
    description: str = ""
    keywords: List[str] = []
    history_info: str = ""
    detail_info: str = ""
    related_spots: List[str] = []

class ScenicSpot(BaseModel):
    """景区"""
    id: str
    name: str
    location: GeoLocation
    radius: int = 500  # 景区范围（米）
    description: str = ""
    sub_spots: List[SubSpot] = []


# ═══════════════════════════════════════════════════════════════
# API 请求/响应
# ═══════════════════════════════════════════════════════════════

class LocationRequest(BaseModel):
    """GPS定位请求"""
    lat: float = Field(..., description="纬度")
    lng: float = Field(..., description="经度")
    heading: Optional[float] = Field(None, description="朝向角度（0-360）")

class NearbyResponse(BaseModel):
    """附近景点响应"""
    matched: bool
    in_scenic_area: bool
    scenic_spot: Optional[Dict[str, Any]] = None
    sub_spot: Optional[Dict[str, Any]] = None
    distance: Optional[int] = None
    message: str = ""

class NarrationRequest(BaseModel):
    """讲解词请求"""
    spot_id: str
    sub_spot_id: str
    level: NarrationLevel = NarrationLevel.STANDARD
    preference: UserPreference = UserPreference()

class NarrationResponse(BaseModel):
    """讲解词响应"""
    spot_name: str
    level: str
    narration: str
    language: str = "zh"
    accessibility_desc: Optional[str] = None  # 视障用户画面描述

class QARequest(BaseModel):
    """问答请求"""
    spot_id: str
    sub_spot_id: str
    question: str
    preference: UserPreference = UserPreference()

class QAResponse(BaseModel):
    """问答响应"""
    answer: str
    source: str = ""
    spot_name: str = ""

class HealthResponse(BaseModel):
    """健康检查"""
    status: str = "ok"
    version: str = ""
    scenic_spots_count: int = 0
