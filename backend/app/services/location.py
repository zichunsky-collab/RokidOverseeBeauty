"""定位服务 - GPS定位 + 景区识别"""
from typing import Optional, Tuple
from ..models.schemas import GeoLocation, ScenicSpot, SubSpot
from ..services.knowledge_base import knowledge_base


class LocationService:
    """定位服务"""

    def find_nearby(self, lat: float, lng: float) -> dict:
        """根据GPS坐标查找附近景点
        
        Returns:
            {
                "matched": bool,
                "in_scenic_area": bool,
                "scenic_spot": {...} | None,
                "sub_spot": {...} | None,
                "distance": int | None,
                "message": str
            }
        """
        spot, sub_spot, distance = knowledge_base.find_nearby_spot(lat, lng)

        if spot and sub_spot:
            return {
                "matched": True,
                "in_scenic_area": True,
                "scenic_spot": {"id": spot.id, "name": spot.name, "distance": distance},
                "sub_spot": {"id": sub_spot.id, "name": sub_spot.name, "distance": distance},
                "distance": distance,
                "message": f"已识别：{spot.name} > {sub_spot.name}"
            }

        # 不在任何景点范围内，返回最近的景区信息
        nearest = self._find_nearest_spot(lat, lng)
        if nearest:
            spot, dist = nearest
            return {
                "matched": False,
                "in_scenic_area": True,
                "scenic_spot": {"id": spot.id, "name": spot.name, "distance": int(dist)},
                "sub_spot": None,
                "distance": int(dist),
                "message": f"您在{spot.name}景区内，距离最近景点约{int(dist)}米"
            }

        return {
            "matched": False,
            "in_scenic_area": False,
            "scenic_spot": None,
            "sub_spot": None,
            "distance": None,
            "message": "您当前不在任何景区范围内"
        }

    def _find_nearest_spot(self, lat: float, lng: float) -> Optional[Tuple[ScenicSpot, float]]:
        """找到最近的景区（不要求在范围内）"""
        import math

        user_loc = GeoLocation(lat=lat, lng=lng)
        best = None
        best_dist = float("inf")

        for spot in knowledge_base.get_all_spots():
            dist = self._calc_distance(user_loc, spot.location)
            if dist < best_dist:
                best_dist = dist
                best = spot

        if best and best_dist < 5000:  # 5公里内
            return best, best_dist
        return None

    def _calc_distance(self, p1: GeoLocation, p2: GeoLocation) -> float:
        """Haversine公式计算距离"""
        import math
        R = 6371000
        lat1, lat2 = math.radians(p1.lat), math.radians(p2.lat)
        dlat = math.radians(p2.lat - p1.lat)
        dlng = math.radians(p2.lng - p1.lng)
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


location_service = LocationService()
