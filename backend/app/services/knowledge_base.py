"""知识库管理服务 - 加载和查询景区数据"""
import json
import os
from typing import Optional, List, Dict
from ..models.schemas import ScenicSpot, SubSpot, GeoLocation
from ..core.config import settings


class KnowledgeBaseService:
    """知识库服务 - 管理景区数据"""

    def __init__(self):
        self.spots: Dict[str, ScenicSpot] = {}
        self._load_all_spots()

    def _load_all_spots(self):
        """加载所有景区数据"""
        data_dir = os.path.join(os.path.dirname(__file__), "..", "..", settings.DATA_DIR)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            return

        for filename in os.listdir(data_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(data_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    spot = ScenicSpot(**data)
                    self.spots[spot.id] = spot
                    print(f"✅ 已加载景区: {spot.name} ({len(spot.sub_spots)}个子景点)")
                except Exception as e:
                    print(f"❌ 加载失败 {filename}: {e}")

    def get_all_spots(self) -> List[ScenicSpot]:
        """获取所有景区"""
        return list(self.spots.values())

    def get_spot(self, spot_id: str) -> Optional[ScenicSpot]:
        """获取指定景区"""
        return self.spots.get(spot_id)

    def get_sub_spot(self, spot_id: str, sub_spot_id: str) -> Optional[SubSpot]:
        """获取子景点"""
        spot = self.spots.get(spot_id)
        if not spot:
            return None
        for sub in spot.sub_spots:
            if sub.id == sub_spot_id:
                return sub
        return None

    def find_nearby_spot(self, lat: float, lng: float) -> tuple:
        """查找最近的景点
        
        Returns:
            (ScenicSpot, SubSpot, distance_meters) 或 (None, None, None)
        """
        user_loc = GeoLocation(lat=lat, lng=lng)
        best_match = None
        best_sub = None
        best_distance = float("inf")

        for spot in self.spots.values():
            # 先检查是否在景区范围内
            spot_dist = self._calc_distance(user_loc, spot.location)
            if spot_dist > spot.radius:
                continue

            # 在景区内，找最近的子景点
            for sub in spot.sub_spots:
                sub_dist = self._calc_distance(user_loc, sub.location)
                if sub_dist < sub.radius and sub_dist < best_distance:
                    best_match = spot
                    best_sub = sub
                    best_distance = sub_dist

        return best_match, best_sub, int(best_distance) if best_distance != float("inf") else None

    def _calc_distance(self, p1: GeoLocation, p2: GeoLocation) -> float:
        """计算两点之间的距离（米）- Haversine公式"""
        import math
        R = 6371000  # 地球半径（米）

        lat1 = math.radians(p1.lat)
        lat2 = math.radians(p2.lat)
        dlat = math.radians(p2.lat - p1.lat)
        dlng = math.radians(p2.lng - p1.lng)

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    def reload(self):
        """重新加载所有数据"""
        self.spots.clear()
        self._load_all_spots()


# 单例
knowledge_base = KnowledgeBaseService()
