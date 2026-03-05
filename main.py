import os
from flask import Flask, request
import telebot
from telebot import types

TOKEN = os.getenv("TOKEN")  # Token do BotFather
ADMIN_ID = 1532248370       # Seu ID de admin
WEBHOOK_URL = "https://bot-salao-production.up.railway.app/"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
usuarios = {}
HORARIOS_DISPONIVEIS = ["10:00", "11:00", "14:00", "15:00", "16:00"]

# ================= MENU PRINCIPAL =================
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

# ================= VER AGENDAMENTOS =================
@bot.message_handler(func=lambda m: m.text == "📋 Meus agendamentos")
def ver_agendamentos(message):
    chat_id = message.chat.id
    try:
        with open("agendamentos.txt", "r", encoding="utf-8") as arquivo:
            linhas = [l for l in arquivo.readlines() if f"ID:{chat_id}" in l]
        if linhas:
            texto = "📅 Seus agendamentos:\n"
            for l in linhas:
                partes = l.strip().split("|")
                servico = partes[3].split(":")[1].strip()
                horario = partes[4].split(":")[1].strip()
                texto += f" - {servico} às {horario}\n"
            bot.send_message(chat_id, texto)
        else:
            bot.send_message(chat_id, "Você não possui agendamentos.")
    except:
        bot.send_message(chat_id, "Nenhum agendamento encontrado.")

# ================= CANCELAR =================
@bot.message_handler(func=lambda m: m.text == "❌ Cancelar")
def cancelar(message):
    chat_id = message.chat.id
    agendados = []
    try:
        with open("agendamentos.txt", "r", encoding="utf-8") as arquivo:
            agendados = [l for l in arquivo.readlines() if f"ID:{chat_id}" in l]
    except:
        pass

    if not agendados:
        bot.send_message(chat_id, "Você não possui agendamentos para cancelar.")
        return

    markup = types.InlineKeyboardMarkup()
    for l in agendados:
        partes = l.strip().split("|")
        horario = partes[4].split(":")[1].strip()
        markup.add(types.InlineKeyboardButton(f"Cancelar {horario}", callback_data=f"cancelar|{horario}"))
    bot.send_message(chat_id, "Escolha o horário para cancelar:", reply_markup=markup)

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
        bot.send_message(chat_id, "Qual serviço deseja?")        
    elif etapa == "servico":
        usuarios[chat_id]["servico"] = message.text
        usuarios[chat_id]["etapa"] = "horario"
        markup = types.InlineKeyboardMarkup()
        agendados = []
        try:
            with open("agendamentos.txt", "r", encoding="utf-8") as arquivo:
                agendados = [l.split("|")[4].split(":")[1].strip() for l in arquivo.readlines()]
        except:
            pass
        for h in HORARIOS_DISPONIVEIS:
            texto = f"{h} ✅" if h not in agendados else f"{h} ❌"
            cb = h if h not in agendados else "ocupado"
            markup.add(types.InlineKeyboardButton(texto, callback_data=cb))
        bot.send_message(chat_id, "Escolha o horário:", reply_markup=markup)

# ================= CALLBACK =================
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    chat_id = call.message.chat.id
    data = call.data

    if data.startswith("cancelar|"):
        horario = data.split("|")[1]
        try:
            with open("agendamentos.txt", "r", encoding="utf-8") as f:
                linhas = f.readlines()
            linhas = [l for l in linhas if not (f"ID:{chat_id}" in l and horario in l)]
            with open("agendamentos.txt", "w", encoding="utf-8") as f:
                f.writelines(linhas)
            bot.send_message(chat_id, f"❌ Horário {horario} cancelado!")
        except:
            bot.send_message(chat_id, "Erro ao cancelar horário.")
        return

    if data == "ocupado":
        bot.answer_callback_query(call.id, "Esse horário já está ocupado!")
        return

    nome = usuarios[chat_id]["nome"]
    telefone = usuarios[chat_id]["telefone"]
    servico = usuarios[chat_id]["servico"]
    horario = data
    with open("agendamentos.txt", "a", encoding="utf-8") as f:
        f.write(f"ID:{chat_id} | Nome:{nome} | Telefone:{telefone} | Serviço:{servico} | Horário:{horario}\n")

    bot.send_message(chat_id, f"✅ Horário {horario} confirmado!")
    bot.send_message(ADMIN_ID, f"📢 Novo agendamento!\n{nome} | {telefone} | {servico} | {horario}")
    del usuarios[chat_id]
    menu_principal(chat_id)

# ================= PAINEL ADMIN =================
@bot.message_handler(commands=['admin'])
def admin(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ Sem permissão")
        return
    agendados = []
    try:
        with open("agendamentos.txt", "r", encoding="utf-8") as f:
            agendados = f.readlines()
    except:
        pass
    texto = "📊 TODOS OS AGENDAMENTOS:\n"
    if agendados:
        for l in agendados:
            texto += l
    else:
        texto += "Nenhum agendamento."
    bot.send_message(ADMIN_ID, texto)
    
# ================= PEGAR ID =================
@bot.message_handler(commands=['id'])
def pegar_id(message):
    bot.send_message(message.chat.id, f"Seu ID é: {message.chat.id}")

# ================= WEBHOOK =================
@app.route('/', methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode("utf-8"))])
    return "!", 200

@app.route('/', methods=['GET'])
def check():
    return "Bot ativo", 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
