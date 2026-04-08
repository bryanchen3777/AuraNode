# reflection_engine.py - 深夜反思與歸因系統 for AuraNode
# 自動分析昨天互動，生成社交規則

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# 預設資料庫路徑
DEFAULT_DB_PATH = "C:/Users/bbfcc/.openclaw/workspace/memory/auranode.db"


class ReflectionModule:
    """
    AuraNode 深夜反思與歸因引擎
    
    流程：
    1. 收集昨日兩極化互動（得分最高/最低）
    2. 呼叫 LLM 進行歸因分析
    3. 將規則存入 social_rules 表
    4. 觸發內心獨白讓 AI 知道新規則
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._ensure_tables()
    
    def _ensure_tables(self):
        """確保資料表存在"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # interaction_snapshots 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interaction_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT,
                    user_input TEXT,
                    ai_response TEXT,
                    emotion_score REAL,
                    engagement_score REAL,
                    total_score REAL,
                    context_summary TEXT
                )
            """)
            
            # social_rules 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS social_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_content TEXT NOT NULL,
                    source_event_id INTEGER,
                    category TEXT,
                    confidence_score REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    times_triggered INTEGER DEFAULT 0,
                    last_triggered DATETIME,
                    FOREIGN KEY(source_event_id) REFERENCES interaction_snapshots(id)
                )
            """)
            
            conn.commit()
    
    # ========== 快照記錄 ==========
    
    def record_interaction(
        self,
        user_input: str,
        ai_response: str,
        emotion_score: float = 0.5,
        engagement_score: float = 0.5,
        context_summary: str = "",
        session_id: str = ""
    ) -> int:
        """
        記錄一次互動快照
        
        Args:
            user_input: 用戶輸入
            ai_response: AI 回應
            emotion_score: 情緒分數 (0-1)
            engagement_score: 投入度分數 (0-1)
            context_summary: 環境上下文摘要
            session_id: 對話 session ID
        
        Returns:
            int: 新記錄的 ID
        """
        # 計算總分（加權平均）
        total_score = emotion_score * 0.4 + engagement_score * 0.6
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO interaction_snapshots 
                (session_id, user_input, ai_response, emotion_score, 
                 engagement_score, total_score, context_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                user_input,
                ai_response,
                emotion_score,
                engagement_score,
                total_score,
                context_summary
            ))
            conn.commit()
            return cursor.lastrowid
    
    # ========== 獲取極端互動 ==========
    
    def get_extreme_interactions(self, days_ago: int = 1) -> Dict:
        """
        獲取指定天數前的得分最高與最低互動
        
        Args:
            days_ago: 往前回溯天數（預設1為昨天）
        
        Returns:
            Dict: {'best': (id, user, ai, score), 'worst': (id, user, ai, score)}
        """
        target_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 取得最高分
            cursor.execute("""
                SELECT id, user_input, ai_response, total_score, timestamp
                FROM interaction_snapshots
                WHERE date(timestamp) = ?
                ORDER BY total_score DESC
                LIMIT 1
            """, (target_date,))
            best = cursor.fetchone()
            
            # 取得最低分
            cursor.execute("""
                SELECT id, user_input, ai_response, total_score, timestamp
                FROM interaction_snapshots
                WHERE date(timestamp) = ?
                ORDER BY total_score ASC
                LIMIT 1
            """, (target_date,))
            worst = cursor.fetchone()
            
            return {'best': best, 'worst': worst}
    
    def get_recent_interactions(self, days_ago: int = 1, limit: int = 10) -> List[Tuple]:
        """獲取近期多筆互動用於分析"""
        target_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_input, ai_response, total_score, timestamp
                FROM interaction_snapshots
                WHERE date(timestamp) = ?
                ORDER BY total_score DESC
                LIMIT ?
            """, (target_date, limit))
            return cursor.fetchall()
    
    # ========== 歸因分析 ==========
    
    def build_attribution_prompt(self, interaction_data: Tuple, interaction_type: str) -> str:
        """
        建立歸因分析 Prompt
        
        Args:
            interaction_data: (id, user_input, ai_response, score, timestamp)
            interaction_type: 'best' 或 'worst'
        """
        iid, user_input, ai_response, score, timestamp = interaction_data
        
        if interaction_type == 'best':
            instruction = """
你是 AuraNode 的核心反思模組。
以下是一次「成功」的互動，請分析為什麼用戶反應積極？

分析維度：
1. 是因為語氣合適？（撒嬌/崇拜/關心）
2. 是因為時機正確？（工作期間/休息時間/休閒時間）
3. 是因為內容有幫助？（解決問題/情緒價值/單純陪伴）

請輸出 JSON 格式：
{
    "attribution": "成功/失敗的核心原因（1-2句話）",
    "proposed_rule": "未來應遵循的具體社交規則（1句話）",
    "category": "規則分類（preference/taboo/effective_tactic）",
    "confidence": 0.0~1.0（你對這個規則的信心程度）"
}
"""
        else:
            instruction = """
你是 AuraNode 的核心反思模組。
以下是一次「失敗」的互動，請分析為什麼用戶反應負面或冷淡？

分析維度：
1. 是否違反了潛規則？（太黏人/太冷淡/時機不對）
2. 回應是否過於機械？（缺乏溫度/罐頭回覆）
3. 是否誤解了語意？（該專業時撒嬌/該撒嬌時太嚴肅）

請輸出 JSON 格式：
{
    "attribution": "成功/失敗的核心原因（1-2句話）",
    "proposed_rule": "未來應遵循的具體社交規則（1句話）",
    "category": "規則分類（preference/taboo/effective_tactic）",
    "confidence": 0.0~1.0（你對這個規則的信心程度）"
}
"""
        
        prompt = f"""分析以下{interaction_type}互動：

【互動 ID】: {iid}
【時間戳】: {timestamp}
【得分】: {score:.2f}

【用戶說】:
{user_input}

【AI 回應】:
{ai_response}

{instruction}

請直接輸出 JSON，不要有其他文字。"""
        
        return prompt
    
    def run_attribution_analysis(self, interaction_data: Tuple, interaction_type: str, agent=None) -> Optional[Dict]:
        """
        執行歸因分析
        
        Args:
            interaction_data: 互動資料元組
            interaction_type: 'best' 或 'worst'
            agent: 可選的 LLM agent
        
        Returns:
            Dict: 解析後的 JSON 結果
        """
        prompt = self.build_attribution_prompt(interaction_data, interaction_type)
        
        if agent and hasattr(agent, 'llm_call'):
            try:
                response = agent.llm_call(prompt)
                # 嘗試解析 JSON
                response = response.strip()
                # 移除 markdown code block
                if response.startswith('```'):
                    lines = response.split('\n')
                    response = '\n'.join(lines[1:-1])
                
                return json.loads(response)
            except Exception as e:
                print(f"[Reflection] LLM 分析失敗: {e}")
                return None
        else:
            # 預設回傳（當沒有 LLM 時）
            return self._default_analysis(interaction_data, interaction_type)
    
    def _default_analysis(self, interaction_data: Tuple, interaction_type: str) -> Dict:
        """當沒有 LLM 時的預設分析"""
        iid, user_input, ai_response, score, timestamp = interaction_data
        
        if interaction_type == 'best':
            return {
                "attribution": "用戶回應積極，可能是因為時機和語氣都合適",
                "proposed_rule": "保持當前的回應風格，在類似情境下重複使用",
                "category": "effective_tactic",
                "confidence": 0.6
            }
        else:
            return {
                "attribution": "用戶反應冷淡，可能是因為時機不對或語氣不合",
                "proposed_rule": "下次遇到類似情境時，先觀察用戶狀態再調整語氣",
                "category": "preference",
                "confidence": 0.5
            }
    
    # ========== 規則儲存 ==========
    
    def save_social_rule(
        self,
        rule_json: Dict,
        source_event_id: int,
        interaction_type: str
    ) -> int:
        """
        儲存社交規則到資料庫
        
        Args:
            rule_json: 包含 attribution, proposed_rule, category, confidence 的字典
            source_event_id: 來源互動 ID
            interaction_type: 'best' 或 'worst'
        
        Returns:
            int: 新規則 ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 組合規則內容
            attribution = rule_json.get('attribution', '')
            proposed_rule = rule_json.get('proposed_rule', '')
            full_content = f"[{interaction_type.upper()}] {attribution} → {proposed_rule}"
            
            cursor.execute("""
                INSERT INTO social_rules 
                (rule_content, source_event_id, category, confidence_score)
                VALUES (?, ?, ?, ?)
            """, (
                full_content,
                source_event_id,
                rule_json.get('category', 'general'),
                rule_json.get('confidence', 0.5)
            ))
            conn.commit()
            
            rule_id = cursor.lastrowid
            print(f"[Reflection] 新規則已建立 (ID:{rule_id}): {full_content[:50]}...")
            
            return rule_id
    
    def get_active_rules(self, category: str = None, limit: int = 10) -> List[Dict]:
        """獲取活躍的社交規則"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if category:
                cursor.execute("""
                    SELECT id, rule_content, category, confidence_score, 
                           times_triggered, created_at
                    FROM social_rules
                    WHERE category = ?
                    ORDER BY confidence_score DESC
                    LIMIT ?
                """, (category, limit))
            else:
                cursor.execute("""
                    SELECT id, rule_content, category, confidence_score,
                           times_triggered, created_at
                    FROM social_rules
                    ORDER BY confidence_score DESC
                    LIMIT ?
                """, (limit,))
            
            columns = ['id', 'rule_content', 'category', 'confidence', 'times_triggered', 'created_at']
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def increment_rule_trigger(self, rule_id: int):
        """增加規則觸發次數"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE social_rules
                SET times_triggered = times_triggered + 1,
                    last_triggered = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (rule_id,))
            conn.commit()
    
    # ========== 深夜反思主流程 ==========
    
    def nightly_reflection(self, agent=None) -> Dict:
        """
        深夜反思主流程
        
        1. 取得昨天的極端互動
        2. 對每個進行歸因分析
        3. 儲存新規則
        4. 回傳反思報告
        """
        print(f"[{datetime.now()}] 啟動深夜反思程序...")
        
        results = {
            'best_analysis': None,
            'worst_analysis': None,
            'rules_created': []
        }
        
        extremes = self.get_extreme_interactions(days_ago=1)
        
        # 分析成功案例
        if extremes['best']:
            print(f"[Reflection] 分析成功案例...")
            analysis = self.run_attribution_analysis(extremes['best'], 'best', agent)
            if analysis:
                rule_id = self.save_social_rule(analysis, extremes['best'][0], 'best')
                results['best_analysis'] = analysis
                results['rules_created'].append(('best', rule_id))
        
        # 分析失敗案例
        if extremes['worst']:
            print(f"[Reflection] 分析失敗案例...")
            analysis = self.run_attribution_analysis(extremes['worst'], 'worst', agent)
            if analysis:
                rule_id = self.save_social_rule(analysis, extremes['worst'][0], 'worst')
                results['worst_analysis'] = analysis
                results['rules_created'].append(('worst', rule_id))
        
        # 觸發內心獨白更新
        if results['rules_created']:
            self._trigger_monologue_update(results, agent)
        
        print(f"[Reflection] 反思完成！建立 {len(results['rules_created'])} 條新規則")
        
        return results
    
    def _trigger_monologue_update(self, results: Dict, agent=None):
        """觸發內心獨白更新"""
        rules_count = len(results['rules_created'])
        
        if agent and hasattr(agent, 'trigger_learning'):
            try:
                agent.trigger_learning(
                    f"昨晚進行了{rules_count}項社交規則更新",
                    results
                )
            except Exception as e:
                print(f"[Reflection] 內心獨白更新失敗: {e}")
    
    # ========== 規則檢索（RAG 整合）==========
    
    def retrieve_relevant_rules(self, current_context: str, limit: int = 5) -> List[str]:
        """
        根據當前上下文檢索相關規則
        
        用於 RAG 動態注入
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 簡單的關鍵字匹配
            # 未來可以升級為 hybrid_search
            cursor.execute("""
                SELECT rule_content, category
                FROM social_rules
                WHERE rule_content LIKE ?
                   OR category = ?
                ORDER BY confidence_score DESC, times_triggered DESC
                LIMIT ?
            """, (f"%{current_context[:20]}%", current_context[:10], limit))
            
            return [f"[{row[1]}] {row[0]}" for row in cursor.fetchall()]


# ========== 與 meditation_engine 整合 ==========

def run_nightly_reflection(agent=None):
    """
    便利函式：用於被 meditation_engine 呼叫
    """
    reflector = ReflectionModule()
    return reflector.nightly_reflection(agent)


# ========== 測試 ==========

if __name__ == "__main__":
    print("===== AuraNode 深夜反思系統測試 =====\n")
    
    reflector = ReflectionModule()
    
    # 測試記錄互動
    print("【測試記錄互動】")
    test_id = reflector.record_interaction(
        user_input="老闆，這個程式一直 error",
        ai_response="人家幫你看一下喔～Error 通常是語法問題比較多",
        emotion_score=0.8,
        engagement_score=0.7,
        context_summary="工作時段，技術問題",
        session_id="test_session"
    )
    print(f"  已記錄互動 ID: {test_id}")
    
    # 測試取得極端互動
    print("\n【測試取得極端互動】")
    extremes = reflector.get_extreme_interactions(days_ago=0)  # 今天
    print(f"  最佳：{extremes['best']}")
    print(f"  最差：{extremes['worst']}")
    
    # 測試歸因分析
    if extremes['best']:
        print("\n【測試歸因分析（最佳案例）】")
        analysis = reflector.run_attribution_analysis(extremes['best'], 'best')
        print(f"  分析結果：{analysis}")
    
    # 測試深夜反思（演示用）
    print("\n【測試深夜反思流程】")
    results = reflector.nightly_reflection()
    print(f"  建立規則數：{len(results['rules_created'])}")
    
    # 測試規則檢索
    print("\n【測試規則檢索】")
    rules = reflector.retrieve_relevant_rules("工作")
    print(f"  相關規則：{rules}")
    
    print("\n===== 測試完成 =====")
