# -*- coding: utf-8 -*-
import json
import os
import time
import threading
from datetime import datetime, timedelta
import pytz
from vk_api import VkApi
from vk_api.utils import get_random_id
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

# ========== ВАШИ ДАННЫЕ ==========
VK_TOKEN = "vk1.a.EbSYpn3rfQTbNf38pAZZh4UBzo1AVAX8aL8lfpa9jRPgxS42rU_VSCcsYG3ZRBv6m4slxy6GWk8HxsNqoFwedcirLv8WpsGBt20-SlxN9MihjWLxubeuj3KwUTVA4T9guFs6FRArlUiS_7f7sbgr1OMa8KqKu4xsw4gw0xFCpAWt0bOPnH7cEMI_TkmNYrzzbORfKFqhGzRcDNRuHeq94Q"
GROUP_ID = 238603745
# ==================================

# Устанавливаем часовой пояс Москвы
MOSCOW_TZ = pytz.timezone('Europe/Moscow')
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

def get_current_msk_time():
    """Возвращает текущее время по Москве"""
    return datetime.now(MOSCOW_TZ)

def get_current_msk_date():
    """Возвращает текущую дату по Москве в формате ГГГГ-ММ-ДД"""
    return get_current_msk_time().strftime("%Y-%m-%d")

def get_current_msk_time_str():
    """Возвращает текущее время по Москве в формате ЧЧ:ММ"""
    return get_current_msk_time().strftime("%H:%M")

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

def get_reminder_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("⏰ За 30 минут", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("⏰ За 1 час", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("⏰ За 2 часа", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("❌ Отмена", color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()

user_states = {}

def add_plan(user_id, target_date, time_str, description, reminder_minutes):
    if str(user_id) not in plans:
        plans[str(user_id)] = []
    new_id = len(plans[str(user_id)]) + 1
    
    # Вычисляем время напоминания
    reminder_time = None
    if reminder_minutes > 0:
        try:
            plan_datetime = datetime.strptime(f"{target_date} {time_str}", "%Y-%m-%d %H:%M")
            plan_datetime = MOSCOW_TZ.localize(plan_datetime)
            reminder_time = (plan_datetime - timedelta(minutes=reminder_minutes)).strftime("%Y-%m-%d %H:%M")
        except:
            reminder_time = None
    
    plan = {
        "id": new_id,
        "date": target_date,
        "time": time_str,
        "description": description,
        "reminder_minutes": reminder_minutes,
        "reminder_time": reminder_time,
        "reminder_sent": False,
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

def format_reminder_text(minutes):
    if minutes == 30:
        return "⏰ За 30 минут"
    elif minutes == 60:
        return "⏰ За 1 час"
    elif minutes == 120:
        return "⏰ За 2 часа"
    return "Без напоминания"

def format_plans_list(plans_list):
    if not plans_list:
        return "📭 У вас пока нет планов"
    result = "📋 *Ваши планы:*\n\n"
    for p in plans_list:
        reminder_text = format_reminder_text(p.get("reminder_minutes", 0))
        result += f"🆔 {p['id']} | 📅 {p['date']} | ⏰ {p['time']}\n📌 {p['description']}\n🔔 {reminder_text}\n\n"
    result += "Чтобы удалить: `удалить ID`"
    return result

def check_reminders(vk):
    """Проверка и отправка напоминаний (по московскому времени)"""
    print("✅ Планировщик напоминаний запущен (Московское время)")
    while True:
        try:
            # Получаем текущее московское время
            now_msk = get_current_msk_time()
            current_date = now_msk.strftime("%Y-%m-%d")
            current_time = now_msk.strftime("%H:%M")
            
            print(f"⏰ Проверка времени: {current_date} {current_time} (МСК)")
            
            for user_id, user_plans in plans.items():
                for plan in user_plans:
                    # Проверяем основное событие
                    plan_datetime = f"{plan.get('date')} {plan.get('time')}"
                    if plan_datetime == f"{current_date} {current_time}":
                        send_message(vk, int(user_id), f"🔔 *СОБЫТИЕ!*\n\n{plan['description']}")
                        print(f"✅ Отправлено уведомление о событии {user_id}: {plan['description']}")
                    
                    # Проверяем напоминание
                    reminder_time = plan.get("reminder_time")
                    reminder_sent = plan.get("reminder_sent", False)
                    if reminder_time and not reminder_sent:
                        if reminder_time == f"{current_date} {current_time}":
                            minutes = plan.get("reminder_minutes", 0)
                            if minutes == 30:
                                time_text = "Через 30 минут"
                            elif minutes == 60:
                                time_text = "Через 1 час"
                            elif minutes == 120:
                                time_text = "Через 2 часа"
                            else:
                                time_text = "Скоро"
                            
                            send_message(vk, int(user_id), f"🔔 *НАПОМИНАНИЕ!*\n\n{time_text} у вас:\n📌 {plan['description']}")
                            plan["reminder_sent"] = True
                            save_plans()
                            print(f"✅ Отправлено напоминание {user_id}: {plan['description']} ({time_text})")
            
            time.sleep(60)  # Проверяем каждую минуту
        except Exception as e:
            print(f"❌ Ошибка в планировщике: {e}")
            time.sleep(60)

print("🤖 ЗАПУСК БОТА (Московское время)")
print("-" * 40)

vk_session = VkApi(token=VK_TOKEN)
vk = vk_session.get_api()

print(f"✅ Бот подключен к ВК!")
print(f"📌 ID группы: {GROUP_ID}")
print(f"🕐 Текущее время по Москве: {get_current_msk_time().strftime('%Y-%m-%d %H:%M:%S')}")
print("💬 Напишите любое сообщение в сообщество")
print("=" * 50)

reminder_thread = threading.Thread(target=check_reminders, args=(vk,), daemon=True)
reminder_thread.start()

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
                state = user_states[user_id]
                
                if text == "❌ Отмена" or text.lower() == "отмена":
                    del user_states[user_id]
                    send_message(vk, peer_id, "❌ Создание плана отменено", get_main_keyboard())
                
                elif state["step"] == "waiting_date":
                    try:
                        datetime.strptime(text, "%Y-%m-%d")
                        state["date"] = text
                        state["step"] = "waiting_time"
                        send_message(vk, peer_id, "⏰ Введите время (ЧЧ:ММ):", get_cancel_keyboard())
                    except ValueError:
                        send_message(vk, peer_id, "❌ Неверный формат. Введите дату в формате ГГГГ-ММ-ДД (например: 2025-12-31)", get_cancel_keyboard())
                
                elif state["step"] == "waiting_time":
                    try:
                        datetime.strptime(text, "%H:%M")
                        state["time"] = text
                        state["step"] = "waiting_reminder"
                        send_message(vk, peer_id, "🔔 Выберите когда напомнить:", get_reminder_keyboard())
                    except ValueError:
                        send_message(vk, peer_id, "❌ Неверный формат. Введите время в формате ЧЧ:ММ (например: 18:00)", get_cancel_keyboard())
                
                elif state["step"] == "waiting_reminder":
                    if text == "⏰ За 30 минут":
                        reminder_minutes = 30
                    elif text == "⏰ За 1 час":
                        reminder_minutes = 60
                    elif text == "⏰ За 2 часа":
                        reminder_minutes = 120
                    else:
                        send_message(vk, peer_id, "❌ Пожалуйста, выберите вариант из меню", get_reminder_keyboard())
                        continue
                    
                    state["reminder_minutes"] = reminder_minutes
                    state["step"] = "waiting_desc"
                    send_message(vk, peer_id, "📝 Введите описание:", get_cancel_keyboard())
                
                elif state["step"] == "waiting_desc":
                    add_plan(user_id, state["date"], state["time"], text, state["reminder_minutes"])
                    del user_states[user_id]
                    
                    reminder_text = format_reminder_text(state["reminder_minutes"])
                    send_message(vk, peer_id, 
                        f"✅ *План добавлен!*\n\n"
                        f"📅 Дата: {state['date']}\n"
                        f"⏰ Время: {state['time']}\n"
                        f"📌 Описание: {text}\n"
                        f"🔔 Напоминание: {reminder_text}\n\n"
                        f"Я напомню вам в указанное время (по Москве)!",
                        get_main_keyboard())
                continue
            
            # Основные команды
            if text.lower() in ["добавить план", "добавить", "📝 добавить план", "add plan", "add"]:
                user_states[user_id] = {"step": "waiting_date"}
                send_message(vk, peer_id, "📅 Введите дату в формате ГГГГ-ММ-ДД (например: 2025-12-31):", get_cancel_keyboard())
            
            elif text.lower() in ["мои планы", "планы", "список", "📋 мои планы", "my plans", "plans", "list"]:
                user_plans = get_user_plans(user_id)
                send_message(vk, peer_id, format_plans_list(user_plans), get_main_keyboard())
            
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
2. 2025-12-31
3. 18:00
4. Выберите когда напомнить
5. Новый год

🔔 Бот работает по *московскому времени (МСК)*!"""
                send_message(vk, peer_id, help_text, get_main_keyboard())
            
            else:
                send_message(vk, peer_id, "👋 Напишите *Помощь* для списка команд", get_main_keyboard())
        
        time.sleep(2)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        time.sleep(5)
