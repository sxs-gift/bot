import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ===== НАСТРОЙКИ =====
TOKEN = "8772612144:AAEU_wDtpmN_rWWKasQUyPCt9tzqORHfPZM"
OWNER_ID = 8167702565  # Твой Telegram ID
# ====================

# Хранилище: {user_id: state}
user_states = {}

# Хранилище заявок: {номер_заявки: {"user_id": int, "text": str, "type": "minister"}}
applications = {}
next_app_id = 1

# Временное хранилище для ожидания ввода номера заявки владельцем
owner_waiting_for_app_id = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Предложение", callback_data="offer")],
        [InlineKeyboardButton("👔 Министр", callback_data="minister")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Главное меню:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "offer":
        user_states[user_id] = "waiting_offer"
        await query.edit_message_text("Отправьте свой ник и идею:")

    elif query.data == "minister":
        user_states[user_id] = "waiting_minister"
        await query.edit_message_text("Введите свой ник и должность:")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_app_id
    user_id = update.message.from_user.id
    text = update.message.text

    # Обработка ввода номера заявки от владельца
    if user_id == OWNER_ID and user_id in owner_waiting_for_app_id:
        owner_waiting_for_app_id.discard(user_id)
        try:
            app_num = int(text.strip())
            if app_num in applications:
                app_data = applications[app_num]
                # Кнопки для принятия/отказа
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Принять", callback_data=f"accept_{app_num}"),
                        InlineKeyboardButton("❌ Отказать", callback_data=f"reject_{app_num}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"📌 Заявка #{app_num}\nОт: {app_data['user_id']}\nТекст: {app_data['text']}\n\nВыберите действие:",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(f"❌ Заявка #{app_num} не найдена.")
        except ValueError:
            await update.message.reply_text("❌ Введите ЧИСЛО — номер заявки.")
        return

    # Обычная обработка от пользователей
    if user_id not in user_states:
        await update.message.reply_text("Пожалуйста, начните с /start")
        return

    state = user_states[user_id]
    user_name = update.message.from_user.full_name
    username = update.message.from_user.username or "нет username"

    if state == "waiting_offer":
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"📩 НОВОЕ ПРЕДЛОЖЕНИЕ\nОт: {user_name} (@{username})\nТекст:\n{text}"
        )
        await update.message.reply_text("✅ Спасибо! Ваше предложение отправлено.")
        del user_states[user_id]

    elif state == "waiting_minister":
        app_num = next_app_id
        next_app_id += 1
        applications[app_num] = {
            "user_id": user_id,
            "text": text,
            "type": "minister",
            "user_name": user_name,
            "username": username
        }

        # Отправляем владельцу уведомление с номером заявки
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"👔 НОВАЯ ЗАЯВКА НА МИНИСТРА #{app_num}\nОт: {user_name} (@{username})\nТекст:\n{text}\n\nДля решения используй команду:\n/apply {app_num}"
        )
        await update.message.reply_text(f"✅ Ваша заявка принята! Номер заявки: #{app_num}. Ожидайте решения.")
        del user_states[user_id]

async def apply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для владельца: /apply <номер>"""
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("❌ Только владелец бота может использовать эту команду.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("ℹ️ Использование: /apply <номер_заявки>")
        return

    try:
        app_num = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Номер заявки должен быть числом.")
        return

    if app_num not in applications:
        await update.message.reply_text(f"❌ Заявка #{app_num} не найдена.")
        return

    app_data = applications[app_num]
    keyboard = [
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"accept_{app_num}"),
            InlineKeyboardButton("❌ Отказать", callback_data=f"reject_{app_num}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"📌 Заявка #{app_num}\nОт: {app_data['user_name']} (@{app_data['username']})\nТекст: {app_data['text']}\n\nВыберите действие:",
        reply_markup=reply_markup
    )

async def decision_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки Принять/Отказать"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Только владелец может принимать решения
    if user_id != OWNER_ID:
        await query.edit_message_text("❌ Вы не являетесь владельцем бота.")
        return

    data = query.data  # accept_123 или reject_123
    action, app_num_str = data.split('_')
    app_num = int(app_num_str)

    if app_num not in applications:
        await query.edit_message_text(f"❌ Заявка #{app_num} уже была обработана или не существует.")
        return

    app_data = applications[app_num]
    user_to_notify = app_data["user_id"]
    app_text = app_data["text"]

    if action == "accept":
        # Уведомляем пользователя
        await context.bot.send_message(
            chat_id=user_to_notify,
            text=f"✅ Ваша заявка на министра (#{app_num}) принята!\n📝 Ваши данные: {app_text}\nПоздравляем!"
        )
        await query.edit_message_text(f"✅ Заявка #{app_num} ПРИНЯТА. Пользователь уведомлён.")
    else:  # reject
        await context.bot.send_message(
            chat_id=user_to_notify,
            text=f"❌ Ваша заявка на министра (#{app_num}) отклонена.\n📝 Ваши данные: {app_text}\nСпасибо за участие!"
        )
        await query.edit_message_text(f"❌ Заявка #{app_num} ОТКЛОНЕНА. Пользователь уведомлён.")

    # Удаляем заявку из хранилища
    del applications[app_num]

async def list_apps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /list_apps — показать все активные заявки"""
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("❌ Только для владельца.")
        return

    if not applications:
        await update.message.reply_text("📭 Нет активных заявок.")
        return

    msg = "📋 Активные заявки:\n"
    for num, data in applications.items():
        msg += f"#{num} — {data['user_name']} (@{data['username']})\n   {data['text'][:50]}...\n"
    await update.message.reply_text(msg)

async def cancel_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in user_states:
        del user_states[user_id]
    await update.message.reply_text("Действие отменено. Нажмите /start для главного меню.")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel_state))
    app.add_handler(CommandHandler("apply", apply_command))
    app.add_handler(CommandHandler("list_apps", list_apps))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(offer|minister)$"))
    app.add_handler(CallbackQueryHandler(decision_handler, pattern="^(accept|reject)_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()