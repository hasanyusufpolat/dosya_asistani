# config.py
"""
Bot yapılandırma dosyası
"""

# ========== BOT AYARLARI ==========
BOT_TOKEN = "8530574443:AAHnMkNcNHVbtYIbGrqUmylGh7bikFRZkWU"
ADMIN_ID = 6284943821  # @userinfobot'dan aldığın ID

# ========== PAKET AYARLARI ==========
DEFAULT_PACKAGE_SIZE = 30  # Varsayılan paket boyutu
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# ========== DÖNÜŞÜM AYARLARI ==========
SUPPORTED_FORMATS = {
    '.pdf': 'PDF',
    '.doc': 'WORD', '.docx': 'WORD',
    '.xls': 'EXCEL', '.xlsx': 'EXCEL',
    '.ppt': 'POWERPOINT', '.pptx': 'POWERPOINT',
    '.png': 'GORSEL', '.jpg': 'GORSEL', '.jpeg': 'GORSEL'
}

# Dönüşüm haritası (hangi formattan hangilerine dönüşebilir)
CONVERSION_MAP = {
    'WORD': ['PDF', 'EXCEL', 'POWERPOINT', 'GORSEL'],
    'EXCEL': ['PDF', 'WORD', 'POWERPOINT'],
    'POWERPOINT': ['PDF', 'WORD', 'GORSEL'],
    'PDF': ['WORD', 'GORSEL'],
    'GORSEL': ['PDF', 'WORD']
}

# Buton görünen isimleri
DISPLAY_NAMES = {
    'PDF': '📄 PDF',
    'WORD': '📝 Word',
    'EXCEL': '📊 Excel',
    'POWERPOINT': '📽️ PowerPoint',
    'GORSEL': '🖼️ Görsel'
}

# Dosya uzantıları
EXTENSION_MAP = {
    'PDF': '.pdf',
    'WORD': '.docx',
    'EXCEL': '.xlsx',
    'POWERPOINT': '.pptx',
    'GORSEL': '.png'
}