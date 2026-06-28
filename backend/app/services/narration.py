"""讲解词生成服务 - 核心引擎（MiMo/OpenAI兼容格式）"""
import json
from typing import Optional
from ..core.config import settings
from ..core.prompts import (
    NARRATION_SYSTEM_PROMPT, NARRATION_TEMPLATES,
    STYLE_MODIFIERS, INTEREST_MODIFIERS,
    LANGUAGE_MAP, QA_SYSTEM_PROMPT, VISION_DESCRIPTION_PROMPT
)
from ..models.schemas import (
    NarrationLevel, UserPreference, SubSpot, ScenicSpot, Depth
)


# ═══════════════════════════════════════════════════════════════
# LLM API 调用（OpenAI兼容格式）
# ═══════════════════════════════════════════════════════════════

async def call_llm(system_prompt: str, user_prompt: str) -> str:
    """调用LLM API生成内容（OpenAI兼容格式，支持MiMo）"""
    import httpx

    if not settings.LLM_API_KEY:
        # 没有API Key时返回模拟数据，方便本地调试
        return _mock_response(user_prompt)

    url = f"{settings.LLM_BASE_URL}/chat/completions"

    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.8,
        "top_p": 0.95,
        "max_tokens": 1024,
    }

    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def _mock_response(prompt: str) -> str:
    """本地调试用的模拟响应"""
    if "基础讲解" in prompt or "basic" in prompt.lower():
        return "这座看着不起眼的小楼，曾经决定过整个王朝的命运——停一下？"
    elif "深度讲解" in prompt or "deep" in prompt.lower():
        return ("你眼前这座城楼，已经在这里站了六百多年了。\n\n"
                "很多人不知道，它最初其实不是用来给皇帝住的。永乐皇帝迁都北京时，"
                "先修建了这座城楼作为临时指挥所，等紫禁城修好了才搬进去。"
                "换句话说，你现在站的地方，比皇帝正式上班的地方还早几个月出生。\n\n"
                "你看城楼上那些箭窗，红底白环黑靶心，像不像一只只眼睛？"
                "这可不是为了好看。当年这里停满了飞鸟，一开窗就扑楞楞乱飞影响军情，"
                "古人就把窗户画成眼睛的样子吓鸟——明朝人的脑洞，服不服？\n\n"
                "前面还有个更有意思的地方，跟我走。")
    else:
        return ("你看这台阶上的浮雕，磨得快看不清了——不是风吹的，"
                "是三百年来无数人跪着磕头磨出来的。当年文武百官上朝，"
                "走到这儿就得跪下，膝盖跪完了还不够，还得用磕头把这石头跪出感情来。"
                "所以你看，这台阶磨平的程度，基本就是清朝官员膝盖的耐磨指数。")


# ═══════════════════════════════════════════════════════════════
# 讲解词生成
# ═══════════════════════════════════════════════════════════════

async def generate_narration(
    spot: ScenicSpot,
    sub_spot: SubSpot,
    level: NarrationLevel,
    preference: UserPreference
) -> dict:
    """生成讲解词"""
    # 构建景点信息文本
    spot_info = f"景点名称：{spot.name} > {sub_spot.name}\n简介：{sub_spot.description}"
    history_info = sub_spot.history_info or "暂无详细历史资料"
    detail_info = sub_spot.detail_info or sub_spot.description
    related = ", ".join(sub_spot.related_spots) if sub_spot.related_spots else "暂无"

    # 获取模板
    template = NARRATION_TEMPLATES[level.value]
    user_prompt = template["prompt"].format(
        spot_name=f"{spot.name} > {sub_spot.name}",
        spot_info=spot_info,
        history_info=history_info,
        detail_info=detail_info,
        related_spots=related
    )

    # 添加个性化修饰
    system_prompt = NARRATION_SYSTEM_PROMPT + "\n\n"
    system_prompt += STYLE_MODIFIERS.get(preference.style.value, "")
    system_prompt += "\n" + INTEREST_MODIFIERS.get(preference.interest.value, "")

    # 深度模式
    if preference.depth == Depth.DEEP:
        system_prompt += "\n当前是深度游览模式，请展开更多细节和故事。"

    # 语言要求
    lang_name = LANGUAGE_MAP.get(preference.language.value, "中文")
    if preference.language.value != "zh":
        system_prompt += f"\n请用{lang_name}回答。"

    # 调用大模型
    narration = await call_llm(system_prompt, user_prompt)

    # 视障模式：生成画面描述
    accessibility_desc = None
    if preference.accessibility_mode == "visual_desc":
        vision_prompt = f"请为以下景点生成一段画面描述，帮助视障用户理解眼前的场景：\n\n{spot.name} > {sub_spot.name}\n{sub_spot.description}"
        accessibility_desc = await call_llm(VISION_DESCRIPTION_PROMPT, vision_prompt)

    return {
        "spot_name": f"{spot.name} > {sub_spot.name}",
        "level": level.value,
        "narration": narration.strip(),
        "language": preference.language.value,
        "accessibility_desc": accessibility_desc
    }


# ═══════════════════════════════════════════════════════════════
# 问答
# ═══════════════════════════════════════════════════════════════

async def answer_question(
    spot: ScenicSpot,
    sub_spot: SubSpot,
    question: str,
    preference: UserPreference
) -> dict:
    """回答游客提问"""
    context = f"当前景点：{spot.name} > {sub_spot.name}\n景点介绍：{sub_spot.description}\n历史资料：{sub_spot.history_info}"
    user_prompt = f"{context}\n\n游客提问：{question}"

    lang_name = LANGUAGE_MAP.get(preference.language.value, "中文")
    system = QA_SYSTEM_PROMPT
    if preference.language.value != "zh":
        system += f"\n请用{lang_name}回答。"

    answer = await call_llm(system, user_prompt)

    return {
        "answer": answer.strip(),
        "source": f"{spot.name} > {sub_spot.name}",
        "spot_name": spot.name,
    }
