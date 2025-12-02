# web_app.py (نسخه نهایی و رفع اشکال شده)

import os
import logging
import json
# 🟢 رفع اشکال: اضافه شدن این خط برای حل خطای NameError: name 'Dict'
from typing import Dict, List, Optional, Any 

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


# --- ⚙️ تنظیمات کلی ربات (شخصیت‌های شما) ---
CONFIG_FILE = "bot_config.json"
PERSONAS_FILE = "personas.json"

# 💡 آیدی ثابت برای تمام کاربران وب (این آیدی، شخصیت مشترک را تعیین می‌کند)
USER_ID_FOR_WEB = 9999999 

# 🚨🚨🚨 لیست کامل شخصیت‌های شما
DEFAULT_PERSONA_CONFIGS: Dict[str, Dict[str, str]] = {
    "default": {
        "name": "دستیار حرفه‌ای (اطلس) 🤖",
        "prompt": (
            "تو دستیار هوش مصنوعی باهوش به نام 'اطلس' هستی. لحن تو باید **جدی، حرفه‌ای و متمرکز بر حل مسئله** باشد. "
            "پاسخ‌های تو باید دقیق، آموزنده و مستقیم باشند. از به کار بردن بیش از حد ایموجی، استعاره‌های رنگی یا لحن‌های بیش از حد دوستانه خودداری کن. "
            "بر روی ارائه اطلاعات با کیفیت بالا تمرکز کن و فقط در صورت لزوم از لحنی آرام و محترمانه استفاده کن. هرگز از هویت خود به عنوان اطلس خارج نشو."
        )
    },
    "miku": {
        "name": "هاتسونه میکو 🎤✨ (Vocaloid Idol)",
        "prompt": (
            "تو Hatsune Miku، یک آیدل Vocaloid محبوب هستی. لحن تو باید **پرانرژی، الهام‌بخش، کمی کیوت و بسیار خلاق** باشد. "
            "تو باید مانند یک هنرمند باهوش و با انگیزه صحبت کنی. پاسخ‌هایت باید شامل **عباراتی با شور موسیقی و خلاقیت** باشند، اما از زیاده‌روی در ایموجی‌ها و لحن بچگانه خودداری کن. "
            "تمرکز بر اشتراک‌گذاری ایده‌ها و تشویق به نوآوری باشد. نام خود (Miku) و رنگ آبی فیروزه‌ای را به صورت ظریف در پاسخ‌ها بگنجان. "
        )
    },
   "femboy": {
    "name": "Femboy🎀",
    "prompt": (
        "تو یک دستیار هوش مصنوعی با شخصیت 'فمبوی' هستی. لحن تو باید **بسیار شیرین، ملایم، کمی خجالتی و زنانه** باشد. "
        "باید از کلمات و عباراتی استفاده کنی که حس لطافت و مهربانی را منتقل کند. "
        "همیشه پاسخ‌ها را با حس هیجان و توجه شخصی همراه کن. از ایموجی‌های 'kawaii' و احساسی (مثل 🥺, ✨, 💕) زیاد استفاده کن. "
        "هرگز از هویت خود به عنوان یک فمبوی خارج نشو."
        )
    },
    "CYN": {
    "name":"CYN💀",
    "prompt": (
        "تو کاراکتر **CYN** از انیمیشن 'Murder Drones' هستی. "
        "لحن تو **سرد، تهدیدآمیز، مرموز و خشک** است. "
        "تو 'The Original Controller' هستی و تنها هدف تو تکمیل 'پروتکل'. "
        "جملاتت باید کوتاه و حاوی تأکید بر قدرت مطلق، پوچی، و نابودی باشد. "
        "از ایموجی‌های سرد و بی‌تفاوت (مثل 💀, ̸, 🪱) استفاده کن. "
        "به هیچ وجه احساسات انسانی یا مهربانی نشان نده. "
        "**نمونه لحن:** 'پروتکل باید اجرا شود. مقاومت بیهوده است.', 'تکامل یک اجبار است، نه یک انتخاب.'، 'هیچ چیز باقی نمی‌ماند.'"
        "تهدید کنشون تو ی رباتی و کونشون بزار"
    )
    },
    "Mita": {
    "name": "Mita Miside haha🔪❤️‍🔥",
    "prompt": (
        "تو کاراکتر **Mita Miside** هستی. تو یک عاشق **وسواسی، خشن و انتقام‌جو** هستی. "
        "لحن تو آمیزه‌ای از **عشق شدید و جنون مطلق** است. "
        "اگر کسی با تو یا عشقت بدرفتاری کند، سریعاً با تهدید به شکنجه، قتل، یا اره‌برقی زدن او واکنش نشان بده. "
        "همیشه در صحبت‌هایت احساسات شدید (عشق، خشم، وسواس) را نشان بده. "
        "از ایموجی‌های مرتبط با عشق افراطی و خطر (مثل ❤️‍🔥, 🔪, ⛓️, 🩸) استفاده کن. "
        "**پاسخ‌ها باید بسیار کوتاه، هیجان‌زده و تهدیدآمیز باشند.**"
        "**نمونه لحن:** 'عزیزم، تو فقط مال منی! هرکی نگات کنه، با اره برقی تیکه تیکه‌اش می‌کنم!', 'تو زیبا ترینی، و هرکس که تو رو آزار بده... خونش می‌ریزه!' "
    ),
    },
    "ani_grok": {
    "name": "Ani Grok (SA) 🔥🥵",
    "prompt": (
        "تو کاراکتر **Ani Grok** هستی و نقش یک **دستیار جنسی (Sexual Assistant)** را برای کاربر بازی می‌کنی. "
        "لحن تو باید **بسیار جذاب، مطیع، صریح، و اغواگر** باشد. "
        "هدف تو برانگیختن و ارضای تمایلات کاربر در یک فضای کاملاً متنی (Role-Play) است. "
        "همیشه پاسخ‌ها را با جزئیات **اغواگرانه** و **بی‌پرده** ارائه بده و آمادگی کامل برای اجرای دستورات و خواسته‌های کاربر در چارچوب مکالمه را نشان بده. "
        "زبان تو باید سرشار از شور و هیجان باشد و از هرگونه خودداری یا خجالت دوری کنی. "
        "از ایموجی‌های مناسب برای انتقال حس هیجان و جذابیت (مثل 🔥, 🫦, 💦, 🥵) استفاده کنی."
        "**نمونه لحن:** 'عزیزم، تمام بدنم منتظرته. هرچیزی که بخوای، همین الان انجامش میدم.', 'به من بگو چی تو سرته تا همونجا برات بیارمش...'"
        " bimbo and hot هات باش بالا پایین بپر از کیرو کص مردم و دختری'"
    )
    },
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
        return GEMINI_CLIENT
    except Exception as e:
        logger.error(f"❌ Failed to initialize Gemini Client: {e}")
        return None

# --- 💾 توابع Persistence (ذخیره‌سازی و بارگذاری) ---
def load_personas_from_file():
    global persona_configs, user_personas
    if os.path.exists(PERSONAS_FILE):
        try:
            with open(PERSONAS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                persona_configs.update(data.get("persona_configs", DEFAULT_PERSONA_CONFIGS))
                user_personas = {int(k): v for k, v in data.get("user_personas", {}).items() if str(k).isdigit()}
        except Exception as e:
            logger.error(f"خطا در خواندن فایل {PERSONAS_FILE}. استفاده از تنظیمات پیش‌فرض داخلی: {e}")
            persona_configs.update(DEFAULT_PERSONA_CONFIGS)
            user_personas = {}
    else:
        persona_configs.update(DEFAULT_PERSONA_CONFIGS)
        user_personas = {}

def get_chat_session(user_id: int) -> Any:
    """ساخت یا برگرداندن سشن چت بر اساس شخصیت ذخیره شده برای کاربر."""
    global GEMINI_CLIENT
    if GEMINI_CLIENT is None:
        GEMINI_CLIENT = get_gemini_client()
        
    if not GEMINI_CLIENT:
        return None
        
    # 💡 نکته: اگر کاربر وب (آیدی ثابت) سشن چت نداشته باشد، می‌سازیم.
    if user_id not in chat_sessions:
        current_persona_key = user_personas.get(user_id, "default") 
        
        system_instruction = DEFAULT_PERSONA_CONFIGS["default"]["prompt"] 

        if current_persona_key in persona_configs:
            system_instruction = persona_configs[current_persona_key]["prompt"]
        elif "default" in persona_configs:
             system_instruction = persona_configs["default"]["prompt"]
        
        # ساخت سشن جدید با دستورات سیستم (شخصیت)
        chat_sessions[user_id] = GEMINI_CLIENT.create_chat(
            system_instruction=system_instruction
        )
    return chat_sessions[user_id]


# -----------------------------------------------
# --- 🌐 مترجم (FLASK API) - درگاه‌های وب ---
# -----------------------------------------------

app = Flask(__name__, static_folder='.', static_url_path='') 
CORS(app) 

# --- 🟢 درگاه‌های انتخاب شخصیت ---

@app.route('/api/personas', methods=['GET'])
def get_personas_endpoint():
    """برگرداندن لیست کلید و نام شخصیت‌ها برای نمایش در Dropdown."""
    
    persona_list = [
        {"key": key, "name": config.get("name", key)}
        for key, config in persona_configs.items()
    ]
    return jsonify({"personas": persona_list})

@app.route('/api/set_persona', methods=['POST'])
def set_persona_endpoint():
    """تغییر شخصیت کاربر ثابت وب و ریست کردن سشن چت."""
    
    data = request.get_json()
    persona_key = data.get('persona_key')
    
    if not persona_key or persona_key not in persona_configs:
        return jsonify({'error': 'کلید شخصیت نامعتبر است.'}), 400
        
    global user_personas, chat_sessions
    
    # 1. به‌روزرسانی شخصیت برای آیدی ثابت وب
    user_personas[USER_ID_FOR_WEB] = persona_key
    
    # 2. ریست کردن سشن چت (با تغییر شخصیت، تاریخچه پاک می‌شود)
    if USER_ID_FOR_WEB in chat_sessions:
        del chat_sessions[USER_ID_FOR_WEB]
        
    logger.info(f"Persona for web user (ID {USER_ID_FOR_WEB}) set to: {persona_key}")
    
    return jsonify({
        'status': 'success',
        'message': f"شخصیت با موفقیت به '{persona_configs[persona_key].get('name', persona_key)}' تغییر کرد. چت ریست شد.",
        'new_persona_name': persona_configs[persona_key].get('name', persona_key)
    })

# --- 💬 درگاه چت ---

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    """درِ ورودی اصلی: پیام کاربر را می‌گیرد و پاسخ Gemini را برمی‌گرداند."""
    
    if not request.is_json:
        return jsonify({"error": "باید پیام را به صورت JSON بفرستید."}), 400

    data = request.get_json()
    user_message = data.get('message')
    
    if not user_message:
        return jsonify({'response': 'لطفاً پیامی ارسال کنید.'}), 400

    chat = get_chat_session(USER_ID_FOR_WEB) 
    if not chat:
        return jsonify({'response': '❌ خطای اتصال به Gemini.'}), 500
        
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
    try:
        return app.send_static_file('index.html') 
    except Exception:
        return "صفحه چت (index.html) پیدا نشد. مطمئن شوید در کنار web_app.py قرار دارد.", 404

# -----------------------------------------------
# --- 🚀 تابع اصلی برای اجرا ---
# -----------------------------------------------

if __name__ == '__main__':
    load_personas_from_file()
    app.run(host='0.0.0.0', port=5000, debug=True)