from flask import Flask, render_template
from bot.database import listar_agendamentos, buscar_cliente

app = Flask(__name__)

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
