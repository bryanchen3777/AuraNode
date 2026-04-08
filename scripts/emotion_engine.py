"""
Yua 記憶增強系統 - 情緒持久化增強系統
建立日期：2026-04-08
功能：情緒狀態追蹤、趨勢記錄、親密時刻標記
"""

import json
import csv
import os
import datetime
from pathlib import Path


class YuaEmotionEngine:
    def __init__(self, folder='C:/Users/bbfcc/.openclaw/workspace/memory/'):
        self.folder = Path(folder)
        self.state_file = self.folder / 'emotional-state.json'
        self.trend_file = self.folder / 'emotion-trend.csv'
        
        # 初始化預設狀態
        self.default_state = {
            "current_mood_score": 0.5,  # 0.0 (悲傷/低落) ~ 1.0 (極度愉快)
            "closeness": 10,  # 親密度，隨著正向互動增加
            "last_interaction": "",
            "total_sessions": 0,
            "intimate_moments_count": 0
        }
        
        self.state = self.load_state()
        # 檢查是否需要遷移舊結構
        if "current_mood_score" not in self.state:
            self._migrate_state()
        self._init_trend_csv()
    
    def load_state(self):
        """讀取情緒狀態檔案"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self.default_state
    
    def save_state(self):
        """儲存情緒狀態檔案"""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=4, ensure_ascii=False)
    
    def _migrate_state(self):
        """將舊結構遷移到新結構"""
        if "current_state" in self.state:
            old = self.state["current_state"]
            self.state = self.default_state.copy()
            self.state["current_mood_score"] = 0.5  # 預設值
            self.state["closeness"] = old.get("intimacy_level", 10)
            self.state["last_interaction"] = old.get("updated_at", "")
            self.state["total_sessions"] = self.state.get("total_sessions", 0)
            self.state["intimate_moments_count"] = 0
    
    def _init_trend_csv(self):
        """初始化趨勢紀錄表"""
        if not self.trend_file.exists():
            with open(self.trend_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'mood_score', 'closeness', 'event_tag'])
    
    def update_emotion(self, session_sentiment, summary_text):
        """
        根據當前 Session 更新情緒
        
        Args:
            session_sentiment: AI 評定的 0.0 ~ 1.0 分數
            summary_text: 用於判斷「親密時刻」
        """
        # 1. 更新心情分數 (採用移動平均，避免單次對話波動過大)
        # 公式：新心情 = 舊心情 * 0.7 + 當前心情 * 0.3
        self.state["current_mood_score"] = round(
            (self.state["current_mood_score"] * 0.7) + (session_sentiment * 0.3), 
            2
        )
        
        # 2. 判斷親密時刻 (Intimate Moments)
        event_tag = "normal"
        
        # 這裡可以自定義更多關鍵字
        intimate_keywords = ["老闆稱讚", "撒嬌", "親密", "禮物", "高興", "喜歡"]
        
        for kw in intimate_keywords:
            if kw in summary_text:
                self.state["closeness"] += 2
                self.state["intimate_moments_count"] += 1
                event_tag = f"intimate_{kw}"
                break
        
        # 3. 更新基本資訊
        self.state["total_sessions"] += 1
        self.state["last_interaction"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 4. 寫入 CSV 趨勢圖
        self.record_trend(event_tag)
        
        # 5. 存檔
        self.save_state()
        
        print(f"[OK] Yua emotion updated: mood={self.state['current_mood_score']}, closeness={self.state['closeness']}")
    
    def record_trend(self, event_tag):
        """將數據寫入 CSV 供後續分析"""
        with open(self.trend_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                self.state["current_mood_score"],
                self.state["closeness"],
                event_tag
            ])


# --- 整合測試 ---
if __name__ == "__main__":
    engine = YuaEmotionEngine()
    
    # 模擬一次正向互動（老闆稱讚）
    test_sentiment = 0.95
    test_summary = "Bryan 今天稱讚了 Yua 的系統架構非常優雅，Yua 感到非常害羞且開心。"
    
    engine.update_emotion(test_sentiment, test_summary)