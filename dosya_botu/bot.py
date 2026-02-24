# bot.py
"""
ANA BOT DOSYASI - PROFESYONEL VERSİYON
Gelişmiş hata yönetimi, loglama ve optimizasyon
Tüm modüller entegre edilmiştir
"""
        
import os
import datetime
import sqlite3
import logging
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Kendi modüllerimiz
from config import *
import database as db
import converters
import utils
from payments import (
    show_packages, show_package_detail, start_payment,
    confirm_payment, approve_payment, reject_payment, 
    cancel_payment, back_to_main, init_payments_table
)
import datetime
import time
import os
import sys

# ========== ZAMAN KONTROLÜ ==========
def check_business_hours():
    """Sabah 8 - akşam 8 arası çalışır"""
    now = datetime.datetime.now()
    hour = now.hour
    # Sabah 8 (8) ile akşam 8 (20) arası
    if 8 <= hour < 20:
        return True
    else:
        return False

def wait_until_morning():
    """Sabah 8'e kadar bekle"""
    now = datetime.datetime.now()
    target = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now.hour >= 20:  # Akşam 8'den sonraysa
        target = target + datetime.timedelta(days=1)  # Yarın sabaha bekle
    
    wait_seconds = (target - now).total_seconds()
    print(f"😴 Bot şu anda çalışma saatleri dışında. Sabah 8'de başlamak için {wait_seconds/3600:.1f} saat bekleyecek.")
    time.sleep(wait_seconds)

# Ana çalışma döngüsü
while True:
    if check_business_hours():
        print("✅ Çalışma saatleri içindeyiz. Bot başlatılıyor...")
        break  # Botu başlat
    else:
        wait_until_morning()
# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========== YARDIMCI FONKSİYONLAR ==========
def get_user_rights_direct(user_id: int) -> int:
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

# ========== BOT KOMUTLARI ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komutu - Kullanıcıyı karşılar"""
    user = update.effective_user
    db.register_user(user)
    
    # Kalan hak kontrolü - doğrudan veritabanından
    remaining = get_user_rights_direct(user.id)
    
    keyboard = [[InlineKeyboardButton("👋 Merhaba", callback_data="merhaba")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = f"""🤖 **Dosya Asistanı'na hoş geldiniz!** 

━━━━━━━━━━━━━━━━━━━━━
👤 **Kullanıcı:** {user.first_name}
📦 **Kalan Hakkınız:** {remaining} Dosya

📁 **Desteklenen Formatlar:**
• PDF • Word • Excel • PowerPoint • Görsel

━━━━━━━━━━━━━━━━━━━━━
Başlamak için butona tıklayın."""
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    logger.info(f"✅ Kullanıcı girişi: {user.id} - {user.first_name} - Kalan hak: {remaining}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buton tıklamalarını yönet"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "merhaba":
        keyboard = [
            [InlineKeyboardButton("📎 Dosya Yükle", callback_data="dosya_yukle")],
            [InlineKeyboardButton("💳 Paket Satın Al", callback_data="show_packages")],
            [InlineKeyboardButton("📊 Kalan Haklarım", callback_data="check_rights")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="📂 **Dosya Asistanı hazır**\n\nNe yapmak istersiniz?\n\n"
                 "📎 **Dosya Yükle** - Dönüşüm yapmak için\n"
                 "💳 **Paket Satın Al** - Yeni paket almak için\n"
                 "📊 **Kalan Haklarım** - Hak durumunuzu görmek için\n\n"
                 "Desteklenen dosya türleri:\n"
                 "• PDF (`.pdf`)\n"
                 "• Word (`.doc`, `.docx`)\n"
                 "• Excel (`.xls`, `.xlsx`)\n"
                 "• PowerPoint (`.ppt`, `.pptx`)\n"
                 "• Görsel (`.png`, `.jpg`, `.jpeg`)",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        logger.info(f"📋 Ana menü gösterildi: {user_id}")
    
    elif query.data == "dosya_yukle":
        await query.message.reply_text(
            "📎 **Dosya gönderme butonu**\n\n"
            "Lütfen aşağıdaki 📎 simgesine tıklayarak dosyanızı seçin ve gönderin."
        )
    
    elif query.data == "check_rights":
        remaining = get_user_rights_direct(user_id)
        stats = db.get_user_stats(user_id)
        
        if stats:
            message = f"""📊 **HAK DURUMUNUZ**

━━━━━━━━━━━━━━━━━━━━━
📦 **Kalan Hak:** `{remaining}` Dosya
✅ **Başarılı İşlem:** `{stats['success']}`
❌ **Başarısız İşlem:** `{stats['failed']}`
📈 **Toplam İşlem:** `{stats['total']}`
📅 **Bugünkü İşlem:** `{stats.get('today', 0)}`
📊 **Haftalık İşlem:** `{stats.get('weekly', 0)}`

━━━━━━━━━━━━━━━━━━━━━
💡 Yeni paket satın almak için butona tıklayın."""
            
            keyboard = [[InlineKeyboardButton("💳 Paket Satın Al", callback_data="show_packages")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await query.message.reply_text("❌ Bilgilerinize ulaşılamadı.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dosya gönderildiğinde çalışır"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "isimsiz"
    
    # Hak kontrolü - doğrudan veritabanından
    remaining = get_user_rights_direct(user_id)
    logger.info(f"📥 Dosya yükleme: {username} - Kalan hak: {remaining}")
    
    if remaining <= 0:
        # Paket satın almak ister misiniz? sorusu
        keyboard = [
            [InlineKeyboardButton("✅ Evet, Paket Satın Al", callback_data="show_packages")],
            [InlineKeyboardButton("❌ Hayır, Teşekkürler", callback_data="merhaba")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ **PAKET HAKKINIZ TÜKENMİŞTİR!**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "📦 Dönüştürme işlemine devam etmek için yeni bir paket satın almanız gerekiyor.\n\n"
            "🎁 **SİZE ÖZEL İNDİRİMLİ PAKETLER:**\n"
            "• 🌟 Başlangıç Paketi: 5 Hak → 200 TL (300 TL)\n"
            "• 🚀 Gümüş Paket: 15 Hak → 500 TL (750 TL)\n"
            "• 💎 Elmas Paket: 30 Hak → 1000 TL (1400 TL) 🔥\n"
            "• 👑 Platin Paket: 50 Hak → 1500 TL (2000 TL)\n"
            "• 🏆 Elit Paket: 75 Hak → 2250 TL (3000 TL) 🔥\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "🔽 **Paket satın almak ister misiniz?**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # Dosya bilgilerini al
    document = update.message.document
    file_name = document.file_name
    file_size = document.file_size
    
    # Dosya türünü belirle
    file_ext = os.path.splitext(file_name)[1].lower()
    
    if file_ext not in SUPPORTED_FORMATS:
        format_list = "\n".join([f"• {fmt}" for fmt in SUPPORTED_FORMATS.values()])
        await update.message.reply_text(
            f"❌ **Desteklenmeyen dosya türü!**\n\n"
            f"Lütfen şu formatlardan birini gönderin:\n{format_list}"
        )
        return
    
    file_type = SUPPORTED_FORMATS[file_ext]
    
    # temp klasörü kontrolü
    if not os.path.exists('temp'):
        os.makedirs('temp')
        logger.info("📁 temp klasörü oluşturuldu")
    
    # Dosyayı indir
    try:
        await update.message.reply_text(f"📥 **Dosya indiriliyor...**\nDosya: `{file_name}`")
        
        file = await context.bot.get_file(document.file_id)
        safe_name = utils.safe_filename(file_name)
        file_path = f"temp/{user_id}_{safe_name}"
        await file.download_to_drive(file_path)
        
        # Dosya boyutu kontrolü
        if file_size > MAX_FILE_SIZE:
            await update.message.reply_text(f"⚠️ **Dosya boyutu çok büyük!**\nMaksimum {MAX_FILE_SIZE/(1024*1024)} MB dosya gönderebilirsiniz.")
            os.remove(file_path)
            return
        
        await update.message.reply_text(f"✅ Dosya başarıyla indirildi.\nBoyut: `{utils.format_size(file_size)}`")
        logger.info(f"✅ Dosya indirildi: {file_name} - {utils.format_size(file_size)}")
        
    except Exception as e:
        logger.error(f"❌ Dosya indirilirken hata: {e}")
        await update.message.reply_text("❌ **Dosya indirilirken bir hata oluştu.**\nLütfen tekrar deneyin.")
        return
    
    # Dosya bilgisini kaydet
    context.user_data['current_file'] = file_path
    context.user_data['file_type'] = file_type
    context.user_data['file_name'] = file_name
    context.user_data['file_size'] = file_size
    
    # Dönüşüm seçeneklerini göster
    await show_conversion_options(update, context, file_type)

async def show_conversion_options(update: Update, context: ContextTypes.DEFAULT_TYPE, file_type):
    """Dosya türüne göre buton menüsü göster"""
    
    options = CONVERSION_MAP.get(file_type, ['PDF'])
    
    keyboard = []
    for opt in options:
        display_name = DISPLAY_NAMES.get(opt, opt)
        callback_data = f"convert|{opt}"
        keyboard.append([InlineKeyboardButton(display_name, callback_data=callback_data)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📄 **Dosya Algılandı**\n\n"
        f"📁 Dosya türü: **{DISPLAY_NAMES.get(file_type, file_type)}**\n"
        f"🔄 Dönüştürülebilecek formatlar:\n\n"
        f"Lütfen dönüştürmek istediğiniz formatı seçin:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def convert_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dönüştürme butonuna basıldığında"""
    query = update.callback_query
    await query.answer()
    
    if not query.data.startswith('convert'):
        return
    
    target = query.data.split('|')[1]
    
    # Dosya bilgilerini al
    file_path = context.user_data.get('current_file')
    file_name = context.user_data.get('file_name')
    file_type = context.user_data.get('file_type')
    file_size = context.user_data.get('file_size', 0)
    user_id = update.effective_user.id
    
    if not file_path or not os.path.exists(file_path):
        await query.edit_message_text("❌ **Dosya bulunamadı!**\nLütfen dosyayı tekrar yükleyin.")
        return
    
    # Dönüşüm başlangıç zamanı
    start_time = datetime.datetime.now()
    
    # Bekleme mesajı
    await query.edit_message_text(
        f"⏳ **Dosya dönüştürülüyor...**\n\n"
        f"📁 Kaynak: `{file_name}`\n"
        f"🔄 Hedef: **{DISPLAY_NAMES.get(target, target)}**\n\n"
        f"Bu işlem birkaç saniye sürebilir, lütfen bekleyin..."
    )
    
    # Çıktı dosyası adını oluştur
    base_name = os.path.splitext(file_name)[0]
    output_ext = EXTENSION_MAP.get(target, '.pdf')
    safe_name = utils.safe_filename(f"{user_id}_{base_name}_converted{output_ext}")
    output_path = f"temp/{safe_name}"
    
    # Dönüştürme işlemini yap
    success, error = await converters.convert_file(file_path, output_path, file_type, target)
    
    # İşlem süresini hesapla
    end_time = datetime.datetime.now()
    processing_time = (end_time - start_time).total_seconds()
    
    if success and os.path.exists(output_path):
        # Kullanıcıya dönüştürülmüş dosyayı gönder
        with open(output_path, 'rb') as f:
            await query.message.reply_document(
                document=f,
                filename=f"{base_name}_converted{output_ext}",
                caption=f"✅ **Dönüştürme tamamlandı!**"
            )
        
        # Hakkı azalt (BAŞARILI işlem)
        db.decrease_rights(user_id)
        
        # Dönüşüm kaydını ekle
        db.save_conversion_record(
            user_id=user_id,
            file_name=file_name,
            file_size=file_size,
            source_format=file_type,
            target_format=target,
            status='success',
            processing_time=processing_time
        )
        
        # Yeni hak miktarını al
        new_remaining = get_user_rights_direct(user_id)
        
        # Detaylı istatistikleri göster
        stats = db.get_user_stats(user_id)
        if stats:
            user_data = {
                'used': stats['success'],
                'remaining': new_remaining
            }
            detailed_stats = utils.create_detailed_stats(user_data, stats, processing_time)
            await query.message.reply_text(detailed_stats, parse_mode='Markdown')
        
        logger.info(f"✅ Dönüşüm başarılı: {user_id} - {file_type} -> {target} - Kalan hak: {new_remaining}")
        
        # Geçici dosyaları temizle
        utils.clean_temp_files(user_id, file_path, output_path)
        
    else:
        # Başarısız dönüşüm (HAK GİTMEZ)
        db.increase_failed_count(user_id)
        
        # Başarısız kaydı ekle
        db.save_conversion_record(
            user_id=user_id,
            file_name=file_name,
            file_size=file_size,
            source_format=file_type,
            target_format=target,
            status='failed',
            processing_time=processing_time,
            error_message=error
        )
        
        error_msg = error if error else "Bilinmeyen hata"
        await query.message.reply_text(
            f"❌ **Dönüştürme başarısız!**\n\n"
            f"📁 Dosya: `{file_name}`\n"
            f"🔄 Hedef: **{DISPLAY_NAMES.get(target, target)}**\n"
            f"⚠️ Hata: `{error_msg[:200]}`\n\n"
            f"📂 **Yeni dosyanızı bekliyorum...**"
        )
        
        logger.warning(f"⚠️ Dönüşüm başarısız: {user_id} - {file_type} -> {target} - Hata: {error_msg[:100]}")
        
        # Geçici dosyayı temizle
        utils.clean_temp_files(user_id, file_path)

# ========== ADMIN KOMUTLARI ==========
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin komutu"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Bu komutu kullanma yetkiniz yok.")
        logger.warning(f"⚠️ Yetkisiz admin erişimi: {user_id}")
        return
    
    # Bekleyen ödeme sayısını göster
    conn = sqlite3.connect('database/bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM pending_payments WHERE status = 'pending'")
    pending_count = cursor.fetchone()[0]
    conn.close()
    
    keyboard = [
        [InlineKeyboardButton("📊 Sistem Durumu", callback_data="admin_durum")],
        [InlineKeyboardButton("👥 Toplam Kullanıcı", callback_data="admin_kullanici")],
        [InlineKeyboardButton("📈 Bugünkü Dönüşümler", callback_data="admin_bugun")],
        [InlineKeyboardButton("✅ Başarılı Dönüşümler", callback_data="admin_basarili")],
        [InlineKeyboardButton("❌ Başarısız Dönüşümler", callback_data="admin_basarisiz")],
        [InlineKeyboardButton(f"💰 Bekleyen Ödemeler ({pending_count})", callback_data="admin_pending_payments")],
        [InlineKeyboardButton("🔍 Kullanıcı Sorgula", callback_data="admin_sorgula")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👑 **Admin Paneli**\n\n"
        "Lütfen bir işlem seçin:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    logger.info(f"👑 Admin paneli açıldı: {user_id}")

async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin butonlarını yönet"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await query.message.reply_text("❌ Yetkisiz erişim!")
        return
    
    stats = db.get_admin_stats()
    
    if query.data == "admin_durum" and stats:
        await query.message.reply_text(
            f"📊 **Sistem Durumu**\n\n"
            f"👥 Toplam Kullanıcı: `{stats['total_users']}`\n"
            f"📈 Bugünkü Dönüşüm: `{stats['today_conversions']}`\n"
            f"✅ Başarılı: `{stats['success_total']}`\n"
            f"❌ Başarısız: `{stats['failed_total']}`\n"
            f"📁 Toplam Dönüşüm: `{stats['success_total'] + stats['failed_total']}`\n"
            f"📊 Toplam Başarılı: `{stats['total_success']}`\n"
            f"📊 Toplam Başarısız: `{stats['total_failed']}`\n"
            f"📊 Aktif Kullanıcılar: `{stats.get('active_users', 0)}`",
            parse_mode='Markdown'
        )
    
    elif query.data == "admin_kullanici" and stats:
        await query.message.reply_text(f"👥 **Toplam Kayıtlı Kullanıcı:** `{stats['total_users']}`", parse_mode='Markdown')
    
    elif query.data == "admin_bugun" and stats:
        await query.message.reply_text(f"📈 **Bugünkü Dönüşümler:** `{stats['today_conversions']}`", parse_mode='Markdown')
    
    elif query.data == "admin_basarili" and stats:
        await query.message.reply_text(f"✅ **Başarılı Dönüşümler:** `{stats['success_total']}`", parse_mode='Markdown')
    
    elif query.data == "admin_basarisiz" and stats:
        await query.message.reply_text(f"❌ **Başarısız Dönüşümler:** `{stats['failed_total']}`", parse_mode='Markdown')
    
    elif query.data == "admin_pending_payments":
        # Bekleyen ödemeleri göster
        conn = sqlite3.connect('database/bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, username, package_name, amount, requested_at 
            FROM pending_payments 
            WHERE status = 'pending'
            ORDER BY requested_at DESC
        ''')
        pending = cursor.fetchall()
        conn.close()
        
        if pending:
            text = "💰 **BEKLEYEN ÖDEMELER**\n\n"
            for p in pending:
                text += f"• `#{p[0]}` - @{p[1]} - {p[2]} - {p[3]} TL - {p[4][:16]}\n"
            await query.message.reply_text(text, parse_mode='Markdown')
        else:
            await query.message.reply_text("✅ **Bekleyen ödeme yok.**", parse_mode='Markdown')
    
    elif query.data == "admin_sorgula":
        await query.message.reply_text(
            "🔍 **Kullanıcı Sorgulama**\n\n"
            "Sorgulamak istediğiniz kullanıcının Telegram ID'sini gönderin.\n\n"
            "Örnek: `123456789`"
        )
        context.user_data['awaiting_user_id'] = True

async def handle_user_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı ID sorgulamasını yönet"""
    if context.user_data.get('awaiting_user_id'):
        user_id = update.message.text.strip()
        
        try:
            user_id = int(user_id)
            conn = sqlite3.connect('database/bot.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id, username, first_name, package_type, remaining_rights, 
                       successful_conversions, failed_conversions, registered_at
                FROM users WHERE user_id = ?
            ''', (user_id,))
            user = cursor.fetchone()
            
            if user:
                await update.message.reply_text(
                    f"👤 **Kullanıcı Bilgileri**\n\n"
                    f"🆔 ID: `{user[0]}`\n"
                    f"👤 Kullanıcı Adı: @{user[1] if user[1] else 'Yok'}\n"
                    f"📝 İsim: {user[2]}\n"
                    f"📦 Paket: {user[3]} Dosya\n"
                    f"🔁 Kalan Hak: {user[4]}\n"
                    f"✅ Başarılı: {user[5]}\n"
                    f"❌ Başarısız: {user[6]}\n"
                    f"📅 Kayıt: {user[7]}\n",
                    parse_mode='Markdown'
                )
                logger.info(f"🔍 Kullanıcı sorgulandı: {user_id}")
            else:
                await update.message.reply_text("❌ Kullanıcı bulunamadı.")
            
            conn.close()
            
        except ValueError:
            await update.message.reply_text("❌ Geçersiz ID formatı. Lütfen sadece rakam girin.")
        except Exception as e:
            logger.error(f"❌ Kullanıcı sorgulama hatası: {e}")
            await update.message.reply_text(f"❌ Hata: {str(e)}")
        
        context.user_data['awaiting_user_id'] = False

# ========== ANA FONKSİYON ==========
def main():
    """Botu başlat"""
    print("🚀 Dosya Asistanı Bot başlatılıyor...")
    print("=" * 60)
    
    print(f"🔑 Token: {BOT_TOKEN[:15]}...")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"📁 Modüler yapı: 6 dosya aktif")
    print(f"🔄 Dönüşüm: converters.py (GELİŞMİŞ)")
    print(f"💰 Ödeme: payments.py (TELEFONSUZ - KULLANICI ADI İLE)")
    print(f"📊 Loglama: bot.log, payments.log, database.log")
    
    # Veritabanını oluştur
    try:
        db.init_database()
        init_payments_table()
        print("✅ Veritabanı başarıyla oluşturuldu/güncellendi")
    except Exception as e:
        print(f"❌ Veritabanı hatası: {e}")
        # Acil durum çözümü
        conn = sqlite3.connect('database/bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                package_type TEXT DEFAULT '30',
                remaining_rights INTEGER DEFAULT 30,
                total_conversions INTEGER DEFAULT 0,
                successful_conversions INTEGER DEFAULT 0,
                failed_conversions INTEGER DEFAULT 0,
                last_package_date TEXT,
                registered_at TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                file_name TEXT,
                file_size INTEGER,
                source_format TEXT,
                target_format TEXT,
                status TEXT,
                processing_time REAL,
                error_message TEXT,
                converted_at TEXT
            )
        ''')
        conn.commit()
        conn.close()
        print("✅ Veritabanı acil durumda oluşturuldu.")
    
    # Bot uygulamasını oluştur
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Komut handler'ları
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    
    # Buton handler'ları
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^(merhaba|dosya_yukle|check_rights)$"))
    application.add_handler(CallbackQueryHandler(convert_handler, pattern="^convert"))
    application.add_handler(CallbackQueryHandler(admin_button_handler, pattern="^admin_"))
    
    # Ödeme handler'ları
    application.add_handler(CallbackQueryHandler(show_packages, pattern="^show_packages$"))
    application.add_handler(CallbackQueryHandler(show_package_detail, pattern="^package_"))
    application.add_handler(CallbackQueryHandler(start_payment, pattern="^buy_"))
    application.add_handler(CallbackQueryHandler(confirm_payment, pattern="^confirm_payment_"))
    application.add_handler(CallbackQueryHandler(approve_payment, pattern="^approve_payment_"))
    application.add_handler(CallbackQueryHandler(reject_payment, pattern="^reject_payment_"))
    application.add_handler(CallbackQueryHandler(cancel_payment, pattern="^cancel_payment$"))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_to_main$"))
    
    # Mesaj handler'ları
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_query))
    
    print("✅ Bot yapılandırması tamamlandı.")
    print("=" * 60)
    print("🤖 Bot çalışıyor...")
    print("📱 Telegram: @dosya_asistani_bot")
    print("🛑 Durdurmak: CTRL+C")
    print("=" * 60)
    
    try:
        application.run_polling()
    except Exception as e:
        print(f"❌ Bot çalışırken hata: {e}")
        logger.error(f"❌ Bot hatası: {e}")
    finally:
        print("👋 Bot durduruldu.")
        logger.info("👋 Bot durduruldu.")

if __name__ == "__main__":

    main()

