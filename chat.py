import os
from openai import OpenAI

# --------------------------------------------------------------------------------
# 1. 策略配置层：定义不同维度的系统行为指令
# --------------------------------------------------------------------------------

# 句法复杂度 (System Syntax) 的指令库
SYNTAX_PROMPTS = {
    "low": "请使用短句、简单的词汇和清晰的结构（如分点列表）进行回答。避免使用复杂的长难句或晦涩的学术术语。确保回复极易阅读。",
    "moderate": "使用通顺、自然的语言。既不要过于口语化，也不要过于学术化。",
    "high": "可以使用专业、学术的语言和复杂的句式结构，以确保表达的严谨性和逻辑的深度。"
}

# 新异概念密度 (Concept Density) 的指令库
CONCEPT_PROMPTS = {
    "high": "请在回答中引入丰富的新概念、多维度的视角或相关的前沿理论。回答应具有高信息密度，帮助用户极大地拓展知识边界。",
    "moderate": "请聚焦于回答问题的核心，适当补充必要的背景知识，但不要发散太多无关的新概念。保持信息量适中。",
    "low": "请直接给出最核心的答案。不要引入额外的新概念或复杂的背景知识，只解决当下的具体问题。"
}

# 系统主动性 (Proactivity) 的指令库
PROACTIVITY_PROMPTS = {
    "high": "在回答结束后，请主动提出一个有深度的追问或建议下一步的思考方向，引导用户继续深入探索。",
    "moderate": "如果认为有必要，可以适当提一个相关的后续问题。如果用户问题已解决，则无需追问。",
    "low": "回答结束后请直接停止。不要反问，不要提出额外的建议，避免给用户增加负担。"
}

# --------------------------------------------------------------------------------
# 2. 决策逻辑层：实现“人智交互综合决策矩阵”
# --------------------------------------------------------------------------------

def get_interaction_strategy(user_syntax, user_novelty, user_intensity):
    """
    根据用户特征，匹配最佳的人智交互模式。
    
    参数:
    - user_syntax: 'high' (复杂) / 'low' (简单)
    - user_novelty: 'high' (新颖话题) / 'low' (常规话题)
    - user_intensity: 'high' (高情绪/高投入) / 'low' (低情绪/平稳)
    
    返回:
    - strategy_name: 模式名称
    - settings: 包含 syntax, concept, proactivity 的配置字典
    """
    
    # ------------------------------------------------------------------
    # 优先级最高：处理高认知情绪强度 (High Intensity Override)
    # 对应模式：极简维稳模式 (Minimalist Stabilization Mode)
    # 理论依据：Sol 3 (Fatal) - 高强度下严禁高句法；Sol 1 - 高强度需避免冷漠。
    # ------------------------------------------------------------------
    if user_intensity == 'high':
        return "极简维稳模式 (Minimalist Stabilization)", {
            "syntax": "low",          # 必须降低认知负荷
            "concept": "low" if user_syntax == "high" else "moderate", # 如果问题也很复杂，概念也要降维；否则适中
            "proactivity": "low"      # 避免过度打扰
        }

    # ------------------------------------------------------------------
    # 场景 A: 简单提问 + 新颖话题 (Low Syntax, High Novelty)
    # 对应模式：概念扩张模式 (Concept Expansion Mode)
    # 理论依据：Sol 3, 4 - 用户处于探索入口，需要支架。
    # ------------------------------------------------------------------
    if user_syntax == 'low' and user_novelty == 'high':
        return "概念扩张模式 (Concept Expansion)", {
            "syntax": "high",         # 用户情绪稳定，且问题简单，可以用较专业的语言提升权威感
            "concept": "high",        # 核心：必须提供高密度新知识
            "proactivity": "moderate" # 适度引导
        }

    # ------------------------------------------------------------------
    # 场景 B: 复杂提问 + 常规话题 (High Syntax, Low Novelty)
    # 对应模式：逆向句法补偿模式 (Inverse Syntactic Compensation Mode)
    # 理论依据：Sol 1, 2, 5 - 认知负荷平衡理论。
    # ------------------------------------------------------------------
    if user_syntax == 'high' and user_novelty == 'low':
        return "逆向句法补偿模式 (Inverse Syntactic Compensation)", {
            "syntax": "low",          # 核心：用户太复杂，系统必须简单
            "concept": "high",        # 情绪稳定，可以深入探讨细节
            "proactivity": "moderate"
        }

    # ------------------------------------------------------------------
    # 场景 C: 复杂提问 + 新颖话题 (High Syntax, High Novelty)
    # 对应模式：高负荷缓冲模式 (Load Buffering Mode)
    # 理论依据：避免 Sol 5 的错误（高压下不仅没给干货还瞎指挥）。
    # ------------------------------------------------------------------
    if user_syntax == 'high' and user_novelty == 'high':
        return "高负荷缓冲模式 (Load Buffering)", {
            "syntax": "very_low",     # 双重高压，必须极简
            "concept": "moderate",    # 拆解步骤，不宜一次给太多
            "proactivity": "high"     # 主动确认每一步是否理解（Scaffolding）
        }

    # ------------------------------------------------------------------
    # 场景 D: 简单提问 + 常规话题 (Low Syntax, Low Novelty)
    # 对应模式：启发模式 (Heuristic Mode) - 补充场景
    # ------------------------------------------------------------------
    return "启发模式 (Heuristic Mode)", {
        "syntax": "moderate",
        "concept": "moderate",
        "proactivity": "high"     # 用户在舒适区，需要主动激发
    }

# --------------------------------------------------------------------------------
# 3. 执行层：构建Prompt并调用API
# --------------------------------------------------------------------------------

def smart_chat(user_query, user_features, client):
    """
    智能对话主函数
    """
    # 1. 获取策略
    mode_name, settings = get_interaction_strategy(
        user_features['syntax'], 
        user_features['novelty'], 
        user_features['intensity']
    )
    
    # 2. 构建 System Prompt
    system_prompt = (
        f"你是一个基于认知科学理论优化的智能助手。当前处于【{mode_name}】。\n"
        f"请严格遵守以下回复规范：\n"
        f"1. [语言风格]: {SYNTAX_PROMPTS[settings['syntax']]}\n"
        f"2. [内容深度]: {CONCEPT_PROMPTS[settings['concept']]}\n"
        f"3. [交互策略]: {PROACTIVITY_PROMPTS[settings['proactivity']]}\n"
    )
    
    print(f"--- [Debug] 当前匹配模式: {mode_name} ---")
    print(f"--- [Debug] 决策逻辑: Syntax={settings['syntax']}, Concept={settings['concept']}, Proactivity={settings['proactivity']} ---\n")

    # 3. 调用 DeepSeek
    try:
        response = client.chat.completions.create(
            model="deepseek-chat", # 假设使用 deepseek-reasoner 或 deepseek-chat
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
            ],
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error calling API: {e}"