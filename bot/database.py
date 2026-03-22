import sqlite3

def conectar():
    return sqlite3.connect("agendamentos.db", check_same_thread=False)


def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        nome TEXT,
        plano TEXT DEFAULT 'free'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agendamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        nome TEXT,
        telefone TEXT,
        servico TEXT,
        valor REAL,
        data TEXT,
        hora TEXT
    )
    """)

    conn.commit()
    conn.close()


# ================= CLIENTES =================

def criar_cliente(telegram_id, nome="Novo Cliente"):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO clientes (telegram_id, nome)
    VALUES (?, ?)
    """, (telegram_id, nome))

    conn.commit()
    conn.close()


def buscar_cliente(telegram_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, telegram_id, nome, plano
    FROM clientes WHERE telegram_id=?
    """, (telegram_id,))

    cliente = cursor.fetchone()
    conn.close()

    if cliente:
        return {
            "id": cliente[0],
            "telegram_id": cliente[1],
            "nome": cliente[2],
            "plano": cliente[3]
        }
    return None


# ================= AGENDAMENTOS =================

def salvar_agendamento(cliente_id, nome, telefone, servico, valor, data, hora):
    conn = conectar()
    cursor = conn.cursor()

    # trava contra duplicidade
    cursor.execute("""
    SELECT * FROM agendamentos
    WHERE cliente_id=? AND data=? AND hora=?
    """, (cliente_id, data, hora))

    if cursor.fetchone():
        conn.close()
        return False

    cursor.execute("""
    INSERT INTO agendamentos (cliente_id, nome, telefone, servico, valor, data, hora)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (cliente_id, nome, telefone, servico, valor, data, hora))

    conn.commit()
    conn.close()
    return True


def listar_agendamentos(cliente_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT nome, servico, valor, data, hora
    FROM agendamentos
    WHERE cliente_id=?
    ORDER BY data, hora
    """, (cliente_id,))

    dados = cursor.fetchall()
    conn.close()
    return dados


def horario_ocupado(cliente_id, data, hora):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 1 FROM agendamentos
    WHERE cliente_id=? AND data=? AND hora=?
    """, (cliente_id, data, hora))

    ocupado = cursor.fetchone() is not None
    conn.close()
    return ocupado


def faturamento_por_dia(cliente_id, data):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT SUM(valor)
    FROM agendamentos
    WHERE cliente_id=? AND data=?
    """, (cliente_id, data))

    total = cursor.fetchone()[0]
    conn.close()

    return total or 0
