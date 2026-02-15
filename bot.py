import requests
import time
import hashlib
import json
import re
import random
import string
import sys
import os

# Fix encoding for Windows
if sys.platform == 'win32':
    os.system('')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from colorama import Fore, Style, init
init(autoreset=True)

# ===================== CONFIGURATION =====================
SALT = "vT*IUEGgyL"
REFERER_ID = "32csm5KxjqlKGaK8AiOewsvn0-YCiIYWbWPY3fyFyg4mTiqZ6jY9ziLqYenQzQSqEI75sA=="
BASE_URL = "https://app.allscale.io"
ACCOUNTS_FILE = "accounts.txt"

TEMPMAIL_LOL_API = "https://api.tempmail.lol"
MAIL_TM_API = "https://api.mail.tm"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"

# ===================== LOGGING =====================
W = Style.RESET_ALL
G = Fore.GREEN
R = Fore.RED
Y = Fore.YELLOW
C = Fore.CYAN
M = Fore.MAGENTA

def log(msg, level="info"):
    ts = time.strftime("%H:%M:%S")
    prefix = {"info": f"{C}INFO{W}", "success": f"{G} OK {W}", "error": f"{R}FAIL{W}", "wait": f"{Y}WAIT{W}", "step": f"{M}STEP{W}"}.get(level, f"{C}INFO{W}")
    if level == "wait":
        print(f"  {C}[{ts}]{W} [{prefix}] {msg}          ", end="\r")
    else:
        print(f"  {C}[{ts}]{W} [{prefix}] {msg}")

def banner():
    print(f"""
{C}  =============================================={W}
{G}     Allscale Auto Registration Bot{W}
{Y}     Referral: {REFERER_ID[:25]}...{W}
{C}  =============================================={W}
""")

def divider(num, total):
    print(f"\n{C}  --- [AKUN {num}/{total}] ---{W}")

# ===================== SIGNATURE =====================
def generate_signature(timestamp):
    return hashlib.sha256(f"{SALT}{timestamp}".encode()).hexdigest()

# ===================== OTP EXTRACTION =====================
def extract_otp(text):
    if not text:
        return None
    clean = re.sub(r'<[^>]+>', ' ', text)
    for p in [r'(?:code|otp|verification|kode)\s*(?:is|:)?\s*(\d{6})', r'(\d{6})\s*(?:is your|as your)', r'\b(\d{6})\b']:
        m = re.search(p, clean, re.IGNORECASE)
        if m:
            return m.group(1)
    return None

# ===================== TEMP MAIL: tempmail.lol =====================
class TempMailLol:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.email = None
        self.token = None

    def create_account(self):
        try:
            res = self.session.get(f"{TEMPMAIL_LOL_API}/generate", timeout=15)
            if res.status_code == 200:
                data = res.json()
                self.email = data["address"]
                self.token = data["token"]
                log(f"Email dibuat: {G}{self.email}{W}", "success")
                return True
            log(f"Gagal buat email: HTTP {res.status_code}", "error")
            return False
        except Exception as e:
            log(f"Error buat email: {e}", "error")
            return False

    def wait_for_otp(self, timeout=180):
        log(f"Menunggu OTP masuk (max {timeout}s)...", "info")
        start = time.time()
        while time.time() - start < timeout:
            try:
                res = self.session.get(f"{TEMPMAIL_LOL_API}/auth/{self.token}", timeout=15)
                if res.status_code == 200:
                    emails = res.json().get("email", [])
                    if emails:
                        for mail in emails:
                            body = mail.get("body", "") or mail.get("html", "") or mail.get("text", "")
                            subject = mail.get("subject", "")
                            otp = extract_otp(body) or extract_otp(subject)
                            if otp:
                                print()
                                log(f"OTP diterima: {G}{otp}{W}", "success")
                                return otp
            except:
                pass
            elapsed = int(time.time() - start)
            log(f"Cek inbox... {elapsed}s/{timeout}s", "wait")
            time.sleep(5)
        print()
        log(f"Timeout! OTP tidak diterima dalam {timeout}s", "error")
        return None

# ===================== TEMP MAIL: mail.tm =====================
class MailTM:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.email = None
        self.token = None

    def create_account(self):
        try:
            res = self.session.get(f"{MAIL_TM_API}/domains", timeout=15)
            domains = res.json().get("hydra:member", [])
            if not domains:
                log("Tidak ada domain tersedia", "error")
                return False
            domain = domains[0]["domain"]
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=14))
            self.email = f"{username}@{domain}"
            payload = {"address": self.email, "password": password}
            res = self.session.post(f"{MAIL_TM_API}/accounts", json=payload, timeout=15)
            if res.status_code == 201:
                res = self.session.post(f"{MAIL_TM_API}/token", json=payload, timeout=15)
                if res.status_code == 200:
                    self.token = res.json()["token"]
                    self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                    log(f"Email dibuat: {G}{self.email}{W}", "success")
                    return True
            log(f"Gagal buat email: HTTP {res.status_code}", "error")
            return False
        except Exception as e:
            log(f"Error buat email: {e}", "error")
            return False

    def wait_for_otp(self, timeout=180):
        log(f"Menunggu OTP masuk (max {timeout}s)...", "info")
        start = time.time()
        while time.time() - start < timeout:
            try:
                res = self.session.get(f"{MAIL_TM_API}/messages", timeout=15)
                if res.status_code == 200:
                    messages = res.json().get("hydra:member", [])
                    if messages:
                        msg_id = messages[0]["id"]
                        res = self.session.get(f"{MAIL_TM_API}/messages/{msg_id}", timeout=15)
                        if res.status_code == 200:
                            data = res.json()
                            body = data.get("text", "") or data.get("html", "")
                            subject = data.get("subject", "")
                            otp = extract_otp(body) or extract_otp(subject)
                            if otp:
                                print()
                                log(f"OTP diterima: {G}{otp}{W}", "success")
                                return otp
            except:
                pass
            elapsed = int(time.time() - start)
            log(f"Cek inbox... {elapsed}s/{timeout}s", "wait")
            time.sleep(5)
        print()
        log(f"Timeout! OTP tidak diterima dalam {timeout}s", "error")
        return None

# ===================== ALLSCALE BOT =====================
class AllscaleBot:
    def __init__(self):
        self.session = requests.Session()
        self.timestamp_delta = 0
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://app.allscale.io",
            "Referer": f"https://app.allscale.io/pay/register?code={REFERER_ID}",
            "Accept-Language": "en-US,en;q=0.9",
            "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        })

    def get_timestamp(self):
        return int((time.time() * 1000 + self.timestamp_delta) / 1000)

    def update_delta(self, response):
        server_ts = response.headers.get("x-system-timestamp")
        if server_ts:
            try:
                self.timestamp_delta = int(server_ts) - int(time.time() * 1000)
            except:
                pass

    def send_otp(self, email):
        ts = self.get_timestamp()
        sig = generate_signature(ts)
        headers = {"timestamp": str(ts), "secret-key": sig}
        payload = {"email": email, "check_user_existence": False}
        
        log("Mengirim OTP...", "step")
        try:
            res = self.session.post(f"{BASE_URL}/api/public/turnkey/send_email_otp", headers=headers, json=payload, timeout=30)
            self.update_delta(res)
            if res.status_code == 200:
                log("OTP berhasil dikirim!", "success")
                return True
            err = ""
            try: err = res.json().get("errors", res.text[:200])
            except: err = res.text[:200]
            log(f"Gagal kirim OTP: HTTP {res.status_code} - {err}", "error")
            return False
        except Exception as e:
            log(f"Error kirim OTP: {e}", "error")
            return False

    def auth_otp(self, email, otp_code):
        ts = self.get_timestamp()
        sig = generate_signature(ts)
        headers = {"timestamp": str(ts), "secret-key": sig}
        payload = {"email": email, "otp_id": email, "otp_code": otp_code, "referer_id": REFERER_ID, "remember_me": False}
        
        log(f"Verifikasi OTP: {otp_code}...", "step")
        try:
            res = self.session.post(f"{BASE_URL}/api/public/turnkey/email_otp_auth", headers=headers, json=payload, timeout=30)
            self.update_delta(res)
            if res.status_code == 200:
                cookies = {c.name: c.value for c in res.cookies}
                refresh_token = cookies.get("allscale_refresh_token", "N/A")
                with open(ACCOUNTS_FILE, "a") as f:
                    f.write(f"{refresh_token}|{email}\n")
                log(f"REGISTRASI BERHASIL!", "success")
                log(f"Refresh Token: {refresh_token}", "success")
                return True
            err = ""
            try: err = res.json().get("errors", res.text[:200])
            except: err = res.text[:200]
            log(f"Verifikasi gagal: HTTP {res.status_code} - {err}", "error")
            return False
        except Exception as e:
            log(f"Error verifikasi: {e}", "error")
            return False

# ===================== MAIN =====================
def register_single(provider_class):
    mail = provider_class()
    if not mail.create_account():
        return False
    bot = AllscaleBot()
    if not bot.send_otp(mail.email):
        return False
    otp = mail.wait_for_otp(timeout=180)
    if not otp:
        return False
    return bot.auth_otp(mail.email, otp)

def main():
    banner()
    
    try:
        count = int(input(f"  {Y}Berapa akun yang mau dibuat?{W} "))
    except (ValueError, KeyboardInterrupt):
        count = 1
    
    print(f"""
  {C}Pilih Temp Mail Provider:{W}
    {G}1{W}. tempmail.lol {Y}(recommended){W}
    {G}2{W}. mail.tm
    {G}3{W}. Coba keduanya (fallback)
""")
    try:
        choice = int(input(f"  {Y}Pilih [1/2/3]:{W} "))
    except (ValueError, KeyboardInterrupt):
        choice = 1
    
    success_count = 0
    fail_count = 0
    
    for i in range(count):
        divider(i + 1, count)
        
        result = False
        if choice == 1:
            result = register_single(TempMailLol)
        elif choice == 2:
            result = register_single(MailTM)
        elif choice == 3:
            result = register_single(TempMailLol)
            if not result:
                log("Coba fallback: mail.tm...", "info")
                result = register_single(MailTM)
        
        if result:
            success_count += 1
        else:
            fail_count += 1
        
        if i < count - 1:
            delay = random.randint(5, 15)
            log(f"Jeda {delay}s sebelum akun berikutnya...", "wait")
            time.sleep(delay)
            print()
    
    print(f"""
{C}  =============================================={W}
{G}     HASIL REGISTRASI{W}
{C}  ----------------------------------------------{W}
     Berhasil : {G}{success_count}{W}
     Gagal    : {R}{fail_count}{W}
     Total    : {Y}{count}{W}
     Tersimpan: {G}{ACCOUNTS_FILE}{W}
{C}  =============================================={W}
""")

if __name__ == "__main__":
    main()


