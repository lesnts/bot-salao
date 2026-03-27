import os
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise Exception("TOKEN não encontrado!")

bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

# 🔒 Controle de updates já processados
updates_processados = set()


# =========================
# MENU INICIAL
# =========================
def menu_principal():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📅 Agendar", callback_data="agendar"),
        InlineKeyboardButton("📖 Meus agendamentos", callback_data="meus")
    )
    return markup


@bot.message_handler(commands=['start'])
def start(msg):
    bot.send_message(
        msg.chat.id,
        "✨ Bem-vinda! Escolha uma opção:",
        reply_markup=menu_principal()
    )


# =========================
# CALLBACKS
# =========================
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):

    # 🔒 ANTI DUPLICAÇÃO
    if call.id in updates_processados:
        return
    updates_processados.add(call.id)

    bot.answer_callback_query(call.id)

    if call.data == "agendar":
        escolher_dia(call.message)

    elif call.data == "meus":
        bot.send_message(call.message.chat.id, "📖 Seus agendamentos aparecerão aqui.")

    elif call.data.startswith("dia_"):
        escolher_horario(call.message, call.data.replace("dia_", ""))

    elif call.data.startswith("hora_"):
        confirmar(call.message, call.data.replace("hora_", ""))

    elif call.data == "confirmar":
        bot.send_message(call.message.chat.id, "✅ Agendamento confirmado!")
        bot.send_message(call.message.chat.id, "Menu:", reply_markup=menu_principal())

    elif call.data == "cancelar":
        bot.send_message(call.message.chat.id, "❌ Agendamento cancelado.")
        bot.send_message(call.message.chat.id, "Menu:", reply_markup=menu_principal())


# =========================
# DIAS EM PORTUGUÊS
# =========================
def escolher_dia(msg):
    markup = InlineKeyboardMarkup()

    dias = [
        ("Segunda", "dia_seg"),
        ("Terça", "dia_ter"),
        ("Quarta", "dia_qua"),
        ("Quinta", "dia_qui"),
        ("Sexta", "dia_sex"),
        ("Sábado", "dia_sab")
    ]

    for nome, valor in dias:
        markup.add(InlineKeyboardButton(nome, callback_data=valor))

    bot.send_message(msg.chat.id, "📅 Escolha o dia:", reply_markup=markup)


# =========================
# HORÁRIOS
# =========================
def escolher_horario(msg, dia):
    markup = InlineKeyboardMarkup()

    horarios = ["10:00", "11:00", "14:00", "15:00", "16:00"]

    for h in horarios:
        markup.add(
            InlineKeyboardButton(f"{h} ✅", callback_data=f"hora_{dia}_{h}")
        )

    bot.send_message(msg.chat.id, f"⏰ Horários para {dia}:", reply_markup=markup)


# =========================
# CONFIRMAÇÃO
# =========================
def confirmar(msg, dados):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Confirmar", callback_data="confirmar"),
        InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")
    )

    bot.send_message(
        msg.chat.id,
        f"📌 Confirmar agendamento?\n\n{dados}",
        reply_markup=markup
    )


# =========================
# WEBHOOK
# =========================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")

    update = telebot.types.Update.de_json(json_str)

    # 🔒 ANTI DUPLICAÇÃO GLOBAL
    if update.update_id in updates_processados:
        return "ok", 200

    updates_processados.add(update.update_id)

    bot.process_new_updates([update])
    return "ok", 200


@app.route("/")
def home():
    return "Bot rodando!"


# =========================
# START
# =========================
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=os.getenv("WEBHOOK_URL") + "/" + TOKEN)

    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
