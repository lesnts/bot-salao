import os
import time
import threading
from datetime import datetime, timedelta
from flask import Flask, request, render_template
import telebot
from telebot import types

from bot.database import *

TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

criar_tabelas()

usuarios = {}

HORARIOS_DISPONIVEIS = ["10:00", "11:00", "14:00", "15:00", "16:00"]

SERVICOS = {
    "Corte": 30,
    "Escova": 40,
    "Progressiva": 120
}

# ================= CLIENTE =================

def get_cliente(chat_id):
    cliente = buscar_cliente(chat_id)
    if not cliente:
        criar_cliente(chat_id)
        cliente = buscar_cliente(chat_id)
    return cliente

# ================= MENU =================

def menu_principal(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("📅 Agendar"),
        types.KeyboardButton("📋 Meus agendamentos"),
        types.KeyboardButton("❌ Cancelar")
    )
    bot.send_message(chat_id, "Escolha uma opção:", reply_markup=markup)

@bot.message_handler(commands=['start'])
def start(message):
    get_cliente(message.chat.id)
    menu_principal(message.chat.id)

# ================= MEUS AGENDAMENTOS =================

@bot.message_handler(func=lambda m: m.text == "📋 Meus agendamentos")
def meus_agendamentos(message):
    chat_id = message.chat.id
    cliente = get_cliente(chat_id)

    dados = listar_agendamentos(cliente["id"])

    if not dados:
        bot.send_message(chat_id, "Você não possui agendamentos.")
        return

    texto = "📋 Seus agendamentos:\n\n"
    for nome, servico, valor, data, hora in dados:
        texto += f"{data} às {hora} - {servico} (R${valor})\n"

    bot.send_message(chat_id, texto)

# ================= INICIAR AGENDAMENTO =================

@bot.message_handler(func=lambda m: m.text == "📅 Agendar")
def agendar(message):
    chat_id = message.chat.id

    usuarios[chat_id] = {}

    markup = types.InlineKeyboardMarkup()

    for servico in SERVICOS:
        markup.add(
            types.InlineKeyboardButton(
                servico,
                callback_data=f"agendar|servico|{servico}"
            )
        )

    bot.send_message(chat_id, "Escolha o serviço:", reply_markup=markup)

# ================= CALLBACK PROFISSIONAL =================

@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):

    if call.id in callbacks_processados:
        return
    callbacks_processados.add(call.id)

    bot.answer_callback_query(call.id)

    chat_id = call.message.chat.id
    u = usuarios.get(chat_id)

    if not u:
        return

    try:
        acao, tipo, valor = call.data.split("|")
    except:
        return

    # ================= SERVIÇO =================
    if tipo == "servico":
        u["servico"] = valor
        u["valor"] = SERVICOS.get(valor, 0)

        markup = types.InlineKeyboardMarkup()
        hoje = datetime.now()

        for i in range(5):
            dia = hoje + timedelta(days=i)
            data_formatada = dia.strftime("%Y-%m-%d")

            markup.add(
                types.InlineKeyboardButton(
                    dia.strftime("%d/%m"),
                    callback_data=f"agendar|data|{data_formatada}"
                )
            )

        bot.edit_message_text(
            "Escolha a data:",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=markup
        )

    # ================= DATA =================
    elif tipo == "data":
        u["data"] = valor

        markup = types.InlineKeyboardMarkup()

        for hora in HORARIOS_DISPONIVEIS:
            markup.add(
                types.InlineKeyboardButton(
                    hora,
                    callback_data=f"agendar|horario|{hora}"
                )
            )

        bot.edit_message_text(
            "Escolha o horário:",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=markup
        )

    # ================= HORÁRIO =================
    elif tipo == "horario":
        u["horario"] = valor

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Confirmar", callback_data="agendar|confirmar|ok"),
            types.InlineKeyboardButton("❌ Cancelar", callback_data="agendar|cancelar|ok")
        )

        bot.edit_message_text(
            f"Confirmar agendamento?\n📅 {u['data']} às {u['horario']}\n💇 {u['servico']}",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=markup
        )

    # ================= CONFIRMAR =================
    elif tipo == "confirmar":

        if u.get("finalizado"):
            return

        u["finalizado"] = True

        cliente = get_cliente(chat_id)

        salvar_agendamento(
            cliente["id"],
            u.get("nome", "Cliente"),
            u.get("telefone", ""),
            u["servico"],
            u["valor"],
            u["data"],
            u["horario"]
        )

        bot.edit_message_text(
            f"✅ Agendado!\n📅 {u['data']} às {u['horario']}\n💇 {u['servico']}",
            chat_id=chat_id,
            message_id=call.message.message_id
        )

        usuarios.pop(chat_id, None)
        menu_principal(chat_id)

    # ================= CANCELAR =================
    elif tipo == "cancelar":

        usuarios.pop(chat_id, None)

        bot.edit_message_text(
            "❌ Agendamento cancelado.",
            chat_id=chat_id,
            message_id=call.message.message_id
        )

        menu_principal(chat_id)

# ================= WEBHOOK =================

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.stream.read().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)

        # 🔥 ANTI DUPLICAÇÃO REAL (BANCO)
        if update_ja_processado(update.update_id):
            return '', 200

        bot.process_new_updates([update])
        return '', 200

    return '', 403

# ================= DASHBOARD =================

@app.route("/dashboard/<int:telegram_id>")
def dashboard(telegram_id):
    cliente = buscar_cliente(telegram_id)

    if not cliente:
        return "Cliente não encontrado"

    agendamentos = listar_agendamentos(cliente["id"])

    return render_template(
        "dashboard.html",
        cliente=cliente,
        agendamentos=agendamentos
    )

# ================= START =================

if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=WEBHOOK_URL + "/webhook")

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
