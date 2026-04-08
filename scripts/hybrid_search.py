# hybrid_search.py - Hybrid Search for Yua
# 混合搜尋：結合 FTS5（關鍵字）與語意相似度

import sqlite3
import re
from typing import List, Dict, Tuple, Optional
from collections import Counter

# sentence_transformers is optional
HAS_SENTENCE_TRANSFORMERS = False
SentenceTransformer = None


# ========== 常數 ==========

RRF_K = 60  # RRF 常數


class HybridMemoryEngine:
    """
    Yua 的混合搜尋引擎
    
    結合：
    1. SQLite FTS5（關鍵字匹配）
    2. 語意相似度（基於簡單文字相似度）
    
    使用 Reciprocal Rank Fusion (RRF) 合併結果
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = "C:/Users/bbfcc/.openclaw/workspace/memory/yua_memory.db"
        
        self.db_path = db_path
        self.model = None
        self.use_semantic = False
        
        # 嘗試載入語意模型
        if HAS_SENTENCE_TRANSFORMERS:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                self.use_semantic = True
                print(f"[Hybrid Search] Semantic model loaded: all-MiniLM-L6-v2")
            except Exception as e:
                print(f"[Hybrid Search] Cannot load model: {e}")
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    # ========== 簡單文字相似度 ==========
    
    def _tokenize(self, text: str) -> List[str]:
        """中英文分詞"""
        text = re.sub(r'[^\w\s]', ' ', str(text))
        tokens = text.lower().split()
        stopwords = {'的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一個', '上', '也', '很', '到', '說', '要', '去', '你', '會', '著', '沒有', '看', '好', '自己', '這', '那', '什麼', '為', '什麼', '你', '我', '他', '她', '它', '們', '個', '把', '被'}
        return [t for t in tokens if t not in stopwords and len(t) > 1]
    
    def _cosine_similarity(self, text1: str, text2: str) -> float:
        """餘弦相似度（基於詞頻）"""
        tokens1 = self._tokenize(text1)
        tokens2 = self._tokenize(text2)
        
        if not tokens1 or not tokens2:
            return 0.0
        
        freq1 = Counter(tokens1)
        freq2 = Counter(tokens2)
        
        dot = sum(freq1.get(t, 0) * freq2.get(t, 0) for t in set(tokens1))
        norm1 = sum(freq1[t]**2 for t in freq1) ** 0.5
        norm2 = sum(freq2[t]**2 for t in freq2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot / (norm1 * norm2)
    
    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """Jaccard 相似度"""
        tokens1 = set(self._tokenize(text1))
        tokens2 = set(self._tokenize(text2))
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        return len(intersection) / len(union)
    
    # ========== 搜尋 ==========
    
    def _get_fts_results(self, query: str, limit: int = 20) -> List[Dict]:
        """FTS5 關鍵字搜尋"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                results = cursor.execute(
                    """
                    SELECT content, summary, bm25(memory_fts) as score
                    FROM memory_fts
                    WHERE memory_fts MATCH ?
                    ORDER BY score
                    LIMIT ?
                    """,
                    (query, limit)
                ).fetchall()
                
                return [{'content': r[0], 'summary': r[1], 'fts_score': abs(r[2])} for r in results]
        except Exception as e:
            print(f"[Hybrid Search] FTS error: {e}")
            return []
    
    def _get_recent_memories(self, limit: int = 50) -> List[Dict]:
        """取得最近的記憶用於語意比對"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                results = cursor.execute(
                    """
                    SELECT content, summary, sentiment_score
                    FROM conversation_history
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (limit,)
                ).fetchall()
                
                return [{'content': r[0], 'summary': r[1] or r[0], 'sentiment': r[2]} for r in results]
        except Exception as e:
            print(f"[Hybrid Search] Memory fetch error: {e}")
            return []
    
    # ========== 混合搜尋主函式 ==========
    
    def hybrid_search(self, query: str, top_n: int = 5, 
                     fts_weight: float = 0.5, 
                     semantic_weight: float = 0.5) -> List[Dict]:
        """
        混合搜尋
        
        1. FTS5 關鍵字匹配
        2. 語意相似度（Cosine + Jaccard 平均）
        3. RRF 合併
        """
        # 1. FTS5 結果
        fts_results = self._get_fts_results(query, limit=20)
        
        # 2. 語意比對
        recent_memories = self._get_recent_memories(limit=50)
        
        semantic_scores = []
        for mem in recent_memories:
            text = mem.get('summary') or mem.get('content', '')
            # 平均 Cosine + Jaccard
            cosine = self._cosine_similarity(query, text)
            jaccard = self._jaccard_similarity(query, text)
            avg_sim = (cosine + jaccard) / 2
            mem['semantic_score'] = avg_sim
            semantic_scores.append(mem)
        
        # 排序
        semantic_scores.sort(key=lambda x: x['semantic_score'], reverse=True)
        semantic_results = semantic_scores[:20]
        
        # 3. RRF 合併
        return self._rrf_merge(fts_results, semantic_results, top_n, fts_weight, semantic_weight)
    
    def _rrf_merge(self, fts_results: List[Dict], semantic_results: List[Dict],
                   top_n: int, fts_weight: float, semantic_weight: float) -> List[Dict]:
        """RRF 合併"""
        k = RRF_K
        
        # 建立排名字典
        fts_ranks = {r['content']: rank for rank, r in enumerate(fts_results)}
        semantic_ranks = {r['content']: rank for rank, r in enumerate(semantic_results)}
        
        # 計算 RRF 分數
        all_contents = set(fts_ranks.keys()) | set(semantic_ranks.keys())
        
        rrf_scores = {}
        for content in all_contents:
            score = 0
            
            if content in fts_ranks:
                rank = fts_ranks[content]
                score += fts_weight * (1 / (k + rank))
            
            if content in semantic_ranks:
                rank = semantic_ranks[content]
                score += semantic_weight * (1 / (k + rank))
            
            rrf_scores[content] = score
        
        # 合併元資料
        content_to_meta = {}
        for r in fts_results:
            content_to_meta[r['content']] = {
                'content': r['content'],
                'summary': r.get('summary'),
                'fts_score': r.get('fts_score', 0),
                'semantic_score': 0
            }
        
        for r in semantic_results:
            if r['content'] in content_to_meta:
                content_to_meta[r['content']]['semantic_score'] = r.get('semantic_score', 0)
            else:
                content_to_meta[r['content']] = {
                    'content': r['content'],
                    'summary': r.get('summary'),
                    'fts_score': 0,
                    'semantic_score': r.get('semantic_score', 0)
                }
        
        # 排序並返回
        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for content, rrf_score in sorted_results[:top_n]:
            if content in content_to_meta:
                result = content_to_meta[content]
                result['rrf_score'] = rrf_score
                results.append(result)
        
        return results
    
    def search(self, query: str, top_n: int = 5) -> List[Dict]:
        """便利搜尋介面"""
        return self.hybrid_search(query, top_n=top_n)


# ========== 測試 ==========

if __name__ == "__main__":
    print("===== Yua Hybrid Search Test =====\n")
    
    engine = HybridMemoryEngine()
    
    # Test searches
    test_queries = [
        "老闆喜歡什麼",
        "Python 程式",
        "撒嬌"
    ]
    
    print("【Hybrid Search Test】")
    for query in test_queries:
        print(f"\nQuery: {query}")
        results = engine.search(query, top_n=3)
        
        if results:
            for i, r in enumerate(results, 1):
                print(f"  {i}. FTS={r.get('fts_score', 0):.2f} SEM={r.get('semantic_score', 0):.2f} RRF={r.get('rrf_score', 0):.3f}")
                print(f"     {r.get('content', '')[:50]}...")
        else:
            print("  No results")
    
    print("\n===== Done =====")
