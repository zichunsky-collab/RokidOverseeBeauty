# 镜览山河 - AI眼镜智能景区讲解系统

## 项目结构

```
jinglanshetu/
├── README.md              ← 本文件
├── backend/
│   ├── server.py          ← Python Flask 后端服务
│   └── requirements.txt   ← Python 依赖
├── data/
│   └── zongtongfu.json    ← 南京总统府知识库（10个子景点）
└── android/
    └── README.md          ← Android 端开发指南（含完整代码）
```

## 快速开始

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
python3 server.py
# 服务启动在 http://0.0.0.0:5000
```

### 2. 测试 API

```bash
# 健康检查
curl http://localhost:5000/api/health

# GPS 查询（总统府坐标）
curl "http://localhost:5000/api/nearby?lat=32.0456&lng=118.7942"

# 获取讲解词
curl "http://localhost:5000/api/narration?spot_id=zongtongfu&sub_spot_id=datang&level=2"

# 问答
curl -X POST http://localhost:5000/api/qa \
  -H "Content-Type: application/json" \
  -d '{"spot_id":"zongtongfu","sub_spot_id":"zichao","question":"子超楼为什么叫子超楼"}'
```

### 3. 开发 Android 端

详见 `android/README.md`

## API 接口

| 接口 | 方法 | 参数 | 说明 |
|------|------|------|------|
| `/api/health` | GET | - | 健康检查 |
| `/api/scenic_spots` | GET | - | 列出所有景区 |
| `/api/nearby` | GET | `lat`, `lng` | GPS 查询附近景点 |
| `/api/narration` | GET | `spot_id`, `sub_spot_id`, `level`(1/2/3) | 获取讲解词 |
| `/api/qa` | POST | JSON: `spot_id`, `sub_spot_id`, `question` | 问答 |

## 知识库格式

每个景区一个 JSON 文件，放在 `data/` 目录下。格式参考 `zongtongfu.json`。

## 待办

- [ ] 修复高德 API Key（需要开通 Web 服务类型）
- [ ] 部署后端到公网服务器
- [ ] 开发 Android App
- [ ] 接入 Rokid 眼镜 SDK
- [ ] 增加更多景区知识库
- [ ] 接入大模型实现动态讲解词生成
