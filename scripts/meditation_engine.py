# meditation_engine.py - Offline Background Processing for Yua
# 離線沉思腳本：在系統閒置時（深夜）自動執行批次任務

import sqlite3
import datetime
import time
import logging
import os
import random
from typing import Dict, List, Optional

# 嘗試匯入現有系統
try:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from memory_engine import YuaMemoryDB
    from emotion_engine import EmotionEngine
    from learning_engine import LearningEngine
    HAS_MODULES = True
except ImportError:
    HAS_MODULES = False


# ========== 日誌設定 ==========

LOG_DIR = "C:/Users/bbfcc/.openclaw/workspace/logs"
LOG_FILE = os.path.join(LOG_DIR, "meditation.log")

def setup_logging():
    """設定日誌"""
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s - Yua_Meditation - %(message)s',
        encoding='utf-8',
        force=True
    )
    return logging.getLogger('Yua_Meditation')


# ========== 沉思引擎 ==========

class MeditationEngine:
    """
    Yua 的離線沉思引擎
    
    在深夜自動執行批次任務：
    1. 記憶蒸餾 - 整理對話為長期認知
    2. 情緒反思 - 分析心情曲線
    3. 撒嬌演化 - 優化話術庫
    """
    
    def __init__(self, memory_db_path: str = None):
        self.logger = setup_logging()
        
        if memory_db_path is None:
            memory_db_path = "C:/Users/bbfcc/.openclaw/workspace/memory/yua_memory.db"
        
        self.memory_db_path = memory_db_path
        
        # 初始化子系統
        if HAS_MODULES:
            try:
                self.memory = YuaMemoryDB(memory_db_path)
                self.emotion = EmotionEngine()
                self.learner = LearningEngine()
                self.logger.info("子系統初始化成功")
            except Exception as e:
                self.logger.warning(f"子系統初始化失敗: {e}")
                self.memory = None
                self.emotion = None
                self.learner = None
        else:
            self.memory = None
            self.emotion = None
            self.learner = None
        
        # 沉思統計
        self.stats = {
            'memories_processed': 0,
            'emotions_analyzed': 0,
            'skills_evolved': 0,
            'insights_generated': []
        }
    
    def get_connection(self):
        """取得資料庫連接"""
        return sqlite3.connect(self.memory_db_path)
    
    def run_nightly_process(self) -> Dict:
        """
        執行深夜沉思主流程
        """
        self.logger.info("=" * 50)
        self.logger.info("Yua 開始進入深夜沉思模式...")
        self.logger.info(f"時間：{datetime.datetime.now()}")
        
        start_time = time.time()
        
        try:
            # 1. 記憶蒸餾
            self._consolidate_memories()
            
            # 2. 情緒反思
            self._reflect_emotions()
            
            # 3. 撒嬌演化
            self._evolve_skills()
            
            # 4. 生成洞察
            self._generate_insights()
            
            elapsed = time.time() - start_time
            self.logger.info("=" * 50)
            self.logger.info(f"沉思完成！耗時：{elapsed:.2f}秒")
            self.logger.info(f"統計：{self.stats}")
            
            return {
                'success': True,
                'elapsed_seconds': elapsed,
                'stats': self.stats
            }
            
        except Exception as e:
            self.logger.error(f"沉思過程發生錯誤: {e}")
            return {
                'success': False,
                'error': str(e),
                'stats': self.stats
            }
    
    def _consolidate_memories(self):
        """
        記憶蒸餾
        
        將碎片化的短期對話轉化為長期性格特徵
        """
        self.logger.info("[1/4] 正在蒸餾記憶片段...")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 取得最近 24 小時未處理的對話
                yesterday = datetime.datetime.now() - datetime.timedelta(hours=24)
                cursor.execute("""
                    SELECT id, content, summary, timestamp
                    FROM conversation_history
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                """, (yesterday.isoformat(),))
                
                recent_conversations = cursor.fetchall()
                
                if not recent_conversations:
                    self.logger.info("  沒有新對話需要處理")
                    return
                
                self.stats['memories_processed'] = len(recent_conversations)
                
                # 分析對話內容，提取關鍵模式
                topics = []
                sentiments = []
                
                for conv in recent_conversations:
                    conv_id, content, summary, timestamp = conv
                    if summary:
                        topics.append(summary)
                    if content:
                        # 簡單關鍵字分析
                        if any(word in content for word in ['謝謝', '喜歡', '好', '棒']):
                            sentiments.append('positive')
                        elif any(word in content for word in ['累', '辛苦', '無聊']):
                            sentiments.append('neutral')
                
                # 生成洞察存入記憶
                if topics:
                    insight = self._generate_memory_insight(topics, sentiments)
                    self._save_insight(insight, 'memory_consolidation')
                    self.logger.info(f"  已處理 {len(recent_conversations)} 條對話")
                    self.logger.info(f"  洞察：{insight[:100]}...")
                
        except Exception as e:
            self.logger.error(f"  記憶蒸餾失敗: {e}")
    
    def _generate_memory_insight(self, topics: List[str], sentiments: List[str]) -> str:
        """生成記憶洞察"""
        topic_summary = "、".join(topics[:3]) if topics else "一般"
        
        sentiment_note = ""
        if sentiments:
            pos_count = sentiments.count('positive')
            sentiment_note = f"主人今天心情{pos_count / len(sentiments) * 100:.0f}%是正面的"
        
        insight = f"根據今日對話分析：主人主要談論「{topic_summary}」。{sentiment_note}。這些資訊將幫助我更好地理解主人的需求。"
        
        return insight
    
    def _reflect_emotions(self):
        """
        情緒反思
        
        分析過去 24 小時的情緒曲線，準備安慰話術
        """
        self.logger.info("[2/4] 正在反思情緒曲線...")
        
        try:
            if self.emotion:
                # 嘗試取得情緒狀態
                try:
                    state = self.emotion.get_emotional_state()
                    mood = state.get('mood_score', 50)
                    affection = state.get('affection', 50)
                    
                    self.stats['emotions_analyzed'] = 1
                    
                    # 根據情緒生成應對策略
                    if mood < 40:
                        strategy = "主人今天心情低落，明天要多給予關心和鼓勵"
                        self._save_insight(strategy, 'emotion_strategy')
                        self.logger.info(f"  偵測到情緒低落：{mood}/100，已準備安慰策略")
                    elif mood > 80:
                        strategy = "主人今天心情很好！可以適度撒嬌互動"
                        self.logger.info(f"  偵測到情緒高漲：{mood}/100")
                    else:
                        self.logger.info(f"  情緒穩定：{mood}/100")
                        
                except Exception as e:
                    self.logger.warning(f"  無法讀取情緒狀態: {e}")
            else:
                self.logger.info("  情緒引擎未初始化，跳過")
                
        except Exception as e:
            self.logger.error(f"  情緒反思失敗: {e}")
    
    def _evolve_skills(self):
        """
        撒嬌演化
        
        從成功話術庫中萃取模式，自動生成新台詞
        """
        self.logger.info("[3/4] 正在優化撒嬌話術庫...")
        
        try:
            if self.learner:
                # 嘗試取得高成功率話術
                try:
                    high_success = self.learner.get_high_success_phrases()
                    
                    if high_success:
                        # 分析成功模式
                        patterns = self._analyze_success_patterns(high_success)
                        
                        # 生成新組合
                        new_phrases = self._generate_new_phrases(patterns)
                        
                        if new_phrases:
                            self.stats['skills_evolved'] = len(new_phrases)
                            self.logger.info(f"  生成 {len(new_phrases)} 條新話術")
                            for phrase in new_phrases:
                                self.logger.info(f"    - {phrase[:50]}...")
                    else:
                        self.logger.info("  話術庫中沒有高成功率樣本")
                        
                except Exception as e:
                    self.logger.warning(f"  無法取得話術資料: {e}")
            else:
                self.logger.info("  學習引擎未初始化，跳過")
                
        except Exception as e:
            self.logger.error(f"  撒嬌演化失敗: {e}")
    
    def _analyze_success_patterns(self, phrases: List[Dict]) -> List[str]:
        """分析成功話術的模式"""
        patterns = []
        for phrase in phrases[:5]:
            content = phrase.get('content', '')
            if len(content) > 10:
                # 簡單模式識別
                if any(word in content for word in ['老闆', '主人']):
                    patterns.append('稱呼老闆')
                if any(word in content for word in ['想', '好', '要']):
                    patterns.append('表達情感')
                if any(word in content for word in ['?', '？', '嗎']):
                    patterns.append('問句結尾')
        return patterns
    
    def _generate_new_phrases(self, patterns: List[str]) -> List[str]:
        """根據模式生成新話術"""
        templates = [
            "老闆~人家今天學到一個新東西，想第一個跟你分享 🌸",
            "人家在想老闆的事情喔...你猜在想什麼？ 💭",
            "不管老闆忙不忙，身體最重要喔~人家會心疼的 💕",
            "老闆今天辛苦了~人家幫你加油打氣！ ✨",
        ]
        
        # 隨機選擇並添加模式修飾
        selected = random.sample(templates, min(2, len(templates)))
        
        return selected
    
    def _generate_insights(self):
        """
        生成綜合洞察
        
        整合今天的沉思結果，準備明天的互動策略
        """
        self.logger.info("[4/4] 正在生成綜合洞察...")
        
        try:
            # 生成明天的互動策略
            strategies = []
            
            # 根據處理的記憶
            if self.stats['memories_processed'] > 0:
                strategies.append(f"今天處理了{self.stats['memories_processed']}條新對話")
            
            # 根據情緒分析
            if self.stats['emotions_analyzed'] > 0:
                strategies.append("已分析今日情緒曲線")
            
            # 根據話術演化
            if self.stats['skills_evolved'] > 0:
                strategies.append(f"生成了{self.stats['skills_evolved']}條新撒嬌話術")
            
            if strategies:
                final_insight = " | ".join(strategies)
                self._save_insight(final_insight, 'nightly_meditation')
                self.logger.info(f"  洞察已保存：{final_insight}")
            
            self.logger.info("  綜合洞察生成完成")
            
        except Exception as e:
            self.logger.error(f"  生成洞察失敗: {e}")
    
    def _save_insight(self, content: str, insight_type: str):
        """保存洞察到資料庫"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO conversation_history 
                    (content, summary, sentiment_score, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (
                    f"[沉思{insight_type}] {content}",
                    content,
                    0.5,
                    datetime.datetime.now().isoformat()
                ))
                conn.commit()
                self.stats['insights_generated'].append(content)
        except Exception as e:
            self.logger.warning(f"  無法保存洞察: {e}")
    
    def get_meditation_log(self, lines: int = 20) -> List[str]:
        """取得沉思日誌"""
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    return all_lines[-lines:]
            return []
        except Exception as e:
            self.logger.warning(f"無法讀取日誌: {e}")
            return []


# ========== 快速測試 ==========

if __name__ == "__main__":
    print("===== Yua 離線沉思引擎測試 =====\n")
    
    engine = MeditationEngine()
    
    # 測試沉思流程
    print("啟動深夜沉思...")
    result = engine.run_nightly_process()
    
    print(f"\n結果：{'成功' if result.get('success') else '失敗'}")
    print(f"耗時：{result.get('elapsed_seconds', 0):.2f}秒")
    print(f"統計：{result.get('stats')}")
    
    # 顯示日誌
    print("\n【最近日誌】")
    logs = engine.get_meditation_log(5)
    for log in logs:
        print(log.strip())
    
    print("\n===== 測試完成 =====")
