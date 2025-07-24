import asyncio
import random
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

BOT_TOKEN = '7745952395:AAG99TwbXM0gsKmbVjJjE75DOj2xK9UOD_U'

participants = {}
CHANNEL_ID = None
current_prize = ""
current_image_url = ""
raffle_end_time = None
raffle_active = False
selected_winner = None
raffle_message_template = ""  # Текст с датой и призом


async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHANNEL_ID
    if not context.args:
        await update.message.reply_text("Используй: /setchannel <@username или -100...>")
        return
    CHANNEL_ID = context.args[0]
    await update.message.reply_text(f"✅ Канал установлен: {CHANNEL_ID}")


async def start_raffle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_prize, current_image_url, CHANNEL_ID
    global raffle_end_time, raffle_active, participants, raffle_message_template, selected_winner

    selected_winner = None  # сбрасываем ранее выбранного победителя

    if len(context.args) < 4:
        await update.message.reply_text(
            "Используй:\n"
            "/raffle \"название приза\" <ссылка_на_фото> <YYYY-MM-DD HH:MM>\n\n"
            "Пример:\n"
            "/raffle \"Айфон\" https://img.jpg 2025-07-25 21:30"
        )
        return

    full_text = " ".join(context.args)
    if full_text.count("\"") < 2:
        await update.message.reply_text("Пример: /raffle \"PlayStation 5\" https://img.jpg 2025-07-25 21:30")
        return

    current_prize = full_text.split("\"")[1]
    rest = full_text.split("\"")[2].strip()

    parts = rest.split()
    if len(parts) < 3:
        await update.message.reply_text("Укажи ссылку на фото и дату окончания в формате: YYYY-MM-DD HH:MM")
        return

    current_image_url = parts[0]
    end_str = " ".join(parts[1:3])

    try:
        raffle_end_time = datetime.strptime(end_str, "%Y-%m-%d %H:%M")
    except ValueError:
        await update.message.reply_text("Неверный формат даты/времени. Используй: YYYY-MM-DD HH:MM")
        return

    raffle_active = True
    participants.clear()

    keyboard = [[InlineKeyboardButton("✅ Я участвую!", callback_data="join_raffle")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    raffle_message_template = (
        f"🎉 *Розыгрыш начался!*\n\n"
        f"🎁 *Приз:* {current_prize}\n"
        f"⏰ *Закончится:* {raffle_end_time.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"Жми кнопку ниже, чтобы участвовать!"
    )

    try:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=current_image_url,
            caption=raffle_message_template,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

        if CHANNEL_ID:
            await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=current_image_url,
                caption=raffle_message_template,
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при отправке фото: {e}")

    asyncio.create_task(check_raffle_end(context.bot))


async def check_raffle_end(bot):
    global raffle_active, raffle_end_time, participants, current_prize, selected_winner

    while raffle_active:
        now = datetime.now()
        if now >= raffle_end_time:
            raffle_active = False
            if participants:
                if selected_winner:
                    winner_name = selected_winner
                else:
                    _, winner_name = random.choice(list(participants.items()))

                text = (
                    f"⏰ Розыгрыш завершён!\n"
                    f"🏆 Победитель: {winner_name}\n"
                    f"🎁 Приз: {current_prize}\n"
                    f"Поздравляем! 🎉"
                )
            else:
                text = "⏰ Розыгрыш завершён!\nК сожалению, участников не было."

            if CHANNEL_ID:
                await bot.send_message(chat_id=CHANNEL_ID, text=text)

            participants.clear()
            selected_winner = None
            break
        await asyncio.sleep(30)


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global raffle_active, participants, raffle_message_template
    query = update.callback_query
    user = query.from_user
    await query.answer()

    if not raffle_active:
        await query.answer("❌ Розыгрыш завершён, участие закрыто.", show_alert=True)
        return

    if user.id not in participants:
        participants[user.id] = f"@{user.username}" if user.username else user.full_name
        new_text = (
            f"{raffle_message_template}\n\n"
            f"📌 Участников: {len(participants)}"
        )
        keyboard = [[InlineKeyboardButton("✅ Я участвую!", callback_data="join_raffle")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_caption(caption=new_text, reply_markup=reply_markup)
    else:
        await query.answer("Ты уже участвуешь.", show_alert=True)


async def show_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if participants:
        msg = "**Участники розыгрыша:**\n" + "\n".join(f"- {name}" for name in participants.values())
    else:
        msg = "❗ Пока никто не участвует."
    await update.message.reply_text(msg)


async def pick_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHANNEL_ID, current_prize, current_image_url, selected_winner
    if not context.args:
        await update.message.reply_text("Используй: /pick @username")
        return

    username = context.args[0].lstrip("@")

    found = None
    for name in participants.values():
        if name.lstrip("@").lower() == username.lower():
            found = name
            break

    if found:
        selected_winner = found
        result_text = (
            f"🏆 *Победитель:* {found}\n"
            f"🎁 Приз: {current_prize}\n\n"
            f"Поздравляем! 🎉"
        )
        await update.message.reply_text(result_text, parse_mode="Markdown")

        if CHANNEL_ID:
            try:
                await context.bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=current_image_url,
                    caption=result_text,
                    parse_mode="Markdown",
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка при публикации в канал: {e}")
    else:
        await update.message.reply_text(f"{context.args[0]} не участвует в розыгрыше.")


async def set_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global selected_winner, participants
    if not context.args:
        await update.message.reply_text("Используй: /setwinner @username")
        return

    username = context.args[0].lstrip("@")

    found = None
    for name in participants.values():
        if name.lstrip("@").lower() == username.lower():
            found = name
            break

    if found:
        selected_winner = found
        await update.message.reply_text(f"✅ Победитель заранее выбран: {selected_winner}")
    else:
        await update.message.reply_text(f"{context.args[0]} не участвует в розыгрыше.")


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 *Список команд:*\n\n"
        "/setchannel <@канал или -100...> — установить канал для розыгрышей\n"
        "/raffle \"приз\" <ссылка_на_фото> <YYYY-MM-DD HH:MM> — начать розыгрыш\n"
        "/participants — список участников текущего розыгрыша\n"
        "/pick @username — вручную выбрать победителя\n"
        "/setwinner @username — заранее выбрать победителя\n"
        "/help — показать это сообщение\n\n"
        "👤 Участники могут нажимать кнопку *«Я участвую!»* под розыгрышем"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("setchannel", set_channel))
    app.add_handler(CommandHandler("raffle", start_raffle))
    app.add_handler(CommandHandler("participants", show_participants))
    app.add_handler(CommandHandler("pick", pick_winner))
    app.add_handler(CommandHandler("setwinner", set_winner))
    app.add_handler(CommandHandler("help", show_help))
    app.add_handler(CallbackQueryHandler(button_click, pattern="join_raffle"))

    print("Бот запущен.")
    app.run_polling()


if __name__ == "__main__":
    run_bot()
