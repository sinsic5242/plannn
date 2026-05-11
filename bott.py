# -*- coding: utf-8 -*-
import json
import os
import time
import threading
from datetime import datetime
from vk_api import VkApi
from vk_api.utils import get_random_id
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

# ========== НОВЫЕ ДАННЫЕ ==========
VK_TOKEN = "vk1.a.EbSYpn3rfQTbNf38pAZZh4UBzo1AVAX8aL8lfpa9jRPgxS42rU_VSCcsYG3ZRBv6m4slxy6GWk8HxsNqoFwedcirLv8WpsGBt20-SlxN9MihjWLxubeuj3KwUTVA4T9guFs6FRArlUiS_7f7sbgr1OMa8KqKu4xsw4gw0xFCpAWt0bOPnH7cEMI_TkmNYrzzbORfKFqhGzRcDNRuHeq94Q"
GROUP_ID = 238603745
# ==================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "plans.json")

# Загружаем планы
if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        plans = json.load(f)
else:
    plans = {}
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)

def save_plans():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(plans, f)

def send_message(vk, peer_id, text, keyboard=None):
    params = {"peer_id": peer_id, "message": text, "random_id": get_random_id()}
    if keyboard:
        params["keyboard"] = keyboard
    vk.messages.send(**params)

def get_main_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("📝 Add plan", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("📋 My plans", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("🗑 Delete plan", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("❓ Help", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

def get_cancel_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("❌ Cancel", color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()

user_states = {}

def add_plan(user_id, target_date, time_str, description):
    if str(user_id) not in plans:
        plans[str(user_id)] = []
    new_id = len(plans[str(user_id)]) + 1
    plan = {
        "id": new_id,
        "date": target_date,
        "time": time_str,
        "description": description,
        "created": datetime.now().isoformat()
    }
    plans[str(user_id)].append(plan)
    save_plans()
    return plan

def get_user_plans(user_id):
    return plans.get(str(user_id), [])

def delete_plan(user_id, plan_id):
    if str(user_id) in plans:
        plans[str(user_id)] = [p for p in plans[str(user_id)] if p.get("id") != plan_id]
        save_plans()
        return True
    return False

def format_plans_list(plans_list):
    if not plans_list:
        return "📭 You have no plans yet"
    result = "📋 *Your plans:*\n\n"
    for p in plans_list:
        result += f"🆔 {p['id']} | 📅 {p['date']} | ⏰ {p['time']}\n📌 {p['description']}\n\n"
    result += "To delete: `delete ID`"
    return result

def check_reminders(vk):
    while True:
        try:
            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M")
            for user_id, user_plans in plans.items():
                for plan in user_plans:
                    if plan.get("date") == current_date and plan.get("time") == current_time:
                        send_message(vk, int(user_id), f"🔔 *REMINDER!*\n\n{plan['description']}")
                        print(f"Sent reminder to {user_id}: {plan['description']}")
            time.sleep(60)
        except Exception as e:
            print(f"Reminder error: {e}")
            time.sleep(60)

print("🤖 BOT STARTING...")
print("-" * 40)

vk_session = VkApi(token=VK_TOKEN)
vk = vk_session.get_api()

print(f"✅ Bot connected to VK!")
print(f"📌 Group ID: {GROUP_ID}")
print("💬 Send any message to the community")
print("=" * 50)

reminder_thread = threading.Thread(target=check_reminders, args=(vk,), daemon=True)
reminder_thread.start()
print("✅ Reminder scheduler started!")

while True:
    try:
        response = vk.messages.getConversations(count=200, filter="unread")
        for item in response.get("items", []):
            msg = item.get("last_message", {})
            if not msg:
                continue
            text = msg.get("text", "").strip()
            peer_id = msg.get("peer_id")
            user_id = str(msg.get("from_id"))
            if not text or not peer_id:
                continue
            
            print(f"📨 {user_id}: {text[:50]}")
            
            if user_id in user_states:
                if text == "❌ Cancel" or text.lower() == "cancel":
                    del user_states[user_id]
                    send_message(vk, peer_id, "❌ Cancelled", get_main_keyboard())
                elif user_states[user_id]["step"] == "waiting_date":
                    user_states[user_id]["date"] = text
                    user_states[user_id]["step"] = "waiting_time"
                    send_message(vk, peer_id, "Enter time (HH:MM):", get_cancel_keyboard())
                elif user_states[user_id]["step"] == "waiting_time":
                    user_states[user_id]["time"] = text
                    user_states[user_id]["step"] = "waiting_desc"
                    send_message(vk, peer_id, "Enter description:", get_cancel_keyboard())
                elif user_states[user_id]["step"] == "waiting_desc":
                    add_plan(user_id, user_states[user_id]["date"], user_states[user_id]["time"], text)
                    del user_states[user_id]
                    send_message(vk, peer_id, "✅ Plan added!", get_main_keyboard())
                continue
            
            if text.lower() in ["add plan", "add", "📝 add plan"]:
                user_states[user_id] = {"step": "waiting_date"}
                send_message(vk, peer_id, "✏️ Enter date (YYYY-MM-DD):", get_cancel_keyboard())
            elif text.lower() in ["my plans", "plans", "list", "📋 my plans"]:
                send_message(vk, peer_id, format_plans_list(get_user_plans(user_id)), get_main_keyboard())
            elif text.lower().startswith("delete"):
                parts = text.split()
                if len(parts) == 2 and parts[1].isdigit():
                    if delete_plan(user_id, int(parts[1])):
                        send_message(vk, peer_id, "✅ Plan deleted!", get_main_keyboard())
                    else:
                        send_message(vk, peer_id, "❌ Plan not found", get_main_keyboard())
                else:
                    send_message(vk, peer_id, "❌ Send: `delete ID` (e.g., delete 3)", get_main_keyboard())
            elif text.lower() in ["help", "start", "❓ help"]:
                help_text = """🤖 *Planner Bot Commands*

📝 *Add plan* — create a new task
📋 *My plans* — view all tasks
🗑 *delete ID* — delete a task
❓ *Help* — show this message

*Example:*
1. Add plan
2. 2025-05-15
3. 18:00
4. Gym"""
                send_message(vk, peer_id, help_text, get_main_keyboard())
            else:
                send_message(vk, peer_id, "👋 Send *Help* for commands", get_main_keyboard())
        time.sleep(2)
    except Exception as e:
        print(f"❌ Error: {e}")
        time.sleep(5)
