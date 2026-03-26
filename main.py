import os
import threading
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

# ================= AGENDAR =================

@bot.message_handler(func=lambda m: m.text == "📅 Agendar")
def agendar(message):
    chat_id = message.chat.id
    usuarios[chat_id] = {"etapa": "nome"}
    bot.send_message(chat_id, "Qual seu nome?")

@bot.message_handler(func=lambda m: True)
def fluxo(message):
    chat_id = message.chat.id

    if chat_id not in usuarios:
        return

    etapa = usuarios[chat_id]["etapa"]

    if etapa == "nome":
        usuarios[chat_id]["nome"] = message.text
        usuarios[chat_id]["etapa"] = "telefone"
        bot.send_message(chat_id, "Digite seu telefone:")

    elif etapa == "telefone":
        usuarios[chat_id]["telefone"] = message.text
        usuarios[chat_id]["etapa"] = "servico"

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        for s, v in SERVICOS.items():
            markup.add(types.KeyboardButton(f"{s} - R${v}"))

        bot.send_message(chat_id, "Escolha o serviço:", reply_markup=markup)

    elif etapa == "servico":
        servico_nome = message.text.split(" - ")[0]

        if servico_nome not in SERVICOS:
            bot.send_message(chat_id, "Serviço inválido.")
            return

        usuarios[chat_id]["servico"] = servico_nome
        usuarios[chat_id]["valor"] = SERVICOS[servico_nome]
        usuarios[chat_id]["etapa"] = "data"

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        hoje = datetime.now()

        for i in range(7):
            dia = hoje + timedelta(days=i)
            nome_dia = DIAS_SEMANA[dia.weekday()]
            texto = f"{nome_dia} • {dia.strftime('%d/%m')}"
            markup.add(types.KeyboardButton(texto))

        bot.send_message(chat_id, "Escolha a data:", reply_markup=markup)

    elif etapa == "data":
        try:
            data_formatada = message.text.split(" • ")[1] + f"/{datetime.now().year}"
            usuarios[chat_id]["data"] = data_formatada
            usuarios[chat_id]["etapa"] = "horario"

            cliente = get_cliente(chat_id)

            markup = types.InlineKeyboardMarkup()

            for h in HORARIOS_DISPONIVEIS:
                if horario_ocupado(cliente["id"], data_formatada, h):
                    markup.add(types.InlineKeyboardButton(f"{h} ❌", callback_data="ocupado"))
                else:
                    markup.add(types.InlineKeyboardButton(f"{h} ✅", callback_data=h))

            bot.send_message(chat_id, "Escolha o horário:", reply_markup=markup)

        except:
            bot.send_message(chat_id, "Formato inválido.")

# ================= CALLBACK HORÁRIO =================

@bot.callback_query_handler(func=lambda c: ":" in c.data)
def selecionar_horario(call):
    chat_id = call.message.chat.id
    horario = call.data

    if horario == "ocupado":
        bot.answer_callback_query(call.id, "Já ocupado.")
        return

    u = usuarios.get(chat_id)
    if not u:
        return

    u["horario"] = horario

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Confirmar", callback_data="confirmar"),
        types.InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")
    )

    bot.send_message(
        chat_id,
        f"Confirmar agendamento?\n📅 {u['data']} às {horario}\n💇 {u['servico']}",
        reply_markup=markup
    )

# ================= CALLBACK CONFIRMAR =================

@bot.callback_query_handler(func=lambda c: c.data == "confirmar")
def confirmar(call):
    chat_id = call.message.chat.id

    cliente = get_cliente(chat_id)
    u = usuarios.get(chat_id)

    if not u:
        return

    if horario_ocupado(cliente["id"], u["data"], u["horario"]):
        bot.answer_callback_query(call.id, "Horário já ocupado.")
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

    bot.send_message(
        chat_id,
        f"✅ Agendado!\n📅 {u['data']} às {u['horario']}\n💇 {u['servico']}"
    )

    del usuarios[chat_id]
    menu_principal(chat_id)

# ================= CALLBACK CANCELAR =================

@bot.callback_query_handler(func=lambda c: c.data == "cancelar")
def cancelar(call):
    chat_id = call.message.chat.id

    if chat_id in usuarios:
        del usuarios[chat_id]

    bot.send_message(chat_id, "❌ Agendamento cancelado.")
    menu_principal(chat_id)

# ================= WEBHOOK =================

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.stream.read().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return '', 403

@app.route('/', methods=['GET'])
def check():
    return "Bot ativo", 200

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
    bot.set_webhook(url=WEBHOOK_URL + "/webhook")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
