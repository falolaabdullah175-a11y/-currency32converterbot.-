import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import requests
import json
from datetime import datetime

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment variable (set this in Railway)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("No TELEGRAM_TOKEN found in environment variables!")

# Free API for exchange rates (no API key required)
EXCHANGE_API_URL = "https://api.exchangerate-api.com/v4/latest/"

# Supported currencies with symbols
CURRENCIES = {
    'USD': '🇺🇸 US Dollar',
    'EUR': '🇪🇺 Euro',
    'GBP': '🇬🇧 British Pound',
    'JPY': '🇯🇵 Japanese Yen',
    'INR': '🇮🇳 Indian Rupee',
    'CNY': '🇨🇳 Chinese Yuan',
    'BRL': '🇧🇷 Brazilian Real',
    'CAD': '🇨🇦 Canadian Dollar',
    'AUD': '🇦🇺 Australian Dollar',
    'CHF': '🇨🇭 Swiss Franc',
    'SGD': '🇸🇬 Singapore Dollar',
    'NZD': '🇳🇿 New Zealand Dollar',
    'KRW': '🇰🇷 South Korean Won',
    'RUB': '🇷🇺 Russian Ruble',
    'ZAR': '🇿🇦 South African Rand',
    'NGN': '🇳🇬 Nigerian Naira',
    'KES': '🇰🇪 Kenyan Shilling',
    'EGP': '🇪🇬 Egyptian Pound',
    'MXN': '🇲🇽 Mexican Peso',
    'AED': '🇦🇪 UAE Dirham'
}

# Store user's selected currencies temporarily (in memory - will reset on restart)
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued."""
    user = update.effective_user
    welcome_message = f"""
👋 Welcome, {user.first_name}! 

I'm your Currency Converter Bot!
I can help you convert between 20+ world currencies instantly.

📌 **How to use me:**
• Type /convert to start a conversion
• Or directly type: `100 USD to EUR`
• Use /currencies to see all supported currencies
• Use /help for more commands

Let's convert! 🚀
"""
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message."""
    help_text = """
📖 **Help & Commands**

• /start - Start the bot
• /help - Show this help message
• /convert - Start an interactive conversion
• /currencies - List all supported currencies
• /rate - Check exchange rate between two currencies
• /about - About this bot

**Quick Conversion:**
Just type a message like:
`100 USD to EUR`
`2500 JPY in USD`
`50 GBP to NGN`

**Pro tip:** You can also use the inline mode by typing:
`@currency32converterbot 100 USD to EUR`
in any chat!
"""
    await update.message.reply_text(help_text)

async def currencies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all supported currencies."""
    currency_list = "🌍 **Supported Currencies:**\n\n"
    for code, name in CURRENCIES.items():
        currency_list += f"• `{code}` - {name}\n"
    
    currency_list += "\n\nTo convert, type: `100 USD to EUR`"
    await update.message.reply_text(currency_list)

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """About the bot."""
    about_text = """
💱 **Currency32 Converter Bot**

• Version: 1.0.0
• Powered by ExchangeRate-API
• Free to use • No limits
• Live exchange rates

**Developed with ❤️ using Python & Telegram Bot API**

Source code available on GitHub.
"""
    await update.message.reply_text(about_text)

async def convert_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start interactive conversion."""
    keyboard = [
        [InlineKeyboardButton("💰 Amount", callback_data='amount')],
        [InlineKeyboardButton("🔁 From Currency", callback_data='from_currency')],
        [InlineKeyboardButton("🎯 To Currency", callback_data='to_currency')],
        [InlineKeyboardButton("🔄 Convert Now", callback_data='convert_now')],
        [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔧 **Interactive Converter**\n\n"
        "Select an option below to set up your conversion:\n"
        "1️⃣ Set the amount\n"
        "2️⃣ Choose 'From' currency\n"
        "3️⃣ Choose 'To' currency\n"
        "4️⃣ Click 'Convert Now'",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'cancel':
        await query.edit_message_text("❌ Conversion cancelled. Type /convert to start again.")
        return
    
    elif query.data == 'amount':
        await query.edit_message_text(
            "💵 Please enter the amount you want to convert.\n"
            "Example: `100` or `1500.50`"
        )
        context.user_data['waiting_for'] = 'amount'
        
    elif query.data == 'from_currency':
        keyboard = []
        row = []
        for i, (code, name) in enumerate(CURRENCIES.items()):
            row.append(InlineKeyboardButton(code, callback_data=f'from_{code}'))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data='cancel')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔁 Select the currency you want to convert **FROM**:",
            reply_markup=reply_markup
        )
        
    elif query.data == 'to_currency':
        keyboard = []
        row = []
        for i, (code, name) in enumerate(CURRENCIES.items()):
            row.append(InlineKeyboardButton(code, callback_data=f'to_{code}'))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data='cancel')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎯 Select the currency you want to convert **TO**:",
            reply_markup=reply_markup
        )
        
    elif query.data.startswith('from_'):
        code = query.data.replace('from_', '')
        context.user_data['from_currency'] = code
        await query.edit_message_text(
            f"✅ **From Currency Set:** {CURRENCIES[code]}\n\n"
            f"Now set the 'To' currency or click 'Convert Now'."
        )
        
    elif query.data.startswith('to_'):
        code = query.data.replace('to_', '')
        context.user_data['to_currency'] = code
        await query.edit_message_text(
            f"✅ **To Currency Set:** {CURRENCIES[code]}\n\n"
            f"Now set the amount or click 'Convert Now'."
        )
        
    elif query.data == 'convert_now':
        amount = context.user_data.get('amount')
        from_curr = context.user_data.get('from_currency')
        to_curr = context.user_data.get('to_currency')
        
        if not amount:
            await query.edit_message_text("⚠️ Please set the amount first!")
            return
        if not from_curr:
            await query.edit_message_text("⚠️ Please select the 'From' currency first!")
            return
        if not to_curr:
            await query.edit_message_text("⚠️ Please select the 'To' currency first!")
            return
            
        # Perform conversion
        result = await perform_conversion(amount, from_curr, to_curr)
        await query.edit_message_text(result)
        
        # Clear user data
        context.user_data.clear()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages for quick conversion."""
    text = update.message.text.strip()
    
    # Check if user is in interactive mode
    if context.user_data.get('waiting_for') == 'amount':
        try:
            amount = float(text)
            context.user_data['amount'] = amount
            context.user_data['waiting_for'] = None
            
            keyboard = [
                [InlineKeyboardButton("🔁 From Currency", callback_data='from_currency')],
                [InlineKeyboardButton("🎯 To Currency", callback_data='to_currency')],
                [InlineKeyboardButton("🔄 Convert Now", callback_data='convert_now')],
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ Amount set: **{amount}**\n\n"
                f"Now select the currencies and click 'Convert Now'.",
                reply_markup=reply_markup
            )
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number (e.g., 100 or 1500.50)")
        return
    
    # Check for quick conversion pattern: "100 USD to EUR" or "100 USD in EUR"
    import re
    pattern = r'^(\d+\.?\d*)\s+([A-Z]{3})\s+(?:to|in)\s+([A-Z]{3})$'
    match = re.match(pattern, text.upper())
    
    if match:
        amount = float(match.group(1))
        from_curr = match.group(2)
        to_curr = match.group(3)
        
        if from_curr not in CURRENCIES:
            await update.message.reply_text(f"❌ '{from_curr}' is not supported. Use /currencies to see all.")
            return
        if to_curr not in CURRENCIES:
            await update.message.reply_text(f"❌ '{to_curr}' is not supported. Use /currencies to see all.")
            return
            
        result = await perform_conversion(amount, from_curr, to_curr)
        await update.message.reply_text(result)
    else:
        # If not a command and not in interactive mode, suggest commands
        await update.message.reply_text(
            "🤔 I didn't understand that.\n\n"
            "Try these formats:\n"
            "• `100 USD to EUR`\n"
            "• `2500 JPY in NGN`\n"
            "• /convert for interactive mode\n"
            "• /help for all commands"
        )

async def perform_conversion(amount, from_curr, to_curr):
    """Perform the actual currency conversion using API."""
    try:
        # Get exchange rates
        response = requests.get(f"{EXCHANGE_API_URL}{from_curr}")
        data = response.json()
        
        if response.status_code != 200:
            return "❌ Sorry, I'm having trouble fetching exchange rates. Please try again later."
        
        rate = data['rates'].get(to_curr)
        if not rate:
            return f"❌ Sorry, I couldn't find the rate for {to_curr}."
        
        converted_amount = amount * rate
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
        
        result = f"""
💱 **Currency Conversion**

💰 {amount:,.2f} {from_curr} = **{converted_amount:,.2f} {to_curr}**

📊 **Exchange Rate:** 1 {from_curr} = {rate:.4f} {to_curr}

🕐 Updated: {timestamp}

Powered by ExchangeRate-API
"""
        return result
        
    except requests.exceptions.RequestException:
        return "❌ Network error. Please check your connection and try again."
    except Exception as e:
        logger.error(f"Conversion error: {e}")
        return "❌ An error occurred. Please try again later."

async def rate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show exchange rate between two currencies."""
    args = context.args
    
    if len(args) != 2:
        await update.message.reply_text(
            "📊 **Check Exchange Rate**\n\n"
            "Usage: `/rate USD EUR`\n"
            "Example: `/rate USD NGN`\n\n"
            "Get a list of currencies with /currencies"
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
    
    try:
        response = requests.get(f"{EXCHANGE_API_URL}{from_curr}")
        data = response.json()
        
        if response.status_code != 200:
            await update.message.reply_text("❌ Error fetching rates. Please try again.")
            return
            
        rate = data['rates'].get(to_curr)
        if not rate:
            await update.message.reply_text(f"❌ Could not find rate for {to_curr}.")
            return
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
        
        result = f"""
📊 **Exchange Rate**

1 {from_curr} = **{rate:.4f} {to_curr}**
1 {to_curr} = **{(1/rate):.4f} {from_curr}**

🕐 Updated: {timestamp}
"""
        await update.message.reply_text(result)
        
    except Exception as e:
        logger.error(f"Rate error: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("currencies", currencies))
    application.add_handler(CommandHandler("about", about))
    application.add_handler(CommandHandler("convert", convert_start))
    application.add_handler(CommandHandler("rate", rate_command))
    
    # Add callback query handler for buttons
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Add message handler for text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the Bot
    print("🤖 Currency32 Converter Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
