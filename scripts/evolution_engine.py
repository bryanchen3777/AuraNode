# evolution_engine.py - 話術基因突變與演化系統 for AuraNode
# 將遺傳演算法概念應用於自然語言處理

import sqlite3
import json
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import Counter

# 預設資料庫路徑
DEFAULT_DB_PATH = "C:/Users/bbfcc/.openclaw/workspace/memory/auranode.db"


# ========== 話術維度常數 ==========

TONE_TYPES = {
    'PROFESSIONAL': '專業權威',
    'EMPATHIC': '親切感性',
    'SCARCITY': '急迫稀缺',
    'BENEFIT': '利益導向',
    'CURIOSITY': '好奇驅動'
}

# 話術階段
STAGE_EXPLORE = 'EXPLORE'
STAGE_MATURE = 'MATURE'
STAGE_ARCHIVED = 'ARCHIVED'

# 閾值設定
MIN_EXPLORE_USAGE = 5       # 探索期最少測試次數
SUCCESS_THRESHOLD = 0.6      # 晉升閾值
FAILURE_THRESHOLD = 0.3     # 淘汰閾值


class EvolutionEngine:
    """
    AuraNode 話術基因突變與演化引擎
    
    採用「精英保留策略」：
    1. 當話術成功率超過閾值時，觸發突變
    2. 生成 5 種不同維度的變體
    3. 進入探索區進行 A/B 測試
    4. 根據成功率決定晉升或淘汰
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._ensure_tables()
    
    def _ensure_tables(self):
        """確保資料表存在"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # script_genes 表（話術基因庫）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS script_genes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_id INTEGER,
                    content TEXT NOT NULL,
                    stage TEXT DEFAULT 'EXPLORE',
                    tone_type TEXT,
                    usage_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    score FLOAT DEFAULT 0.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_used DATETIME,
                    evolution_depth INTEGER DEFAULT 0
                )
            """)
            
            # evolution_log 表（演化日誌）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evolution_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_script_id INTEGER,
                    child_script_id INTEGER,
                    mutation_type TEXT,
                    reason TEXT,
                    result_stage TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    # ========== 話術記錄 ==========
    
    def register_script(self, content: str, tone_type: str = None, 
                      parent_id: int = None, evolution_depth: int = 0) -> int:
        """
        註冊新話術到基因庫
        
        Args:
            content: 話術內容
            tone_type: 變異維度
            parent_id: 母體話術 ID
            evolution_depth: 演化深度
        
        Returns:
            int: 新話術 ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO script_genes 
                (content, tone_type, parent_id, stage, evolution_depth)
                VALUES (?, ?, ?, ?, ?)
            """, (content, tone_type, parent_id, STAGE_EXPLORE, evolution_depth))
            conn.commit()
            
            script_id = cursor.lastrowid
            print(f"[Evolution] 新話術已註冊 (ID:{script_id}): {content[:30]}...")
            
            return script_id
    
    def record_usage(self, script_id: int, is_success: bool):
        """
        記錄話術使用結果
        
        Args:
            script_id: 話術 ID
            is_success: 是否成功
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 更新使用次數
            cursor.execute("""
                UPDATE script_genes
                SET usage_count = usage_count + 1,
                    success_count = success_count + ?,
                    score = CASE 
                        WHEN usage_count + 1 > 0 
                        THEN (success_count + ?) / (usage_count + 1)
                        ELSE 0
                    END,
                    last_used = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (1 if is_success else 0, 1 if is_success else 0, script_id))
            
            conn.commit()
            
            # 檢查是否需要評估
            self._evaluate_and_evolve(script_id)
    
    def _evaluate_and_evolve(self, script_id: int):
        """評估話術並決定演化方向"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, content, usage_count, score, stage, tone_type
                FROM script_genes
                WHERE id = ?
            """, (script_id,))
            
            result = cursor.fetchone()
            if not result:
                return
            
            sid, content, usage, score, stage, tone_type = result
            
            # 只有 EXPLORE 階段的才評估
            if stage != STAGE_EXPLORE:
                return
            
            # 如果使用次數還沒達到最低標準，不評估
            if usage < MIN_EXPLORE_USAGE:
                return
            
            # 評估結果
            if score >= SUCCESS_THRESHOLD:
                # 晉升為 MATURE
                cursor.execute("""
                    UPDATE script_genes
                    SET stage = ?
                    WHERE id = ?
                """, (STAGE_MATURE, script_id))
                
                self._log_evolution(script_id, None, 'PROMOTION', 
                                   f'Score {score:.2f} >= {SUCCESS_THRESHOLD}', STAGE_MATURE)
                
                print(f"[Evolution] 話術 {script_id} 晉升為 MATURE (score={score:.2f})")
                
            elif score < FAILURE_THRESHOLD:
                # 淘汰
                cursor.execute("""
                    UPDATE script_genes
                    SET stage = ?
                    WHERE id = ?
                """, (STAGE_ARCHIVED, script_id))
                
                self._log_evolution(script_id, None, 'ARCHIVED',
                                   f'Score {score:.2f} < {FAILURE_THRESHOLD}', STAGE_ARCHIVED)
                
                print(f"[Evolution] 話術 {script_id} 已淘汰 (score={score:.2f})")
    
    def _log_evolution(self, parent_id: int, child_id: int, 
                      mutation_type: str, reason: str, result_stage: str):
        """記錄演化日誌"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO evolution_log
                (parent_script_id, child_script_id, mutation_type, reason, result_stage)
                VALUES (?, ?, ?, ?, ?)
            """, (parent_id, child_id, mutation_type, reason, result_stage))
            conn.commit()
    
    # ========== 突變生成 ==========
    
    def build_mutation_prompt(self, original_script: str, 
                            target_context: str = "") -> str:
        """
        建立突變 Prompt
        
        Args:
            original_script: 原始話術
            target_context: 目標上下文描述
        """
        tone_axes = "\n".join([
            f"- {tone}: {desc}" 
            for tone, desc in TONE_TYPES.items()
        ])
        
        prompt = f"""你是 AuraNode 的話術演化引擎。

【原始話術】
{original_script}

【目標情境】
{target_context or "一般對話情境"}

【演化任務】
請保留原始話術的核心意圖，但針對以下 5 種維度進行「基因突變」，生成 5 個變體：

{tone_axes}

【輸出格式】
請輸出 JSON 陣列，每個元素包含：
- "tone_type": 維度名稱
- "content": 突變後的話術內容
- "rationale": 突變理由（1句話）

直接輸出 JSON，不要有其他文字。"""
        
        return prompt
    
    def generate_mutations(self, original_script: str, 
                         target_context: str = "",
                         agent=None) -> List[Dict]:
        """
        生成話術突變體
        
        Args:
            original_script: 原始話術
            target_context: 目標上下文
            agent: 可選的 LLM agent
        
        Returns:
            List[Dict]: 突變體清單
        """
        prompt = self.build_mutation_prompt(original_script, target_context)
        
        if agent and hasattr(agent, 'llm_call'):
            try:
                response = agent.llm_call(prompt)
                response = response.strip()
                
                # 移除 markdown code block
                if response.startswith('```'):
                    lines = response.split('\n')
                    response = '\n'.join(lines[1:-1])
                
                mutations = json.loads(response)
                return mutations
                
            except Exception as e:
                print(f"[Evolution] LLM 突變生成失敗: {e}")
                return self._default_mutations(original_script)
        else:
            return self._default_mutations(original_script)
    
    def _default_mutations(self, original_script: str) -> List[Dict]:
        """當沒有 LLM 時的預設突變"""
        mutations = []
        
        # 簡單的字尾/前綴變化
        variations = [
            (TONE_TYPES['PROFESSIONAL'], f"{original_script}（這是專業建議）"),
            (TONE_TYPES['EMPATHIC'], f"人家覺得... {original_script}"),
            (TONE_TYPES['SCARCITY'], f"快試試看！{original_script}"),
            (TONE_TYPES['BENEFIT'], f"這樣做會更好：{original_script}"),
            (TONE_TYPES['CURIOSITY'], f"你知道嗎？{original_script}")
        ]
        
        for tone_type, content in variations:
            mutations.append({
                'tone_type': tone_type,
                'content': content,
                'rationale': '預設變異'
            })
        
        return mutations
    
    # ========== 精英選擇 ==========
    
    def select_elite_scripts(self, min_score: float = 0.5, 
                           min_usage: int = 3) -> List[Tuple]:
        """
        選擇精英話術（用於觸發突變）
        
        Returns:
            List[Tuple]: (id, content, score, usage_count)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, content, score, usage_count, evolution_depth
                FROM script_genes
                WHERE stage = ?
                  AND score >= ?
                  AND usage_count >= ?
                  AND evolution_depth < 5
                ORDER BY score DESC
                LIMIT 10
            """, (STAGE_MATURE, min_score, min_usage))
            
            return cursor.fetchall()
    
    def trigger_evolution(self, agent=None) -> Dict:
        """
        觸發話術演化主流程
        
        1. 選擇精英話術
        2. 生成突變體
        3. 註冊並開始探索
        """
        print(f"[{datetime.now()}] 啟動話術演化程序...")
        
        results = {
            'elites_selected': 0,
            'mutations_generated': 0,
            'new_scripts': []
        }
        
        # 選擇精英
        elites = self.select_elite_scripts()
        results['elites_selected'] = len(elites)
        
        for elite in elites:
            eid, content, score, usage, depth = elite
            
            # 生成突變
            mutations = self.generate_mutations(content, agent=agent)
            
            for mut in mutations:
                tone_type = mut.get('tone_type', 'UNKNOWN')
                new_content = mut.get('content', '')
                
                if new_content:
                    # 註冊新話術
                    new_id = self.register_script(
                        content=new_content,
                        tone_type=tone_type,
                        parent_id=eid,
                        evolution_depth=depth + 1
                    )
                    
                    results['mutations_generated'] += 1
                    results['new_scripts'].append(new_id)
                    
                    # 記錄演化日誌
                    self._log_evolution(eid, new_id, 'MUTATION',
                                       mut.get('rationale', ''), STAGE_EXPLORE)
        
        print(f"[Evolution] 演化完成！")
        print(f"  精英選擇：{results['elites_selected']}")
        print(f"  突變生成：{results['mutations_generated']}")
        
        return results
    
    # ========== 話術選擇（給回應時呼叫）==========
    
    def select_script_for_context(self, context_hint: str = "") -> Optional[Dict]:
        """
        根據上下文選擇合適的話術
        
        Args:
            context_hint: 上下文提示（可用的關鍵字）
        
        Returns:
            Dict: 選擇的話術資料
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 優先從 MATURE 區選擇
            cursor.execute("""
                SELECT id, content, tone_type, score, usage_count
                FROM script_genes
                WHERE stage = ?
                ORDER BY score DESC, usage_count DESC
                LIMIT 20
            """, (STAGE_MATURE,))
            
            mature_scripts = cursor.fetchall()
            
            if mature_scripts:
                # 簡單的 Thompson Sampling 近似
                weights = [max(0.1, s[3]) * (1 + s[4]/100) for s in mature_scripts]
                total_weight = sum(weights)
                weights = [w/total_weight for w in weights]
                
                selected = random.choices(mature_scripts, weights=weights, k=1)[0]
                
                return {
                    'id': selected[0],
                    'content': selected[1],
                    'tone_type': selected[2],
                    'score': selected[3],
                    'source': 'MATURE'
                }
            
            # 如果 MATURE 沒有，嘗試 EXPLORE（探索新話術）
            cursor.execute("""
                SELECT id, content, tone_type, score, usage_count
                FROM script_genes
                WHERE stage = ?
                ORDER BY RANDOM()
                LIMIT 5
            """, (STAGE_EXPLORE,))
            
            explore_scripts = cursor.fetchall()
            
            if explore_scripts:
                selected = random.choice(explore_scripts)
                return {
                    'id': selected[0],
                    'content': selected[1],
                    'tone_type': selected[2],
                    'score': selected[3],
                    'source': 'EXPLORE'
                }
            
            return None
    
    # ========== 統計與報表 ==========
    
    def get_statistics(self) -> Dict:
        """取得演化統計"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            for stage in [STAGE_EXPLORE, STAGE_MATURE, STAGE_ARCHIVED]:
                cursor.execute("""
                    SELECT COUNT(*), AVG(score), SUM(usage_count)
                    FROM script_genes
                    WHERE stage = ?
                """, (stage,))
                
                result = cursor.fetchone()
                stats[stage] = {
                    'count': result[0] or 0,
                    'avg_score': result[1] or 0,
                    'total_usage': result[2] or 0
                }
            
            # 演化代際統計
            cursor.execute("""
                SELECT MAX(evolution_depth) as max_depth
                FROM script_genes
            """)
            stats['max_evolution_depth'] = cursor.fetchone()[0] or 0
            
            return stats
    
    def get_top_performers(self, limit: int = 10) -> List[Dict]:
        """取得表現最好的話術"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, content, tone_type, score, usage_count, stage
                FROM script_genes
                WHERE usage_count >= 3
                ORDER BY score DESC
                LIMIT ?
            """, (limit,))
            
            columns = ['id', 'content', 'tone_type', 'score', 'usage_count', 'stage']
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


# ========== 便利函式 ==========

def register_and_use(script_content: str, context: str = "",
                    agent=None, is_success: bool = None) -> Optional[Dict]:
    """
    便利函式：註冊話術並有機會使用
    
    如果提供 is_success，會記錄使用結果
    """
    engine = EvolutionEngine()
    
    # 註冊
    script_id = engine.register_script(script_content)
    
    # 記錄使用
    if is_success is not None:
        engine.record_usage(script_id, is_success)
    
    return {'id': script_id, 'content': script_content}


# ========== 測試 ==========

if __name__ == "__main__":
    print("===== AuraNode 話術演化系統測試 =====\n")
    
    engine = EvolutionEngine()
    
    # 測試註冊話術
    print("【測試註冊話術】")
    test_scripts = [
        ("老闆辛苦了，喝杯水休息一下吧～", "EMPATHIC"),
        ("這個問題人家幫你看一下喔", "BENEFIT"),
    ]
    
    for content, tone in test_scripts:
        sid = engine.register_script(content, tone)
        print(f"  已註冊 ID:{sid}: {content[:30]}...")
    
    # 測試記錄使用
    print("\n【測試記錄使用】")
    engine.record_usage(1, is_success=True)
    engine.record_usage(1, is_success=False)
    engine.record_usage(2, is_success=True)
    
    # 測試選擇話術
    print("\n【測試選擇話術】")
    selected = engine.select_script_for_context()
    if selected:
        print(f"  選擇：{selected['content'][:30]}... (from {selected['source']})")
    
    # 測試突變生成
    print("\n【測試突變生成】")
    mutations = engine.generate_mutations("老闆辛苦了")
    print(f"  生成 {len(mutations)} 個突變體：")
    for m in mutations:
        print(f"    [{m.get('tone_type', 'N/A')}] {m.get('content', '')[:30]}...")
    
    # 測試統計
    print("\n【測試統計】")
    stats = engine.get_statistics()
    print(f"  EXPLORE: {stats['EXPLORE']['count']} 個")
    print(f"  MATURE: {stats['MATURE']['count']} 個")
    print(f"  ARCHIVED: {stats['ARCHIVED']['count']} 個")
    
    print("\n===== 測試完成 =====")
