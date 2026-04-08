"""
Yua 記憶增強系統 - SQLite FTS5 記憶引擎
建立日期：2026-04-08
功能：對話記錄儲存、全文搜尋、情緒追蹤
"""

import sqlite3
import os
import datetime

class YuaMemoryDB:
    def __init__(self, db_path='C:/Users/bbfcc/.openclaw/workspace/memory/yua_memory.db'):
        """初始化記憶資料庫"""
        # 確保資料夾存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """建立資料庫連接"""
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        """初始化資料庫與 FTS5 表格"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. 建立原始對話記錄表格 (儲存所有細節)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    content TEXT NOT NULL,
                    summary TEXT,
                    sentiment_score REAL
                )
            ''')
            
            # 2. 建立 FTS5 虛擬表格 (用於全文檢索)
            # 這裡我們主要對 content 和 summary 建立索引
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    content, 
                    summary,
                    content='conversation_history',
                    content_rowid='id'
                )
            ''')
            
            # 3. 建立觸發器 (Trigger)
            # 當原始表新增資料時，自動同步到 FTS 虛擬表
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS after_insert_history 
                AFTER INSERT ON conversation_history
                BEGIN 
                    INSERT INTO memory_fts(rowid, content, summary) 
                    VALUES (new.id, new.content, new.summary);
                END
            ''')
            
            conn.commit()
            print(f"[OK] Yua memory database initialized: {self.db_path}")
    
    def add_memory(self, content, summary="", sentiment=0.0):
        """新增一條記憶"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "INSERT INTO conversation_history (content, summary, sentiment_score) VALUES (?, ?, ?)"
            cursor.execute(query, (content, summary, sentiment))
            conn.commit()
            return cursor.lastrowid
    
    def search_memory(self, keyword):
        """使用 FTS5 進行全文搜尋"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 使用 MATCH 語法進行高效搜尋
            query = '''
                SELECT conversation_history.id, conversation_history.timestamp, 
                       conversation_history.content, conversation_history.summary, 
                       conversation_history.sentiment_score 
                FROM conversation_history 
                JOIN memory_fts ON conversation_history.id = memory_fts.rowid 
                WHERE memory_fts MATCH ? 
                ORDER BY rank
            '''
            cursor.execute(query, (keyword,))
            return cursor.fetchall()
    
    def get_recent_memories(self, limit=5):
        """獲取最近的對話記憶"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM conversation_history ORDER BY timestamp DESC LIMIT ?", (limit,))
            return cursor.fetchall()

# --- 測試運行 ---
if __name__ == "__main__":
    yua_db = YuaMemoryDB()
    
    # 測試新增
    mem_id = yua_db.add_memory(
        content="今天和 Bryan 討論了關於 Soul Evolution 2.0 的進展，他看起來很有信心。",
        summary="討論專案進度",
        sentiment=0.8
    )
    print(f"已新增記憶 ID: {mem_id}")
    
    # 測試搜尋
    results = yua_db.search_memory("Soul Evolution")
    print(f"搜尋結果: {results}")