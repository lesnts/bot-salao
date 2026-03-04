import os
from flask import Flask, request
import telebot

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 1532248370
WEBHOOK_URL = "https://bot-salao-production.up.railway.app/"  # seu domínio Railway

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
usuarios = {}

# ================= MENU =================
from telebot import types

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("📅 Agendar horário")
    btn2 = types.KeyboardButton("📋 Ver agendamentos")
    markup.add(btn1, btn2)
    bot.send_message(
        message.chat.id,
        "💇‍♀️ Bem-vinda ao Salão Bella!\n\nEscolha uma opção:",
        reply_markup=markup
    )

# ================= VER AGENDAMENTOS =================
@bot.message_handler(func=lambda message: message.text == "📋 Ver agendamentos")
def ver_agendamentos(message):
    chat_id = message.chat.id
    try:
        with open("agendamentos.txt", "r", encoding="utf-8") as arquivo:
            linhas = arquivo.readlines()
        meus = [l for l in linhas if f"ID:{chat_id}" in l]
        if meus:
            bot.send_message(chat_id, "📅 Seus agendamentos:\n\n" + "".join(meus))
        else:
            bot.send_message(chat_id, "Você ainda não possui agendamentos.")
    except FileNotFoundError:
        bot.send_message(chat_id, "Nenhum agendamento encontrado.")

# ================= AGENDAR =================
@bot.message_handler(func=lambda message: message.text == "📅 Agendar horário")
def botao_agendar(message):
    usuarios[message.chat.id] = {"etapa": "nome"}
    bot.send_message(message.chat.id, "Qual é seu nome?")

# ================= FLUXO =================
@bot.message_handler(func=lambda message: True)
def responder(message):
    chat_id = message.chat.id
    if chat_id not in usuarios:
        return
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
        bot.send_message(
            chat_id,
            "Escolha um horário disponível:\n"
            "10:00\n11:00\n14:00\n15:00\n16:00\n\n"
            "Ou digite outro se necessário:"
        )

    elif etapa == "horario":
        horario = message.text
        try:
            with open("agendamentos.txt", "r", encoding="utf-8") as arquivo:
                if horario in arquivo.read():
                    bot.send_message(chat_id, "❌ Esse horário já foi reservado. Escolha outro.")
                    return
        except FileNotFoundError:
            pass

        usuarios[chat_id]["horario"] = horario
        nome = usuarios[chat_id]["nome"]
        telefone = usuarios[chat_id]["telefone"]
        servico = usuarios[chat_id]["servico"]

        with open("agendamentos.txt", "a", encoding="utf-8") as arquivo:
            arquivo.write(
                f"ID:{chat_id} | Nome:{nome} | Telefone:{telefone} | Serviço:{servico} | Horário:{horario}\n"
            )

        mensagem_admin = (
            "📢 NOVO AGENDAMENTO!\n\n"
            f"👤 Nome: {nome}\n"
            f"📞 Telefone: {telefone}\n"
            f"💅 Serviço: {servico}\n"
            f"🕒 Horário: {horario}"
        )

        bot.send_message(ADMIN_ID, mensagem_admin)
        bot.send_message(chat_id, "✅ Pedido enviado! Em breve entraremos em contato.")
        del usuarios[chat_id]

# ================= PAINEL ADMIN =================
@bot.message_handler(commands=['admin'])
def painel_admin(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ Você não tem permissão.")
        return
    try:
        with open("agendamentos.txt", "r", encoding="utf-8") as arquivo:
            dados = arquivo.read()
        if dados.strip() == "":
            bot.send_message(ADMIN_ID, "Nenhum agendamento encontrado.")
        else:
            bot.send_message(ADMIN_ID, "📊 TODOS OS AGENDAMENTOS:\n\n" + dados)
    except FileNotFoundError:
        bot.send_message(ADMIN_ID, "Nenhum agendamento encontrado.")

# ================= WEBHOOK =================
@app.route('/', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

@app.route('/', methods=['GET'])
def webhook_check():
    return "Bot ativo!", 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    print("Bot rodando com webhook!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
