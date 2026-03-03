import os
import telebot
from telebot import types

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 1532248370

bot = telebot.TeleBot(TOKEN)

usuarios = {}

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("📅 Agendar horário")
    btn2 = types.KeyboardButton("📋 Ver agendamentos")

    markup.add(btn1)
    markup.add(btn2)

    bot.send_message(
        message.chat.id,
        "💇‍♀️ Bem-vinda ao Salão Bella!\n\nEscolha uma opção:",
        reply_markup=markup
    )
@bot.message_handler(func=lambda message: message.text == "📅 Agendar horário")
def botao_agendar(message):
    usuarios[message.chat.id] = {"etapa": "nome"}
    bot.send_message(message.chat.id, "Qual é seu nome?")
@bot.message_handler(func=lambda message: True)
def responder(message):
    chat_id = message.chat.id

    if chat_id in usuarios:
        etapa = usuarios[chat_id]["etapa"]

        if etapa == "nome":
            usuarios[chat_id]["nome"] = message.text
            usuarios[chat_id]["etapa"] = "telefone"
            bot.send_message(chat_id, "Digite seu telefone com DDD:")

        elif etapa == "telefone":
            usuarios[chat_id]["telefone"] = message.text
            usuarios[chat_id]["etapa"] = "servico"
            bot.send_message(chat_id, "Qual serviço deseja?")

        elif etapa == "servico":
            usuarios[chat_id]["servico"] = message.text
            usuarios[chat_id]["etapa"] = "horario"
            bot.send_message(chat_id, "Qual melhor dia e horário?")

        elif etapa == "horario":
            usuarios[chat_id]["horario"] = message.text

            nome = usuarios[chat_id]["nome"]
            telefone = usuarios[chat_id]["telefone"]
            servico = usuarios[chat_id]["servico"]
            horario = usuarios[chat_id]["horario"]

            # Salvar em arquivo
            with open("agendamentos.txt", "a", encoding="utf-8") as arquivo:
                arquivo.write(
                    f"Nome: {nome} | Telefone: {telefone} | Serviço: {servico} | Horário: {horario}\n"
                )

            # ✅ NOTIFICAÇÃO PARA VOCÊ
            mensagem_admin = (
                "📢 NOVO AGENDAMENTO!\n\n"
                f"👤 Nome: {nome}\n"
                f"📞 Telefone: {telefone}\n"
                f"💅 Serviço: {servico}\n"
                f"🕒 Horário: {horario}"
            )

            bot.send_message(ADMIN_ID, mensagem_admin)

            bot.send_message(chat_id,
                             "✅ Pedido enviado! Em breve entraremos em contato.")

            del usuarios[chat_id]

    else:
        bot.send_message(chat_id, "Digite /agendar para marcar horário.")
@bot.message_handler(func=lambda message: message.text == "📋 Ver agendamentos")
def ver_agendamentos(message):
    try:
        with open("agendamentos.txt", "r", encoding="utf-8") as arquivo:
            dados = arquivo.read()

            if dados.strip() == "":
                bot.send_message(message.chat.id, "Nenhum agendamento ainda.")
            else:
                bot.send_message(message.chat.id, f"📅 Agendamentos:\n\n{dados}")
    except:
        bot.send_message(message.chat.id, "Nenhum agendamento encontrado.")
print("Bot rodando...")
bot.infinity_polling()
