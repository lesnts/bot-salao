import psycopg2
import os

# ================= CONEXÃO =================

def conectar():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

# ================= CRIAR TABELAS =================

def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id SERIAL PRIMARY KEY,
        telegram_id BIGINT UNIQUE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agendamentos (
        id SERIAL PRIMARY KEY,
        cliente_id INTEGER,
        nome TEXT,
        telefone TEXT,
        servico TEXT,
        valor INTEGER,
        data TEXT,
        horario TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS updates_processados (
        update_id BIGINT PRIMARY KEY
    );
    """)

    conn.commit()
    conn.close()

# ================= ANTI DUPLICAÇÃO =================

def processar_update(update):

    # 🔒 camada 1: update duplicado
    if update_ja_processado(update.update_id):
        return

    chat_id = None

    if update.message:
        chat_id = update.message.chat.id
    elif update.callback_query:
        chat_id = update.callback_query.message.chat.id

    # 🔒 camada 2: lock por usuário
    if chat_id:
        if not adquirir_lock(chat_id):
            return  # já está sendo processado

    try:
        bot.process_new_updates([update])

    finally:
        if chat_id:
            liberar_lock(chat_id)

# ================= CLIENTES =================

def buscar_cliente(telegram_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, telegram_id FROM clientes WHERE telegram_id = %s",
        (telegram_id,)
    )

    resultado = cursor.fetchone()
    conn.close()

    if resultado:
        return {"id": resultado[0], "telegram_id": resultado[1]}
    return None


def criar_cliente(telegram_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO clientes (telegram_id) VALUES (%s) ON CONFLICT DO NOTHING",
        (telegram_id,)
    )

    conn.commit()
    conn.close()

# ================= AGENDAMENTOS =================

def salvar_agendamento(cliente_id, nome, telefone, servico, valor, data, horario):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO agendamentos 
        (cliente_id, nome, telefone, servico, valor, data, horario)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (cliente_id, nome, telefone, servico, valor, data, horario))

    conn.commit()
    conn.close()


def listar_agendamentos(cliente_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT nome, servico, valor, data, horario
        FROM agendamentos
        WHERE cliente_id = %s
        ORDER BY data, horario
    """, (cliente_id,))

    dados = cursor.fetchall()
    conn.close()

    return dados


def horario_ocupado(cliente_id, data, horario):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM agendamentos
        WHERE data = %s AND horario = %s
    """, (data, horario))

    resultado = cursor.fetchone()
    conn.close()

    return resultado is not None

def adquirir_lock(chat_id):
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO locks (chat_id) VALUES (%s)",
            (chat_id,)
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


def liberar_lock(chat_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM locks WHERE chat_id = %s",
        (chat_id,)
    )

    conn.commit()
    conn.close()
