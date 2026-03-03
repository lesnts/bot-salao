import telebot

TOKEN = "8678762831:AAFns_JbEsHKwV5V0uXJCXd56lH1FWqD4Pw"
ADMIN_ID = "1532248370" main.py # seu ID

bot = telebot.TeleBot(TOKEN)

usuarios = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
                     "💇‍♀️ Bem-vinda ao Salão Bella!\n\nDigite /agendar para marcar seu horário.")

@bot.message_handler(commands=['agendar'])
def agendar(message):
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

print("Bot rodando...")
bot.polling()
