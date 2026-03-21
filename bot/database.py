import sqlite3

def conectar():
    return sqlite3.connect("agendamentos.db")


def criar_tabela():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agendamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        servico TEXT,
        data TEXT,
        hora TEXT
    )
    """)

    conn.commit()
    conn.close()


def salvar_agendamento(nome, servico, data, hora):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO agendamentos (nome, servico, data, hora) VALUES (?, ?, ?, ?)",
        (nome, servico, data, hora)
    )

    conn.commit()
    conn.close()


def listar_agendamentos():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT nome, servico, data, hora FROM agendamentos")
    dados = cursor.fetchall()

    conn.close()
    return dados


def horario_ocupado(data, hora):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM agendamentos WHERE data=? AND hora=?",
        (data, hora)
    )

    resultado = cursor.fetchone()

    conn.close()
    return resultado is not None
