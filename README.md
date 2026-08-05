# 🔒 Anonim Telegram Sohbet Botu

Bu proje, Telegram kullanıcılarının birbirlerinin kullanıcı adı veya kimliğini görmeden tamamen **anonim** bir şekilde mesajlaşmasını, fotoğraf, video, ses kaydı, sticker ve belge paylaşmasını sağlayan gelişmiş bir Python Telegram Botudur.

---

## ✨ Özellikler

- **🔒 %100 Anonimlik**: Mesajlar Telegram API'sinin `copy_message` yöntemi ile aktarılır. Gönderenin adı veya ID'si kesinlikle karşı tarafa iletilmez.
- **🔎 Akıllı Eşleşme Kuyruğu**: "Eşleşme Ara" butonuna basan kullanıcılar bekleme havuzuna alınır ve eşleşen 2 kişi anında sohbet odasına bağlanır.
- **⚡ Hızlı İşlemler**:
  - `🔎 Eşleşme Ara`: Rastgele bir partner arar.
  - `➡️ Sonraki Partner`: Mevcut sohbeti bitirip doğrudan yeni birine geçer.
  - `❌ Sohbeti Bitir`: Sohbeti sonlandırır ve ana menüye döner.
  - `⚠️ Şikayet Et`: Rahatsız edici kullanıcıları raporlar ve sohbeti bitirir.
- **📊 Canlı İstatistikler**: Toplam kullanıcı, aktif sohbet sayısı ve kuyruktakileri gösterir.
- **🛡️ Admin Kontrol Paneli**:
  - `/stats`: Bot istatistiklerini görüntüler.
  - `/broadcast <mesaj>`: Tüm kullanıcılara duyuru mesajı gönderir.
  - `/ban <user_id>` / `/unban <user_id>`: İstenmeyen kullanıcıları engeller veya engelini kaldırır.

---

## 🛠️ Kurulum Adımları

### 1. Telegram Bot Token Alma (`@BotFather`)
1. Telegram uygulamasında **[@BotFather](https://t.me/BotFather)** hesabını aratın ve sohbeti başlatın.
2. `/newbot` komutunu gönderin.
3. Botunuz için bir isim ve kullanıcı adı (örneğin: `AnonimSohbetRobotu_bot`) belirleyin.
4. `@BotFather` size bir **HTTP API Token** verecektir (Örnek: `7123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`).

### 2. Bağımlılıkları Yükleme
Terminal / Komut Satırında projenin bulunduğu dizinde şu komutu çalıştırın:

```bash
pip install -r requirements.txt
```

### 3. Yapılandırma (`.env` Dosyası)
Klasör içindeki `.env.example` dosyasının adını `.env` olarak değiştirin veya yeni bir `.env` dosyası oluşturup şu bilgileri yazın:

```env
BOT_TOKEN=7123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
ADMIN_ID=123456789
```

> **Not:** `ADMIN_ID` bilgisini öğrenmek için Telegram'da **[@userinfobot](https://t.me/userinfobot)** bota mesaj atabilirsiniz.

### 4. Botu Çalıştırma

```bash
python bot.py
```

Başarılı şekilde çalıştığında terminalde `🚀 Anonim Telegram Botu Çalışıyor...` mesajını göreceksiniz.

---

## 📁 Proje Yapısı

```
anonymous-telegram-bot/
├── bot.py              # Bot ana mantığı, klavye butonları ve mesaj iletimi
├── database.py         # SQLite veritabanı eşleşme ve kuyruk yönetimi
├── config.py           # .env dosyası yapılandırma yükleyicisi
├── requirements.txt    # Gereksinim duyulan Python paketleri
├── .env.example        # Yapılandırma taslağı
└── README.md           # Kullanım rehberi
```
