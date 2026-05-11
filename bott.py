# -*- coding: utf-8 -*-
import json
import os
import time
import threading
import re
from datetime import datetime, timedelta
from vk_api import VkApi
from vk_api.utils import get_random_id
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

# ========== ВАШИ ДАННЫЕ ==========
VK_GROUP_TOKEN = "vk1.a.fCWJs3My8jJsg9_sM0btIelqMouuIcmHk-c-bEQ7W8q7LS9WWJW7rAvv3IV1FnRSU4hBsDAt78FyjxLlCee3beW97uilIc5s70J2yYZDbHBa1kIi4UeBOqmUX1miPRnNfIjT6E6YpGh_r5Kkllhycbb_VGpYB3vPhJtMiHfPcOFa_zkJ5bs7UYiK93RWNCIQrK7XzKqDKhHLTF26pDJ6dQ"
GROUP_ID = 238582845
# ==================================

# Определяем путь к файлу с данными
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "plans.json")

plans = {}

# Безопасная загрузка планов
if os.path.exists(DATA_FILE):
    try:
        if os.path.getsize(DATA_FILE) > 0:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                plans = json.load(f)
        else:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        plans = {}
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
else:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

def save_plans():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(plans, f, ensure_ascii=False, indent=2)

def send_message(vk, peer_id, text, keyboard=None):
    params = {
        "peer_id": peer_id,
        "message": text,
        "random_id": get_random_id(),
        "parse_mode": 'Markdown'
    }
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

def parse_date(date_text):
    date_text = date_text.lower().strip()
    now = datetime.now()
    
    if date_text == "tomorrow" or date_text == "завтра":
        return now + timedelta(days=1)
    if date_text == "day after tomorrow" or date_text == "послезавтра":
        return now + timedelta(days=2)
    if date_text == "today" or date_text == "сегодня":
        return now
    
    patterns = [
        r'^(\d{1,2})[\.\s]+(\d{1,2})$',
        r'^(\d{1,2})[\.\s]+(\d{1,2})[\.\s]+(\d{4})$',
    ]
    
    for pattern in patterns:
        match = re.match(pattern, date_text)
        if match:
            groups = match.groups()
            if len(groups) == 2:
                day = int(groups[0])
                month = int(groups[1])
                year = now.year
            else:
                day = int(groups[0])
                month = int(groups[1])
                year = int(groups[2])
            
            try:
                target_date = datetime(year, month, day)
                if target_date.date() < now.date():
                    target_date = datetime(year + 1, month, day)
                return target_date
            except ValueError:
                return None
    return None

def get_weekday_name(date_obj):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return days[date_obj.weekday()]

def format_date_for_display(date_obj):
    months = ["January", "February", "March", "April", "May", "June", 
              "July", "August", "September", "October", "November", "December"]
    return f"{date_obj.day} {months[date_obj.month-1]}"

def add_plan(user_id, target_date, time_str, description):
    if str(user_id) not in plans:
        plans[str(user_id)] = []
    
    new_id = 1
    for p in plans[str(user_id)]:
        if p.get("id", 0) >= new_id:
            new_id = p["id"] + 1
    
    plan = {
        "id": new_id,
        "date": target_date.date().isoformat(),
        "day": get_weekday_name(target_date),
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
        original_count = len(plans[str(user_id)])
        plans[str(user_id)] = [p for p in plans[str(user_id)] if p.get("id") != plan_id]
        if len(plans[str(user_id)]) < original_count:
            save_plans()
            return True
    return False

def format_plans_list(plans_list):
    if not plans_list:
        return "📭 You have no plans yet"
    
    plans_list.sort(key=lambda x: (x["date"], x["time"]))
    
    result = "📋 *Your plans:*\n\n"
    current_date = None
    for plan in plans_list:
        if plan["date"] != current_date:
            current_date = plan["date"]
            date_obj = datetime.fromisoformat(plan["date"])
            result += f"\n*{get_weekday_name(date_obj)} {format_date_for_display(date_obj)}:*\n"
        result += f"  {plan['time']} — {plan['description']}  (id: {plan['id']})\n"
    
    result += "\nTo delete a plan, send: `delete ID`"
    return result

def check_reminders(vk):
    while True:
        try:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            current_date = now.date().isoformat()
            
            for user_id, user_plans in list(plans.items()):
                for plan in user_plans:
                    if plan.get("date") == current_date and plan.get("time") == current_time:
                        date_obj = datetime.fromisoformat(plan["date"])
                        send_message(
                            vk, 
                            int(user_id), 
                            f"🔔 *REMINDER!*\n\n{get_weekday_name(date_obj)} {format_date_for_display(date_obj)} at {plan['time']}:\n📌 {plan['description']}"
                        )
                        print(f"Sent reminder to {user_id}: {plan['description']}")
            time.sleep(60)
        except Exception as e:
            print(f"Reminder error: {e}")
            time.sleep(60)

def handle_add_plan_start(vk, peer_id, user_id):
    user_states[user_id] = {"step": "waiting_date"}
    send_message(vk, peer_id, 
        "📝 *Create plan*\n\n"
        "Enter the **date**:\n"
        "• *tomorrow*\n"
        "• *15 march* or *15.03*\n"
        "• *15.03.2025*\n\n"
        "Or press Cancel", 
        get_cancel_keyboard())

def handle_add_plan_date(vk, peer_id, user_id, date_text):
    target_date = parse_date(date_text)
    
    if target_date is None:
        send_message(vk, peer_id, 
            "❌ Cannot recognize date.\n\n"
            "Try:\n"
            "• *tomorrow*\n"
            "• *15 march*\n"
            "• *15.03*\n\n"
            "Or press Cancel", 
            get_cancel_keyboard())
        return
    
    if target_date.date() < datetime.now().date():
        send_message(vk, peer_id, 
            f"❌ Date *{format_date_for_display(target_date)}* has passed.\n\n"
            "Please choose a future date.\n\n"
            "Or press Cancel", 
            get_cancel_keyboard())
        return
    
    user_states[user_id] = {"step": "waiting_time", "date": target_date.isoformat()}
    send_message(vk, peer_id, 
        f"📝 Date: *{get_weekday_name(target_date)} {format_date_for_display(target_date)}*\n\n"
        "Now enter **time** in HH:MM format (e.g., 18:00)\n\n"
        "Or press Cancel", 
        get_cancel_keyboard())

def handle_add_plan_time(vk, peer_id, user_id, time_str):
    if ":" not in time_str:
        send_message(vk, peer_id, "❌ Invalid format. Send time as HH:MM (e.g., 18:00)", get_cancel_keyboard())
        return
    
    parts = time_str.split(":")
    if len(parts) != 2:
        send_message(vk, peer_id, "❌ Invalid format. Send time as HH:MM (e.g., 18:00)", get_cancel_keyboard())
        return
    
    hour, minute = parts
    if not hour.isdigit() or not minute.isdigit() or int(hour) > 23 or int(minute) > 59:
        send_message(vk, peer_id, "❌ Invalid time. Hours 0-23, minutes 0-59", get_cancel_keyboard())
        return
    
    user_states[user_id]["step"] = "waiting_desc"
    user_states[user_id]["time"] = time_str
    send_message(vk, peer_id, 
        f"📝 Date: *{datetime.fromisoformat(user_states[user_id]['date']).strftime('%A, %d %B')}*\n"
        f"⏰ Time: *{time_str}*\n\n"
        "Enter **description** of the task\n\n"
        "Or press Cancel", 
        get_cancel_keyboard())

def handle_add_plan_desc(vk, peer_id, user_id, desc):
    target_date = datetime.fromisoformat(user_states[user_id]["date"])
    time_str = user_states[user_id]["time"]
    
    plan = add_plan(user_id, target_date, time_str, desc)
    send_message(vk, peer_id, 
        f"✅ *Plan added!*\n\n"
        f"📅 *{get_weekday_name(target_date)} {format_date_for_display(target_date)}*\n"
        f"⏰ *{time_str}*\n"
        f"📌 *{desc}*\n\n"
        f"Plan ID: {plan['id']}\n\n"
        f"🔔 I will remind you at the scheduled time!", 
        get_main_keyboard())
    
    del user_states[user_id]

def handle_cancel(vk, peer_id, user_id):
    if user_id in user_states:
        del user_states[user_id]
    send_message(vk, peer_id, "❌ Plan creation cancelled", get_main_keyboard())

print("\n🤖 BOT STARTING")
print("-" * 40)

vk_session = VkApi(token=VK_GROUP_TOKEN)
vk = vk_session.get_api()

print("✅ Bot connected to VK!")
print("💬 Send any message to the community")
print("🛑 Press Ctrl+C to stop")
print("="*50 + "\n")

reminder_thread = threading.Thread(target=check_reminders, args=(vk,), daemon=True)
reminder_thread.start()
print("✅ Reminder scheduler started!")

while True:
    try:
        response = vk.messages.getConversations(count=200, filter="unread")
        for item in response.get('items', []):
            msg = item.get('last_message', {})
            if not msg:
                continue
            
            text = msg.get('text', '').strip()
            peer_id = msg.get('peer_id')
            user_id = str(msg.get('from_id'))
            
            if not text or not peer_id:
                continue
            
            print(f"📨 {user_id}: {text[:50]}")
            
            if user_id in user_states:
                state = user_states[user_id]
                
                if text == "❌ Cancel":
                    handle_cancel(vk, peer_id, user_id)
                elif state["step"] == "waiting_date":
                    handle_add_plan_date(vk, peer_id, user_id, text)
                elif state["step"] == "waiting_time":
                    handle_add_plan_time(vk, peer_id, user_id, text)
                elif state["step"] == "waiting_desc":
                    handle_add_plan_desc(vk, peer_id, user_id, text)
                continue
            
            if text in ["📝 Add plan", "add plan", "add", "new plan", "new"]:
                handle_add_plan_start(vk, peer_id, user_id)
            
            elif text in ["📋 My plans", "my plans", "plans", "list"]:
                user_plans = get_user_plans(user_id)
                send_message(vk, peer_id, format_plans_list(user_plans), get_main_keyboard())
            
            elif text in ["🗑 Delete plan", "delete plan", "delete"]:
                user_plans = get_user_plans(user_id)
                if not user_plans:
                    send_message(vk, peer_id, "📭 You have no plans to delete", get_main_keyboard())
                else:
                    send_message(vk, peer_id, 
                        f"🗑 *Delete plan*\n\n"
                        f"To delete a plan, send:\n`delete ID`\n\n"
                        f"Your plans:\n{format_plans_list(user_plans)}", 
                        get_main_keyboard())
            
            elif text.lower().startswith("delete"):
                parts = text.split()
                if len(parts) == 2 and parts[1].isdigit():
                    plan_id = int(parts[1])
                    if delete_plan(user_id, plan_id):
                        send_message(vk, peer_id, f"✅ Plan with ID {plan_id} deleted!", get_main_keyboard())
                    else:
                        send_message(vk, peer_id, f"❌ Plan with ID {plan_id} not found", get_main_keyboard())
                else:
                    send_message(vk, peer_id, "❌ Send: `delete ID` (e.g., delete 3)", get_main_keyboard())
            
            elif text in ["❓ Help", "help", "start"]:
                help_text = """🤖 *Planner Bot*

📝 *Add plan* — create a new task
📋 *My plans* — view all tasks
🗑 *Delete plan* — delete a task by ID

*Date formats:*
• tomorrow
• 15 march or 15.03
• 15.03.2025

*Example:*
1. "Add plan"
2. "tomorrow"
3. "18:00"
4. "Gym"

Done! 🔔"""
                send_message(vk, peer_id, help_text, get_main_keyboard())
            
            else:
                send_message(vk, peer_id, 
                    "👋 *Welcome!*\n\n"
                    "I'm a planner bot. I'll help you remember important tasks.\n\n"
                    "Press *«Add plan»* or type *«Help»*.", 
                    get_main_keyboard())
        
        time.sleep(2)
        
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)