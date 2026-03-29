import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")

def conectar():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


# ================= TABELAS =================

def criar_tabelas():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id SERIAL PRIMARY KEY,
        telegram_id BIGINT UNIQUE
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS agendamentos (
        id SERIAL PRIMARY KEY,
        cliente_id INTEGER,
        nome TEXT,
        telefone TEXT,
        servico TEXT,
        valor INTEGER,
        data DATE,
        horario TIME,

        CONSTRAINT unique_agendamento UNIQUE (cliente_id, data, horario)
    );
    """)

    conn.commit()
    cur.close()
    conn.close()


# ================= CLIENTES =================

def buscar_cliente(telegram_id):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT * FROM clientes WHERE telegram_id = %s", (telegram_id,))
    cliente = cur.fetchone()

    cur.close()
    conn.close()

    return cliente


def criar_cliente(telegram_id):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO clientes (telegram_id)
    VALUES (%s)
    ON CONFLICT (telegram_id) DO NOTHING
    """, (telegram_id,))

    conn.commit()
    cur.close()
    conn.close()


# ================= AGENDAMENTOS =================

def salvar_agendamento(cliente_id, nome, telefone, servico, valor, data, horario):
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute("""
        INSERT INTO agendamentos
        (cliente_id, nome, telefone, servico, valor, data, horario)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (cliente_id, nome, telefone, servico, valor, data, horario))

        conn.commit()

    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        print("⚠️ Agendamento duplicado ignorado")

    finally:
        cur.close()
        conn.close()


def listar_agendamentos(cliente_id):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
    SELECT nome, servico, valor, data, horario
    FROM agendamentos
    WHERE cliente_id = %s
    ORDER BY data, horario
    """, (cliente_id,))

    dados = cur.fetchall()

    cur.close()
    conn.close()

    return dados


def horario_ocupado(cliente_id, data, horario):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
    SELECT 1 FROM agendamentos
    WHERE cliente_id = %s AND data = %s AND horario = %s
    """, (cliente_id, data, horario))

    ocupado = cur.fetchone() is not None

    cur.close()
    conn.close()

    return ocupado
