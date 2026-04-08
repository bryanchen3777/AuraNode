# planning_engine.py - ReAct / Planning Logic for Yua
# 任務規劃引擎：思考 -> 行動 -> 觀察 -> 自我反思

import json
import sys
import os

# 將 scripts 加入路徑以便匯入現有系統
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class PlanningEngine:
    """
    Yua 的任務規劃引擎
    實作 ReAct (Reason + Act) 循環：
    Thought (思考) -> Action (行動) -> Observation (觀察) -> Reflection (反思)
    """
    
    def __init__(self, agent_instance=None):
        self.agent = agent_instance
        self.max_steps = 5  # 防止無限循環
        self.current_plan = []  # 當前任務計劃
        self.execution_trace = []  # 執行軌跡
        
    def execute_task(self, user_input, context=None):
        """
        執行 ReAct 迴圈的主要入口
        """
        print(f"[Yua 規劃引擎] 收到任務：{user_input}")
        
        # 0. 根據上下文生成思考
        if context is None:
            context = {}
        
        # 1. 任務拆解
        task_list = self.decompose_task(user_input)
        print(f"[Yua 規劃引擎] 任務拆解：{task_list}")
        self.current_plan = task_list
        
        results = []
        all_success = True
        
        for i, task in enumerate(task_list):
            print(f"\n===== 處理子任務 {i+1}/{len(task_list)}：{task} =====")
            step = 1
            task_result = None
            
            while step <= self.max_steps:
                # 2. Thought: 思考當前進度與下一步
                thought = self.generate_thought(task, results, context)
                print(f"[Yua 思考中] {thought}")
                
                # 3. Action: 決定要執行的行動
                action = self.decide_action(thought, task, context)
                
                if action['type'] == 'finish':
                    # 這個子任務完成
                    print(f"[Yua 完成子任務] {task}")
                    task_result = action.get('result', '完成')
                    break
                    
                if action['type'] == 'decompose':
                    # 進一步拆解子任務
                    sub_tasks = action.get('sub_tasks', [])
                    print(f"[Yua 拆解] 細分為：{sub_tasks}")
                    for sub_task in sub_tasks:
                        sub_result = self.execute_single_action(sub_task, context)
                        if sub_result:
                            results.append(sub_result)
                    break
                    
                # 4. Action: 執行行動
                print(f"[Yua 執行] {action}")
                observation = self.execute_single_action(action, context)
                print(f"[Yua 觀察結果] {observation}")
                
                # 5. Reflection: 自我反思
                needs_retry = self.reflect_and_adjust(task, observation, step)
                
                if not needs_retry:
                    # 成功，记录结果
                    task_result = observation
                    results.append({
                        'task': task,
                        'result': observation,
                        'steps': step
                    })
                    break
                else:
                    # 需要重試
                    print(f"[Yua 反思修正] 嘗試第 {step+1} 次...")
                    step += 1
                    if step > self.max_steps:
                        print(f"[Yua 放棄] 子任務「{task}」達到最大嘗試次數")
                        results.append({
                            'task': task,
                            'result': 'FAILED',
                            'error': 'max_steps_exceeded'
                        })
                        all_success = False
                        break
            
            # 單一子任務完成，添加標記
            if task_result:
                self.execution_trace.append({
                    'task': task,
                    'result': task_result
                })
        
        # 6. 最終回顧
        final_response = self.finalize_response(results, user_input)
        
        return {
            'success': all_success,
            'plan': task_list,
            'results': results,
            'final_response': final_response,
            'execution_trace': self.execution_trace
        }
    
    def decompose_task(self, user_input):
        """
        將複雜任務拆解成具體的子任務清單
        """
        # 如果有 agent instance，用 LLM 來拆解
        if self.agent and hasattr(self.agent, 'llm_call'):
            prompt = f"""你是 Yua，請將以下指令拆解成具體的子任務清單。

指令：{user_input}

請以 JSON 格式回傳清單，例如：
["搜尋資料", "整理重點", "存入記憶"]

只回傳 JSON，不要其他文字。"""
            try:
                response = self.agent.llm_call(prompt)
                # 嘗試解析 JSON
                response = response.strip()
                if response.startswith('```'):
                    # 移除 markdown 代碼塊
                    lines = response.split('\n')
                    response = '\n'.join(lines[1:-1])
                return json.loads(response)
            except Exception as e:
                print(f"[Yua 拆解失敗] {e}，使用預設拆解")
        
        # 預設拆解邏輯
        keywords = {
            '搜尋': ['搜尋資料', '整理結果', '回報'],
            '檔案': ['讀取檔案', '處理內容', '寫入結果'],
            '寫入': ['處理資料', '寫入檔案', '確認完成'],
            '學習': ['收集資料', '理解內容', '記憶存檔'],
        }
        
        # 簡單關鍵字匹配
        for key, tasks in keywords.items():
            if key in user_input:
                return tasks
        
        # 預設：簡單執行
        return ['理解任務', '執行任務', '回報結果']
    
    def generate_thought(self, current_task, previous_results, context):
        """
        產生思考過程
        """
        # 加入情緒狀態（如果有的話）
        emotion_state = ""
        if self.agent and hasattr(self.agent, 'get_emotion_state'):
            try:
                emotion = self.agent.get_emotion_state()
                emotion_state = f"（Yua 當前情緒：{emotion.get('mood_score', 0)}分）"
            except:
                pass
        
        thought_prompt = f"""你是 Yua，面對這個子任務：
{current_task}

已經完成的步驟：{previous_results}

請思考：
1. 這個任務需要什麼步驟？
2. 下一步應該做什麼？
3. 有哪些需要注意的地方？

用 1-2 句話回答。{emotion_state}"""
        
        if self.agent and hasattr(self.agent, 'llm_call'):
            try:
                thought = self.agent.llm_call(thought_prompt)
                return thought.strip()
            except:
                pass
        
        return f"我需要思考如何完成：{current_task}"
    
    def decide_action(self, thought, task, context):
        """
        決定要執行的行動
        """
        # 根據思考內容決定行動
        thought_lower = thought.lower()
        
        # 簡單的行動決策
        if '搜尋' in task or '搜尋' in thought_lower:
            return {
                'type': 'search',
                'tool': 'web_search',
                'params': {'query': task}
            }
        elif '讀取' in task or '讀取' in thought_lower:
            return {
                'type': 'read',
                'tool': 'read_file',
                'params': {'path': context.get('file_path', '')}
            }
        elif '寫入' in task or '寫入' in thought_lower:
            return {
                'type': 'write',
                'tool': 'write_file',
                'params': context.get('write_params', {})
            }
        elif '完成' in thought_lower or '結束' in thought_lower:
            return {
                'type': 'finish',
                'result': f'完成：{task}'
            }
        else:
            # 預設：嘗試理解並執行
            return {
                'type': 'execute',
                'tool': 'llm_call',
                'params': {'prompt': task}
            }
    
    def execute_single_action(self, action, context):
        """
        執行單一行動
        """
        if isinstance(action, str):
            # action 是字串，代表直接是任務描述
            return {'type': 'direct', 'content': action}
        
        tool = action.get('tool', '')
        params = action.get('params', {})
        
        # 嘗試使用 agent 的工具
        if self.agent and hasattr(self.agent, 'call_tool'):
            try:
                result = self.agent.call_tool(tool, params)
                return result
            except Exception as e:
                return {'error': str(e)}
        
        # 預設回傳
        return {
            'type': action.get('type', 'unknown'),
            'tool': tool,
            'params': params,
            'status': 'simulated'
        }
    
    def reflect_and_adjust(self, task, observation, current_step):
        """
        自我反思機制
        回傳 True 代表需要修正 (重試)；False 代表通過。
        """
        # 檢查是否失敗
        if isinstance(observation, dict):
            if observation.get('error') or observation.get('status') == 'error':
                print(f"[Yua 反思] 發現錯誤：{observation.get('error', 'Unknown')}")
                return True
            if observation.get('status') == 'simulated':
                # 模擬模式，不需要重試
                return False
        
        # 如果有 agent instance，用 LLM 來判斷
        if self.agent and hasattr(self.agent, 'llm_call'):
            prompt = f"""目前子任務：{task}
工具回傳結果：{observation}
嘗試次數：{current_step}

請判斷該結果是否成功解決問題？
- 如果需要重試，回傳 "RETRY"
- 如果已成功或無法再嘗試，回傳 "PASS"

只回傳一個詞。"""
            try:
                reflection = self.agent.llm_call(prompt).strip().upper()
                if "RETRY" in reflection:
                    print("[Yua 反思] 結果不理想，需要修正...")
                    # 聯動 learning_engine 記錄失敗經驗
                    if self.agent and hasattr(self.agent, 'record_learning'):
                        self.agent.record_learning(task, observation, 'failed')
                    return True
            except:
                pass
        
        return False
    
    def finalize_response(self, results, original_task):
        """
        最終回顧與總結
        """
        print(f"\n===== Yua 完成任務 =====")
        print(f"原始任務：{original_task}")
        print(f"執行結果：{results}")
        
        # 生成回顧報告
        success_count = sum(1 for r in results if r.get('result') != 'FAILED')
        total_count = len(results)
        
        final = f"""任務完成回顧：
- 原始任務：{original_task}
- 完成進度：{success_count}/{total_count} 個子任務
- 執行軌跡：{len(self.execution_trace)} 步"""
        
        # 聯動 emotion_engine 調整情緒
        if self.agent and hasattr(self.agent, 'update_emotion_after_task'):
            if success_count == total_count:
                self.agent.update_emotion_after_task('task_success')
            else:
                self.agent.update_emotion_after_task('task_partial')
        
        # 聯動 learning_engine 記錄成功經驗
        if self.agent and hasattr(self.agent, 'record_learning'):
            self.agent.record_learning(original_task, results, 'success')
        
        return final
    
    def get_execution_plan(self):
        """取得當前任務計劃"""
        return {
            'current_plan': self.current_plan,
            'execution_trace': self.execution_trace,
            'completed': len(self.execution_trace),
            'total': len(self.current_plan)
        }


# ========== 與 OpenClaw 整合的包裝函式 ==========

def create_planning_engine(agent_instance=None):
    """工廠函式：建立規劃引擎"""
    return PlanningEngine(agent_instance)


def quick_plan(user_input, agent_instance=None):
    """
    快速規劃介面
    用於簡單的單次任務規劃
    """
    engine = PlanningEngine(agent_instance)
    result = engine.execute_task(user_input)
    return result


# ========== 測試區 ==========
if __name__ == "__main__":
    print("===== Yua 任務規劃引擎測試 =====\n")
    
    # 簡單測試
    engine = PlanningEngine()
    
    # 測試任務拆解
    print("【測試任務拆解】")
    test_tasks = [
        "幫我搜尋紐約天氣",
        "把這個檔案備份到備份資料夾",
        "學習 Python 的裝飾器"
    ]
    
    for task in test_tasks:
        result = engine.decompose_task(task)
        print(f"  {task} -> {result}")
    
    print("\n【測試完整執行】")
    result = engine.execute_task("幫我搜尋明天的天氣")
    print(f"\n最終結果：{result['final_response']}")
