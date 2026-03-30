import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import sqlite3
import random
import string
import os
import time
from datetime import datetime
from flask import Flask
import threading
import requests

# Yahan apna bot token dalein
TOKEN = '8579040508:AAE42DeIKIie05ZKZHRpQsEDa2pFE2_JWWY'
bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

ADMIN_ID = 1484173564
APPROVAL_CHANNEL = "@ValiModes_key"
PROOF_CHANNEL = "@ValiModes_Proofs" 

GPLINKS_API = 'B18249211d7c30c6913544160bc04bffeb0b8408'

# ================= DATABASE SETUP =================
conn = sqlite3.connect('webseries_bot.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS channels (channel_id TEXT, link TEXT)''')
try: c.execute("ALTER TABLE channels ADD COLUMN style TEXT DEFAULT 'primary'")
except: pass 

c.execute('''CREATE TABLE IF NOT EXISTS join_reqs (user_id INTEGER, channel_id TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, join_date TEXT, coins INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0, last_bonus REAL DEFAULT 0)''')
c.execute('''CREATE TABLE IF NOT EXISTS pending_refs (user_id INTEGER PRIMARY KEY, referrer_id INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS completed_refs (user_id INTEGER PRIMARY KEY, referrer_id INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS vip_keys (key_code TEXT PRIMARY KEY, duration INTEGER, status TEXT DEFAULT 'UNUSED', used_by INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, value TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS promo_codes (code TEXT PRIMARY KEY, reward INTEGER, max_uses INTEGER, used_count INTEGER DEFAULT 0)''')
c.execute('''CREATE TABLE IF NOT EXISTS promo_users (user_id INTEGER, code TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS active_tasks (user_id INTEGER PRIMARY KEY, task_id TEXT)''')

c.execute("INSERT OR IGNORE INTO settings (name, value) VALUES ('key_link', 'https://www.mediafire.com/file/if3uvvwjbj87lo2/DRIPCLIENT_v6.2_GLOBAL_AP.apks/file')")
c.execute("INSERT OR IGNORE INTO settings (name, value) VALUES ('base_price', '15')") 
c.execute("INSERT OR IGNORE INTO settings (name, value) VALUES ('yt_channel', 'none')") # YouTube Force Sub
conn.commit()

user_last_msg = {}
verify_spam = {} 
temp_channel_data = {}

def flood_check(user_id):
    now = time.time()
    if user_id in user_last_msg and now - user_last_msg[user_id] < 1.0: return True
    user_last_msg[user_id] = now
    return False

def is_user_banned(user_id):
    c.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,))
    res = c.fetchone()
    return res and res[0] == 1

# ================= FLASK WEB DASHBOARD =================
app = Flask(__name__)
@app.route('/')
def home(): return "V5.3 God-Level Bot is Running! Sab set hai bhai."

@app.route('/vip-panel')
def vip_panel():
    conn_db = sqlite3.connect('webseries_bot.db', check_same_thread=False)
    cur = conn_db.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    tot_users = cur.fetchone()[0]
    html = f"""
    <html>
    <head><title>ValiMods VIP Dashboard</title>
    <style>body{{background-color:#121212;color:#00ffcc;font-family:Arial;text-align:center;padding:50px;}}
    .box{{border:2px solid #00ffcc;padding:20px;border-radius:10px;display:inline-block;}}</style></head>
    <body>
    <h1>👨‍💻 ValiMods VIP Server</h1>
    <div class="box"><h2>👥 Total Users: {tot_users}</h2><p>Bot is 100% Active and securing keys!</p></div>
    </body></html>
    """
    return html

def run_web(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))


# ================= 👨‍💻 VIP ADMIN COMMANDS =================
@bot.message_handler(commands=['admin', 'check', 'addcoins'])
def admin_super_commands(message):
    if message.chat.id != ADMIN_ID: return
    cmd = message.text.split()[0]

    if cmd == '/admin':
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton("➕ Add Channel", callback_data="add_channel"),
                   InlineKeyboardButton("➖ Remove Channel", callback_data="remove_channel"))
        markup.add(InlineKeyboardButton("📋 View Added Channels", callback_data="view_channels"),
                   InlineKeyboardButton("📊 Stats & Users", callback_data="adm_stats"))
        markup.add(InlineKeyboardButton("🎥 Set YT Channel", callback_data="set_yt"),
                   InlineKeyboardButton("📢 PRO Broadcast", callback_data="adm_broadcast"))
        bot.send_message(message.chat.id, "👨‍💻 <b>Admin Panel V5.3</b>", reply_markup=markup)

    elif cmd == '/check':
        try:
            uid = int(message.text.split()[1])
            c.execute("SELECT coins, join_date, is_banned FROM users WHERE user_id=?", (uid,))
            user = c.fetchone()
            if not user: return bot.reply_to(message, "❌ User database mein nahi hai.")
            c.execute("SELECT COUNT(*) FROM completed_refs WHERE referrer_id=?", (uid,))
            refs = c.fetchone()[0]
            bot.reply_to(message, f"🕵️ <b>User Details:</b>\n🆔 ID: <code>{uid}</code>\n💰 Coins: {user[0]}\n📅 Joined: {user[1]}\n👥 Total Referrals: {refs}")
        except: bot.reply_to(message, "❌ Format: `/check USER_ID`")

    elif cmd == '/addcoins':
        try:
            _, uid, amt = message.text.split()
            c.execute("UPDATE users SET coins = coins + ? WHERE user_id=?", (int(amt), int(uid)))
            conn.commit()
            bot.reply_to(message, f"✅ {amt} Coins added to {uid}!")
            bot.send_message(int(uid), f"🎁 Admin ne aapko <b>{amt} Coins</b> gift kiye hain!")
        except: bot.reply_to(message, "❌ Format: `/addcoins USER_ID AMOUNT`")

@bot.callback_query_handler(func=lambda call: call.data in ["add_channel", "remove_channel", "view_channels", "set_yt"] or call.data.startswith("adm_") or call.data.startswith("style_"))
def admin_callbacks(call):
    if call.message.chat.id != ADMIN_ID: return
    
    if call.data == "set_yt":
        msg = bot.send_message(call.message.chat.id, "🎥 <b>YouTube Sub-to-Unlock:</b>\nApne YouTube channel ka link bhejo.\n<i>(Band karne ke liye 'none' likho)</i>")
        bot.register_next_step_handler(msg, process_yt)
        
    elif call.data.startswith("style_"):
        style = call.data.split("_")[1]
        data = temp_channel_data.get(call.message.chat.id)
        if data:
            c.execute("INSERT INTO channels (channel_id, link, style) VALUES (?, ?, ?)", (data['ch_id'], data['link'], style))
            conn.commit()
            bot.edit_message_text(f"✅ Channel <code>{data['ch_id']}</code> added!", chat_id=call.message.chat.id, message_id=call.message.message_id)
            del temp_channel_data[call.message.chat.id]
        return
    elif call.data == "add_channel":
        msg = bot.send_message(call.message.chat.id, "🤖 Bot ko channel me Admin banao!\nPhir Channel ID send karo:")
        bot.register_next_step_handler(msg, process_add_channel)
    elif call.data == "view_channels":
        c.execute("SELECT channel_id, link, style FROM channels")
        channels = c.fetchall()
        c.execute("SELECT value FROM settings WHERE name='yt_channel'")
        yt = c.fetchone()[0]
        text = f"▶️ <b>YT Force Sub:</b> {yt}\n\n📋 <b>Added Channels:</b>\n\n"
        for ch in channels: text += f"ID: <code>{ch[0]}</code>\n🎨 Color: {ch[2].upper()}\nLink: {ch[1]}\n\n"
        bot.send_message(call.message.chat.id, text, disable_web_page_preview=True)
    elif call.data == "remove_channel":
        msg = bot.send_message(call.message.chat.id, "🗑️ Channel ID bhejo:")
        bot.register_next_step_handler(msg, lambda m: [c.execute("DELETE FROM channels WHERE channel_id=?", (m.text.strip(),)), conn.commit(), bot.send_message(m.chat.id, "✅ Removed!")])
    elif call.data == "adm_stats":
        c.execute("SELECT COUNT(*) FROM users")
        tot = c.fetchone()[0]
        bot.send_message(call.message.chat.id, f"📊 <b>BOT STATS</b>\n👥 Total Users: {tot}")
    elif call.data == "adm_broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 <b>PRO Broadcast:</b>\nKoi bhi Media (Photo/Video) ya Text bhejo:")
        bot.register_next_step_handler(msg, process_broadcast)

def process_yt(message):
    link = message.text.strip()
    c.execute("UPDATE settings SET value=? WHERE name='yt_channel'", (link,))
    conn.commit()
    bot.send_message(message.chat.id, f"✅ YouTube Link Updated: {link}")

def process_add_channel(message):
    ch_id = message.text.strip()
    try:
        invite_link = bot.create_chat_invite_link(ch_id, creates_join_request=True).invite_link
        temp_channel_data[message.chat.id] = {'ch_id': ch_id, 'link': invite_link}
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton("🔵 Blue", callback_data="style_primary"), InlineKeyboardButton("🟢 Green", callback_data="style_success"), InlineKeyboardButton("🔴 Red", callback_data="style_danger"), InlineKeyboardButton("⚪ Grey", callback_data="style_secondary"))
        bot.send_message(message.chat.id, "🎨 <b>Color choose karein:</b>", reply_markup=markup)
    except Exception as e: bot.send_message(message.chat.id, f"❌ Error: {e}")

def process_broadcast(message):
    c.execute("SELECT user_id FROM users WHERE is_banned=0")
    sent = 0
    for u in c.fetchall():
        try: 
            bot.copy_message(u[0], message.chat.id, message.message_id)
            sent += 1
            time.sleep(0.05)
        except: pass
    bot.send_message(message.chat.id, f"✅ Broadcast Done! Sent to {sent} users.")

# ================= USER FEATURES (COIN TRANSFER) =================
@bot.message_handler(commands=['pay'])
def pay_coins(message):
    uid = message.from_user.id
    try:
        parts = message.text.split()
        target_id = int(parts[1])
        amount = int(parts[2])
        if amount <= 0: return bot.reply_to(message, "❌ Amount sahi daalo!")
        
        c.execute("SELECT coins FROM users WHERE user_id=?", (uid,))
        my_coins = c.fetchone()[0]
        if my_coins < amount: return bot.reply_to(message, "❌ Itne coins nahi hain!")

        c.execute("UPDATE users SET coins = coins - ? WHERE user_id=?", (amount, uid))
        c.execute("UPDATE users SET coins = coins + ? WHERE user_id=?", (amount, target_id))
        conn.commit()
        bot.reply_to(message, f"✅ Successfully sent <b>{amount} Coins</b> to <code>{target_id}</code>!")
        bot.send_message(target_id, f"💸 Aapko ID <code>{uid}</code> se <b>{amount} Coins</b> mile hain!")
    except: bot.reply_to(message, "❌ Format: `/pay USER_ID AMOUNT`")

# ================= JOIN REQUEST & FORCE SUB SYSTEM (GRID LAYOUT) =================
def get_unjoined_channels(user_id):
    try: c.execute("SELECT channel_id, link FROM channels")
    except: c.execute("SELECT channel_id, link FROM channels")
    channels = c.fetchall()
    unjoined = []
    for ch in channels:
        joined = False
        try:
            if bot.get_chat_member(ch[0], user_id).status in ['member', 'administrator', 'creator']: joined = True
        except: pass
        if not joined:
            c.execute("SELECT * FROM join_reqs WHERE user_id=? AND channel_id=?", (user_id, ch[0]))
            if c.fetchone(): joined = True
        if not joined: unjoined.append(ch)
    return unjoined

def check_user_status(user_id):
    return len(get_unjoined_channels(user_id)) == 0

@bot.chat_join_request_handler()
def handle_join_request(message: telebot.types.ChatJoinRequest):
    c.execute("INSERT INTO join_reqs (user_id, channel_id) VALUES (?, ?)", (message.from_user.id, str(message.chat.id)))
    conn.commit()

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    if is_user_banned(uid): return

    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, username, join_date) VALUES (?, ?, ?)", (uid, message.from_user.username or "Unknown", datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
        
    args = message.text.split()
    if len(args) > 1:
        param = args[1]
        if param.startswith("task_"):
            task_id = param.replace("task_", "")
            c.execute("SELECT * FROM active_tasks WHERE user_id=? AND task_id=?", (uid, task_id))
            if c.fetchone():
                c.execute("DELETE FROM active_tasks WHERE user_id=?", (uid,))
                c.execute("UPDATE users SET coins = coins + 5 WHERE user_id=?", (uid,)) 
                conn.commit()
                bot.send_message(uid, "🎉 <b>Task Done!</b> +5 Coins added.")
        elif param.isdigit():
            ref_id = int(param)
            if ref_id != uid:
                c.execute("SELECT * FROM completed_refs WHERE user_id=?", (uid,))
                if not c.fetchone():
                    c.execute("UPDATE users SET coins = coins + 2 WHERE user_id=?", (ref_id,))
                    c.execute("INSERT INTO completed_refs (user_id, referrer_id) VALUES (?, ?)", (uid, ref_id))
                    conn.commit()
                    try: bot.send_message(ref_id, "🎉 Referral successful! +2 Coins.")
                    except: pass
                    
    send_force_sub(message.chat.id, uid)

def send_force_sub(chat_id, user_id):
    unjoined = get_unjoined_channels(user_id)
    c.execute("SELECT value FROM settings WHERE name='yt_channel'")
    yt_link = c.fetchone()[0]
    
    if not unjoined and yt_link.lower() == 'none':
        send_main_menu(chat_id)
        return
        
    # 🔥 3 BUTTONS PER ROW GRID 🔥
    markup = InlineKeyboardMarkup(row_width=3)
    btns = []
    for i, ch in enumerate(unjoined):
        btns.append(InlineKeyboardButton(f"Join {i+1}", url=ch[1]))
    
    markup.add(*btns) # Isse 3-3 buttons line mein aayenge
    
    if yt_link.lower() != 'none':
        markup.row(InlineKeyboardButton("▶️ Subscribe YouTube (Zaroori)", url=yt_link))

    markup.row(InlineKeyboardButton("✅ Done !!", callback_data="verify_channels"))
    
    bot.send_video(chat_id, "https://files.catbox.moe/4hbu2q.mp4", caption="💎 𝗪𝗘𝗟𝗖𝗢𝗠𝗘 𝗧𝗢 𝗩𝗔𝗟𝗜 𝗠𝗢𝗗𝗦\n\nSaare channels join karke Done dabayein!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "verify_channels")
def verify_callback(call):
    if not get_unjoined_channels(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_main_menu(call.message.chat.id)
    else: bot.answer_callback_query(call.id, "❌ Pehle saare channels join karo!", show_alert=True)


# ================= MAIN MENU & VIP FEATURES =================
def send_main_menu(chat_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("👤 My Account"), KeyboardButton("🔗 Refer & Earn"))
    markup.add(KeyboardButton("💸 Earn Free Coins"), KeyboardButton("🛒 VIP Key Shop")) 
    markup.add(KeyboardButton("🎲 Play Game"), KeyboardButton("🎬 AI Story Script")) 
    markup.add(KeyboardButton("🎁 Daily Bonus"), KeyboardButton("🎟️ Redeem Promo"))
    bot.send_message(chat_id, "✅ Use the menu below to navigate:", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def text_commands(message):
    uid = message.from_user.id
    if not check_user_status(uid): return send_force_sub(message.chat.id, uid)
    
    c.execute("SELECT coins, last_bonus FROM users WHERE user_id=?", (uid,))
    coins, last_bonus = c.fetchone()
    text = message.text

    if text == "👤 My Account":
        bot.send_message(uid, f"👤 <b>Account</b>\n🆔 ID: <code>{uid}</code>\n💰 Coins: <b>{coins}</b>")
        
    elif text == "🔗 Refer & Earn":
        bot.send_message(uid, f"📢 Invite and get 2 Coins!\nLink: https://t.me/{bot.get_me().username}?start={uid}")

    elif text == "🎁 Daily Bonus":
        now = time.time()
        if now - float(last_bonus) > 86400:
            c.execute("UPDATE users SET coins = coins + 2, last_bonus = ? WHERE user_id=?", (now, uid))
            conn.commit()
            bot.send_message(uid, "🎉 +2 Coins Claimed!")
        else: bot.send_message(uid, "⏳ Aaj ka bonus le liya hai. Kal aana!")

    elif text == "🎲 Play Game":
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("HEADS", callback_data="flip_heads"), InlineKeyboardButton("TAILS", callback_data="flip_tails"))
        bot.send_message(uid, "🎲 <b>Coin Flip (Bet: 5 Coins)</b>\nSahi guess par coins double!", reply_markup=markup)

    elif text == "🎬 AI Story Script":
        scripts = ["🎬 Scene: Samosa defeated on highway...", "🎬 Scene: Chutney slow motion saree entry..."]
        bot.send_message(uid, f"🧠 <b>AI Script:</b>\n{random.choice(scripts)}")
        
    elif text == "💸 Earn Free Coins":
        tid = ''.join(random.choices(string.ascii_letters, k=8))
        c.execute("INSERT OR REPLACE INTO active_tasks VALUES (?, ?)", (uid, tid))
        conn.commit()
        dest = f"https://t.me/{bot.get_me().username}?start=task_{tid}"
        res = requests.get(f"https://gplinks.in/api?api={GPLINKS_API}&url={dest}").json()
        if res.get('status') == 'success':
            bot.send_message(uid, "💸 Click button and skip ads for 5 coins:", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("Open Task", url=res['shortenedUrl'])))

    elif text == "🛒 VIP Key Shop":
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("Buy 1-Day Key (15 Coins)", callback_data="buy_1_15"))
        bot.send_message(uid, "🛒 VIP Key Shop:", reply_markup=markup)

    else:
        # 🔥 SMART AI CHATBOT AUTO-REPLY 🔥
        msg = text.lower()
        if any(x in msg for x in ["hi", "hello", "hey", "kaise"]):
            bot.reply_to(message, "Hello! Main ValiMods VIP Assistant hoon. Menu buttons ka use karein! 😊")
        elif "key" in msg:
            bot.reply_to(message, "Key lene ke liye 'Shop' mein jayein. Coins chahiye toh Task poora karein! 🔥")
        else: bot.reply_to(message, "Theek hai! Bot ko use karne ke liye niche ke buttons dabayein. 🤖")

# ================= GAME & SHOP LOGIC =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("flip_"))
def handle_flip(call):
    uid = call.from_user.id
    c.execute("SELECT coins FROM users WHERE user_id=?", (uid,))
    coins = c.fetchone()[0]
    if coins < 5: return bot.answer_callback_query(call.id, "❌ Minimum 5 coins chahiye!", show_alert=True)
    
    res = random.choice(["heads", "tails"])
    guess = call.data.split("_")[1]
    bot.delete_message(call.message.chat.id, call.message.message_id)
    if guess == res:
        c.execute("UPDATE users SET coins = coins + 5 WHERE user_id=?", (uid,))
        bot.send_message(uid, f"🎉 <b>Result: {res.upper()}!</b> Tum jeet gaye! +5 Coins.")
    else:
        c.execute("UPDATE users SET coins = coins - 5 WHERE user_id=?", (uid,))
        bot.send_message(uid, f"😢 <b>Result: {res.upper()}!</b> Tum haar gaye. -5 Coins.")
    conn.commit()

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def handle_shop_buy(call):
    uid = call.from_user.id
    _, days, price = call.data.split("_")
    price = int(price)
    c.execute("SELECT coins FROM users WHERE user_id=?", (uid,))
    if c.fetchone()[0] >= price:
        c.execute("UPDATE users SET coins = coins - ? WHERE user_id=?", (price, uid))
        conn.commit()
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ APPROVE", callback_data=f"ap_{uid}_{days}"), InlineKeyboardButton("❌ REJECT", callback_data=f"rj_{uid}_{price}"))
        bot.send_message(APPROVAL_CHANNEL, f"🆕 Request from {uid} ({days} Day)", reply_markup=markup)
        bot.send_message(uid, "⏳ Request Sent to Admin!")
    else: bot.answer_callback_query(call.id, "❌ Coins kam hain!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ap_") or call.data.startswith("rj_"))
def handle_approval(call):
    if call.from_user.id != ADMIN_ID: return
    p = call.data.split("_")
    uid, val = int(p[1]), p[2]
    if p[0] == "ap":
        bot.send_message(uid, f"🎉 Approved! Your Key: <code>{random.randint(1000,9999)}</code>")
        bot.send_message(PROOF_CHANNEL, f"✅ Proof: User {uid} got {val} Day VIP Access!")
    else:
        c.execute("UPDATE users SET coins = coins + ? WHERE user_id=?", (int(val), uid))
        conn.commit()
        bot.send_message(uid, "❌ Request Rejected. Coins refunded.")

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    bot.infinity_polling()
