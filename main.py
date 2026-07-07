#!/usr/bin/env python3
"""
Currency32 Converter Bot - Telegram bot for currency conversion
Deployed on Railway
"""

import os
import sys
import logging
import re
from datetime import datetime
from typing import Dict, Optional
import asyncio

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ==================== CONFIGURATION ====================

# Get bot token from environment variable
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    logging.error("❌ TELEGRAM_TOKEN not set in environment variables!")
    logging.error("Please set TELEGRAM_TOKEN in Railway variables")
    sys.exit(1)

# API URLs
EXCHANGE_API_URL = "https://api.exchangerate-api.com/v4/latest/"
FALLBACK_API_URL = "https://api.frankfurter.app/latest?from="

# ==================== LOGGING ====================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ==================== DATA ====================

CURRENCIES = {
    "USD": "🇺🇸 US Dollar",
    "EUR": "🇪🇺 Euro",
    "GBP": "🇬🇧 British Pound",
    "JPY": "🇯🇵 Japanese Yen",
    "INR": "🇮🇳 Indian Rupee",
    "CNY": "🇨🇳 Chinese Yuan",
    "BRL": "🇧🇷 Brazilian Real",
    "CAD": "🇨🇦 Canadian Dollar",
    "AUD": "🇦🇺 Australian Dollar",
    "CHF": "🇨🇭 Swiss Franc",
    "SGD": "🇸🇬 Singapore Dollar",
    "NZD": "🇳🇿 New Zealand Dollar",
    "KRW": "🇰🇷 South Korean Won",
    "RUB": "🇷🇺 Russian Ruble",
    "ZAR": "🇿🇦 South African Rand",
    "NGN": "🇳🇬 Nigerian Naira",
    "KES": "🇰🇪 Kenyan Shilling",
    "EGP": "🇪🇬 Egyptian Pound",
    "MXN": "🇲🇽 Mexican Peso",
    "AED": "🇦🇪 UAE Dirham",
    "SAR": "🇸🇦 Saudi Riyal",
    "TRY": "🇹🇷 Turkish Lira",
    "THB": "🇹🇭 Thai Baht",
    "VND": "🇻🇳 Vietnamese Dong",
    "IDR": "🇮🇩 Indonesian Rupiah",
    "PHP": "🇵🇭 Philippine Peso",
    "MYR": "🇲🇾 Malaysian Ringgit",
}

# ==================== HELPER FUNCTIONS ====================

async def fetch_exchange_rates(base_currency: str) -> Optional[Dict]:
    """Fetch exchange rates from API with fallback."""
    try:
        # Primary API
        response = requests.get(
            f"{EXCHANGE_API_URL}{base_currency}",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if "rates" in data:
                logger.info(f"✅ Rates fetched for {base_currency}")
                return data

        # Fallback API
        logger.warning(f"⚠️ Trying fallback API for {base_currency}")
        response = requests.get(
            f"{FALLBACK_API_URL}{base_currency}",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if "rates" in data:
                logger.info(f"✅ Fallback rates fetched for {base_currency}")
                return data

        logger.error(f"❌ All APIs failed for {base_currency}")
        return None

    except Exception as e:
        logger.error(f"💥 API error: {e}")
        return None

async def perform_conversion(amount: float, from_curr: str, to_curr: str) -> str:
    """Perform currency conversion."""
    try:
        data = await fetch_exchange_rates(from_curr)
        if not data:
            return "❌ Sorry, I'm having trouble fetching exchange rates. Please try again later."

        rate = data["rates"].get(to_curr)
        if not rate:
            return f"❌ Sorry, I couldn't find the rate for {to_curr}."

        converted = amount * rate
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        return f"""
💱 **Currency Conversion**

💰 {amount:,.2f} {from_curr} = **{converted:,.2f} {to_curr}**

📊 Rate: 1 {from_curr} = {rate:.4f} {to_curr}
🕐 Updated: {timestamp}
"""
    except Exception as e:
        logger.error(f"Conversion error: {e}")
        return "❌ An error occurred. Please try again."

# ==================== COMMAND HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    welcome = f"""
👋 **Welcome, {user.first_name}!** 

I'm **Currency32 Converter Bot** - your instant currency conversion companion!

💡 **Quick usage:**
`100 USD to EUR`
`50 GBP in NGN`

📌 **Commands:**
/convert - Interactive conversion
/rate USD EUR - Check exchange rate
/currencies - List all currencies
/help - Show all commands

Let's convert! 💱
"""
    await update.message.reply_text(welcome)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = """
📖 **Help & Commands**

**Quick Conversion:**
• `100 USD to EUR`
• `2500 JPY in NGN`

**Commands:**
/start - Start the bot
/help - Show this help
/convert - Interactive conversion
/rate USD EUR - Check exchange rate
/currencies - List all currencies

**Interactive Mode:**
1. Type /convert
2. Set the amount
3. Choose currencies
4. Click 'Convert Now!'

💡 Works in groups too!
"""
    await update.message.reply_text(help_text)

async def currencies_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /currencies command."""
    text = "🌍 **Supported Currencies:**\n\n"
    for code, name in sorted(CURRENCIES.items()):
        text += f"• `{code}` - {name}\n"
    text += "\n💡 Type `100 USD to EUR` to convert!"
    await update.message.reply_text(text)

async def convert_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /convert command."""
    keyboard = [
        [InlineKeyboardButton("💰 Set Amount", callback_data="set_amount")],
        [InlineKeyboardButton("🔁 From Currency", callback_data="from_currency")],
        [InlineKeyboardButton("🎯 To Currency", callback_data="to_currency")],
        [InlineKeyboardButton("🔄 Convert Now!", callback_data="convert_now")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ]
    await update.message.reply_text(
        "🔧 **Interactive Converter**\n\n"
        "1️⃣ Click 'Set Amount'\n"
        "2️⃣ Choose currencies\n"
        "3️⃣ Click 'Convert Now!'",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def rate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /rate command."""
    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "📊 **Check Exchange Rate**\n\n"
            "Usage: `/rate USD EUR`\n"
            "Example: `/rate USD NGN`"
        )
        return

    from_curr = args[0].upper()
    to_curr = args[1].upper()

    if from_curr not in CURRENCIES or to_curr not in CURRENCIES:
        await update.message.reply_text("❌ Currency not supported. Use /currencies")
        return

    data = await fetch_exchange_rates(from_curr)
    if not data:
        await update.message.reply_text("❌ Error fetching rates. Please try again.")
        return

    rate = data["rates"].get(to_curr)
    if not rate:
        await update.message.reply_text(f"❌ Could not find rate for {to_curr}.")
        return

    await update.message.reply_text(
        f"📊 **Exchange Rate**\n\n"
        f"1 {from_curr} = **{rate:.4f} {to_curr}**\n"
        f"1 {to_curr} = **{(1/rate):.4f} {from_curr}**"
    )

# ==================== BUTTON HANDLERS ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button clicks."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    conversion = context.user_data.get("conversion", {})
    context.user_data["conversion"] = conversion

    if data == "cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Cancelled. Type /convert to start again.")
        return

    if data == "set_amount":
        conversion["waiting_for"] = "amount"
        await query.edit_message_text(
            "💵 **Enter the amount**\n\n"
            "Type a number like: `100` or `1500.50`"
        )
        return

    if data == "from_currency":
        keyboard = []
        row = []
        for code, name in sorted(CURRENCIES.items()):
            row.append(InlineKeyboardButton(code, callback_data=f"from_{code}"))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        await query.edit_message_text(
            "🔁 **Select 'From' Currency:**",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data == "to_currency":
        keyboard = []
        row = []
        for code, name in sorted(CURRENCIES.items()):
            row.append(InlineKeyboardButton(code, callback_data=f"to_{code}"))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        await query.edit_message_text(
            "🎯 **Select 'To' Currency:**",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data.startswith("from_"):
        code = data.replace("from_", "")
        conversion["from_currency"] = code
        await query.edit_message_text(
            f"✅ **From Currency Set:** {CURRENCIES[code]}\n\n"
            f"Now set 'To' currency or click 'Convert Now!'"
        )
        return

    if data.startswith("to_"):
        code = data.replace("to_", "")
        conversion["to_currency"] = code
        await query.edit_message_text(
            f"✅ **To Currency Set:** {CURRENCIES[code]}\n\n"
            f"Now click 'Convert Now!'"
        )
        return

    if data == "convert_now":
        amount = conversion.get("amount")
        from_curr = conversion.get("from_currency")
        to_curr = conversion.get("to_currency")

        if not amount:
            await query.edit_message_text("⚠️ Please set the amount first!")
            return
        if not from_curr:
            await query.edit_message_text("⚠️ Please select 'From' currency!")
            return
        if not to_curr:
            await query.edit_message_text("⚠️ Please select 'To' currency!")
            return

        result = await perform_conversion(amount, from_curr, to_curr)
        await query.edit_message_text(result)
        context.user_data.clear()

# ==================== MESSAGE HANDLER ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages."""
    text = update.message.text.strip()
    conversion = context.user_data.get("conversion", {})
    context.user_data["conversion"] = conversion

    # Handle amount input
    if conversion.get("waiting_for") == "amount":
        try:
            amount = float(text)
            if amount <= 0:
                await update.message.reply_text("❌ Please enter a positive number!")
                return
            conversion["amount"] = amount
            conversion["waiting_for"] = None
            await update.message.reply_text(
                f"✅ **Amount set:** {amount:,.2f}\n\n"
                f"Now select currencies and click 'Convert Now!'"
            )
            return
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number (e.g., 100 or 1500.50)")
            return

    # Quick conversion: "100 USD to EUR"
    pattern = r"^(\d+\.?\d*)\s+([A-Z]{3})\s+(?:to|in)\s+([A-Z]{3})$"
    match = re.match(pattern, text.upper())

    if match:
        amount = float(match.group(1))
        from_curr = match.group(2)
        to_curr = match.group(3)

        if from_curr not in CURRENCIES or to_curr not in CURRENCIES:
            await update.message.reply_text("❌ Currency not supported. Use /currencies")
            return

        result = await perform_conversion(amount, from_curr, to_curr)
        await update.message.reply_text(result)
        return

    # Default response
    await update.message.reply_text(
        "🤔 **I didn't understand that.**\n\n"
        "💡 Try: `100 USD to EUR`\n"
        "📚 Use /help for all commands"
    )

# ==================== MAIN ====================

def main():
    """Main entry point."""
    logger.info("🚀 Starting Currency32 Converter Bot...")
    logger.info(f"📊 {len(CURRENCIES)} currencies supported")
    logger.info(f"🔑 Token: {TOKEN[:10]}...{TOKEN[-5:]}")

    try:
        application = Application.builder().token(TOKEN).build()

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("currencies", currencies_command))
        application.add_handler(CommandHandler("convert", convert_start))
        application.add_handler(CommandHandler("rate", rate_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("✅ Bot is running...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
