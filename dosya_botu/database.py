"""
GELİŞMİŞ VERİTABANI YÖNETİM SİSTEMİ
Tüm veritabanı işlemleri bu dosyada profesyonelce yönetilir
"""

import sqlite3
import os
import datetime
import logging
from contextlib import contextmanager
from typing import Optional, Dict, List, Any, Tuple
from config import DEFAULT_PACKAGE_SIZE

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Profesyonel Veritabanı Yöneticisi"""
    
    def __init__(self, db_path: str = 'database/bot.db'):
        self.db_path = db_path
        self._ensure_database_dir()
        
    def _ensure_database_dir(self):
        """Veritabanı klasörünün varlığını kontrol et"""
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            logger.info(f"📁 Veritabanı klasörü oluşturuldu: {db_dir}")
    
    @contextmanager
    def get_connection(self):
        """Veritabanı bağlantısını yönet (context manager)"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Sözlük benzeri erişim
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"❌ Veritabanı hatası: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
                logger.debug("🔌 Veritabanı bağlantısı kapatıldı")
    
    def execute_query(self, query: str, params: tuple = ()) -> Optional[List[Dict]]:
        """SQL sorgusunu çalıştır ve sonuçları sözlük listesi olarak döndür"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if query.strip().upper().startswith('SELECT'):
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            else:
                conn.commit()
                return None
    
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """INSERT sorgusu çalıştır ve son eklenen ID'yi döndür"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.lastrowid
    
    # ========== TABLO OLUŞTURMA VE GÜNCELLEME ==========
    
    def create_tables(self):
        """Tüm veritabanı tablolarını oluştur"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # KULLANICILAR ANA TABLOSU
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language_code TEXT DEFAULT 'tr',
                    is_premium BOOLEAN DEFAULT 0,
                    package_type TEXT DEFAULT '30',
                    remaining_rights INTEGER DEFAULT 30,
                    total_conversions INTEGER DEFAULT 0,
                    successful_conversions INTEGER DEFAULT 0,
                    failed_conversions INTEGER DEFAULT 0,
                    last_activity TEXT,
                    registered_at TEXT,
                    updated_at TEXT,
                    notes TEXT
                )
            ''')
            logger.info("✅ Users tablosu oluşturuldu/kontrol edildi")
            
            # KULLANICI AKTİVİTE LOGLARI
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    activity_type TEXT NOT NULL,
                    details TEXT,
                    ip_address TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            ''')
            logger.info("✅ User activity tablosu oluşturuldu")
            
            # DÖNÜŞÜM KAYITLARI
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size INTEGER,
                    source_format TEXT NOT NULL,
                    target_format TEXT NOT NULL,
                    status TEXT NOT NULL,
                    processing_time REAL,
                    error_message TEXT,
                    converted_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            ''')
            logger.info("✅ Conversions tablosu oluşturuldu")
            
            # İNDİCE'LER (Performans için)
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_user_id ON user_activity(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_created ON user_activity(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversions_user_id ON conversions(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversions_date ON conversions(converted_at)')
            
            logger.info("✅ Veritabanı indeksleri oluşturuldu")
            conn.commit()
    
    def upgrade_database(self):
        """Veritabanını güncelle (eski sürümlerden yeni sürüme)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # users tablosundaki sütunları kontrol et
                cursor.execute("PRAGMA table_info(users)")
                columns = [col['name'] for col in cursor.fetchall()]
                
                # Eksik sütunları ekle
                if 'total_conversions' not in columns:
                    logger.info("🔄 'total_conversions' sütunu ekleniyor...")
                    cursor.execute("ALTER TABLE users ADD COLUMN total_conversions INTEGER DEFAULT 0")
                    # Mevcut kayıtları güncelle
                    cursor.execute("UPDATE users SET total_conversions = successful_conversions + failed_conversions")
                    logger.info("✅ 'total_conversions' sütunu eklendi")
                
                if 'last_name' not in columns:
                    logger.info("🔄 'last_name' sütunu ekleniyor...")
                    cursor.execute("ALTER TABLE users ADD COLUMN last_name TEXT")
                    logger.info("✅ 'last_name' sütunu eklendi")
                
                if 'language_code' not in columns:
                    logger.info("🔄 'language_code' sütunu ekleniyor...")
                    cursor.execute("ALTER TABLE users ADD COLUMN language_code TEXT DEFAULT 'tr'")
                    logger.info("✅ 'language_code' sütunu eklendi")
                
                if 'is_premium' not in columns:
                    logger.info("🔄 'is_premium' sütunu ekleniyor...")
                    cursor.execute("ALTER TABLE users ADD COLUMN is_premium BOOLEAN DEFAULT 0")
                    logger.info("✅ 'is_premium' sütunu eklendi")
                
                if 'updated_at' not in columns:
                    logger.info("🔄 'updated_at' sütunu ekleniyor...")
                    cursor.execute("ALTER TABLE users ADD COLUMN updated_at TEXT")
                    # Mevcut kayıtları güncelle
                    cursor.execute("UPDATE users SET updated_at = last_activity WHERE updated_at IS NULL")
                    logger.info("✅ 'updated_at' sütunu eklendi")
                
                if 'notes' not in columns:
                    logger.info("🔄 'notes' sütunu ekleniyor...")
                    cursor.execute("ALTER TABLE users ADD COLUMN notes TEXT")
                    logger.info("✅ 'notes' sütunu eklendi")
                
                conn.commit()
                logger.info("✅ Veritabanı güncellemesi tamamlandı")
                
        except Exception as e:
            logger.error(f"❌ Veritabanı güncellenirken hata: {e}")
    
    # ========== KULLANICI İŞLEMLERİ ==========
    
    def register_user(self, user) -> bool:
        """
        Kullanıcıyı veritabanına kaydet veya güncelle
        Returns: Başarılı ise True, değilse False
        """
        try:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            username = user.username or ""
            first_name = user.first_name or ""
            last_name = getattr(user, 'last_name', "") or ""
            language_code = getattr(user, 'language_code', "tr") or "tr"
            is_premium = 1 if getattr(user, 'is_premium', False) else 0
            
            # Kullanıcı var mı kontrol et
            existing = self.execute_query(
                "SELECT * FROM users WHERE user_id = ?", 
                (user.id,)
            )
            
            if not existing:
                # YENİ KULLANICI
                query = '''
                    INSERT INTO users 
                    (user_id, username, first_name, last_name, language_code, is_premium,
                     remaining_rights, total_conversions, successful_conversions, 
                     failed_conversions, last_activity, registered_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?, ?)
                '''
                self.execute_query(query, (
                    user.id, username, first_name, last_name, language_code, is_premium,
                    DEFAULT_PACKAGE_SIZE, now, now, now
                ))
                
                # Aktivite kaydı
                self.log_user_activity(user.id, 'registration', 'Yeni kullanıcı kaydı')
                
                logger.info(f"✅ YENİ KULLANICI KAYDEDİLDİ: {user.id} - @{username}")
                return True
            else:
                # MEVCUT KULLANICI - Bilgileri güncelle
                query = '''
                    UPDATE users SET 
                        username = ?,
                        first_name = ?,
                        last_name = ?,
                        language_code = ?,
                        is_premium = ?,
                        last_activity = ?,
                        updated_at = ?
                    WHERE user_id = ?
                '''
                self.execute_query(query, (
                    username, first_name, last_name, language_code, is_premium, 
                    now, now, user.id
                ))
                
                # Aktivite kaydı
                self.log_user_activity(user.id, 'login', 'Kullanıcı girişi')
                
                logger.info(f"✅ KULLANICI GÜNCELLENDİ: {user.id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Kullanıcı kaydedilirken hata: {e}")
            return False
    
    def log_user_activity(self, user_id: int, activity_type: str, details: str = ""):
        """Kullanıcı aktivitelerini kaydet"""
        try:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            query = '''
                INSERT INTO user_activity (user_id, activity_type, details, created_at)
                VALUES (?, ?, ?, ?)
            '''
            self.execute_query(query, (user_id, activity_type, details, now))
            logger.debug(f"📝 Aktivite kaydedildi: {user_id} - {activity_type}")
        except Exception as e:
            logger.error(f"❌ Aktivite kaydedilirken hata: {e}")
    
    def get_user_info(self, user_id: int) -> Optional[Dict]:
        """Kullanıcı bilgilerini detaylı getir"""
        try:
            result = self.execute_query(
                "SELECT * FROM users WHERE user_id = ?", 
                (user_id,)
            )
            return result[0] if result else None
        except Exception as e:
            logger.error(f"❌ Kullanıcı bilgisi alınırken hata: {e}")
            return None
    
    def get_remaining_rights(self, user_id: int) -> int:
        """Kullanıcının kalan hakkını getir"""
        try:
            result = self.execute_query(
                "SELECT remaining_rights FROM users WHERE user_id = ?", 
                (user_id,)
            )
            return result[0]['remaining_rights'] if result else 0
        except Exception as e:
            logger.error(f"❌ Hak sorgulanırken hata: {e}")
            return 0
    
    def decrease_rights(self, user_id: int) -> bool:
        """Kullanıcının hakkını 1 azalt (BAŞARILI işlem)"""
        try:
            # Önce mevcut hakları kontrol et
            current = self.get_remaining_rights(user_id)
            if current <= 0:
                logger.warning(f"⚠️ Kullanıcı {user_id}'nin hakkı kalmamış!")
                return False
            
            query = """
                UPDATE users SET 
                    remaining_rights = remaining_rights - 1,
                    successful_conversions = successful_conversions + 1,
                    total_conversions = total_conversions + 1,
                    last_activity = ?,
                    updated_at = ?
                WHERE user_id = ? AND remaining_rights > 0
            """
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.execute_query(query, (now, now, user_id))
            
            self.log_user_activity(user_id, 'conversion_success', 'Başarılı dönüşüm')
            logger.info(f"✅ Kullanıcı {user_id} hakkı azaltıldı. Kalan: {current-1}")
            return True
        except Exception as e:
            logger.error(f"❌ Hak azaltılırken hata: {e}")
            return False
    
    def increase_failed_count(self, user_id: int) -> bool:
        """Başarısız işlem sayısını artır (HAK GİTMEZ)"""
        try:
            query = """
                UPDATE users SET 
                    failed_conversions = failed_conversions + 1,
                    total_conversions = total_conversions + 1,
                    last_activity = ?,
                    updated_at = ?
                WHERE user_id = ?
            """
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.execute_query(query, (now, now, user_id))
            
            self.log_user_activity(user_id, 'conversion_failed', 'Başarısız dönüşüm')
            logger.info(f"✅ Kullanıcı {user_id} başarısız işlem kaydedildi.")
            return True
        except Exception as e:
            logger.error(f"❌ Başarısız sayısı artırılırken hata: {e}")
            return False
    
    def add_rights(self, user_id: int, rights_to_add: int, package_id: str = None) -> bool:
        """Kullanıcıya hak ekle (paket satın alımında)"""
        try:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Mevcut hakları kontrol et
            current = self.get_remaining_rights(user_id)
            
            if package_id:
                query = """
                    UPDATE users SET 
                        remaining_rights = remaining_rights + ?,
                        package_type = ?,
                        last_activity = ?,
                        updated_at = ?
                    WHERE user_id = ?
                """
                self.execute_query(query, (rights_to_add, package_id, now, now, user_id))
            else:
                query = """
                    UPDATE users SET 
                        remaining_rights = remaining_rights + ?,
                        last_activity = ?,
                        updated_at = ?
                    WHERE user_id = ?
                """
                self.execute_query(query, (rights_to_add, now, now, user_id))
            
            self.log_user_activity(user_id, 'rights_added', f'+{rights_to_add} hak eklendi')
            logger.info(f"✅ Kullanıcı {user_id} - {rights_to_add} hak eklendi. Yeni toplam: {current + rights_to_add}")
            return True
        except Exception as e:
            logger.error(f"❌ Hak eklenirken hata: {e}")
            return False
    
    # ========== DÖNÜŞÜM KAYITLARI ==========
    
    def save_conversion_record(self, user_id: int, file_name: str, file_size: int, 
                              source_format: str, target_format: str, status: str, 
                              processing_time: float, error_message: str = None) -> bool:
        """Dönüşüm kaydını veritabanına ekle"""
        try:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            query = '''
                INSERT INTO conversions 
                (user_id, file_name, file_size, source_format, target_format, 
                 status, processing_time, error_message, converted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            self.execute_query(query, (
                user_id, file_name, file_size, source_format, target_format,
                status, processing_time, error_message, now
            ))
            
            logger.info(f"📁 Dönüşüm kaydedildi: {user_id} - {source_format}->{target_format} - {status}")
            return True
        except Exception as e:
            logger.error(f"❌ Dönüşüm kaydı eklenirken hata: {e}")
            return False
    
    # ========== İSTATİSTİKLER ==========
    
    def get_user_stats(self, user_id: int) -> Optional[Dict]:
        """Kullanıcı istatistiklerini getir"""
        try:
            # Kullanıcı bilgileri
            user = self.execute_query('''
                SELECT 
                    remaining_rights,
                    total_conversions,
                    successful_conversions,
                    failed_conversions,
                    registered_at
                FROM users 
                WHERE user_id = ?
            ''', (user_id,))
            
            if not user:
                return None
            
            # Bugünkü işlem sayısı
            today = self.execute_query('''
                SELECT COUNT(*) as count FROM conversions 
                WHERE user_id = ? AND date(converted_at) = date('now')
            ''', (user_id,))
            
            # Son 7 günlük işlemler
            weekly = self.execute_query('''
                SELECT COUNT(*) as count FROM conversions 
                WHERE user_id = ? AND converted_at >= date('now', '-7 days')
            ''', (user_id,))
            
            u = user[0]
            return {
                'remaining': u['remaining_rights'],
                'total': u['total_conversions'] or 0,
                'success': u['successful_conversions'] or 0,
                'failed': u['failed_conversions'] or 0,
                'today': today[0]['count'] if today else 0,
                'weekly': weekly[0]['count'] if weekly else 0,
                'registered_at': u['registered_at']
            }
        except Exception as e:
            logger.error(f"❌ İstatistik alınırken hata: {e}")
            return None
    
    def get_admin_stats(self) -> Optional[Dict]:
        """Admin için sistem istatistikleri"""
        try:
            # Toplam kullanıcı
            total_users = self.execute_query("SELECT COUNT(*) as count FROM users")
            
            # Bugünkü dönüşümler
            today_conversions = self.execute_query(
                "SELECT COUNT(*) as count FROM conversions WHERE date(converted_at) = date('now')"
            )
            
            # Başarılı dönüşümler
            success_total = self.execute_query(
                "SELECT COUNT(*) as count FROM conversions WHERE status='success'"
            )
            
            # Başarısız dönüşümler
            failed_total = self.execute_query(
                "SELECT COUNT(*) as count FROM conversions WHERE status='failed'"
            )
            
            # Toplam başarılı işlemler (kullanıcı bazlı)
            total_success = self.execute_query(
                "SELECT SUM(successful_conversions) as sum FROM users"
            )
            
            # Toplam başarısız işlemler
            total_failed = self.execute_query(
                "SELECT SUM(failed_conversions) as sum FROM users"
            )
            
            # Aktif kullanıcılar (son 24 saat)
            active_users = self.execute_query('''
                SELECT COUNT(DISTINCT user_id) as count FROM user_activity 
                WHERE created_at >= datetime('now', '-1 day')
            ''')
            
            # En çok kullanılan formatlar
            top_formats = self.execute_query('''
                SELECT target_format, COUNT(*) as count 
                FROM conversions 
                GROUP BY target_format 
                ORDER BY count DESC 
                LIMIT 5
            ''')
            
            format_text = "\n".join([f"  • {f['target_format']}: {f['count']}" for f in top_formats]) if top_formats else "  • Veri yok"
            
            return {
                'total_users': total_users[0]['count'] if total_users else 0,
                'active_users': active_users[0]['count'] if active_users else 0,
                'today_conversions': today_conversions[0]['count'] if today_conversions else 0,
                'success_total': success_total[0]['count'] if success_total else 0,
                'failed_total': failed_total[0]['count'] if failed_total else 0,
                'total_success': total_success[0]['sum'] or 0 if total_success else 0,
                'total_failed': total_failed[0]['sum'] or 0 if total_failed else 0,
                'top_formats': format_text
            }
        except Exception as e:
            logger.error(f"❌ Admin istatistikleri alınırken hata: {e}")
            return None
    
    def get_pending_payments(self) -> List[Dict]:
        """Bekleyen ödemeleri getir"""
        try:
            return self.execute_query('''
                SELECT * FROM pending_payments 
                WHERE status = 'pending' 
                ORDER BY requested_at DESC
            ''')
        except Exception as e:
            logger.error(f"❌ Bekleyen ödemeler alınırken hata: {e}")
            return []
    
    def get_user_conversions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Kullanıcının son dönüşümlerini getir"""
        try:
            return self.execute_query('''
                SELECT * FROM conversions 
                WHERE user_id = ? 
                ORDER BY converted_at DESC 
                LIMIT ?
            ''', (user_id, limit))
        except Exception as e:
            logger.error(f"❌ Kullanıcı dönüşümleri alınırken hata: {e}")
            return []
    
    def backup_database(self, backup_path: str = None):
        """Veritabanı yedeği al"""
        try:
            if not backup_path:
                backup_path = f"database/backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"💾 Veritabanı yedeği alındı: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"❌ Yedekleme hatası: {e}")
            return None


# ========== GLOBAL ERİŞİM NOKTALARI ==========
_db_manager = None

def get_db() -> DatabaseManager:
    """Singleton DatabaseManager instance'ı döndür"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager

# Kolaylık fonksiyonları (geriye uyumluluk için)
def init_database():
    """Veritabanını oluştur (geriye uyumluluk)"""
    db = get_db()
    db.create_tables()
    # Veritabanını güncelle (eski sürümler için)
    db.upgrade_database()

def register_user(user):
    """Kullanıcı kaydet (geriye uyumluluk)"""
    return get_db().register_user(user)

def get_remaining_rights(user_id):
    """Kalan hak (geriye uyumluluk)"""
    return get_db().get_remaining_rights(user_id)

def decrease_rights(user_id):
    """Hak azalt (geriye uyumluluk)"""
    return get_db().decrease_rights(user_id)

def increase_failed_count(user_id):
    """Başarısız sayısı artır (geriye uyumluluk)"""
    return get_db().increase_failed_count(user_id)

def save_conversion_record(user_id, file_name, file_size, source_format, target_format, 
                          status, processing_time, error_message=None):
    """Dönüşüm kaydet (geriye uyumluluk)"""
    return get_db().save_conversion_record(user_id, file_name, file_size, source_format, 
                                          target_format, status, processing_time, error_message)

def get_user_stats(user_id):
    """Kullanıcı istatistikleri (geriye uyumluluk)"""
    return get_db().get_user_stats(user_id)

def get_admin_stats():
    """Admin istatistikleri (geriye uyumluluk)"""
    return get_db().get_admin_stats()

def log_user_activity(user_id, activity_type, details=""):
    """Aktivite kaydet (geriye uyumluluk)"""
    return get_db().log_user_activity(user_id, activity_type, details)

def add_rights(user_id, rights_to_add, package_id=None):
    """Hak ekle (geriye uyumluluk)"""
    return get_db().add_rights(user_id, rights_to_add, package_id)


# ========== TEST FONKSİYONU ==========
if __name__ == "__main__":
    print("🔧 Veritabanı test ediliyor...")
    db = get_db()
    db.create_tables()
    db.upgrade_database()  # Güncellemeyi çalıştır
    print("✅ Veritabanı hazır!")
    print(f"📊 Admin istatistikleri: {db.get_admin_stats()}")