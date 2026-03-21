import os
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, request
import telebot
from telebot import types

from database import *

# ================= CONFIG =================

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
    menu_principal(message.chat.id)

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
    total = 0

    for nome, servico, data, hora in dados:
        valor = SERVICOS.get(servico, 0)
        total += valor
        texto += f"{data} {hora} - {nome} ({servico}) R${valor}\n"

    texto += f"\n💰 Faturamento estimado: R${total}"

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
        usuarios[chat_id]["etapa"] = "servico"

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for s in SERVICOS:
            markup.add(types.KeyboardButton(f"{s} - R${SERVICOS[s]}"))

        bot.send_message(chat_id, "Escolha o serviço:", reply_markup=markup)

    elif etapa == "servico":
        servico = message.text.split(" - ")[0]

        if servico not in SERVICOS:
            bot.send_message(chat_id, "Escolha um serviço válido.")
            return

        usuarios[chat_id]["servico"] = servico
        usuarios[chat_id]["etapa"] = "data"
        bot.send_message(chat_id, "Digite a data (DD/MM/AAAA):")

    elif etapa == "data":
        try:
            data_escolhida = datetime.strptime(message.text, "%d/%m/%Y")
            hoje = datetime.now()
            limite = hoje + timedelta(days=30)

            if data_escolhida.date() < hoje.date():
                bot.send_message(chat_id, "❌ Data inválida.")
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
    horario = call.data

    if horario == "ocupado":
        bot.answer_callback_query(call.id, "Horário ocupado.")
        return

    user = usuarios.get(chat_id)

    if not user:
        return

    if horario_ocupado(user["data"], horario):
        bot.answer_callback_query(call.id, "Alguém pegou esse horário.")
        return

    salvar_agendamento(
        user["nome"],
        user["servico"],
        user["data"],
        horario
    )

    valor = SERVICOS[user["servico"]]

    bot.send_message(chat_id, f"✅ Agendado!\n{user['data']} às {horario}\n💰 R${valor}")

    bot.send_message(
        ADMIN_ID,
        f"📢 Novo agendamento!\n{user['nome']} - {user['servico']} - {user['data']} {horario}"
    )

    del usuarios[chat_id]
    menu_principal(chat_id)

# ================= RELATÓRIO =================

def relatorio_diario():
    while True:
        agora = datetime.now()

        if agora.hour == 20 and agora.minute == 30:
            hoje = agora.strftime("%d/%m/%Y")
            dados = listar_agendamentos()

            hoje_lista = [d for d in dados if d[2] == hoje]

            if hoje_lista:
                total = 0
                texto = f"📊 Relatório do dia {hoje}\n\n"

                for nome, servico, data, hora in hoje_lista:
                    valor = SERVICOS.get(servico, 0)
                    total += valor
                    texto += f"{hora} - {nome} ({servico}) R${valor}\n"

                texto += f"\n💰 Total: R${total}"
            else:
                texto = f"Nenhum agendamento hoje."

            bot.send_message(ADMIN_ID, texto)
            time.sleep(60)

        time.sleep(30)

threading.Thread(target=relatorio_diario).start()

# ================= WEBHOOK =================

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
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
