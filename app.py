from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
import os
import base64
from io import BytesIO
from PIL import Image, ImageOps
from datetime import datetime, timedelta
import urllib.parse
import re
import json
import time

app = Flask(__name__)
app.secret_key = 'samemomomo_secret_key'

products = []
auctions = []
notes = []
reviews = [
    {"id": 1, "name": "محمد أحمد", "rating": 5, "comment": "متجر فخم جداً والقطع أصلية وتوصيل سريع، شكراً لكم!"},
    {"id": 2, "name": "عمر خالد", "rating": 5, "comment": "تجربة شراء ممتازة والتعامل راقي جداً."}
]
product_id_counter = 1
auction_id_counter = 1
note_id_counter = 1
review_id_counter = 3
ADMIN_PASSWORD = "samemomomo**1"

login_attempts = 0
lockout_until = 0

site_stats = {
    "total_visits": 0
}

CART_FILE = "persistent_cart.json"

def load_persistent_cart():
    try:
        if os.path.exists(CART_FILE):
            with open(CART_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_persistent_cart(cart_data):
    try:
        with open(CART_FILE, 'w', encoding='utf-8') as f:
            json.dump(cart_data, f, ensure_ascii=False)
    except Exception:
        pass

def get_user_cart_id():
    if 'user_cart_uuid' not in session:
        import uuid
        session['user_cart_uuid'] = str(uuid.uuid4())
    return session['user_cart_uuid']

def get_cart():
    all_carts = load_persistent_cart()
    uid = get_user_cart_id()
    cart = all_carts.get(uid, [])
    
    updated = False
    for item in cart:
        if not item.get('image') or not item.get('title'):
            prod = next((p for p in products if p['id'] == item['id']), None)
            if prod:
                item['title'] = prod['title']
                item['price'] = prod['price']
                item['image'] = prod['images'][0] if prod['images'] and len(prod['images']) > 0 else ""
                updated = True
    if updated:
        all_carts[uid] = cart
        save_persistent_cart(all_carts)
        
    return cart

def update_cart_in_storage(cart):
    all_carts = load_persistent_cart()
    uid = get_user_cart_id()
    all_carts[uid] = cart
    save_persistent_cart(all_carts)

site_controls = {
    "block_posting": False,  
    "enable_search": True,
    "enable_socials": True,       
    "enable_copyright": True,
    "enable_contact_btn": True,   
    "enable_reviews_page": True,  
    "enable_auctions": True,      
    "enable_cart": True,
    "enable_cod_note": True,
    "enable_forgot_pass": True,
    "enable_scroll_top": True,
    "enable_marquee": True,
    "enable_bg_overlay": True,        
    "currency_symbol": "د.أ",
    "marquee_text": "🔥 أهلاً بكم في متجر عتيق - كل قطعة أصلية ولها حكاية فريدة 🏛️ | توصيل سريع لجميع المحافظات 🚚",
    "cod_note_text": "الدفع عند الاستلام 💵",
    "use_logo_image": False,
    "logo_image": "",
    "logo_size": "130px",
    "enable_logo_pulse": True,
    "logo_animation_style": "rotate",
    "logo_pulse_speed": "3s",
    "logo_pulse_color": "#d97706",
    "admin_whatsapp": "962790000000",
    "social_links": [
        {"name": "إنستغرام", "url": "#"},
        {"name": "تيليجرام", "url": "#"}
    ],
    "copyright_text": "جميع الحقوق محفوظة © عتيق 2026. تم تصميم وتطوير المنصة بعناية فائقة."
}

text_visibility = {
    "settings_btn_text": True,
    "subtitle": True,
    "heading_products": True,
    "no_products": True,
    "heading_auctions": True,
    "toggle_btn_open": True,
    "toggle_btn_close": True,
    "form_main_title": True,
    "label_title": True,
    "input_title_placeholder": True,
    "label_price": True,
    "input_price_placeholder": True,
    "label_quantity": True,
    "input_quantity_placeholder": True,
    "label_description": True,
    "input_description_placeholder": True,
    "label_contact_method": True,
    "contact_type_instagram": True,
    "contact_type_phone": True,
    "input_contact_placeholder": True,
    "upload_text": True,
    "submit_btn": True,
    "back_home": True,
    "view_details": True,
    "search_placeholder": True,
    "contact_word": True,
    "bid_name_label": True,
    "bid_phone_label": True,
    "bid_amount_label": True,
    "bid_submit_btn": True,
    "sort_newest": True,
    "sort_price_low": True,
    "sort_price_high": True
}

site_config = {
    "title": "عتيق | Atiq",
    "subtitle": "لكل قطعة حكاية",
    "bg_image": "",
    "texts": {
        "settings_btn_text": "⚙️ الإعدادات ▼",
        "subtitle": "لكل قطعة حكاية",
        "heading_products": "المنتجات المعروضه",
        "no_products": "لا توجد منتجات معروضة حالياً.",
        "heading_auctions": "🔥 المزادات الحالية المشتعلة",
        "toggle_btn_open": "➕ إضافة قطعة جديدة",
        "toggle_btn_close": "✖ إغلاق القائمة",
        "form_main_title": "أضف قطعة جديدة للمتجر",
        "label_title": "اسم المنتج أو القطعة",
        "input_title_placeholder": "أدخل اسم القطعة",
        "label_price": "السعر",
        "input_price_placeholder": "أدخل الرقم فقط (مثال: 15)",
        "label_quantity": "الكمية المتوفرة",
        "input_quantity_placeholder": "أدخل الكمية (مثال: 1)",
        "label_description": "نبذة أو قصة عن المنتج",
        "input_description_placeholder": "اكتب قصة هذه القطعة أو نبذة عنها...",
        "label_contact_method": "طريقة التواصل",
        "contact_type_instagram": "حساب Instagram",
        "contact_type_phone": "الرقم الخاص بي",
        "input_contact_placeholder": "أدخل حساب الانستغرام أو الرقم",
        "upload_text": "اضغط هنا لاختيار صور المنتج 📸",
        "submit_btn": "نشر المنتج",
        "back_home": "← العودة إلى المتجر الرئيسي",
        "view_details": "عرض التفاصيل",
        "search_placeholder": "🔍 ابحث عن عنصر أو منتج...",
        "contact_word": "شراء",
        "bid_name_label": "اسمك الكريم:",
        "bid_phone_label": "رقم هاتفك للتواصل:",
        "bid_amount_label": "قيمة السعر المقترح للمزايدة:",
        "bid_submit_btn": "تثبيت المزايدة 🚀",
        "sort_newest": "🕒 الأحدث",
        "sort_price_low": "💵 السعر: من الأقل للأعلى",
        "sort_price_high": "📈 السعر: من الأعلى للأقل"
    },
    "colors": {
        "bg_color": "#000000",             
        "title": "#ff5252",                
        "subtitle": "#aaaaaa",             
        "logo_bg": "#000000",              
        "logo_border": "#ef4444",          
        "products_heading": "#ffffff",     
        "no_products": "#777777",          
        "auctions_heading": "#fbbf24",     
        "product_bg": "#111111",           
        "product_title": "#ffffff",        
        "product_price": "#25d366",        
        "whatsapp_btn": "#25d366",         
        "share_btn_color": "#2563eb",      
        "cart_btn": "#dc2626",             
        "toggle_btn": "#25d366",           
        "form_main_title": "#ffffff",      
        "label_title": "#cccccc",          
        "upload_text": "#ffffff",          
        "submit_btn": "#25d366",
        "glow_color": "#25d366",
        "search_bar_bg": "#111111",
        "search_bar_text": "#ffffff",
        "filter_btn_bg": "#111111",
        "filter_btn_text": "#ffffff"
    }
}

color_names_ar = {
    "bg_color": "لون خلفية الموقع العامة",
    "title": "لون عنوان الموقع الرئيسي",
    "logo_bg": "لون خلفية مربع الشعار",
    "logo_border": "لون إطار وتوهج مربع الشعار",
    "subtitle": "لون وصف/شعار الموقع الفرعي",
    "products_heading": "لون عنوان قسم المنتجات المعروضة",
    "no_products": "لون جملة عدم وجود منتجات",
    "auctions_heading": "لون عنوان قسم المزادات",
    "product_bg": "لون خلفية بطاقة/مربع المنتج",
    "product_title": "لون عنوان المنتج",
    "product_price": "لون سعر المنتج والكمية",
    "whatsapp_btn": "لون زر عرض التفاصيل والمشاركة",
    "share_btn_color": "لون ثانوي إضافي",
    "cart_btn": "لون خلفية زر أضف إلى السلة",
    "toggle_btn": "لون زر فتح وإغلاق قائمة الإضافة",
    "form_main_title": "لون عنوان نموذج الإضافة",
    "label_title": "لون عناوين الحقول (Labels)",
    "upload_text": "لون نص اختيار الصور",
    "submit_btn": "لون زر نشر المنتج",
    "glow_color": "لون إضاءة وتوهج سلة المشتريات ✨",
    "search_bar_bg": "لون خلفية شريط البحث",
    "search_bar_text": "لون نص شريط البحث",
    "filter_btn_bg": "لون خلفية زر الفلترة ⌃",
    "filter_btn_text": "لون أيقونة ونصوص زر الفلترة"
}

def get_destination_url(target, encoded_msg=""):
    target = target.strip()
    if target.startswith("http://") or target.startswith("https://"):
        return target
    else:
        clean_num = re.sub(r'[^0-9]', '', target)
        if encoded_msg:
            return f"https://api.whatsapp.com/send?phone={clean_num}&text={encoded_msg}"
        else:
            return f"https://wa.me/{clean_num}"

def format_price(raw_price):
    if not raw_price:
        return ""
    clean_val = str(raw_price).strip()
    curr = site_controls.get("currency_symbol", "د.أ")
    if curr in clean_val:
        return clean_val
    numbers_only = re.sub(r'[^0-9.]', '', clean_val)
    if numbers_only:
        return f"{numbers_only} {curr}"
    return clean_val

product_detail_template = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ product.title }} - {{ config.title }}</title>
    <style>
        body { background-color: {{ config.colors.bg_color }}; color: #ffffff; font-family: Tahoma, sans-serif; margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; }
        .detail-container { background: #111; border: 1px solid #222; border-radius: 14px; padding: 25px; width: 100%; max-width: 600px; box-shadow: 0 4px 25px rgba(0,0,0,0.9); margin-top: 20px; text-align: center; }
        .gallery { display: flex; flex-direction: row; overflow-x: auto; gap: 10px; margin-bottom: 20px; }
        .gallery img { width: 100%; max-height: 500px; object-fit: contain; border-radius: 8px; background: #000; border: 1px solid #333; flex: 0 0 100%; }
        .product-title { font-size: 22px; font-weight: bold; color: {{ config.colors.product_title }}; margin-bottom: 10px; }
        .product-price { font-size: 18px; color: {{ config.colors.product_price }}; font-weight: bold; margin-bottom: 15px; }
        .product-desc { background: #000; border: 1px solid #222; border-radius: 8px; padding: 15px; margin-bottom: 20px; text-align: right; color: #ddd; font-size: 14px; line-height: 1.6; white-space: pre-wrap; }
        .buy-toggle-btn { display: block; text-align: center; background: {{ config.colors.whatsapp_btn }}; color: white; padding: 12px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 15px; margin-bottom: 10px; border: none; width: 100%; cursor: pointer; }
        .share-btn { display: block; text-align: center; background: {{ config.colors.whatsapp_btn }}; color: white; padding: 12px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 15px; margin-bottom: 10px; border: none; width: 100%; cursor: pointer; }
        .checkout-form { display: none; background: #000; border: 1px solid #333; padding: 15px; border-radius: 8px; margin-bottom: 15px; text-align: right; }
        .checkout-form input { width: 100%; padding: 10px; margin-bottom: 10px; border-radius: 6px; border: 1px solid #333; background: #111; color: #fff; box-sizing: border-box; font-size: 13px; outline: none; }
        .checkout-submit { background: #25d366; color: #fff; border: none; width: 100%; padding: 10px; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 14px; }
        .back-link { display: inline-block; color: #25d366; text-decoration: none; font-size: 14px; font-weight: bold; margin-top: 10px; }
        .error-msg { background: rgba(220, 38, 38, 0.1); border: 1px solid #dc2626; color: #ef4444; padding: 8px; border-radius: 6px; text-align: center; font-size: 12px; margin-bottom: 10px; }
        .toast-msg { position: fixed; bottom: 30px; background: #25d366; color: #000; padding: 12px 25px; border-radius: 10px; font-weight: bold; font-size: 14px; box-shadow: 0 5px 15px rgba(0,0,0,0.5); z-index: 1000; display: none; align-items: center; gap: 8px; }
    </style>
</head>
<body>
    <div id="toast" class="toast-msg">✅ تم نسخ رابط المنتج</div>
    <div class="detail-container">
        <h1 class="product-title">{{ product.title }}</h1>
        <div class="product-price">{{ product.price }}</div>
        {% if product.description %}
        <div class="product-desc">
            <b style="color: {{ config.colors.title }}; display: block; margin-bottom: 8px; text-align: right;">قصة القطعة:</b>
            {{ product.description }}
        </div>
        {% endif %}
        <div class="gallery">{% for img in product.images %}<img src="{{ img }}" alt="صورة المنتج">{% endfor %}</div>
        <button class="share-btn" onclick="shareCurrentProduct()">مشاركة هذه القطعة 🔗</button>
        {% if controls.enable_contact_btn and not product.is_sold %}
            <button class="buy-toggle-btn" onclick="toggleCheckout()">{{ config.texts.contact_word }} 🛒</button>
            <div id="checkoutForm" class="checkout-form {% if error %}active{% endif %}" style="display: {% if error %}block{% else %}none{% endif %};">
                <h3 style="color: #fbbf24; font-size: 14px; margin-bottom: 10px;">أدخل بيانات الشخصية لإتمام الشراء:</h3>
                {% if error %}<div class="error-msg">{{ error }}</div>{% endif %}
                <form action="/buy-product/{{ product.id }}" method="POST">
                    <label style="font-size: 12px; color: #ccc;">الاسم الثلاثي:</label><input type="text" name="full_name" placeholder="الاسم الثلاثي" required>
                    <label style="font-size: 12px; color: #ccc;">المحافظة:</label><input type="text" name="province" placeholder="المحافظة (مثال: عمان)" required>
                    <label style="font-size: 12px; color: #ccc;">الشارع:</label><input type="text" name="street" placeholder="اسم الشارع أو المنطقة" required>
                    <label style="font-size: 12px; color: #ccc;">رقم الهاتف للتواصل:</label><input type="text" name="phone" placeholder="رقم الهاتف (أرقام فقط)" oninput="this.value = this.value.replace(/[^0-9]/g, '')" required>
                    {% if controls.enable_cod_note and controls.cod_note_text %}
                        <div style="font-size: 12px; color: #fbbf24; margin-bottom: 12px; text-align: right; font-weight: bold;">{{ controls.cod_note_text }}</div>
                    {% endif %}
                    <button type="submit" class="checkout-submit">إرسال الطلب عبر الواتساب 🚀</button>
                </form>
            </div>
        {% endif %}
        {% if controls.enable_cart and not product.is_sold %}
            <button type="button" class="buy-toggle-btn" style="background: {{ config.colors.cart_btn }}; margin-bottom: 15px;" onclick="addToCart({{ product.id }})">أضف إلى السلة 🛒</button>
        {% elif product.is_sold %}
            <p style="color: #dc2626; font-weight: bold; margin-bottom: 15px;">عذراً، هذا المنتج تم بيعه.</p>
        {% endif %}
        {% if vis.back_home %}<a href="/" class="back-link">{{ config.texts.back_home }}</a>{% endif %}
    </div>
    <script>
        function shareCurrentProduct() {
            const productUrl = window.location.href;
            const shareText = `شاهد هذه القطعة المميزة من متجر عتيق:\n📌 {{ product.title }}\n💰 السعر: {{ product.price }}\n🔗 الرابط: ${productUrl}`;
            if (navigator.share) { navigator.share({ title: '{{ product.title }}', text: shareText, url: productUrl }).catch(() => {}); }
            else {
                navigator.clipboard.writeText(shareText);
                const toast = document.getElementById('toast');
                toast.innerText = "✅ تم نسخ تفاصيل ورابط القطعة للمشاركة!";
                toast.style.display = 'flex';
                setTimeout(() => { toast.style.display = 'none'; }, 3000);
            }
        }
        function toggleCheckout() {
            const form = document.getElementById('checkoutForm');
            if (form.style.display === 'block') { form.style.display = 'none'; }
            else { form.style.display = 'block'; form.scrollIntoView({ behavior: 'smooth' }); }
        }
        function addToCart(productId) {
            fetch('/add-to-cart-ajax/' + productId, { method: 'POST', credentials: 'same-origin' })
            .then(response => response.json())
            .then(data => {
                const toast = document.getElementById('toast');
                if(data.success) { toast.innerText = "✅ تم الإضافة إلى السلة"; toast.style.background = "#25d366"; toast.style.color = "#000"; }
                else { toast.innerText = "⚠️ هذا المنتج مضاف مسبقاً في السلة"; toast.style.background = "#dc2626"; toast.style.color = "#fff"; }
                toast.style.display = 'flex';
                setTimeout(() => { toast.style.display = 'none'; }, 3000);
            });
        }
    </script>
</body>
</html>
"""

cart_template = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سلة المشتريات - {{ config.title }}</title>
    <style>
        body { background: {{ config.colors.bg_color }}; color: #fff; font-family: Tahoma, sans-serif; padding: 20px; display: flex; flex-direction: column; align-items: center; min-height: 100vh; box-sizing: border-box; }
        .full-screen-container { width: 100%; max-width: 100%; box-sizing: border-box; display: flex; flex-direction: column; justify-content: space-between; min-height: calc(100vh - 40px); }
        h1 { color: #dc2626; text-align: center; font-size: 24px; margin-bottom: 25px; text-shadow: 0 0 15px {{ config.colors.glow_color }}; }
        .cart-items-wrapper { width: 100%; max-width: 950px; margin: 0 auto; display: flex; flex-direction: column; gap: 15px; }
        .cart-item { display: flex; justify-content: space-between; align-items: center; background: #0a0a0a; padding: 14px 18px; border-radius: 10px; border: 1px solid #222; box-shadow: 0 0 20px {{ config.colors.glow_color }}; gap: 12px; }
        .cart-item-left { display: flex; align-items: center; gap: 15px; flex: 1; text-decoration: none; }
        .cart-item-img { width: 65px; height: 65px; object-fit: cover; border-radius: 8px; border: 1px solid #333; background: #000; flex-shrink: 0; }
        .cart-item-info { display: flex; flex-direction: column; gap: 4px; }
        .cart-item-title { font-size: 16px; font-weight: bold; color: #fff; }
        .cart-item-price { font-size: 14px; color: #25d366; font-weight: bold; }
        .delete-btn { background: #dc2626; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: bold; flex-shrink: 0; }
        .back-area { width: 100%; max-width: 950px; margin: 30px auto 10px auto; text-align: center; }
        .back { display: inline-block; color: #25d366; text-decoration: none; font-weight: bold; font-size: 15px; }
    </style>
</head>
<body>
    <div class="full-screen-container">
        <div class="cart-items-wrapper">
            <h1>🛒 سلة المشتريات الخاصة بك</h1>
            {% if cart_items|length == 0 %}
                <p style="color: #888; text-align: center; padding: 50px; font-size: 16px;">السلة فارغة حالياً.</p>
            {% else %}
                {% for item in cart_items %}
                    <div class="cart-item">
                        <a href="/product/{{ item.id }}" class="cart-item-left">
                            {% if item.image %}<img src="{{ item.image }}" alt="صورة المنتج" class="cart-item-img">{% endif %}
                            <div class="cart-item-info">
                                <div class="cart-item-title">{{ item.title }}</div>
                                <div class="cart-item-price">{{ item.price }}</div>
                            </div>
                        </a>
                        <form action="/remove-from-cart/{{ item.cart_id }}" method="POST" style="margin:0;"><button type="submit" class="delete-btn">حذف</button></form>
                    </div>
                {% endfor %}
            {% endif %}
        </div>
        <div class="back-area"><a href="/" class="back">← العودة إلى المتجر الرئيسي</a></div>
    </div>
</body>
</html>
"""

default_html_template = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ config.title }}</title>
    <style>
        body { background-color: {{ config.colors.bg_color }}; {% if config.bg_image %}background-image: url('{{ config.bg_image }}'); background-size: cover; background-position: center; background-attachment: fixed; {% endif %} font-family: Tahoma, sans-serif; margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; min-height: 100vh; box-sizing: border-box; }
        {% if config.bg_image and controls.enable_bg_overlay %}body::before { content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.75); z-index: -1; }{% endif %}
        
        .marquee-bar { width: 100%; max-width: 900px; background: rgba(217, 119, 6, 0.15); border: 1px solid #d97706; color: #fbbf24; padding: 8px 0; border-radius: 8px; margin-bottom: 20px; overflow: hidden; white-space: nowrap; box-sizing: border-box; font-size: 13px; font-weight: bold; }
        .marquee-content { display: inline-block; animation: marqueeAnim 20s linear infinite; padding-left: 100%; }
        @keyframes marqueeAnim { 0% { transform: translate(0, 0); } 100% { transform: translate(-100%, 0); } }

        .top-bar { width: 100%; max-width: 900px; display: flex; justify-content: flex-end; align-items: center; margin-bottom: 15px; position: relative; }
        .dropdown { position: relative; display: inline-block; }
        .settings-btn { background: #111111; border: 1px solid #333333; padding: 10px 18px; border-radius: 12px; text-decoration: none; color: #ffffff; font-size: 13px; font-weight: bold; cursor: pointer; display: inline-block; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        .settings-btn:hover { background: #1a1a1a; border-color: #25d366; }
        .dropdown-content { display: none; position: absolute; left: 0; background-color: #111; min-width: 190px; box-shadow: 0px 8px 16px rgba(0,0,0,0.5); border: 1px solid #333; border-radius: 8px; z-index: 10; overflow: hidden; margin-top: 5px; }
        .dropdown-content a { color: #fff; padding: 10px 14px; text-decoration: none; display: flex; justify-content: space-between; align-items: center; font-size: 13px; text-align: right; border-bottom: 1px solid #222; }
        .dropdown-content a:last-child { border-bottom: none; }
        .dropdown-content a:hover { background-color: #222; color: #25d366; }
        .show { display: block; }
        .cart-badge { background: {{ config.colors.cart_btn }}; color: white; border-radius: 50%; padding: 2px 6px; font-size: 11px; font-weight: bold; }

        .toast-msg { position: fixed; bottom: 30px; background: #25d366; color: #000; padding: 12px 25px; border-radius: 10px; font-weight: bold; font-size: 14px; box-shadow: 0 5px 15px rgba(0,0,0,0.5); z-index: 1000; display: none; align-items: center; gap: 8px; }

        .header { text-align: center; margin-bottom: 25px; }
        .glass-title { background: {{ config.colors.logo_bg }}; border: 2px solid {{ config.colors.logo_border }}; display: inline-block; padding: 12px 25px; border-radius: 14px; color: {{ config.colors.title }}; font-size: 28px; font-weight: bold; margin: 0; }
        
        @keyframes rotatingGlow {
            0% { box-shadow: 0 0 15px {{ controls.logo_pulse_color }}, 10px 0 25px rgba(217, 119, 6, 0.4); }
            33% { box-shadow: 0 0 20px {{ controls.logo_pulse_color }}, 0 10px 25px rgba(217, 119, 6, 0.4); }
            66% { box-shadow: 0 0 15px {{ controls.logo_pulse_color }}, -10px 0 25px rgba(217, 119, 6, 0.4); }
            100% { box-shadow: 0 0 15px {{ controls.logo_pulse_color }}, 10px 0 25px rgba(217, 119, 6, 0.4); }
        }

        @keyframes classicPulse {
            0% { box-shadow: 0 0 10px {{ controls.logo_pulse_color }}; }
            50% { box-shadow: 0 0 25px {{ controls.logo_pulse_color }}, 0 0 40px {{ controls.logo_pulse_color }}; }
            100% { box-shadow: 0 0 10px {{ controls.logo_pulse_color }}; }
        }

        @keyframes flashPulse {
            0% { box-shadow: 0 0 5px {{ controls.logo_pulse_color }}; opacity: 0.8; }
            50% { box-shadow: 0 0 30px {{ controls.logo_pulse_color }}; opacity: 1; }
            100% { box-shadow: 0 0 5px {{ controls.logo_pulse_color }}; opacity: 0.8; }
        }

        .logo-img-container { 
            display: inline-block; 
            background: {{ config.colors.logo_bg }}; 
            border: 2px solid {{ config.colors.logo_border }}; 
            border-radius: 50%; 
            padding: 5px; 
            width: {{ controls.logo_size }}; 
            height: {{ controls.logo_size }}; 
            overflow: hidden; 
            box-sizing: border-box; 
            {% if controls.enable_logo_pulse %}
                {% if controls.logo_animation_style == 'rotate' %}
                    animation: rotatingGlow {{ controls.logo_pulse_speed }} infinite linear;
                {% elif controls.logo_animation_style == 'pulse' %}
                    animation: classicPulse {{ controls.logo_pulse_speed }} infinite ease-in-out;
                {% elif controls.logo_animation_style == 'flash' %}
                    animation: flashPulse {{ controls.logo_pulse_speed }} infinite steps(2, start);
                {% endif %}
            {% endif %}
        }
        .logo-img-container img { width: 100%; height: 100%; object-fit: cover; border-radius: 50%; display: block; }
        .header p { color: {{ config.colors.subtitle }}; font-size: 13px; margin: 10px 0 0 0; }
        
        .search-filter-bar { width: 100%; max-width: 900px; margin-bottom: 20px; display: flex; gap: 10px; align-items: center; box-sizing: border-box; }
        .search-input { flex: 1; height: 46px; padding: 0 18px; background: {{ config.colors.search_bar_bg }}; color: {{ config.colors.search_bar_text }}; border: 1px solid #333; border-radius: 10px; font-size: 14px; box-sizing: border-box; outline: none; }
        
        .filter-dropdown-container { position: relative; display: inline-block; height: 46px; }
        .filter-icon-btn { background: {{ config.colors.filter_btn_bg }}; color: {{ config.colors.filter_btn_text }}; border: 1px solid #333; width: 46px; height: 46px; border-radius: 10px; font-size: 18px; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center; box-sizing: border-box; }
        .filter-icon-btn:hover { border-color: #25d366; }
        .filter-content { display: none; position: absolute; left: 0; background-color: #111; min-width: 210px; box-shadow: 0px 8px 16px rgba(0,0,0,0.8); border: 1px solid #333; border-radius: 8px; z-index: 10; overflow: hidden; margin-top: 5px; }
        .filter-content div { color: {{ config.colors.filter_btn_text }}; padding: 10px 14px; cursor: pointer; font-size: 13px; text-align: right; border-bottom: 1px solid #222; }
        .filter-content div:last-child { border-bottom: none; }
        .filter-content div:hover { background-color: #222; color: #25d366; }
        .filter-show { display: block; }

        .auctions-section { width: 100%; max-width: 900px; margin-bottom: 30px; }
        .auction-card { background: #151515; border: 1px solid #d97706; border-radius: 12px; padding: 15px; margin-bottom: 15px; display: flex; flex-direction: column; gap: 10px; }
        .auction-header { display: flex; justify-content: space-between; align-items: center; }
        .auction-title { font-size: 16px; font-weight: bold; color: #fbbf24; }
        .auction-timer { background: rgba(217, 119, 6, 0.2); border: 1px solid #d97706; color: #fbbf24; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: bold; }
        .auction-images { display: flex; flex-direction: row; overflow-x: auto; gap: 8px; background: #000; padding: 8px; width: 100%; box-sizing: border-box; border-radius: 8px; margin-bottom: 5px; }
        .auction-images img { width: 100%; max-height: 200px; object-fit: contain; border-radius: 6px; flex: 0 0 100%; background: #000; }
        .auction-details { font-size: 13px; color: #ccc; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px; }
        .bid-btn { background: #d97706; color: white; border: none; padding: 8px; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 13px; text-align: center; text-decoration: none; display: block; }

        .products-section { width: 100%; max-width: 900px; margin-bottom: 20px; flex: 1; }
        .products-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; width: 100%; }
        @media (min-width: 768px) { .products-grid { grid-template-columns: repeat(4, 1fr); } }
        
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .product-card { background: {{ config.colors.product_bg }}; border: 1px solid #222222; border-radius: 10px; overflow: hidden; display: flex; flex-direction: column; justify-content: space-between; text-decoration: none; position: relative; animation: fadeInUp 0.6s ease-out forwards; }
        
        .product-card.sold-card { opacity: 0.65; }
        .sold-badge { position: absolute; top: 10px; right: 10px; background: #dc2626; color: white; padding: 4px 10px; font-size: 11px; font-weight: bold; border-radius: 4px; z-index: 2; }
        .product-images { display: flex; flex-direction: row; overflow-x: auto; gap: 8px; background: #000; padding: 8px; width: 100%; box-sizing: border-box; }
        .product-images img { width: 100%; height: 140px; object-fit: cover; border-radius: 6px; flex: 0 0 100%; }
        .product-info { padding: 12px; }
        .product-title { font-size: 14px; font-weight: bold; margin-bottom: 5px; color: {{ config.colors.product_title }}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .product-price { color: {{ config.colors.product_price }}; font-weight: bold; margin-bottom: 8px; font-size: 13px; }
        
        .card-buttons { display: flex; flex-direction: column; gap: 6px; }
        
        .contact-btn-wrapper { display: flex; align-items: stretch; width: 100%; border-radius: 6px; overflow: hidden; background: {{ config.colors.whatsapp_btn }}; }
        .contact-btn { display: flex; align-items: center; justify-content: center; text-align: center; color: white; padding: 7px 10px; text-decoration: none; font-weight: bold; font-size: 11px; flex: 1; border: none; background: transparent; cursor: pointer; box-sizing: border-box; }
        .inline-share-btn { display: flex; align-items: center; justify-content: center; background: transparent; color: white; padding: 7px 12px; border: none; cursor: pointer; text-decoration: none; box-sizing: border-box; border-right: 1px solid rgba(255,255,255,0.25); }
        .inline-share-btn svg { width: 14px; height: 14px; fill: currentColor; }

        .add-to-cart-btn { background: {{ config.colors.cart_btn }}; color: white; border: none; padding: 7px; border-radius: 6px; font-weight: bold; font-size: 11px; cursor: pointer; text-align: center; width: 100%; text-decoration: none; box-sizing: border-box; }
        .sold-btn-disabled { background: #555 !important; }

        .scroll-top-btn { display: none; position: fixed; bottom: 25px; right: 25px; background: {{ config.colors.whatsapp_btn }}; color: #fff; width: 42px; height: 42px; border-radius: 50%; border: 2px solid #fff; font-size: 18px; font-weight: bold; cursor: pointer; z-index: 500; align-items: center; justify-content: center; box-shadow: 0 4px 15px rgba(0,0,0,0.6); }

        .pagination { display: flex; justify-content: center; gap: 8px; margin: 30px 0 15px 0; flex-wrap: wrap; }
        .page-link { background: #111; border: 1px solid #333; color: #fff; padding: 8px 14px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: bold; }
        .page-link.active { background: #25d366; border-color: #25d366; color: #000; }
        .page-link:hover:not(.active) { background: #222; }

        .toggle-form-btn { background-color: {{ config.colors.toggle_btn }}; color: white; border: 2px solid #ffffff; padding: 12px 25px; border-radius: 10px; font-size: 16px; font-weight: bold; cursor: pointer; margin-bottom: 25px; }
        .container { background: #111111; border: 1px solid #222; border-radius: 12px; padding: 20px; width: 100%; max-width: 600px; margin-bottom: 30px; display: none; }
        .container.active { display: block; }
        .form-main-title { color: {{ config.colors.form_main_title }}; font-size: 18px; text-align: center; margin-bottom: 20px; }
        .input-group { margin-bottom: 15px; }
        .input-group label { display: block; margin-bottom: 5px; font-size: 13px; color: {{ config.colors.label_title }}; }
        .input-group input, .input-group textarea, .input-group select { width: 100%; padding: 12px; border: 1px solid #333; border-radius: 8px; background: #000; color: white; font-size: 14px; box-sizing: border-box; outline: none; margin-bottom: 8px; }
        .file-upload { border: 2px dashed #25d366; border-radius: 8px; padding: 15px; text-align: center; background: rgba(37, 211, 102, 0.03); cursor: pointer; margin-bottom: 10px; color: {{ config.colors.upload_text }}; font-size: 13px; }
        .submit-btn { background-color: {{ config.colors.submit_btn }}; color: white; border: none; width: 100%; padding: 12px; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; }
        .error-msg { background: rgba(220, 38, 38, 0.1); border: 1px solid #dc2626; color: #ef4444; padding: 10px; border-radius: 8px; text-align: center; font-size: 13px; margin-bottom: 15px; }

        .site-footer { width: 100%; max-width: 900px; margin-top: 40px; padding: 20px 0; border-top: 1px solid #222; display: flex; flex-direction: column; align-items: center; gap: 12px; text-align: center; }
        .footer-socials { display: flex; gap: 15px; flex-wrap: wrap; justify-content: center; }
        .footer-social-link { color: #aaa; text-decoration: none; font-size: 13px; background: #111; padding: 6px 14px; border-radius: 6px; border: 1px solid #222; }
        .footer-copyright { color: #666; font-size: 12px; text-decoration: none; }
    </style>
</head>
<body>
    <div id="toast" class="toast-msg">✅ تم نسخ رابط المنتج</div>

    {% if controls.enable_scroll_top %}
    <button id="scrollTopBtn" class="scroll-top-btn" onclick="scrollToTop()" title="العودة للأعلى">▲</button>
    {% endif %}

    {% if controls.enable_marquee and controls.marquee_text %}
    <div class="marquee-bar">
        <div class="marquee-content">{{ controls.marquee_text }}</div>
    </div>
    {% endif %}

    <div class="top-bar">
        <div class="dropdown">
            {% if vis.settings_btn_text %}<button onclick="toggleDropdown()" class="settings-btn">{{ config.texts.settings_btn_text }}</button>{% endif %}
            <div id="settingsDropdown" class="dropdown-content">
                {% if controls.enable_cart %}
                    <a href="/cart">🛒 سلة المشتريات <span class="cart-badge">{{ cart_count }}</span></a>
                {% endif %}
                {% if controls.enable_reviews_page %}<a href="/reviews">⭐ آراء العملاء</a>{% endif %}
                {% if controls.enable_copyright %}<a href="/copyright">📄 حقوق النشر والشروط</a>{% endif %}
                <a href="/admin" style="color: #25d366; font-weight: bold;">🔐 لوحة التحكم</a>
            </div>
        </div>
    </div>
    <div class="header">
        {% if controls.use_logo_image and controls.logo_image %}
            <div class="logo-img-container"><img src="{{ controls.logo_image }}" alt="شعار الموقع"></div>
        {% else %}
            <h1 class="glass-title">{{ config.title }}</h1>
        {% endif %}
        {% if vis.subtitle %}<p>{{ config.texts.subtitle }}</p>{% endif %}
    </div>
    
    {% if controls.enable_search and vis.search_placeholder %}
    <div class="search-filter-bar">
        <input type="text" id="searchInput" class="search-input" placeholder="{{ config.texts.search_placeholder }}" onkeyup="filterAndSortProducts()">
        <div class="filter-dropdown-container">
            <button type="button" class="filter-icon-btn" onclick="toggleFilterMenu()" title="ترتيب المنتجات">⌃</button>
            <div id="filterMenu" class="filter-content">
                {% if vis.sort_newest %}<div onclick="selectSort('newest', '{{ config.texts.sort_newest }}')">{{ config.texts.sort_newest }}</div>{% endif %}
                {% if vis.sort_price_low %}<div onclick="selectSort('price-low', '{{ config.texts.sort_price_low }}')">{{ config.texts.sort_price_low }}</div>{% endif %}
                {% if vis.sort_price_high %}<div onclick="selectSort('price-high', '{{ config.texts.sort_price_high }}')">{{ config.texts.sort_price_high }}</div>{% endif %}
            </div>
        </div>
        <input type="hidden" id="sortValue" value="newest">
    </div>
    {% endif %}

    {% if controls.enable_auctions and auctions|length > 0 %}
    <div class="auctions-section">
        {% if vis.heading_auctions %}<h2 style="color: {{ config.colors.auctions_heading }}; margin-bottom: 15px; text-align: right; font-size: 18px;">{{ config.texts.heading_auctions }}</h2>{% endif %}
        {% for a in auctions %}
        <div class="auction-card">
            <div class="auction-header">
                <span class="auction-title">🏷️ {{ a.title }}</span>
                <span class="auction-timer" data-end="{{ a.end_time }}">⏳ جاري التحميل...</span>
            </div>
            {% if a.images and a.images|length > 0 %}
            <div class="auction-images">{% for img in a.images %}<img src="{{ img }}" alt="صورة المزاد">{% endfor %}</div>
            {% endif %}
            <div class="auction-details">
                <span>السعر الحالي: 
                    {% if a.bids and a.bids|length > 0 %}
                        {% set sorted_bids = a.bids|sort(attribute='raw_amount', reverse=True) %}
                        <select style="background: #000; color: #25d366; border: 1px solid #333; padding: 4px 8px; border-radius: 6px; font-weight: bold; outline: none;">
                            <option value="{{ sorted_bids[0].amount }}">{{ sorted_bids[0].amount }} (بواسطة: {{ sorted_bids[0].name }})</option>
                            {% for b in sorted_bids[1:] %}<option value="{{ b.amount }}">{{ b.amount }} (بواسطة: {{ b.name }})</option>{% endfor %}
                        </select>
                    {% else %}
                        <b style="color: #25d366;">{{ a.current_price }}</b>
                    {% endif %}
                </span>
                <span>الحد الأدنى للمزايدة: <b>{{ a.min_bid }}</b></span>
                {% if a.max_price %}<span>الحد الأقصى (الشراء الفوري): <b style="color: #ff5252;">{{ a.max_price }}</b></span>{% endif %}
            </div>
            <a href="/auction/{{ a.id }}" class="bid-btn">مشاركة وعرض تفاصيل المزاد 🔨</a>
        </div>
        {% endfor %}
    </div>
    {% endif %}

    <div class="products-section">
        {% if vis.heading_products %}<h2 style="color: {{ config.colors.products_heading }}; margin-bottom: 15px; text-align: right;">{{ config.texts.heading_products }}</h2>{% endif %}
        <div class="products-grid" id="productsGrid">
            {% if products|length == 0 and vis.no_products %}<p style="color: {{ config.colors.no_products }}; text-align: center; grid-column: 1 / -1; padding: 20px;">{{ config.texts.no_products }}</p>{% endif %}
            {% for p in page_products %}
                <div class="product-card {% if p.is_sold %}sold-card{% endif %}" data-title="{{ p.title }}" data-price="{{ p.numeric_price }}" data-id="{{ p.id }}">
                    {% if p.is_sold %}<div class="sold-badge">تم البيع</div>{% endif %}
                    <div class="product-images">{% for img in p.images %}<img src="{{ img }}" alt="صورة">{% endfor %}</div>
                    <div class="product-info">
                        <div class="product-title" title="{{ p.title }}">{{ p.title }}</div>
                        <div class="product-price">{{ p.price }}</div>
                        <div class="card-buttons">
                            {% if vis.view_details %}
                                <div class="contact-btn-wrapper">
                                    <a href="/product/{{ p.id }}" class="contact-btn {% if p.is_sold %}sold-btn-disabled{% endif %}">
                                        {% if p.is_sold %}تم البيع{% else %}{{ config.texts.view_details }}{% endif %}
                                    </a>
                                    <button type="button" class="inline-share-btn {% if p.is_sold %}sold-btn-disabled{% endif %}" onclick="quickShareProduct('{{ p.title | replace("'", "\\'") }}', '{{ p.price }}', '/product/{{ p.id }}')" title="مشاركة القطعة">
                                        <svg viewBox="0 0 24 24"><path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92c0-1.61-1.31-2.92-2.92-2.92z"/></svg>
                                    </button>
                                </div>
                            {% endif %}
                            {% if controls.enable_cart and not p.is_sold %}
                                <button type="button" class="add-to-cart-btn" onclick="addToCart({{ p.id }})">أضف إلى السلة 🛒</button>
                            {% endif %}
                        </div>
                    </div>
                </div>
            {% endfor %}
        </div>
        {% if total_pages > 1 %}
        <div class="pagination" id="paginationSection">
            {% for p_num in range(1, total_pages + 1) %}<a href="/?page={{ p_num }}" class="page-link {% if p_num == current_page %}active{% endif %}">{{ p_num }}</a>{% endfor %}
        </div>
        {% endif %}
    </div>

    {% if not controls.block_posting and (vis.toggle_btn_open or vis.toggle_btn_close) %}
    <button class="toggle-form-btn" onclick="toggleForm()" id="toggleBtn">{{ config.texts.toggle_btn_open }}</button>
    <div class="container {% if error %}active{% endif %}" id="formContainer">
        {% if vis.form_main_title %}<h2 class="form-main-title">{{ config.texts.form_main_title }}</h2>{% endif %}
        {% if error %}<div class="error-msg">{{ error }}</div>{% endif %}
        <form action="/add" method="POST" enctype="multipart/form-data">
            <div class="input-group">
                {% if vis.label_title %}<label style="color: {{ config.colors.label_title }};">{{ config.texts.label_title }}</label>{% endif %}
                <input type="text" name="title" {% if vis.input_title_placeholder %}placeholder="{{ config.texts.input_title_placeholder }}"{% endif %} required>
            </div>
            <div class="input-group">
                {% if vis.label_price %}<label style="color: {{ config.colors.label_title }};">{{ config.texts.label_price }} ({{ controls.currency_symbol }})</label>{% endif %}
                <input type="text" name="price" {% if vis.input_price_placeholder %}placeholder="{{ config.texts.input_price_placeholder }}"{% endif %}>
            </div>
            <div class="input-group">
                <label style="color: {{ config.colors.label_title }};">{{ config.texts.label_quantity }}</label>
                <input type="text" name="quantity" placeholder="{{ config.texts.input_quantity_placeholder }}" value="1">
            </div>
            <div class="input-group">
                <label style="color: {{ config.colors.label_title }};">{{ config.texts.label_description }}</label>
                <textarea name="description" rows="3" placeholder="{{ config.texts.input_description_placeholder }}"></textarea>
            </div>
            {% if vis.upload_text %}
            <div class="file-upload" onclick="document.getElementById('imagesInput').click();">
                {{ config.texts.upload_text }}
                <input type="file" id="imagesInput" name="images" multiple accept="image/*" style="display: none;" onchange="showCount(this)">
            </div>
            <div id="file-count" style="font-size: 12px; color: #aaa; margin-bottom: 15px; text-align: center;"></div>
            {% endif %}
            {% if vis.submit_btn %}<button type="submit" class="submit-btn">{{ config.texts.submit_btn }}</button>{% endif %}
        </form>
    </div>
    {% endif %}

    {% if controls.enable_socials or controls.enable_copyright %}
    <footer class="site-footer">
        {% if controls.enable_socials and controls.social_links|length > 0 %}
        <div class="footer-socials">{% for s in controls.social_links %}<a href="{{ s.url }}" target="_blank" class="footer-social-link">{{ s.name }}</a>{% endfor %}</div>
        {% endif %}
        {% if controls.enable_copyright %}<a href="/copyright" class="footer-copyright">حقوق النشر والشروط</a>{% endif %}
    </footer>
    {% endif %}
    <script>
        // حفظ واسترجاع موضع التمرير تلقائياً عند تصفح المنتجات والعودة
        window.addEventListener('beforeunload', function() {
            sessionStorage.setItem('scrollPosition', window.scrollY);
        });

        window.addEventListener('load', function() {
            const savedPosition = sessionStorage.getItem('scrollPosition');
            if (savedPosition !== null) {
                window.scrollTo(0, parseInt(savedPosition));
                sessionStorage.removeItem('scrollPosition');
            }
        });

        const scrollBtn = document.getElementById('scrollTopBtn');
        let isAutoScrolling = false;

        window.addEventListener('scroll', () => {
            if (scrollBtn) {
                if (window.scrollY > 300) { scrollBtn.style.display = 'flex'; }
                else { scrollBtn.style.display = 'none'; }
            }
        });

        // إيقاف الصعود التلقائي فوراً عند أي تفاعل أو نقر من المستخدم
        ['wheel', 'touchstart', 'mousedown', 'keydown'].forEach(eventType => {
            window.addEventListener(eventType, () => {
                if (isAutoScrolling) {
                    isAutoScrolling = false;
                }
            }, { passive: true });
        });

        function scrollToTop() {
            isAutoScrolling = true;
            const targetPosition = 0;
            const startPosition = window.pageYOffset;
            const distance = targetPosition - startPosition;
            const duration = 800; // مدة الصعود بالمللي ثانية
            let startTime = null;

            function animation(currentTime) {
                if (!startTime) startTime = currentTime;
                const timeElapsed = currentTime - startTime;
                const run = ease(timeElapsed, startPosition, distance, duration);
                window.scrollTo(0, run);

                if (isAutoScrolling && timeElapsed < duration && window.pageYOffset > 0) {
                    requestAnimationFrame(animation);
                } else {
                    isAutoScrolling = false;
                }
            }

            function ease(t, b, c, d) {
                t /= d / 2;
                if (t < 1) return c / 2 * t * t + b;
                t--;
                return -c / 2 * (t * (t - 2) - 1) + b;
            }

            requestAnimationFrame(animation);
        }

        function quickShareProduct(title, price, path) {
            event.stopPropagation();
            const productUrl = window.location.origin + path;
            const shareText = `شاهد هذه القطعة المميزة من متجر عتيق:\n📌 ${title}\n💰 السعر: ${price}\n🔗 الرابط: ${productUrl}`;
            if (navigator.share) { navigator.share({ title: title, text: shareText, url: productUrl }).catch(() => {}); }
            else {
                navigator.clipboard.writeText(shareText);
                const toast = document.getElementById('toast');
                toast.innerText = "✅ تم نسخ تفاصيل ورابط القطعة للمشاركة!";
                toast.style.display = 'flex';
                setTimeout(() => { toast.style.display = 'none'; }, 3000);
            }
        }

        function toggleFilterMenu() { document.getElementById("filterMenu").classList.toggle("filter-show"); }
        function selectSort(sortType, sortName) { document.getElementById("sortValue").value = sortType; document.getElementById("filterMenu").classList.remove("filter-show"); filterAndSortProducts(); }
        window.addEventListener('click', function(e) {
            if (!e.target.closest('.filter-dropdown-container')) {
                var menu = document.getElementById("filterMenu");
                if (menu && menu.classList.contains('filter-show')) { menu.classList.remove('filter-show'); }
            }
        });
        function addToCart(productId) {
            fetch('/add-to-cart-ajax/' + productId, { method: 'POST', credentials: 'same-origin' })
            .then(response => response.json())
            .then(data => {
                const toast = document.getElementById('toast');
                if(data.success) { toast.innerText = "✅ تم الإضافة إلى السلة"; toast.style.background = "#25d366"; toast.style.color = "#000"; }
                else { toast.innerText = "⚠️ هذا المنتج مضاف مسبقاً في السلة"; toast.style.background = "#dc2626"; toast.style.color = "#fff"; }
                toast.style.display = 'flex';
                setTimeout(() => { toast.style.display = 'none'; }, 3000);
            });
        }
        function toggleDropdown() { document.getElementById("settingsDropdown").classList.toggle("show"); }
        window.onclick = function(event) {
            if (!event.target.matches('.settings-btn') && !event.target.closest('.settings-btn')) {
                var dropdowns = document.getElementsByClassName("dropdown-content");
                for (var i = 0; i < dropdowns.length; i++) {
                    var openDropdown = dropdowns[i];
                    if (openDropdown.classList.contains('show')) { openDropdown.classList.remove('show'); }
                }
            }
        }
        function updateTimers() {
            const timers = document.querySelectorAll('.auction-timer');
            timers.forEach(timer => {
                const endTime = new Date(timer.getAttribute('data-end')).getTime();
                const now = new Date().getTime();
                const distance = endTime - now;
                if (distance < 0) { timer.innerHTML = " انتهى المزاد ❌"; }
                else {
                    const days = Math.floor(distance / (1000 * 60 * 60 * 24));
                    const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                    const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                    const seconds = Math.floor((distance % (1000 * 60)) / 1000);
                    timer.innerHTML = `⏳ متبقي: ${days} يوم و ${hours}س ${minutes}د ${seconds}ث`;
                }
            });
        }
        setInterval(updateTimers, 1000);
        updateTimers();

        function toggleForm() {
            const container = document.getElementById('formContainer');
            const btn = document.getElementById('toggleBtn');
            if (container.style.display === 'block') { container.style.display = 'none'; btn.innerText = '{{ config.texts.toggle_btn_open }}'; }
            else { container.style.display = 'block'; btn.innerText = '{{ config.texts.toggle_btn_close }}'; container.scrollIntoView({ behavior: 'smooth' }); }
        }
        window.onload = function() {
            {% if error %}
                const container = document.getElementById('formContainer');
                if(container) { container.style.display = 'block'; document.getElementById('toggleBtn').innerText = '{{ config.texts.toggle_btn_close }}'; }
            {% endif %}
        };
        function showCount(input) { if(input.files.length > 0) { document.getElementById('file-count').innerText = "✅ تم اختيار " + input.files.length + " صورة."; } }
        
        function filterAndSortProducts() {
            const searchInput = document.getElementById('searchInput');
            const sortInput = document.getElementById('sortValue');
            const grid = document.getElementById('productsGrid');
            const pagination = document.getElementById('paginationSection');
            if(!grid) return;
            const filter = searchInput ? searchInput.value.toLowerCase() : '';
            const sortVal = sortInput ? sortInput.value : 'newest';
            const cards = Array.from(grid.getElementsByClassName('product-card'));
            if (pagination) { pagination.style.display = (filter !== '' || sortVal !== 'newest') ? 'none' : 'flex'; }
            cards.forEach(card => {
                const title = card.getAttribute('data-title').toLowerCase();
                card.style.display = title.includes(filter) ? "" : "none";
            });
            cards.sort((a, b) => {
                const priceA = parseFloat(a.getAttribute('data-price')) || 0;
                const priceB = parseFloat(b.getAttribute('data-price')) || 0;
                const idA = parseInt(a.getAttribute('data-id')) || 0;
                const idB = parseInt(b.getAttribute('data-id')) || 0;
                if (sortVal === 'price-low') { return priceA - priceB; }
                else if (sortVal === 'price-high') { return priceB - priceA; }
                else { return idB - idA; }
            });
            cards.forEach(card => grid.appendChild(card));
        }
    </script>
</body>
</html>
"""
auction_detail_template = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مزاد: {{ auction.title }}</title>
    <style>
        body { background: #000; color: #fff; font-family: Tahoma, sans-serif; padding: 20px; display: flex; flex-direction: column; align-items: center; }
        .box { background: #111; border: 1px solid #d97706; border-radius: 12px; padding: 25px; width: 100%; max-width: 600px; box-sizing: border-box; margin-top: 20px; }
        h1 { color: #fbbf24; text-align: center; font-size: 20px; margin-bottom: 15px; }
        .auction-gallery { display: flex; flex-direction: row; overflow-x: auto; gap: 10px; margin-bottom: 15px; background: #000; padding: 10px; border-radius: 8px; border: 1px solid #333; }
        .auction-gallery img { width: 100%; max-height: 500px; object-fit: contain; border-radius: 6px; flex: 0 0 100%; background: #000; }
        .info { font-size: 14px; margin-bottom: 10px; color: #ddd; display: flex; justify-content: space-between; align-items: center; background: #000; padding: 10px; border-radius: 8px; border: 1px solid #222; }
        input { width: 100%; padding: 12px; margin-bottom: 10px; border-radius: 8px; border: 1px solid #333; background: #000; color: #fff; box-sizing: border-box; outline: none; }
        button { width: 100%; padding: 12px; border-radius: 8px; background: #d97706; color: white; border: none; font-weight: bold; cursor: pointer; font-size: 15px; }
        .error-msg { background: rgba(220, 38, 38, 0.1); border: 1px solid #dc2626; color: #ef4444; padding: 10px; border-radius: 8px; text-align: center; font-size: 13px; margin-bottom: 15px; }
        .back { display: block; text-align: center; margin-top: 20px; color: #25d366; text-decoration: none; font-weight: bold; font-size: 14px; }
    </style>
</head>
<body>
    <div class="box">
        <h1>🔨 مزاد على: {{ auction.title }}</h1>
        {% if auction.images and auction.images|length > 0 %}
        <div class="auction-gallery">{% for img in auction.images %}<img src="{{ img }}" alt="صورة المزاد">{% endfor %}</div>
        {% endif %}
        <p style="color: #bbb; font-size: 13px; margin-bottom: 15px; text-align: right;">{{ auction.description }}</p>
        <div class="info">
            <span>السعر الحالي:</span>
            {% if auction.bids and auction.bids|length > 0 %}
                {% set sorted_bids = auction.bids|sort(attribute='raw_amount', reverse=True) %}
                <select style="background: #000; color: #25d366; border: 1px solid #333; padding: 6px 10px; border-radius: 6px; font-weight: bold; outline: none; font-size: 14px;">
                    <option value="{{ sorted_bids[0].amount }}">{{ sorted_bids[0].amount }} (بواسطة: {{ sorted_bids[0].name }})</option>
                    {% for b in sorted_bids[1:] %}<option value="{{ b.amount }}">{{ b.amount }} (بواسطة: {{ b.name }})</option>{% endfor %}
                </select>
            {% else %}
                <b style="color: #25d366;">{{ auction.current_price }}</b>
            {% endif %}
        </div>
        <div class="info"><span>الحد الأدنى للمزايدة:</span><b>{{ auction.min_bid }}</b></div>
        {% if auction.max_price %}<div class="info"><span>الحد الأقصى (الشراء الفوري):</span><b style="color: #ff5252;">{{ auction.max_price }}</b></div>{% endif %}
        {% if error %}<div class="error-msg">{{ error }}</div>{% endif %}
        <form action="/bid/{{ auction.id }}" method="POST" style="margin-top: 20px;">
            {% if vis.bid_name_label %}<label style="display: block; margin-bottom: 5px; font-size: 13px;">{{ config.texts.bid_name_label }}</label>{% endif %}
            <input type="text" name="bidder_name" placeholder="أدخل اسمك" required>
            {% if vis.bid_phone_label %}<label style="display: block; margin-bottom: 5px; font-size: 13px;">{{ config.texts.bid_phone_label }}</label>{% endif %}
            <input type="text" name="bidder_phone" placeholder="أدخل رقم هاتفك" oninput="this.value = this.value.replace(/[^0-9]/g, '')" required>
            {% if vis.bid_amount_label %}<label style="display: block; margin-bottom: 5px; font-size: 13px;">{{ config.texts.bid_amount_label }}</label>{% endif %}
            <input type="text" name="bid_amount" placeholder="أدخل مبلغ المزايدة الجديد (أرقام فقط)" oninput="this.value = this.value.replace(/[^0-9]/g, '')" required>
            <button type="submit">{{ config.texts.bid_submit_btn }}</button>
        </form>
        <a href="/" class="back">← العودة إلى المتجر الرئيسي</a>
    </div>
</body>
</html>
"""

reviews_page_template = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>آراء العملاء - {{ config.title }}</title>
    <style>
        body { background: #000; color: #fff; font-family: Tahoma, sans-serif; margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; min-height: 100vh; box-sizing: border-box; }
        .box { background: #111; border: 1px solid #222; padding: 25px; border-radius: 12px; width: 100%; max-width: 650px; margin-top: 20px; box-sizing: border-box; }
        h1 { color: #ff5252; text-align: center; font-size: 20px; margin-bottom: 20px; }
        .review-card { background: #000; padding: 15px; border-radius: 8px; border: 1px solid #222; margin-bottom: 12px; display: flex; flex-direction: column; gap: 6px; }
        .review-header { display: flex; justify-content: space-between; align-items: center; }
        .review-stars { color: #fbbf24; font-size: 14px; letter-spacing: 2px; }
        .review-card p { color: #fff; font-size: 13px; margin: 0; line-height: 1.5; }
        .review-card span { color: #25d366; font-size: 11px; font-weight: bold; }
        .add-review-form { margin-top: 25px; border-top: 1px solid #222; padding-top: 20px; }
        input, textarea { width: 100%; padding: 10px; margin-bottom: 10px; border-radius: 8px; border: 1px solid #333; background: #000; color: #fff; font-size: 13px; box-sizing: border-box; outline: none; }
        .rating-select { display: flex; flex-direction: row-reverse; justify-content: flex-end; gap: 5px; margin-bottom: 12px; }
        .rating-select input { display: none; }
        .rating-select label { font-size: 24px; color: #444; cursor: pointer; transition: color 0.2s; }
        .rating-select input:checked ~ label, .rating-select label:hover, .rating-select label:hover ~ label { color: #fbbf24; }
        button { width: 100%; padding: 12px; border-radius: 8px; background: #25d366; color: white; border: none; font-weight: bold; cursor: pointer; font-size: 14px; }
        .back { display: block; text-align: center; margin-top: 25px; color: #25d366; text-decoration: none; font-weight: bold; font-size: 14px; }
    </style>
</head>
<body>
    <div class="box">
        <h1>⭐ آراء العملاء وتجاربهم</h1>
        {% if reviews|length == 0 %}<p style="color: #888; text-align: center; padding: 15px; font-size: 13px;">لا توجد آراء مسجلة حالياً.</p>{% endif %}
        {% for r in reviews %}
            <div class="review-card">
                <div class="review-header">
                    <span>- {{ r.name }}</span>
                    <div class="review-stars">{% for i in range(r.rating) %}⭐{% endfor %}</div>
                </div>
                <p>"{{ r.comment }}"</p>
            </div>
        {% endfor %}
        <div class="add-review-form">
            <h3 style="color: #fff; font-size: 15px; margin-bottom: 12px; text-align: right;">أضف رأيك وتجربتك معنا:</h3>
            <form action="/add-review" method="POST">
                <input type="text" name="reviewer_name" placeholder="اسمك الكريم" required>
                <label style="font-size: 12px; color: #ccc; margin-bottom: 5px; display: block; text-align: right;">التقييم بالنجوم:</label>
                <div class="rating-select">
                    <input type="radio" id="star5" name="rating" value="5" checked><label for="star5">★</label>
                    <input type="radio" id="star4" name="rating" value="4"><label for="star4">★</label>
                    <input type="radio" id="star3" name="rating" value="3"><label for="star3">★</label>
                    <input type="radio" id="star2" name="rating" value="2"><label for="star2">★</label>
                    <input type="radio" id="star1" name="rating" value="1"><label for="star1">★</label>
                </div>
                <textarea name="reviewer_comment" rows="3" placeholder="اكتب رأيك هنا..." required></textarea>
                <button type="submit">نشر الرأي</button>
            </form>
        </div>
        <a href="/" class="back">← العودة إلى المتجر الرئيسي</a>
    </div>
</body>
</html>
"""

copyright_template = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>حقوق النشر والشروط</title>
    <style>
        body { background: #000; color: #fff; font-family: Tahoma, sans-serif; margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; min-height: 100vh; box-sizing: border-box; }
        .box { background: #111; border: 1px solid #222; padding: 30px; border-radius: 12px; width: 100%; flex: 1; display: flex; flex-direction: column; justify-content: space-between; box-sizing: border-box; }
        .content-area { max-width: 900px; margin: 0 auto; width: 100%; }
        h1 { color: #25d366; text-align: center; font-size: 22px; margin-bottom: 25px; } 
        p { color: #ddd; font-size: 15px; line-height: 1.8; white-space: pre-wrap; text-align: right; } 
        .back { display: block; text-align: center; margin-top: 30px; color: #25d366; text-decoration: none; font-weight: bold; font-size: 15px; }
    </style>
</head>
<body>
    <div class="box">
        <div class="content-area">
            <h1>حقوق النشر والشروط</h1>
            <p>{{ text }}</p>
        </div>
        <div><a href="/" class="back">← العودة إلى المتجر الرئيسي</a></div>
    </div>
</body>
</html>
"""

admin_template = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة الإعدادات والتحكم</title>
    <style>
        body { background: #000; color: #fff; font-family: Tahoma, sans-serif; padding: 20px; display: flex; flex-direction: column; align-items: center; }
        .container { background: #111; padding: 25px; border-radius: 12px; border: 1px solid #222; width: 100%; max-width: 650px; margin-top: 20px; }
        h2, h3 { color: #fff; text-align: center; margin-bottom: 20px; }
        input[type="text"], input[type="password"], input[type="number"], textarea, select { width: 100%; padding: 10px; margin-bottom: 10px; border-radius: 8px; border: 1px solid #333; background: #000; color: #fff; box-sizing: border-box; font-size: 13px; outline: none; }
        input[type="color"] { width: 50px; height: 32px; border: 1px solid #333; border-radius: 6px; background: #000; cursor: pointer; padding: 0; vertical-align: middle; }
        button { width: 100%; padding: 12px; margin-bottom: 15px; border-radius: 8px; background: #25d366; color: white; border: none; font-weight: bold; cursor: pointer; font-size: 15px; }
        button:disabled { background: #444 !important; cursor: not-allowed; }
        .product-row { display: flex; justify-content: space-between; align-items: center; background: #000; padding: 12px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #222; gap: 10px; }
        .product-actions { display: flex; gap: 8px; align-items: center; }
        .delete-btn { background: #dc2626; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; width: auto; margin: 0; }
        .sold-btn { background: #d97706; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; width: auto; margin: 0; }
        .unsold-btn { background: #2563eb; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; width: auto; margin: 0; }
        .back-link { display: block; text-align: center; margin-top: 20px; color: #25d366; text-decoration: none; font-size: 14px; font-weight: bold; }
        .section-box { border-top: 1px solid #222; margin-top: 25px; padding-top: 20px; }
        .row-item { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; background: #000; padding: 6px 10px; border-radius: 6px; border: 1px solid #222; }
        .row-item span { font-size: 12px; color: #ccc; width: 55%; text-align: right; }
        .row-item input[type="text"] { width: 35%; margin: 0; }
        label { display: block; margin-bottom: 5px; font-size: 13px; color: #fff; font-weight: bold; }
        .checkbox-label { display: flex; align-items: center; gap: 10px; background: #000; padding: 10px; border-radius: 8px; border: 1px solid #222; cursor: pointer; margin-bottom: 10px; font-size: 14px; color: #fff; font-weight: normal; }
        .checkbox-label input { width: 18px; height: 18px; cursor: pointer; }
        .note-card { background: #000; border: 1px solid #333; padding: 12px; border-radius: 8px; margin-bottom: 10px; font-size: 13px; }
        .collapsible-header { background: #1a1a1a; border: 1px solid #333; color: #fff; padding: 14px 18px; border-radius: 8px; cursor: pointer; font-size: 15px; font-weight: bold; display: flex; justify-content: space-between; align-items: center; margin-top: 15px; user-select: none; }
        .collapsible-header:hover { background: #222; color: #25d366; }
        .collapsible-content { display: none; background: #0a0a0a; border: 1px solid #222; border-top: none; padding: 15px; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px; margin-bottom: 15px; }
        .forgot-pass-btn { display: block; text-align: center; background: #25d366; color: #000; padding: 10px; border-radius: 8px; text-decoration: none; font-size: 13px; font-weight: bold; margin-top: 10px; }
        .forgot-pass-btn:hover { background: #22bf5b; }
        .stat-box { background: #000; border: 1px solid #333; padding: 12px 15px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>لوحة الإعدادات والتحكم</h2>
        {% if not authorized %}
            {% if is_locked %}
                <div style="background: rgba(220, 38, 38, 0.1); border: 1px solid #dc2626; color: #ef4444; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 15px;">
                    <p style="font-weight: bold; margin-bottom: 5px;">⚠️ تم حظر تسجيل الدخول مؤقتاً!</p>
                    <p style="font-size: 13px;">لقد أدخلت كلمة المرور بشكل خاطئ 5 مرات. يرجى الانتظار:</p>
                    <p id="countdown" style="font-size: 18px; font-weight: bold; margin-top: 8px; color: #fbbf24;">15:00</p>
                </div>
            {% else %}
                <form method="POST">
                    <p style="margin-bottom: 12px; font-size: 14px; color: #ccc; text-align: center;">الرجاء إدخال رمز المرور للوصول:</p>
                    <input type="password" name="password" placeholder="رمز المرور" required>
                    <button type="submit">دخول</button>
                </form>
                {% if error %}<p style="color: #ef4444; text-align: center; font-size: 13px; margin-top: 10px;">❌ رمز المرور غير صحيح! (المحاولات المتبقية: {{ remaining_attempts }})</p>{% endif %}
                {% if controls.enable_forgot_pass %}
                <a href="https://wa.me/{{ controls.admin_whatsapp }}?text={{ 'مرحباً سامر، لقد نسيت كلمة مرور لوحة التحكم الخاصة بمتجر عتيق، أرجو مساعدتي في استرجاعها.' | urlencode }}" target="_blank" class="forgot-pass-btn">🔑 نسيت كلمة السر؟ (إرسال تنبيه واتساب)</a>
                {% endif %}
            {% endif %}
        {% else %}
            <p style="color: #25d366; text-align: center; margin-bottom: 15px; font-weight: bold;">تم تسجيل الدخول بنجاح</p>

            <div class="collapsible-header" onclick="toggleSection('sec_stats')"><span>📊 إحصائيات المتجر والزيارات</span><span id="icon-sec_stats">▼</span></div>
            <div id="sec_stats" class="collapsible-content">
                <div class="stat-box">
                    <span>إجمالي زيارات المتجر:</span>
                    <b style="color: #25d366; font-size: 16px;">{{ stats.total_visits }} زيارة</b>
                </div>
                <h4 style="color: #fbbf24; font-size: 14px; margin: 15px 0 10px 0;">مشاهدات قطع المنتجات:</h4>
                {% if products|length == 0 %}
                    <p style="color: #777; font-size: 12px; text-align: center;">لا توجد منتجات حالياً.</p>
                {% else %}
                    {% set sorted_prods = products|sort(attribute='views', reverse=True) %}
                    {% for p in sorted_prods %}
                        <div class="stat-box">
                            <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 70%;">🏷️ {{ p.title }}</span>
                            <b style="color: #38bdf8;">{{ p.views | default(0) }} مشاهدة</b>
                        </div>
                    {% endfor %}
                {% endif %}
            </div>

            <div class="collapsible-header" onclick="toggleSection('sec_currency')"><span>💵 إعدادات عملة المتجر (رمز العملة)</span><span id="icon-sec_currency">▼</span></div>
            <div id="sec_currency" class="collapsible-content">
                <form action="/update-currency" method="POST">
                    <label>رمز العملة الرسمي (يتم إضافته تلقائياً بجانب الأسعار):</label>
                    <input type="text" name="currency_symbol" value="{{ controls.currency_symbol }}" placeholder="مثال: د.أ" required>
                    <button type="submit" style="background: #25d366; margin-top: 10px;">حفظ رمز العملة ✅</button>
                </form>
            </div>

            <div class="collapsible-header" onclick="toggleSection('sec_marquee')"><span>📢 إعدادات الشريط الإعلاني المتحرك</span><span id="icon-sec_marquee">▼</span></div>
            <div id="sec_marquee" class="collapsible-content">
                <form action="/update-marquee" method="POST">
                    <label class="checkbox-label"><input type="checkbox" name="enable_marquee" {% if controls.enable_marquee %}checked{% endif %}> تفعيل الشريط الإعلاني المتحرك أعلى المتجر</label>
                    <label>نص الإعلان أو التنبيه المتحرك:</label>
                    <textarea name="marquee_text" rows="3" placeholder="اكتب النص الإعلاني هنا..." required>{{ controls.marquee_text }}</textarea>
                    <button type="submit" style="background: #25d366; margin-top: 10px;">حفظ إعدادات الشريط الإعلاني ✅</button>
                </form>
            </div>

            <div class="collapsible-header" onclick="toggleSection('sec_password')"><span>🔑 تغيير رمز مرور لوحة التحكم</span><span id="icon-sec_password">▼</span></div>
            <div id="sec_password" class="collapsible-content">
                <form action="/update-password" method="POST">
                    <label>رمز المرور الحالي:</label><input type="password" name="current_password" placeholder="أدخل الرمز الحالي" required>
                    <label>رمز المرور الجديد:</label><input type="password" name="new_password" placeholder="أدخل الرمز الجديد" required>
                    <button type="submit" style="background: #dc2626;">تحديث رمز المرور</button>
                </form>
            </div>
            <div class="collapsible-header" onclick="toggleSection('sec_wa')"><span>📱 رابط التواصل أو رقم الواتساب</span><span id="icon-sec_wa">▼</span></div>
            <div id="sec_wa" class="collapsible-content">
                <form action="/update-admin-whatsapp" method="POST">
                    <label>رقم واتساب أو رابط إنستغرام:</label><input type="text" name="admin_whatsapp" value="{{ controls.admin_whatsapp }}" placeholder="مثال: 962790000000" required>
                    <button type="submit">حفظ وجهة التواصل</button>
                </form>
            </div>
            <div class="collapsible-header" onclick="toggleSection('sec_cod')"><span>💵 إعدادات جملة الدفع عند الاستلام</span><span id="icon-sec_cod">▼</span></div>
            <div id="sec_cod" class="collapsible-content">
                <form action="/update-cod-settings" method="POST">
                    <label class="checkbox-label"><input type="checkbox" name="enable_cod_note" {% if controls.enable_cod_note %}checked{% endif %}> تفعيل ظهور جملة الدفع عند الاستلام تحت رقم الهاتف</label>
                    <label>نص العبارة التوضيحية:</label><input type="text" name="cod_note_text" value="{{ controls.cod_note_text }}" placeholder="مثال: الدفع عند الاستلام 💵" required>
                    <button type="submit" style="margin-top: 10px;">حفظ إعدادات العبارة</button>
                </form>
            </div>
            <div class="collapsible-header" onclick="toggleSection('sec1')"><span>⚙️ إدارة الخصائص والميزات العامة</span><span id="icon-sec1">▼</span></div>
            <div id="sec1" class="collapsible-content">
                <form action="/update-controls" method="POST">
                    <label class="checkbox-label"><input type="checkbox" name="enable_cart" {% if controls.enable_cart %}checked{% endif %}> تفعيل سلة المشتريات وزر "أضف إلى السلة"</label>
                    <label class="checkbox-label"><input type="checkbox" name="enable_auctions" {% if controls.enable_auctions %}checked{% endif %}> تفعيل قسم المزادات</label>
                    <label class="checkbox-label"><input type="checkbox" name="enable_scroll_top" {% if controls.enable_scroll_top %}checked{% endif %}> تفعيل زر "العودة إلى الأعلى" في المتجر</label>
                    <label class="checkbox-label"><input type="checkbox" name="enable_forgot_pass" {% if controls.enable_forgot_pass %}checked{% endif %}> تفعيل زر "نسيت كلمة السر" في صفحة الدخول</label>
                    <label class="checkbox-label"><input type="checkbox" name="block_posting" {% if controls.block_posting %}checked{% endif %}> منع المستخدمين من الإضافة</label>
                    <label class="checkbox-label"><input type="checkbox" name="enable_search" {% if controls.enable_search %}checked{% endif %}> تفعيل البحث</label>
                    <label class="checkbox-label"><input type="checkbox" name="enable_contact_btn" {% if controls.enable_contact_btn %}checked{% endif %}> تفعيل زر الشراء</label>
                    <label class="checkbox-label"><input type="checkbox" name="enable_socials" {% if controls.enable_socials %}checked{% endif %}> تفعيل السوشيال ميديا</label>
                    <label class="checkbox-label"><input type="checkbox" name="enable_copyright" {% if controls.enable_copyright %}checked{% endif %}> تفعيل حقوق النشر</label>
                    <label class="checkbox-label"><input type="checkbox" name="enable_reviews_page" {% if controls.enable_reviews_page %}checked{% endif %}> تفعيل آراء العملاء</label>
                    <button type="submit" style="margin-top: 10px;">حفظ الخصائص</button>
                </form>
            </div>
            <div class="collapsible-header" onclick="toggleSection('sec2')"><span>📝 إدارة النصوص والظهور</span><span id="icon-sec2">▼</span></div>
            <div id="sec2" class="collapsible-content">
                <form action="/update-texts" method="POST">
                    {% for key, val in config.texts.items() %}
                        <div class="row-item">
                            <label style="display: flex; align-items: center; gap: 8px; font-size: 13px; color: #fff; cursor: pointer; width: 45%; margin: 0;">
                                <input type="checkbox" name="vis_{{ key }}" {% if vis[key] %}checked{% endif %}>{{ key }}
                            </label>
                            <input type="text" name="txt_{{ key }}" value="{{ val }}" required>
                        </div>
                    {% endfor %}
                    <button type="submit" style="margin-top: 15px;">حفظ النصوص</button>
                </form>
            </div>
            <div class="collapsible-header" onclick="toggleSection('sec3')"><span>🎨 تعديل الألوان والتصميم وخلفية الموقع</span><span id="icon-sec3">▼</span></div>
            <div id="sec3" class="collapsible-content">
                <form action="/update-config" method="POST" enctype="multipart/form-data">
                    <label>اسم الموقع:</label><input type="text" name="title" value="{{ config.title }}" required>
                    <label>وصف الموقع الأساسي:</label><input type="text" name="subtitle" value="{{ config.subtitle }}" required>
                    <label>صورة الخلفية:</label><input type="file" name="bg_image_file" accept="image/*" style="margin-bottom: 10px; color: #fff;">
                    <label class="checkbox-label" style="margin-bottom: 15px;"><input type="checkbox" name="enable_bg_overlay" {% if controls.enable_bg_overlay %}checked{% endif %}> تفعيل طبقة العتمة/التظليل فوق صورة الخلفية 🌑</label>
                    {% for color_key, color_val in config.colors.items() %}
                    <div class="row-item">
                        <span>{{ color_names_ar.get(color_key, color_key) }}:</span>
                        <input type="color" name="c_{{ color_key }}" value="{{ color_val }}">
                    </div>
                    {% endfor %}
                    <button type="submit" style="margin-top: 15px;">حفظ التصميم</button>
                </form>
            </div>
            <div class="collapsible-header" onclick="toggleSection('sec_logo')"><span>🖼️ إدارة صورة شعار الموقع الدائري والحجم والحركات</span><span id="icon-sec_logo">▼</span></div>
            <div id="sec_logo" class="collapsible-content">
                <form action="/update-logo" method="POST" enctype="multipart/form-data">
                    <label class="checkbox-label"><input type="checkbox" name="use_logo_image" {% if controls.use_logo_image %}checked{% endif %}> تفعيل صورة الشعار الدائري في الموقع</label>
                    <label>اختر صورة الشعار (موصى بها مربعة لتبدو دائرية فخمة):</label><input type="file" name="logo_file" accept="image/*" style="color: #fff; margin-bottom: 12px;">
                    <label>حجم الشعار الدائري:</label>
                    <select name="logo_size" style="background:#000; color:#fff; padding:10px; border-radius:8px; border:1px solid #333; margin-bottom:10px; width:100%;">
                        <option value="90px" {% if controls.logo_size == '90px' %}selected{% endif %}>صغير (90 بكسل)</option>
                        <option value="110px" {% if controls.logo_size == '110px' %}selected{% endif %}>وسط (110 بكسل)</option>
                        <option value="130px" {% if controls.logo_size == '130px' %}selected{% endif %}>متوسط (130 بكسل - موصى به)</option>
                        <option value="170px" {% if controls.logo_size == '170px' %}selected{% endif %}>كبير (170 بكسل)</option>
                        <option value="210px" {% if controls.logo_size == '210px' %}selected{% endif %}>كبير جداً (210 بكسل)</option>
                    </select>
                    <hr style="border: 0; border-top: 1px solid #333; margin: 15px 0;">
                    <label class="checkbox-label"><input type="checkbox" name="enable_logo_pulse" {% if controls.enable_logo_pulse %}checked{% endif %}> تفعيل إضاءة وتوهج الشعار الدائري ✨</label>
                    
                    <label>اختر شكل وحركة الإضاءة:</label>
                    <select name="logo_animation_style" style="background:#000; color:#fff; padding:10px; border-radius:8px; border:1px solid #333; margin-bottom:10px; width:100%;">
                        <option value="rotate" {% if controls.logo_animation_style == 'rotate' %}selected{% endif %}>إضاءة متلاحقة تلف وتدور (دوران)</option>
                        <option value="pulse" {% if controls.logo_animation_style == 'pulse' %}selected{% endif %}>النبض الكلاسيكي (تكبير وتصغير)</option>
                        <option value="flash" {% if controls.logo_animation_style == 'flash' %}selected{% endif %}>نبض سريع ووامض (Flash)</option>
                    </select>

                    <label>سرعة الحركة (بالثواني):</label>
                    <select name="logo_pulse_speed" style="background:#000; color:#fff; padding:10px; border-radius:8px; border:1px solid #333; margin-bottom:10px; width:100%;">
                        <option value="5s" {% if controls.logo_pulse_speed == '5s' %}selected{% endif %}>بطيء (5 ثواني)</option>
                        <option value="3s" {% if controls.logo_pulse_speed == '3s' %}selected{% endif %}>متوسط (3 ثواني - موصى به)</option>
                        <option value="1.5s" {% if controls.logo_pulse_speed == '1.5s' %}selected{% endif %}>سريع (ثانية ونصف)</option>
                    </select>
                    <label>لون التوهج والإضاءة:</label>
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                        <input type="color" name="logo_pulse_color" value="{{ controls.logo_pulse_color }}">
                        <span style="font-size: 12px; color: #aaa;">اختر لون التوهج</span>
                    </div>
                    <button type="submit" style="background: #25d366; margin-top: 10px;">حفظ إعدادات الشعار ✅</button>
                </form>
            </div>
            <div class="collapsible-header" onclick="toggleSection('sec_auctions')"><span>🔨 إدارة وإطلاق المزادات</span><span id="icon-sec_auctions">▼</span></div>
            <div id="sec_auctions" class="collapsible-content">
                <form action="/admin-add-auction" method="POST" enctype="multipart/form-data">
                    <label>عنوان المزاد (اسم القطعة):</label><input type="text" name="title" placeholder="مثال: ساعة فاخرة نادرة" required>
                    <label>وصف المزاد أو تفاصيله:</label><textarea name="description" rows="3" placeholder="تفاصيل وحالة القطعة..."></textarea>
                    <label>السعر الابتدائي (أدخل الرقم فقط - يتم إضافة {{ controls.currency_symbol }} تلقائياً):</label><input type="text" name="current_price" placeholder="مثال: 50" required>
                    <label>الحد الأدنى للزيادة:</label><input type="text" name="min_bid" placeholder="مثال: 5" required>
                    <label>الحد الأقصى للشراء الفوري (اختياري):</label><input type="text" name="max_price" placeholder="مثال: 150">
                    <label>مدة المزاد بالساعات:</label><input type="number" name="duration_hours" value="48" required>
                    <label>صور القطعة للمزاد 📸:</label><input type="file" name="auction_images" multiple accept="image/*" style="color: #fff; margin-bottom: 10px;">
                    <button type="submit" style="background: #d97706; margin-top: 10px;">إطلاق المزاد 🚀</button>
                </form>
                <div style="margin-top: 15px;">
                    <h4 style="color: #fbbf24; font-size: 14px; margin-bottom: 10px;">المزادات النشطة:</h4>
                    {% if auctions|length == 0 %}<p style="color: #777; font-size: 12px; text-align: center;">لا توجد مزادات نشطة.</p>{% endif %}
                    {% for a in auctions %}
                        <div class="product-row" style="flex-direction: column; align-items: flex-start; gap: 5px;">
                            <div style="display: flex; justify-content: space-between; width: 100%;">
                                <span><b>{{ a.title }}</b> (السعر الحالي: {{ a.current_price }})</span>
                                <form action="/delete-auction/{{ a.id }}" method="POST" style="margin:0;"><button type="submit" class="delete-btn">حذف</button></form>
                            </div>
                            {% if a.bids and a.bids|length > 0 %}<span style="font-size: 11px; color: #25d366;">إجمالي المزايدات: {{ a.bids|length }} مزايدة</span>{% endif %}
                        </div>
                    {% endfor %}
                </div>
            </div>
            <div class="collapsible-header" onclick="toggleSection('sec_code')"><span>💻 محرر الكود الداخلي</span><span id="icon-sec_code">▼</span></div>
            <div id="sec_code" class="collapsible-content">
                <form action="/update-code" method="POST">
                    <textarea name="custom_html" rows="10" style="font-family: monospace; font-size: 11px; direction: ltr; text-align: left;" required>{{ raw_template }}</textarea>
                    <button type="submit">حفظ وتحديث كود الواجهة</button>
                </form>
            </div>
            <div class="collapsible-header" onclick="toggleSection('sec_reviews')"><span>⭐ إدارة وحذف آراء العملاء</span><span id="icon-sec_reviews">▼</span></div>
            <div id="sec_reviews" class="collapsible-content">
                {% if reviews|length == 0 %}<p style="color: #888; text-align: center; padding: 10px; font-size: 12px;">لا توجد آراء مسجلة حالياً.</p>{% endif %}
                {% for r in reviews %}
                    <div class="product-row">
                        <span><b>{{ r.name }}</b> (⭐ {{ r.rating }}): {{ r.comment }}</span>
                        <form action="/delete-review/{{ r.id }}" method="POST" style="margin:0;"><button type="submit" class="delete-btn">حذف</button></form>
                    </div>
                {% endfor %}
            </div>
            <div class="collapsible-header" onclick="toggleSection('sec_notes')"><span>💡 مفكرة الأفكار والملاحظات</span><span id="icon-sec_notes">▼</span></div>
            <div id="sec_notes" class="collapsible-content">
                <form action="/add-note" method="POST" enctype="multipart/form-data">
                    <label>عنوان الفكرة أو الملاحظة:</label><input type="text" name="note_title" required>
                    <label>تفاصيل الفكرة:</label><textarea name="note_content" rows="4" required></textarea>
                    <label>صور توضيحية:</label><input type="file" name="note_images" multiple accept="image/*" style="color: #fff; margin-bottom: 10px;">
                    <button type="submit">إضافة للمفكرة</button>
                </form>
                <div style="margin-top: 15px;">
                    {% for n in notes %}
                        <div class="note-card">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                <b style="color: #ff5252; font-size: 14px;">{{ n.title }}</b>
                                <form action="/delete-note/{{ n.id }}" method="POST" style="margin:0;"><button type="submit" class="delete-btn" style="padding: 3px 8px; font-size: 11px;">حذف</button></form>
                            </div>
                            <p style="color: #ddd; white-space: pre-wrap; margin: 5px 0;">{{ n.content }}</p>
                        </div>
                    {% endfor %}
                </div>
            </div>
            <div class="section-box">
                <h3>➕ إضافة منتج جديد</h3>
                <form action="/admin-add-product" method="POST" enctype="multipart/form-data">
                    <label>{{ config.texts.label_title }}</label><input type="text" name="title" required>
                    <label>{{ config.texts.label_price }} (أدخل الرقم فقط - يتم إضافة {{ controls.currency_symbol }} تلقائياً)</label><input type="text" name="price">
                    <label>{{ config.texts.label_quantity }}</label><input type="text" name="quantity" value="1">
                    <label>{{ config.texts.label_description }}</label><textarea name="description" rows="3"></textarea>
                    <label>{{ config.texts.upload_text }}</label><input type="file" name="images" multiple accept="image/*" style="color: #fff; margin-bottom: 10px;">
                    <button type="submit">نشر المنتج</button>
                </form>
            </div>
            <div class="collapsible-header" onclick="toggleSection('sec_products')"><span>📦 قائمة المنتجات الحالية</span><span id="icon-sec_products">▼</span></div>
            <div id="sec_products" class="collapsible-content">
                {% for p in products %}
                    <div class="product-row">
                        <span><b>{{ p.title }}</b> ({{ p.price }})</span>
                        <div class="product-actions">
                            <form action="/toggle-sold/{{ p.id }}" method="POST" style="margin:0;"><button type="submit" class="{% if p.is_sold %}unsold-btn{% else %}sold-btn{% endif %}">{% if p.is_sold %}إلغاء البيع{% else %}تم البيع{% endif %}</button></form>
                            <form action="/delete/{{ p.id }}" method="POST" style="margin:0;"><button type="submit" class="delete-btn">حذف</button></form>
                        </div>
                    </div>
                {% endfor %}
            </div>
        {% endif %}
        <a href="/" class="back-link">← العودة إلى المتجر الرئيسي</a>
    </div>
    <script>
        function toggleSection(secId) {
            const content = document.getElementById(secId);
            const icon = document.getElementById('icon-' + secId);
            if (content.style.display === 'block') { content.style.display = 'none'; icon.innerText = '▼'; }
            else { content.style.display = 'block'; icon.innerText = '▲'; }
        }
        {% if is_locked %}
        let remainingSeconds = {{ remaining_seconds }};
        const countdownEl = document.getElementById('countdown');
        const timer = setInterval(() => {
            if (remainingSeconds <= 0) { clearInterval(timer); window.location.reload(); }
            else {
                remainingSeconds--;
                let mins = Math.floor(remainingSeconds / 60);
                let secs = remainingSeconds % 60;
                countdownEl.innerText = (mins < 10 ? "0" : "") + mins + ":" + (secs < 10 ? "0" : "") + secs;
            }
        }, 1000);
        {% endif %}
    </script>
</body>
</html>
"""

current_html_template = default_html_template

def process_and_compress_image(image_file):
    try:
        img = Image.open(image_file)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        try: img = ImageOps.exif_transpose(img)
        except Exception: pass
        img.thumbnail((1000, 1000))
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=80)
        return f"data:image/jpeg;base64,{base64.b64encode(buffer.getvalue()).decode('utf-8')}"
    except Exception:
        return None

@app.route('/')
def index():
    global current_html_template, site_stats
    site_stats['total_visits'] += 1
    cart = get_cart()
    per_page = 30
    try: page = int(request.args.get('page', 1))
    except ValueError: page = 1
    total_products = len(products)
    total_pages = (total_products + per_page - 1) // per_page if total_products > 0 else 1
    if page < 1: page = 1
    if page > total_pages: page = total_pages
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_products = products[start_idx:end_idx]
    return render_template_string(current_html_template, products=products, page_products=page_products, current_page=page, total_pages=total_pages, auctions=auctions, config=site_config, controls=site_controls, vis=text_visibility, cart_count=len(cart), error=None)

@app.route('/cart')
def cart_page():
    if not site_controls['enable_cart']: return redirect(url_for('index'))
    cart = get_cart()
    return render_template_string(cart_template, cart_items=cart, config=site_config)

@app.route('/add-to-cart-ajax/<int:p_id>', methods=['POST'])
def add_to_cart_ajax(p_id):
    product = next((p for p in products if p['id'] == p_id), None)
    if product and not product.get('is_sold', False):
        cart = list(get_cart())
        already_exists = any(item['id'] == p_id for item in cart)
        if already_exists: return jsonify({"success": False, "msg": "مضاف مسبقاً"})
        import uuid
        first_img = product['images'][0] if product['images'] and len(product['images']) > 0 else ""
        cart_item = {"cart_id": str(uuid.uuid4()), "id": product['id'], "title": product['title'], "price": product['price'], "image": first_img}
        cart.append(cart_item)
        update_cart_in_storage(cart)
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/remove-from-cart/<cart_id>', methods=['POST'])
def remove_from_cart(cart_id):
    cart = list(get_cart())
    cart = [item for item in cart if item.get('cart_id') != cart_id]
    update_cart_in_storage(cart)
    return redirect(url_for('cart_page'))

@app.route('/auction/<int:a_id>')
def auction_detail(a_id):
    auction = next((a for a in auctions if a['id'] == a_id), None)
    if not auction: return redirect(url_for('index'))
    return render_template_string(auction_detail_template, auction=auction, config=site_config, controls=site_controls, vis=text_visibility, error=None)

@app.route('/bid/<int:a_id>', methods=['POST'])
def place_bid(a_id):
    global auctions
    bidder_name = request.form.get('bidder_name', '').strip()
    bidder_phone = request.form.get('bidder_phone', '').strip()
    bid_amount_str = request.form.get('bid_amount', '').strip()
    auction = next((a for a in auctions if a['id'] == a_id), None)
    if not auction: return redirect(url_for('index'))
    
    clean_phone = bidder_phone.replace(" ", "")
    if not clean_phone.isdigit() or len(clean_phone) < 7:
        return render_template_string(auction_detail_template, auction=auction, config=site_config, controls=site_controls, vis=text_visibility, error="❌ خطأ: رقم الهاتف يجب أن يتكون من أرقام فقط وألا يقل عن 7 أرقام!")
    if not bid_amount_str.isdigit():
        return render_template_string(auction_detail_template, auction=auction, config=site_config, controls=site_controls, vis=text_visibility, error="❌ خطأ: السعر المقترح للمزايدة يجب أن يكون أرقاماً فقط بدون أحرف!")
    
    bid_raw = int(bid_amount_str)
    
    current_highest_raw = 0
    if auction.get('bids') and len(auction['bids']) > 0:
        current_highest_raw = max(b['raw_amount'] for b in auction['bids'])
    else:
        current_highest_raw = int(re.sub(r'[^0-9]', '', str(auction['current_price'])))
    
    if bid_raw <= current_highest_raw:
        return render_template_string(auction_detail_template, auction=auction, config=site_config, controls=site_controls, vis=text_visibility, error=f"❌ خطأ: عذراً، يجب أن تكون المزايدة أعلى من السعر الحالي ({current_highest_raw})!")

    formatted_bid_amount = format_price(str(bid_raw))
    
    if auction.get('max_price'):
        try:
            max_val = int(re.sub(r'[^0-9]', '', str(auction['max_price'])))
            if bid_raw > max_val:
                return render_template_string(auction_detail_template, auction=auction, config=site_config, controls=site_controls, vis=text_visibility, error=f"❌ خطأ: عذراً، لا يمكنك تقديم مزايدة أكبر من الحد الأقصى ({auction['max_price']})!")
        except Exception: pass
        
    if bid_raw and bidder_name:
        if 'bids' not in auction: auction['bids'] = []
        auction['bids'].append({"name": bidder_name, "phone": bidder_phone, "amount": formatted_bid_amount, "raw_amount": bid_raw})
        auction['bids'] = sorted(auction['bids'], key=lambda x: x['raw_amount'], reverse=True)
        top_bid = auction['bids'][0]
        auction['current_price'] = f"{top_bid['amount']} (بواسطة: {top_bid['name']})"
        
        msg = f"مرحباً سامر، لدي مزايدة جديدة\nعلى القطعة: {auction['title']}\nقيمة المزايدة: {formatted_bid_amount}\nاسم المزايد: {bidder_name}\nرقم الهاتف: {bidder_phone}"
        encoded_msg = urllib.parse.quote(msg)
        target_setting = site_controls.get('admin_whatsapp', '962790000000')
        final_url = get_destination_url(target_setting, encoded_msg)
        return redirect(final_url)
        
    return redirect(url_for('auction_detail', a_id=a_id))

@app.route('/buy-product/<int:p_id>', methods=['POST'])
def buy_product(p_id):
    full_name = request.form.get('full_name', '').strip()
    province = request.form.get('province', '').strip()
    street = request.form.get('street', '').strip()
    phone = request.form.get('phone', '').strip()
    product = next((p for p in products if p['id'] == p_id), None)
    if not product: return redirect(url_for('index'))
    clean_phone = phone.replace(" ", "")
    if not clean_phone.isdigit() or len(clean_phone) < 7:
        return render_template_string(product_detail_template, product=product, config=site_config, controls=site_controls, vis=text_visibility, error="❌ خطأ: رقم الهاتف يجب أن يتكون من أرقام فقط وألا يقل عن 7 أرقام!")
    if full_name and province and street and phone:
        msg = f"مرحباً سامر، لدي طلب شراء جديد\nعلى القطعة: {product['title']} (السعر: {product['price']})\nاسم الزبون: {full_name}\nالمحافظة: {province}\nالشارع: {street}\nرقم الهاتف: {phone}"
        encoded_msg = urllib.parse.quote(msg)
        target_setting = site_controls.get('admin_whatsapp', '962790000000')
        final_url = get_destination_url(target_setting, encoded_msg)
        return redirect(final_url)
    return redirect(url_for('product_detail', p_id=p_id))

@app.route('/update-admin-whatsapp', methods=['POST'])
def update_admin_whatsapp():
    global site_controls
    whatsapp = request.form.get('admin_whatsapp', '').strip()
    if whatsapp: site_controls['admin_whatsapp'] = whatsapp
    return redirect(url_for('admin'))

@app.route('/update-currency', methods=['POST'])
def update_currency():
    global site_controls
    curr = request.form.get('currency_symbol', '').strip()
    if curr: site_controls['currency_symbol'] = curr
    return redirect(url_for('admin'))

@app.route('/update-cod-settings', methods=['POST'])
def update_cod_settings():
    global site_controls
    site_controls['enable_cod_note'] = True if request.form.get('enable_cod_note') == 'on' else False
    text = request.form.get('cod_note_text', '').strip()
    if text: site_controls['cod_note_text'] = text
    return redirect(url_for('admin'))

@app.route('/update-marquee', methods=['POST'])
def update_marquee():
    global site_controls
    site_controls['enable_marquee'] = True if request.form.get('enable_marquee') == 'on' else False
    text = request.form.get('marquee_text', '').strip()
    if text: site_controls['marquee_text'] = text
    return redirect(url_for('admin'))

@app.route('/update-password', methods=['POST'])
def update_password():
    global ADMIN_PASSWORD
    current_pass = request.form.get('current_password', '')
    new_pass = request.form.get('new_password', '').strip()
    if current_pass == ADMIN_PASSWORD and new_pass: ADMIN_PASSWORD = new_pass
    return redirect(url_for('admin'))

@app.route('/admin-add-auction', methods=['POST'])
def admin_add_auction():
    global auction_id_counter, auctions
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    raw_price = request.form.get('current_price', '').strip()
    raw_min = request.form.get('min_bid', '').strip()
    raw_max = request.form.get('max_price', '').strip()
    
    try:
        duration_hours = int(request.form.get('duration_hours', 48))
    except ValueError:
        duration_hours = 48
        
    end_time = datetime.now() + timedelta(hours=duration_hours) + timedelta(hours=3)
    
    current_price = format_price(raw_price)
    min_bid = format_price(raw_min)
    max_price = format_price(raw_max) if raw_max else ""
    
    images_list = [process_and_compress_image(f) for f in request.files.getlist('auction_images') if f and f.filename != '']
    if title and current_price:
        auctions.insert(0, {"id": auction_id_counter, "title": title, "description": description, "current_price": current_price, "min_bid": min_bid, "max_price": max_price, "end_time": end_time.isoformat(), "images": [img for img in images_list if img], "bids": []})
        auction_id_counter += 1
    return redirect(url_for('admin'))

@app.route('/delete-auction/<int:a_id>', methods=['POST'])
def delete_auction(a_id):
    global auctions
    auctions = [a for a in auctions if a['id'] != a_id]
    return redirect(url_for('admin'))

@app.route('/reviews')
def reviews_page():
    if not site_controls['enable_reviews_page']: return redirect(url_for('index'))
    return render_template_string(reviews_page_template, reviews=reviews, config=site_config)

@app.route('/product/<int:p_id>')
def product_detail(p_id):
    global products
    product = next((p for p in products if p['id'] == p_id), None)
    if not product: return redirect(url_for('index'))
    product['views'] = product.get('views', 0) + 1
    return render_template_string(product_detail_template, product=product, config=site_config, controls=site_controls, vis=text_visibility, error=None)

@app.route('/copyright')
def copyright_page():
    if not site_controls['enable_copyright']: return redirect(url_for('index'))
    return render_template_string(copyright_template, text=site_controls['copyright_text'])

@app.route('/update-code', methods=['POST'])
def update_code():
    global current_html_template
    new_code = request.form.get('custom_html', '').strip()
    if new_code: current_html_template = new_code
    return redirect(url_for('admin'))

@app.route('/add-review', methods=['POST'])
def add_review():
    global review_id_counter, reviews
    name = request.form.get('reviewer_name', '').strip()
    comment = request.form.get('reviewer_comment', '').strip()
    try: rating = int(request.form.get('rating', 5))
    except ValueError: rating = 5
    if name and comment:
        reviews.insert(0, {"id": review_id_counter, "name": name, "rating": rating, "comment": comment})
        review_id_counter += 1
    return redirect(url_for('reviews_page'))

@app.route('/delete-review/<int:r_id>', methods=['POST'])
def delete_review(r_id):
    global reviews
    reviews = [r for r in reviews if r['id'] != r_id]
    return redirect(url_for('admin'))

@app.route('/add-note', methods=['POST'])
def add_note():
    global note_id_counter
    title = request.form.get('note_title', '').strip()
    content = request.form.get('note_content', '').strip()
    images_list = [process_and_compress_image(f) for f in request.files.getlist('note_images') if f and f.filename != '']
    if title and content:
        notes.insert(0, {"id": note_id_counter, "title": title, "content": content, "images": [img for img in images_list if img]})
        note_id_counter += 1
    return redirect(url_for('admin'))

@app.route('/delete-note/<int:n_id>', methods=['POST'])
def delete_note(n_id):
    global notes
    notes = [n for n in notes if n['id'] != n_id]
    return redirect(url_for('admin'))

@app.route('/add', methods=['POST'])
def add_product():
    global product_id_counter
    if site_controls['block_posting']: return redirect(url_for('index'))
    title = request.form.get('title')
    raw_price = request.form.get('price', '')
    price = format_price(raw_price)
    quantity = request.form.get('quantity', '1').strip()
    description = request.form.get('description', '').strip()
    images_list = [process_and_compress_image(f) for f in request.files.getlist('images') if f and f.filename != '']
    numeric_price = 0.0
    try: numeric_price = float(re.sub(r'[^0-9.]', '', str(raw_price)))
    except Exception: pass
    if title:
        products.insert(0, {"id": product_id_counter, "title": title, "price": price, "numeric_price": numeric_price, "quantity": quantity, "description": description, "contact_type": "phone", "contact_value": "", "images": [img for img in images_list if img], "is_sold": False, "views": 0})
        product_id_counter += 1
    return redirect(url_for('index'))

@app.route('/admin-add-product', methods=['POST'])
def admin_add_product():
    global product_id_counter
    title = request.form.get('title')
    raw_price = request.form.get('price', '')
    price = format_price(raw_price)
    quantity = request.form.get('quantity', '1').strip()
    description = request.form.get('description', '').strip()
    images_list = [process_and_compress_image(f) for f in request.files.getlist('images') if f and f.filename != '']
    numeric_price = 0.0
    try: numeric_price = float(re.sub(r'[^0-9.]', '', str(raw_price)))
    except Exception: pass
    if title:
        products.insert(0, {"id": product_id_counter, "title": title, "price": price, "numeric_price": numeric_price, "quantity": quantity, "description": description, "contact_type": "phone", "contact_value": "", "images": [img for img in images_list if img], "is_sold": False, "views": 0})
        product_id_counter += 1
    return redirect(url_for('admin'))

@app.route('/update-logo', methods=['POST'])
def update_logo():
    global site_controls
    site_controls['use_logo_image'] = True if request.form.get('use_logo_image') else False
    site_controls['enable_logo_pulse'] = True if request.form.get('enable_logo_pulse') else False
    
    anim_style = request.form.get('logo_animation_style')
    if anim_style:
        site_controls['logo_animation_style'] = anim_style
        
    speed = request.form.get('logo_speed') or request.form.get('logo_pulse_speed')
    if speed:
        site_controls['logo_pulse_speed'] = speed
        
    color = request.form.get('logo_pulse_color')
    if color:
        site_controls['logo_pulse_color'] = color
        
    size = request.form.get('logo_size')
    if size:
        site_controls['logo_size'] = size

    logo_file = request.files.get('logo_file')
    if logo_file and logo_file.filename != '':
        comp_logo = process_and_compress_image(logo_file)
        if comp_logo: site_controls['logo_image'] = comp_logo
    return redirect(url_for('admin'))

@app.route('/update-controls', methods=['POST'])
def update_controls():
    global site_controls
    site_controls['enable_cart'] = True if request.form.get('enable_cart') == 'on' else False
    site_controls['enable_auctions'] = True if request.form.get('enable_auctions') == 'on' else False
    site_controls['enable_scroll_top'] = True if request.form.get('enable_scroll_top') == 'on' else False
    site_controls['enable_forgot_pass'] = True if request.form.get('enable_forgot_pass') == 'on' else False
    site_controls['block_posting'] = True if request.form.get('block_posting') == 'on' else False
    site_controls['enable_search'] = True if request.form.get('enable_search') == 'on' else False
    site_controls['enable_contact_btn'] = True if request.form.get('enable_contact_btn') == 'on' else False
    site_controls['enable_socials'] = True if request.form.get('enable_socials') == 'on' else False
    site_controls['enable_copyright'] = True if request.form.get('enable_copyright') == 'on' else False
    site_controls['enable_reviews_page'] = True if request.form.get('enable_reviews_page') == 'on' else False
    return redirect(url_for('admin'))

@app.route('/update-texts', methods=['POST'])
def update_texts():
    global site_config, text_visibility
    for key in site_config['texts']:
        form_txt = request.form.get(f'txt_{key}')
        if form_txt: site_config['texts'][key] = form_txt
        text_visibility[key] = True if request.form.get(f'vis_{key}') == 'on' else False
    return redirect(url_for('admin'))

@app.route('/update-config', methods=['POST'])
def update_config():
    global site_config, site_controls
    site_config['title'] = request.form.get('title', site_config['title'])
    site_config['subtitle'] = request.form.get('subtitle', site_config['subtitle'])
    site_controls['enable_bg_overlay'] = True if request.form.get('enable_bg_overlay') == 'on' else False
    for key in site_config['colors']:
        val = request.form.get(f'c_{key}')
        if val: site_config['colors'][key] = val
    bg_file = request.files.get('bg_image_file')
    if bg_file and bg_file.filename != '':
        comp_bg = process_and_compress_image(bg_file)
        if comp_bg: site_config['bg_image'] = comp_bg
    return redirect(url_for('admin'))

@app.route('/delete/<int:p_id>', methods=['POST'])
def delete_product(p_id):
    global products
    products = [p for p in products if p['id'] != p_id]
    return redirect(url_for('admin'))

@app.route('/toggle-sold/<int:p_id>', methods=['POST'])
def toggle_sold(p_id):
    global products
    for p in products:
        if p['id'] == p_id: p['is_sold'] = not p.get('is_sold', False)
    return redirect(url_for('admin'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    global ADMIN_PASSWORD, current_html_template, login_attempts, lockout_until, site_stats
    authorized = False
    error = False
    current_time = time.time()
    is_locked = current_time < lockout_until
    remaining_seconds = int(lockout_until - current_time) if is_locked else 0
    if request.method == 'POST':
        if is_locked:
            return render_template_string(admin_template, products=products, auctions=auctions, notes=notes, reviews=reviews, config=site_config, controls=site_controls, vis=text_visibility, stats=site_stats, authorized=False, error=True, is_locked=True, remaining_seconds=remaining_seconds, raw_template=current_html_template, color_names_ar=color_names_ar)
        if request.form.get('password') == ADMIN_PASSWORD:
            authorized = True
            login_attempts = 0
        else:
            error = True
            login_attempts += 1
            if login_attempts >= 5:
                lockout_until = current_time + 900
                is_locked = True
                remaining_seconds = 900
                login_attempts = 0
    remaining_attempts = max(0, 5 - login_attempts)
    return render_template_string(admin_template, products=products, auctions=auctions, notes=notes, reviews=reviews, config=site_config, controls=site_controls, vis=text_visibility, stats=site_stats, authorized=authorized, error=error, is_locked=is_locked, remaining_seconds=remaining_seconds, remaining_attempts=remaining_attempts, raw_template=current_html_template, color_names_ar=color_names_ar)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
