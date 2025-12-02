import os
import logging
import asyncio
import json
import io
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone


# --- 🚀 وابستگی‌های اضافی ---
from dotenv import load_dotenv
from PIL import Image

# --- 🧠 وابستگی‌های جیمینای ---
from google import genai
from google.genai import types

from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember, ReplyKeyboardMarkup, KeyboardButton
# 🟢 فیکس: اضافه کردن import برای مدیریت خطای رایج تلگرام
from telegram.error import BadRequest, TelegramError # 👈🏻 TelegramError را اضافه کردیم
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

# 🟢 دستور چاپ برای اشکال‌زدایی فوری در Railway
print("--- 🟢 Railway Initialization Check: Starting main.py Process ---")


# --- 🔒 تنظیمات و توکن‌ها (خوانده شده از .env شما) ---

BOT_TOKEN: str = os.getenv("BOT_TOKEN", os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN"))
GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINIAPIKEY")

admin_id_str = os.getenv("ADMIN_USER_ID", "")
# 💡 فیکس: تبدیل مطمئن ADMIN_USER_ID به لیست اعداد صحیح
ADMIN_IDS: List[int] = [int(i.strip()) for i in admin_id_str.split(',') if i.strip().isdigit()]


# ⚠️ اگر کلید جیمینای موجود نباشد، ربات اجرا نخواهد شد.
if not GEMINI_API_KEY:
    logger.error("❌ GEMINI_API_KEY در متغیرهای محیطی یافت نشد. ربات نمی‌تواند اجرا شود.")
    # 🟢 چاپ نهایی برای اشکال‌زدایی
    print("--- ❌ CRITICAL ERROR: GEMINI_API_KEY Missing ---") 
    # raise ValueError("GEMINI_API_KEY Missing") # اگر بخواهید فوراً کرش کنید.
# ... (بقیه کدهای تابع notify_admin_of_message و توابع دیگر که در کد قبلی داشتید) ...
# ... (توجه: من کل کد شما را ندارم، مطمئن شوید که تمام توابع قبلی را حفظ کرده‌اید.) ...

# 🟢 تابع notify_admin_of_message (برای اطمینان از صحت)
async def notify_admin_of_message(message: str, context: ContextTypes.DEFAULT_TYPE, chat_id: Optional[int] = None) -> None:
    """ارسال پیام نظارتی به تمام ادمین‌های لیست شده."""
    if not ADMIN_IDS:
        logger.warning("ADMIN_USER_ID تنظیم نشده است.")
        return

    # 🟢 چاپ برای اشکال‌زدایی
    print(f"--- 🟢 Trying to send log to {ADMIN_IDS} ---")

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except BadRequest as e:
            # این خطا معمولاً به دلیل مسدود کردن ربات توسط کاربر است
            logger.error(f"Error sending log to admin {admin_id}: {e}")
            # 🟢 چاپ خطا
            print(f"--- 💥 Telegram Error: BadRequest to {admin_id} ({e}) ---")
        except TelegramError as e:
            # سایر خطاهای تلگرام
            logger.error(f"General Telegram Error sending log to admin {admin_id}: {e}")
            # 🟢 چاپ خطا
            print(f"--- 💥 General Telegram Error to {admin_id} ({e}) ---")
        except Exception as e:
            logger.error(f"Unknown error notifying admin {admin_id}: {e}")
            # 🟢 چاپ خطا
            print(f"--- 💥 Unknown Error to {admin_id} ({e}) ---")


# ... (تمام توابع هندلر مثل handle_start، handle_gemini_message، و غیره باید اینجا باشند) ...


def main() -> None:
    """شروع به اجرای ربات (Polling) می‌کند."""

    # 🟢 چاپ برای اشکال‌زدایی
    print(f"--- 🔑 BOT_TOKEN status: {'Set' if BOT_TOKEN else 'Missing'} ---")
    print(f"--- 🔑 ADMIN_IDS count: {len(ADMIN_IDS)} ---")
    
    try:
        # 1. ساخت Application (اینجا ممکن است به دلیل توکن اشتباه کرش کند)
        application = Application.builder().token(BOT_TOKEN).build()
    except Exception as e:
        # اگر مشکلی در توکن یا ساخت Application بود، اینجا چاپ می‌شود.
        print(f"--- 💥 CRITICAL ERROR in Application Build: {e} ---")
        logger.error(f"CRITICAL ERROR in Application Build: {e}")
        return # پایان برنامه

    # 2. ثبت هندلرها
    # ... (تمام خطوط application.add_handler(...) شما باید اینجا باشند) ...

    # 4. شروع Polling
    logger.info("Telebot has started polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
