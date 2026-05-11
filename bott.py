# -*- coding: utf-8 -*-
import json
import os
import time
import threading
from datetime import datetime
from vk_api import VkApi
from vk_api.utils import get_random_id
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

# ========== ВАШИ ДАННЫЕ ==========
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
    keyboard.add_button("📝 Добавить план", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("📋 Мои планы", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("🗑 Удалить план", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("❓ Помощь", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

def get_cancel_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("❌ Отмена", color=VkKeyboardColor.NEGATIVE)
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
        return "📭 У вас пока нет планов"
    result = "📋 *Ваши планы:*\n\n"
    for p in plans_list:
        result += f"🆔 {p['id']} | 📅 {p['date']} | ⏰ {p['time']}\n📌 {p['description']}\n\n"
    result += "Чтобы удалить: `удалить ID`"
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
                        send_message(vk, int(user_id), f"🔔 *НАПОМИНАНИЕ!*\n\n{plan['description']}")
                        print(f"Отправлено напоминание {user_id}: {plan['description']}")
            time.sleep(60)
        except Exception as e:
            print(f"Ошибка напоминаний: {e}")
            time.sleep(60)

print("🤖 ЗАПУСК БОТА")
print("-" * 40)

vk_session = VkApi(token=VK_TOKEN)
vk = vk_session.get_api()

print(f"✅ Бот подключен к ВК!")
print(f"📌 ID группы: {GROUP_ID}")
print("💬 Напишите любое сообщение в сообщество")
print("=" * 50)

reminder_thread = threading.Thread(target=check_reminders, args=(vk,), daemon=True)
reminder_thread.start()
print("✅ Планировщик напоминаний запущен!")

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
                if text == "❌ Отмена" or text.lower() == "отмена" or text.lower() == "cancel":
                    del user_states[user_id]
                    send_message(vk, peer_id, "❌ Создание плана отменено", get_main_keyboard())
                elif user_states[user_id]["step"] == "waiting_date":
                    user_states[user_id]["date"] = text
                    user_states[user_id]["step"] = "waiting_time"
                    send_message(vk, peer_id, "⏰ Введите время (ЧЧ:ММ):", get_cancel_keyboard())
                elif user_states[user_id]["step"] == "waiting_time":
                    user_states[user_id]["time"] = text
                    user_states[user_id]["step"] = "waiting_desc"
                    send_message(vk, peer_id, "📝 Введите описание:", get_cancel_keyboard())
                elif user_states[user_id]["step"] == "waiting_desc":
                    add_plan(user_id, user_states[user_id]["date"], user_states[user_id]["time"], text)
                    del user_states[user_id]
                    send_message(vk, peer_id, "✅ План добавлен!", get_main_keyboard())
                continue
            
            if text.lower() in ["добавить план", "добавить", "📝 добавить план", "add plan", "add"]:
                user_states[user_id] = {"step": "waiting_date"}
                send_message(vk, peer_id, "📅 Введите дату (ГГГГ-ММ-ДД):", get_cancel_keyboard())
            elif text.lower() in ["мои планы", "планы", "список", "📋 мои планы", "my plans", "plans", "list"]:
                send_message(vk, peer_id, format_plans_list(get_user_plans(user_id)), get_main_keyboard())
            elif text.lower().startswith("удалить") or text.lower().startswith("delete"):
                parts = text.split()
                if len(parts) == 2 and parts[1].isdigit():
                    if delete_plan(user_id, int(parts[1])):
                        send_message(vk, peer_id, "✅ План удалён!", get_main_keyboard())
                    else:
                        send_message(vk, peer_id, "❌ План не найден", get_main_keyboard())
                else:
                    send_message(vk, peer_id, "❌ Отправьте: `удалить ID` (например: удалить 3)", get_main_keyboard())
            elif text.lower() in ["помощь", "help", "start", "❓ помощь"]:
                help_text = """🤖 *Команды бота-планировщика*

📝 *Добавить план* — создать новую задачу
📋 *Мои планы* — посмотреть все задачи
🗑 *удалить ID* — удалить задачу (например: удалить 3)
❓ *Помощь* — показать это сообщение

*Пример создания плана:*
1. Добавить план
2. 2025-05-15
3. 18:00
4. Пойти в зал

🔔 Бот напомнит в указанное время!"""
                send_message(vk, peer_id, help_text, get_main_keyboard())
            else:
                send_message(vk, peer_id, "👋 Напишите *Помощь* для списка команд", get_main_keyboard())
        time.sleep(2)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        time.sleep(5)
