import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# ===== НАСТРОЙКИ =====
TOKEN = "8772612144:AAEU_wDtpmN_rWWKasQUyPCt9tzqORHfPZM"  # Вставь сюда свой токен
OWNER_ID = 8167702565  # Вставь свой Telegram ID

# Ссылка на фото (если не нужна, оставь пустой)
PHOTO_URL = ""  # Например: "https://telegra.ph/file/example.jpg"
# ====================

# Состояния
WAITING_OFFER = 1
WAITING_NICKNAME = 2
WAITING_POSITION = 3
WAITING_ONLINE = 4
WAITING_CHANGES = 5
WAITING_PREVIOUS_EXPERIENCE = 6

# Хранилища
applications = {}
next_app_id = 1
owner_waiting_meeting = {}
user_states = {}
temp_data = {}

# Список министров
ministers = {
    "Министр экономики": "",
    "Министр спавна": "",
    "Министр ПодГорода": "",
    "Министр правосудия": "",
    "Министр дорог": ""
}

POSITIONS = list(ministers.keys())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Предложение", callback_data="offer")],
        [InlineKeyboardButton("👔 Министр", callback_data="minister")],
        [InlineKeyboardButton("ℹ️ Информация", callback_data="info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if PHOTO_URL:
        await update.message.reply_photo(photo=https://sun9-8.userapi.com/s/v1/ig2/xtyNX_gKELsgnfnMtDAZRj-YlCPMpLJNi0-eqQLsSiqzWE3vUaxxtJybqE-IBP6H1zyhi0rDVIVsHm4g1U7isEwZ.jpg?quality=95&as=32x43,48x64,72x97,108x145,160x215,240x322,360x483,480x644,540x724,640x859,720x966&from=bu&u=UWLFsG4V6-xXWAPMY6I6CkDCfiiT5PApxThv-X481r4&cs=720x0, caption="Главное меню", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Главное меню", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "offer":
        user_states[user_id] = WAITING_OFFER
        await query.edit_message_text("Отправьте свой ник и идею:")
    
    elif query.data == "minister":
        user_states[user_id] = WAITING_NICKNAME
        temp_data[user_id] = {}
        await query.edit_message_text("ШАГ 1 из 5\n\nВведите ваш ник:")
    
    elif query.data == "info":
        info_text = "🏛 ИНФОРМАЦИЯ О ПРАВИТЕЛЬСТВЕ\n\n"
        info_text += "👑 Президент: MCLov1n\n\n"
        info_text += "📋 МИНИСТРЫ:\n"
        for pos, name in ministers.items():
            if name:
                info_text += f"   • {pos}: {name}\n"
            else:
                info_text += f"   • {pos}: ❌ вакантно\n"
        await query.edit_message_text(info_text)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    
    # Проверка на ввод времени встречи от владельца
    if user_id == OWNER_ID and user_id in owner_waiting_meeting:
        app_num = owner_waiting_meeting[user_id]
        del owner_waiting_meeting[user_id]
        
        if app_num in applications:
            user_to_notify = applications[app_num]["user_id"]
            await context.bot.send_message(
                chat_id=user_to_notify,
                text=f"📅 ВАМ НАЗНАЧЕНА ВСТРЕЧА\n\nПо заявке #{app_num}\n\nВремя: {text}\nМесто: на сервере\n\nЖдём вас!"
            )
            await update.message.reply_text(f"✅ Встреча назначена!\nВремя: {text}")
        else:
            await update.message.reply_text(f"❌ Заявка #{app_num} не найдена")
        return
    
    # Получаем состояние пользователя
    state = user_states.get(user_id)
    
    if state == WAITING_OFFER:
        user_name = update.message.from_user.full_name
        username = update.message.from_user.username or "нет username"
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"📩 НОВОЕ ПРЕДЛОЖЕНИЕ\n\nОт: {user_name}\n\nUsername: @{username}\n\nТекст:\n{text}"
        )
        await update.message.reply_text("✅ Спасибо! Ваше предложение отправлено владельцу.")
        del user_states[user_id]
    
    elif state == WAITING_NICKNAME:
        temp_data[user_id]["nickname"] = text
        user_states[user_id] = WAITING_POSITION
        
        keyboard = [[InlineKeyboardButton(pos, callback_data=f"pos_{pos}")] for pos in POSITIONS]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("ШАГ 2 из 5\n\nВыберите должность:", reply_markup=reply_markup)
    
    elif state == WAITING_ONLINE:
        temp_data[user_id]["online"] = text
        user_states[user_id] = WAITING_CHANGES
        await update.message.reply_text("ШАГ 4 из 5\n\nЧто бы вы изменили, если бы стали на эту должность?")
    
    elif state == WAITING_CHANGES:
        temp_data[user_id]["changes"] = text
        user_states[user_id] = WAITING_PREVIOUS_EXPERIENCE
        await update.message.reply_text("ШАГ 5 из 5\n\nСтояли ли вы на подобной должности ранее? (Да/Нет, можно с подробностями)")
    
    elif state == WAITING_PREVIOUS_EXPERIENCE:
        temp_data[user_id]["experience"] = text
        await finish_application(update, context)

async def position_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    position = query.data.replace("pos_", "")
    
    temp_data[user_id]["position"] = position
    user_states[user_id] = WAITING_ONLINE
    
    await query.edit_message_text(f"✅ Должность выбрана: {position}\n\nШАГ 3 из 5\n\nКакой у вас средний онлайн в день?\n(например: 4-5 часов)")

async def finish_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_app_id
    user_id = update.message.from_user.id
    data = temp_data[user_id]
    user_name = update.message.from_user.full_name
    username = update.message.from_user.username or "нет username"
    
    app_num = next_app_id
    next_app_id += 1
    
    full_text = (
        f"👤 Ник: {data['nickname']}\n"
        f"📌 Должность: {data['position']}\n"
        f"⏱ Онлайн: {data['online']}\n"
        f"💡 Изменения: {data['changes']}\n"
        f"📜 Опыт: {data['experience']}"
    )
    
    applications[app_num] = {
        "user_id": user_id,
        "text": full_text,
        "user_name": user_name,
        "username": username,
        "position": data['position']
    }
    
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=f"👔 НОВАЯ ЗАЯВКА НА МИНИСТРА #{app_num}\n\nОт: {user_name}\n\nUsername: @{username}\n\n{full_text}\n\nИспользуй команду:\n/apply {app_num}"
    )
    
    await update.message.reply_text(f"✅ АНКЕТА ОТПРАВЛЕНА!\n\nНомер вашей заявки: #{app_num}\n\nОжидайте решения владельца.")
    
    del user_states[user_id]
    del temp_data[user_id]

async def apply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("❌ Только владелец бота может использовать эту команду")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("ℹ️ Использование: /apply <номер_заявки>\n\nПример: /apply 5")
        return
    
    try:
        app_num = int(context.args[0])
    except:
        await update.message.reply_text("❌ Номер заявки должен быть числом")
        return
    
    if app_num not in applications:
        await update.message.reply_text(f"❌ Заявка #{app_num} не найдена")
        return
    
    app_data = applications[app_num]
    
    keyboard = [
        [
            InlineKeyboardButton("✅ ПРИНЯТЬ", callback_data=f"accept_{app_num}"),
            InlineKeyboardButton("❌ ОТКАЗАТЬ", callback_data=f"reject_{app_num}")
        ],
        [
            InlineKeyboardButton("📅 НАЗНАЧИТЬ ВСТРЕЧУ", callback_data=f"meeting_{app_num}"),
            InlineKeyboardButton("✍️ НАПИШИ МНЕ", callback_data=f"contact_{app_num}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📌 ЗАЯВКА #{app_num}\n\nОт: {app_data['user_name']}\n\n{app_data['text']}\n\nВыберите действие:",
        reply_markup=reply_markup
    )

async def decision_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != OWNER_ID:
        await query.edit_message_text("❌ Вы не являетесь владельцем бота")
        return
    
    action, app_num_str = query.data.split('_')
    app_num = int(app_num_str)
    
    if app_num not in applications:
        await query.edit_message_text(f"❌ Заявка #{app_num} уже была обработана")
        return
    
    app_data = applications[app_num]
    
    if action == "accept":
        await context.bot.send_message(
            chat_id=app_data["user_id"],
            text=f"✅ ВАША ЗАЯВКА #{app_num} ПРИНЯТА!\n\nПоздравляем с назначением!\n\n{app_data['text']}"
        )
        await query.edit_message_text(f"✅ Заявка #{app_num} ПРИНЯТА\n\nПользователь уведомлён")
        del applications[app_num]
    
    elif action == "reject":
        await context.bot.send_message(
            chat_id=app_data["user_id"],
            text=f"❌ ВАША ЗАЯВКА #{app_num} ОТКЛОНЕНА\n\nСпасибо за участие!"
        )
        await query.edit_message_text(f"❌ Заявка #{app_num} ОТКЛОНЕНА\n\nПользователь уведомлён")
        del applications[app_num]
    
    elif action == "meeting":
        owner_waiting_meeting[OWNER_ID] = app_num
        await query.edit_message_text(f"📅 НАЗНАЧЕНИЕ ВСТРЕЧИ\n\nВведите время встречи для заявки #{app_num}\n\nПример: завтра в 19:00 МСК")
    
    elif action == "contact":
        await context.bot.send_message(
            chat_id=app_data["user_id"],
            text=f"👋 ВАША ЗАЯВКА #{app_num} ОЖИДАЕТ ВНИМАНИЯ\n\nНапишите президенту: @paran0yy"
        )
        await query.edit_message_text(f"✍️ Пользователю отправлено приглашение связаться с президентом по заявке #{app_num}")

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    
    if not applications:
        await update.message.reply_text("📭 Нет активных заявок")
        return
    
    msg = "📋 АКТИВНЫЕ ЗАЯВКИ:\n\n"
    for num, data in applications.items():
        msg += f"#{num} — {data['user_name']} — {data['position']}\n"
    await update.message.reply_text(msg)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in user_states:
        del user_states[user_id]
    if user_id in temp_data:
        del temp_data[user_id]
    await update.message.reply_text("❌ Действие отменено.\n\nНапишите /start для главного меню")

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("apply", apply_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CallbackQueryHandler(button_callback, pattern="^(offer|minister|info)$"))
    app.add_handler(CallbackQueryHandler(position_callback, pattern="^pos_"))
    app.add_handler(CallbackQueryHandler(decision_callback, pattern="^(accept|reject|meeting|contact)_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print("✅ БОТ ЗАПУЩЕН!")
    print("Напиши /start в Telegram")
    app.run_polling()

if __name__ == "__main__":
    main()
