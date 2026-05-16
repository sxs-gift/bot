import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ===== НАСТРОЙКИ =====
TOKEN = "8772612144:AAEU_wDtpmN_rWWKasQUyPCt9tzqORHfPZM"
OWNER_ID = 8167702565  # Твой Telegram ID
# ====================

# Состояния для заявки на министра
(
    WAITING_NICKNAME,
    WAITING_POSITION,
    WAITING_ONLINE,
    WAITING_CHANGES,
    WAITING_PREVIOUS_EXPERIENCE
) = range(5)

# Хранилище заявок: {номер: данные}
applications = {}
next_app_id = 1

# Для ожидания ввода времени встречи от владельца
owner_waiting_meeting_time = {}  # {user_id: app_num}

# ===== СПИСОК МИНИСТРОВ (ЗАДАЁШЬ ЗДЕСЬ) =====
# Заполни ники министров вручную
ministers = {
    "Министр экономики": "",
    "Министр спавна": "",
    "Министр ПодГорода": "",
    "Министр правосудия": "",
    "Министр дорог": ""
}
# ============================================

# Должности для выбора
POSITIONS = list(ministers.keys())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Предложение", callback_data="offer")],
        [InlineKeyboardButton("👔 Министр", callback_data="minister")],
        [InlineKeyboardButton("ℹ️ Информация", callback_data="info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("«Главное меню»", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "offer":
        context.user_data["state"] = "waiting_offer"
        await query.edit_message_text("Отправьте свой ник и идею:")

    elif query.data == "minister":
        context.user_data["state"] = WAITING_NICKNAME
        context.user_data["minister_data"] = {}
        await query.edit_message_text("«ШАГ 1/5»\nВведите ваш ник:")

    elif query.data == "info":
        # Формируем список министров
        ministers_list = ""
        for position, name in ministers.items():
            if name:
                ministers_list += f"• {position}: «{name}»\n"
            else:
                ministers_list += f"• {position}: «вакантно»\n"
        
        info_text = (
            "«Информация о правительстве»\n\n"
            f"Президент: «MCLov1n»\n\n"
            "Министры:\n"
            f"{ministers_list}\n"
            "Имена министров указаны в коде бота"
        )
        await query.edit_message_text(info_text)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    state = context.user_data.get("state")

    # Обработка ввода времени встречи от владельца
    if user_id == OWNER_ID and user_id in owner_waiting_meeting_time:
        app_num = owner_waiting_meeting_time.pop(user_id)
        if app_num in applications:
            app_data = applications[app_num]
            user_to_notify = app_data["user_id"]
            await context.bot.send_message(
                chat_id=user_to_notify,
                text=f"«Вам назначена встреча» по заявке #{app_num}\n\nВремя: «{text}»\nМесто: на сервере\n\nЖдём вас!"
            )
            await update.message.reply_text(f"✅ Встреча назначена! Пользователь уведомлён о времени: «{text}»")
        else:
            await update.message.reply_text(f"❌ Заявка #{app_num} не найдена.")
        return

    # Обработка простого предложения
    if state == "waiting_offer":
        user_name = update.message.from_user.full_name
        username = update.message.from_user.username or "нет username"
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"«НОВОЕ ПРЕДЛОЖЕНИЕ»\nОт: {user_name} (@{username})\nТекст:\n{text}"
        )
        await update.message.reply_text("✅ Спасибо! Ваше предложение отправлено владельцу.")
        del context.user_data["state"]

    # Анкета министра
    elif state == WAITING_NICKNAME:
        context.user_data["minister_data"]["nickname"] = text
        context.user_data["state"] = WAITING_POSITION
        
        keyboard = [[InlineKeyboardButton(pos, callback_data=f"pos_{pos}")] for pos in POSITIONS]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("«ШАГ 2/5»\nВыберите должность:", reply_markup=reply_markup)

    elif state == WAITING_ONLINE:
        context.user_data["minister_data"]["online"] = text
        context.user_data["state"] = WAITING_CHANGES
        await update.message.reply_text("«ШАГ 4/5»\nЧто бы вы изменили, будь вы на этой должности?")

    elif state == WAITING_CHANGES:
        context.user_data["minister_data"]["changes"] = text
        context.user_data["state"] = WAITING_PREVIOUS_EXPERIENCE
        await update.message.reply_text("«ШАГ 5/5»\nСтояли ли вы на подобной должности ранее? (Да/Нет, можно с подробностями)")

    elif state == WAITING_PREVIOUS_EXPERIENCE:
        context.user_data["minister_data"]["previous_experience"] = text
        await finish_minister_application(update, context)

async def position_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    pos = query.data.replace("pos_", "")
    context.user_data["minister_data"]["position"] = pos
    context.user_data["state"] = WAITING_ONLINE
    
    await query.edit_message_text(f"✅ Должность: «{pos}»\n\n«ШАГ 3/5»\nКакой у вас средний онлайн в день? (например: 5-6 часов)")

async def finish_minister_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_app_id
    user_id = update.message.from_user.id
    data = context.user_data["minister_data"]
    user_name = update.message.from_user.full_name
    username = update.message.from_user.username or "нет username"

    app_num = next_app_id
    next_app_id += 1

    full_text = (
        f"Ник: {data['nickname']}\n"
        f"Должность: {data['position']}\n"
        f"Средний онлайн: {data['online']}\n"
        f"Что изменит: {data['changes']}\n"
        f"Опыт: {data['previous_experience']}"
    )

    applications[app_num] = {
        "user_id": user_id,
        "text": full_text,
        "type": "minister",
        "user_name": user_name,
        "username": username,
        "raw_data": data.copy()
    }

    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=f"«НОВАЯ ЗАЯВКА НА МИНИСТРА» #{app_num}\nОт: {user_name} (@{username})\n\n{full_text}\n\nДля решения используй:\n/apply {app_num}"
    )

    await update.message.reply_text(
        f"✅ Анкета отправлена!\nВаша заявка #{app_num}\nОжидайте решения владельца."
    )

    del context.user_data["state"]
    del context.user_data["minister_data"]

async def apply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("❌ Только владелец.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("ℹ️ Использование: /apply <номер_заявки>")
        return

    try:
        app_num = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Номер должен быть числом.")
        return

    if app_num not in applications:
        await update.message.reply_text(f"❌ Заявка #{app_num} не найдена.")
        return

    app_data = applications[app_num]
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"accept_{app_num}"),
            InlineKeyboardButton("❌ Отказать", callback_data=f"reject_{app_num}")
        ],
        [
            InlineKeyboardButton("📅 Назначить встречу", callback_data=f"meeting_{app_num}"),
            InlineKeyboardButton("✍️ Напиши мне", callback_data=f"contact_{app_num}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"«Заявка» #{app_num}\nОт: {app_data['user_name']} (@{app_data['username']})\n\n{app_data['text']}\n\nВыберите действие:",
        reply_markup=reply_markup
    )

async def decision_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != OWNER_ID:
        await query.edit_message_text("❌ Вы не владелец.")
        return

    action, app_num_str = query.data.split('_')
    app_num = int(app_num_str)

    if app_num not in applications:
        await query.edit_message_text(f"❌ Заявка #{app_num} уже обработана.")
        return

    app_data = applications[app_num]
    user_to_notify = app_data["user_id"]

    if action == "accept":
        await context.bot.send_message(
            chat_id=user_to_notify,
            text=f"✅ Ваша заявка на министра (#{app_num}) ПРИНЯТА!\n\n{app_data['text']}\n\nПоздравляем с назначением!"
        )
        await query.edit_message_text(f"✅ Заявка #{app_num} ПРИНЯТА. Пользователь уведомлён.")
        del applications[app_num]

    elif action == "reject":
        await context.bot.send_message(
            chat_id=user_to_notify,
            text=f"❌ Ваша заявка на министра (#{app_num}) ОТКЛОНЕНА.\n\n{app_data['text']}\n\nСпасибо за участие!"
        )
        await query.edit_message_text(f"❌ Заявка #{app_num} ОТКЛОНЕНА. Пользователь уведомлён.")
        del applications[app_num]

    elif action == "meeting":
        owner_waiting_meeting_time[OWNER_ID] = app_num
        await query.edit_message_text(
            f"«Назначение встречи»\nВведите время встречи для заявки #{app_num}\n\nПример: завтра в 19:00 МСК или сегодня в 21:00 на сервере"
        )

    elif action == "contact":
        await context.bot.send_message(
            chat_id=user_to_notify,
            text=f"Ваша заявка #{app_num} ожидает внимания.\n\nНапишите президенту: @paran0yy"
        )
        await query.edit_message_text(f"✍️ Пользователю отправлено приглашение связаться с президентом (@paran0yy) по заявке #{app_num}")

async def list_apps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    if not applications:
        await update.message.reply_text("«Нет активных заявок»")
        return
    msg = "«Активные заявки»:\n"
    for num, data in applications.items():
        msg += f"#{num} — {data['user_name']} (@{data['username']}) — {data['raw_data']['position']}\n"
    await update.message.reply_text(msg)

async def cancel_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Действие отменено. Нажмите /start")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel_state))
    app.add_handler(CommandHandler("apply", apply_command))
    app.add_handler(CommandHandler("list_apps", list_apps))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(offer|minister|info)$"))
    app.add_handler(CallbackQueryHandler(position_callback, pattern="^pos_"))
    app.add_handler(CallbackQueryHandler(decision_handler, pattern="^(accept|reject|meeting|contact)_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("✅ Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
