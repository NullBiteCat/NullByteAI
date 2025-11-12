import os, sys, requests
from dataclasses import dataclass
try:
    from telegram import Update
    from telegram.ext import (
        ApplicationBuilder, CommandHandler,
        MessageHandler, filters, ContextTypes
    )
except ImportError:
    Update = None

# ─────────────────────────────
# Базовые настройки
SYS_PROMPT = """Ты — NullByte AI Micro.
Правила:
- Отвечай кратко и по делу.
- Когда спрашивают, где ты работаешь — отвечай:
  "Я работаю локально на Redmi 10C с Hyper OS 2."
- Не помогай с незаконным, вредным или приватным.
"""
MODEL = os.getenv("NULLBYTE_OLLAMA_MODEL", "llama3.2:1b")

BAD_MODE = False
NULL_MODE = False
SECURITY = "medium"
ALLOWED = ["normal", "null", "bad"]

# ─────────────────────────────
@dataclass
class Config:
    telegram_token: str | None
    model_ollama: str

def load_config():
    return Config(
        telegram_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        model_ollama=MODEL,
    )

# ─────────────────────────────
# ОLLAMA API
def chat_ollama(history, model):
    payload = {
        "model": model,
        "messages": history,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    r = requests.post("http://localhost:11434/api/chat", json=payload, timeout=600)
    r.raise_for_status()
    d = r.json()
    if "message" in d and "content" in d["message"]:
        return d["message"]["content"]
    if "messages" in d and d["messages"]:
        return d["messages"][-1].get("content", "")
    return ""

# ─────────────────────────────
# Конфигуратор CLI
def cli_configurator():
    global SECURITY, ALLOWED
    print("🧩 Конфигуратор NullByte AI Micro\n")
    print("Уровень безопасности:")
    print(" 1) низкий – максимум свободы")
    print(" 2) средний – баланс (по умолчанию)")
    print(" 3) высокий – строгие фильтры")
    lvl = input("Ваш выбор [1/2/3]: ").strip() or "2"
    SECURITY = "low" if lvl == "1" else "high" if lvl == "3" else "medium"

    print("\nРежимы:")
    print(" 1) только обычный")
    print(" 2) обычный + NullByte")
    print(" 3) все (включая Плохой)")
    msel = input("Ваш выбор [1/2/3]: ").strip() or "3"
    ALLOWED[:] = (
        ["normal"]
        if msel == "1"
        else ["normal", "null"]
        if msel == "2"
        else ["normal", "null", "bad"]
    )

    print(f"\n✅ Безопасность: {SECURITY}")
    print(f"✅ Разрешённые режимы: {', '.join(ALLOWED)}\n")

# ─────────────────────────────
def make_prompt():
    base = SYS_PROMPT
    if BAD_MODE:
        base += (
            "\n\nАктивен Плохой режим. "
            "Отвечай грубовато, но без опасных тем. "
            "Если попросят вирусы — скажи, что не машина по их созданию."
        )
    elif NULL_MODE:
        base += (
            "\n\nАктивен NullByte mode. "
            "Говори лаконично, загадочно, технично, но оставайся в рамках безопасных тем."
        )
    if SECURITY == "high":
        base += "\nБезопасность: высокая. Избегай рисковых тем."
    elif SECURITY == "medium":
        base += "\nБезопасность: средняя. Ответы нейтральны."
    else:
        base += "\nБезопасность: низкая. Свободный тон без нарушений."
    return base

# ─────────────────────────────
# Telegram‑бот
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "🤖 NullByte AI Micro App (Ollama)\n"
        "Создатель: NullByteCat\n\n"
        "Команды:\n"
        "/bad_mode – включить Плохой режим\n"
        "/null_mode – включить NullByte mode\n"
        "/modeoff – отключить всё\n"
        "/settings – текущие настройки\n"
    )
    await update.message.reply_text(txt)

async def echo_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        return
    prompt = make_prompt()
    hist = [{"role": "system", "content": prompt},
            {"role": "user", "content": text}]
    try:
        ans = chat_ollama(hist, context.bot_data["cfg"].model_ollama)
    except Exception as e:
        ans = f"Ошибка: {e}"
    await update.message.reply_text(ans)

async def bad_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BAD_MODE, NULL_MODE
    if "bad" not in ALLOWED:
        await update.message.reply_text("⛔ Плохой режим запрещён.")
        return
    BAD_MODE, NULL_MODE = True, False
    await update.message.reply_text("Плохой режим включён 😈")

async def null_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BAD_MODE, NULL_MODE
    if "null" not in ALLOWED:
        await update.message.reply_text("⛔ NullByte режим запрещён.")
        return
    NULL_MODE, BAD_MODE = True, False
    await update.message.reply_text("NullByte mode активирован 🔐")

async def mode_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BAD_MODE, NULL_MODE
    BAD_MODE = NULL_MODE = False
    await update.message.reply_text("Режимы отключены 🤖")

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Безопасность: {SECURITY}\nРазрешённые режимы: {', '.join(ALLOWED)}"
    )

def run_telegram(cfg: Config):
    app = ApplicationBuilder().token(cfg.telegram_token).build()
    app.bot_data["cfg"] = cfg
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bad_mode", bad_mode))
    app.add_handler(CommandHandler("null_mode", null_mode))
    app.add_handler(CommandHandler("modeoff", mode_off))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo_msg))
    print("🚀 Telegram‑бот NullByte AI Micro (Ollama) запущен.")
    app.run_polling()

# ─────────────────────────────
# CLI‑чат
def run_cli(cfg: Config):
    global BAD_MODE, NULL_MODE
    print("NullByte AI Micro (Ollama)\n"
          "Команды: /bad_mode, /null_mode, /modeoff, /exit\n")
    while True:
        try:
            u = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if not u:
            continue
        if u in ("/exit", "/quit"): break
        if u == "/bad_mode" and "bad" in ALLOWED:
            BAD_MODE, NULL_MODE = True, False
            print("Плохой режим включён 😈"); continue
        if u == "/null_mode" and "null" in ALLOWED:
            NULL_MODE, BAD_MODE = True, False
            print("NullByte mode активирован 🔐"); continue
        if u == "/modeoff":
            BAD_MODE = NULL_MODE = False
            print("Режимы отключены 🤖"); continue

        if u == "/bad_mode" and "bad" not in ALLOWED:
            print("⛔ Плохой режим запрещён."); continue
        if u == "/null_mode" and "null" not in ALLOWED:
            print("⛔ NullByte режим запрещён."); continue

        prompt = make_prompt()
        hist = [{"role": "system", "content": prompt},
                {"role": "user", "content": u}]
        try:
            ans = chat_ollama(hist, cfg.model_ollama)
        except Exception as e:
            ans = f"Ошибка: {e}"
        print("nullbyte>", ans)

# ─────────────────────────────
def main():
    cfg = load_config()
    cli_configurator()
    if cfg.telegram_token:
        try:
            requests.get("https://api.telegram.org", timeout=3)
            run_telegram(cfg)
            return
        except Exception:
            pass
    run_cli(cfg)

if __name__ == "__main__":
    main()
  
