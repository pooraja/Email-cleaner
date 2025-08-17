# cleaner.py
import imaplib, email, datetime, json, shutil
from pathlib import Path
import pandas as pd
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
from config import load_config

config = load_config()
proton_cfg = config["proton"]

REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)

# --- Tunables ---
LARGE_MB = 5
PROMO_KEYWORDS = ("sale", "offer", "discount", "deal", "limited time", "coupon", "promo")
PERSONAL_DOMAINS = ("gmail.com", "proton.me", "protonmail.com", "outlook.com", "yahoo.com")

def _decode(s: str | None) -> str:
    if not s:
        return ""
    try:
        return str(make_header(decode_header(s)))
    except Exception:
        return s

def connect_proton():
    # Proton Mail Bridge using STARTTLS on 1143
    imap = imaplib.IMAP4(proton_cfg["host"], proton_cfg["port"])
    imap.starttls()
    imap.login(proton_cfg["username"], proton_cfg["password"])
    return imap

def categorize_and_action(subject: str | None, from_: str | None, unsub: str | None, size_mb: float | None):
    subj = (subject or "").lower()
    sender = (from_ or "").lower()
    has_unsub = bool(unsub and str(unsub).strip())

    if has_unsub:
        return "newsletter", "archive"

    if any(k in subj for k in PROMO_KEYWORDS):
        return "promotion", "trash"

    if size_mb is not None and size_mb > LARGE_MB:
        return "large", "archive"

    if any(dom in sender for dom in PERSONAL_DOMAINS):
        return "personal", "keep"

    return "other", "keep"

def run_cleaner():
    imap = connect_proton()
    rows = []
    try:
        imap.select("INBOX")
        typ, data = imap.search(None, "ALL")
        ids = data[0].split()[-50:] if data and data[0] else []

        for msg_id in ids:
            typ, msg_data = imap.fetch(msg_id, "(RFC822)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue

            msg = email.message_from_bytes(msg_data[0][1])
            from_ = _decode(msg.get("From"))
            subject = _decode(msg.get("Subject"))

            # Parse email date to ISO 8601
            raw_date = msg.get("Date")
            try:
                date_ = parsedate_to_datetime(raw_date).isoformat()
            except Exception:
                date_ = None

            try:
                size_mb = round(len(msg.as_bytes()) / (1024 * 1024), 2)
            except Exception:
                size_mb = None

            unsub = msg.get("List-Unsubscribe")

            category, action = categorize_and_action(subject, from_, unsub, size_mb if size_mb is not None else 0.0)

            rows.append({
                "Date": date_,
                "From": from_,
                "Subject": subject,
                "Category": category,
                "Action": action,
                "SizeMB": size_mb if size_mb is not None else 0.0,
                "Unsubscribe": unsub
            })
    finally:
        # Always logout even if something fails
        try:
            imap.logout()
        except Exception:
            pass

    # Build dataframe (can be empty)
    df = pd.DataFrame(rows)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"report_{ts}.csv"
    df.to_csv(report_path, index=False)

    # Save run status (atomic write)
    status = {
        "last_run": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": int(len(df)),
        "archived": int((df["Action"] == "archive").sum()) if not df.empty else 0,
        "trashed": int((df["Action"] == "trash").sum()) if not df.empty else 0,
        "report": str(report_path)
    }

    tmp_path = REPORT_DIR / "status_tmp.json"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(status, f)
    shutil.move(tmp_path, REPORT_DIR / "status.json")

    return str(report_path)
