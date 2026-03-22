import os
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, request
import telebot
from telebot import types

from bot.database import *

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

criar_tabela()

usuarios = {}

HORARIOS_DISPONIVEIS = ["10:00", "11:00", "14:00", "15:00", "16:00"]

SERVICOS = {
    "Corte": 30,
    "Escova": 40,
    "Progressiva": 120
}

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

def get_cliente(chat_id):
    cliente = buscar_cliente(chat_id)
    if not cliente:
        criar_cliente(chat_id)
        cliente = buscar_cliente(chat_id)
    return cliente
    
# ================= ADMIN =================

@bot.message_handler(commands=['admin'])
def admin(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ Sem permissão")
        return

    dados = listar_agendamentos()

    if not dados:
        bot.send_message(ADMIN_ID, "Nenhum agendamento.")
        return

    texto = "📊 TODOS OS AGENDAMENTOS:\n\n"
    for nome, servico, valor, data, hora in dados:
        texto += f"{data} {hora} - {nome} ({servico}) R${valor}\n"

    bot.send_message(ADMIN_ID, texto)

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

        texto = "Escolha o serviço:\n\n"
        for s, v in SERVICOS.items():
            texto += f"{s} - R${v}\n"

        bot.send_message(chat_id, texto)

    elif etapa == "servico":
        if message.text not in SERVICOS:
            bot.send_message(chat_id, "Serviço inválido.")
            return

        usuarios[chat_id]["servico"] = message.text
        usuarios[chat_id]["valor"] = SERVICOS[message.text]
        usuarios[chat_id]["etapa"] = "data"

        bot.send_message(chat_id, "Digite a data (DD/MM/AAAA):")

    elif etapa == "data":
        try:
            data_escolhida = datetime.strptime(message.text, "%d/%m/%Y")
            hoje = datetime.now()
            limite = hoje + timedelta(days=30)

            if data_escolhida.date() < hoje.date():
                bot.send_message(chat_id, "❌ Data passada.")
                return

            if data_escolhida > limite:
                bot.send_message(chat_id, "❌ Máximo 30 dias.")
                return

            usuarios[chat_id]["data"] = message.text
            usuarios[chat_id]["etapa"] = "horario"

            markup = types.InlineKeyboardMarkup()

            for h in HORARIOS_DISPONIVEIS:
                if horario_ocupado(message.text, h):
                    markup.add(types.InlineKeyboardButton(f"{h} ❌", callback_data="ocupado"))
                else:
                    markup.add(types.InlineKeyboardButton(f"{h} ✅", callback_data=h))

            bot.send_message(chat_id, "Escolha o horário:", reply_markup=markup)

        except:
            bot.send_message(chat_id, "Formato inválido.")

# ================= CALLBACK =================

@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    chat_id = call.message.chat.id
    data_callback = call.data

    if data_callback == "ocupado":
        bot.answer_callback_query(call.id, "Já ocupado.")
        return

cliente = get_cliente(chat_id)

ok = salvar_agendamento(
    cliente["id"],
    u["nome"],
    u["telefone"],
    u["servico"],
    u["valor"],
    u["data"],
    data_callback
)

    if not ok:
        bot.send_message(chat_id, "❌ Horário já foi ocupado.")
        return

bot.send_message(chat_id, f"✅ Agendado {u['data']} às {data_callback}")

    bot.send_message(
        ADMIN_ID,
        f"📢 Novo:\n{u['nome']} | {u['servico']} | R${u['valor']} | {u['data']} {data_callback}"
    )

    del usuarios[chat_id]
    menu_principal(chat_id)

# ================= RELATÓRIO =================

def relatorio_diario():
    while True:
        agora = datetime.now()

        if agora.hour == 20 and agora.minute == 30:
            hoje = agora.strftime("%d/%m/%Y")

            total = faturamento_por_dia(hoje)

            bot.send_message(
                ADMIN_ID,
                f"📊 Relatório {hoje}\n💰 Faturamento: R${total}"
            )

            time.sleep(60)

        time.sleep(30)

threading.Thread(target=relatorio_diario).start()

# ================= WEBHOOK =================

@app.route('/', methods=['POST'])
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

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
