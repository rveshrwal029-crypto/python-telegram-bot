from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import datetime
import re

# ====== CONFIG ======
TOKEN = "8479394710:AAFywL1HdBHsOnxI6wNDnRxYdOX3M1WS9" 
ADMINS = {6603524612, 7773526534}
authorized_users = set(ADMINS)

# ====== STORAGE ======
transactions = {}     # {chat_id: [transactions]}
exchange_rates = {}   # {chat_id: rate}
fee_rates = {}        # {chat_id: fee}

# ====== HELPERS ======
def is_authorized(user_id):
    return user_id in authorized_users

def add_transaction(chat_id, user, amount_inr=0, amount_usd=0, type="income"):
    if chat_id not in transactions:
        transactions[chat_id] = []
    transactions[chat_id].append({
        "user": user,
        "amount_inr": amount_inr,
        "amount_usd": amount_usd,
        "type": type,
        "time": datetime.datetime.now().strftime("%H:%M:%S")
    })

def get_exchange_rate(chat_id):
    return exchange_rates.get(chat_id, 106)

def get_fee_rate(chat_id):
    return fee_rates.get(chat_id, 0)

# ====== COMMANDS ======
def start(update: Update, context: CallbackContext):
    update.message.reply_text("✅ Bot started! Use + / - / T / T- for transactions.")

def summary(update: Update, context: CallbackContext):
    if not is_authorized(update.effective_user.id):
        return
    chat_id = update.effective_chat.id
    update.message.reply_text(summary_message(chat_id), parse_mode="Markdown")

def clear_bills(update: Update, context: CallbackContext):
    if not is_authorized(update.effective_user.id):
        return
    chat_id = update.effective_chat.id
    transactions[chat_id] = []
    update.message.reply_text("Today's bill has been cleared and recording can be restarted")

# ====== SUMMARY MESSAGE ======
def summary_message(chat_id):
    tx = transactions.get(chat_id, [])
    incomes = [t for t in tx if t["type"] == "income"]
    payouts = [t for t in tx if t["type"] == "payout"]

    total_income_inr = sum(t["amount_inr"] for t in incomes)
    total_income_usd = sum(t["amount_usd"] for t in incomes)

    total_payout_inr = sum(t["amount_inr"] for t in payouts)
    total_payout_usd = sum(t["amount_usd"] for t in payouts)

    not_yet_inr = total_income_inr - total_payout_inr
    not_yet_usd = total_income_usd - total_payout_usd

    rate = get_exchange_rate(chat_id)
    fee = get_fee_rate(chat_id)

    income_lines = "\n".join(
        [f"{t['time']}   {t['amount_inr']:.0f} / {rate} = {t['amount_usd']:.2f}U   {t['user']}" for t in incomes]
    ) or "None"

    payout_lines = "\n".join(
        [f"{t['time']}   {t['amount_usd']:.2f}U ({t['amount_inr']:.0f})   {t['user']}" for t in payouts]
    ) or "None"

    message = f"""
 *Today's Income ({len(incomes)})*
{income_lines}

 *Today's Issued ({len(payouts)})*
{payout_lines}

 Total Income : {total_income_inr}
 Exchange Rate : {rate}
 Fee Rate : {fee}%

 Already issued : {total_income_inr} | {total_income_usd:.2f}U
 Should be issued : {total_payout_inr} | {total_payout_usd:.2f}U
 Not yet issued : {not_yet_inr} | {not_yet_usd:.2f}U
    """
    return message

# ====== TEXT HANDLER ======
def text_handler(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip()
    user = update.effective_user.first_name

    # ❌ Ignore unauthorized users
    if not is_authorized(user_id):
        return

    # ✅ Add operator
    if text.lower().startswith("add "):
        try:
            new_id = int(text.split()[1])
            authorized_users.add(new_id)
            return update.message.reply_text(f"✅ Added operator with ID: {new_id}")
        except:
            return update.message.reply_text("⚠️ Example: add 123456789")

    # ✅ Remove operator
    if text.lower().startswith("del "):
        try:
            remove_id = int(text.split()[1])
            authorized_users.discard(remove_id)
            return update.message.reply_text(f"❌ Removed operator with ID: {remove_id}")
        except:
            return update.message.reply_text("⚠️ Example: del 123456789")

    # ✅ Exchange rate
    if text.lower().startswith("exchange"):
        match = re.search(r"(\d+(\.\d+)?)", text)
        if match:
            exchange_rates[chat_id] = float(match.group(1))
            return update.message.reply_text(f"Exchange rate set successfully, current exchange rate is: {exchange_rates[chat_id]}")
        else:
            return update.message.reply_text("⚠️ Example: exchange rate109")

    # ✅ Fee rate
    if text.lower().startswith("fee"):
        match = re.search(r"(\d+(\.\d+)?)", text)
        if match:
            fee_rates[chat_id] = float(match.group(1))
            return update.message.reply_text(f"⚖️ Fee rate set: {fee_rates[chat_id]}%")
        else:
            return update.message.reply_text("⚠️ Example: fee 2")

    # ✅ Clear bills
    if text.lower().startswith("clearing bills"):
        transactions[chat_id] = []
        return update.message.reply_text("Today's bill has been cleared and recording can be restarted")

    rate = get_exchange_rate(chat_id)

    # ✅ Income (+100)
    if text.startswith("+"):
        try:
            amount = float(text[1:].strip())
            usd = amount / rate
            add_transaction(chat_id, user, amount_inr=amount, amount_usd=usd, type="income")
            return update.message.reply_text(summary_message(chat_id), parse_mode="Markdown")
        except:
            return update.message.reply_text("⚠️ Invalid income format.")

    # ✅ Negative Income (-100)
    if text.startswith("-"):
        try:
            amount = float(text[1:].strip())
            inr = -amount
            usd = inr / rate
            add_transaction(chat_id, user, amount_inr=inr, amount_usd=usd, type="income")
            return update.message.reply_text(summary_message(chat_id), parse_mode="Markdown")
        except:
            return update.message.reply_text("⚠️ Invalid negative income format.")

    # ✅ Payout (T100 or T100U)
    if text.upper().startswith("T") and not text.upper().startswith("T-"):
        try:
            amt = float(text[1:].replace("U", "").replace("u", "").strip())
            inr = amt * rate
            add_transaction(chat_id, user, amount_inr=inr, amount_usd=amt, type="payout")
            return update.message.reply_text(summary_message(chat_id), parse_mode="Markdown")
        except:
            return update.message.reply_text("⚠️ Invalid payout format.")

    # ✅ Payout reversal (T-100 or T-100U)
    if text.upper().startswith("T-"):
        try:
            amt = float(text[2:].replace("U", "").replace("u", "").strip())
            inr = -amt * rate
            add_transaction(chat_id, user, amount_inr=inr, amount_usd=-amt, type="payout")
            return update.message.reply_text(summary_message(chat_id), parse_mode="Markdown")
        except:
            return update.message.reply_text("⚠️ Invalid payout reversal format.")

# ====== MAIN ======
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("summary", summary))
    dp.add_handler(CommandHandler("clear", clear_bills))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import datetime
import re

# ====== CONFIG ======
TOKEN = "8479394710:AAFywL1HdBHsOnxI6wNDnrxYdOX3M1WS9gQ"
ADMINS = {6603524612, 7773526534}
authorized_users = set(ADMINS)

# ====== STORAGE ======
transactions = {}     # {chat_id: [transactions]}
exchange_rates = {}   # {chat_id: rate}
fee_rates = {}        # {chat_id: fee}

# ====== HELPERS ======
def is_authorized(user_id):
    return user_id in authorized_users

def add_transaction(chat_id, user, amount_inr=0, amount_usd=0, type="income"):
    if chat_id not in transactions:
        transactions[chat_id] = []
    transactions[chat_id].append({
        "user": user,
        "amount_inr": amount_inr,
        "amount_usd": amount_usd,
        "type": type,
        "time": datetime.datetime.now().strftime("%H:%M:%S")
    })

def get_exchange_rate(chat_id):
    return exchange_rates.get(chat_id, 106)

def get_fee_rate(chat_id):
    return fee_rates.get(chat_id, 0)

# ====== COMMANDS ======
def start(update: Update, context: CallbackContext):
    update.message.reply_text("✅ Bot started! Use + / - / T / T- for transactions.")

def summary(update: Update, context: CallbackContext):
    if not is_authorized(update.effective_user.id):
        return
    chat_id = update.effective_chat.id
    update.message.reply_text(summary_message(chat_id), parse_mode="Markdown")

def clear_bills(update: Update, context: CallbackContext):
    if not is_authorized(update.effective_user.id):
        return
    chat_id = update.effective_chat.id
    transactions[chat_id] = []
    update.message.reply_text("Today's bill has been cleared and recording can be restarted")

# ====== SUMMARY MESSAGE ======
def summary_message(chat_id):
    tx = transactions.get(chat_id, [])
    incomes = [t for t in tx if t["type"] == "income"]
    payouts = [t for t in tx if t["type"] == "payout"]

    total_income_inr = sum(t["amount_inr"] for t in incomes)
    total_income_usd = sum(t["amount_usd"] for t in incomes)

    total_payout_inr = sum(t["amount_inr"] for t in payouts)
    total_payout_usd = sum(t["amount_usd"] for t in payouts)

    not_yet_inr = total_income_inr - total_payout_inr
    not_yet_usd = total_income_usd - total_payout_usd

    rate = get_exchange_rate(chat_id)
    fee = get_fee_rate(chat_id)

    income_lines = "\n".join(
        [f"{t['time']}   {t['amount_inr']:.0f} / {rate} = {t['amount_usd']:.2f}U   {t['user']}" for t in incomes]
    ) or "None"

    payout_lines = "\n".join(
        [f"{t['time']}   {t['amount_usd']:.2f}U ({t['amount_inr']:.0f})   {t['user']}" for t in payouts]
    ) or "None"

    message = f"""
 *Today's Income ({len(incomes)})*
{income_lines}

 *Today's Issued ({len(payouts)})*
{payout_lines}

 Total Income : {total_income_inr}
 Exchange Rate : {rate}
 Fee Rate : {fee}%

 Already issued : {total_income_inr} | {total_income_usd:.2f}U
 Should be issued : {total_payout_inr} | {total_payout_usd:.2f}U
 Not yet issued : {not_yet_inr} | {not_yet_usd:.2f}U
    """
    return message

# ====== TEXT HANDLER ======
def text_handler(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip()
    user = update.effective_user.first_name

    # ❌ Ignore unauthorized users
    if not is_authorized(user_id):
        return

    # ✅ Add operator
    if text.lower().startswith("add "):
        try:
            new_id = int(text.split()[1])
            authorized_users.add(new_id)
            return update.message.reply_text(f"✅ Added operator with ID: {new_id}")
        except:
            return update.message.reply_text("⚠️ Example: add 123456789")

    # ✅ Remove operator
    if text.lower().startswith("del "):
        try:
            remove_id = int(text.split()[1])
            authorized_users.discard(remove_id)
            return update.message.reply_text(f"❌ Removed operator with ID: {remove_id}")
        except:
            return update.message.reply_text("⚠️ Example: del 123456789")

    # ✅ Exchange rate
    if text.lower().startswith("exchange"):
        match = re.search(r"(\d+(\.\d+)?)", text)
        if match:
            exchange_rates[chat_id] = float(match.group(1))
            return update.message.reply_text(f"Exchange rate set successfully, current exchange rate is: {exchange_rates[chat_id]}")
        else:
            return update.message.reply_text("⚠️ Example: exchange rate109")

    # ✅ Fee rate
    if text.lower().startswith("fee"):
        match = re.search(r"(\d+(\.\d+)?)", text)
        if match:
            fee_rates[chat_id] = float(match.group(1))
            return update.message.reply_text(f"⚖️ Fee rate set: {fee_rates[chat_id]}%")
        else:
            return update.message.reply_text("⚠️ Example: fee 2")

    # ✅ Clear bills
    if text.lower().startswith("clearing bills"):
        transactions[chat_id] = []
        return update.message.reply_text("Today's bill has been cleared and recording can be restarted")

    rate = get_exchange_rate(chat_id)

    # ✅ Income (+100)
    if text.startswith("+"):
        try:
            amount = float(text[1:].strip())
            usd = amount / rate
            add_transaction(chat_id, user, amount_inr=amount, amount_usd=usd, type="income")
            return update.message.reply_text(summary_message(chat_id), parse_mode="Markdown")
        except:
            return update.message.reply_text("⚠️ Invalid income format.")

    # ✅ Negative Income (-100)
    if text.startswith("-"):
        try:
            amount = float(text[1:].strip())
            inr = -amount
            usd = inr / rate
            add_transaction(chat_id, user, amount_inr=inr, amount_usd=usd, type="income")
            return update.message.reply_text(summary_message(chat_id), parse_mode="Markdown")
        except:
            return update.message.reply_text("⚠️ Invalid negative income format.")

    # ✅ Payout (T100 or T100U)
    if text.upper().startswith("T") and not text.upper().startswith("T-"):
        try:
            amt = float(text[1:].replace("U", "").replace("u", "").strip())
            inr = amt * rate
            add_transaction(chat_id, user, amount_inr=inr, amount_usd=amt, type="payout")
            return update.message.reply_text(summary_message(chat_id), parse_mode="Markdown")
        except:
            return update.message.reply_text("⚠️ Invalid payout format.")

    # ✅ Payout reversal (T-100 or T-100U)
    if text.upper().startswith("T-"):
        try:
            amt = float(text[2:].replace("U", "").replace("u", "").strip())
            inr = -amt * rate
            add_transaction(chat_id, user, amount_inr=inr, amount_usd=-amt, type="payout")
            return update.message.reply_text(summary_message(chat_id), parse_mode="Markdown")
        except:
            return update.message.reply_text("⚠️ Invalid payout reversal format.")

# ====== MAIN ======
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("summary", summary))
    dp.add_handler(CommandHandler("clear", clear_bills))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
