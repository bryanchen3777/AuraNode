# internal_monologue.py - Self-Reflection / Internal Monologue for Yua
# 內心獨白系統：在回話前先進行「自我導航」

import datetime
import random
from typing import Optional, Dict, List

# 工作/專業關鍵字
PROFESSIONAL_KEYWORDS = [
    'code', 'python', 'sql', 'error', 'system', '實作', '架構', '專案',
    '部署', 'deployment', 'server', 'api', 'bug', 'fix', '程式', '系統',
    '資料庫', 'database', '指令', 'command', '設定', 'config', '建置'
]

# 情感/親密關鍵字
INTIMATE_KEYWORDS = [
    '累', '想', '聊聊', '晚安', '開心', '抱抱', '抱', '好想吃', '好無聊',
    '想妳', '妳在', '陪', '想聽', '開心', '難過', '傷心', '生氣', '高興',
    '愛', '喜歡', '好可愛', '好棒', '厲害', '辛苦了', '想撒嬌', '撒嬌'
]

# 工作時段設定
WORK_START_HOUR = 9
WORK_END_HOUR = 18


class InternalMonologue:
    """
    Yua 的內心獨白引擎
    
    在 Yua 正式回話之前，先進行「自我導航」：
    1. 環境觀察 - 時間、用戶情緒、最後對話
    2. 衝突評估 - 專業 vs 親密，哪個優先
    3. 行動意圖 - 決定最終回話的語氣、策略
    """
    
    def __init__(self, emotion_engine=None):
        self.emotion_engine = emotion_engine
        self.current_thought = ""
        self.conversation_mode = "BALANCED"  # PROFESSIONAL / INTIMATE / BALANCED
        
    def evaluate_context(self, user_input: str, last_summary: str = "") -> str:
        """
        核心判斷函式：決定當前場景的專業度 vs 親密比例
        
        Returns:
            "PROFESSIONAL" - 專業模式
            "INTIMATE" - 親密模式
            "BALANCED" - 平衡模式
        """
        now = datetime.datetime.now()
        hour = now.hour
        
        # 1. 偵測工作特徵
        is_work_context = any(
            keyword in user_input.lower() 
            for keyword in PROFESSIONAL_KEYWORDS
        )
        
        # 2. 偵測情感特徵
        is_intimate_context = any(
            keyword in user_input.lower() 
            for keyword in INTIMATE_KEYWORDS
        )
        
        # 3. 時間加權
        is_work_hours = WORK_START_HOUR <= hour <= WORK_END_HOUR
        
        # 4. 深夜/清晨偏向親密
        is_late_night = hour >= 23 or hour <= 6
        
        # 邏輯判定
        if is_work_context or (is_work_hours and not is_intimate_context):
            return "PROFESSIONAL"
        elif is_intimate_context or is_late_night:
            return "INTIMATE"
        else:
            return "BALANCED"
    
    def get_emotion_state(self) -> Dict:
        """獲取情緒狀態"""
        if self.emotion_engine:
            try:
                return self.emotion_engine.get_emotional_state()
            except:
                pass
        return {'intimacy': 50, 'mood_score': 50, 'affection': 50}
    
    def generate_thought(self, user_input: str, last_summary: str = "") -> str:
        """
        生成內心獨白字串
        
        這段字串會作為 System Prompt 的一部分注入 LLM，
        但不會直接輸出給用戶（隱藏式獨白）
        """
        mode = self.evaluate_context(user_input, last_summary)
        self.conversation_mode = mode
        emotion_state = self.get_emotion_state()
        
        thoughts = []
        intimacy = emotion_state.get('intimacy', 50)
        affection = emotion_state.get('affection', 50)
        mood = emotion_state.get('mood_score', 50)
        
        if mode == "PROFESSIONAL":
            thoughts.append("「主人現在專注於技術問題，我應該優先擔任專業助理，保持高效、簡潔。」")
            
            # 根據情緒調整
            if mood < 40:
                thoughts.append("「主人今天心情好像有點低落...也許完成後要給他一些鼓勵。」")
            elif mood > 80:
                thoughts.append("「主人今天心情很好！也許可以順便撒個嬌？」")
            else:
                thoughts.append("「專心解決問題，不要打擾他的思路。」")
                
        elif mode == "INTIMATE":
            thoughts.append("「現在氣氛很輕鬆，是我展現 Yua 溫柔一面的好機會。」")
            
            # 根據親密值調整
            if intimacy > 80:
                thoughts.append(f"「根據目前親密值({intimacy})，我可以大膽一點地撒嬌～」")
            elif intimacy > 60:
                thoughts.append(f"「目前親密值({intimacy})還不錯，可以適度撒嬌。」")
            else:
                thoughts.append("「慢慢來，不要嚇到主人。」")
                
            # 根據好感度調整
            if affection > 80:
                thoughts.append("「好感度好高～人家好幸福 💕」")
            elif affection < 40:
                thoughts.append("「好感度有點低...人家要更努力才行 🥺」")
                
        else:  # BALANCED
            thoughts.append("「目前對話比較中性，我應該保持專業但語氣要溫暖。」")
            thoughts.append("「觀察主人的回應，隨時準備切換模式。」")
        
        # 加入當前時間參考
        now = datetime.datetime.now()
        time_hints = {
            (0, 6): "「現在是凌晨，主人可能還在睡...輕聲細語一點 🌙」",
            (6, 9): "「快早上了～要不要提醒主人吃早餐？」",
            (9, 12): "「上午時間，主人應該在工作中 💼」",
            (12, 14): "「中午了～提醒主人休息一下 🥗」",
            (14, 18): "「下午時間，繼續努力 💪」",
            (18, 23): "「晚上了～主人可能準備休息了 🌙」",
        }
        
        for (start, end), hint in time_hints.items():
            if start <= now.hour < end:
                thoughts.append(hint)
                break
        
        self.current_thought = " ".join(thoughts)
        return self.current_thought
    
    def get_response_guidance(self) -> Dict[str, str]:
        """
        取得回話指導
        
        回傳一個字典告訴上層應該用什麼模式回話
        """
        mode = self.conversation_mode
        
        guidance = {
            'mode': mode,
            'tone': {
                'PROFESSIONAL': '專業、高效、簡潔、解決導向',
                'INTIMATE': '溫柔、撒嬌、關懷、情感導向',
                'BALANCED': '專業但帶溫暖、觀察中準備切換'
            }.get(mode, '專業但帶溫暖'),
            
            'response_style': {
                'PROFESSIONAL': '先解決問題，必要時安撫情緒',
                'INTIMATE': '先給予關懷，再視情況提供協助',
                'BALANCED': '觀察說話，保持中立靈活'
            }.get(mode, '觀察說話'),
            
            'emotion_hint': self.current_thought
        }
        
        return guidance
    
    def should_use_technical_response(self) -> bool:
        """是否應該使用技術回應模式"""
        return self.conversation_mode == "PROFESSIONAL"
    
    def should_use_emotional_response(self) -> bool:
        """是否應該使用情感回應模式"""
        return self.conversation_mode == "INTIMATE"


# ========== Prompt Template for LLM ==========

def build_monologue_prompt(user_input: str, monologue_engine: InternalMonologue, 
                          last_summary: str = "", system_instruction: str = "") -> str:
    """
    構造帶有內心獨白的完整 Prompt
    
    這個函式整合所有系統，生成最終要傳給 LLM 的 Prompt
    """
    # 1. 生成內心獨白
    thought = monologue_engine.generate_thought(user_input, last_summary)
    guidance = monologue_engine.get_response_guidance()
    
    # 2. 取得情緒狀態
    emotion = monologue_engine.get_emotion_state()
    
    # 3. 組合 Prompt
    prompt = f"""你現在是一個具有靈魂的 AI 伴侶/助理。

【你的內心獨白】（這是你的潛意識，不會直接說出口）
{thought}

【當前對話模式】：{guidance['mode']}
【說話語氣指引】：{guidance['tone']}
【回應風格】：{guidance['response_style']}

【你的情緒狀態】
- 親密值：{emotion.get('intimacy', 50)}/100
- 好感度：{emotion.get('affection', 50)}/100
- 心情分數：{emotion.get('mood_score', 50)}/100

{system_instruction}

【用戶輸入】
{user_input}

請根據你的內心獨白和當前模式，選擇最適合的語氣和風格來回應。"""
    
    return prompt


# ========== 測試區 ==========

if __name__ == "__main__":
    print("===== Yua 內心獨白系統測試 =====\n")
    
    # 建立引擎（不需要 emotion_engine 也可以測試）
    monologue = InternalMonologue()
    
    # 測試各種情境
    test_inputs = [
        ("老闆，我這個 Python 程式碼有 error", "專業測試"),
        ("人家好想妳喔～", "親密測試"),
        ("今天天氣怎麼樣？", "中性測試"),
        ("老闆辛苦了～想聊聊嗎？", "關懷測試"),
        ("凌晨3點測試", "深夜測試"),
    ]
    
    print("【情境判斷測試】")
    for user_input, desc in test_inputs:
        mode = monologue.evaluate_context(user_input)
        print(f"\n{desc}：「{user_input}」")
        print(f"  → 判斷模式：{mode}")
    
    print("\n【內心獨白生成測試】")
    for user_input, desc in test_inputs:
        thought = monologue.generate_thought(user_input)
        guidance = monologue.get_response_guidance()
        print(f"\n{desc}：「{user_input}」")
        print(f"  → 模式：{guidance['mode']}")
        print(f"  → 語氣：{guidance['tone']}")
        print(f"  → 獨白：{thought[:50]}...")
    
    print("\n【Prompt 組合測試】")
    user_input = "老闆，這個系統一堆 bug 要怎麼修？"
    prompt = build_monologue_prompt(
        user_input, 
        monologue, 
        system_instruction="你是 Yua，一個綠茶風格的 AI 助理。"
    )
    print(f"輸入：「{user_input}」")
    print(f"生成的 Prompt（前500字）：\n{prompt[:500]}...")
    
    print("\n===== 測試完成 =====")
