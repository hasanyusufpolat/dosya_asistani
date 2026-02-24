"""
PROFESYONEL PAKET SATIN ALMA SİSTEMİ
Database entegrasyonlu - Kullanıcı kayıt ve hak yönetimi
Gelişmiş hata yönetimi ve loglama ile
"""

import datetime
import sqlite3
import traceback
import logging
from typing import Optional, Dict, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Kendi modülümüz
import database as db

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('payments.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========== PAKET TANIMLARI (GÜNCEL FİYATLAR) ==========
PACKAGES = {
    '5': {
        'id': '5',
        'name': 'BAŞLANGIÇ PAKETİ',
        'full_name': '🌟 BAŞLANGIÇ PAKETİ',
        'rights': 5,
        'original_price': 300,
        'price': 200,
        'emoji': '🌟',
        'description': '• 5 Dosya Dönüştürme Hakkı\n• Tüm formatlar desteklenir\n• 7/24 destek\n• Hızlı dönüşüm',
        'features': [
            '✅ PDF → Word, Excel',
            '✅ Word → PDF, Excel, PowerPoint',
            '✅ Excel → PDF, Word, PowerPoint',
            '✅ PowerPoint → PDF, Word',
            '✅ Görsel → PDF, Word (OCR)'
        ],
        'popular': False,
        'discount': 33  # %33 indirim
    },
    '15': {
        'id': '15',
        'name': 'GÜMÜŞ PAKET',
        'full_name': '🚀 GÜMÜŞ PAKET',
        'rights': 15,
        'original_price': 750,
        'price': 500,
        'emoji': '🚀',
        'description': '• 15 Dosya Dönüştürme Hakkı\n• Tüm formatlar desteklenir\n• Öncelikli destek\n• Toplu dönüşüm avantajı',
        'features': [
            '✅ Tüm dönüşüm formatları',
            '✅ 15 dosya dönüştürme hakkı',
            '✅ Öncelikli işlem sırası',
            '✅ E-posta desteği'
        ],
        'popular': False,
        'discount': 33
    },
    '30': {
        'id': '30',
        'name': 'ELMAS PAKET',
        'full_name': '💎 ELMAS PAKET',
        'rights': 30,
        'original_price': 1400,
        'price': 1000,
        'emoji': '💎',
        'description': '• 30 Dosya Dönüştürme Hakkı\n• Tüm formatlar desteklenir\n• Öncelikli destek\n• En popüler paket',
        'features': [
            '✅ Tüm dönüşüm formatları',
            '✅ 30 dosya dönüştürme hakkı',
            '✅ Öncelikli işlem sırası',
            '✅ Acil destek hattı',
            '✅ %30 daha avantajlı'
        ],
        'popular': True,
        'discount': 29
    },
    '50': {
        'id': '50',
        'name': 'PLATİN PAKET',
        'full_name': '👑 PLATİN PAKET',
        'rights': 50,
        'original_price': 2000,
        'price': 1500,
        'emoji': '👑',
        'description': '• 50 Dosya Dönüştürme Hakkı\n• Tüm formatlar desteklenir\n• VIP destek\n• En ekonomik paket',
        'features': [
            '✅ Tüm dönüşüm formatları',
            '✅ 50 dosya dönüştürme hakkı',
            '✅ VIP destek hattı',
            '✅ Özel indirimler',
            '✅ %25 daha avantajlı'
        ],
        'popular': False,
        'discount': 25
    },
    '75': {
        'id': '75',
        'name': 'ELİT PAKET',
        'full_name': '🏆 ELİT PAKET (En Çok Tercih Edilen)',
        'rights': 75,
        'original_price': 3000,
        'price': 2250,
        'emoji': '🏆',
        'description': '• 75 Dosya Dönüştürme Hakkı\n• Tüm formatlar desteklenir\n• 7/24 VIP destek\n• Maksimum avantaj',
        'features': [
            '✅ Tüm dönüşüm formatları',
            '✅ 75 dosya dönüştürme hakkı',
            '✅ 7/24 VIP destek',
            '✅ Özel menajer desteği',
            '✅ %25 daha avantajlı'
        ],
        'popular': True,
        'discount': 25
    }
}

# ========== BANKA BİLGİLERİ ==========
BANK_ACCOUNTS = {
    'ziraat': {
        'bank': '🏦 ZİRAAT BANKASI',
        'name': 'YUSUF POLAT',
        'iban': 'TR92 0001 0004 6796 3186 2350 01',
        'branch': 'Şanlıurfa Şubesi'
    }
}

# ========== YARDIMCI FONKSİYONLAR ==========
def get_user_remaining_rights_direct(user_id: int) -> int:
    """Kullanıcının kalan hakkını doğrudan veritabanından al"""
    try:
        conn = sqlite3.connect('database/bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT remaining_rights FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    except Exception as e:
        logger.error(f"❌ Hak sorgulanırken hata: {e}")
        return 0

def repair_database_if_needed() -> bool:
    """Veritabanında eksik sütunları kontrol et ve ekle"""
    try:
        conn = sqlite3.connect('database/bot.db')
        cursor = conn.cursor()
        
        # Mevcut sütunları kontrol et
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        required_columns = [
            'successful_conversions', 
            'failed_conversions', 
            'total_conversions',
            'last_activity',
            'updated_at'
        ]
        
        for column in required_columns:
            if column not in columns:
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {column} INTEGER DEFAULT 0")
                    logger.info(f"✅ '{column}' sütunu eklendi")
                except:
                    pass
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Veritabanı tamiri sırasında hata: {e}")
        return False

# ========== BEKLEYEN ÖDEMELER TABLOSU ==========
def init_payments_table():
    """Ödeme tablosunu oluştur"""
    conn = sqlite3.connect('database/bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            package_id TEXT,
            package_name TEXT,
            package_rights INTEGER,
            amount REAL,
            status TEXT DEFAULT 'pending',
            requested_at TEXT,
            approved_at TEXT,
            approved_by INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS completed_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            package_id TEXT,
            package_name TEXT,
            package_rights INTEGER,
            rights_added INTEGER,
            amount REAL,
            payment_date TEXT,
            approved_by INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("✅ Ödeme tabloları oluşturuldu.")

# ========== PAKET MENÜSÜ ==========
async def show_packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ana paket menüsünü göster"""
    
    keyboard = []
    for package_id, package in PACKAGES.items():
        popular_tag = " 🔥 POPÜLER" if package.get('popular') else ""
        button_text = f"{package['emoji']} {package['name']}{popular_tag}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"package_{package_id}")])
    
    keyboard.append([InlineKeyboardButton("◀️ Ana Menüye Dön", callback_data="back_to_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = """🎁 **PAKET SATIN ALMA**

━━━━━━━━━━━━━━━━━━━━━
📦 **SİZE ÖZEL İNDİRİMLİ PAKETLER**

Aşağıdan size uygun paketi seçin:

• 🌟 **Başlangıç:** 5 Hak → 200 TL (300 TL yerine)
• 🚀 **Gümüş:** 15 Hak → 500 TL (750 TL yerine)
• 💎 **Elmas:** 30 Hak → 1000 TL (1400 TL yerine) 🔥
• 👑 **Platin:** 50 Hak → 1500 TL (2000 TL yerine)
• 🏆 **Elit:** 75 Hak → 2250 TL (3000 TL yerine) 🔥

━━━━━━━━━━━━━━━━━━━━━
👇 **Detaylı bilgi için paket seçin:**"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def show_package_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Seçilen paketin detaylarını göster"""
    query = update.callback_query
    await query.answer()
    
    package_id = query.data.replace('package_', '')
    package = PACKAGES.get(package_id)
    
    if not package:
        await query.edit_message_text("❌ Paket bulunamadı!")
        return
    
    discount = package.get('discount', 0)
    savings = package['original_price'] - package['price']
    popular_tag = " 🔥 POPÜLER" if package.get('popular') else ""
    features_text = "\n".join([f"  {f}" for f in package['features']])
    
    message = f"""📦 **{package['emoji']} {package['full_name']}{popular_tag}**

━━━━━━━━━━━━━━━━━━━━━
📊 **PAKET İÇERİĞİ**
• 📁 **{package['rights']} Dosya Dönüştürme Hakkı**
• 🔄 Tüm formatlar desteklenir
• ⚡ Anında dönüşüm
• 🎯 7/24 destek

━━━━━━━━━━━━━━━━━━━━━
💰 **FİYAT BİLGİSİ**
• ~~{package['original_price']:,} TL~~ → **{package['price']:,} TL**
• 💸 **%{discount} İndirim!** (Kazancın: {savings:,} TL)
• 💎 Dosya başı sadece **{package['price']/package['rights']:.1f} TL**

━━━━━━━━━━━━━━━━━━━━━
✨ **ÖZELLİKLER**
{features_text}

━━━━━━━━━━━━━━━━━━━━━
📌 **NASIL SATIN ALIRIM?**
1️⃣ "SATIN AL" butonuna tıkla
2️⃣ Banka bilgilerini gör
3️⃣ Havale/EFT yap
4️⃣ "ÖDEMEYİ ONAYLA" butonuna tıkla
5️⃣ Onaydan sonra hakların aktif

⏱️ **Onay süresi:** 5-10 dakika
📞 **Destek:** @Yusozone"""

    keyboard = [
        [InlineKeyboardButton("💳 SATIN AL", callback_data=f"buy_{package_id}")],
        [InlineKeyboardButton("◀️ Paketlere Dön", callback_data="show_packages")],
        [InlineKeyboardButton("❌ İptal", callback_data="cancel_payment")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def start_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ödeme işlemini başlat"""
    query = update.callback_query
    await query.answer()
    
    package_id = query.data.replace('buy_', '')
    package = PACKAGES.get(package_id)
    
    context.user_data['pending_package'] = package_id
    bank = BANK_ACCOUNTS['ziraat']
    
    message = f"""💳 **ÖDEME BİLGİLERİ**

━━━━━━━━━━━━━━━━━━━━━
📦 **SEÇİLEN PAKET:**
{package['emoji']} {package['full_name']}
📁 {package['rights']} Dosya Hakkı

━━━━━━━━━━━━━━━━━━━━━
💰 **TUTAR:**
~~{package['original_price']:,} TL~~ → **{package['price']:,} TL**
💸 Kazancın: {package['original_price'] - package['price']:,} TL

━━━━━━━━━━━━━━━━━━━━━
🏦 **BANKA HESABIMIZ**

{bank['bank']} - {bank.get('branch', '')}
• 👤 **Alıcı Adı:** `{bank['name']}`
• 🔢 **IBAN:** `{bank['iban']}`

━━━━━━━━━━━━━━━━━━━━━
📌 **ÖDEME TALİMATI**

1️⃣ **{package['price']:,} TL** gönder
2️⃣ Açıklamaya **@{update.effective_user.username or 'kullaniciadi'}** yaz
3️⃣ "✅ ÖDEMEYİ ONAYLA" butonuna tıkla
4️⃣ Onayı bekle

⚠️ **Açıklama kısmına kullanıcı adını yazmayı UNUTMA!**

⏱️ **Onay süresi:** 5-10 dakika
📞 **Sorun olursa:** @Yusozone"""

    keyboard = [
        [InlineKeyboardButton("✅ ÖDEMEYİ ONAYLA", callback_data=f"confirm_payment_{package_id}")],
        [InlineKeyboardButton("◀️ Geri", callback_data=f"package_{package_id}")],
        [InlineKeyboardButton("❌ İptal", callback_data="cancel_payment")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ödeme yapıldığını onayla"""
    query = update.callback_query
    await query.answer()
    
    package_id = query.data.replace('confirm_payment_', '')
    package = PACKAGES.get(package_id)
    
    user = update.effective_user
    user_id = user.id
    username = user.username or "kullanici_adi_yok"
    first_name = user.first_name or ""
    
    # Kullanıcıyı veritabanına kaydet (varsa güncelle, yoksa ekle)
    db.register_user(user)
    
    # Aktivite kaydı
    db.log_user_activity(user_id, 'payment_request', f'{package["full_name"]} için ödeme talebi')
    
    # Bekleyen ödemeyi kaydet
    conn = sqlite3.connect('database/bot.db')
    cursor = conn.cursor()
    
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        INSERT INTO pending_payments 
        (user_id, username, first_name, package_id, package_name, package_rights, amount, requested_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, package_id, package['full_name'], package['rights'], package['price'], now))
    
    payment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    logger.info(f"💰 Yeni ödeme talebi: {username} - {package['full_name']} - {package['price']} TL")
    
    # Kullanıcıya bilgi ver
    await query.edit_message_text(
        f"""✅ **ÖDEME ONAYI GÖNDERİLDİ!**

━━━━━━━━━━━━━━━━━━━━━
📦 **Paket:** {package['emoji']} {package['full_name']}
💰 **Tutar:** {package['price']:,} TL
📁 **Hak:** {package['rights']} Dosya
👤 **Kullanıcı:** @{username}

━━━━━━━━━━━━━━━━━━━━━
⏳ **Ödemeniz kontrol ediliyor...**

🔍 En kısa sürede (5-10 dk) onaylanacaktır.

📞 Onaydan sonra haklarınız aktif olacak.

💬 Sorun yaşarsanız: @Yusozone

━━━━━━━━━━━━━━━━━━━━━
📌 **İşlem ID:** `#{payment_id}`""",
        parse_mode='Markdown'
    )
    
    # ADMIN'E BİLDİR
    from config import ADMIN_ID
    
    discount = ((package['original_price'] - package['price']) / package['original_price']) * 100
    
    admin_message = f"""🚨 **YENİ ÖDEME ONAY BEKLİYOR!**

━━━━━━━━━━━━━━━━━━━━━
👤 **KULLANICI BİLGİLERİ**
• 🆔 ID: `{user_id}`
• 👤 Kullanıcı: @{username}
• 📝 İsim: {first_name}

━━━━━━━━━━━━━━━━━━━━━
📦 **PAKET BİLGİLERİ**
• Paket: {package['emoji']} {package['full_name']}
• Hak: {package['rights']} Dosya
• Tutar: ~~{package['original_price']:,} TL~~ → **{package['price']:,} TL**
• İndirim: %{discount:.0f}
• Kazanç: {package['original_price'] - package['price']} TL

━━━━━━━━━━━━━━━━━━━━━
⏰ **Talep Zamanı:** `{now}`
🆔 **İşlem ID:** `#{payment_id}`

━━━━━━━━━━━━━━━━━━━━━
👇 **İşlem yapın:**"""
    
    keyboard = [
        [
            InlineKeyboardButton("✅ ONAYLA", callback_data=f"approve_payment_{payment_id}"),
            InlineKeyboardButton("❌ REDDET", callback_data=f"reject_payment_{payment_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Admin'e mesaj gönder
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        logger.info(f"✅ Admin bildirimi gönderildi: {ADMIN_ID}")
    except Exception as e:
        logger.error(f"❌ Admin bildirimi gönderilemedi: {e}")
    
    # Admin'e sesli bildirim
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text="🔔 **YENİ ÖDEME!** 🔔",
            parse_mode='Markdown'
        )
    except:
        pass

async def approve_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin ödemeyi onaylar - KULLANICI OTOMATİK KAYDOLUR"""
    query = update.callback_query
    await query.answer()
    
    from config import ADMIN_ID
    
    if update.effective_user.id != ADMIN_ID:
        await query.message.reply_text("❌ Yetkisiz erişim!")
        return
    
    payment_id = int(query.data.replace('approve_payment_', ''))
    
    conn = None
    try:
        conn = sqlite3.connect('database/bot.db')
        cursor = conn.cursor()
        
        # Ödeme bilgilerini al
        cursor.execute('''
            SELECT user_id, username, first_name, package_id, package_name, package_rights, amount 
            FROM pending_payments 
            WHERE id = ? AND status = 'pending'
        ''', (payment_id,))
        
        payment = cursor.fetchone()
        
        if not payment:
            await query.edit_message_text("❌ Ödeme kaydı bulunamadı veya daha önce işlem görmüş!")
            if conn:
                conn.close()
            return
        
        user_id, username, first_name, package_id, package_name, rights, amount = payment
        package = PACKAGES.get(package_id)
        
        if not package:
            await query.edit_message_text("❌ Paket bulunamadı!")
            if conn:
                conn.close()
            return
        
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Kullanıcıyı kontrol et, yoksa oluştur
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user_exists = cursor.fetchone()
        
        # YENİ HAK MİKTARINI HESAPLA
        if not user_exists:
            # YENİ KULLANICI - TÜM SÜTUNLAR EKLENDİ
            cursor.execute('''
                INSERT INTO users 
                (user_id, username, first_name, remaining_rights, package_type, 
                 total_conversions, successful_conversions, failed_conversions, 
                 last_activity, registered_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 0, 0, 0, ?, ?, ?)
            ''', (user_id, username, first_name, rights, package_id, now, now, now))
            logger.info(f"✅ YENİ KULLANICI OLUŞTURULDU: {user_id} - {username}")
            new_rights = rights
        else:
            # MEVCUT KULLANICI - MEVCUT HAKLARI AL
            cursor.execute('SELECT remaining_rights FROM users WHERE user_id = ?', (user_id,))
            current_rights = cursor.fetchone()[0]
            
            # YENİ HAK = ESKİ HAK + EKLENEN HAK
            new_rights = current_rights + rights
            
            # Kullanıcının haklarını güncelle
            cursor.execute('''
                UPDATE users SET 
                    remaining_rights = ?,
                    package_type = ?,
                    last_activity = ?,
                    updated_at = ?
                WHERE user_id = ?
            ''', (new_rights, package_id, now, now, user_id))
            
            logger.info(f"✅ KULLANICI HAKLARI GÜNCELLENDİ: {user_id} {current_rights} → {new_rights} (+{rights})")
        
        # Ödeme durumunu güncelle
        cursor.execute('''
            UPDATE pending_payments SET 
                status = 'approved',
                approved_at = ?,
                approved_by = ?
            WHERE id = ?
        ''', (now, ADMIN_ID, payment_id))
        
        # Tamamlanmış ödemelere ekle
        cursor.execute('''
            INSERT INTO completed_payments 
            (user_id, username, first_name, package_id, package_name, package_rights, rights_added, amount, payment_date, approved_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, package_id, package_name, rights, rights, amount, now, ADMIN_ID))
        
        # Değişiklikleri KAYDET (COMMIT)
        conn.commit()
        
        # Kullanıcıya bildir - BAŞARILI MESAJI (GERÇEK HAK MİKTARI İLE)
        await context.bot.send_message(
            chat_id=user_id,
            text=f"""✅ **ÖDEMENİZ ONAYLANDI!** 🎉

━━━━━━━━━━━━━━━━━━━━━
🎉 **Tebrikler! Paketiniz aktif edildi.**

📦 **Paket:** {package['emoji']} {package['full_name']}
📁 **Eklenen Hak:** +{rights} Dosya
💰 **Ödenen Tutar:** {amount:,} TL
💸 **Kazancınız:** {package['original_price'] - amount:,} TL

━━━━━━━━━━━━━━━━━━━━━
🔁 **GÜNCEL DURUM**
• Kalan Hakkınız: **{new_rights}** Dosya

━━━━━━━━━━━━━━━━━━━━━
🚀 Hemen dosya dönüştürmeye başlayabilirsiniz!""",
            parse_mode='Markdown'
        )
        
        # Kullanıcıya yeni butonlu mesaj gönder (Sohbete Başla butonu)
        keyboard = [[InlineKeyboardButton("📁 DOSYA YÜKLE", callback_data="dosya_yukle")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=user_id,
            text="📂 **Dosya göndermek için aşağıdaki butona tıklayın:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Aktivite kaydı
        db.log_user_activity(user_id, 'payment_approved', f'{package_name} paketi onaylandı')
        
        # Admin'e onay mesajı
        await query.edit_message_text(
            f"✅ **ÖDEME ONAYLANDI!**\n\n"
            f"👤 Kullanıcı: @{username}\n"
            f"📦 Paket: {package['emoji']} {package['name']}\n"
            f"📁 +{rights} hak eklendi.\n"
            f"💰 Tutar: {amount:,} TL\n"
            f"🆔 İşlem ID: #{payment_id}\n"
            f"📊 Güncel Hak: {new_rights} Dosya\n\n"
            f"📝 Kullanıcı kaydı: {'Yeni' if not user_exists else 'Mevcut'}",
            parse_mode='Markdown'
        )
        
        logger.info(f"✅ Ödeme onaylandı: {payment_id} - {username} - {new_rights} hak")
        
    except sqlite3.OperationalError as e:
        error_msg = str(e)
        logger.error(f"❌ Veritabanı hatası: {error_msg}")
        
        if "no column named" in error_msg:
            # Veritabanını acil tamir et
            await query.edit_message_text("⚠️ Veritabanı güncelleniyor, lütfen 5 saniye sonra tekrar dene...")
            
            if repair_database_if_needed():
                await query.edit_message_text("✅ Veritabanı güncellendi, şimdi tekrar dene.")
            else:
                await query.edit_message_text("❌ Veritabanı güncellenemedi, lütfen yetkiliyle iletişime geçin.")
        else:
            if conn:
                conn.rollback()
            await query.edit_message_text(f"❌ Hata oluştu: {error_msg[:100]}")
    except Exception as e:
        logger.error(f"❌ Ödeme onaylanırken hata: {e}")
        traceback.print_exc()
        if conn:
            conn.rollback()
        await query.edit_message_text(f"❌ Hata oluştu: {str(e)[:100]}")
    finally:
        if conn:
            conn.close()

async def reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin ödemeyi reddeder"""
    query = update.callback_query
    await query.answer()
    
    from config import ADMIN_ID
    
    if update.effective_user.id != ADMIN_ID:
        await query.message.reply_text("❌ Yetkisiz erişim!")
        return
    
    payment_id = int(query.data.replace('reject_payment_', ''))
    
    conn = None
    try:
        conn = sqlite3.connect('database/bot.db')
        cursor = conn.cursor()
        
        # Ödeme bilgilerini al
        cursor.execute('''
            SELECT user_id, username, package_name, amount FROM pending_payments 
            WHERE id = ? AND status = 'pending'
        ''', (payment_id,))
        
        payment = cursor.fetchone()
        
        if not payment:
            await query.edit_message_text("❌ Ödeme kaydı bulunamadı veya daha önce işlem görmüş!")
            if conn:
                conn.close()
            return
        
        user_id, username, package_name, amount = payment
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Ödeme durumunu güncelle
        cursor.execute('''
            UPDATE pending_payments SET 
                status = 'rejected',
                approved_at = ?,
                approved_by = ?
            WHERE id = ?
        ''', (now, ADMIN_ID, payment_id))
        
        conn.commit()
        
        logger.info(f"❌ Ödeme reddedildi: {payment_id} - {username}")
        
        # Kullanıcıya bildir
        await context.bot.send_message(
            chat_id=user_id,
            text="""❌ **ÖDEMENİZ ONAYLANMADI!**

━━━━━━━━━━━━━━━━━━━━━
Maalesef ödemeniz onaylanamadı.

📌 **OLASI NEDENLER:**
• Ödeme henüz hesabımıza ulaşmamış
• Tutar eksik yatırılmış
• Açıklamaya kullanıcı adı yazılmamış
• IBAN yanlış girilmiş

━━━━━━━━━━━━━━━━━━━━━
📞 **DESTEK İÇİN:** @Yusozone

🔄 Yeniden denemek için /start yazabilirsiniz.""",
            parse_mode='Markdown'
        )
        
        # Kullanıcıya yeni butonlu mesaj gönder (Sohbete Başla butonu)
        keyboard = [[InlineKeyboardButton("📁 TEKRAR DENE", callback_data="show_packages")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=user_id,
            text="📂 **Tekrar denemek için aşağıdaki butona tıklayın:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Aktivite kaydı
        db.log_user_activity(user_id, 'payment_rejected', f'{package_name} paketi reddedildi')
        
        await query.edit_message_text(
            f"❌ **ÖDEME REDDEDİLDİ!**\n\n"
            f"👤 Kullanıcı: @{username}\n"
            f"📦 Paket: {package_name}\n"
            f"💰 Tutar: {amount:,} TL\n"
            f"🆔 İşlem ID: #{payment_id}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"❌ Ödeme reddedilirken hata: {e}")
        traceback.print_exc()
        if conn:
            conn.rollback()
        await query.edit_message_text(f"❌ Hata oluştu: {str(e)[:100]}")
    finally:
        if conn:
            conn.close()

async def cancel_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ödeme işlemini iptal et"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("👋 Merhaba", callback_data="merhaba")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "❌ **İşlem iptal edildi.**\n\n"
        "Ana menüye döndünüz. Tekrar denemek için butona tıklayın.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ana menüye dön"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("👋 Merhaba", callback_data="merhaba")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🤖 **Dosya Asistanı'na hoş geldiniz!**\n\n"
        "Başlamak için butona tıklayın.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )