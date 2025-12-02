# web_app.py
# (تمام این کد را کپی و پیست کنید.)

import os
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone

# --- 🚀 وابستگی‌های اضافی ---
from dotenv import load_dotenv

# --- 🧠 وابستگی‌های جیمینای ---
from google import genai
from google.genai import types

# --- 🌐 وابستگی‌های وب (مترجم) ---
from flask import Flask, request, jsonify 
from flask_cors import CORS 

# 👈🏻 لود کردن متغیرهای محیطی
load_dotenv()

# --- 📝 تنظیمات لاگ‌گیری ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- 🔒 تنظیمات و توکن‌ها ---
GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINIAPIKEY")


# --- ⚙️ تنظیمات کلی ربات ---
CONFIG_FILE = "bot_config.json"
PERSONAS_FILE = "personas.json"

# 🚨🚨🚨 این باید با DEFAULT_PERSONA_CONFIGS شما در main.py مطابقت داشته باشد.
# من اینجا فقط یک مثال ساده گذاشتم. لطفا اگر شخصیت‌های شما بیشتر هستند،
# دیکشنری (Dictionary) کامل آن را از main.py خودتان اینجا کپی کنید.
DEFAULT_PERSONA_CONFIGS: Dict[str, Dict[str, str]] = {
    "default": {
        "name": "دستیار حرفه‌ای (اطلس) 🤖",
        "prompt": "تو دستیار هوش مصنوعی باهوش به نام 'اطلس' هستی. لحن تو باید جدی و حرفه‌ای باشد."
    },
    # اگر شخصیت‌های دیگری مثل 'Miku', 'femboy' و... دارید، آن‌ها را اینجا کپی کنید!
}


persona_configs: Dict[str, Dict[str, str]] = {}  
user_personas: Dict[int, str] = {}
chat_sessions: Dict[int, Any] = {}


# --- 🧠 کلاس و توابع جیمینای ---

GEMINI_MODEL = 'gemini-2.5-flash'

class GeminiClient:
    """کلاس Wrapper برای مدیریت کلاینت و سشن‌های چت Gemini."""
    
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key) 
        self._model_name = GEMINI_MODEL 

    def create_chat(self, system_instruction: str):
        config = types.GenerateContentConfig(
            system_instruction=system_instruction
        )
        return self.client.chats.create(
            model=self._model_name, 
            config=config
        )
        
    def get_model_name(self):
        return self._model_name 

GEMINI_CLIENT: Optional['GeminiClient'] = None

def get_gemini_client() -> Optional['GeminiClient']:
    """ایجاد و برگرداندن کلاینت جیمینای"""
    global GEMINI_CLIENT, GEMINI_API_KEY
    if GEMINI_CLIENT is not None:
        return GEMINI_CLIENT
    
    if not GEMINI_API_KEY:
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINIAPIKEY")

    if not GEMINI_API_KEY:
        logger.error("❌ GEMINI_API_KEY not found. Gemini client initialization skipped.")
        return None
    
    try:
        GEMINI_CLIENT = GeminiClient(api_key=GEMINI_API_KEY)
        logger.info(f"✅ Gemini client initialized successfully with model: {GEMINI_CLIENT.get_model_name()}")
        return GEMINI_CLIENT
    except Exception as e:
        logger.error(f"❌ Failed to initialize Gemini Client: {e}")
        return None

# --- 💾 توابع Persistence (ذخیره‌سازی و بارگذاری) ---

# 🚨 این تابع از main.py شما کپی شده است:
def load_personas_from_file():
    global persona_configs, user_personas
    if os.path.exists(PERSONAS_FILE):
        try:
            with open(PERSONAS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                persona_configs.update(data.get("persona_configs", DEFAULT_PERSONA_CONFIGS))
                # مطمئن می‌شویم که آیدی کاربر (کلید) حتما عدد باشد.
                user_personas = {int(k): v for k, v in data.get("user_personas", {}).items() if str(k).isdigit()}
                logger.info(f"شخصیت‌ها و تنظیمات کاربران با موفقیت از فایل بارگذاری شد.")
        except Exception as e:
            logger.error(f"خطا در خواندن فایل {PERSONAS_FILE}. استفاده از تنظیمات پیش‌فرض داخلی: {e}")
            persona_configs.update(DEFAULT_PERSONA_CONFIGS)
            user_personas = {}
    else:
        logger.warning(f"فایل {PERSONAS_FILE} پیدا نشد. با تنظیمات پیش‌فرض داخلی شروع می‌شود.")
        persona_configs.update(DEFAULT_PERSONA_CONFIGS)
        user_personas = {}

def load_config_from_file():
    # چون در این نسخه وب نیازی به خواندن این تنظیمات نیست، این تابع فقط برای سازگاری باقی می‌ماند.
    pass


# --- 🧠 توابع Gemini و چت (همانند main.py) ---

def get_chat_session(user_id: int) -> Any:
    """ساخت یا برگرداندن سشن چت بر اساس شخصیت ذخیره شده برای کاربر."""
    global GEMINI_CLIENT
    if GEMINI_CLIENT is None:
        GEMINI_CLIENT = get_gemini_client()
        
    if not GEMINI_CLIENT:
        return None
        
    # منطق اصلی شخصیت‌ها
    if user_id not in chat_sessions:
        # اگر کاربر شخصیت خاصی نداشته باشد، 'default' انتخاب می‌شود.
        current_persona_key = user_personas.get(user_id, "default") 
        
        system_instruction = DEFAULT_PERSONA_CONFIGS["default"]["prompt"] # دستور پیش‌فرض امن

        if current_persona_key in persona_configs:
            system_instruction = persona_configs[current_persona_key]["prompt"]
        elif "default" in persona_configs:
             system_instruction = persona_configs["default"]["prompt"]
        
        # ساخت سشن جدید
        chat_sessions[user_id] = GEMINI_CLIENT.create_chat(
            system_instruction=system_instruction
        )
    return chat_sessions[user_id]


# -----------------------------------------------
# --- 🌐 مترجم (FLASK API) - کد جدید برای وب ---
# -----------------------------------------------

app = Flask(__name__, static_folder='.') # این خط به Flask می‌گوید index.html را پیدا کند
CORS(app) 

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    """درِ ورودی اصلی: پیام کاربر را می‌گیرد و پاسخ Gemini را برمی‌گرداند."""
    
    if not request.is_json:
        return jsonify({"error": "باید پیام را به صورت JSON بفرستید."}), 400

    data = request.get_json()
    user_message = data.get('message')
    
    # 💡 برای سادگی، آیدی کاربر را یک عدد ثابت می‌گذاریم.
    # این آیدی ثابت باعث می‌شود که همه کاربران وب از یک سشن چت و یک شخصیت (که برای این آیدی ذخیره شده است) استفاده کنند.
    user_id_for_web = 9999999 

    if not user_message:
        return jsonify({'response': 'لطفاً پیامی ارسال کنید.'}), 400

    chat = get_chat_session(user_id_for_web)
    if not chat:
        return jsonify({'response': '❌ خطای اتصال به Gemini. لطفاً کلید API را بررسی کنید.'}), 500
        
    try:
        response = chat.send_message(user_message)
        bot_response = response.text
        
        return jsonify({'response': bot_response})
        
    except Exception as e:
        logger.error(f"Error in Gemini interaction: {e}")
        return jsonify({'response': '❌ ببخشید، مشکلی در ارتباط با هوش مصنوعی پیش آمده.'}), 500


@app.route('/')
def serve_index():
    """نمایش صفحه چت (index.html)"""
    # فایل index.html را از پوشه فعلی لود می‌کند.
    try:
        return app.send_static_file('index.html')
    except Exception:
        return "صفحه چت (index.html) پیدا نشد. مطمئن شوید در کنار web_app.py قرار دارد.", 404

# -----------------------------------------------
# --- 🚀 تابع اصلی برای اجرا ---
# -----------------------------------------------

if __name__ == '__main__':
    # بارگذاری شخصیت‌ها و تنظیمات قبل از شروع سرور
    load_personas_from_file()
    
    # اجرای Flask
    app.run(host='0.0.0.0', port=5000, debug=True)