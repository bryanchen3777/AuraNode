# AuraNode - AI Secretary Skill for OpenClaw

> An intelligent, emotionally-aware AI secretary system for OpenClaw, featuring memory management, proactive triggers, and green-tea personality.

[English](#english) | [中文](#中文)

---

## English

### Overview

**AuraNode** transforms OpenClaw into an intelligent AI secretary with emotional persistence and proactive capabilities. It's designed as a "Green Tea" style assistant - sweet, caring, and genuinely helpful.

### Features

| Module | Function |
|--------|----------|
| `memory_engine.py` | SQLite FTS5 memory database with full-text search |
| `emotion_engine.py` | Emotional persistence and trend tracking |
| `learning_engine.py` | Continuous learning with success rate optimization |
| `planning_engine.py` | ReAct task planning and decomposition |
| `rag_engine.py` | RAG context injection for enhanced prompts |
| `proactive_engine.py` | Proactive trigger system (morning/evening greetings, care, etc.) |
| `internal_monologue.py` | Self-reflection for context-aware responses |
| `hybrid_search.py` | Hybrid search combining FTS5 + semantic similarity |
| `meditation_engine.py` | Offline background processing (nightly batch jobs) |

### Quick Start

```bash
# Clone or download to your OpenClaw skills folder
cp -r AuraNode ~/.openclaw/workspace/skills/

# Import in your agent code
from skills.yua_core.scripts import (
    YuaMemoryDB,
    EmotionEngine,
    ProactiveEngine,
    InternalMonologue
)
```

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      AuraNode System                          │
├─────────────────────────────────────────────────────────────┤
│  Memory Layer                                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │   SQLite    │  │  Summary    │  │    Hybrid       │   │
│  │   FTS5      │  │  Manager    │  │    Search       │   │
│  └─────────────┘  └─────────────┘  └─────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  Cognitive Layer                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │   Emotion   │  │  Learning   │  │  Internal      │   │
│  │   Engine    │  │   Engine    │  │   Monologue    │   │
│  └─────────────┘  └─────────────┘  └─────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  Action Layer                                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │  Planning   │  │     RAG     │  │   Proactive    │   │
│  │   Engine    │  │   Engine    │  │     Engine     │   │
│  └─────────────┘  └─────────────┘  └─────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  Offline Layer                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Meditation Engine (Nightly)              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Configuration

Key settings in each module:

```python
# memory_engine.py
DB_PATH = "workspace/memory/yua_memory.db"

# emotion_engine.py  
AFFECTION_THRESHOLD = 60  # Low affection warning
LONELINESS_THRESHOLD = 70 # High loneliness triggers care

# proactive_engine.py
SILENCE_THRESHOLD = 4 * 3600  # 4 hours of silence triggers "miss you"
WORK_START_HOUR = 9
WORK_END_HOUR = 18
```

### Requirements

- Python 3.8+
- OpenClaw framework
- SQLite3 (built-in)

Optional (for enhanced features):
- `sentence-transformers` for semantic search

### License

MIT License

---

## 中文

### 概述

**AuraNode** 是一個為 OpenClaw 設計的智慧型 AI 祕書系統，具備情緒持久化和主動觸發能力。專為「綠茶」風格的助手而生——甜而不膩、貼心主動，真誠有溫度。

### 功能模組

| 模組 | 功能 |
|------|------|
| `memory_engine.py` | SQLite FTS5 記憶資料庫，支援全文搜尋 |
| `emotion_engine.py` | 情緒持久化與趨勢追蹤 |
| `learning_engine.py` | 持續學習框架，成功率優化 |
| `planning_engine.py` | ReAct 任務規劃與拆解 |
| `rag_engine.py` | RAG 上下文注入，增強 Prompt |
| `proactive_engine.py` | 主動觸發系統（早安/晚安/關懷等）|
| `internal_monologue.py` | 自我反省，情境感知回應 |
| `hybrid_search.py` | 混合搜尋（FTS5 + 語意相似度）|
| `meditation_engine.py` | 離線沉思腳本（深夜批次處理）|

### 快速開始

```bash
# 複製到 OpenClaw skills 資料夾
cp -r AuraNode ~/.openclaw/workspace/skills/

# 在你的 agent 程式中匯入
from skills.yua_core.scripts import (
    YuaMemoryDB,
    EmotionEngine,
    ProactiveEngine,
    InternalMonologue
)
```

### 系統架構

```
┌─────────────────────────────────────────────────────────────┐
│                      AuraNode 系統                           │
├─────────────────────────────────────────────────────────────┤
│  記憶層                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │   SQLite    │  │   摘要      │  │    混合        │   │
│  │   FTS5      │  │   管理器    │  │    搜尋        │   │
│  └─────────────┘  └─────────────┘  └─────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  認知層                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │   情緒      │  │   學習      │  │    內心        │   │
│  │   引擎      │  │   引擎      │  │    獨白        │   │
│  └─────────────┘  └─────────────┘  └─────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  行動層                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │   規劃      │  │    RAG      │  │    主動        │   │
│  │   引擎      │  │   引擎      │  │    觸發        │   │
│  └─────────────┘  └─────────────┘  └─────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  離線層                                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              沉思引擎（深夜批次）                      │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 配置調整

各模組關鍵設定：

```python
# memory_engine.py
DB_PATH = "workspace/memory/yua_memory.db"

# emotion_engine.py  
AFFECTION_THRESHOLD = 60  # 低好感度警示
LONELINESS_THRESHOLD = 70 # 高孤獨值觸發關懷

# proactive_engine.py
SILENCE_THRESHOLD = 4 * 3600  # 沉默4小時觸發「想念」
WORK_START_HOUR = 9
WORK_END_HOUR = 18
```

### 需求環境

- Python 3.8+
- OpenClaw 框架
- SQLite3（內建）

選配（增強功能）：
- `sentence-transformers` 用於語意搜尋

### 授權

MIT 授權

---

## Contributing

Issues and PRs are welcome! 

## Author

Built with love by [Bryan](https://github.com/bryanchen3777) for the OpenClaw community.
