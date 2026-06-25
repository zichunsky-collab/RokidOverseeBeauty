"""
镜览山河 - AI眼镜智能景区讲解系统
后端服务：GPS → 高德POI → 知识库 → 大模型讲解词生成
"""

import json
import math
import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ============ 配置 ============
GAODE_KEY = os.environ.get("GAODE_KEY", "6ec0f76e80b0d23285991c56bf7f6dfa")
# 大模型API（可选，不配置则使用知识库预置讲解词）
LLM_API_URL = os.environ.get("LLM_API_URL", "")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "")

# ============ 加载知识库 ============
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
knowledge_base = {}


def load_knowledge_base():
    """加载所有景区知识库JSON"""
    global knowledge_base
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(DATA_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                spot_id = data["scenic_spot"]["id"]
                knowledge_base[spot_id] = data
                print(f"[KB] 已加载景区: {data['scenic_spot']['name']} ({len(data.get('sub_spots', []))} 个子景点)")


# ============ 工具函数 ============

def haversine_distance(lat1, lng1, lat2, lng2):
    """计算两个经纬度之间的距离（米）"""
    R = 6371000  # 地球半径（米）
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def find_nearest_sub_spot(lat, lng, spot_data):
    """在景区内找到最近的子景点"""
    best = None
    best_dist = float("inf")

    for sub in spot_data.get("sub_spots", []):
        sub_lng, sub_lat = sub["center"]
        dist = haversine_distance(lat, lng, sub_lat, sub_lng)
        trigger_radius = sub.get("radius", 30)
        if dist < trigger_radius and dist < best_dist:
            best = sub
            best_dist = dist

    return best, best_dist


def find_matching_scenic_spot(lat, lng):
    """根据GPS坐标匹配景区"""
    for spot_id, spot_data in knowledge_base.items():
        spot = spot_data["scenic_spot"]
        spot_lng, spot_lat = spot["center"]
        dist = haversine_distance(lat, lng, spot_lat, spot_lng)
        spot_radius = spot.get("radius", 500)
        if dist < spot_radius:
            return spot_data, dist
    return None, float("inf")


def call_llm(prompt):
    """调用大模型生成讲解词（可选）"""
    if not LLM_API_URL or not LLM_API_KEY:
        return None
    try:
        headers = {
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": LLM_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一位有20年经验的金牌导游，专讲历史文化与古建筑。像在跟朋友聊天，喜欢用类比把复杂的事说简单。会穿插有趣的野史、冷知识。不念数字堆砌，不用'该建筑''该景点'等书面词，先勾起兴趣再报名字。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 500,
        }
        resp = requests.post(LLM_API_URL, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[LLM] 调用失败: {e}")
    return None


# ============ API 端点 ============

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "loaded_scenes": len(knowledge_base)})


@app.route("/api/nearby", methods=["GET"])
def nearby():
    """
    根据GPS坐标查询附近景点
    参数: lat, lng
    返回: 匹配的景区和子景点信息
    """
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)

    if lat is None or lng is None:
        return jsonify({"error": "缺少 lat 或 lng 参数"}), 400

    # 1. 先在本地知识库匹配
    spot_data, spot_dist = find_matching_scenic_spot(lat, lng)
    if spot_data:
        sub_spot, sub_dist = find_nearest_sub_spot(lat, lng, spot_data)
        return jsonify({
            "matched": True,
            "scenic_spot": {
                "id": spot_data["scenic_spot"]["id"],
                "name": spot_data["scenic_spot"]["name"],
                "distance": round(spot_dist),
            },
            "sub_spot": {
                "id": sub_spot["id"],
                "name": sub_spot["name"],
                "distance": round(sub_dist),
            } if sub_spot else None,
            "in_scenic_area": True,
        })

    # 2. 本地没匹配到，调高德POI查询附近景点
    try:
        # 如果高德Key未配置或不可用，返回提示
        if GAODE_KEY == "YOUR_KEY":
            return jsonify({
                "matched": False,
                "in_scenic_area": False,
                "nearby_pois": [],
                "message": "高德API Key未配置，请设置环境变量 GAODE_KEY",
            })

        gaode_url = "https://restapi.amap.com/v3/place/around"
        params = {
            "key": GAODE_KEY,
            "location": f"{lng},{lat}",
            "radius": 2000,
            "types": "风景名胜",
            "extensions": "base",
            "offset": 5,
        }
        resp = requests.get(gaode_url, params=params, timeout=5)
        data = resp.json()

        if data.get("status") == "1" and data.get("pois"):
            pois = []
            for poi in data["pois"][:5]:
                pois.append({
                    "name": poi.get("name", ""),
                    "address": poi.get("address", ""),
                    "location": poi.get("location", ""),
                    "distance": poi.get("distance", ""),
                })
            return jsonify({
                "matched": False,
                "in_scenic_area": False,
                "nearby_pois": pois,
                "message": "当前不在已收录景区内，以下是附近景点",
            })
        else:
            # 高德API失败，返回错误信息
            return jsonify({
                "matched": False,
                "in_scenic_area": False,
                "nearby_pois": [],
                "message": f"高德API返回: {data.get('info', '未知错误')}",
                "gaode_infocode": data.get("infocode", ""),
            })

    except Exception as e:
        return jsonify({
            "matched": False,
            "in_scenic_area": False,
            "error": str(e),
        })


@app.route("/api/narration", methods=["GET"])
def narration():
    """
    获取讲解词
    参数: spot_id, sub_spot_id, level (基础层/标准层/深度层), lang (zh/en)
    """
    spot_id = request.args.get("spot_id", "")
    sub_spot_id = request.args.get("sub_spot_id", "")
    level = request.args.get("level", "")
    lang = request.args.get("lang", "zh")

    # 兼容 URL 编码：支持 level=1/2/3 或中文
    level_map = {"1": "基础层", "2": "标准层", "3": "深度层"}
    level = level_map.get(level, level) or "标准层"
    if level not in ("基础层", "标准层", "深度层"):
        level = "标准层"

    spot_data = knowledge_base.get(spot_id)
    if not spot_data:
        return jsonify({"error": f"未找到景区: {spot_id}"}), 404

    # 查找子景点
    sub_spot = None
    for sub in spot_data.get("sub_spots", []):
        if sub["id"] == sub_spot_id:
            sub_spot = sub
            break

    if not sub_spot:
        return jsonify({"error": f"未找到子景点: {sub_spot_id}"}), 404

    # 获取讲解词
    narration_text = sub_spot.get("narration", {}).get(level, "")
    if not narration_text:
        narration_text = sub_spot.get("narration", {}).get("标准层", "暂无讲解内容")

    # 尝试用大模型润色（可选）
    if LLM_API_URL:
        llm_prompt = f"""以下是关于{sub_spot['name']}的讲解素材，请用口语化、故事化的方式重新组织，像一个有趣的导游在跟游客聊天。
不要用"该景点""该建筑"等书面词。控制在150字以内。

素材：{narration_text}"""
        llm_result = call_llm(llm_prompt)
        if llm_result:
            narration_text = llm_result

    return jsonify({
        "spot_name": sub_spot["name"],
        "level": level,
        "narration": narration_text,
        "qa": sub_spot.get("qa", {}),
    })


@app.route("/api/qa", methods=["POST"])
def qa():
    """
    问答接口
    请求体: { "spot_id": "xxx", "sub_spot_id": "xxx", "question": "xxx" }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "请求体为空"}), 400

    spot_id = data.get("spot_id", "")
    sub_spot_id = data.get("sub_spot_id", "")
    question = data.get("question", "")

    spot_data = knowledge_base.get(spot_id)
    if not spot_data:
        return jsonify({"error": f"未找到景区: {spot_id}"}), 404

    sub_spot = None
    for sub in spot_data.get("sub_spots", []):
        if sub["id"] == sub_spot_id:
            sub_spot = sub
            break

    if not sub_spot:
        return jsonify({"error": f"未找到子景点: {sub_spot_id}"}), 404

    # 1. 先在预设Q&A中查找最匹配的答案
    qa_data = sub_spot.get("qa", {})
    best_answer = None
    for q, a in qa_data.items():
        # 简单关键词匹配
        if any(kw in question for kw in q):
            best_answer = a
            break

    if best_answer:
        return jsonify({
            "answer": best_answer,
            "source": "knowledge_base",
            "spot_name": sub_spot["name"],
        })

    # 2. 预设Q&A没匹配到，调大模型
    if LLM_API_URL:
        context = sub_spot.get("narration", {}).get("深度层", "")
        llm_prompt = f"""游客在{sub_spot['name']}参观时问了一个问题，请根据以下背景知识回答。回答要像导游跟游客聊天一样自然，不要用书面语。如果不确定答案，诚实说不知道。

背景知识：{context}

游客问题：{question}"""
        llm_answer = call_llm(llm_prompt)
        if llm_answer:
            return jsonify({
                "answer": llm_answer,
                "source": "llm",
                "spot_name": sub_spot["name"],
            })

    return jsonify({
        "answer": "这个问题我不太确定答案，建议您看看旁边的介绍牌，或者到了下一个景点我再给您详细讲讲。",
        "source": "fallback",
        "spot_name": sub_spot["name"],
    })


@app.route("/api/scenic_spots", methods=["GET"])
def list_scenic_spots():
    """列出所有已收录景区"""
    spots = []
    for spot_id, spot_data in knowledge_base.items():
        spot = spot_data["scenic_spot"]
        spots.append({
            "id": spot_id,
            "name": spot["name"],
            "sub_spots_count": len(spot_data.get("sub_spots", [])),
        })
    return jsonify({"spots": spots})


if __name__ == "__main__":
    load_knowledge_base()
    print(f"\n[Server] 已加载 {len(knowledge_base)} 个景区")
    print(f"[Server] 高德Key: {GAODE_KEY[:8]}...")
    print(f"[Server] LLM: {'已配置' if LLM_API_URL else '未配置（使用预置讲解词）'}")
    print(f"[Server] 启动服务: http://0.0.0.0:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
