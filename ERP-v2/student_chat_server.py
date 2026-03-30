#!/usr/bin/env python3
"""
COSH AI 學生聊天室
Port: 0329
獨立於 ERP v2 的輕量 AI 對話服務
"""

import os
import sys
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

# 設定模板路徑
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, template_folder=TEMPLATE_DIR)
CORS(app)  # 允許跨域

# 示範模式回應
def generate_demo_response(message):
    """根據關鍵字產生回應"""
    msg_lower = message.lower()
    
    if any(k in msg_lower for k in ['煩', '累', '壓力', '不開心', '難過', '沮喪']):
        return "聽起來你最近有點辛苦呢... 要不要說說發生了什麼事？有時候把心事說出來會舒服一點 🤗 我在這裡聽你說。"
    
    elif any(k in msg_lower for k in ['點子', '創意', '想法', '建議', '靈感']):
        return "好呀！讓我們一起動動腦筋 💡\\n\\n1. 試試看「腦力激盪」：先不管可不可行，把所有想到的都寫下來\\n2. 換個角度想：如果是你喜歡的作家/導演，他們會怎麼處理？\\n3. 結合興趣：把你喜歡的事物混搭在一起，常常會有驚喜！\\n\\n你想針對哪個方向深入聊聊？"
    
    elif any(k in msg_lower for k in ['故事', '小說', '劇本', '科幻', '奇幻']):
        return "來編個故事吧！🚀\\n\\n「當人類發現，夢境其實是另一個平行宇宙的入口...」\\n\\n你覺得接下來會發生什麼事？主角是誰？他/她為什麼要進入夢境世界？"
    
    elif any(k in msg_lower for k in ['音樂', '歌', '聽歌', '推薦']):
        return "音樂是最好的療癒！🎵\\n\\n看你想要什麼氛圍：\\n• 放鬆：Lo-fi hip hop、輕爵士\\n• 專注：古典樂、環境音樂\\n• 充電：獨立搖滾、電子音樂\\n\\n你現在是什麼心情？我可以推薦更具體的！"
    
    elif any(k in msg_lower for k in ['放鬆', '休息', '無聊', '做什麼']):
        return "放鬆也很重要！這裡有幾個點子 ✨\\n\\n• 試試「5-4-3-2-1」技巧：找出5個看到的、4個摸到的、3個聽到的、2個聞到的、1個嚐到的\\n• 畫個塗鴉，不用想太多\\n• 聽一首沒聽過的歌，閉上眼睛感受\\n• 寫下三件今天值得感謝的事\\n\\n哪個聽起來不錯？"
    
    elif any(k in msg_lower for k in ['考試', '成績', '功課', '作業', '學校']):
        return "學校的事確實會帶來壓力 📚\\n\\n想聊聊具體發生了什麼嗎？還是你需要一些學習或時間管理的小建議？\\n\\n記得：成績不代表你的價值，你比任何分數都更重要 💪"
    
    elif any(k in msg_lower for k in ['夢想', '未來', '想成為', '目標']):
        return "談夢想總是讓人興奮！🌟\\n\\n你想成為什麼樣的人？或者想做什麼樣的事？\\n\\n不用擔心現在看起來遙不可及，每個大夢想都是從小步驟開始的。告訴我你的想法！"
    
    elif any(k in msg_lower for k in ['朋友', '同學', '人際', '吵架', '誤會']):
        return "人際關係有時候真的很複雜... 💭\\n\\n發生了什麼事嗎？有時候說出來，我們可以一起想想怎麼處理。\\n\\n不管怎樣，記得你值得被好好對待。"
    
    elif any(k in msg_lower for k in ['你好', '嗨', 'hi', 'hello', 'hey']):
        return "嗨！很高興認識你 👋\\n\\n我是 COSH AI，可以陪你聊天、發想點子、或者只是靜靜地聽你說話。\\n\\n今天想聊什麼呢？"
    
    elif any(k in msg_lower for k in ['謝謝', '感謝', 'thx', 'thanks']):
        return "不客氣！😊 隨時歡迎回來聊天。希望你今天有個美好的一天！✨"
    
    elif any(k in msg_lower for k in ['再見', 'bye', '掰掰', '下次見']):
        return "再見！很高興能陪你聊天 👋\\n\\n記得：不管遇到什麼，你都不是一個人。隨時回來找我！✨"
    
    else:
        return f"「{message}」—— 有趣的想法！可以多說一點嗎？我很好奇 💭\\n\\n或者，如果你想轉換心情，我可以：\\n• 幫你想一些創意點子\\n• 陪你聊聊心情\\n• 一起發想故事\\n• 推薦放鬆的方式"

@app.route('/')
def index():
    """聊天室首頁"""
    return render_template('student_chat.html')

@app.route('/api/chat', methods=['POST'])
def chat_api():
    """AI 聊天 API"""
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({'success': False, 'message': '請輸入訊息'}), 400
    
    try:
        # 嘗試連接 oMLX 本地模型
        try:
            import requests
            # oMLX 預設在 port 8000 或 1234
            omlx_ports = [8000, 1234, 8080]
            ai_response = None
            
            for port in omlx_ports:
                try:
                    response = requests.post(
                        f'http://localhost:{port}/v1/chat/completions',
                        json={
                            'model': 'qwen3.5-9b',
                            'messages': [
                                {'role': 'system', 'content': '你是一個友善、有創意的 AI 助理，專門陪伴高中生聊天、抒發情緒、發想創意。請用輕鬆、溫暖、年輕的語氣回應，可以適度使用表情符號。'},
                                {'role': 'user', 'content': message}
                            ],
                            'stream': False,
                            'max_tokens': 500,
                            'temperature': 0.8
                        },
                        timeout=5
                    )
                    if response.status_code == 200:
                        result = response.json()
                        ai_response = result['choices'][0]['message']['content']
                        break
                except:
                    continue
            
            if ai_response:
                return jsonify({'success': True, 'response': ai_response})
        except:
            pass
        
        # 如果 oMLX 沒有回應，使用示範回應
        response_text = generate_demo_response(message)
        return jsonify({'success': True, 'response': response_text})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/health')
def health_check():
    """健康檢查"""
    return jsonify({
        'status': 'ok',
        'service': 'COSH AI Student Chat',
        'port': 329,
        'time': __import__('datetime').datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🚀 COSH AI 學生聊天室啟動中...")
    print("📱 請訪問: http://localhost:329")
    print("")
    app.run(host='0.0.0.0', port=329, debug=False)
