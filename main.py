#!/usr/bin/env python3
"""
Currency32 Converter Bot - A Telegram bot for real-time currency conversion
Deployed on Railway with GitHub
"""

import os
import sys
import logging
import re
import json
from datetime import datetime
from typing import Dict, Optional, Tuple

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

# Get bot token from environment variable (set in Railway)
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    logging.error("❌ TELEGRAM_TOKEN not set in environment variables!")
    sys.exit(1)

# Free API for exchange rates (no API key required)
EXCHANGE_API_URL = "https://api.exchangerate-api.com/v4/latest/"

# Fallback API if primary fails
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

# Supported currencies with symbols
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

def get_currency_list() -> str:
    """Generate formatted list of supported currencies."""
    lines = ["🌍 **Supported Currencies:**\n"]
    for i, (code, name) in enumerate(sorted(CURRENCIES.items()), 1):
        lines.append(f"{i:2}. `{code}` - {name}")
    lines.append("\n💡 Type `100 USD to EUR` for quick conversion!")
    return "\n".join(lines)


async def fetch_exchange_rates(base_currency: str) -> Optional[Dict]:
    """
    Fetch exchange rates from API with fallback.
    Returns dict with rates or None if failed.
    """
    try:
        # Primary API (ExchangeRate-API)
        response = requests.get(
            f"{EXCHANGE_API_URL}{base_currency}",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if "rates" in data:
                logger.info(f"✅ Rates fetched successfully for {base_currency}")
                return data

        # Fallback API (Frankfurter)
        logger.warning(f"⚠️ Primary API failed, trying fallback for {base_currency}")
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

    except requests.exceptions.Timeout:
        logger.error(f"⏰ Timeout fetching rates for {base_currency}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"🌐 Network error: {e}")
        return None
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        return None


async def perform_conversion(
    amount: float,
    from_currency: str,
    to_currency: str
) -> str:
    """
    Perform currency conversion and return formatted result.
    """
    try:
        data = await fetch_exchange_rates(from_currency)
        if not data:
            return "❌ Sorry, I'm having trouble fetching exchange rates. Please try again later."

        rate = data["rates"].get(to_currency)
        if not rate:
            return f"❌ Sorry, I couldn't find the rate for {to_currency}."

        converted_amount = amount * rate
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        result = f"""
💱 **Currency Conversion**

💰 {amount:,.2f} {from_currency} = **{converted_amount:,.2f} {to_currency}**

📊 **Exchange Rate:** 1 {from_currency} = {rate:.4f} {to_currency}
📈 1 {to_currency} = {(1/rate):.4f} {from_currency}

🕐 Updated: {timestamp}

_Powered by ExchangeRate-API_
"""
        return result

    except Exception as e:
        logger.error(f"Conversion error: {e}")
        return "❌ An error occurred during conversion. Please try again."


def create_currency_keyboard(callback_prefix: str, include_cancel: bool = True) -> InlineKeyboardMarkup:
    """Create a paginated keyboard for currency selection."""
    keyboard = []
    row = []
    
    for code, name in sorted(CURRENCIES.items()):
        # Shorten the display name for buttons
        display = f"{code} {name[:10]}..." if len(name) > 10 else f"{code} {name}"
        row.append(InlineKeyboardButton(display, callback_data=f"{callback_prefix}_{code}"))
        if len(row) == 2:  # 2 buttons per row for better readability
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    if include_cancel:
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== COMMAND HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    welcome_message = f"""
👋 **Welcome, {user.first_name}!** 

I'm **Currency32 Converter Bot** - your instant currency conversion companion!

🌟 **Features:**
• Convert between 30+ world currencies
• Real-time exchange rates
• Interactive conversion with buttons
• Quick conversion via simple text

📌 **Quick Start:**
Just type: `100 USD to EUR` or `50 GBP in NGN`

🚀 **Commands:**
/convert - Interactive conversion
/rate - Check exchange rate
/currencies - List all currencies
/help - Show all commands

Let's convert! 💱
"""
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = """
📖 **Help & Commands**

**Basic Commands:**
/start - Start the bot
/help - Show this help
/convert - Start interactive conversion
/rate USD EUR - Check exchange rate
/currencies - List all supported currencies
/about - About this bot

**Quick Conversion:**
Just type a message like:
• `100 USD to EUR`
• `2500 JPY in NGN`
• `50 GBP to USD`

**Interactive Mode:**
1. Type /convert
2. Set the amount
3. Choose 'From' currency
4. Choose 'To' currency
5. Click 'Convert Now'

**Inline Mode:**
Type `@currency32converterbot 100 USD to EUR` in any chat!

💡 **Pro Tip:** The bot works in groups too!
"""
    await update.message.reply_text(help_text)


async def currencies_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /currencies command."""
    await update.message.reply_text(get_currency_list())


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /about command."""
    about_text = """
💱 **Currency32 Converter Bot**

• **Version:** 1.0.0
• **Created:** 2026
• **APIs:** ExchangeRate-API & Frankfurter
• **Languages:** Python 3.11
• **Platform:** Telegram & Railway

**Features:**
✅ 30+ currencies supported
✅ Real-time rates
✅ Interactive interface
✅ Quick text conversion
✅ Group chat support

**Source Code:** GitHub
**Developer:** @YourUsername

_Made with ❤️ for the Telegram community_
"""
    await update.message.reply_text(about_text)


async def convert_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /convert command - start interactive conversion."""
    keyboard = [
        [InlineKeyboardButton("💰 Set Amount", callback_data="set_amount")],
        [InlineKeyboardButton("🔁 From Currency", callback_data="from_currency")],
        [InlineKeyboardButton("🎯 To Currency", callback_data="to_currency")],
        [InlineKeyboardButton("🔄 Convert Now!", callback_data="convert_now")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🔧 **Interactive Converter**\n\n"
        "Follow these steps:\n"
        "1️⃣ Click 'Set Amount' and enter a number\n"
        "2️⃣ Choose 'From Currency'\n"
        "3️⃣ Choose 'To Currency'\n"
        "4️⃣ Click 'Convert Now!'\n\n"
        "Your selection will be saved as you go!",
        reply_markup=reply_markup,
    )


async def rate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /rate command - check exchange rate."""
    args = context.args

    if len(args) != 2:
        await update.message.reply_text(
            "📊 **Check Exchange Rate**\n\n"
            "Usage: `/rate USD EUR`\n"
            "Example: `/rate USD NGN`\n\n"
            "📋 Get currency list with /currencies"
        )
        return

    from_curr = args[0].upper()
    to_curr = args[1].upper()

    if from_curr not in CURRENCIES:
        await update.message.reply_text(f"❌ '{from_curr}' is not supported. Use /currencies to see all.")
        return
    if to_curr not in CURRENCIES:
        await update.message.reply_text(f"❌ '{to_curr}' is not supported. Use /currencies to see all.")
        return

    data = await fetch_exchange_rates(from_curr)
    if not data:
        await update.message.reply_text("❌ Error fetching rates. Please try again.")
        return

    rate = data["rates"].get(to_curr)
    if not rate:
        await update.message.reply_text(f"❌ Could not find rate for {to_curr}.")
        return

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    result = f"""
📊 **Exchange Rate**

1 {from_curr} = **{rate:.4f} {to_curr}**
1 {to_curr} = **{(1/rate):.4f} {from_curr}**

🕐 Updated: {timestamp}
"""
    await update.message.reply_text(result)


# ==================== CALLBACK HANDLERS ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data

    # Initialize user data if not exists
    if "conversion" not in context.user_data:
        context.user_data["conversion"] = {}

    conversion = context.user_data["conversion"]

    # Handle cancel
    if data == "cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Conversion cancelled. Type /convert to start again.")
        return

    # Handle amount
    if data == "set_amount":
        await query.edit_message_text(
            "💵 **Enter the amount**\n\n"
            "Please type the amount you want to convert.\n"
            "Example: `100` or `1500.50`\n\n"
            "Type /cancel to abort."
        )
        conversion["waiting_for"] = "amount"
        return

    # Handle from currency selection
    if data == "from_currency":
        keyboard = create_currency_keyboard("from")
        await query.edit_message_text(
            "🔁 **Select 'From' Currency**\n\n"
            "Choose the currency you want to convert **FROM**:",
            reply_markup=keyboard,
        )
        return

    # Handle to currency selection
    if data == "to_currency":
        keyboard = create_currency_keyboard("to")
        await query.edit_message_text(
            "🎯 **Select 'To' Currency**\n\n"
            "Choose the currency you want to convert **TO**:",
            reply_markup=keyboard,
        )
        return

    # Handle from_ currency selection
    if data.startswith("from_"):
        code = data.replace("from_", "")
        conversion["from_currency"] = code
        await query.edit_message_text(
            f"✅ **From Currency Set:** {CURRENCIES[code]}\n\n"
            f"Now set the 'To' currency or click 'Convert Now!'.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎯 To Currency", callback_data="to_currency")],
                [InlineKeyboardButton("🔄 Convert Now!", callback_data="convert_now")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
            ]),
        )
        return

    # Handle to_ currency selection
    if data.startswith("to_"):
        code = data.replace("to_", "")
        conversion["to_currency"] = code
        await query.edit_message_text(
            f"✅ **To Currency Set:** {CURRENCIES[code]}\n\n"
            f"Now set the amount or click 'Convert Now!'.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Set Amount", callback_data="set_amount")],
                [InlineKeyboardButton("🔄 Convert Now!", callback_data="convert_now")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
            ]),
        )
        return

    # Handle convert now
    if data == "convert_now":
        amount = conversion.get("amount")
        from_curr = conversion.get("from_currency")
        to_curr = conversion.get("to_currency")

        # Validate all fields are set
        if not amount:
            await query.edit_message_text(
                "⚠️ **Amount not set!**\n\n"
                "Click 'Set Amount' and enter a number.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 Set Amount", callback_data="set_amount")],
                    [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
                ]),
            )
            return

        if not from_curr:
            await query.edit_message_text(
                "⚠️ **'From' Currency not set!**\n\n"
                "Click 'From Currency' to select one.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔁 From Currency", callback_data="from_currency")],
                    [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
                ]),
            )
            return

        if not to_curr:
            await query.edit_message_text(
                "⚠️ **'To' Currency not set!**\n\n"
                "Click 'To Currency' to select one.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎯 To Currency", callback_data="to_currency")],
                    [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
                ]),
            )
            return

        # Perform the conversion
        result = await perform_conversion(amount, from_curr, to_curr)
        await query.edit_message_text(result)

        # Clear conversion data after successful conversion
        context.user_data.clear()
        return


# ==================== MESSAGE HANDLER ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages."""
    text = update.message.text.strip()
    user_id = update.effective_user.id

    # Check if we're waiting for amount input
    conversion = context.user_data.get("conversion", {})
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
                f"Now select the currencies and click 'Convert Now!'.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔁 From Currency", callback_data="from_currency")],
                    [InlineKeyboardButton("🎯 To Currency", callback_data="to_currency")],
                    [InlineKeyboardButton("🔄 Convert Now!", callback_data="convert_now")],
                    [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
                ]),
            )
            return

        except ValueError:
            await update.message.reply_text(
                "❌ Please enter a valid number.\n"
                "Example: `100` or `1500.50`\n\n"
                "Type /cancel to abort."
            )
            return

    # Check for quick conversion pattern: "100 USD to EUR" or "100 USD in EUR"
    pattern = r"^(\d+\.?\d*)\s+([A-Z]{3})\s+(?:to|in)\s+([A-Z]{3})$"
    match = re.match(pattern, text.upper())

    if match:
        amount = float(match.group(1))
        from_curr = match.group(2)
        to_curr = match.group(3)

        if from_curr not in CURRENCIES:
            await update.message.reply_text(
                f"❌ '{from_curr}' is not supported.\n"
                f"Use /currencies to see all supported currencies."
            )
            return

        if to_curr not in CURRENCIES:
            await update.message.reply_text(
                f"❌ '{to_curr}' is not supported.\n"
                f"Use /currencies to see all supported currencies."
            )
            return

        result = await perform_conversion(amount, from_curr, to_curr)
        await update.message.reply_text(result)
        return

    # If not a command and not in interactive mode, suggest commands
    if not text.startswith("/"):
        await update.message.reply_text(
            "🤔 **I didn't understand that.**\n\n"
            "💡 Try these formats:\n"
            "• `100 USD to EUR`\n"
            "• `2500 JPY in NGN`\n"
            "• /convert for interactive mode\n"
            "• /help for all commands\n\n"
            "📚 Use /currencies to see all supported currencies."
        )


# ==================== ERROR HANDLER ====================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the bot."""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ **Something went wrong!**\n\n"
            "Please try again later. If the problem persists, contact the developer."
        )


# ==================== MAIN FUNCTION ====================

def main() -> None:
    """Main entry point for the bot."""
    logger.info("🚀 Starting Currency32 Converter Bot...")
    logger.info(f"📊 {len(CURRENCIES)} currencies supported")
    logger.info(f"🔑 Token: {TOKEN[:10]}...{TOKEN[-5:]}")

    try:
        # Create the Application
        application = Application.builder().token(TOKEN).build()

        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("currencies", currencies_command))
        application.add_handler(CommandHandler("about", about_command))
        application.add_handler(CommandHandler("convert", convert_start))
        application.add_handler(CommandHandler("rate", rate_command))

        # Add callback query handler
        application.add_handler(CallbackQueryHandler(button_callback))

        # Add message handler for text messages (excluding commands)
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )

        # Add error handler
        application.add_error_handler(error_handler)

        # Start the bot
        logger.info("✅ Bot is running and waiting for messages...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
