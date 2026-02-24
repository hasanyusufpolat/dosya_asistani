# utils.py
"""
Yardımcı fonksiyonlar
"""

import os
import datetime

def safe_filename(filename):
    """Güvenli dosya adı oluştur"""
    # Geçersiz karakterleri temizle
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename

def format_size(size_bytes):
    """Byte'ı okunabilir formata çevir"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.1f} MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.1f} GB"

def clean_temp_files(user_id, *file_paths):
    """Geçici dosyaları temizle"""
    deleted = 0
    for file_path in file_paths:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                deleted += 1
        except:
            pass
    if deleted > 0:
        print(f"🧹 {deleted} geçici dosya temizlendi: {user_id}")

def get_time_string():
    """Şu anki zamanı string olarak döndür"""
    return datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

def create_detailed_stats(user_data, conversion_stats, processing_time):
    """Detaylı istatistik mesajı oluştur"""
    
    stats = f"""📊 **KULLANIM ÖZETİ**

━━━━━━━━━━━━━━━━━━━━━
📦 **PAKET DURUMU**
• Paket: `30 Dosya Paketi`
• Kullanılan: `{user_data['used']}` dosya
• Kalan Hak: `{user_data['remaining']}` dosya
━━━━━━━━━━━━━━━━━━━━━

📈 **İSTATİSTİKLERİNİZ**
• Toplam Dönüşüm: `{conversion_stats['total']}`
  ├─ Başarılı: `{conversion_stats['success']}` ✅
  └─ Başarısız: `{conversion_stats['failed']}` ❌
• Bugünkü İşlem: `{conversion_stats['today']}`

⏱️ **İŞLEM DETAYI**
• İşlem Süresi: `{processing_time:.1f}` saniye
• İşlem Tarihi: `{get_time_string()}`

━━━━━━━━━━━━━━━━━━━━━
📂 **Yeni dosyanızı bekliyorum...** 
"""
    return stats