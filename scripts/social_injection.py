# social_injection.py - 動態社交規則注入系統 for AuraNode
# 在回應前動態注入社交規則到 System Prompt

import datetime
from typing import Dict, List, Optional

# 預設資料庫路徑
DEFAULT_DB_PATH = "C:/Users/bbfcc/.openclaw/workspace/memory/auranode.db"


class SocialInjectionEngine:
    """
    AuraNode 動態社交規則注入引擎
    
    串聯現有系統：
    - rag_engine：檢索記憶與規則
    - internal_monologue：獲取情境判斷
    - evolution_engine：話術風格建議
    - reflection_engine：社交規則資料庫
    
    流程：
    1. 從 internal_monologue 獲取當前情境
    2. 根據情境標籤檢索相關社交規則
    3. 組合進 System Prompt 動態注入
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        
        # 嘗試匯入現有系統
        self.rag = None
        self.evolution = None
        self.reflection = None
        
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            
            from rag_engine import build_dynamic_context
            self.rag_build_context = build_dynamic_context
        except ImportError:
            self.rag_build_context = None
    
    # ========== 情境標籤提取 ==========
    
    def _determine_context_tags(self, monologue_data: Dict) -> List[str]:
        """
        分析內心獨白，提取關鍵標籤用於檢索
        
        Args:
            monologue_data: 來自 internal_monologue 的資料
        
        Returns:
            List[str]: 情境標籤列表
        """
        tags = []
        
        # 從情緒維度提取
        emotion = monologue_data.get('current_emotion', 'neutral')
        if emotion:
            tags.append(emotion)
        
        # 從意圖維度提取
        intent = monologue_data.get('user_intent', 'general')
        if intent:
            tags.append(intent)
        
        # 從對話模式提取
        mode = monologue_data.get('conversation_mode', 'BALANCED')
        if mode:
            tags.append(mode.lower())
        
        # 從使用者情緒提取
        user_emotion = monologue_data.get('user_emotion', '')
        if user_emotion:
            tags.append(user_emotion)
        
        # 時間維度（深夜自動切換撒嬌或溫柔模式）
        hour = datetime.datetime.now().hour
        if 23 <= hour or hour <= 5:
            tags.append('late_night')
            tags.append('rest_period')
        elif 9 <= hour <= 18:
            tags.append('work_hours')
        else:
            tags.append('off_hours')
        
        # 工作/休閒維度
        if monologue_data.get('is_work_context'):
            tags.append('work_context')
        else:
            tags.append('casual_context')
        
        return list(set(tags))  # 去重
    
    # ========== 規則檢索 ==========
    
    def get_social_rules(self, monologue_data: Dict, 
                       category: str = None, limit: int = 3) -> List[Dict]:
        """
        根據當前情境檢索相關的社交規則
        
        Args:
            monologue_data: 內心獨白資料
            category: 可選的規則分類過濾
            limit: 返回數量
        
        Returns:
            List[Dict]: 匹配的社交規則
        """
        import sqlite3
        
        tags = self._determine_context_tags(monologue_data)
        
        # 構建查詢
        query_parts = [f"%{tag}%" for tag in tags]
        query_conditions = " OR ".join(["rule_content LIKE ?"] * len(query_parts))
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if category:
                cursor.execute(f"""
                    SELECT id, rule_content, category, confidence_score
                    FROM social_rules
                    WHERE ({query_conditions})
                      AND category = ?
                    ORDER BY confidence_score DESC
                    LIMIT ?
                """, (*query_parts, category, limit))
            else:
                cursor.execute(f"""
                    SELECT id, rule_content, category, confidence_score
                    FROM social_rules
                    WHERE {query_conditions}
                    ORDER BY confidence_score DESC
                    LIMIT ?
                """, (*query_parts, limit))
            
            columns = ['id', 'rule_content', 'category', 'confidence']
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def _get_default_rules(self, monologue_data: Dict) -> List[str]:
        """當沒有找到規則時的預設規則"""
        mode = monologue_data.get('conversation_mode', 'BALANCED')
        
        default_rules = {
            'PROFESSIONAL': [
                '保持專業、簡潔、解決導向',
                '先確認問題核心，再提供解決方案',
                '避免過多情感表達，專注在任務完成'
            ],
            'INTIMATE': [
                '語氣溫柔，可以加入撒嬌元素',
                '多使用「人家」、「老闆」等親密稱謂',
                '適度表達關心與想念'
            ],
            'BALANCED': [
                '保持專業但帶溫暖',
                '觀察用戶回應，隨時準備切換模式'
            ]
        }
        
        return default_rules.get(mode, default_rules['BALANCED'])
    
    # ========== 動態 Prompt 組裝 ==========
    
    def build_social_context_section(self, monologue_data: Dict) -> str:
        """
        建立社交行為準則區塊
        
        Returns:
            str: 格式化後的社交準則文字
        """
        # 檢索相關規則
        rules = self.get_social_rules(monologue_data, limit=3)
        
        if not rules:
            default_rules = self._get_default_rules(monologue_data)
            rules_text = "\n".join([f"- {r}" for r in default_rules])
        else:
            rules_text = "\n".join([
                f"- [{r['category']}] {r['rule_content']} (信心: {r['confidence']:.0%})"
                for r in rules
            ])
        
        return rules_text
    
    def build_evolution_hint_section(self, monologue_data: Dict) -> str:
        """
        建立話術風格引導區塊
        
        從 evolution_engine 獲取成功話術建議
        """
        hints = []
        
        # 嘗試從 evolution_engine 獲取優化話術
        try:
            from evolution_engine import EvolutionEngine
            evolution = EvolutionEngine(self.db_path)
            top_scripts = evolution.get_top_performers(limit=3)
            
            if top_scripts:
                hints.append("參考成功話術案例：")
                for script in top_scripts:
                    tone = script.get('tone_type', 'N/A')
                    content = script.get('content', '')[:30]
                    hints.append(f"- [{tone}] {content}...")
        except ImportError:
            pass
        
        # 從內心獨白獲取當前指導
        guidance = monologue_data.get('response_guidance', {})
        if guidance:
            tone = guidance.get('tone', '')
            style = guidance.get('response_style', '')
            if tone:
                hints.append(f"當前語氣：{tone}")
            if style:
                hints.append(f"回應風格：{style}")
        
        if not hints:
            hints.append("保持自然、真誠的回應風格")
        
        return "\n".join(hints)
    
    def build_monologue_section(self, monologue_data: Dict) -> str:
        """建立內心獨白區塊"""
        thought = monologue_data.get('current_thought', '')
        mode = monologue_data.get('conversation_mode', 'BALANCED')
        
        if not thought:
            return f"（當前模式：{mode}，根據情境自動調整回應）"
        
        return f"""（內心獨白：{thought[:100]}...）"""
    
    # ========== 主要注入函式 ==========
    
    def inject_prompt(
        self,
        base_system_prompt: str,
        monologue_data: Dict,
        user_input: str = ""
    ) -> str:
        """
        動態 Prompt 注入主函式
        
        將社交規則、話術風格、內心獨白整合進 System Prompt
        
        Args:
            base_system_prompt: 原始 System Prompt
            monologue_data: 來自 internal_monologue 的資料
            user_input: 用戶輸入（可選）
        
        Returns:
            str: 注入後的完整 System Prompt
        """
        # 1. 社交行為準則
        social_context = self.build_social_context_section(monologue_data)
        
        # 2. 話術風格引導
        evolution_hint = self.build_evolution_hint_section(monologue_data)
        
        # 3. 內心獨白（可選，通常給開發者看）
        monologue_section = self.build_monologue_section(monologue_data)
        
        # 組合 injection block
        injection_block = f"""

### 當前社交行為準則 (DYNAMIC RULES) ###
{social_context}

### 話術風格引導 (EVOLUTION HINT) ###
{evolution_hint}

{monologue_section}

請根據上述社交準則，選擇最適合當前情境的回應方式。
"""
        
        # 插入到 base_prompt 的結尾（但在一些特殊標記之前）
        if "[INSTRUCTION]" in base_system_prompt:
            return base_system_prompt.replace("[INSTRUCTION]", injection_block.strip())
        else:
            return base_system_prompt.strip() + injection_block
    
    # ========== 快速注入捷徑 ==========
    
    def inject_for_response(
        self,
        base_prompt: str,
        user_input: str,
        emotion_score: float = 0.5,
        engagement_score: float = 0.5,
        context_summary: str = ""
    ) -> str:
        """
        快速回應注入
        
        適用於直接從對話中注入，不需要先跑完整的 internal_monologue
        
        Args:
            base_prompt: 原始 Prompt
            user_input: 用戶輸入
            emotion_score: 情緒分數
            engagement_score: 投入度分數
            context_summary: 上下文摘要
        
        Returns:
            str: 注入後的 Prompt
        """
        # 快速構建一個簡單的 monologue_data
        hour = datetime.datetime.now().hour
        work_hours = 9 <= hour <= 18
        
        # 簡單的規則觸發
        is_work = work_hours and any(
            kw in user_input.lower() 
            for kw in ['python', 'code', 'error', 'sql', '系統', '程式']
        )
        
        quick_monologue = {
            'conversation_mode': 'PROFESSIONAL' if is_work else 'INTIMATE',
            'current_emotion': 'focused' if is_work else 'affectionate',
            'user_intent': 'technical' if is_work else 'casual',
            'is_work_context': is_work,
            'user_emotion': 'neutral',
            'response_guidance': {
                'tone': '專業簡潔' if is_work else '溫柔撒嬌',
                'response_style': '先解決後安撫' if is_work else '先關心後陪伴'
            }
        }
        
        return self.inject_prompt(base_prompt, quick_monologue, user_input)


# ========== 與現有系統整合 ==========

def create_injection_engine(db_path: str = None) -> SocialInjectionEngine:
    """工廠函式：建立注入引擎"""
    return SocialInjectionEngine(db_path)


def quick_inject(base_prompt: str, user_input: str, **kwargs) -> str:
    """
    快速注入捷徑函式
    
    使用方式：
    enhanced_prompt = quick_inject(base_prompt, user_input)
    """
    engine = SocialInjectionEngine()
    return engine.inject_for_response(base_prompt, user_input, **kwargs)


# ========== 測試 ==========

if __name__ == "__main__":
    print("===== AuraNode 動態社交規則注入系統測試 =====\n")
    
    engine = SocialInjectionEngine()
    
    # 測試情境標籤提取
    print("【測試情境標籤提取】")
    test_monologue = {
        'conversation_mode': 'PROFESSIONAL',
        'current_emotion': 'focused',
        'user_intent': 'technical_help',
        'is_work_context': True,
        'user_emotion': 'frustrated',
        'current_thought': '主人正在處理技術問題，我應該專注在解決問題上'
    }
    
    tags = engine._determine_context_tags(test_monologue)
    print(f"  標籤：{tags}")
    
    # 測試社交規則檢索
    print("\n【測試社交規則檢索】")
    rules = engine.get_social_rules(test_monologue, limit=3)
    print(f"  找到 {len(rules)} 條規則")
    for r in rules:
        print(f"    - [{r['category']}] {r['rule_content'][:40]}...")
    
    # 測試 Prompt 注入
    print("\n【測試 Prompt 注入】")
    base_prompt = "你是 AuraNode，一個綠茶風格的 AI 祕書。"
    
    enhanced = engine.inject_prompt(base_prompt, test_monologue)
    print(f"  原始長度：{len(base_prompt)}")
    print(f"  注入後長度：{len(enhanced)}")
    print(f"  內容預覽：\n{enhanced[:300]}...")
    
    # 測試快速注入
    print("\n【測試快速注入】")
    user_input = "老闆，這個 Python 程式一直 error"
    quick_result = engine.inject_for_response(
        base_prompt, 
        user_input,
        emotion_score=0.6,
        engagement_score=0.7
    )
    print(f"  用戶輸入：{user_input}")
    print(f"  結果預覽：\n{quick_result[:300]}...")
    
    print("\n===== 測試完成 =====")
