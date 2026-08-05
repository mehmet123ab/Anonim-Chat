import sys
import logging
import asyncio

# Windows terminal UTF-8 desteği
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, LabeledPrice
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    ContextTypes,
    filters
)

import config
import database as db

# Log yapılandırması
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Klavye Butonları Metinleri ---
BTN_FIND = "🔎 Rastgele Eşleşme Ara"
BTN_FIND_GENDER = "🎯 Cinsiyete Göre Ara"
BTN_BUY_CREDITS = "⭐️ Hak Satın Al (100 Hak / 50 Yıldız)"
BTN_CANCEL_QUEUE = "❌ Aramayı İptal Et"
BTN_NEXT = "➡️ Sonraki Partner"
BTN_STOP = "❌ Sohbeti Bitir"
BTN_REPORT = "⚠️ Şikayet Et"
BTN_STATS = "📊 İstatistikler"
BTN_HELP = "ℹ️ Yardım"

BTN_GENDER_MALE = "👨 Erkek"
BTN_GENDER_FEMALE = "👩 Kadın"

BTN_TARGET_MALE = "👨 Erkek Partner Ara"
BTN_TARGET_FEMALE = "👩 Kadın Partner Ara"
BTN_CANCEL = "❌ İptal"

# --- Klavyeler ---
GENDER_SELECT_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton(BTN_GENDER_MALE), KeyboardButton(BTN_GENDER_FEMALE)]
    ],
    resize_keyboard=True
)

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton(BTN_FIND), KeyboardButton(BTN_FIND_GENDER)],
        [KeyboardButton(BTN_BUY_CREDITS)],
        [KeyboardButton(BTN_STATS), KeyboardButton(BTN_HELP)]
    ],
    resize_keyboard=True
)

CHOOSE_TARGET_GENDER_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton(BTN_TARGET_MALE), KeyboardButton(BTN_TARGET_FEMALE)],
        [KeyboardButton(BTN_CANCEL)]
    ],
    resize_keyboard=True
)

QUEUE_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton(BTN_CANCEL_QUEUE)]
    ],
    resize_keyboard=True
)

CHAT_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton(BTN_NEXT), KeyboardButton(BTN_STOP)],
        [KeyboardButton(BTN_REPORT)]
    ],
    resize_keyboard=True
)

# --- Handlers ---
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start ve Yardım komutu."""
    user = update.effective_user
    db.add_or_update_user(user.id, user.username, user.first_name)
    
    if db.is_user_banned(user.id):
        await update.message.reply_text("❌ Hesabınız engellenmiştir.")
        return

    gender = db.get_user_gender(user.id)
    if not gender:
        # Cinsiyet henüz seçilmemiş
        await update.message.reply_markdown(
            f"👋 **Merhaba {user.first_name}!**\n\n"
            "🔒 **Anonim Sohbet Botu**'na hoş geldiniz.\n"
            "Devam edebilmek için lütfen **kendi cinsiyetinizi** seçin:",
            reply_markup=GENDER_SELECT_KEYBOARD
        )
        return

    credits = db.get_gender_credits(user.id)
    welcome_text = (
        f"👋 **Merhaba {user.first_name}!**\n\n"
        "🔒 **Anonim Sohbet Botu**'na hoş geldiniz.\n"
        f"👤 Cinsiyetiniz: *{gender}*\n"
        f"⭐️ Kalan Filtreli Eşleşme Hakkınız: `{credits}`\n\n"
        "📌 **Kullanabileceğiniz Butonlar:**\n"
        "• **🔎 Rastgele Eşleşme Ara**: Herkesle rastgele eşleşir (Ücretsiz).\n"
        "• **🎯 Cinsiyete Göre Ara**: Belirlediğiniz cinsiyet ile eşleşir (1 Hak düşer).\n"
        "• **⭐️ Hak Satın Al**: Telegram Yıldızları ile 100 filtreli eşleşme satın alır.\n"
        "• **➡️ Sonraki Partner**: Mevcut sohbeti bitirip yeni birine geçer.\n"
        "• **❌ Sohbeti Bitir**: Sohbeti sonlandırır.\n"
        "• **⚠️ Şikayet Et**: Rahatsız edici kullanıcıları raporlar.\n\n"
        "Başlamak için aşağıdaki butonlardan birine basın!"
    )
    await update.message.reply_markdown(welcome_text, reply_markup=MAIN_KEYBOARD)

async def buy_credits_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Telegram Yıldızları (XTR) ile ödeme faturası (Invoice) oluşturur ve gönderir."""
    chat_id = update.effective_chat.id
    
    title = "100 Cinsiyet Filtreli Eşleşme Hakkı"
    description = "Sohbet ararken tercih ettiğiniz cinsiyetle (Erkek/Kadın) eşleşme sağlayan 100 hak."
    payload = "gender_credits_100"
    currency = "XTR"  # Telegram Stars para birimi
    prices = [LabeledPrice("100 Cinsiyet Filtreli Hak", 50)]  # 50 Telegram Yıldızı (~1$)

    try:
        await context.bot.send_invoice(
            chat_id=chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token="",  # Telegram Stars için provider_token boş string olmalıdır
            currency=currency,
            prices=prices
        )
    except Exception as e:
        logger.error(f"Invoice gönderilemedi: {e}")
        await update.message.reply_text(
            "⚠️ Ödeme faturası oluşturulurken bir hata oluştu. Lütfen daha sonra tekrar deneyin."
        )

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ödeme öncesi doğrulama kontrolü."""
    query = update.pre_checkout_query
    if query.invoice_payload != "gender_credits_100":
        await query.answer(ok=False, error_message="Bilinmeyen sipariş paketi.")
    else:
        await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Başarılı Telegram Stars ödemesi sonrası hak tanımlama."""
    user_id = update.effective_user.id
    db.add_gender_credits(user_id, 100)
    new_credits = db.get_gender_credits(user_id)
    
    await update.message.reply_markdown(
        "🎉 **Ödeme Başarıyla Tamamlandı!**\n\n"
        "Hesabınıza **100 Adet Cinsiyet Filtreli Eşleşme Hakkı** eklendi.\n"
        f"⭐️ Toplam Kalan Filtreli Hakkınız: `{new_credits}`\n\n"
        "Şimdi **🎯 Cinsiyete Göre Ara** butonunu kullanarak istediğiniz cinsiyet ile eşleşebilirsiniz!",
        reply_markup=MAIN_KEYBOARD
    )

async def find_partner(update: Update, context: ContextTypes.DEFAULT_TYPE, target_gender: str = "ANY"):
    """Sohbet partneri arama ve eşleştirme mantığı."""
    user_id = update.effective_user.id
    
    if db.is_user_banned(user_id):
        await update.message.reply_text("❌ Hesabınız engellenmiştir.")
        return

    own_gender = db.get_user_gender(user_id)
    if not own_gender:
        await start_handler(update, context)
        return

    # Aktif sohbet kontrolü
    current_partner = db.get_active_partner(user_id)
    if current_partner:
        await update.message.reply_text(
            "⚠️ Zaten aktif bir sohbettesiniz.\nSohbeti bitirmek için **❌ Sohbeti Bitir** butonunu kullanın.",
            reply_markup=CHAT_KEYBOARD
        )
        return

    # Filtreli arama yapılıyorsa hak kontrolü
    if target_gender != "ANY":
        if not db.use_gender_credit(user_id):
            await update.message.reply_markdown(
                "⚠️ **Cinsiyet filtreli arama hakkınız bulunmuyor!**\n\n"
                "100 Cinsiyet Filtreli Eşleşme Hakkını **50 Telegram Yıldızı (~1$)** karşılığında hemen satın alabilirsiniz.",
                reply_markup=MAIN_KEYBOARD
            )
            await buy_credits_handler(update, context)
            return

    # Bekleme kuyruğundan partner ara
    partner_id = db.pop_queue_partner(user_id, own_gender=own_gender, target_gender=target_gender)
    
    if partner_id:
        # Eşleşme sağlandı
        db.create_active_chat(user_id, partner_id)
        
        match_msg = (
            "🎉 **Eşleşme Sağlandı!**\n\n"
            "Bir yabancı ile bağlandınız. Merhaba deyin 👋\n"
            "💬 *Gönderdiğiniz tüm mesajlar, fotoğraflar, ses kayıtları ve medyalar anonim olarak iletilir.*"
        )
        
        await update.message.reply_markdown(match_msg, reply_markup=CHAT_KEYBOARD)
        try:
            await context.bot.send_message(
                chat_id=partner_id,
                text=match_msg,
                parse_mode="Markdown",
                reply_markup=CHAT_KEYBOARD
            )
        except Exception as e:
            logger.warning(f"Partner {partner_id} mesaj gönderilemedi: {e}")
            db.end_active_chat(user_id)
            await update.message.reply_text("⚠️ Eşleşilen kullanıcıya ulaşılamadı. Tekrar aranıyor...")
            await find_partner(update, context, target_gender=target_gender)
    else:
        # Kuyruğa ekle
        db.add_to_queue(user_id, target_gender=target_gender, own_gender=own_gender)
        
        gender_str = "Rastgele" if target_gender == "ANY" else f"*{target_gender}*"
        await update.message.reply_markdown(
            f"🔎 **Bir sohbet ortağı ({gender_str}) aranıyor...** Lütfen bekleyin.\n"
            "Biri bağlandığında size bildirim gelecektir.",
            reply_markup=QUEUE_KEYBOARD
        )

async def cancel_queue_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kuyruktan çıkma."""
    user_id = update.effective_user.id
    if db.is_in_queue(user_id):
        db.remove_from_queue(user_id)
        await update.message.reply_text("❌ Arama iptal edildi.", reply_markup=MAIN_KEYBOARD)
    else:
        await update.message.reply_text("Zaten bir arama yapmıyordunuz.", reply_markup=MAIN_KEYBOARD)

async def stop_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mevcut sohbeti sonlandırma."""
    user_id = update.effective_user.id
    
    if db.is_in_queue(user_id):
        db.remove_from_queue(user_id)
        await update.message.reply_text("❌ Arama iptal edildi.", reply_markup=MAIN_KEYBOARD)
        return

    partner_id = db.end_active_chat(user_id)
    
    if partner_id:
        await update.message.reply_text(
            "❌ Sohbeti sonlandırdınız. Yeni biriyle konuşmak için **🔎 Rastgele Eşleşme Ara** butonuna basabilirsiniz.",
            reply_markup=MAIN_KEYBOARD
        )
        try:
            await context.bot.send_message(
                chat_id=partner_id,
                text="❌ Sohbet ortağınız sohbeti sonlandırdı. Yeni biriyle konuşmak için butonları kullanabilirsiniz.",
                parse_mode="Markdown",
                reply_markup=MAIN_KEYBOARD
            )
        except Exception:
            pass
    else:
        await update.message.reply_text("Aktif bir sohbetiniz bulunmuyor.", reply_markup=MAIN_KEYBOARD)

async def next_partner_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mevcut sohbeti bitirip doğrudan yeni birine geçme."""
    user_id = update.effective_user.id
    partner_id = db.end_active_chat(user_id)
    
    if partner_id:
        try:
            await context.bot.send_message(
                chat_id=partner_id,
                text="❌ Sohbet ortağınız başka bir kişiye geçti.",
                parse_mode="Markdown",
                reply_markup=MAIN_KEYBOARD
            )
        except Exception:
            pass

    # Rastgele yeni arama başlat
    await find_partner(update, context, target_gender="ANY")

async def report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mevcut partneri şikayet etme."""
    user_id = update.effective_user.id
    partner_id = db.get_active_partner(user_id)
    
    if partner_id:
        db.add_report(reporter_id=user_id, reported_id=partner_id, reason="Kullanıcı buton ile şikayet edildi.")
        db.end_active_chat(user_id)
        
        await update.message.reply_text(
            "⚠️ Sohbet ortağınız şikayet edildi ve sohbet sonlandırıldı. Bildiriminiz için teşekkürler.",
            reply_markup=MAIN_KEYBOARD
        )
        
        try:
            await context.bot.send_message(
                chat_id=partner_id,
                text="❌ Sohbetiniz şikayet bildirimi nedeniyle sonlandırıldı.",
                reply_markup=MAIN_KEYBOARD
            )
        except Exception:
            pass
            
        if config.ADMIN_ID > 0:
            try:
                await context.bot.send_message(
                    chat_id=config.ADMIN_ID,
                    text=f"🚨 **YENİ ŞİKAYET!**\n\nŞikayet Eden ID: `{user_id}`\nŞikayet Edilen ID: `{partner_id}`",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Admin bilgilendirilemedi: {e}")
    else:
        await update.message.reply_text("Şikayet edebileceğiniz aktif bir sohbet ortağınız yok.", reply_markup=MAIN_KEYBOARD)

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """İstatistik gösterimi."""
    user_id = update.effective_user.id
    total_users, active_chats, in_queue = db.get_stats()
    user_credits = db.get_gender_credits(user_id)
    user_gender = db.get_user_gender(user_id) or "Seçilmedi"

    stats_text = (
        "📊 **Bot İstatistikleri & Hesabınız**\n\n"
        f"👤 Cinsiyetiniz: `{user_gender}`\n"
        f"⭐️ Filtreli Eşleşme Hakkınız: `{user_credits}`\n"
        "------------------------------------\n"
        f"👥 Toplam Kayıtlı Kullanıcı: `{total_users}`\n"
        f"💬 Aktif Sohbet Sayısı: `{active_chats}`\n"
        f"⏳ Bekleme Kuyruğundaki Kişi: `{in_queue}`"
    )
    await update.message.reply_markdown(stats_text)

# --- Admin Komutları ---
async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin duyuru komutu."""
    user_id = update.effective_user.id
    if config.ADMIN_ID == 0 or user_id != config.ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Kullanım: `/broadcast <gönderilecek mesaj>`", parse_mode="Markdown")
        return

    broadcast_text = " ".join(context.args)
    user_ids = db.get_all_user_ids()
    sent_count = 0
    
    await update.message.reply_text(f"📢 Duyuru {len(user_ids)} kullanıcıya iletiliyor...")
    
    for uid in user_ids:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 **Duyuru:**\n\n{broadcast_text}", parse_mode="Markdown")
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
            
    await update.message.reply_text(f"✅ Duyuru başarıyla {sent_count}/{len(user_ids)} kullanıcıya ulaştırıldı.")

async def admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin ban komutu."""
    user_id = update.effective_user.id
    if config.ADMIN_ID == 0 or user_id != config.ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Kullanım: `/ban <user_id>`", parse_mode="Markdown")
        return

    try:
        target_id = int(context.args[0])
        db.end_active_chat(target_id)
        db.remove_from_queue(target_id)
        db.ban_user(target_id)
        await update.message.reply_text(f"🚫 `{target_id}` id'li kullanıcı engellendi.", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("Lütfen geçerli bir sayısal ID girin.")

async def admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin unban komutu."""
    user_id = update.effective_user.id
    if config.ADMIN_ID == 0 or user_id != config.ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Kullanım: `/unban <user_id>`", parse_mode="Markdown")
        return

    try:
        target_id = int(context.args[0])
        db.unban_user(target_id)
        await update.message.reply_text(f"✅ `{target_id}` id'li kullanıcının engeli kaldırıldı.", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("Lütfen geçerli bir sayısal ID girin.")

async def media_block_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tüm fotoğraf, video, ses kaydı, sticker ve medya türlerini kesin olarak engeller."""
    await update.message.reply_markdown(
        "🚫 **MEDYA GÖNDERİMİ ENGELLENDİ!**\n\n"
        "🔒 Güvenlik ve gizlilik nedeniyle **fotoğraf, video, ses kaydı, sticker ve dosya** gönderimi tamamen yasaktır.\n\n"
        "✍️ Lütfen sadece **yazılı metin mesajı** gönderin."
    )

# --- Mesaj ve Yönlendirici ---
async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı mesajlarını yönlendirir ve işler."""
    user = update.effective_user
    user_id = user.id
    text = update.message.text if update.message.text else ""

    if db.is_user_banned(user_id):
        await update.message.reply_text("❌ Hesabınız engellenmiştir.")
        return

    # Kendi Cinsiyeti Seçilmemişse Kaydet
    if text in [BTN_GENDER_MALE, BTN_GENDER_FEMALE]:
        gender_val = "Erkek" if text == BTN_GENDER_MALE else "Kadın"
        db.set_user_gender(user_id, gender_val)
        await update.message.reply_markdown(
            f"✅ Cinsiyetiniz **{gender_val}** olarak kaydedildi!\n\n"
            "Artık eşleşme aramaya başlayabilirsiniz.",
            reply_markup=MAIN_KEYBOARD
        )
        return

    # Eğer cinsiyet tanımlı değilse cinsiyet seçimine yönlendir
    if not db.get_user_gender(user_id):
        await start_handler(update, context)
        return

    # Buton Basımları
    if text in [BTN_FIND, "🔎 Eşleşme Ara"]:
        await find_partner(update, context, target_gender="ANY")
        return
    elif text == BTN_FIND_GENDER:
        credits = db.get_gender_credits(user_id)
        if credits <= 0:
            await update.message.reply_markdown(
                "⚠️ **Cinsiyet filtreli arama yapabilmek için bakiyenizde hak bulunmuyor.**\n\n"
                "100 Filtreli Eşleşme Hakkını **50 Telegram Yıldızı (~1$)** karşılığında satın alabilirsiniz.",
                reply_markup=MAIN_KEYBOARD
            )
            await buy_credits_handler(update, context)
            return

        await update.message.reply_markdown(
            f"🎯 **Cinsiyete Göre Arama**\n"
            f"Kalan Filtreli Eşleşme Hakkınız: `{credits}`\n\n"
            "Hangi cinsiyette bir partnerle eşleşmek istersiniz?",
            reply_markup=CHOOSE_TARGET_GENDER_KEYBOARD
        )
        return
    elif text == BTN_TARGET_MALE:
        await find_partner(update, context, target_gender="Erkek")
        return
    elif text == BTN_TARGET_FEMALE:
        await find_partner(update, context, target_gender="Kadın")
        return
    elif text == BTN_BUY_CREDITS:
        await buy_credits_handler(update, context)
        return
    elif text in [BTN_CANCEL_QUEUE, BTN_CANCEL]:
        await cancel_queue_handler(update, context)
        return
    elif text == BTN_STOP:
        await stop_chat_handler(update, context)
        return
    elif text == BTN_NEXT:
        await next_partner_handler(update, context)
        return
    elif text == BTN_REPORT:
        await report_handler(update, context)
        return
    elif text == BTN_STATS:
        await stats_handler(update, context)
        return
    elif text == BTN_HELP:
        await start_handler(update, context)
        return

    # Aktif sohbet kontrolü
    partner_id = db.get_active_partner(user_id)
    if partner_id:
        try:
            # Sadece metin mesajını ilet
            await context.bot.send_message(
                chat_id=partner_id,
                text=text
            )
        except Exception as e:
            logger.warning(f"Mesaj iletilemedi ({user_id} -> {partner_id}): {e}")
            db.end_active_chat(user_id)
            await update.message.reply_text(
                "⚠️ Mesajınız iletilemedi. Sohbet ortağınız sohbetten ayrılmış olabilir.",
                reply_markup=MAIN_KEYBOARD
            )
        return

    # Kuyruktaysa
    if db.is_in_queue(user_id):
        await update.message.reply_text(
            "⏳ Hâlâ bir eşleşme bekleniyor... Lütfen eşleşme sağlanana kadar bekleyin.",
            reply_markup=QUEUE_KEYBOARD
        )
        return

    # Sohbet yoksa
    await update.message.reply_text(
        "💡 Şu anda aktif bir sohbetiniz yok.\nEşleşme aramak için aşağıdaki butonları kullanabilirsiniz.",
        reply_markup=MAIN_KEYBOARD
    )

def main():
    """Bot uygulamasını başlatır."""
    db.init_db()
    
    if not config.BOT_TOKEN or config.BOT_TOKEN == "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ":
        print("❌ HATA: Lütfen .env dosyasında geçerli bir BOT_TOKEN tanımlayın!")
        return

    app = ApplicationBuilder().token(config.BOT_TOKEN).build()

    # Komutlar
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", start_handler))
    app.add_handler(CommandHandler("find", lambda u, c: find_partner(u, c, target_gender="ANY")))
    app.add_handler(CommandHandler("stop", stop_chat_handler))
    app.add_handler(CommandHandler("next", next_partner_handler))
    app.add_handler(CommandHandler("report", report_handler))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CommandHandler("buy", buy_credits_handler))

    # Admin Komutları
    app.add_handler(CommandHandler("broadcast", admin_broadcast))
    app.add_handler(CommandHandler("ban", admin_ban))
    app.add_handler(CommandHandler("unban", admin_unban))

    # Ödeme (Telegram Stars) Yakalayıcıları
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    # Medya Engelleme Yakalayıcısı (Fotoğraf, Video, Ses kaydı, Sticker, Dosya vb.)
    media_filter = (
        filters.PHOTO | filters.VIDEO | filters.VOICE | filters.AUDIO | 
        filters.Document.ALL | filters.Sticker.ALL | filters.ANIMATION | 
        filters.VIDEO_NOTE | filters.CONTACT | filters.LOCATION
    )
    app.add_handler(MessageHandler(media_filter, media_block_handler))

    # Yalnızca Yazılı Metin Mesajı Yakalayıcısı
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))

    print("🚀 Anonim Telegram Botu (Medya Korumalı & Telegram Yıldızları Destekli) Çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()

