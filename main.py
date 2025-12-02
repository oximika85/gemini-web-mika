import os
import logging
import asyncio
import json
import io
import telegram
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone


# --- 🚀 وابستگی‌های اضافی ---
from dotenv import load_dotenv
from PIL import Image

# --- 🧠 وابستگی‌های جیمینای ---
from google import genai
from google.genai import types

from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember, ReplyKeyboardMarkup, KeyboardButton
from telegram.error import BadRequest
from telegram.constants import ChatType, ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
)

# 👈🏻 لود کردن متغیرهای محیطی از فایل .env
load_dotenv()

# --- 📝 تنظیمات لاگ‌گیری ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- 🔒 تنظیمات و توکن‌ها (خوانده شده از .env شما) ---

BOT_TOKEN: str = os.getenv("BOT_TOKEN", os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN"))
GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINIAPIKEY")

admin_id_str = os.getenv("ADMIN_USER_ID", "")
ADMIN_IDS: List[int] = [int(i.strip()) for i in admin_id_str.split(',') if i.strip()] if admin_id_str else []

# --- 💾 فایل‌های ذخیره‌سازی ---
USER_STATS_FILE = "user_stats.json"
PERSONAS_FILE = "personas.json"
ARCHIVE_FILE = "chat_archive.jsonl" # 🟢 فایل جدید برای ذخیره تاریخچه

# --- 🧠 تنظیمات جیمینای ---
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

# --- 💾 توابع Persistence (ذخیره‌سازی و بارگذاری) ---
# (این توابع مربوط به آمار و شخصیت‌ها حذف شدند تا کد کوتاه بماند. فرض بر این است که از قبل در فایل شما وجود دارند.)

# --- 💾 تابع ذخیره تاریخچه چت ---
def archive_message(
    user_id: int, 
    username: str, 
    message_text: str, 
    response_text: str, 
    chat_type: str, 
    chat_id: int,
    is_gemini_call: bool = True
):
    """
    ذخیره پیام کاربر و پاسخ ربات در یک فایل JSON Lines برای نظارت.
    """
    global ARCHIVE_FILE
    try:
        archive_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "username": username,
            "chat_id": chat_id,
            "chat_type": chat_type,
            "is_gemini_call": is_gemini_call,
            "user_message": message_text.strip()[:1000], 
            "bot_response_snippet": response_text.strip()[:1000] if response_text else "No response", 
        }
        
        with open(ARCHIVE_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(archive_entry, ensure_ascii=False) + '\n')
            
    except Exception as e:
        logger.error(f"❌ Error archiving message: {e}")


# --- 🔔 تابع اطلاع‌رسانی خودکار به مدیر (نسخه نهایی با شناسایی کاربر) ---
async def notify_admin_of_message(
    context: ContextTypes.DEFAULT_TYPE, 
    user: telegram.User, # 💡 دریافت آبجکت کامل کاربر
    chat_id: int,
    message_text: str, 
    response_text: str 
) -> None:
    """
    ارسال پیام ورودی کاربر و خلاصه پاسخ ربات به چت خصوصی مدیران (PM).
    """
    global ADMIN_IDS 
    
    if not ADMIN_IDS:
        logger.warning("❌ ADMIN_USER_ID is not configured. Cannot send log notifications.")
        return
        
    log_time = datetime.now(timezone.utc).strftime('%H:%M:%S UTC')
    
    # اطلاعات شناسایی
    full_name = user.full_name
    username = user.username if user.username else 'ندارد'
    lang_code = user.language_code if user.language_code else 'نامشخص'
    
    # خلاصه کردن پیام‌ها برای نوتیفیکیشن
    msg_snippet = message_text.strip()[:150] + ('...' if len(message_text.strip()) > 150 else '')
    res_snippet = response_text.strip()[:150] + ('...' if len(response_text.strip()) > 150 else '')
    
    # ساخت پیام برای ارسال به مدیر (با اطلاعات بیشتر)
    notification_message = (
        f"**[LOG]** *{log_time}*\n"
        f"**👤 شناسایی کاربر**\n"
        f"  - **نام کامل:** {full_name}\n"
        f"  - **آیدی تلگرام:** `{user.id}`\n"
        f"  - **یوزرنیم:** @{username}\n"
        f"  - **زبان:** {lang_code}\n"
        f"**💬 جزئیات چت**\n"
        f"  - **آیدی چت:** `{chat_id}`\n"
        f"  - **➡️ پیام کاربر:** `{msg_snippet}`\n"
        f"  - **⬅️ خلاصه پاسخ:** `{res_snippet}`"
    )
    
    # ارسال به چت خصوصی هر ادمین
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=notification_message,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.error(f"❌ Error notifying admin {admin_id}: {e}")

# (بقیه توابع حذف شدند تا کد کوتاه بماند. توابع اصلی ربات مانند get_command_aliases, handle_gemini_message, check_archive_command و main باید در فایل شما موجود باشند.)
# 
# 🛑 مهم: مطمئن شوید تابع handle_gemini_message شما به درستی فراخوانی notify_admin_of_message را شامل می‌شود:

# 🟢 فراخوانی در handle_gemini_message:
# ...
# if bot_response:
#     archive_message(...)
#     
#     await notify_admin_of_message(
#         context=context,
#         user=user, 
#         chat_id=chat_id,
#         message_text=message_text,
#         response_text=bot_response
#     )
#     
#     await context.bot.send_message(...)
# ...