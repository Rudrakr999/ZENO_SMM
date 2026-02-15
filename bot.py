import json
import os
import random
import time
import re
import asyncio
import urllib.parse
from datetime import datetime
import requests
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8263168035:AAEL3b6IDQKH4smftqrSYzwI96DM0JHSbJE"
ADMIN_ID = 7037961095
FORCE_CHANNEL = "@nomethod0"

# SERVER 1 - Fixed (With Refund)
SERVER1_API_URL = "https://mysmmprovider.com/api/v2"
SERVER1_API_KEY = "9cdc83908518bfcca287d839cf20b566"
SERVER1_MARKUP = 5

MARKUP_PERCENTAGE = 5
DATA_FILE = "smm_panel_data.json"
SERVICES_CACHE_DURATION = 7200
PAYMENT_GROUP = "@payment_gd18"

# States
ENTER_AMOUNT, ENTER_SERVICE_ID, ENTER_LINK, ENTER_QUANTITY, SUPPORT_MESSAGE, ADMIN_SET_UPI, ADMIN_MANAGE_BALANCE_ID, ADMIN_MANAGE_BALANCE_ACTION, ADMIN_MANAGE_BALANCE_AMOUNT, ADMIN_BAN_ID, ADMIN_BROADCAST_CONTENT, ADMIN_BROADCAST_BUTTON, ADMIN_REFUND_APPROVE, ENTER_PAYMENT_SCREENSHOT, ENTER_UTR = range(15)

CATEGORIES = {
    "search": "🔍 Search Service",
    "tg_members": "👥 Telegram Members",
    "tg_views": "👁 Telegram Views",
    "tg_views_future": "🔮 Telegram Views [Future]",
    "tg_views_last": "📌 Telegram Views [Last Post]",
    "tg_reaction": "❤️ Telegram Reaction",
    "ig_followers": "📸 Instagram Followers",
    "ig_views": "👀 Instagram Views",
    "ig_likes": "💗 Instagram Likes",
}

# ==================== DATA MANAGEMENT ====================
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                for key in ["banned_users", "bot_enabled", "payment_orders", "refund_requests", "manual_deposits", "force_channels", "server2_config"]:
                    if key not in data:
                        if key == "server2_config":
                            data[key] = {"api_url": "", "api_key": "", "markup": 5, "enabled": False}
                        elif key in ["banned_users", "refund_requests", "manual_deposits", "force_channels"]:
                            data[key] = []
                        elif key == "payment_orders":
                            data[key] = {}
                        else:
                            data[key] = True
                if not data.get("force_channels"):
                    data["force_channels"] = [FORCE_CHANNEL]
                return data
        except:
            pass
    return {"users": {}, "orders": {}, "deposits": {}, "banned_users": [], "services_cache_s1": [], "services_cache_s2": [], "cache_time_s1": 0, "cache_time_s2": 0, "upi_id": "", "order_counter": 1000, "deposit_counter": 1000, "bot_enabled": True, "payment_orders": {}, "refund_requests": [], "manual_deposits": [], "force_channels": [FORCE_CHANNEL], "server2_config": {"api_url": "", "api_key": "", "markup": 5, "enabled": False}}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_user_data(data, user_id):
    user_id = str(user_id)
    if user_id not in data["users"]:
        data["users"][user_id] = {"balance": 0.0, "orders": [], "deposits": [], "joined_date": datetime.now().isoformat()}
        save_data(data)
    return data["users"][user_id]

def is_banned(data, user_id):
    return str(user_id) in data.get("banned_users", [])

# ==================== SMM API ====================
def fetch_services(data, server="both"):
    current_time = time.time()
    
    # Server 1
    services_s1 = []
    if data.get("services_cache_s1") and (current_time - data.get("cache_time_s1", 0)) < SERVICES_CACHE_DURATION:
        services_s1 = data["services_cache_s1"]
    else:
        try:
            response = requests.post(SERVER1_API_URL, data={"key": SERVER1_API_KEY, "action": "services"}, timeout=10)
            if response.status_code == 200:
                services_s1 = response.json()
                data["services_cache_s1"] = services_s1
                data["cache_time_s1"] = current_time
                save_data(data)
        except:
            services_s1 = data.get("services_cache_s1", [])
    
    # Add server tag
    for s in services_s1:
        s['server'] = 1
        s['price_with_markup'] = float(s.get('rate', 0)) + SERVER1_MARKUP
    
    # Server 2
    services_s2 = []
    server2_config = data.get("server2_config", {})
    if server2_config.get("enabled") and server2_config.get("api_url") and server2_config.get("api_key"):
        if data.get("services_cache_s2") and (current_time - data.get("cache_time_s2", 0)) < SERVICES_CACHE_DURATION:
            services_s2 = data["services_cache_s2"]
        else:
            try:
                response = requests.post(server2_config["api_url"], data={"key": server2_config["api_key"], "action": "services"}, timeout=10)
                if response.status_code == 200:
                    services_s2 = response.json()
                    data["services_cache_s2"] = services_s2
                    data["cache_time_s2"] = current_time
                    save_data(data)
            except:
                services_s2 = data.get("services_cache_s2", [])
        
        for s in services_s2:
            s['server'] = 2
            s['price_with_markup'] = float(s.get('rate', 0)) + server2_config.get("markup", 5)
    
    if server == "1":
        return services_s1
    elif server == "2":
        return services_s2
    else:
        return services_s1 + services_s2

def place_order_api(service_id, link, quantity, server=1, data=None):
    try:
        if server == 1:
            api_url = SERVER1_API_URL
            api_key = SERVER1_API_KEY
        else:
            server2_config = data.get("server2_config", {})
            api_url = server2_config.get("api_url")
            api_key = server2_config.get("api_key")
        
        response = requests.post(api_url, data={"key": api_key, "action": "add", "service": service_id, "link": link, "quantity": quantity}, timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def check_order_status(order_id, server=1, data=None):
    try:
        if server == 1:
            api_url = SERVER1_API_URL
            api_key = SERVER1_API_KEY
        else:
            server2_config = data.get("server2_config", {})
            api_url = server2_config.get("api_url")
            api_key = server2_config.get("api_key")
        
        response = requests.post(api_url, data={"key": api_key, "action": "status", "order": order_id}, timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def cancel_order_api(order_id, server=1, data=None):
    try:
        if server == 1:
            api_url = SERVER1_API_URL
            api_key = SERVER1_API_KEY
        else:
            server2_config = data.get("server2_config", {})
            api_url = server2_config.get("api_url")
            api_key = server2_config.get("api_key")
        
        response = requests.post(api_url, data={"key": api_key, "action": "cancel", "order": order_id}, timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def search_services(query, services):
    results = []
    for service in services:
        if any(word in service.get('name', '').lower() or word in service.get('category', '').lower() for word in query.lower().split()):
            results.append(service)
    return results[:15]

# ==================== HELPERS ====================
async def check_channel_membership(update, context):
    try:
        data = load_data()
        force_channels = data.get("force_channels", [FORCE_CHANNEL])
        for channel in force_channels:
            try:
                member = await context.bot.get_chat_member(channel, update.effective_user.id)
                if member.status not in ['member', 'administrator', 'creator']:
                    return False
            except:
                return False
        return True
    except:
        return False

def get_main_menu_keyboard():
    return ReplyKeyboardMarkup([["🛒 New Order", "📂 Categories"], ["📦 Order History", "💰 Wallet"], ["💳 Add Funds", "🆘 Support"]], resize_keyboard=True)

def get_cancel_keyboard():
    return ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True)

# ==================== HANDLERS ====================
async def start(update, context):
    data = load_data()
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID and not data.get("bot_enabled", True):
        await update.message.reply_text("🚫 <b>Bot Temporarily Disabled</b>\n\nThe bot is under maintenance.\nWe'll be back soon!", parse_mode='HTML')
        return
    
    if is_banned(data, user_id):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return
    
    if not await check_channel_membership(update, context):
        force_channels = data.get("force_channels", [FORCE_CHANNEL])
        keyboard = []
        for idx, channel in enumerate(force_channels, 1):
            keyboard.append([InlineKeyboardButton(f"✅ Join Channel {idx}", url=f"https://t.me/{channel[1:]}")])
        keyboard.append([InlineKeyboardButton("✅ I Joined", callback_data="check_join")])
        channels_text = "\n".join([f"📢 {ch}" for ch in force_channels])
        await update.message.reply_text(f"⚠️ <b>Must Join Our Channel!</b>\n\n{channels_text}\n\nYou must join all channels to use this bot.\nClick 'Join Channel' buttons, then click 'I Joined'", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return
    
    get_user_data(data, user_id)
    
    welcome_msg = f"╔══════════════════════╗\n💎 SMM PANEL BOT 💎\n╚══════════════════════╝\n\n🌟 Welcome {update.effective_user.first_name}!\n\n📱 Boost Your Social Media\n🚀 Fast & Reliable Service\n💰 Competitive Prices\n🔒 100% Secure & Safe\n\nPowered by @ffzeno18"
    
    server2_enabled = data.get("server2_config", {}).get("enabled", False)
    
    keyboard = [[InlineKeyboardButton("🎯 Server 1 (Refund Available)", callback_data="select_server_1")]]
    if server2_enabled:
        keyboard.append([InlineKeyboardButton("⚡ Server 2 (No Refund)", callback_data="select_server_2")])
    
    await update.message.reply_text(welcome_msg + "\n\n<b>Select Server:</b>", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def select_server_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    server = query.data.replace("select_server_", "")
    context.user_data['selected_server'] = int(server)
    
    server_name = "Server 1 (Refund Available)" if server == "1" else "Server 2 (No Refund)"
    await query.edit_message_text(f"✅ <b>Selected: {server_name}</b>\n\nUse the menu below:", parse_mode='HTML')
    await query.message.reply_text("Use the buttons below:", reply_markup=get_main_menu_keyboard())

async def check_join_callback(update, context):
    query = update.callback_query
    await query.answer()
    if await check_channel_membership(update, context):
        await query.edit_message_text("✅ Verified! Use /start", parse_mode='HTML')
    else:
        await query.answer("❌ You haven't joined yet!", show_alert=True)

async def main_menu_handler(update, context):
    data = load_data()
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id != ADMIN_ID and not data.get("bot_enabled", True):
        await update.message.reply_text("🚫 <b>Bot Temporarily Disabled</b>\n\nThe bot is under maintenance.\nWe'll be back soon!", parse_mode='HTML')
        return ConversationHandler.END
    
    if is_banned(data, user_id):
        await update.message.reply_text("🚫 You are banned.")
        return ConversationHandler.END
    
    if not await check_channel_membership(update, context):
        force_channels = data.get("force_channels", [FORCE_CHANNEL])
        keyboard = []
        for idx, channel in enumerate(force_channels, 1):
            keyboard.append([InlineKeyboardButton(f"✅ Join Channel {idx}", url=f"https://t.me/{channel[1:]}")])
        keyboard.append([InlineKeyboardButton("✅ I Joined", callback_data="check_join")])
        channels_text = "\n".join([f"📢 {ch}" for ch in force_channels])
        await update.message.reply_text(f"⚠️ <b>Must Join Our Channel!</b>\n\n{channels_text}\n\nYou must join all channels to use this bot.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return ConversationHandler.END
    
    if text == "🛒 New Order":
        if not context.user_data.get('selected_server'):
            await update.message.reply_text("⚠️ Please use /start first to select server!", parse_mode='HTML')
            return ConversationHandler.END
        await update.message.reply_text("📝 <b>New Order</b>\n\nEnter service ID:", parse_mode='HTML', reply_markup=get_cancel_keyboard())
        return ENTER_SERVICE_ID
    elif text == "📂 Categories":
        if not context.user_data.get('selected_server'):
            await update.message.reply_text("⚠️ Please use /start first to select server!", parse_mode='HTML')
            return ConversationHandler.END
        keyboard = [[InlineKeyboardButton(name, callback_data=f"cat_{key}")] for key, name in CATEGORIES.items()]
        await update.message.reply_text("📂 <b>Select Category</b>", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    elif text == "📦 Order History":
        user_data = get_user_data(data, user_id)
        orders = user_data["orders"][-10:]
        if not orders:
            await update.message.reply_text("📦 No orders yet!")
            return ConversationHandler.END
        msg = "📦 <b>Your Recent Orders</b>\n\n"
        keyboard_buttons = []
        for order_id in reversed(orders):
            order = data["orders"].get(order_id, {})
            status = order.get('status', 'Unknown')
            server = order.get('server', 1)
            msg += f"🆔 <code>{order_id}</code>\n📊 Status: {status}\n🖥 Server: {server}\n💰 Amount: ₹{order.get('charge', 0):.2f}\n━━━━━━━━━━━━━━\n"
            if status == "Pending" and server == 1:
                keyboard_buttons.append([InlineKeyboardButton(f"❌ Cancel {order_id}", callback_data=f"cancel_order_{order_id}")])
        if keyboard_buttons:
            await update.message.reply_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard_buttons))
        else:
            await update.message.reply_text(msg, parse_mode='HTML')
    elif text == "💰 Wallet":
        user_data = get_user_data(data, user_id)
        balance = user_data["balance"]
        total_orders = len(user_data.get("orders", []))
        msg = f"💰 <b>Wallet Dashboard</b>\n\n💳 Balance: ₹<b>{balance:.2f}</b>\n📦 Total Orders: {total_orders}"
        await update.message.reply_text(msg, parse_mode='HTML')
    elif text == "💳 Add Funds":
        await update.message.reply_text("💳 <b>Add Funds</b>\n\nEnter amount (₹):", parse_mode='HTML', reply_markup=get_cancel_keyboard())
        return ENTER_AMOUNT
    elif text == "🆘 Support":
        await update.message.reply_text("🆘 <b>Support</b>\n\nSend your message:", parse_mode='HTML', reply_markup=get_cancel_keyboard())
        return SUPPORT_MESSAGE
    return ConversationHandler.END

# ==================== CATEGORY & SEARCH ====================
async def category_handler(update, context):
    query = update.callback_query
    await query.answer()
    data = load_data()
    category = query.data.replace("cat_", "")
    
    if category == "search":
        context.user_data['awaiting_search'] = True
        await query.edit_message_text("🔍 <b>Search Service</b>\n\nEnter search keywords (e.g., 'Instagram followers'):", parse_mode='HTML')
        return
    
    server = context.user_data.get('selected_server', 1)
    services = fetch_services(data, str(server))
    
    category_keywords = {"tg_members": ["telegram", "member"], "tg_views": ["telegram", "view"], "tg_views_future": ["telegram", "view", "future"], "tg_views_last": ["telegram", "view", "last"], "tg_reaction": ["telegram", "reaction"], "ig_followers": ["instagram", "follower"], "ig_views": ["instagram", "view"], "ig_likes": ["instagram", "like"]}
    keywords = category_keywords.get(category, [])
    filtered = []
    
    for service in services:
        name_lower = service.get('name', '').lower()
        category_lower = service.get('category', '').lower()
        if all(kw in name_lower or kw in category_lower for kw in keywords):
            filtered.append(service)
    
    if not filtered:
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_categories")]]
        await query.edit_message_text(f"❌ No services found in {CATEGORIES[category]}", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    msg = f"📂 {CATEGORIES[category]}\n\n"
    keyboard_buttons = []
    for service in filtered[:10]:
        msg += f"🆔 ID: {service.get('service')}\n📱 {service.get('name')}\n💰 Rate: ₹{service['price_with_markup']:.2f}/1000\n📊 Min: {service.get('min')} | Max: {service.get('max')}\n━━━━━━━━━━━━━━\n"
        keyboard_buttons.append([InlineKeyboardButton(f"🛒 Order: {service.get('service')}", callback_data=f"direct_order_{service.get('service')}")])
    
    keyboard_buttons.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="back_to_categories")])
    await query.edit_message_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard_buttons))

async def search_handler(update, context):
    # This handler should only process if awaiting_search is True
    if not context.user_data.get('awaiting_search'):
        return
    
    # Reset the flag immediately
    context.user_data['awaiting_search'] = False
    
    query_text = update.message.text.strip()
    data = load_data()
    
    server = context.user_data.get('selected_server', 1)
    services = fetch_services(data, str(server))
    results = search_services(query_text, services)
    
    if not results:
        await update.message.reply_text(f"❌ No results for '{query_text}'\n\nTry different keywords.", parse_mode='HTML', reply_markup=get_main_menu_keyboard())
        return
    
    msg = f"🔍 <b>Search Results for '{query_text}'</b>\n\n"
    keyboard_buttons = []
    for service in results:
        msg += f"🆔 ID: {service.get('service')}\n📱 {service.get('name')}\n💰 Rate: ₹{service['price_with_markup']:.2f}/1000\n🖥 Server: {service.get('server')}\n━━━━━━━━━━━━━━\n"
        keyboard_buttons.append([InlineKeyboardButton(f"🛒 Order: {service.get('service')}", callback_data=f"direct_order_{service.get('service')}")])
    
    if keyboard_buttons:
        await update.message.reply_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard_buttons))
    else:
        await update.message.reply_text(msg, parse_mode='HTML', reply_markup=get_main_menu_keyboard())

async def direct_order_callback(update, context):
    query = update.callback_query
    await query.answer()
    service_id = query.data.replace("direct_order_", "")
    context.user_data['service_id'] = service_id
    await query.edit_message_text(f"🛒 <b>Quick Order</b>\n\n🆔 Service ID: {service_id}\n\n🔗 Enter link/username:", parse_mode='HTML')
    context.user_data['direct_order_mode'] = True

async def back_to_categories(update, context):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton(name, callback_data=f"cat_{key}")] for key, name in CATEGORIES.items()]
    await query.edit_message_text("📂 Select Category", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== ORDER FLOW ====================
async def enter_service_id(update, context):
    if update.message.text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled", reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END
    context.user_data['service_id'] = update.message.text.strip()
    await update.message.reply_text("🔗 Enter link/username:", reply_markup=get_cancel_keyboard())
    return ENTER_LINK

async def enter_link(update, context):
    if update.message.text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled", reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END
    context.user_data['link'] = update.message.text.strip()
    await update.message.reply_text("🔢 Enter quantity:", reply_markup=get_cancel_keyboard())
    return ENTER_QUANTITY

async def enter_quantity(update, context):
    if update.message.text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled", reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END
    
    data = load_data()
    user_id = update.effective_user.id
    user_data = get_user_data(data, user_id)
    
    try:
        quantity = int(update.message.text.strip())
        service_id = context.user_data['service_id']
        link = context.user_data['link']
        server = context.user_data.get('selected_server', 1)
        
        services = fetch_services(data, str(server))
        service = next((s for s in services if str(s.get('service')) == service_id), None)
        
        if not service:
            await update.message.reply_text("❌ Invalid service ID!", reply_markup=get_main_menu_keyboard())
            return ConversationHandler.END
        
        min_qty = int(service.get('min', 0))
        max_qty = int(service.get('max', 999999))
        
        if quantity < min_qty or quantity > max_qty:
            await update.message.reply_text(f"❌ Quantity must be between {min_qty} and {max_qty}", reply_markup=get_main_menu_keyboard())
            return ConversationHandler.END
        
        charge = (service['price_with_markup'] / 1000) * quantity
        
        if user_data["balance"] < charge:
            await update.message.reply_text(f"❌ Insufficient balance!\n\nRequired: ₹{charge:.2f}\nYour Balance: ₹{user_data['balance']:.2f}", parse_mode='HTML', reply_markup=get_main_menu_keyboard())
            return ConversationHandler.END
        
        api_response = place_order_api(service_id, link, quantity, server, data)
        
        if not api_response or 'order' not in api_response:
            await update.message.reply_text("❌ Failed to place order. Try again.", reply_markup=get_main_menu_keyboard())
            return ConversationHandler.END
        
        data["order_counter"] += 1
        order_id = f"ORD{data['order_counter']}"
        data["orders"][order_id] = {"user_id": user_id, "service_id": service_id, "service_name": service.get('name', 'Unknown'), "link": link, "quantity": quantity, "charge": charge, "status": "Pending", "api_order_id": str(api_response['order']), "notified": False, "created_at": datetime.now().isoformat(), "server": server}
        user_data["orders"].append(order_id)
        user_data["balance"] -= charge
        save_data(data)
        
        server_name = "Server 1" if server == 1 else "Server 2"
        refund_text = "\n✅ Refund available for this order" if server == 1 else "\n⚠️ No refund available (Server 2)"
        
        await update.message.reply_text(f"✅ Order Placed!\n\n🆔 Order ID: {order_id}\n🖥 Server: {server_name}\n📱 Service: {service.get('name')}\n📊 Quantity: {quantity}\n💰 Charged: ₹{charge:.2f}\n💳 Balance: ₹{user_data['balance']:.2f}{refund_text}\n\n⏳ Processing...", parse_mode='HTML', reply_markup=get_main_menu_keyboard())
    except ValueError:
        await update.message.reply_text("❌ Invalid quantity!", reply_markup=get_main_menu_keyboard())
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", reply_markup=get_main_menu_keyboard())
    
    return ConversationHandler.END

# ==================== DIRECT ORDER TEXT ====================
async def direct_order_text_handler(update, context):
    if not context.user_data.get('direct_order_mode'):
        return
    
    if not context.user_data.get('link'):
        context.user_data['link'] = update.message.text.strip()
        await update.message.reply_text("🔢 Enter quantity:")
    else:
        try:
            quantity = int(update.message.text.strip())
            data = load_data()
            user_id = update.effective_user.id
            user_data = get_user_data(data, user_id)
            service_id = context.user_data['service_id']
            link = context.user_data['link']
            server = context.user_data.get('selected_server', 1)
            
            services = fetch_services(data, str(server))
            service = next((s for s in services if str(s.get('service')) == service_id), None)
            
            if not service:
                await update.message.reply_text("❌ Service not found!", reply_markup=get_main_menu_keyboard())
                context.user_data['direct_order_mode'] = False
                return
            
            charge = (service['price_with_markup'] / 1000) * quantity
            
            if user_data["balance"] < charge:
                await update.message.reply_text(f"❌ Insufficient balance!\n\nRequired: ₹{charge:.2f}\nBalance: ₹{user_data['balance']:.2f}", parse_mode='HTML', reply_markup=get_main_menu_keyboard())
                context.user_data['direct_order_mode'] = False
                return
            
            api_response = place_order_api(service_id, link, quantity, server, data)
            if not api_response or 'order' not in api_response:
                await update.message.reply_text("❌ Order failed!", reply_markup=get_main_menu_keyboard())
                context.user_data['direct_order_mode'] = False
                return
            
            data["order_counter"] += 1
            order_id = f"ORD{data['order_counter']}"
            data["orders"][order_id] = {"user_id": user_id, "service_id": service_id, "service_name": service.get('name'), "link": link, "quantity": quantity, "charge": charge, "status": "Pending", "api_order_id": str(api_response['order']), "notified": False, "created_at": datetime.now().isoformat(), "server": server}
            user_data["orders"].append(order_id)
            user_data["balance"] -= charge
            save_data(data)
            
            await update.message.reply_text(f"✅ Order Placed!\n\n🆔 {order_id}\n🖥 Server: {server}\n💰 Charged: ₹{charge:.2f}\n💳 Balance: ₹{user_data['balance']:.2f}", parse_mode='HTML', reply_markup=get_main_menu_keyboard())
            context.user_data['direct_order_mode'] = False
            context.user_data['link'] = None
        except ValueError:
            await update.message.reply_text("❌ Invalid quantity!")

# ==================== CANCEL ORDER ====================
async def cancel_order_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = load_data()
    user_id = query.from_user.id
    order_id = query.data.replace("cancel_order_", "")
    order = data["orders"].get(order_id)
    
    if not order or order["user_id"] != user_id:
        await query.answer("❌ Order not found!", show_alert=True)
        return
    
    if order.get("server") != 1:
        await query.answer("❌ No refund available for Server 2 orders!", show_alert=True)
        return
    
    if order["status"] != "Pending":
        await query.answer(f"❌ Cannot cancel {order['status']} order!", show_alert=True)
        return
    
    api_order_id = order.get("api_order_id")
    cancel_result = None
    if api_order_id:
        cancel_result = cancel_order_api(api_order_id, 1, data)
    
    if cancel_result:
        if "error" in cancel_result:
            await query.answer("❌ Order cannot be cancelled (already processing)", show_alert=True)
            return
        
        api_status = cancel_result.get("status", "").lower()
        if "cancel" in api_status or "refund" in api_status or api_status == "canceled":
            charge = order.get("charge", 0)
            order["status"] = "Cancelled"
            user_id_str = str(user_id)
            if user_id_str in data["users"]:
                data["users"][user_id_str]["balance"] += charge
                new_balance = data["users"][user_id_str]["balance"]
            save_data(data)
            
            await query.edit_message_text(f"✅ <b>Order Cancelled & Refunded!</b>\n\n🆔 Order ID: {order_id}\n💰 Refunded: ₹{charge:.2f}\n💳 New Balance: ₹{new_balance:.2f}\n\nAmount has been refunded to your wallet.", parse_mode='HTML')
            return
    
    order["status"] = "Refund Requested"
    charge = order.get("charge", 0)
    
    refund_request = {"order_id": order_id, "user_id": user_id, "amount": charge, "requested_at": datetime.now().isoformat(), "api_order_id": api_order_id}
    
    if "refund_requests" not in data:
        data["refund_requests"] = []
    
    data["refund_requests"].append(refund_request)
    save_data(data)
    
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"💳 <b>New Refund Request</b>\n\n🆔 Order ID: {order_id}\n👤 User ID: {user_id}\n💰 Amount: ₹{charge:.2f}\n📱 Service: {order.get('service_name', 'Unknown')}\n\nUse /admin to manage refunds", parse_mode='HTML')
    except:
        pass
    
    await query.edit_message_text(f"⏳ <b>Refund Request Submitted</b>\n\n🆔 Order ID: {order_id}\n💰 Amount: ₹{charge:.2f}\n\nYour refund request has been sent to admin.\n⏰ It may take 12-24 hours to process.\n\nYou will be notified once the refund is approved.", parse_mode='HTML')

# ==================== DEPOSIT FLOW ====================
async def enter_amount(update, context):
    if update.message.text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled", reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END
    
    data = load_data()
    try:
        amount = float(update.message.text.strip())
        if amount < 10:
            await update.message.reply_text("❌ Minimum ₹10", reply_markup=get_cancel_keyboard())
            return ENTER_AMOUNT
        
        # Store the amount in context
        context.user_data['deposit_amount'] = amount
        upi_id = data.get("upi_id", "pay@paytm")
        
        # Create UPI link with the EXACT amount - properly formatted
        upi_link = f"upi://pay?pa={upi_id}&pn=SMM%20Panel&am={amount:.2f}&cu=INR"
        
        # URL encode the entire UPI link for QR code generation
        import urllib.parse
        encoded_upi = urllib.parse.quote(upi_link, safe='')
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={encoded_upi}"
        
        msg = f"💳 <b>Payment QR Code</b>\n\n💰 Amount: ₹<b>{amount:.2f}</b>\n\n📱 Scan QR code below to pay\n\n⚠️ After payment:\n1. Take screenshot\n2. Send screenshot here"
        
        try:
            await update.message.reply_photo(photo=qr_url, caption=msg, parse_mode='HTML', reply_markup=get_cancel_keyboard())
        except Exception as e:
            # Fallback if QR generation fails
            await update.message.reply_text(f"💳 <b>Payment Details</b>\n\n💰 Amount: ₹<b>{amount:.2f}</b>\n📱 UPI ID: <code>{upi_id}</code>\n\n⚠️ After payment:\n1. Take screenshot\n2. Send screenshot here", parse_mode='HTML', reply_markup=get_cancel_keyboard())
        
        return ENTER_PAYMENT_SCREENSHOT
        
    except ValueError:
        await update.message.reply_text("❌ Invalid amount! Please enter a valid number.", reply_markup=get_cancel_keyboard())
        return ENTER_AMOUNT
    except Exception as e:
        await update.message.reply_text(f"❌ Error: Please try again.", reply_markup=get_main_menu_keyboard(), parse_mode='HTML')
        return ConversationHandler.END

async def enter_payment_screenshot(update, context):
    if update.message.text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled", reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END
    
    if not update.message.photo:
        await update.message.reply_text("❌ Please send payment screenshot!", reply_markup=get_cancel_keyboard())
        return ENTER_PAYMENT_SCREENSHOT
    
    context.user_data['payment_screenshot'] = update.message.photo[-1].file_id
    await update.message.reply_text("✅ Screenshot received!\n\n📝 Now enter UTR/Transaction ID:", parse_mode='HTML', reply_markup=get_cancel_keyboard())
    return ENTER_UTR

async def enter_utr(update, context):
    if update.message.text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled", reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END
    
    utr = update.message.text.strip()
    
    if not utr.isdigit() or len(utr) != 12:
        await update.message.reply_text("❌ <b>Unsupported UTR</b>\n\nUTR must be exactly 12 digits.\nPlease enter valid UTR number:", parse_mode='HTML', reply_markup=get_cancel_keyboard())
        return ENTER_UTR
    
    data = load_data()
    user_id = update.effective_user.id
    amount = context.user_data.get('deposit_amount')
    screenshot = context.user_data.get('payment_screenshot')
    
    data["deposit_counter"] += 1
    deposit_id = f"DEP{data['deposit_counter']}"
    
    deposit_data = {"deposit_id": deposit_id, "user_id": user_id, "amount": amount, "utr": utr, "screenshot": screenshot, "status": "Pending", "created_at": datetime.now().isoformat()}
    
    if "manual_deposits" not in data:
        data["manual_deposits"] = []
    
    data["manual_deposits"].append(deposit_data)
    save_data(data)
    
    user_info = update.effective_user
    username = user_info.username or "No username"
    name = user_info.first_name
    
    try:
        caption = f"💳 <b>New Deposit Request</b>\n\n🆔 Deposit ID: <code>{deposit_id}</code>\n👤 User: {name} (@{username})\n🆔 User ID: <code>{user_id}</code>\n💰 Amount: ₹<b>{amount:.2f}</b>\n🔢 UTR: <code>{utr}</code>\n📅 Time: {datetime.now().strftime('%d-%m-%Y %H:%M')}\n\n📸 Payment Screenshot Attached"
        
        keyboard = [[InlineKeyboardButton("✅ Approve", callback_data=f"approve_deposit_{deposit_id}"), InlineKeyboardButton("❌ Reject", callback_data=f"reject_deposit_{deposit_id}")]]
        
        await context.bot.send_photo(chat_id=PAYMENT_GROUP, photo=screenshot, caption=caption, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        
        await update.message.reply_text(f"✅ <b>Payment Request Submitted!</b>\n\n🆔 Deposit ID: <code>{deposit_id}</code>\n💰 Amount: ₹{amount:.2f}\n🔢 UTR: <code>{utr}</code>\n\n⏰ Your payment is being verified.\nYou will be notified once approved.\n\n⏱️ Usually takes 5-10 minutes.", parse_mode='HTML', reply_markup=get_main_menu_keyboard())
        
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to submit payment request.\n\nError: {str(e)}\n\nPlease contact support.", reply_markup=get_main_menu_keyboard(), parse_mode='HTML')
    
    context.user_data.clear()
    return ConversationHandler.END

# ==================== DEPOSIT APPROVAL ====================
async def approve_deposit_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = load_data()
    deposit_id = query.data.replace("approve_deposit_", "")
    
    deposit_request = None
    for req in data.get("manual_deposits", []):
        if req["deposit_id"] == deposit_id:
            deposit_request = req
            break
    
    if not deposit_request:
        await query.answer("❌ Deposit request not found!", show_alert=True)
        return
    
    if deposit_request["status"] != "Pending":
        await query.answer("❌ Already processed!", show_alert=True)
        return
    
    user_id = deposit_request["user_id"]
    amount = deposit_request["amount"]
    user_id_str = str(user_id)
    
    if user_id_str not in data["users"]:
        data["users"][user_id_str] = {"balance": 0.0, "orders": [], "deposits": [], "joined_date": datetime.now().isoformat()}
    
    data["users"][user_id_str]["balance"] += amount
    new_balance = data["users"][user_id_str]["balance"]
    
    deposit_request["status"] = "Approved"
    deposit_request["approved_at"] = datetime.now().isoformat()
    save_data(data)
    
    try:
        await context.bot.send_message(chat_id=user_id, text=f"✅ <b>Payment Approved!</b>\n\n🆔 Deposit ID: {deposit_id}\n💰 Amount: ₹{amount:.2f}\n💳 New Balance: ₹{new_balance:.2f}\n\nYour payment has been verified successfully!", parse_mode='HTML')
    except:
        pass
    
    await query.edit_message_caption(caption=query.message.caption + f"\n\n✅ <b>APPROVED</b> by {query.from_user.first_name}", parse_mode='HTML')

async def reject_deposit_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = load_data()
    deposit_id = query.data.replace("reject_deposit_", "")
    
    deposit_request = None
    for req in data.get("manual_deposits", []):
        if req["deposit_id"] == deposit_id:
            deposit_request = req
            break
    
    if not deposit_request:
        await query.answer("❌ Deposit request not found!", show_alert=True)
        return
    
    if deposit_request["status"] != "Pending":
        await query.answer("❌ Already processed!", show_alert=True)
        return
    
    user_id = deposit_request["user_id"]
    amount = deposit_request["amount"]
    
    deposit_request["status"] = "Rejected"
    deposit_request["rejected_at"] = datetime.now().isoformat()
    save_data(data)
    
    try:
        await context.bot.send_message(chat_id=user_id, text=f"❌ <b>Payment Rejected</b>\n\n🆔 Deposit ID: {deposit_id}\n💰 Amount: ₹{amount:.2f}\n\nYour payment could not be verified.\nPlease contact support if you believe this is an error.", parse_mode='HTML')
    except:
        pass
    
    await query.edit_message_caption(caption=query.message.caption + f"\n\n❌ <b>REJECTED</b> by {query.from_user.first_name}", parse_mode='HTML')

# ==================== SUPPORT ====================
async def support_message(update, context):
    if update.message.text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled", reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END
    
    user_id = update.effective_user.id
    username = update.effective_user.username or "No username"
    name = update.effective_user.first_name
    
    try:
        if update.message.photo:
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, caption=f"💬 Support\n\n👤 {name} (@{username})\n🆔 {user_id}\n\n📸 Photo", parse_mode='HTML')
        else:
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"💬 Support\n\n👤 {name} (@{username})\n🆔 {user_id}\n\nMessage: {update.message.text}", parse_mode='HTML')
        await update.message.reply_text("✅ Message sent to support!", reply_markup=get_main_menu_keyboard())
    except:
        await update.message.reply_text("❌ Failed to send", reply_markup=get_main_menu_keyboard())
    
    return ConversationHandler.END

# ==================== ADMIN ====================
async def admin_command(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    
    keyboard = [
        [InlineKeyboardButton("⚙️ Set UPI", callback_data="admin_set_upi"), InlineKeyboardButton("💵 Refund Requests", callback_data="admin_refund_requests")],
        [InlineKeyboardButton("📊 All Orders", callback_data="admin_all_orders"), InlineKeyboardButton("👥 User Stats", callback_data="admin_user_stats")],
        [InlineKeyboardButton("💰 Manage Balance", callback_data="admin_manage_balance"), InlineKeyboardButton("🚫 Ban/Unban User", callback_data="admin_ban_user")],
        [InlineKeyboardButton("🤖 Bot ON/OFF", callback_data="admin_bot_toggle"), InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📢 Add Channel", callback_data="admin_add_channel"), InlineKeyboardButton("🖥️ Configure Server 2", callback_data="admin_server2")]
    ]
    
    await update.message.reply_text("👨‍💼 <b>Admin Panel</b>\n\nSelect an option:", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

# Due to character limit, continuing in next message with remaining admin functions...

async def admin_inline_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    data = load_data()
    
    if query.data == "admin_server2":
        server2_config = data.get("server2_config", {})
        status = "✅ Enabled" if server2_config.get("enabled") else "🚫 Disabled"
        api_url = server2_config.get("api_url", "Not Set")
        api_key_display = server2_config.get("api_key", "Not Set")
        if len(api_key_display) > 20:
            api_key_display = api_key_display[:20] + "..."
        markup = server2_config.get("markup", 5)
        
        msg = f"🖥️ <b>Server 2 Configuration</b>\n\nStatus: {status}\nAPI URL: {api_url}\nAPI Key: {api_key_display}\nMarkup: {markup}\n\nSend new config in format:\nurl|key|markup\n\nExample:\nhttps://api.com/v2|abc123key|10"
        
        await query.edit_message_text(msg, parse_mode='HTML')
        context.user_data['awaiting_server2_config'] = True
        return
    
    elif query.data == "admin_refund_requests":
        refund_requests = data.get("refund_requests", [])
        if not refund_requests:
            await query.edit_message_text("✅ No pending refund requests!")
            return
        
        msg = "💵 <b>Refund Requests</b>\n\n"
        keyboard_buttons = []
        for req in refund_requests:
            order_id = req["order_id"]
            amount = req["amount"]
            user_id = req["user_id"]
            msg += f"🆔 {order_id}\n💰 ₹{amount:.2f}\n👤 User: {user_id}\n━━━━━━━━\n"
            keyboard_buttons.append([InlineKeyboardButton(f"✅ Approve {order_id}", callback_data=f"approve_refund_{order_id}")])
        
        keyboard_buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back")])
        await query.edit_message_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard_buttons))
    
    elif query.data == "admin_all_orders":
        total = len(data["orders"])
        pending = sum(1 for o in data["orders"].values() if o["status"] == "Pending")
        completed = sum(1 for o in data["orders"].values() if o["status"] in ["Completed", "Partial"])
        msg = f"📊 <b>Order Statistics</b>\n\n📦 Total: {total}\n⏳ Pending: {pending}\n✅ Completed: {completed}"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]
        await query.edit_message_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "admin_user_stats":
        total_users = len(data["users"])
        banned = len(data.get("banned_users", []))
        total_balance = sum(u["balance"] for u in data["users"].values())
        msg = f"👥 <b>User Statistics</b>\n\n👤 Total: {total_users}\n🚫 Banned: {banned}\n💰 Total Balance: ₹{total_balance:.2f}"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]
        await query.edit_message_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "admin_bot_toggle":
        current_status = data.get("bot_enabled", True)
        data["bot_enabled"] = not current_status
        save_data(data)
        
        new_status = "✅ ENABLED" if data["bot_enabled"] else "🚫 DISABLED"
        
        if not data["bot_enabled"]:
            msg_to_users = "🚫 <b>Bot Temporarily Disabled</b>\n\nThe bot is under maintenance.\nWe'll be back soon!"
        else:
            msg_to_users = "✅ <b>Bot Enabled!</b>\n\nThe bot is now active.\nYou can use all features now!"
        
        for user_id in data["users"].keys():
            try:
                await context.bot.send_message(chat_id=int(user_id), text=msg_to_users, parse_mode='HTML')
                await asyncio.sleep(0.05)
            except:
                pass
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]
        await query.edit_message_text(f"🤖 <b>Bot Status Changed</b>\n\nNew Status: {new_status}\n\nAll users have been notified!", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "admin_set_upi":
        await query.edit_message_text("⚙️ <b>Set UPI ID</b>\n\nSend the new UPI ID:", parse_mode='HTML')
        context.user_data['awaiting_upi'] = True
    
    elif query.data == "admin_manage_balance":
        await query.edit_message_text("💰 <b>Manage Balance</b>\n\nSend user ID:", parse_mode='HTML')
        context.user_data['awaiting_balance_user_id'] = True
    
    elif query.data == "admin_ban_user":
        await query.edit_message_text("🚫 <b>Ban/Unban User</b>\n\nSend user ID:", parse_mode='HTML')
        context.user_data['awaiting_ban_user_id'] = True
    
    elif query.data == "admin_broadcast":
        await query.edit_message_text("📢 <b>Broadcast Message</b>\n\nStep 1: Send your text message:", parse_mode='HTML')
        context.user_data['broadcast_step'] = 'text'
    
    elif query.data == "admin_add_channel":
        current_channels = data.get("force_channels", [])
        channels_list = "\n".join([f"{idx}. {ch}" for idx, ch in enumerate(current_channels, 1)])
        
        await query.edit_message_text(f"📢 <b>Force Join Channels</b>\n\n<b>Current Channels:</b>\n{channels_list}\n\nSend channel username to add (e.g., @yourchannel)\nOr send 'remove N' to remove channel number N", parse_mode='HTML')
        context.user_data['awaiting_add_channel'] = True
    
    elif query.data.startswith("balance_"):
        parts = query.data.split("_")
        action = parts[1]
        user_id = parts[2]
        
        context.user_data['balance_action'] = action
        context.user_data['balance_user_id'] = user_id
        context.user_data['awaiting_balance_amount'] = True
        
        await query.edit_message_text(f"💰 <b>Manage Balance</b>\n\nAction: {action.upper()}\nUser: {user_id}\n\nSend amount:", parse_mode='HTML')
        return
    
    elif query.data == "admin_back":
        keyboard = [
            [InlineKeyboardButton("⚙️ Set UPI", callback_data="admin_set_upi"), InlineKeyboardButton("💵 Refund Requests", callback_data="admin_refund_requests")],
            [InlineKeyboardButton("📊 All Orders", callback_data="admin_all_orders"), InlineKeyboardButton("👥 User Stats", callback_data="admin_user_stats")],
            [InlineKeyboardButton("💰 Manage Balance", callback_data="admin_manage_balance"), InlineKeyboardButton("🚫 Ban/Unban User", callback_data="admin_ban_user")],
            [InlineKeyboardButton("🤖 Bot ON/OFF", callback_data="admin_bot_toggle"), InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("📢 Add Channel", callback_data="admin_add_channel"), InlineKeyboardButton("🖥️ Configure Server 2", callback_data="admin_server2")]
        ]
        await query.edit_message_text("👨‍💼 <b>Admin Panel</b>\n\nSelect an option:", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_text_handler(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    
    data = load_data()
    
    # Server 2 Config
    if context.user_data.get('awaiting_server2_config'):
        try:
            parts = update.message.text.strip().split("|")
            if len(parts) != 3:
                await update.message.reply_text("❌ Invalid format! Use: url|key|markup")
                return
            
            api_url, api_key, markup = parts
            data["server2_config"] = {"api_url": api_url.strip(), "api_key": api_key.strip(), "markup": int(markup.strip()), "enabled": True}
            save_data(data)
            
            await update.message.reply_text(f"✅ Server 2 configured!\n\nURL: {api_url}\nMarkup: {markup}%\n\nServer 2 is now enabled!", parse_mode='HTML')
        except:
            await update.message.reply_text("❌ Invalid format! Use: url|key|markup")
        
        context.user_data['awaiting_server2_config'] = False
        return
    
    # Set UPI
    if context.user_data.get('awaiting_upi'):
        upi_id = update.message.text.strip()
        data["upi_id"] = upi_id
        save_data(data)
        context.user_data['awaiting_upi'] = False
        await update.message.reply_text(f"✅ UPI ID updated to: {upi_id}", parse_mode='HTML')
        return
    
    # Manage Balance - User ID
    if context.user_data.get('awaiting_balance_user_id'):
        user_id = update.message.text.strip()
        if user_id not in data["users"]:
            await update.message.reply_text("❌ User not found!")
            context.user_data['awaiting_balance_user_id'] = False
            return
        
        context.user_data['balance_user_id'] = user_id
        context.user_data['awaiting_balance_user_id'] = False
        
        balance = data["users"][user_id]["balance"]
        keyboard = [
            [InlineKeyboardButton("➕ Add", callback_data=f"balance_add_{user_id}"), InlineKeyboardButton("➖ Deduct", callback_data=f"balance_deduct_{user_id}")],
            [InlineKeyboardButton("📝 Set", callback_data=f"balance_set_{user_id}")]
        ]
        await update.message.reply_text(f"💰 <b>User Balance</b>\n\nUser ID: {user_id}\nCurrent: ₹{balance:.2f}\n\nSelect action:", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Manage Balance - Amount
    if context.user_data.get('awaiting_balance_amount'):
        try:
            amount = float(update.message.text.strip())
            action = context.user_data.get('balance_action')
            user_id = context.user_data.get('balance_user_id')
            
            old_balance = data["users"][user_id]["balance"]
            
            if action == "add":
                data["users"][user_id]["balance"] += amount
            elif action == "deduct":
                data["users"][user_id]["balance"] = max(0, data["users"][user_id]["balance"] - amount)
            elif action == "set":
                data["users"][user_id]["balance"] = amount
            
            new_balance = data["users"][user_id]["balance"]
            save_data(data)
            
            await update.message.reply_text(f"✅ Balance updated!\n\nUser: {user_id}\nOld: ₹{old_balance:.2f}\nNew: ₹{new_balance:.2f}", parse_mode='HTML')
            
            try:
                await context.bot.send_message(chat_id=int(user_id), text=f"💰 <b>Balance Updated</b>\n\nYour balance has been updated by admin.\nNew Balance: ₹{new_balance:.2f}", parse_mode='HTML')
            except:
                pass
            
            context.user_data.clear()
        except ValueError:
            await update.message.reply_text("❌ Invalid amount!")
        return
    
    # Ban/Unban User
    if context.user_data.get('awaiting_ban_user_id'):
        user_id = update.message.text.strip()
        
        if user_id == str(ADMIN_ID):
            await update.message.reply_text("❌ Cannot ban yourself!")
            context.user_data['awaiting_ban_user_id'] = False
            return
        
        if "banned_users" not in data:
            data["banned_users"] = []
        
        if user_id in data["banned_users"]:
            data["banned_users"].remove(user_id)
            save_data(data)
            await update.message.reply_text(f"✅ User {user_id} unbanned!", parse_mode='HTML')
            try:
                await context.bot.send_message(chat_id=int(user_id), text="✅ You have been unbanned!")
            except:
                pass
        else:
            data["banned_users"].append(user_id)
            save_data(data)
            await update.message.reply_text(f"🚫 User {user_id} banned!", parse_mode='HTML')
            try:
                await context.bot.send_message(chat_id=int(user_id), text="🚫 You have been banned from using this bot.")
            except:
                pass
        
        context.user_data['awaiting_ban_user_id'] = False
        return
    
    # Broadcast
    if context.user_data.get('broadcast_step') == 'text':
        broadcast_text = update.message.text
        context.user_data['broadcast_text'] = broadcast_text
        context.user_data['broadcast_step'] = None
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes", callback_data="broadcast_photo_yes"), InlineKeyboardButton("❌ No", callback_data="broadcast_photo_no")]
        ]
        await update.message.reply_text("📸 <b>Add Photo?</b>\n\nDo you want to add a photo to this broadcast?", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    if context.user_data.get('broadcast_step') == 'photo':
        if update.message.photo:
            broadcast_photo = update.message.photo[-1].file_id
            context.user_data['broadcast_photo'] = broadcast_photo
            context.user_data['broadcast_step'] = None
            
            keyboard = [
                [InlineKeyboardButton("✅ Yes", callback_data="broadcast_button_yes"), InlineKeyboardButton("❌ No", callback_data="broadcast_button_no")]
            ]
            await update.message.reply_text("🔘 <b>Add Button?</b>\n\nDo you want to add an inline button?", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text("❌ Please send a photo!")
        return
    
    if context.user_data.get('broadcast_step') == 'button_text':
        button_text = update.message.text.strip()
        context.user_data['broadcast_button_text'] = button_text
        context.user_data['broadcast_step'] = 'button_url'
        await update.message.reply_text("🔗 <b>Button URL</b>\n\nSend button URL (e.g., https://t.me/yourchannel):", parse_mode='HTML')
        return
    
    if context.user_data.get('broadcast_step') == 'button_url':
        button_url = update.message.text.strip()
        context.user_data['broadcast_button_url'] = button_url
        context.user_data['broadcast_step'] = None
        
        await start_broadcast(update, context, data)
        return
    
    # Add/Remove Channel
    if context.user_data.get('awaiting_add_channel'):
        text = update.message.text.strip()
        
        if text.lower().startswith('remove '):
            try:
                idx = int(text.split()[1]) - 1
                channels = data.get("force_channels", [])
                if 0 <= idx < len(channels):
                    removed = channels.pop(idx)
                    data["force_channels"] = channels
                    save_data(data)
                    await update.message.reply_text(f"✅ Removed channel: {removed}", parse_mode='HTML')
                else:
                    await update.message.reply_text("❌ Invalid channel number!")
            except:
                await update.message.reply_text("❌ Invalid format! Use: remove 1")
        elif text.startswith('@'):
            channels = data.get("force_channels", [])
            if text not in channels:
                channels.append(text)
                data["force_channels"] = channels
                save_data(data)
                await update.message.reply_text(f"✅ Added channel: {text}", parse_mode='HTML')
            else:
                await update.message.reply_text("❌ Channel already exists!")
        else:
            await update.message.reply_text("❌ Channel must start with @")
        
        context.user_data['awaiting_add_channel'] = False
        return

async def broadcast_callbacks(update, context):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    if query.data == "broadcast_photo_yes":
        context.user_data['broadcast_step'] = 'photo'
        await query.edit_message_text("📸 <b>Send Photo</b>\n\nSend the photo you want to attach:", parse_mode='HTML')
    
    elif query.data == "broadcast_photo_no":
        context.user_data['broadcast_photo'] = None
        keyboard = [
            [InlineKeyboardButton("✅ Yes", callback_data="broadcast_button_yes"), InlineKeyboardButton("❌ No", callback_data="broadcast_button_no")]
        ]
        await query.edit_message_text("🔘 <b>Add Button?</b>\n\nDo you want to add an inline button?", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "broadcast_button_yes":
        context.user_data['broadcast_step'] = 'button_text'
        await query.edit_message_text("📝 <b>Button Text</b>\n\nSend button text (e.g., Join Channel):", parse_mode='HTML')
    
    elif query.data == "broadcast_button_no":
        context.user_data['broadcast_button_text'] = None
        context.user_data['broadcast_button_url'] = None
        data = load_data()
        await start_broadcast(query, context, data)

async def start_broadcast(update, context, data):
    broadcast_text = context.user_data.get('broadcast_text')
    broadcast_photo = context.user_data.get('broadcast_photo')
    button_text = context.user_data.get('broadcast_button_text')
    button_url = context.user_data.get('broadcast_button_url')
    
    button_markup = None
    if button_text and button_url:
        button_markup = InlineKeyboardMarkup([[InlineKeyboardButton(button_text, url=button_url)]])
    
    success = 0
    failed = 0
    
    if hasattr(update, 'message'):
        await update.message.reply_text("📢 Broadcasting... Please wait", parse_mode='HTML')
    else:
        await update.edit_message_text("📢 Broadcasting... Please wait", parse_mode='HTML')
    
    for user_id in data["users"].keys():
        if user_id in data.get("banned_users", []):
            continue
        try:
            if broadcast_photo:
                await context.bot.send_photo(
                    chat_id=int(user_id),
                    photo=broadcast_photo,
                    caption=broadcast_text,
                    parse_mode='HTML',
                    reply_markup=button_markup
                )
            else:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=broadcast_text,
                    parse_mode='HTML',
                    reply_markup=button_markup
                )
            success += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    
    if hasattr(update, 'message'):
        await update.message.reply_text(f"✅ <b>Broadcast Complete!</b>\n\n✅ Sent: {success}\n❌ Failed: {failed}", parse_mode='HTML')
    else:
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"✅ <b>Broadcast Complete!</b>\n\n✅ Sent: {success}\n❌ Failed: {failed}", parse_mode='HTML')
    
    context.user_data.clear()

async def approve_refund_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    data = load_data()
    order_id = query.data.replace("approve_refund_", "")
    
    refund_request = None
    for req in data.get("refund_requests", []):
        if req["order_id"] == order_id:
            refund_request = req
            break
    
    if not refund_request:
        await query.answer("❌ Refund request not found!", show_alert=True)
        return
    
    user_id = refund_request["user_id"]
    amount = refund_request["amount"]
    user_id_str = str(user_id)
    
    if user_id_str in data["users"]:
        data["users"][user_id_str]["balance"] += amount
        new_balance = data["users"][user_id_str]["balance"]
    
    if order_id in data["orders"]:
        data["orders"][order_id]["status"] = "Refunded"
    
    data["refund_requests"] = [req for req in data.get("refund_requests", []) if req["order_id"] != order_id]
    save_data(data)
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ <b>Refund Approved!</b>\n\n"
                 f"🆔 Order ID: {order_id}\n"
                 f"💰 Refunded: ₹{amount:.2f}\n"
                 f"💳 New Balance: ₹{new_balance:.2f}\n\n"
                 f"Your refund has been processed successfully!",
            parse_mode='HTML'
        )
    except:
        pass
    
    await query.edit_message_text(f"✅ Refund approved for {order_id}\n\n💰 ₹{amount:.2f} refunded to user {user_id}", parse_mode='HTML')

async def admin_reply_handler(update, context):
    if update.effective_user.id != ADMIN_ID or not update.message.reply_to_message:
        return
    original_text = update.message.reply_to_message.text or update.message.reply_to_message.caption or ""
    user_id = None
    for pattern in [r'🆔 (\d+)', r'User ID: (\d+)', r'\b(\d{9,10})\b']:
        match = re.search(pattern, original_text)
        if match:
            user_id = int(match.group(1))
            break
    if user_id:
        try:
            await context.bot.send_message(chat_id=user_id, text=f"💬 Admin Reply:\n\n{update.message.text}", parse_mode='HTML')
            await update.message.reply_text(f"✅ Sent to {user_id}", parse_mode='HTML')
        except:
            await update.message.reply_text("❌ Failed", parse_mode='HTML')

async def unknown_message_handler(update, context):
    if context.user_data.get('direct_order_mode') or context.user_data.get('awaiting_search'):
        return
    
    await update.message.reply_text(
        "❓ <b>I didn't understand what you need</b>\n\n"
        "Please use the menu buttons below.\n"
        "Tap on 🆘 Support for any questions.",
        parse_mode='HTML',
        reply_markup=get_main_menu_keyboard()
    )

async def check_orders_status(context):
    data = load_data()
    for order_id, order in list(data["orders"].items()):
        if order["status"] == "Pending" and not order.get("notified", False):
            api_order_id = order.get("api_order_id")
            server = order.get("server", 1)
            if not api_order_id:
                continue
            status_data = check_order_status(api_order_id, server, data)
            if status_data and "status" in status_data:
                api_status = status_data["status"]
                if api_status in ["Completed", "Partial", "Canceled", "Refunded"]:
                    order["status"] = api_status
                    if api_status in ["Completed", "Partial"]:
                        order["notified"] = True
                    elif api_status in ["Canceled", "Refunded"] and server == 1:
                        charge = order.get("charge", 0)
                        user_id_str = str(order["user_id"])
                        if user_id_str in data["users"]:
                            data["users"][user_id_str]["balance"] += charge
                    save_data(data)
                    try:
                        refund_msg = ""
                        if api_status in ["Canceled", "Refunded"] and server == 1:
                            charge = order.get("charge", 0)
                            user_id_str = str(order["user_id"])
                            if user_id_str in data["users"]:
                                refund_msg = f"\n💰 Refunded: ₹{charge:.2f}\n💳 Balance: ₹{data['users'][user_id_str]['balance']:.2f}"
                        
                        await context.bot.send_message(
                            chat_id=order["user_id"], 
                            text=f"{'✅' if api_status in ['Completed','Partial'] else '❌'} Order {api_status}!\n\n🆔 {order_id}\n📱 {order['service_name']}{refund_msg}", 
                            parse_mode='HTML'
                        )
                    except:
                        pass
    save_data(data)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    
    order_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🛒 New Order$"), main_menu_handler)], 
        states={
            ENTER_SERVICE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_service_id)], 
            ENTER_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_link)], 
            ENTER_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_quantity)]
        }, 
        fallbacks=[MessageHandler(filters.Regex("^❌ Cancel$"), main_menu_handler)]
    )
    app.add_handler(order_conv)
    
    deposit_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💳 Add Funds$"), main_menu_handler)], 
        states={
            ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount)], 
            ENTER_PAYMENT_SCREENSHOT: [MessageHandler(filters.PHOTO | filters.TEXT, enter_payment_screenshot)], 
            ENTER_UTR: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_utr)]
        }, 
        fallbacks=[MessageHandler(filters.Regex("^❌ Cancel$"), main_menu_handler)]
    )
    app.add_handler(deposit_conv)
    
    support_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🆘 Support$"), main_menu_handler)], 
        states={
            SUPPORT_MESSAGE: [MessageHandler(filters.TEXT | filters.PHOTO, support_message)]
        }, 
        fallbacks=[MessageHandler(filters.Regex("^❌ Cancel$"), main_menu_handler)]
    )
    app.add_handler(support_conv)
    
    app.add_handler(CallbackQueryHandler(select_server_callback, pattern="^select_server_"))
    app.add_handler(CallbackQueryHandler(category_handler, pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(back_to_categories, pattern="^back_to_categories$"))
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(cancel_order_callback, pattern="^cancel_order_"))
    app.add_handler(CallbackQueryHandler(direct_order_callback, pattern="^direct_order_"))
    app.add_handler(CallbackQueryHandler(approve_refund_callback, pattern="^approve_refund_"))
    app.add_handler(CallbackQueryHandler(approve_deposit_callback, pattern="^approve_deposit_"))
    app.add_handler(CallbackQueryHandler(reject_deposit_callback, pattern="^reject_deposit_"))
    app.add_handler(CallbackQueryHandler(admin_inline_callback, pattern="^admin_"))
    app.add_handler(CallbackQueryHandler(admin_inline_callback, pattern="^balance_"))
    app.add_handler(CallbackQueryHandler(broadcast_callbacks, pattern="^broadcast_"))
    
    app.add_handler(MessageHandler(filters.Regex("^(📂 Categories|📦 Order History|💰 Wallet)$"), main_menu_handler))
    app.add_handler(MessageHandler(filters.REPLY & filters.ChatType.PRIVATE & filters.User(ADMIN_ID), admin_reply_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE & filters.User(ADMIN_ID), admin_text_handler))
    
    # Search handler MUST come before direct_order and unknown handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, search_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, direct_order_text_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, unknown_message_handler))
    
    app.job_queue.run_repeating(check_orders_status, interval=180, first=15)
    
    print("🤖 SMM Panel Bot Started with Server 1/2 Selection!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
