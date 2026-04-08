# rag_engine.py - RAG Optimization for Yua
# 檢索增強生成：優化 memory_engine 與 Prompt 的結合

import json
import sys
import os

# 將 scripts 加入路徑以便匯入現有系統
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ========== 1. RAG Prompt Template ==========

RAG_PROMPT_TPL = """你是一個具備長期記憶能力的 AI 助理。請根據以下提供的【背景記憶】來回答用戶的【當前任務】。

<background_memories>
{context_text}
</background_memories>

<current_task>
{user_query}
</current_task>

指令：
1. 如果背景記憶中有相關資訊，請優先參考並在回答中體現。
2. 如果記憶中無相關資訊，請根據自身知識回答，但不要虛構記憶。
3. 保持回答簡潔且符合任務需求。
4. 如果涉及到用戶偏好或已知習慣，請在回答中體現出來。
"""


# ========== 2. 動態上下文注入函式 ==========

def build_dynamic_context(query: str, memory_engine, search_limit=3, recent_limit=2, min_importance=0):
    """
    從 memory_engine 提取並格式化上下文
    
    結合 FTS5 全文搜尋（相關性）與近期記憶（時效性）
    
    Args:
        query: 用戶查詢
        memory_engine: memory_engine.py 的實例
        search_limit: FTS5 搜尋返回數量
        recent_limit: 近期記憶返回數量
        min_importance: 最低重要度閾值（0為不限制）
    
    Returns:
        str: 格式化的上下文文字
    """
    combined_memories = []
    seen_content = set()
    
    try:
        # 1. 執行 FTS5 全文搜尋獲取相關記憶
        search_results = memory_engine.search_memory(query)
        # 限制數量
        if search_limit:
            search_results = search_results[:search_limit]
        
        # 2. 獲取最近的記憶（增加對話連貫性）
        recent_results = memory_engine.get_recent_memories(limit=recent_limit)
        
        # 3. 去重並合併
        for m in search_results + recent_results:
            # 處理 tuple 格式 (id, timestamp, content, category, importance)
            if isinstance(m, tuple):
                if len(m) >= 5:
                    importance = m[4] or 0
                    content = m[2] or ''
                    category = m[3] or '一般'
                else:
                    continue
            else:
                importance = m.get('importance', 0)
                content = m.get('content', '')
                category = m.get('category', '一般')
            
            # 檢查重要度閾值
            if importance < min_importance:
                continue
                
            if content and content not in seen_content:
                # 格式化每條記憶
                mem_str = f"[{category}] (重要度: {importance}): {content}"
                combined_memories.append(mem_str)
                seen_content.add(content)
                
    except Exception as e:
        print(f"[RAG Engine] 記憶檢索失敗: {e}")
        return "記憶檢索失敗，使用基本模式。"
    
    if not combined_memories:
        return "目前無相關背景記憶。"
    
    return "\n".join(combined_memories)


def build_rag_prompt(query: str, memory_engine, search_limit=3, recent_limit=2, min_importance=0):
    """
    建立完整的 RAG Prompt
    
    Args:
        query: 用戶查詢
        memory_engine: memory_engine.py 的實例
        search_limit: FTS5 搜尋返回數量
        recent_limit: 近期記憶返回數量
        min_importance: 最低重要度閾值
    
    Returns:
        str: 完整的 RAG Prompt
    """
    context = build_dynamic_context(
        query, 
        memory_engine, 
        search_limit=search_limit,
        recent_limit=recent_limit,
        min_importance=min_importance
    )
    
    return RAG_PROMPT_TPL.format(
        context_text=context,
        user_query=query
    )


# ========== 3. Query 重寫（Pro Tip）============

def rewrite_query_for_fts(query: str, agent=None):
    """
    將用戶模糊的提問轉化為適合 FTS5 的關鍵字
    
    Args:
        query: 用戶原始查詢
        agent: 可選，LLM agent 實例用於複雜查詢重寫
    
    Returns:
        str: 重寫後的查詢
    """
    # 簡單的清理
    query = query.strip()
    
    # 如果有 agent，可以用 LLM 來重寫
    if agent and hasattr(agent, 'llm_call'):
        prompt = f"""將以下用戶查詢轉化為適合 SQLite FTS5 全文搜尋的關鍵字組合。

原始查詢：{query}

要求：
- 提取核心關鍵字
- 移除語氣詞（如「幫我」、「可以」等）
- 保留重要實體（人名、專案名、技術術語）
- 用空格分隔關鍵字

只回傳關鍵字，不要其他文字。"""
        try:
            rewritten = agent.llm_call(prompt).strip()
            return rewritten
        except Exception as e:
            print(f"[RAG] Query 重寫失敗: {e}")
    
    # 預設：簡單清理
    import re
    # 移除常見語氣詞
    stopwords = ['幫我', '請問', '可以', '能不能', '如何', '怎麼', '什麼', '為什麼']
    for sw in stopwords:
        query = query.replace(sw, '')
    
    # 移除多餘空白
    query = re.sub(r'\s+', ' ', query).strip()
    
    return query


# ========== 4. RAG Planner - 與 Planning Engine 整合 ==========

class RAGPlanner:
    """
    RAG + Planning 整合器
    
    在 ReAct 循環中，RAG 在 Reasoning (思考) 階段之前執行
    """
    
    def __init__(self, planning_engine, memory_engine):
        self.planner = planning_engine
        self.memory = memory_engine
        
    def execute_task(self, user_input, use_rag=True, context_config=None):
        """
        執行任務（可選是否使用 RAG）
        
        Args:
            user_input: 用戶輸入
            use_rag: 是否使用 RAG 檢索
            context_config: dict，設定 search_limit, recent_limit, min_importance
        
        Returns:
            dict: 任務執行結果
        """
        if context_config is None:
            context_config = {}
        
        if use_rag:
            # Step A: 檢索記憶
            context = build_dynamic_context(
                user_input, 
                self.memory,
                search_limit=context_config.get('search_limit', 3),
                recent_limit=context_config.get('recent_limit', 2),
                min_importance=context_config.get('min_importance', 0)
            )
            
            # Step B: 組合最終 Prompt
            final_prompt = RAG_PROMPT_TPL.format(
                context_text=context,
                user_query=user_input
            )
            
            print(f"[RAG Planner] 注入上下文：{context[:100]}...")
            
            # Step C: 交給 ReAct 引擎
            result = self.planner.execute_task(final_prompt, context={'rag_used': True})
        else:
            # 不使用 RAG，直接執行
            result = self.planner.execute_task(user_input, context={'rag_used': False})
            
        return result
    
    def query_memory(self, query, limit=5):
        """
        純查詢記憶，不執行任務
        
        Args:
            query: 查詢關鍵字
            limit: 返回數量
        
        Returns:
            list: 記憶清單
        """
        results = self.memory.search_memory(query)
        if limit:
            results = results[:limit]
        return results


# ========== 5. OpenClaw 整合工具 ==========

class YuaRAGExtension:
    """
    OpenClaw 框架的 RAG 擴展
    
    可作為 BaseExtension 或 Processor 整合進 OpenClaw
    確保每次對話都能自動觸發記憶檢索
    """
    
    def __init__(self, memory_engine):
        self.memory = memory_engine
        self.enabled = True
        self.search_limit = 3
        self.recent_limit = 2
        self.min_importance = 0
        
    def process_message(self, message: str, agent=None) -> str:
        """
        處理消息並注入 RAG 上下文
        
        這個函式可以在 OpenClaw 的 message processor 中調用
        """
        if not self.enabled:
            return message
            
        try:
            # 檢查是否需要 RAG（可以根據關鍵字判斷）
            if self._should_use_rag(message):
                context = build_dynamic_context(
                    message,
                    self.memory,
                    search_limit=self.search_limit,
                    recent_limit=self.recent_limit,
                    min_importance=self.min_importance
                )
                
                # 如果有相關記憶，注入到消息中
                if context and "無相關" not in context:
                    enhanced_message = f"""{message}

【背景脈絡】（以下為 Yua 的相關記憶，請參考：
{context}
）"""
                    return enhanced_message
        except Exception as e:
            print(f"[YuaRAGExtension] 處理失敗: {e}")
            
        return message
    
    def _should_use_rag(self, message: str) -> bool:
        """
        判斷是否需要使用 RAG
        
        可以根據消息內容、關鍵字或時間等因素判斷
        """
        # 簡單策略：如果消息超過一定長度或包含特定關鍵字
        if len(message) < 5:
            return False
            
        # 特定觸發關鍵字
        trigger_words = ['記得', '之前', '上次', '曾經', '專案', '計畫', '任務', '專門']
        for word in trigger_words:
            if word in message:
                return True
                
        return True  # 預設啟用
    
    def get_relevant_context(self, query: str) -> str:
        """取得相關上下文"""
        return build_dynamic_context(
            query,
            self.memory,
            search_limit=self.search_limit,
            recent_limit=self.recent_limit,
            min_importance=self.min_importance
        )


# ========== 6. 測試區 ==========

if __name__ == "__main__":
    print("===== Yua RAG Engine 測試 =====\n")
    
    # 測試需要 memory_engine
    try:
        from memory_engine import YuaMemoryDB
        memory = YuaMemoryDB()
        
        # 加入一些測試記憶
        print("【加入測試記憶】")
        memory.add_memory("專案 A 使用 Python 3.10 並部署於 AWS", "技術規格", 5)
        memory.add_memory("老闆喜歡簡潔的回答", "用戶偏好", 4)
        memory.add_memory("每天早上要提醒老闆喝水", "習慣", 3)
        print("測試記憶已加入\n")
        
        # 測試 RAG Prompt 建立
        print("【測試 RAG Prompt】")
        prompt = build_rag_prompt("幫我規劃專案 A 的部署", memory)
        print(prompt[:500])
        print("...\n")
        
        # 測試上下文建立
        print("【測試上下文提取】")
        context = build_dynamic_context("老闆喜歡什麼風格", memory)
        print(context)
        
        # 測試 Query 重寫
        print("\n【測試 Query 重寫】")
        rewritten = rewrite_query_for_fts("幫我想想上次那個專案的情況")
        print(f"原始：幫我想想上次那個專案的情況")
        print(f"重寫：{rewritten}")
        
        # 測試 RAG Extension
        print("\n【測試 YuaRAGExtension】")
        rag_ext = YuaRAGExtension(memory)
        enhanced = rag_ext.process_message("幫我看看老闆的習慣")
        print(f"增強後：{enhanced[:200]}...")
        
    except ImportError as e:
        print(f"需要先有 memory_engine.py: {e}")
        print("\n【獨立測試】")
        
        # 獨立測試（不需要 memory_engine）
        print("測試 Prompt Template:")
        print(RAG_PROMPT_TPL.format(
            context_text="[測試] (重要度: 5): 這是一條測試記憶",
            user_query="測試查詢"
        ))
