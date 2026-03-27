callbacks_processados = set()
updates_processados = set()
import os
import time
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
ultimo_update_id = None

HORARIOS_DISPONIVEIS = ["10:00", "11:00", "14:00", "15:00", "16:00"]

SERVICOS = {
    "Corte": 30,
    "Escova": 40,
    "Progressiva": 120
}

DIAS_SEMANA = {
    0: "Segunda",
    1: "Terça",
    2: "Quarta",
    3: "Quinta",
    4: "Sexta",
    5: "Sábado",
    6: "Domingo"
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
    usuarios[message.chat.id] = {"etapa": "nome"}
    bot.send_message(message.chat.id, "Qual seu nome?")

# ================= FLUXO (CORRIGIDO) =================

callbacks_processados = set()

@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):

    # 🔒 bloqueio absoluto
    if call.id in callbacks_processados:
        return

    callbacks_processados.add(call.id)

    bot.answer_callback_query(call.id)

    chat_id = call.message.chat.id
    data = call.data
    u = usuarios.get(chat_id)

    if not u:
        return

    # ================= HORÁRIO =================
    if ":" in data:

        if data == "ocupado":
            return

        u["horario"] = data

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Confirmar", callback_data="confirmar"),
            types.InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")
        )

        bot.edit_message_text(
            f"Confirmar agendamento?\n📅 {u['data']} às {u['horario']}\n💇 {u['servico']}",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=markup
        )

    # ================= CONFIRMAR =================
    elif data == "confirmar":

        if u.get("finalizado"):
            return

        u["finalizado"] = True

        cliente = get_cliente(chat_id)

        if horario_ocupado(cliente["id"], u["data"], u["horario"]):
            bot.edit_message_text(
                "❌ Horário já ocupado.",
                chat_id=chat_id,
                message_id=call.message.message_id
            )
            return

        salvar_agendamento(
            cliente["id"],
            u["nome"],
            u["telefone"],
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

        if chat_id in usuarios:
            del usuarios[chat_id]

        menu_principal(chat_id)

    # ================= CANCELAR =================
    elif data == "cancelar":

        if chat_id in usuarios:
            del usuarios[chat_id]

        bot.edit_message_text(
            "❌ Agendamento cancelado.",
            chat_id=chat_id,
            message_id=call.message.message_id
        )

        menu_principal(chat_id)

# ================= WEBHOOK (ANTI DUPLICAÇÃO) =================

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.stream.read().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)

        # 🔒 BLOQUEIO ABSOLUTO DE DUPLICAÇÃO
        if update.update_id in updates_processados:
            return '', 200

        updates_processados.add(update.update_id)

        # evita crescer infinito
        if len(updates_processados) > 1000:
            updates_processados.clear()

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
