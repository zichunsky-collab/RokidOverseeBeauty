"""项目配置 - 支持 MiMo / OpenAI 兼容 API"""
import os


def _env(key: str, default="") -> str:
    return os.getenv(key, default)


class Settings:
    def __init__(self):
        self._load_dotenv()

        self.APP_NAME = "镜览山河 - AI景区讲解系统"
        self.APP_VERSION = "1.0.0"
        self.DEBUG = _env("DEBUG", "true").lower() == "true"
        self.HOST = _env("HOST", "0.0.0.0")
        self.PORT = int(_env("PORT", "5000"))

        # LLM 配置（兼容 MiMo / OpenAI 格式）
        self.LLM_API_KEY = _env("LLM_API_KEY")
        self.LLM_MODEL = _env("LLM_MODEL", "MiMo-V2-Pro")
        self.LLM_BASE_URL = _env("LLM_BASE_URL", "https://api.xiaomimimo.com/v1")

        # 高德地图
        self.AMAP_KEY = _env("AMAP_KEY")

        # 定位配置
        self.GEOFENCE_RADIUS = int(_env("GEOFENCE_RADIUS", "500"))
        self.SUB_SPOT_RADIUS = int(_env("SUB_SPOT_RADIUS", "50"))

        # 讲解分层配置
        self.NARRATION_BASIC_THRESHOLD = int(_env("NARRATION_BASIC_THRESHOLD", "3"))
        self.NARRATION_STANDARD_THRESHOLD = int(_env("NARRATION_STANDARD_THRESHOLD", "10"))
        self.NARRATION_DEEP_THRESHOLD = int(_env("NARRATION_DEEP_THRESHOLD", "30"))

        # 用户偏好默认值
        self.DEFAULT_STYLE = _env("DEFAULT_STYLE", "story")
        self.DEFAULT_INTEREST = _env("DEFAULT_INTEREST", "history")
        self.DEFAULT_LANGUAGE = _env("DEFAULT_LANGUAGE", "zh")
        self.DEFAULT_DEPTH = _env("DEFAULT_DEPTH", "normal")

        # 知识库路径
        self.DATA_DIR = _env("DATA_DIR", "data/scenic_spots")

    def _load_dotenv(self):
        """简易 .env 加载"""
        candidates = [
            os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
            os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env"),
        ]
        for path in candidates:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            os.environ.setdefault(k.strip(), v.strip())
                break


settings = Settings()
