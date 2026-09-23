import streamlit as st
import pandas as pd
import sqlite3
import os
import shutil
import json
import random
import urllib.parse
from PIL import Image
from datetime import datetime
import altair as alt

# --- YENİ EKLENEN BULUT BAĞLANTISI ---
from supabase import create_client, Client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"] 

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_connection()
# ------------------------------------

# --- ÖZEL CSS ---
st.set_page_config(page_title="ÖTS - Öğrenci Takip Sistemi", page_icon="🎓", layout="wide")

st.markdown("""
<style>
    /* ================= SOL PANEL (SİMSARİ ve ASİL ALTIN SARISI DÖNÜŞÜMÜ) ================= */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #c5a059 0%, #a37d3d 100%) !important;
    }

    /* Sol menüdeki tüm ana başlıklar ve logolu yazılar */
    [data-testid="stSidebar"] *, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        color: #1a1a1a !important; /* Altın fon üzerinde muazzam duran koyu kontrast tonu */
        font-weight: 600 !important;
    }

    /* Sol paneldeki seçim kutularının ve radyo butonlarının arka planını şeffaf yapıp yazıları beyaz yapma */
    [data-testid="stSidebar"] div[role="radiogroup"],
    [data-testid="stSidebar"] div[data-baseweb="select"] > div,
    [data-testid="stSidebar"] input {
        background-color: transparent !important; /* Kutunun içindeki siyahlığı kaldırır, arka plan görünür */
        border: 1px solid rgba(255, 255, 255, 0.4) !important; /* Hafif şeffaf beyaz çerçeve */
        border-radius: 8px !important;
    }

    /* Kutunun içindeki tüm yazıları net beyaz yapma */
    [data-testid="stSidebar"] div[role="radiogroup"] label p,
    [data-testid="stSidebar"] div[role="radiogroup"] label span,
    [data-testid="stSidebar"] div[data-baseweb="select"] * {
        color: #ffffff !important; /* Yazılar pırıl pırıl beyaz */
    }

    /* Kutuların içindeki yazıları SİMSİYAH ZEMİN ÜZERİNDE BEYAZ YAPALIM */
    [data-testid="stSidebar"] div[role="radiogroup"] label p,
    [data-testid="stSidebar"] div[role="radiogroup"] label span,
    [data-testid="stSidebar"] div[data-baseweb="select"] * {
        color: #ffffff !important; /* Kutunun içindeki yazılar net beyaz */
    }

    /* Seçili olan menü öğesi */
    [data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] p {
        color: #ebd197 !important; /* Seçilince altın sarısı parlasın */
        font-weight: 700 !important;
    }


    /* ================= SAĞ TARAF (ANA SAYFA VE SAYAÇLAR) ================= */
    .stApp {
        background-color: #f8fafc !important;
    }

    /* Üst Karşılama Bannerı (Altın ve Koyu Asil Uyumlu) */
    .ots-header {
        background: linear-gradient(135deg, #141a24 0%, #222e42 100%);
        padding: 22px 28px;
        border-radius: 14px;
        color: white;
        border-left: 6px solid #c5a059;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .ots-header h1 {
        color: #ebd197 !important;
        font-size: 25px !important;
        margin: 0 0 6px 0 !important;
        font-weight: 700 !important;
    }
    .ots-header p {
        color: #cbd5e1 !important;
        margin: 0 !important;
        font-size: 14px !important;
    }

    /* Sayaç Kutuları */
    .sayac-kutu {
        background: #ffffff;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        border: 1px solid #e2e8f0;
        border-top: 4px solid #c5a059;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .sayac-baslik {
        font-size: 13px;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .sayac-sayi {
        font-size: 32px;
        font-weight: 800;
        color: #1e293b;
        margin: 6px 0;
    }
    .sayac-alt {
        font-size: 12px;
        color: #94a3b8;
    }

    /* Buton Tasarımları */
    .stButton > button {
        background: linear-gradient(90deg, #c5a059 0%, #ebd197 100%) !important;
        color: #0f172a !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 12px rgba(197, 160, 89, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 18px rgba(197, 160, 89, 0.5) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 0. GÜVENLİK VE GİRİŞ (LOGIN) EKRANI ---
if 'giris_yapildi' not in st.session_state:
    st.session_state['giris_yapildi'] = False
if 'rol' not in st.session_state:
    st.session_state['rol'] = None
if 'kilitli_ogrenci_id' not in st.session_state:
    st.session_state['kilitli_ogrenci_id'] = None
# YENİ SAAS KİLİDİ: Sisteme giren öğretmenin veya öğrencinin kime ait olduğunu tutar
if 'aktif_ogretmen_id' not in st.session_state:
    st.session_state['aktif_ogretmen_id'] = None

if not st.session_state['giris_yapildi']:
    # ==========================================
    # 💎 FERAH & AYDINLIK GİRİŞ EKRANI TASARIMI
    # ==========================================
    st.markdown("""
    <style>
    /* Tüm sayfanın arka planı */
    .stApp {
        background-color: #f8fafc;
        background-image: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);
        color: #1e293b;
    }
    header {visibility: hidden;}
    
    /* Giriş Kutusunun Tasarımı */
    [data-testid="stForm"] {
        background-color: rgba(255, 255, 255, 0.85) !important;
        border: 2px solid #d4af37 !important;
        border-radius: 15px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);
        padding: 30px;
        backdrop-filter: blur(10px);
    }
    .stTextInput input {
        background-color: #ffffff !important;
        color: #1e293b !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 8px;
        font-weight: bold;
        transition: 0.3s;
    }
    .stTextInput input:focus {
        border: 2px solid #d4af37 !important;
        box-shadow: 0 0 5px rgba(212, 175, 55, 0.3) !important;
    }
    .stTextInput p {
        color: #334155 !important;
        font-size: 15px;
        font-weight: 700;
    }
    [data-testid="stFormSubmitButton"] button {
        background: linear-gradient(90deg, #d4af37, #f1c40f) !important;
        color: #101725 !important;
        font-weight: 900 !important;
        font-size: 18px !important;
        border: none !important;
        border-radius: 8px !important;
        transition: 0.3s !important;
        width: 100% !important;
        padding: 10px !important;
    }
    [data-testid="stFormSubmitButton"] button:hover {
        transform: scale(1.02);
        box-shadow: 0 8px 20px rgba(212, 175, 55, 0.4);
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        c_resim1, c_resim2, c_resim3 = st.columns([1, 2, 1])
        with c_resim2:
            try:
                st.image("karikatur.png", use_container_width=True) 
            except:
                st.markdown("<div style='text-align: center; font-size: 60px;'>👑</div>", unsafe_allow_html=True)
                
        st.markdown("<h1 style='text-align: center; color: #b8860b; margin-bottom: 0px; text-shadow: 1px 1px 2px rgba(0,0,0,0.1); letter-spacing: 2px;'>EMİR HOCA</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; font-size: 18px; margin-top: 5px; margin-bottom: 25px;'>Öğrenci Takip ve Eğitim Koçluğu Portalı</p>", unsafe_allow_html=True)

        with st.form("giris_formu"):
            st.markdown("<div style='text-align:center; color:#475569; font-size:15px; margin-bottom:15px;'>👋 Sistemi kullanmak için giriş yapınız.</div>", unsafe_allow_html=True)
            
            k_adi = st.text_input("Kullanıcı Adı (Öğretmenler) veya Telefon Numarası (Veliler):")
            k_sifre = st.text_input("Şifre:", type="password")
            
            if st.form_submit_button("Sisteme Giriş Yap", type="primary", use_container_width=True):
                temiz_k_adi = str(k_adi).replace(" ", "").strip()
                temiz_k_sifre = str(k_sifre).replace(" ", "").strip()

                # 1. BULUTTAN ÖĞRETMEN SORGULAMASI (Çoklu Öğretmen Mimarisi)
                ogretmen_sorgu = supabase.table("ogretmenler").select("*").eq("kullanici_adi", temiz_k_adi).eq("sifre", temiz_k_sifre).execute()
                
                if len(ogretmen_sorgu.data) > 0:
                    st.session_state['giris_yapildi'] = True
                    st.session_state['rol'] = "ADMIN"
                    st.session_state['aktif_ogretmen_id'] = ogretmen_sorgu.data[0]['id'] # Odanın kilidini aldık
                    st.rerun()
                
                # 2. BULUTTAN ÖĞRENCİ/VELİ SORGULAMASI
                else:
                    temiz_k_sifre_kucuk = temiz_k_sifre.lower()
                    ogrenci_sorgu = supabase.table("ogrenciler").select("id, ad_soyad, veli_telefon, ogretmen_id").eq("veli_telefon", temiz_k_adi).execute()
                    
                    giris_basarili = False
                    for row in ogrenci_sorgu.data:
                        db_ad_temiz = str(row['ad_soyad']).replace(" ", "").strip().lower()
                        beklenen_sifre = f"{db_ad_temiz}42."
                        
                        if temiz_k_sifre_kucuk == beklenen_sifre:
                            st.session_state['giris_yapildi'] = True
                            st.session_state['rol'] = "OGRENCI"
                            st.session_state['kilitli_ogrenci_id'] = row['id']
                            st.session_state['aktif_ogretmen_id'] = row['ogretmen_id'] # Öğrenciyi sadece kendi hocasının alanına hapseder
                            giris_basarili = True
                            break
                            
                    if giris_basarili:
                        st.rerun()
                    else:
                        st.error("Hatalı kullanıcı adı veya şifre! Lütfen bilgilerinizi kontrol edin.")
    
    st.stop()

# --- ÇIKIŞ YAP BUTONU ---
c_ust1, c_ust2 = st.columns([10, 1])
with c_ust2:
    if st.button("🚪 Çıkış"):
        st.session_state.clear()
        st.rerun()

# --- 1. MÜFREDAT HARİTASI (SENİN GÜNCELLEDİĞİN LİSANS KONULARIYLA) ---
SINAV_MÜFREDATI = {
    "TYT": {
        "TYT Türkçe": ["Ses Bilgisi", "Yazım Kuralları", "Noktalama İşaretleri", "Sözcükte Yapı","İsim(Ad)","Sıfat(Ön Ad)","Zamir(Adıl)","Tamlamalar","Zarf(Belirteç)","Edat-Bağlaç-Ünlem","Fiilde Yapı-Ek Fiil","Fiilimsiler","Fiilde Çatı","Söz Grupları","Cümlenin Ögeleri","Cümle Türleri","Anlatım Bozuklukları","Sözcükte Anlam","Cümlede Anlam","Paragrafta Anlatım Biçimleri ve Düşünceyi Geliştirme Yolları","Paragrafta Anlam","Paragrafta Yapı","Paragrafta Öncüllü Sorular","Paragrafta Yeni Nesil Yorumlama ", "Sözcük Türleri",],
        "TYT Matematik": ["Temel Kavramlar", "Sayı Basamakları", "Bölünebilme Kuralları", "EBOB-EKOK", "Rasyonel Sayılar", "Basit Eşitsizlikler", "Mutlak Değer", "Üslü Sayılar", "Köklü Sayılar", "Çarpanlara Ayırma", "Oran-Orantı", "Problemler", "Kümeler", "Mantık", "Fonksiyonlar", "Polinomlar", "2. Dereceden Denklemler", "Permütasyon-Kombinasyon-Olasılık", "Veri-İstatistik"],
        "TYT Geometri": ["Doğruda ve Üçgende Açılar", "Özel Üçgenler", "Çokgenler", "Dörtgenler", "Çember ve Daire", "Analitik Geometri", "Katı Cisimler"],
        "TYT Fizik": ["Fizik Bilimine Giriş", "Madde ve Özellikleri", "Hareket ve Kuvvet", "İş, Güç ve Enerji", "Isı, Sıcaklık ve Genleşme", "Elektrostatik", "Elektrik ve Manyetizma", "Basınç ve Kaldırma Kuvveti", "Dalgalar", "Optik"],
        "TYT Kimya": ["Kimya Bilimi", "Atom ve Periyodik Sistem", "Kimyasal Türler Arası Etkileşimler", "Maddenin Halleri", "Doğa ve Kimya", "Kimyanın Temel Kanunları", "Karışımlar", "Asitler, Bazlar ve Tuzlar", "Kimya Her Yerde"],
        "TYT Biyoloji": ["Canlıların Ortak Özellikleri", "Temel Bileşenler", "Hücre", "Madde Geçişleri", "Canlıların Sınıflandırılması", "Hücre Bölünmeleri", "Kalıtım", "Ekoloji"],
        "TYT Tarih": ["Tarih Bilimi", "İlk ve Orta Çağlarda Türk Dünyası", "İslam Medeniyeti", "Türklerin İslamiyet'i Kabulü", "Osmanlı Devleti", "Atatürk İlke ve İnkılapları", "Milli Mücadele Dönemi"],
        "TYT Coğrafya": ["Doğa ve İnsan", "Dünya'nın Şekli ve Hareketleri", "Harita Bilgisi", "İklim Bilgisi", "İç ve Dış Kuvvetler", "Nüfus ve Yerleşme", "Ekonomik Faaliyetler", "Bölgeler", "Doğal Afetler"]
    },
    "AYT Sayısal": {
        "AYT Matematik": ["Fonksiyonlarda Uygulamalar", "Denklem ve Eşitsizlik Sistemleri", "Parabol", "Trigonometri", "Logaritma", "Diziler", "Limit ve Süreklilik", "Türev", "İntegral"],
        "AYT Geometri": ["Çemberin Analitik İncelenmesi", "Dönüşüm Geometrisi", "Trigonometrik Geometri", "Uzay Geometrisi"],
        "AYT Fizik": ["Vektörler ve Bağıl Hareket", "Newton’ın Hareket Yasaları", "Atışlar", "İtme ve Momentum", "Tork ve Denge", "Elektriksel Kuvvet ve Alan", "Manyetizma", "Çembersel Hareket", "Basit Harmonik Hareket", "Dalga Mekaniği", "Modern Fizik"],
        "AYT Kimya": ["Modern Atom Teorisi", "Gazlar", "Sıvı Çözeltiler", "Kimyasal Tepkimelerde Enerji", "Tepkimelerde Hız ve Denge", "Asit-Baz Dengesi", "KÇÇ", "Kimya ve Elektrik (Elektrokimya)", "Organik Kimyaya Giriş", "Organik Bileşikler"],
        "AYT Biyoloji": ["İnsan Fizyolojisi (Sistemler)", "Komünite ve Popülasyon Ekolojisi", "Genden Proteine", "Hücresel Solunum ve Fotosentez", "Bitki Biyolojisi", "Canlılar ve Çevre"]
    },
    "AYT Eşit Ağırlık": {
        "AYT Matematik": ["Fonksiyonlarda Uygulamalar", "Denklem ve Eşitsizlik Sistemleri", "Parabol", "Trigonometri", "Logaritma", "Diziler", "Limit ve Süreklilik", "Türev", "İntegral"],
        "AYT Edebiyat": ["Anlam Bilgisi", "Şiir Bilgisi", "Edebi Sanatlar", "Halk Edebiyatı", "Divan Edebiyatı", "Tanzimat, Servetifünun, Fecriati", "Milli Edebiyat", "Cumhuriyet Dönemi Türk Edebiyatı", "Edebi Akımlar"],
        "AYT Tarih-1": ["İlk Çağ Uygarlıkları", "İslamiyet Öncesi Türk Tarihi", "İslam Tarihi", "Türkiye Selçuklu Devleti", "Osmanlı Siyasi Tarihi ve Kültür Medeniyeti", "20. Yüzyıl Başlarında Osmanlı", "Milli Mücadele", "Atatürkçülük ve Türk İnkılabı"],
        "AYT Coğrafya-1": ["Ekstrem Doğa Olayları", "Küresel İklim Değişimi", "Şehirler ve Etki Alanları", "Türkiye'de Nüfus, Tarım ve Hayvancılık", "Türkiye'de Madenler ve Sanayi", "Küresel ve Bölgesel Örgütler", "Çevre Sorunları"]
    },
    "AYT Sözel": {
        "AYT Edebiyat": ["Anlam Bilgisi", "Şiir Bilgisi", "Edebi Sanatlar", "Halk Edebiyatı", "Divan Edebiyatı", "Tanzimat, Servetifünun, Fecriati", "Milli Edebiyat", "Cumhuriyet Dönemi Türk Edebiyatı", "Edebi Akımlar"],
        "AYT Tarih (Tüm)": ["Tarih ve Zaman", "İslamiyet Öncesi Türk Tarihi", "İslam Tarihi", "Türkiye Selçuklu Devleti", "Osmanlı Devleti", "İnkılap Tarihi", "Çağdaş Türk ve Dünya Tarihi"],
        "AYT Coğrafya (Tüm)": ["Biyoçeşitlilik", "Şehirlerin Etki Alanları", "Türkiye'nin Ekonomi Politikaları", "Türkiye'de Tarım, Maden ve Sanayi", "Hizmet Sektörü", "Küresel ve Bölgesel Örgütler", "Çevre ve Toplum"],
        "AYT Felsefe Grubu": ["Psikolojinin Temel Süreçleri", "Öğrenme, Bellek, Düşünme", "Ruh Sağlığı", "Sosyolojiye Giriş", "Birey ve Toplum", "Toplumsal Kurumlar", "Klasik Mantık", "Sembolik Mantık"],
        "AYT Din Kültürü": ["İslam ve Bilim", "Anadolu'da İslam", "İslam Düşüncesinde Tasavvufi Yorumlar", "Güncel Dini Meseleler", "Hint ve Çin Dinleri"]
    },
    "KPSS Lisans (GK-GY)": {
        "Lisans Türkçe": ["Ses Bilgisi", "Yazım Kuralları", "Noktalama İşaretleri", "Sözcükte Yapı(Kök Bilgisi)", "Sözcükte Yapı(Ekler)", "Sözcükte Yapı(Yapı Bilgisi)", "Sözcük Türleri(İsim ve Tamlamalar)", "Sözcük Türleri(Zamirler)", "Sözcük Türleri(Sıfatlar)", "Sözcük Türleri(Zarflar)", "Sözcük Türleri(Edat)", "Fiiler", "Fiilimsiler", "Cümle Türleri", "Cümlenin Ögeleri", "Anlatım Bozukluğu", "Sözcükte Anlam", "Cümlede Anlam", "Paragrafta Anlam", "Sözel Mantık"],
        "Lisans Matematik": ["İşlem Yeteneği", "Temel Kavramlar", "Tek - Çift - Pozitif - Negatif Sayılar", "Ardışık Sayılar", "Faktöriyel", "Sayı Basamakları ve Taban Aritmetiği", "Bölme - Bölünebilme", "Asal Çarpanlara Ayırma", "EBOB - EKOK", "Rasyonel Sayılar", "Basit Eşitsizlikler", "Mutlak Değer", "Üslü Sayılar", "Köklü Sayılar", "Çarpanlara Ayırma", "Oran - Orantı", "Birinci Dereceden Denklemler", "Sayı Problemleri", "Kesir Problemleri", "Yaş Problemleri", "Hareket Problemleri", "İşçi - Havuz Problemleri", "Yüzde - Kâr - Zarar - Faiz Problemleri", "Karışım Problemleri", "Grafik Problemleri", "Kümeler", "İşlem - Modüler Aritmetik", "Permütasyon - Kombinasyon - Olasılık", "Fonksiyonlar", "Sayısal Mantık", "Üçgenler", "Çokgenler - Dörtgenler", "Çember - Daire", "Katı Cisimler", "Analitik Geometri"],
        "Lisans Tarih": ["İslamiyet Öncesi Türk Tarihi", "İlk Türk - İslam Devletleri", "Anadolu (Türkiye) Selçuklu Devleti", "Osmanlı Devleti Kültür ve Medeniyeti", "Osmanlı Devleti Kuruluş Dönemi (1299 - 1453)", "Osmanlı Devleti Yükselme Dönemi (1453 - 1595)", "XVII. Yüzyılda Osmanlı Devleti (Duraklama Dönemi) (1595 - 1699)", "XVIII. Yüzyılda Osmanlı Devleti (Gerileme Dönemi) (1699 - 1792)", "XIX. Yüzyılda Osmanlı Devleti (Dağılma Dönemi) (1792 - 1922)", "XX. Yüzyıl Başlarında Osmanlı Devleti", "Mondros Ateşkes Antlaşması ve İlk İşgaller", "Millî Mücadele Hazırlık Dönemi", "I. TBMM Dönemi ve Gelişmeleri (1920 - 1923)", "Millî Mücadele Muharebeler Dönemi", "Atatürk'ün Hayatı", "Atatürk Dönemi İç Politika", "Atatürk İlkeleri", "Atatürk İnkılapları", "Atatürk Dönemi Türk Dış Politikası", "Cumhuriyet Dönemi Kültür ve Medeniyeti", "XX. Yüzyıl Başlarında Dünya (1918 - 1939)", "II. Dünya Savaşı (1939 - 1945)", "Soğuk Savaş Dönemi (1947 - 1990)", "Yumuşama Dönemi (1961 - 1990)", "Küreselleşen Dünya"],
        "Lisans Coğrafya": ["Türkiye'nin Coğrafi Konumu", "İklim", "Türkiye'nin Yeryüzü Şekilleri", "Dağlar", "Akarsular", "Platolar", "Ovalar", "Göller", "Doğal Afetler", "Dış Kuvvetler", "Türkiye'de Nüfus", "Türkiye'de Tarım", "Türkiye'de Hayvancılık", "Madenler", "Sanayi", "Ulaşım - Ticaret - Turizm", "Projeler"],
        "Lisans Vatandaşlık": ["Hukukun Temel Kavramları", "Anayasa Hukukuna Giriş", "1982 Anayasası Genel Esasları", "Temel Hak ve Hürriyetler", "Yasama", "Yürütme", "Yargı", "İdare Hukuku", "İnsan Hakları"]
    },
    "KPSS Eğitim Bilimleri": {
        "Gelişim Psikolojisi": ["Bilişsel Gelişim", "Kişilik Gelişimi", "Ahlak Gelişimi", "Fiziksel Gelişim"],
        "Öğrenme Psikolojisi": ["Klasik Koşullanma", "Edimsel Koşullanma", "Sosyal Öğrenme", "Bilgi İşleme Kuramı", "Gestalt Kuramı"],
        "Öğretim İlke ve Yöntemleri": ["Öğretim İlkeleri", "Öğretim Modelleri", "Öğretim Stratejileri", "Öğretim Yöntem ve Teknikleri", "Kavram Öğretimi"],
        "Ölçme ve Değerlendirme": ["Temel Kavramlar", "Hata Türleri ve Korelasyon", "Güvenilirlik ve Geçerlilik", "Ölçme Araçları", "Test ve Madde İstatistikleri"],
        "Program Geliştirme": ["Eğitimin Temel Kavramları", "Program Tasarımı ve Modelleri", "İhtiyaç Belirleme", "İçerik Düzenleme Yaklaşımları"],
        "Rehberlik": ["Rehberlik Türleri ve İlkeleri", "Öğrenci Kişilik Hizmetleri", "Bireyi Tanıma Teknikleri", "Özel Eğitim"]
    },
    "KPSS ÖABT Lise Matematik": {
        "ÖABT Analiz (%24)": ["Fonksiyonlar, Limit ve Süreklilik", "Türev ve Uygulamaları", "İntegral ve Uygulamaları", "Diziler ve Seriler", "Çok Değişkenli Fonksiyonlar"],
        "ÖABT Cebir (%16)": ["Mantık, Kümeler ve Bağıntı", "Soyut Cebir (Grup, Halka, Cisim)", "Lineer Cebir (Matris, Determinant)", "Vektör Uzayları ve Lineer Dönüşümler", "Sayılar Teorisi"],
        "ÖABT Geometri (%16)": ["Analitik Geometri (Düzlem ve Uzay)", "Sentetik Geometri (Çokgenler, Çember)", "Dönüşümler Geometrisi"],
        "ÖABT Uygulamalı Matematik (%24)": ["Diferansiyel Denklemler (1. ve Yüksek Mertebe)", "Laplace Dönüşümleri", "Olasılık ve İstatistik (Dağılımlar)"],
        "ÖABT Alan Eğitimi (%20)": ["Matematik Öğretim Yaklaşımları", "Kavram Yanılgıları ve Giderilmesi", "Lise Matematik Öğretim Programı", "Problem Çözme Süreçleri"]
    },
    "KPSS ÖABT İlköğretim Matematik": {
        "ÖABT Analiz": ["Fonksiyonlar ve Limit", "Türev ve Uygulamaları", "İntegral ve Uygulamaları", "Diziler ve Seriler"],
        "ÖABT Cebir": ["Soyut Matematik (Kümeler, Mantık)", "Lineer Cebir (Matris, Determinant, Vektör)", "Sayılar Teorisi", "Soyut Cebir"],
        "ÖABT Geometri": ["Düzlem Geometrisi", "Analitik Geometri", "Dönüşümler Geometrisi"],
        "ÖABT Uygulamalı Matematik": ["Diferansiyel Denklemler", "Olasılık ve İstatistik"],
        "ÖABT Alan Eğitimi": ["Ortaokul Matematik Öğretim Programı", "Kavram Yanılgıları", "Öğretim Yöntem ve Teknikleri"]
    },
    "AGS (Akademi Giriş Sınavı)": {
        "Sözel Yetenek": ["Sözcükte Anlam", "Cümlede Anlam", "Anlatımın Oluşması", "Paragrafta Anlam", "Sözel Mantık"],
        "Sayısal Yetenek": ["Temel Matematik", "Grafik ve Tablo Yorumlama", "Mantıksal Muhakeme Problemleri"],
        "Tarih": ["Osmanlı Öncesi Türk Devletleri Tarihi (Siyasal, sosyal, ekonomik ve kültürel gelişmeler)", "Osmanlı Tarihi (XIII. yüzyıldan XX. yüzyıl başlarına kadar yaşanan siyasal, sosyal, ekonomik ve kültürel gelişmeler)", "Atatürk İlkeleri ve İnkılap Tarihi (XX. yüzyıl başından XX. yüzyılın ortalarına kadar, Osmanlı Devleti'nin yıkılışından İkinci Dünya Savaşı'nın sonuna kadar Türkiye tarihinde yaşanan siyasal, sosyal, ekonomik ve kültürel gelişmeler)", "Çağdaş Türk ve Dünya Tarihi (XX. yüzyılın başlangıcından günümüze kadar dünyada; İkinci Dünya Savaşı'ndan günümüze kadar Türkiye'de yaşanan siyasal, sosyal, ekonomik ve kültürel gelişmeler)"],
        "Türkiye Coğrafyası": ["Türkiye Fiziki Coğrafyası", "Türkiye Beşerî ve Ekonomik Coğrafyası"],
        "Eğitim Bilimleri ve Türk Millî Eğitim Sistemi": ["Eğitim Tarihi, Felsefi, Toplumsal, Ekonomik ve Politik Temelleri", "Öğretim Yöntem ve Teknikleri", "Sınıf Yönetimi", "Program Okuryazarlığı", "Eğitimde Ölçme ve Değerlendirme", "Öğrenme Psikolojisi", "Gelişim Psikolojisi", "Rehberlik", "Eğitim ve Öğretim Teknolojileri", "Türk Millî Eğitim Sisteminin Genel Yapısı", "Türkiye Yüzyılı Maarif Modeli"],
        "Mevzuat": ["Türkiye Cumhuriyeti Anayasası (Kanun Numarası: 2709, Kabul Tarihi: 18/10/1982), İnsan Hakları Hukuku", "1739 sayılı Millî Eğitim Temel Kanunu", "222 sayılı İlköğretim ve Eğitim Kanunu", "7528 sayılı Öğretmenlik Mesleği Kanunu"]
    },
    "YDT(DİL)": {
        "İngilizce": [
            "Vocabulary (Kelime Bilgisi)",
            "Grammar (Gramer & Dilbilgisi)",
            "Cloze Test",
            "Cümle Tamamlama",
            "İngilizce - Türkçe Çeviri",
            "Türkçe - İngilizce Çeviri",
            "Paragraf Okuduğunu Anlama",
            "Diyalog Tamamlama",
            "Anlamca En Yakın Cümleyi Bulma (Restatement)",
            "Duruma Uygun Düşen Cümle (Situation)",
            "Paragraf Tamamlama",
            "Anlam Bütünlüğünü Bozan Cümle (Irrelevant)"
        ]
    },
    # ... AGS ve diğer mevcut sınavların burada bitiyor. Sonuna virgül koymayı unutma!
    
    "5. Sınıf": {
        "5. Sınıf Türkçe": [],
        "5. Sınıf Matematik": [],
        "5. Sınıf Fen Bilimleri": [],
        "5. Sınıf Sosyal Bilgiler": [],
        "5. Sınıf İngilizce": [],
        "5. Sınıf Din Kültürü": []
    },
    "6. Sınıf": {
        "6. Sınıf Türkçe": [],
        "6. Sınıf Matematik": [],
        "6. Sınıf Fen Bilimleri": [],
        "6. Sınıf Sosyal Bilgiler": [],
        "6. Sınıf İngilizce": [],
        "6. Sınıf Din Kültürü": []
    },
    "7. Sınıf": {
        "7. Sınıf Türkçe": [],
        "7. Sınıf Matematik": [],
        "7. Sınıf Fen Bilimleri": [],
        "7. Sınıf Sosyal Bilgiler": [],
        "7. Sınıf İngilizce": [],
        "7. Sınıf Din Kültürü": []
    },
    "8. Sınıf (LGS)": {
        "8. Sınıf Türkçe": [],
        "8. Sınıf Matematik": [],
        "8. Sınıf Fen Bilimleri": [],
        "8. Sınıf T.C. İnkılap Tarihi": [],
        "8. Sınıf İngilizce": [],
        "8. Sınıf Din Kültürü": []
    },
    "9. Sınıf": {
        "9. Sınıf Türk Dili ve Edebiyatı": [],
        "9. Sınıf Matematik": [],
        "9. Sınıf Fizik": [],
        "9. Sınıf Kimya": [],
        "9. Sınıf Biyoloji": [],
        "9. Sınıf Tarih": [],
        "9. Sınıf Coğrafya": [],
        "9. Sınıf İngilizce": []
    },
    "10. Sınıf": {
        "10. Sınıf Türk Dili ve Edebiyatı": [],
        "10. Sınıf Matematik": [],
        "10. Sınıf Fizik": [],
        "10. Sınıf Kimya": [],
        "10. Sınıf Biyoloji": [],
        "10. Sınıf Tarih": [],
        "10. Sınıf Coğrafya": [],
        "10. Sınıf İngilizce": []
    },
    "11. Sınıf": {
        "11. Sınıf Türk Dili ve Edebiyatı": [],
        "11. Sınıf Matematik": [],
        "11. Sınıf Fizik": [],
        "11. Sınıf Kimya": [],
        "11. Sınıf Biyoloji": [],
        "11. Sınıf Tarih": [],
        "11. Sınıf Coğrafya": [],
        "11. Sınıf İngilizce": []
    },
    "12. Sınıf": {
        "12. Sınıf Türk Dili ve Edebiyatı": [],
        "12. Sınıf Matematik": [],
        "12. Sınıf Fizik": [],
        "12. Sınıf Kimya": [],
        "12. Sınıf Biyoloji": [],
        "12. Sınıf T.C. İnkılap Tarihi": [],
        "12. Sınıf Coğrafya": [],
        "12. Sınıf İngilizce": []
    }
}

if not os.path.exists("ogrenci_fotolar"):
    os.makedirs("ogrenci_fotolar")

# --- 2. PUAN TAHMİN ALGORİTMASI ---
def puan_ve_siralama_tahmin_et(deneme_turu, toplam_net, netler_dict=None):
    if not netler_dict: netler_dict = {}
    if deneme_turu == "TYT Denemesi":
        puan = 100 + (toplam_net * 3.33)
        if toplam_net >= 100: sira = "1K - 20K"
        elif toplam_net >= 80: sira = "20K - 100K"
        elif toplam_net >= 60: sira = "100K - 300K"
        elif toplam_net >= 40: sira = "300K - 800K"
        else: sira = "800K+"
        return min(500, round(puan, 2)), sira
    elif "AGS" in deneme_turu:
        puan = 50.0 + (toplam_net * 0.625)
        return min(100, round(puan, 2)), "Belirsiz"
    elif "KPSS" in deneme_turu:
        puan = 45.0 + (toplam_net * 0.5)
        return min(100, round(puan, 2)), "Belirsiz"
    elif deneme_turu == "AYT Sayısal Denemesi":
        tyt_neti = netler_dict.get("TYT Toplam Neti", 0)
        ayt_neti = toplam_net - tyt_neti
        puan = 100 + (tyt_neti * 1.33) + (ayt_neti * 3.0) 
        if puan >= 450: sira = "1K - 20K"
        elif puan >= 350: sira = "20K - 100K"
        elif puan >= 250: sira = "100K - 300K"
        else: sira = "300K+"
        return min(500, round(puan, 2)), sira
    return 0, "-"

# --- 3. VERİTABANI İŞLEMLERİ (SUPABASE BULUT SİSTEMİ) ---
# UYARI: init_db() fonksiyonu kaldırıldı çünkü tablolar doğrudan Supabase bulutunda oluşturuldu.

def program_getir(ogrenci_id, hafta_adi):
    res = supabase.table("calisma_programi").select("*").eq("ogrenci_id", ogrenci_id).eq("hafta_adi", hafta_adi).execute()
    if len(res.data) > 0:
        row = res.data[0]
        return (row['pazartesi'], row['sali'], row['carsamba'], row['persembe'], row['cuma'], row['cumartesi'], row['pazar'], row['haftalik_not'])
    return None

def program_kaydet(ogrenci_id, hafta_adi, p, sa, ca, pe, cu, ct, pa, notu):
    res = supabase.table("calisma_programi").select("id").eq("ogrenci_id", ogrenci_id).eq("hafta_adi", hafta_adi).execute()
    data = {
        "ogrenci_id": ogrenci_id, "hafta_adi": hafta_adi,
        "pazartesi": p, "sali": sa, "carsamba": ca, "persembe": pe,
        "cuma": cu, "cumartesi": ct, "pazar": pa, "haftalik_not": notu
    }
    if len(res.data) > 0:
        supabase.table("calisma_programi").update(data).eq("ogrenci_id", ogrenci_id).eq("hafta_adi", hafta_adi).execute()
    else:
        supabase.table("calisma_programi").insert(data).execute()

def odev_ekle(ogrenci_id, ders, kaynak_konu, verilen_soru):
    tarih_bugun = datetime.now().strftime("%d.%m.%Y")
    data = {
        "ogrenci_id": ogrenci_id, "tarih": tarih_bugun, "ders": ders,
        "kaynak_konu": kaynak_konu, "verilen_soru": verilen_soru,
        "durum": "Bekleniyor"
    }
    supabase.table("odev_takip").insert(data).execute()

def konulari_ata(ogrenci_id, sinav_turleri_str):
    # 1. Veritabanındaki mevcut konuları alıyoruz
    res = supabase.table("konu_takip").select("id, ders, konu").eq("ogrenci_id", ogrenci_id).execute()
    mevcut_konular = {f"{row['ders']}-{row['konu']}": row['id'] for row in res.data}
    
    gruplar = sinav_turleri_str.split(', ') if sinav_turleri_str else []
    guncel_konular = set()
    
    # 2. Kodda şu an yazılı olan konuları bul ve Ekle
    for grup in gruplar:
        if grup in SINAV_MÜFREDATI:
            for ders, konular in SINAV_MÜFREDATI[grup].items():
                for konu in konular:
                    key = f"{ders}-{konu}"
                    guncel_konular.add(key)
                    if key not in mevcut_konular:
                        supabase.table("konu_takip").insert({"ogrenci_id": ogrenci_id, "ders": ders, "konu": konu, "durum": "Başlanmadı"}).execute()
                        
    # 3. Silinmiş/Eski Konuları Temizle
    for key, kayit_id in mevcut_konular.items():
        if key not in guncel_konular:
            supabase.table("konu_takip").delete().eq("id", kayit_id).execute()

def ogrenci_ekle(ogrenci_no, ad, tur_str, tel, v_ad, v_tel, hedef):
    # ÇOKLU ÖĞRETMEN KİLİDİ: Öğrenci, o an giriş yapan öğretmenin ID'si ile kaydedilir
    aktif_ogretmen = st.session_state.get('aktif_ogretmen_id') 
    
    data = {
        "ogretmen_id": aktif_ogretmen,
        "ogrenci_no": ogrenci_no, "ad_soyad": ad, "sinav_turu": tur_str,
        "telefon": tel, "veli_ad": v_ad, "veli_telefon": v_tel
    }
    res = supabase.table("ogrenciler").insert(data).execute()
    if res.data:
        ogr_id = res.data[0]['id']
        konulari_ata(ogr_id, tur_str)

def deneme_ekle(ogrenci_id, deneme_adi, deneme_turu, kapsam, net_sozlugu, cozulen_soru):
    tarih_bugun = datetime.now().strftime("%Y-%m-%d")
    netler_json = json.dumps(net_sozlugu)
    toplam_net = sum(net_sozlugu.values())
    data = {
        "ogrenci_id": ogrenci_id, "tarih": tarih_bugun, "deneme_adi": deneme_adi,
        "deneme_turu": deneme_turu, "kapsam": kapsam, "netler_json": netler_json,
        "toplam_net": toplam_net, "cozulen_soru": cozulen_soru
    }
    supabase.table("denemeler").insert(data).execute()

def ogrenci_sil(ogrenci_id):
    supabase.table("denemeler").delete().eq("ogrenci_id", ogrenci_id).execute()
    supabase.table("konu_takip").delete().eq("ogrenci_id", ogrenci_id).execute()
    supabase.table("calisma_programi").delete().eq("ogrenci_id", ogrenci_id).execute()
    supabase.table("odev_takip").delete().eq("ogrenci_id", ogrenci_id).execute()
    supabase.table("haftalik_analiz").delete().eq("ogrenci_id", ogrenci_id).execute()
    supabase.table("ogrenci_kaynaklari").delete().eq("ogrenci_id", ogrenci_id).execute()
    # En son öğrenciyi siliyoruz
    supabase.table("ogrenciler").delete().eq("id", ogrenci_id).execute()

# --- 4. SAYFA AYARLARI ---

st.title("🎓 ÖĞRENCİ TAKİP SİSTEMİ")
st.markdown("---")
secenekler = list(SINAV_MÜFREDATI.keys())

# --- 5. SOL MENÜ ---
logo_yolu = "logo.jpg"
if os.path.exists(logo_yolu):
    c1, c2, c3 = st.sidebar.columns([1, 50, 1]) 
    with c2: st.image(Image.open(logo_yolu), use_container_width=True)

MOTIVASYON_SOZLERI = [
    ("Matematik, evrenin yazıldığı dildir.", "Galileo Galilei"),
    ("Başarı, küçük çabaların her gün tekrar edilmesidir.", "Robert Collier"),
    ("Matematikte zeka, sabırdan sonra gelir.", "Cahit Arf"),
    ("Hayatta en hakiki mürşit ilimdir.", "Mustafa Kemal Atatürk"),
("Bütün ümidim gençliktedir.", "Mustafa Kemal Atatürk"),
("Muallimler! Yeni nesil sizlerin eseri olacaktır.", "Mustafa Kemal Atatürk"),
("En büyük savaş, cahilliğe karşı yapılan savaştır.", "Mustafa Kemal Atatürk"),
("İstikbal göklerdedir.", "Mustafa Kemal Atatürk"),
("Milletleri kurtaranlar yalnız ve ancak öğretmenlerdir.", "Mustafa Kemal Atatürk"),
("Hayatta en hakiki mürşit ilimdir, fendir.", "Mustafa Kemal Atatürk"),
("Türk milletinin yürümekte olduğu terakki ve medeniyet yolunda elinde ve kafasında tuttuğu meşale, müspet ilimdir.", "Mustafa Kemal Atatürk"),

("Matematik, bilimlerin kraliçesi, aritmetik de matematiğin kraliçesidir.", "Carl Friedrich Gauss"),
("Matematiksel keşifler, ilkbaharda ormanda açan menekşeler gibidir; onların mevsimini hiçbir insan ne öne çekebilir ne de geciktirebilir.", "Carl Friedrich Gauss"),
("Matematiğin özü özgürlüğünde yatar.", "Georg Cantor"),
("Matematikte bir soru ortaya koyma sanatı, onu çözme sanatından daha yüksek bir değere sahip olmalıdır.", "Georg Cantor"),
("Bilmeliyiz. Bileceğiz.", "David Hilbert"),
("Matematikte ilerleme, fikirlerle sağlanır; uzun hesaplamalarla değil.", "David Hilbert"),
("Matematik yapma sanatı, genelliğin bütün tohumlarını içinde barındıran özel durumu bulmaktır.", "David Hilbert"),
("Matematiksel bilim benim görüşüme göre bölünmez bir bütündür.", "David Hilbert"),
("Bir matematikçi, bir ressam veya şair gibi, desenlerin yaratıcısıdır.", "G. H. Hardy"),
("Matematikle yalnızca yaratıcı bir sanat olarak ilgileniyorum.", "G. H. Hardy"),
("Büyük matematikte, kaçınılmazlık ve ekonomi ile birleşmiş çok yüksek derecede beklenmediklik vardır.", "G. H. Hardy"),
("Matematikçinin desenleri, ressamın veya şairin desenleri gibi güzel olmalıdır.", "G. H. Hardy"),
("Matematik, en çeşitli olayları karşılaştırır ve onları birleştiren gizli benzerlikleri ortaya çıkarır.", "Joseph Fourier"),
("Doğa yasaları matematiğin diliyle yazılmıştır; bu dilin sembolleri üçgenler, daireler ve diğer geometrik şekillerdir.", "Galileo Galilei"),
("Matematikte güzellik duygusu, sayıların ve şekillerin uyumu ve geometrik zarafet vardır.", "Henri Poincaré"),
("Matematik, farklı şeylere aynı adı verme sanatıdır.", "Henri Poincaré"),
("Matematikteki güzellik, matematikçilerin bildiği gerçek bir estetik duygudur.", "Henri Poincaré"),
("Matematik, yaratıcı bir sanattır.", "G. H. Hardy"),
("Bir matematiksel teori, onu sokakta karşılaştığınız ilk kişiye açıklayabilecek kadar açık hale getirilmedikçe tamamlanmış sayılmaz.", "David Hilbert"),
("Sonsuzluk! Başka hiçbir soru insan ruhunu bu kadar derinden harekete geçirmemiştir.", "David Hilbert"),
("Matematiksel bilimler ırk veya coğrafi sınır tanımaz; matematik için kültürel dünya tek bir ülkedir.", "David Hilbert"),

("Hayal gücü bilgiden daha önemlidir.", "Albert Einstein"),
("Her şey mümkün olduğunca basit yapılmalıdır, ama daha basit değil.", "Albert Einstein"),
("Bilgi sınırlıdır. Hayal gücü ise bütün dünyayı kuşatır.", "Albert Einstein"),

("Eğitim, dünyayı değiştirmek için kullanabileceğiniz en güçlü silahtır.", "Nelson Mandela"),
("Başarı, coşkunuzu kaybetmeden başarısızlıktan başarısızlığa yürümektir.", "Winston Churchill"),
("Dünyada hiçbir şey azim ve kararlılığın yerini tutamaz.", "Calvin Coolidge"),
("Başarılı olmak için yeteneğinizden çok kararlılığınız önemlidir.", "Anonim"),
("Başarı, küçük çabaların her gün tekrarlanmasının sonucudur.", "Anonim"),
("Ne kadar yavaş gittiğiniz önemli değil; yeter ki durmayın.", "Anonim"),
("Başlamak için mükemmel olmayı bekleme.", "Anonim"),
("Bugünkü emeğin, yarının özgüvenidir.", "Anonim"),
("Zor olduğu için vazgeçme; vazgeçtiğin için zor kalır.", "Anonim"),
("Başarısızlık son değildir; vazgeçmek sondur.", "Anonim"),
("Bugün yapmadığın çalışma, yarının stresidir.", "Anonim"),
("Her gün biraz daha iyi olmak, zamanla büyük bir fark yaratır.", "Anonim"),
("Küçük adımlar da seni hedefe götürür.", "Anonim"),
("Düştüğün yer, kalktığın yer olabilir.", "Anonim"),
("Henüz başaramamış olman, başaramayacağın anlamına gelmez.", "Anonim"),
("Çözemediğin soru, henüz çözmediğin sorudur.", "Anonim"),
("Her yanlış, doğruya giden yolda bir adımdır.", "Anonim"),
("Zor sorular, güçlü düşünmeyi öğretir.", "Anonim"),
("Matematikte başarı, en zeki olmak değil; vazgeçmeden düşünmeye devam etmektir.", "Anonim"),
("Bir soruyu çözemiyorsan, pes etmeden önce farklı bir yoldan dene.", "Anonim"),
("Her çözdüğün soru, bir sonraki soruyu biraz daha kolaylaştırır.", "Anonim"),
("Bugün çözemediğin soru, yarın çözdüğün soru olabilir.", "Anonim"),
("Çalışmanın karşılığı bazen hemen görünmez; ama hiçbir emek kaybolmaz.", "Anonim"),
("Hedefin büyükse, sabrın da büyük olmalı.", "Anonim"),
("Bir gün çok çalışmak yerine, her gün biraz çalış.", "Anonim"),
("Başarı, mükemmel olmaktan değil, devam etmekten geçer.", "Anonim"),
("Kendinle yarış; dün olduğundan daha iyi olman yeter.", "Anonim"),
("Bugün attığın küçük bir adım, yarın büyük bir fark yaratabilir.", "Anonim"),
("Disiplin, motivasyonun olmadığı günlerde seni hedefinde tutar.", "Anonim"),
("Hedeflerine ulaşmak için her gün yeniden başlamayı göze al.", "Anonim"),
("Zorlanıyorsan gelişiyorsun.", "Anonim"),
("Kendine zaman tanı; hiçbir başarı bir gecede oluşmaz.", "Anonim"),
("Başarı, bir gecede değil, her gün verilen emekle oluşur.", "Anonim"),
("Bugün çalışırsan yarın kendine teşekkür edersin.", "Anonim"),
("Bahane bulmak zamanı tüketir, çalışmak zamanı değerlendirir.", "Anonim"),
("Kendine verdiğin sözü tuttuğun her gün biraz daha güçlenirsin.", "Anonim"),
("Hedefine ulaşmanın yolu, her gün biraz daha yaklaşmaktır.", "Anonim"),
("Bir soru daha çöz. Bir konu daha öğren. Bir adım daha at.", "Anonim"),
("Kazanmak isteyen önce vazgeçmemeyi öğrenir.", "Anonim"),
("Senin sınırın, çoğu zaman düşündüğünden daha ileridedir.", "Anonim"),
("Başarı, kendini başkalarıyla değil, dünkü halinle kıyaslamaktır.", "Anonim"),
("Büyük hedefler, küçük ama sürekli adımlarla gerçekleşir.", "Anonim"),
("Bugünün çalışması, yarının başarısına dönüşür.", "Anonim"),
("Her çözdüğün problem, zihnini biraz daha güçlendirir.", "Anonim"),
("Soruyu çözemediğin an, öğrenmenin başladığı andır.", "Anonim"),
("Bir problemi çözmek için önce onu anlamak gerekir.", "Anonim"),
("Matematik ezberlemekten çok, düşünmeyi öğrenmektir.", "Anonim"),
("Yanlış yaptığın soru, sana doğru yaptığın sorudan daha fazlasını öğretebilir.", "Anonim"),
("Matematikte hızdan önce düşünmeyi öğren.", "Anonim"),
("Bugün zor olan, yarın senin gücün olacak.", "Anonim"),
("Mücadele ettiğin şey, sonunda seni güçlendirir.", "Anonim"),
("Yol uzun olabilir; önemli olan yürümeye devam etmektir.", "Anonim"),
("Hedefine ulaşmak için her gün biraz daha iyi ol.", "Anonim"),
("Çalışmak, gelecekteki kendine yapacağın en büyük iyiliklerden biridir.", "Anonim"),
("Kendine inanmadığın günlerde bile çalışmaya devam et.", "Anonim"),
("Başarı, yetenekten önce süreklilik ister.", "Anonim"),
("Bir gün değil, her gün çalış.", "Anonim"),
("Hedefine ulaşmak istiyorsan, hedefin için bugün bir şey yap.", "Anonim"),
("Hiçbir soru, üzerinde yeterince düşündüğün zaman sonsuza kadar zor kalmaz.", "Anonim"),
("Her deneme seni sonuca biraz daha yaklaştırır.", "Anonim"),
("Bugünkü küçük fedakârlıklar, yarının büyük sonuçlarını oluşturur.", "Anonim"),
("Kendini geliştirmek için her gün bir fırsattır.", "Anonim"),
("Başarının en önemli adımı, başlamaya karar vermektir.", "Anonim"),
("Pes etmek için bir sebep arama; devam etmek için bir sebep bul.", "Anonim"),
("Hedefin seni korkutuyorsa, doğru büyüklüktedir.", "Anonim"),
("Bugün verdiğin emek, yarın karşına sonuç olarak çıkar.", "Anonim"),
("Bir yanlış cevap, doğru cevaba giden yolda değerli bir adımdır.", "Anonim"),
("Her gün attığın adımlar küçük olabilir; önemli olan geriye gitmemendir.", "Anonim"),
("Başarı, vazgeçmeyenlerin hikâyesidir.", "Anonim"),
("Zorlandığın yerde pes etmek yerine biraz daha düşün.", "Anonim"),
("Kendine yatırım yaptığın hiçbir gün boşa gitmez.", "Anonim"),
("Bugün çalışmak istememen, bugün çalışmaman gerektiği anlamına gelmez.", "Anonim"),
("Motivasyon başlatır, disiplin devam ettirir.", "Anonim"),
("Hedefine ulaşmak için önce bugününü kazan.", "Anonim"),
("Her gün bir önceki günden biraz daha iyi ol.", "Anonim"),
("Çözdüğün her soru, hedefindeki sana biraz daha yaklaştırır.", "Anonim"),
("Başarı, tekrar tekrar denemeye cesaret etmektir.", "Anonim"),
("Zor soruların karşısında kalmak, zihnini güçlendirir.", "Anonim"),
("Bugün yapabileceğin şeyi yarına bırakma.", "Anonim"),
("Küçük ilerlemeleri küçümseme; büyük başarılar onlardan oluşur.", "Anonim"),
("Hedefine giden yolda hızından çok sürekliliğin önemlidir.", "Anonim"),
("Çalıştığın her konu, gelecekteki yükünü biraz daha azaltır.", "Anonim"),
("Bugün vazgeçmezsen, yarın daha güçlü başlayacaksın.", "Anonim"),
("Kendine güvenmek, çalışmanın yerini tutmaz; ama çalışmaya başlamanı sağlar.", "Anonim"),
("Başarılı olmak istiyorsan, zorlandığın yerde kalmayı öğren.", "Anonim"),
("Her soru bir engel değil, bir antrenmandır.", "Anonim"),
("Sınav günü geldiğinde keşke dememek için bugün elinden geleni yap.", "Anonim"),
("Bugünkü çalışma, sınav günündeki rahatlığındır.", "Anonim"),
("Hedefin için yaptığın hiçbir çalışma küçük değildir.", "Anonim"),
("Kendine verdiğin sözleri tutmak, başarıya giden yolun başlangıcıdır.", "Anonim"),
("Biraz daha sabret. Biraz daha çalış. Biraz daha dene.", "Anonim")
]
secilen_soz = random.choice(MOTIVASYON_SOZLERI)

st.sidebar.markdown(f"""
<div style="background-color: #f8f9fa; border-left: 4px solid #d35400; padding: 12px; border-radius: 4px; margin-bottom: 25px;">
    <p style="color: #2c3e50; font-size: 13px; font-style: italic; margin: 0;">"{secilen_soz[0]}"</p>
    <p style="color: #7f8c8d; font-size: 11px; margin-top: 6px; font-weight: bold; text-align: right;">- {secilen_soz[1]}</p>
</div>
""", unsafe_allow_html=True)

if st.session_state['rol'] == "ADMIN":
    st.sidebar.header("➕ Yeni Öğrenci Ekle")
    with st.sidebar.form("ogrenci_ekle_form", clear_on_submit=True):
        ogrenci_no = st.text_input("Öğrenci Numarası (Özel ID)")
        ad_soyad = st.text_input("Öğrenci Adı Soyadı")
        secilen_turler = st.multiselect("Öğrenciye Yüklenecek Müfredatlar", secenekler, default=["TYT"])
        telefon = st.text_input("Öğrenci Telefonu")
        veli_ad = st.text_input("Veli Adı Soyadı")
        veli_telefon = st.text_input("Veli Telefonu")
        hedef_net = st.number_input("Hedeflenen Toplam Net", min_value=0, max_value=120, value=80)
        
        if st.form_submit_button("Öğrenciyi Kaydet"):
            if ad_soyad:
                ogrenci_ekle(ogrenci_no if ogrenci_no else "-", ad_soyad, ", ".join(secilen_turler), telefon, veli_ad, veli_telefon, hedef_net)
                st.sidebar.success(f"{ad_soyad} eklendi!")
                st.rerun()
            else:
                st.sidebar.error("Lütfen öğrenci adını giriniz!")

# ==============================================================================
# ANA SAYFA ÜST KISIM: EŞİT BOYUTLU TARİH VE CANLI AKAN SAAT KUTULARI
# ==============================================================================
from datetime import date
import streamlit.components.v1 as components

bugun = date.today()
yks_tarihi = date(2027, 6, 19)
lgs_tarihi = date(2027, 6, 6)

kalan_yks = max(0, (yks_tarihi - bugun).days)
kalan_lgs = max(0, (lgs_tarihi - bugun).days)

# 1. Üst Kurumsal Karşılama Bannerı
st.markdown("""
<div class="ots-header">
    <h1>🎓 EMİR HOCA — ÖĞRENCİ TAKİP & KOÇLUK PANELİ</h1>
    <p>Öğrenci gelişimini, haftalık çalışma programlarını, ödevleri ve sınav netlerini tek ekrandan yönetin.</p>
</div>
""", unsafe_allow_html=True)

# 2. Sayaç Sütunları
col_sayac1, col_sayac2, col_sayac3, col_sayac4 = st.columns(4)

with col_sayac1:
    st.markdown(f"""
    <div class="sayac-kutu">
        <div class="sayac-baslik">⏳ YKS'YE</div>
        <div class="sayac-sayi">{kalan_yks}</div>
        <div class="sayac-alt">GÜN KALDI</div>
    </div>
    """, unsafe_allow_html=True)

with col_sayac2:
    st.markdown(f"""
    <div class="sayac-kutu">
        <div class="sayac-baslik">🎯 LGS'YE</div>
        <div class="sayac-sayi">{kalan_lgs}</div>
        <div class="sayac-alt">GÜN KALDI</div>
    </div>
    """, unsafe_allow_html=True)

# 3. Kutu: Bugünün Tarihi
with col_sayac3:
    st.markdown(f"""
    <div class="sayac-kutu">
        <div class="sayac-baslik">📅 BUGÜNÜN TARİHİ</div>
        <div class="sayac-sayi" style="font-size: 20px; padding: 6px 0; color: #1e293b;">{bugun.strftime('%d.%m.%Y')}</div>
        <div class="sayac-alt">ÇALIŞMA GÜNÜ</div>
    </div>
    """, unsafe_allow_html=True)

# 4. Kutu: Canlı Akan Saat ve Saniye (Diğerleriyle Birebir Aynı Boyutta)
with col_sayac4:
    components.html("""
    <style>
        body {
            margin: 0;
            background-color: transparent;
        }
        .sayac-kutu {
            background: #ffffff;
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            border: 1px solid #e2e8f0;
            border-top: 4px solid #c5a059;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            font-family: sans-serif;
            box-sizing: border-box;
        }
        .sayac-baslik {
            font-size: 13px;
            font-weight: 700;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .sayac-sayi {
            font-size: 22px;
            font-weight: 800;
            color: #1e293b;
            margin: 6px 0;
        }
        .sayac-alt {
            font-size: 12px;
            color: #94a3b8;
        }
    </style>
    <div class="sayac-kutu">
        <div class="sayac-baslik">🕒 ANLIK SAAT</div>
        <div id="canli-saat" class="sayac-sayi">00:00:00</div>
        <div class="sayac-alt">AKTARIM AKTİF</div>
    </div>

    <script>
        function saatGuncelle() {
            const simdi = new Date();
            const saat = String(simdi.getHours()).padStart(2, '0');
            const dakika = String(simdi.getMinutes()).padStart(2, '0');
            const saniye = String(simdi.getSeconds()).padStart(2, '0');
            document.getElementById('canli-saat').innerHTML = saat + ":" + dakika + ":" + saniye;
        }
        setInterval(saatGuncelle, 1000);
        saatGuncelle();
    </script>
    """, height=128)

st.markdown("<br>", unsafe_allow_html=True)
# --- 6. ANA EKRAN VE PROFİL PANELİ ---
# 1. BULUTTAN ÖĞRENCİ LİSTESİNİ ÇEK (Çoklu Öğretmen Filtresiyle)
if st.session_state['rol'] == "ADMIN":
    res = supabase.table("ogrenciler").select("*").eq("ogretmen_id", st.session_state['aktif_ogretmen_id']).execute()
else:
    res = supabase.table("ogrenciler").select("*").eq("id", st.session_state['kilitli_ogrenci_id']).execute()

df = pd.DataFrame(res.data) if res.data else pd.DataFrame()

if not df.empty:
    st.subheader("⚙️ Öğrenci Koçluk Paneli")
    
    # 1. ÖĞRENCİ SEÇİMİ KİLİDİ
    if st.session_state['rol'] == "ADMIN":
        # Admin tüm öğrencileri listeden seçebilir
        secili_id = st.selectbox(
            "İşlem Yapılacak Öğrenciyi Seçin:", 
            df['id'].tolist(), 
            format_func=lambda x: f"{df[df['id'] == x].iloc[0]['ad_soyad']}"
        )
    else:
        # Öğrenci listeyi göremez, sistem otomatik kendi ID'sini tanımlar
        secili_id = st.session_state['kilitli_ogrenci_id']
        secili_isim = df[df['id'] == secili_id].iloc[0]['ad_soyad']
        st.info(f"👤 Aktif Profil: {secili_isim} (Sadece Okuma Modu)")
        
    secili_ogrenci = df[df['id'] == secili_id].iloc[0]
    
    # KODUN KALBİ: Mevcut öğrencilerin eski verilerini silmeden, yeni eklenen dersleri otomatik atar.
    konulari_ata(secili_id, secili_ogrenci['sinav_turu'])
    
    # 2. SEKMELERİN KİLİTLENMESİ
    if st.session_state['rol'] == "ADMIN":
        sekme_listesi = [
            "📸 Profil", "📚 Kaynak Yönetimi" ,"📅 Çalışma Programı", "📚 Ödev Takibi", "📊 Deneme Puanı", 
            "📑 Ders Konuları", "📝 Haftalık Analiz", "👨‍👩‍👦 Veli Bilgilendirme", 
            "✏️ Güncelle", "🗑️ Sil"
        ]
    else:
        # Öğrenci girdiğinde son 2 sekme (Güncelle ve Sil) kilitli görünür
        sekme_listesi = [
            "📸 Profil", "📚 Kaynak Yönetimi" ,"📅 Çalışma Programı", "📚 Ödev Takibi", "📊 Deneme Puanı", 
            "📑 Ders Konuları", "📝 Haftalık Analiz", "👨‍👩‍👦 Veli Bilgilendirme", 
            "✏️ Güncelle", "🗑️ Sil"
        ]

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs(sekme_listesi)
    
    # --- 1. PROFİL ---
    with tab1:
        col_foto, col_bilgi = st.columns([1, 2])
        with col_foto:
            foto_yolu = f"ogrenci_fotolar/{secili_id}.jpg"
            if os.path.exists(foto_yolu): st.image(Image.open(foto_yolu), use_container_width=True)
            yuklenen_foto = st.file_uploader("Fotoğraf Yükle", type=['jpg', 'png', 'jpeg'], key=f"foto_{secili_id}")
            if yuklenen_foto:
                with open(foto_yolu, "wb") as f: f.write(yuklenen_foto.getbuffer())
                st.rerun()
        with col_bilgi:
            st.write(f"### {secili_ogrenci['ad_soyad']}")
            st.write(f"📚 **Sınav Grubu:** {secili_ogrenci['sinav_turu']} | 🆔 **No:** {secili_ogrenci['ogrenci_no']}")
            st.write(f"📞 **Öğrenci Tel:** {secili_ogrenci['telefon']}")
            st.write(f"👨‍👩‍👦 **Veli:** {secili_ogrenci['veli_ad']} ({secili_ogrenci['veli_telefon']})")
            
            # Sözlükte key yoksa veya null ise varsayılan 80 göster
            hedef_degeri = secili_ogrenci.get('hedef_net', 80)
            if pd.isna(hedef_degeri) or hedef_degeri is None: hedef_degeri = 80
            st.write(f"🎯 **Hedef Toplam Net:** {int(hedef_degeri)}")



    # --- 2. KAYNAK YÖNETİMİ ---
    with tab2:
        st.markdown("### 📚 Öğrencinin Kaynakları ve İlerleme Durumu")
        
        # --- FOTOĞRAFLAR İÇİN KLASÖR OLUŞTURMA ---
        if not os.path.exists('kaynak_fotolari'):
            os.makedirs('kaynak_fotolari')
            
        # (NOT: ALTER TABLE kısımları kaldırıldı. Supabase paneline manuel eklendiği için gerek yok.)
        
        # --- 1. YENİ KAYNAK EKLEME (SADECE ADMİN GÖRÜR) ---
        if st.session_state['rol'] == "ADMIN":
            with st.expander("➕ Yeni Kaynak / Soru Bankası Ekle", expanded=False):
                with st.form("kaynak_ekle_form", clear_on_submit=True):
                    col_k1, col_k2 = st.columns(2)
                    with col_k1:
                        k_ders = st.selectbox("Ders:", ["Matematik", "Geometri", "Fizik", "Kimya", "Biyoloji", "Türkçe", "Tarih", "Coğrafya", "Felsefe", "İngilizce"])
                        k_adi = st.text_input("Kaynak / Kitap Adı:", placeholder="Örn: 3D TYT Matematik Soru Bankası")
                        k_toplam = st.number_input("Kitabın Toplam Sayfa Sayısı:", min_value=1, value=300)
                    with col_k2:
                        k_yayin = st.text_input("Yayın Evi:", placeholder="Örn: 3D Yayınları")
                        k_foto = st.file_uploader("Kaynak Fotoğrafı Seçiniz (İsteğe Bağlı):", type=['png', 'jpg', 'jpeg'])
                    
                    if st.form_submit_button("Kaynağı Kaydet"):
                        if k_adi:
                            # Fotoğraf İşlemi
                            foto_ismi = ""
                            if k_foto is not None:
                                dosya_uzantisi = k_foto.name.split('.')[-1]
                                temiz_ad = "".join([c for c in k_adi if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ", "_")
                                foto_ismi = f"{temiz_ad}_{secili_id}.{dosya_uzantisi}"
                                kayit_yolu = os.path.join("kaynak_fotolari", foto_ismi)
                                with open(kayit_yolu, "wb") as f:
                                    f.write(k_foto.getbuffer())
                                    
                            # Supabase'e Kaydet
                            yeni_kaynak_data = {
                                "ogrenci_id": int(secili_id), "ders": k_ders, "kaynak_adi": k_adi,
                                "yayin_evi": k_yayin, "durum": "Aktif", "toplam_sayfa": int(k_toplam),
                                "mevcut_sayfa": 0, "foto_yolu": foto_ismi
                            }
                            supabase.table("ogrenci_kaynaklari").insert(yeni_kaynak_data).execute()
                            
                            st.success(f"'{k_adi}' başarıyla eklendi!")
                            st.rerun()
                        else:
                            st.error("Lütfen kaynak adını boş bırakmayın.")

        # --- KAYNAKLARI LİSTELEME ---
        res_kaynak = supabase.table("ogrenci_kaynaklari").select("*").eq("ogrenci_id", secili_id).order("id", desc=True).execute()
        df_kaynak = pd.DataFrame(res_kaynak.data) if res_kaynak.data else pd.DataFrame()

        if not df_kaynak.empty:
            for idx, row in df_kaynak.iterrows():
                
                t_sayfa = row.get('toplam_sayfa', 1) or 1 
                m_sayfa = row.get('mevcut_sayfa', 0) or 0
                yuzde = min((m_sayfa / t_sayfa) * 100, 100.0) 
                    
                # Kart tasarımı için border=True kullanıyoruz ve dikeyde ortalıyoruz
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([1.2, 3, 3, 2.5], vertical_alignment="center")
                    
                    with c1:
                        # Sarı hata veren use_column_width düzeltildi -> use_container_width
                        if row.get('foto_yolu') and os.path.exists(os.path.join("kaynak_fotolari", row['foto_yolu'])):
                            st.image(os.path.join("kaynak_fotolari", row['foto_yolu']), use_container_width=True)
                        else:
                            st.markdown("<div style='text-align: center; font-size: 40px; padding: 10px; border: 1px dashed #e2e8f0; border-radius: 8px; color: #cbd5e1;'>📘</div>", unsafe_allow_html=True)
                            
                    with c2:
                        st.markdown(f"<h4 style='margin-bottom: 0px; color: #1e293b;'>{row['kaynak_adi']}</h4>", unsafe_allow_html=True)
                        st.caption(f"**{row['ders']}** | {row['yayin_evi']}")
                             
                    with c3:
                        # %100 olduysa bar yerine kutlama mesajı gösterir
                        if yuzde == 100:
                            st.success("🎉 **KAYNAK BİTTİ**")
                        else:
                            st.markdown(f"**İlerleme:** %{int(yuzde)}")
                            st.progress(int(yuzde))
                            st.caption(f"{m_sayfa} / {t_sayfa} Sayfa Çözüldü")

                    with c4:
                        if st.session_state['rol'] == "ADMIN":
                            # Sayfa sayısını artırma alanı
                            yeni_sayfa = st.number_input("Sayfa Güncelle:", min_value=0, max_value=int(t_sayfa), value=int(m_sayfa), key=f"sayfa_{row['id']}")
                            if st.button("Kaydet", key=f"btn_k_{row['id']}", use_container_width=True, type="primary"):
                                supabase.table("ogrenci_kaynaklari").update({"mevcut_sayfa": int(yeni_sayfa)}).eq("id", row['id']).execute()
                                st.rerun()
        else:
            if st.session_state['rol'] == "ADMIN":
                st.info("Öğrenciye tanımlanmış kaynak bulunmuyor. Yukarıdaki butondan ekleyebilirsiniz.")
            else:
                st.info("Henüz eklenmiş bir kaynak bulunmuyor.")

    with tab3:
        st.markdown("### 📅 Haftalık Çalışma Programı")

        # --- 1. YENİ PROGRAM HAZIRLAMA (SADECE ADMİN GÖRÜR) ---
        if st.session_state['rol'] == "ADMIN":
            with st.expander("➕ Yeni Program Hazırla / Düzenle", expanded=True):
                st.info("💡 **İpucu:** Görevleri alt alta yazın (Örn: Mat 50 Soru). Sistem bunları otomatik olarak tıklanabilir kutucuklara dönüştürecektir.")
                secili_hafta = st.text_input("Tarih Aralığı Girin:", value="06.07.2026 - 13.07.2026", key="h_input")
                eski_p = program_getir(secili_id, secili_hafta)
                
                with st.form("program_form"):
                    c_g1, c_g2 = st.columns(2)
                    with c_g1:
                        pazartesi = st.text_area("Pazartesi", value=eski_p[0] if eski_p else "")
                        carsamba = st.text_area("Çarşamba", value=eski_p[2] if eski_p else "")
                        cuma = st.text_area("Cuma", value=eski_p[4] if eski_p else "")
                        pazar = st.text_area("Pazar", value=eski_p[6] if eski_p else "")
                    with c_g2:
                        sali = st.text_area("Salı", value=eski_p[1] if eski_p else "")
                        persembe = st.text_area("Perşembe", value=eski_p[3] if eski_p else "")
                        cumartesi = st.text_area("Cumartesi", value=eski_p[5] if eski_p else "")
                        haftalik_not = st.text_area("Koçluk Notu", value=eski_p[7] if eski_p else "")

                    if st.form_submit_button("Programı Kaydet"):
                        program_kaydet(secili_id, secili_hafta, pazartesi, sali, carsamba, persembe, cuma, cumartesi, pazar, haftalik_not)
                        st.success("Program başarıyla kaydedildi!")
                        st.rerun()

        # --- 2. SİSTEME KAYITLI PROGRAMLAR (HERKES GÖRÜR) ---
        st.markdown("---")
        st.markdown("### 🗂️ Güncel ve Geçmiş Haftalar")
        
        res_haftalar = supabase.table("calisma_programi").select("*").eq("ogrenci_id", secili_id).order("id", desc=True).execute()
        df_haftalar = pd.DataFrame(res_haftalar.data) if res_haftalar.data else pd.DataFrame()

        if not df_haftalar.empty:
            for idx, row in df_haftalar.iterrows():
                with st.expander(f"📂 {row['hafta_adi']} Programını İncele"):
                    
                    # --- TİKLENEBİLİR GÖREV LİSTESİ (ETKİLEŞİMLİ ALAN) ---
                    gunler_db = [
                        ("Pazartesi", row.get('pazartesi', ''), "pazartesi", "📌"), ("Salı", row.get('sali', ''), "sali", "📌"), 
                        ("Çarşamba", row.get('carsamba', ''), "carsamba", "📌"), ("Perşembe", row.get('persembe', ''), "persembe", "📌"), 
                        ("Cuma", row.get('cuma', ''), "cuma", "📌"), ("Cumartesi", row.get('cumartesi', ''), "cumartesi", "🔥"), 
                        ("Pazar", row.get('pazar', ''), "pazar", "🍀")
                    ]
                    
                    guncel_veriler = {}
                    
                    with st.form(key=f"gorev_form_{row['id']}"):
                        st.markdown("#### 🎯 Günlük Görevler")
                        cols = st.columns(3)
                        col_idx = 0
                        
                        for g_isim, g_icerik, g_key, g_ikon in gunler_db:
                            if g_icerik:
                                with cols[col_idx % 3]:
                                    st.markdown(f"**{g_ikon} {g_isim}**")
                                    satirlar = str(g_icerik).split('\n')
                                    yeni_satirlar = []
                                    
                                    for i, satir in enumerate(satirlar):
                                        if satir.strip() == "": continue
                                        
                                        is_checked = False
                                        gorev_metni = satir
                                        if satir.startswith("[X] "):
                                            is_checked = True
                                            gorev_metni = satir[4:]
                                        elif satir.startswith("[ ] "):
                                            is_checked = False
                                            gorev_metni = satir[4:]
                                            
                                        check = st.checkbox(gorev_metni, value=is_checked, key=f"chk_{row['id']}_{g_key}_{i}")
                                        yeni_satirlar.append(f"[X] {gorev_metni}" if check else f"[ ] {gorev_metni}")
                                    
                                    guncel_veriler[g_key] = "\n".join(yeni_satirlar)
                                col_idx += 1
                            else:
                                guncel_veriler[g_key] = ""
                        
                        if row.get('haftalik_not'):
                            st.info(f"💡 **Emir Hocanın Notu:** {row['haftalik_not']}")
                        
                        if st.form_submit_button("✅ İlerlemeyi Kaydet (Tikleri Güncelle)"):
                            guncel_prog_data = {
                                "pazartesi": guncel_veriler['pazartesi'], "sali": guncel_veriler['sali'], 
                                "carsamba": guncel_veriler['carsamba'], "persembe": guncel_veriler['persembe'], 
                                "cuma": guncel_veriler['cuma'], "cumartesi": guncel_veriler['cumartesi'], "pazar": guncel_veriler['pazar']
                            }
                            supabase.table("calisma_programi").update(guncel_prog_data).eq("id", row['id']).execute()
                            st.success("Görev ilerlemeleri kaydedildi!")
                            st.rerun()

                    st.divider()

                    # --- PDF VE WHATSAPP İÇİN YENİ NESİL ALTIN SARISI TASARIM ---
                    def wp_formatla(metin):
                        return str(metin).replace("[X] ", "✅ ").replace("[ ] ", "⬜ ") if metin else ""
                    
                    # HTML İçin CSS ile kusursuz çizilmiş kutucuklar
                    def html_formatla(metin):
                        if not metin: return '<div style="color:#a8a29e; font-style:italic; font-family:\'Kalam\', cursive; font-size:14px; margin-top:5px;">Serbest Gün...</div>'
                        satirlar = str(metin).split('\n')
                        html_liste = '<ul class="task-list">'
                        for satir in satirlar:
                            if satir.strip() == "": continue
                            if satir.startswith("[X] "):
                                html_liste += f'<li class="task done"><span class="check-box checked">✔</span><span class="task-text">{satir[4:]}</span></li>'
                            elif satir.startswith("[ ] "):
                                html_liste += f'<li class="task"><span class="check-box empty"></span><span class="task-text">{satir[4:]}</span></li>'
                            else:
                                html_liste += f'<li class="task"><span class="check-box bullet">•</span><span class="task-text">{satir}</span></li>'
                        html_liste += '</ul>'
                        return html_liste

                    wp_text = f"📒 *HAFTALIK ÇALIŞMA PROGRAMI* 📒\n👤 *Öğrenci:* {secili_ogrenci['ad_soyad']}\n📅 *Tarih:* _{row['hafta_adi']}_\n➖➖➖➖➖➖\n"
                    for g_isim, g_icerik, g_key, g_ikon in gunler_db:
                        if g_icerik: wp_text += f"{g_ikon} *{g_isim[:3].upper()}:*\n{wp_formatla(g_icerik)}\n\n"
                    if row.get('haftalik_not'): wp_text += f"💡 *NOT:* _{row['haftalik_not']}_"
                    
                    tel_clean = str(secili_ogrenci['telefon']).replace(" ", "")
                    if tel_clean.startswith("0"): tel_clean = "90" + tel_clean[1:]
                    wp_url = f"https://wa.me/{tel_clean}?text={urllib.parse.quote(wp_text)}"
                    
                    # --- KESİN TEK SAYFA MİLİMETRİK HTML TASARIMI ---
                    html_icerik = f"""
                    <!DOCTYPE html>
                    <html lang="tr">
                    <head>
                        <meta charset="UTF-8">
                        <title>{secili_ogrenci['ad_soyad']} - {row['hafta_adi']}</title>
                        <link href="https://fonts.googleapis.com/css2?family=Kalam:wght@400;700&family=Nunito:wght@600;800;900&display=swap" rel="stylesheet">
                        <style>
                            /* EKRAN (TARAYICI) GÖRÜNÜMÜ */
                            * {{ box-sizing: border-box; }}
                            body {{ background-color: #fcfbf8; font-family: 'Nunito', sans-serif; margin: 0; padding: 20px; color: #333; }}
                            .container {{ width: 100%; max-width: 1200px; margin: auto; background-color: #fff; padding: 20px; border-radius: 12px; border: 2px solid #d4af37; box-shadow: 0 5px 15px rgba(212, 175, 55, 0.1); display: flex; flex-direction: column; }}
                            
                            .header {{ text-align: center; border-bottom: 2px solid #d4af37; padding-bottom: 10px; margin-bottom: 15px; }}
                            .header h1 {{ margin: 0; color: #b8860b; font-size: 24px; font-weight: 900; letter-spacing: 1px; }}
                            .header p {{ margin: 3px 0 0 0; font-size: 14px; font-weight: 800; color: #78716c; }}
                            
                            .grid-container {{ display: grid; grid-template-columns: repeat(4, 1fr); grid-template-rows: repeat(2, 1fr); gap: 10px; }}
                            .gun-kutu {{ border: 1.5px dashed #c5a059; border-radius: 8px; padding: 8px; background-color: #fefcf8; overflow: hidden; }}
                            .gun-baslik {{ font-size: 15px; font-weight: 900; color: #b8860b; margin-bottom: 6px; border-bottom: 1px solid #f3e8d3; padding-bottom: 4px; }}
                            
                            .task-list {{ list-style: none; padding: 0; margin: 0; }}
                            .task {{ display: flex; align-items: flex-start; margin-bottom: 4px; font-family: 'Kalam', cursive; font-size: 14px; color: #444; line-height: 1.2; }}
                            .task.done {{ text-decoration: line-through; color: #a8a29e; }}
                            
                            .check-box {{ display: inline-block; width: 12px; height: 12px; border: 1.5px solid #d4af37; border-radius: 3px; text-align: center; line-height: 12px; font-size: 10px; margin-right: 6px; margin-top: 2px; flex-shrink: 0; font-family: sans-serif; }}
                            .check-box.checked {{ background-color: #d4af37; color: #fff; font-weight: bold; border-color: #d4af37; }}
                            .check-box.empty {{ background-color: #fff; }}
                            .check-box.bullet {{ border: none; background: transparent; color: #d4af37; font-size: 18px; line-height: 12px; margin-top: 0; }}
                            .task-text {{ flex: 1; }}
                            
                            .not-kutu {{ border: 2px solid #b8860b; border-radius: 8px; padding: 8px; background-color: #fff9e6; overflow: hidden; }}
                            .not-metin {{ font-family: 'Kalam', cursive; font-size: 15px; color: #996515; white-space: pre-wrap; }}

                            /* 🔴 KESİN TEK SAYFA PDF (PRINT) ZORLAMASI 🔴 */
                            @page {{ size: A4 landscape; margin: 0 !important; }}
                            @media print {{ 
                                html, body {{ 
                                    width: 297mm !important; 
                                    height: 209mm !important; /* A4'ün fiziksel sınırları (taşmaları önlemek için 1mm kısaltıldı) */
                                    margin: 0 !important; 
                                    padding: 0 !important; 
                                    overflow: hidden !important; 
                                    -webkit-print-color-adjust: exact !important; 
                                    print-color-adjust: exact !important; 
                                    background-color: #fff !important;
                                }}
                                .container {{ 
                                    width: 100% !important; 
                                    height: 100% !important; 
                                    border: none !important; 
                                    box-shadow: none !important; 
                                    padding: 8mm 10mm !important; /* Kağıdın içerisinden verilen güvenli kenar boşlukları */
                                    margin: 0 !important; 
                                }}
                                .grid-container {{ 
                                    height: calc(100% - 60px) !important; /* Başlık alanını hesaptan düşüp tam ekrana yayıyoruz */
                                }}
                                .gun-kutu, .not-kutu {{
                                    height: 100% !important; 
                                }}
                            }}
                        </style>
                    </head>
                    <body onload="setTimeout(function() {{ window.print(); }}, 800);">
                        <div class="container">
                            <div class="header">
                                <h1>🎓 HAFTALIK ÇALIŞMA PROGRAMI</h1>
                                <p>👤 {secili_ogrenci['ad_soyad']} | 📅 {row['hafta_adi']}</p>
                            </div>
                            <div class="grid-container">
                    """
                    
                    # 7 Gün ve 1 Not Kutusu = Tam 8 Kutu (4x2 Grid'e kusursuz oturur)
                    gunler_html = [
                        ("Pazartesi", html_formatla(row.get('pazartesi', ''))), ("Salı", html_formatla(row.get('sali', ''))), 
                        ("Çarşamba", html_formatla(row.get('carsamba', ''))), ("Perşembe", html_formatla(row.get('persembe', ''))), 
                        ("Cuma", html_formatla(row.get('cuma', ''))), ("Cumartesi", html_formatla(row.get('cumartesi', ''))), 
                        ("Pazar", html_formatla(row.get('pazar', '')))
                    ]
                    
                    for g_isim, g_icerik in gunler_html:
                        html_icerik += f'<div class="gun-kutu"><div class="gun-baslik">{g_isim}</div>{g_icerik}</div>'
                            
                    not_icerik = row.get("haftalik_not") if row.get("haftalik_not") else "Öğrencimize iyi çalışmalar dilerim..."
                    html_icerik += f'<div class="not-kutu"><div class="gun-baslik">💡 Emir Hocanın Notu</div><div class="not-metin">{not_icerik}</div></div>'
                        
                    html_icerik += '</div></div></body></html>'
                    
                    # --- 3. BUTONLARIN GÖSTERİMİ (ADMİN VE ÖĞRENCİ AYRIMI) ---
                    if st.session_state['rol'] == "ADMIN":
                        col_btn1, col_btn2 = st.columns(2)
                        col_btn1.link_button("📲 WhatsApp'tan Gönder", wp_url, use_container_width=True)
                        col_btn2.download_button("📄 PDF Olarak Yazdır (Tek Sayfa)", data=html_icerik, file_name=f"{row['hafta_adi']}_program.html", mime="text/html", use_container_width=True)
                    else:
                        st.download_button("📄 Programı PDF Olarak İndir", data=html_icerik, file_name=f"{row['hafta_adi']}_program.html", mime="text/html", use_container_width=True)
        else:
            st.info("Kayıtlı geçmiş hafta bulunmuyor.")

# --- 3. ÖDEV TAKİBİ ---
    with tab4: 
        col_odev1, col_odev2 = st.columns([1, 2])
        
        with col_odev1:
            # --- 1. YENİ ÖDEV VERME FORMU (SADECE ADMİN) ---
            if st.session_state['rol'] == "ADMIN":
                st.markdown("#### ➕ Yeni Ödev Ver")
                
                # Supabase verileri çek
                res_ok = supabase.table("ogrenci_kaynaklari").select("ders, kaynak_adi, yayin_evi").eq("ogrenci_id", secili_id).execute()
                df_ogrenci_kaynaklar = pd.DataFrame(res_ok.data) if res_ok.data else pd.DataFrame()
                
                res_k = supabase.table("konu_takip").select("ders").eq("ogrenci_id", secili_id).execute()
                df_k = pd.DataFrame(res_k.data) if res_k.data else pd.DataFrame()

                dersler_listesi = list(df_k['ders'].unique()) if not df_k.empty else ["Matematik", "Türkçe", "Fizik", "Kimya", "Biyoloji"]
                odev_giris_turu = st.radio("Ödev Giriş Mantığı:", ["📚 Kayıtlı Kaynaktan Seç", "✍️ Manuel Giriş Yap"], horizontal=True)

                with st.form("odev_ver_form"):
                    if odev_giris_turu == "📚 Kayıtlı Kaynaktan Seç":
                        if not df_ogrenci_kaynaklar.empty:
                            kaynak_secenekleri = [f"{row['ders']} - {row['kaynak_adi']} ({row['yayin_evi']})" for idx, row in df_ogrenci_kaynaklar.iterrows()]
                            secilen_kaynak_str = st.selectbox("Kayıtlı Kitap Seçin:", kaynak_secenekleri)
                            ek_konu_sayfa = st.text_input("Konu / Test / Sayfa Aralığı:", placeholder="Örn: Test 3-6 / Sayfa 45-50")
                            
                            o_ders = secilen_kaynak_str.split(" - ")[0]
                            kaynak_adi_temiz = secilen_kaynak_str.split(" (")[0].split(" - ")[1]
                            o_kaynak = f"[{kaynak_adi_temiz}] {ek_konu_sayfa}" if ek_konu_sayfa else kaynak_adi_temiz
                        else:
                            st.info("Bu öğrenci için kayıtlı kaynak bulunamadı. Aşağıdan manuel girebilir veya 'Kaynak Yönetimi' sekmesinden kitap ekleyebilirsiniz.")
                            o_ders = st.selectbox("Ders Seçimi", dersler_listesi)
                            o_kaynak = st.text_input("Kaynak ve Konu", placeholder="Örn: Soru Bankası - Paragraf")
                    else:
                        o_ders = st.selectbox("Ders Seçimi", dersler_listesi)
                        o_kaynak = st.text_input("Kaynak ve Konu", placeholder="Örn: Yaprak Test / 2023 Çıkmış Sorular")

                    o_soru = st.number_input("Hedef Soru Sayısı", min_value=1, step=10, value=50)

                    if st.form_submit_button("Ödevi Ata", type="primary"):
                        if o_kaynak:
                            odev_ekle(secili_id, o_ders, o_kaynak, o_soru)
                            st.success("Ödev başarıyla atandı!")
                            st.rerun()
                        else:
                            st.error("Lütfen kaynak ve konu bilgisini doldurun.")
            else:
                # Öğrenciye sol tarafta form yerine şık bir bilgi notu gösterelim
                st.info("📚 **Ödev Takibi:** Bu alandan sana atanan ödevleri ve hedefleri görebilirsin. Ödev girişleri ve sonuç güncellemeleri Emir Hoca tarafından yapılmaktadır.")

        with col_odev2:
            st.markdown("#### 📝 Ödev Durum Tablosu")
            res_odev = supabase.table("odev_takip").select("*").eq("ogrenci_id", secili_id).order("id", desc=True).execute()
            df_odev = pd.DataFrame(res_odev.data) if res_odev.data else pd.DataFrame()
            
            if not df_odev.empty:
                gosterilecek_odev = df_odev.rename(columns={'tarih': 'Tarih', 'ders': 'Ders', 'kaynak_konu': 'Kaynak/Konu', 'verilen_soru': 'Hedef Soru', 'dogru': 'D', 'yanlis': 'Y', 'bos': 'B', 'net': 'Net', 'durum': 'Durum'})
                
                # --- 2. TABLO VE GÜNCELLEME İZNİ KONTROLÜ ---
                if st.session_state['rol'] == "ADMIN":
                    # Admin için düzenlenebilir tablo
                    duzenlenen_df = st.data_editor(gosterilecek_odev, disabled=["id", "Tarih", "Ders", "Kaynak/Konu", "Hedef Soru", "Net", "Durum", "ogrenci_id", "raporlandi"], hide_index=True)
                    if st.button("Sonuçları Güncelle", type="primary"):
                        for idx, row in duzenlenen_df.iterrows():
                            d, y, b, he = int(row['D']), int(row['Y']), int(row['B']), int(row['Hedef Soru'])
                            net = d - (y / 4.0) if (d+y+b) > 0 else 0
                            yuzde = (net / he) * 100 if he > 0 else 0
                            d_str = "🟢 Çok İyi" if yuzde >= 75 else "🟡 Orta" if yuzde >= 50 else "🔴 Zayıf" if (d+y+b)>0 else "Bekleniyor"
                            
                            supabase.table("odev_takip").update({"dogru": d, "yanlis": y, "bos": b, "net": float(net), "durum": d_str}).eq("id", int(row['id'])).execute()
                            
                        st.rerun()
                else:
                    # Öğrenci için sadece okunabilir tablo (veri değiştirilemez, buton çıkmaz)
                    st.dataframe(gosterilecek_odev, hide_index=True, use_container_width=True)
            else:
                st.info("Henüz atanmış bir ödev bulunmuyor.")

# --- DENEME ANALİZİ VE NET TAKİBİ ---
    with tab5:
        col_veri_giris, col_grafik = st.columns([1, 2])
        
        with col_veri_giris:
            # --- 1. DENEME KAYDI EKLEME FORMU (SADECE ADMİN) ---
            if st.session_state['rol'] == "ADMIN":
                st.markdown("#### 📝 Deneme Kaydı Ekle")
                
                # ÖĞRENCİNİN SINAV TÜRLERİNE GÖRE DİNAMİK DENEME LİSTESİ OLUŞTURMA
                ogrenci_sinav_str = secili_ogrenci['sinav_turu'] if secili_ogrenci['sinav_turu'] else ""
                deneme_turleri = []
                
                if "TYT" in ogrenci_sinav_str:
                    deneme_turleri.append("TYT Denemesi")
                if "AYT" in ogrenci_sinav_str:
                    deneme_turleri.extend(["AYT Sayısal Denemesi", "AYT Eşit Ağırlık Denemesi", "AYT Sözel Denemesi"])
                if "YDT" in ogrenci_sinav_str:
                    deneme_turleri.append("YDT İngilizce Denemesi")
                if "LGS" in ogrenci_sinav_str:
                    deneme_turleri.append("LGS Denemesi")
                if "KPSS Lisans" in ogrenci_sinav_str:
                    deneme_turleri.append("KPSS Lisans (GK-GY) Denemesi")
                if "KPSS Ön Lisans" in ogrenci_sinav_str:
                    deneme_turleri.append("KPSS Ön Lisans (GK-GY) Denemesi")
                if "KPSS Ortaöğretim" in ogrenci_sinav_str:
                    deneme_turleri.append("KPSS Ortaöğretim (GK-GY) Denemesi")
                if "ÖABT" in ogrenci_sinav_str:
                    deneme_turleri.append("ÖABT Lise Matematik Denemesi")
                if "AGS" in ogrenci_sinav_str:
                    deneme_turleri.append("AGS Denemesi")
                    
                # Eğer öğrenciye özel bir tür bulunamadıysa varsayılan listeyi sunar
                if not deneme_turleri:
                    deneme_turleri = ["TYT Denemesi", "AYT Sayısal Denemesi", "LGS Denemesi", "YDT İngilizce Denemesi"]
                
                # Çift kayıtları engeller
                deneme_turleri = list(dict.fromkeys(deneme_turleri))

                secilen_deneme_turu = st.selectbox("Deneme Türü Seçin:", deneme_turleri)
                kapsam = st.radio("Kapsam:", ["Genel Deneme", "Branş Denemesi"], horizontal=True)
                
                with st.form(f"deneme_form_{secili_id}", clear_on_submit=True):
                    d_adi = st.text_input("Deneme Adı / Yayın Evi:", placeholder="Örn: Özdebir Türkiye Geneli 1")
                    c_soru = st.number_input("Bu Haftaki Toplam Çözülen Soru Sayısı", min_value=0, value=0, step=10)
                    
                    st.markdown("##### 📌 Net Girişi (Yapılan Netleri Giriniz)")
                    netler = {}
                    
                    if kapsam == "Genel Deneme":
                        if secilen_deneme_turu == "TYT Denemesi":
                            netler["Türkçe"] = st.number_input("Türkçe Netiniz:", min_value=-10.0, max_value=40.0, value=0.0, step=0.25)
                            netler["Matematik"] = st.number_input("Matematik Netiniz:", min_value=-10.0, max_value=40.0, value=0.0, step=0.25)
                            netler["Sosyal"] = st.number_input("Sosyal Netiniz:", min_value=-5.0, max_value=20.0, value=0.0, step=0.25)
                            netler["Fen"] = st.number_input("Fen Netiniz:", min_value=-5.0, max_value=20.0, value=0.0, step=0.25)
                        elif "AYT" in secilen_deneme_turu:
                            netler["AYT Matematik"] = st.number_input("AYT Matematik Netiniz:", min_value=-10.0, max_value=40.0, value=0.0, step=0.25)
                            netler["AYT Fizik"] = st.number_input("AYT Fizik Netiniz:", min_value=-5.0, max_value=14.0, value=0.0, step=0.25)
                            netler["AYT Kimya"] = st.number_input("AYT Kimya Netiniz:", min_value=-5.0, max_value=13.0, value=0.0, step=0.25)
                            netler["AYT Biyoloji"] = st.number_input("AYT Biyoloji Netiniz:", min_value=-5.0, max_value=13.0, value=0.0, step=0.25)
                        elif secilen_deneme_turu == "YDT İngilizce Denemesi":
                            netler["İngilizce"] = st.number_input("İngilizce Netiniz:", min_value=-20.0, max_value=80.0, value=0.0, step=0.25)
                        elif secilen_deneme_turu == "LGS Denemesi":
                            netler["Türkçe"] = st.number_input("Türkçe Netiniz:", min_value=-6.6, max_value=20.0, value=0.0, step=0.25)
                            netler["Matematik"] = st.number_input("Matematik Netiniz:", min_value=-6.6, max_value=20.0, value=0.0, step=0.25)
                            netler["Fen Bilimleri"] = st.number_input("Fen Bilimleri Netiniz:", min_value=-6.6, max_value=20.0, value=0.0, step=0.25)
                            netler["T.C. İnkılap"] = st.number_input("T.C. İnkılap Netiniz:", min_value=-3.3, max_value=10.0, value=0.0, step=0.25)
                            netler["Din Kültürü"] = st.number_input("Din Kültürü Netiniz:", min_value=-3.3, max_value=10.0, value=0.0, step=0.25)
                            netler["İngilizce"] = st.number_input("İngilizce Netiniz:", min_value=-3.3, max_value=10.0, value=0.0, step=0.25)
                        elif "KPSS" in secilen_deneme_turu:
                            netler["Türkçe"] = st.number_input("Türkçe Netiniz:", min_value=-10.0, max_value=30.0, value=0.0, step=0.25)
                            netler["Matematik"] = st.number_input("Matematik Netiniz:", min_value=-10.0, max_value=30.0, value=0.0, step=0.25)
                            netler["Tarih"] = st.number_input("Tarih Netiniz:", min_value=-10.0, max_value=27.0, value=0.0, step=0.25)
                            netler["Coğrafya"] = st.number_input("Coğrafya Netiniz:", min_value=-5.0, max_value=18.0, value=0.0, step=0.25)
                            netler["Vatandaşlık"] = st.number_input("Vatandaşlık Netiniz:", min_value=-5.0, max_value=15.0, value=0.0, step=0.25)
                        elif "ÖABT" in secilen_deneme_turu:
                            netler["Analiz"] = st.number_input("Analiz Netiniz:", min_value=-5.0, max_value=24.0, value=0.0, step=0.25)
                            netler["Cebir"] = st.number_input("Cebir Netiniz:", min_value=-5.0, max_value=16.0, value=0.0, step=0.25)
                            netler["Geometri"] = st.number_input("Geometri Netiniz:", min_value=-5.0, max_value=16.0, value=0.0, step=0.25)
                            netler["Uygulamalı Matematik"] = st.number_input("Uygulamalı Matematik Netiniz:", min_value=-5.0, max_value=24.0, value=0.0, step=0.25)
                            netler["Alan Eğitimi"] = st.number_input("Alan Eğitimi Netiniz:", min_value=-5.0, max_value=20.0, value=0.0, step=0.25)
                        elif secilen_deneme_turu == "AGS Denemesi":
                            netler["Sözel Yetenek"] = st.number_input("Sözel Yetenek Netiniz:", min_value=-3.75, max_value=15.0, value=0.0, step=0.25)
                            netler["Sayısal Yetenek"] = st.number_input("Sayısal Yetenek Netiniz:", min_value=-3.75, max_value=15.0, value=0.0, step=0.25)
                            netler["Tarih"] = st.number_input("Tarih Netiniz:", min_value=-1.5, max_value=6.0, value=0.0, step=0.25)
                            netler["Türkiye Coğrafyası"] = st.number_input("Türkiye Coğrafyası Netiniz:", min_value=-1.5, max_value=6.0, value=0.0, step=0.25)
                            netler["Eğitim Bilimleri"] = st.number_input("Eğitim Bilimleri Netiniz:", min_value=-7.5, max_value=30.0, value=0.0, step=0.25)
                            netler["Mevzuat"] = st.number_input("Mevzuat Netiniz:", min_value=-2.0, max_value=8.0, value=0.0, step=0.25)
                    else:
                        secilen_brans = st.selectbox("Branş Dersi Seçin:", ["Türkçe", "Matematik", "AYT Matematik", "Fizik", "Kimya", "Biyoloji", "Tarih", "Coğrafya", "Felsefe", "İngilizce", "Geometri"])
                        netler[secilen_brans] = st.number_input(f"{secilen_brans} Netinizi Giriniz:", min_value=-10.0, max_value=120.0, value=0.0, step=0.25)

                    if st.form_submit_button("Analizi Kaydet", type="primary"):
                        if d_adi:
                            deneme_ekle(secili_id, d_adi, secilen_deneme_turu, kapsam, netler, c_soru)
                            st.success("Deneme kaydı başarıyla eklendi!")
                            st.rerun()
                        else:
                            st.error("Lütfen deneme adını yazınız.")
            else:
                # Öğrenci için sol tarafta sadece bilgilendirme mesajı
                st.info("📊 **Deneme Takibi:** \n\nDeneme netlerin ve analizlerin Emir Hoca tarafından sisteme işlenmektedir. \n\n👉 Sağ taraftaki ekrandan gelişim grafiklerini ve geçmiş sınav sonuçlarını inceleyebilirsin.")

        with col_grafik:
            # --- 2. GRAFİKLER VE GEÇMİŞ DENEMELER (HERKES GÖREBİLİR) ---
            res_deneme = supabase.table("denemeler").select("*").eq("ogrenci_id", secili_id).execute()
            df_deneme = pd.DataFrame(res_deneme.data) if res_deneme.data else pd.DataFrame()
            
            if not df_deneme.empty:
                df_deneme['netler_dict'] = df_deneme['netler_json'].apply(json.loads)
                son_deneme = df_deneme.iloc[-1]
                
                st.markdown(f"#### 📈 Son Deneme: {son_deneme['deneme_adi']}")
                c1, c2 = st.columns(2)
                c1.metric("Son Toplam Net", f"{son_deneme['toplam_net']:g}")
                c2.metric("Tür / Kapsam", f"{son_deneme['deneme_turu']} ({son_deneme['kapsam']})")
                
                st.divider()
                
                grafik_kapsam = st.radio("Grafik Görünümü:", ["🏆 Genel Denemeler Net Grafiği", "🎯 Branş Denemeleri Net Grafiği"], horizontal=True)
                
                grafik_verisi = []
                sira = 1
                
                if "Genel Denemeler" in grafik_kapsam:
                    filtreli_df = df_deneme[df_deneme['kapsam'] == "Genel Deneme"].sort_values(by="id")
                    for index, row in filtreli_df.iterrows():
                        grafik_verisi.append({"Sıra": sira, "Deneme": row['deneme_adi'], "Net": row['toplam_net']})
                        sira += 1
                else:
                    filtreli_df = df_deneme[df_deneme['kapsam'] == "Branş Denemesi"].sort_values(by="id")
                    mevcut_branslar = set()
                    for index, row in filtreli_df.iterrows():
                        mevcut_branslar.update(row['netler_dict'].keys())
                    
                    if mevcut_branslar:
                        secili_brans_grafik = st.selectbox("Grafikte İncelenecek Branş Dersi:", list(mevcut_branslar))
                        for index, row in filtreli_df.iterrows():
                            if secili_brans_grafik in row['netler_dict']:
                                grafik_verisi.append({"Sıra": sira, "Deneme": row['deneme_adi'], "Net": row['netler_dict'][secili_brans_grafik]})
                                sira += 1
                    else:
                        st.info("Henüz kaydedilmiş bir branş denemesi bulunmuyor.")
                
                if grafik_verisi:
                    df_g = pd.DataFrame(grafik_verisi)
                    
                    grafik = alt.Chart(df_g).encode(
                        x=alt.X("Deneme", sort=alt.EncodingSortField(field="Sıra", order="ascending"), title="Denemeler", axis=alt.Axis(labelAngle=-45, grid=False)),
                        y=alt.Y("Net", title="Net Sayısı", scale=alt.Scale(zero=False, padding=20)),
                        tooltip=[alt.Tooltip("Deneme", title="Deneme Adı"), alt.Tooltip("Net", title="Yapılan Net")]
                    )
                    
                    cizgi = grafik.mark_line(interpolate='monotone', strokeWidth=4, color="#e67e22")
                    noktalar = grafik.mark_circle(size=100, color="#d35400")
                    alan = grafik.mark_area(
                        interpolate='monotone', opacity=0.3, 
                        color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color='#f39c12', offset=0), alt.GradientStop(color='rgba(255, 255, 255, 0)', offset=1)], x1=1, x2=1, y1=0, y2=1)
                    )
                    st.altair_chart((alan + cizgi + noktalar).properties(height=350).interactive(), use_container_width=True)
                
                # GEÇMİŞ DENEMELER DETAYLI İNCELEME TABLOSU
                st.markdown("#### 📋 Geçmiş Deneme Kayıtları Detayı")
                gecmis_liste = []
                for idx, row in df_deneme.sort_values(by="id", ascending=False).iterrows():
                    net_detay_str = " | ".join([f"{k}: {v}" for k, v in row['netler_dict'].items()])
                    gecmis_liste.append({
                        "Deneme Adı": row['deneme_adi'],
                        "Sınav Türü": row['deneme_turu'],
                        "Kapsam": row['kapsam'],
                        "Toplam Net": row['toplam_net'],
                        "Ders Netleri Detayı": net_detay_str
                    })
                st.dataframe(pd.DataFrame(gecmis_liste), hide_index=True, use_container_width=True)
                
            else:
                st.info("Henüz deneme verisi girilmemiş.")
                
    # --- 5. DERS KONULARI ---
    with tab6:
        st.markdown("### 📑 Ders Konuları İlerleme Durumu")
        res_konu = supabase.table("konu_takip").select("*").eq("ogrenci_id", secili_id).execute()
        df_konu = pd.DataFrame(res_konu.data) if res_konu.data else pd.DataFrame()
        
        if not df_konu.empty:
            benzersiz_dersler = df_konu['ders'].unique().tolist()
            secili_ders = st.selectbox("Ders Seç:", benzersiz_dersler, key="konu_ders_sec")
            
            df_secili = df_konu[df_konu['ders'] == secili_ders].copy()
            
            # --- ORİJİNAL MÜFREDAT SIRASINA GÖRE DİZME İŞLEMİ ---
            dogru_sira = []
            ogrenci_gruplari = secili_ogrenci['sinav_turu'].split(', ') if secili_ogrenci['sinav_turu'] else []
            for grup in ogrenci_gruplari:
                if grup in SINAV_MÜFREDATI and secili_ders in SINAV_MÜFREDATI[grup]:
                    for k in SINAV_MÜFREDATI[grup][secili_ders]:
                        if k not in dogru_sira:
                            dogru_sira.append(k)
            
            # Veritabanında olup da müfredattan sildiğin henüz güncellenmemiş konular varsa en alta ekle
            for k in df_secili['konu'].tolist():
                if k not in dogru_sira:
                    dogru_sira.append(k)
                    
            # Tabloyu bu doğru sıraya göre ayarla
            df_secili['konu'] = pd.Categorical(df_secili['konu'], categories=dogru_sira, ordered=True)
            df_secili = df_secili.sort_values('konu')
            # -----------------------------------------------------

            # --- SADECE ADMİN İÇİN GÜNCELLEME ALANI ---
            if st.session_state['rol'] == "ADMIN":
                st.markdown("---")
                st.markdown("#### ✏️ Konu Durumu Güncelle")
                secili_konu = st.selectbox("Konu Seç:", df_secili['konu'].tolist(), key="konu_secim_admin")
                mevcut_durum = df_secili[df_secili['konu'] == secili_konu].iloc[0]['durum']
                kayit_id = df_secili[df_secili['konu'] == secili_konu].iloc[0]['id']
                
                durum_secenekleri = ["Başlanmadı", "Çalışıyor", "Tekrar Edilmesi Gerekiyor", "Tamamlandı"]
                idx_durum = durum_secenekleri.index(mevcut_durum) if mevcut_durum in durum_secenekleri else 0
                yeni_durum = st.selectbox("Durum Belirle:", durum_secenekleri, index=idx_durum, key="yeni_durum_admin")
                
                if st.button("Durumu Kaydet", type="primary", key="btn_konu_kaydet"):
                    supabase.table("konu_takip").update({"durum": yeni_durum}).eq("id", int(kayit_id)).execute()
                    st.success("Durum başarıyla güncellendi!")
                    st.rerun()
                st.markdown("---")

            # --- TABLO (HERKES GÖRÜR) ---
            st.markdown("#### 📊 Mevcut İlerleme Tablosu")
            st.table(df_secili[['konu', 'durum']].rename(columns={'konu': 'Konu', 'durum': 'Durum'}).set_index('Konu'))
        else:
            st.warning("Bu öğrenci için müfredat bulunamadı.")

    # --- 6. HAFTALIK ANALİZ ---
    with tab7:
        if st.session_state['rol'] == "ADMIN":
            st.markdown("### 📝 Öğrenci Haftalık Analiz Notları")
            h_tarihi = st.text_input("Analiz Edilecek Hafta:", value="06.07.2026 - 13.07.2026", key="analiz_h_input")
            h_notu = st.text_area("Bu hafta öğrenci nasıldı? Hangi konularda eksiklik görüldü, ne tavsiye edersiniz?", height=150)
            
            if st.button("Analizi Sisteme Kaydet", type="primary"):
                supabase.table("haftalik_analiz").insert({"ogrenci_id": int(secili_id), "hafta_tarihi": h_tarihi, "analiz_notu": h_notu}).execute()
                st.success("Analiz notunuz başarıyla eklendi!")
                st.rerun()
                
            st.markdown("---")
            st.markdown("#### 🗂️ Geçmiş Analiz Raporları")
            res_analiz = supabase.table("haftalik_analiz").select("*").eq("ogrenci_id", secili_id).order("id", desc=True).execute()
            df_analiz = pd.DataFrame(res_analiz.data) if res_analiz.data else pd.DataFrame()
            
            if not df_analiz.empty:
                for idx, row in df_analiz.iterrows():
                    with st.expander(f"🔍 {row['hafta_tarihi']} Analizi"):
                        st.write(row['analiz_notu'])
        else:
            # Öğrenci girdiğinde sadece bu uyarıyı görecek
            st.error("🔒 **Giriş Yetkiniz Yok:** Bu alan sadece öğretmen kullanımı içindir. Analiz raporlarına erişim izniniz bulunmamaktadır.")

    # --- 7. VELİ BİLGİLENDİRME VE RAPOR ARŞİVİ ---
    with tab8:
        if st.session_state['rol'] == "ADMIN":
            st.markdown("### 👨‍👩‍👦 Veli Bilgilendirme ve Seçmeli Rapor Sistemi")
            st.info(f"**Veli:** {secili_ogrenci['veli_ad']} | **İletişim:** {secili_ogrenci['veli_telefon']}")
            
            # (NOT: ALTER TABLE VE CREATE TABLE KISIMLARI KALDIRILDI. SUPABASE PANELİNDEN EKLENECEK.)

            # RAPOR İÇERİĞİ SEÇİMİ
            st.markdown("#### ⚙️ Raporda Neler Yer Alsın?")
            rapor_secenekleri = ["📚 Ödev Durumları", "📈 Genel Deneme Analizi", "🎯 Branş Denemeleri", "📖 Kayıtlı Kaynakların Durumu", "🎯 Haftanın Hedefi"]
            secilen_moduller = st.multiselect("Rapora eklenecek bölümleri işaretleyiniz:", rapor_secenekleri, default=rapor_secenekleri)
            
            haftanin_hedefi = ""
            if "🎯 Haftanın Hedefi" in secilen_moduller:
                haftanin_hedefi = st.text_input("Önümüzdeki Haftanın Hedefi (Örn: Logaritma fasikülü bitecek):")
                
            veli_ozel_not = st.text_area("Veliye İletilecek Özel Not (Emir Hocanın Notu):", height=80, placeholder="Örn: Bu hafta ödevlerini çok düzenli yaptı, gayretinden memnunum...")
            
            # STREAMLIT HAFIZA (SESSION STATE) ANAHTARLARI
            state_key_metin = f"rapor_metni_{secili_id}"
            state_key_html = f"rapor_html_{secili_id}"
            state_key_hazir = f"rapor_hazir_{secili_id}"

            if st.button("Raporu Hazırla", type="primary"):
                # Rapor Metni Başlangıcı (Tarih eklendi)
                su_an = datetime.now()
                veli_metni = f"🎓 *ÖTS - VELİ BİLGİLENDİRME RAPORU* 🎓\n👤 *Öğrenci:* {secili_ogrenci['ad_soyad']}\n📅 *Tarih:* {su_an.strftime('%d.%m.%Y')}\n➖➖➖➖➖➖\n"
                rapor_html = ""
                
                # 1. ÖDEV DURUMLARI (Sadece raporlanmamış yeniler)
                if "📚 Ödev Durumları" in secilen_moduller:
                    res_all_odev = supabase.table("odev_takip").select("id, ders, kaynak_konu, durum, raporlandi").eq("ogrenci_id", secili_id).order("id", desc=True).execute()
                    df_all_odev = pd.DataFrame(res_all_odev.data) if res_all_odev.data else pd.DataFrame()
                    yeni_odevler = df_all_odev[(df_all_odev['raporlandi'] == 0) | (df_all_odev['raporlandi'].isna())] if not df_all_odev.empty else pd.DataFrame()
                    
                    veli_metni += "📚 *BU HAFTAKİ ÖDEV DURUMLARI:*\n"
                    rapor_html += '<div class="kutu"><div class="kutu-baslik">📚 Bu Haftaki Ödev Durumları</div>'
                    if not yeni_odevler.empty:
                        for _, odev in yeni_odevler.iterrows():
                            veli_metni += f" └ {odev['ders']} ({odev['kaynak_konu']}): {odev['durum']}\n"
                            rapor_html += f'<div class="satir">🔹 <b>{odev["ders"]}</b> ({odev["kaynak_konu"]}): <i>{odev["durum"]}</i></div>'
                    else:
                        veli_metni += " └ Raporlanacak yeni ödev kaydı bulunmuyor.\n"
                        rapor_html += '<div class="satir">Raporlanacak yeni ödev kaydı bulunmuyor.</div>'
                    veli_metni += "\n"
                    rapor_html += '</div>'
                
                # 2. GENEL DENEME ANALİZİ
                if "📈 Genel Deneme Analizi" in secilen_moduller:
                    res_genel = supabase.table("denemeler").select("*").eq("ogrenci_id", secili_id).eq("kapsam", "Genel Deneme").order("id", desc=True).execute()
                    genel_denemeler = pd.DataFrame(res_genel.data) if res_genel.data else pd.DataFrame()
                    
                    veli_metni += "📈 *GENEL DENEME ANALİZİ:*\n"
                    rapor_html += '<div class="kutu"><div class="kutu-baslik">📈 Genel Deneme Analizi</div>'
                    
                    raporlanmamis_genel = genel_denemeler[(genel_denemeler['raporlandi'] == 0) | (genel_denemeler['raporlandi'].isna())] if not genel_denemeler.empty else pd.DataFrame()
                    
                    if not raporlanmamis_genel.empty:
                        son_deneme = raporlanmamis_genel.iloc[0]
                        veli_metni += f" 🎯 *Son Deneme:* {son_deneme['deneme_adi']}\n"
                        veli_metni += f" 📊 *Toplam Net:* {son_deneme['toplam_net']}\n\n"
                        
                        rapor_html += f'<div class="satir" style="font-size:18px;">🎯 <b>Son Deneme:</b> {son_deneme["deneme_adi"]}</div>'
                        rapor_html += f'<div class="satir" style="font-size:18px; margin-bottom: 12px;">📊 <b>Toplam Net:</b> {son_deneme["toplam_net"]}</div>'
                        
                        net_dict = json.loads(son_deneme['netler_json'])
                        onceki_deneme = genel_denemeler.iloc[1] if len(genel_denemeler) > 1 else None
                        onceki_net_dict = json.loads(onceki_deneme['netler_json']) if onceki_deneme is not None else {}
                        
                        for ders, net in net_dict.items():
                            fark_metni = ""
                            fark_html = ""
                            if onceki_deneme is not None and ders in onceki_net_dict:
                                fark = net - onceki_net_dict[ders]
                                if fark > 0: 
                                    fark_metni = f" (+{fark:g} net artış 📈)"
                                    fark_html = f' <span style="color:#27ae60; font-size:14px; font-weight:bold;">(+{fark:g} net artış 📈)</span>'
                                elif fark < 0: 
                                    fark_metni = f" ({fark:g} net düşüş 📉)"
                                    fark_html = f' <span style="color:#c0392b; font-size:14px; font-weight:bold;">({fark:g} net düşüş 📉)</span>'
                                else:
                                    fark_metni = " (Net değişmedi ➖)"
                                    fark_html = ' <span style="color:#7f8c8d; font-size:14px;">(Net değişmedi ➖)</span>'
                                    
                            veli_metni += f"  - {ders}: {net} Net{fark_metni}\n"
                            rapor_html += f'<div class="satir" style="margin-left: 15px;">🔸 <b>{ders}:</b> {net} Net{fark_html}</div>'
                    else:
                        veli_metni += " └ Yeni girilmiş genel deneme bulunmuyor.\n"
                        rapor_html += '<div class="satir">Yeni girilmiş genel deneme bulunmuyor.</div>'
                    veli_metni += "\n"
                    rapor_html += '</div>'

                # 3. BRANŞ DENEMELERİ
                if "🎯 Branş Denemeleri" in secilen_moduller:
                    res_brans = supabase.table("denemeler").select("id, deneme_adi, deneme_turu, netler_json, raporlandi").eq("ogrenci_id", secili_id).eq("kapsam", "Branş Denemesi").order("id", desc=True).execute()
                    df_brans = pd.DataFrame(res_brans.data) if res_brans.data else pd.DataFrame()
                    brans_denemeler = df_brans[(df_brans['raporlandi'] == 0) | (df_brans['raporlandi'].isna())] if not df_brans.empty else pd.DataFrame()
                    
                    veli_metni += "🎯 *BRANŞ DENEMELERİ (DERS BAZLI):*\n"
                    rapor_html += '<div class="kutu"><div class="kutu-baslik">🎯 Branş Denemeleri Analizi</div>'
                    if not brans_denemeler.empty:
                        for _, brans in brans_denemeler.iterrows():
                            brans_net = list(json.loads(brans['netler_json']).values())[0] if json.loads(brans['netler_json']) else 0
                            veli_metni += f" └ {brans['deneme_adi']} ({brans['deneme_turu']}): {brans_net} Net\n"
                            rapor_html += f'<div class="satir">🔹 <b>{brans["deneme_adi"]}</b>: {brans_net} Net</div>'
                    else:
                        veli_metni += " └ Yeni branş denemesi bulunmuyor.\n"
                        rapor_html += '<div class="satir">Yeni branş denemesi bulunmuyor.</div>'
                    veli_metni += "\n"
                    rapor_html += '</div>'

                # 4. KAYNAK İLERLEMESİ (YÜZDELİK SİSTEME GÖRE GÜNCELLENDİ)
                if "📖 Kayıtlı Kaynakların Durumu" in secilen_moduller:
                    res_kay = supabase.table("ogrenci_kaynaklari").select("ders, kaynak_adi, toplam_sayfa, mevcut_sayfa").eq("ogrenci_id", secili_id).execute()
                    kaynaklar = pd.DataFrame(res_kay.data) if res_kay.data else pd.DataFrame()
                        
                    veli_metni += "📖 *KİTAP/KAYNAK DURUMLARI:*\n"
                    rapor_html += '<div class="kutu"><div class="kutu-baslik">📖 Kitap & Kaynak İlerlemesi</div>'
                    if not kaynaklar.empty:
                        for _, kaynak in kaynaklar.iterrows():
                            t_sayfa = kaynak.get('toplam_sayfa', 1) or 1
                            m_sayfa = kaynak.get('mevcut_sayfa', 0) or 0
                            yuzde = min((m_sayfa / t_sayfa) * 100, 100.0)
                            
                            if yuzde == 100:
                                durum_metni = "Tüm sorular çözüldü, kitap bitti. 🎉"
                            else:
                                durum_metni = f"%{int(yuzde)} oranında tamamlandı ({m_sayfa}/{t_sayfa} Sayfa)."
                                
                            veli_metni += f" └ {kaynak['ders']} - {kaynak['kaynak_adi']}: {durum_metni}\n"
                            rapor_html += f'<div class="satir">📘 <b>{kaynak["ders"]}</b> - {kaynak["kaynak_adi"]}: <i>{durum_metni}</i></div>'
                    else:
                        veli_metni += " └ Kayıtlı ilerleme bulunmuyor.\n"
                        rapor_html += '<div class="satir">Kayıtlı ilerleme bulunmuyor.</div>'
                    veli_metni += "\n"
                    rapor_html += '</div>'

                # 5. HAFTANIN HEDEFİ
                if "🎯 Haftanın Hedefi" in secilen_moduller and haftanin_hedefi:
                    veli_metni += f"🎯 *ÖNÜMÜZDEKİ HAFTANIN HEDEFİ:*\n └ {haftanin_hedefi}\n\n"
                    rapor_html += f'<div class="not-kutu" style="border-color:#2980b9; background-color:#ebf5fb; margin-top: 20px;"><div class="not-baslik" style="color:#2980b9;">🎯 Önümüzdeki Haftanın Hedefi</div><div style="font-size: 16px;">{haftanin_hedefi}</div></div>'

                # ÖZEL NOT EKLENTİSİ
                veli_metni += f"➖➖➖➖➖➖\n💡 *EMİR HOCANIN NOTU:*\n_{veli_ozel_not if veli_ozel_not else 'Öğrencimizin planlı takibi devam etmektedir.'}_"
                rapor_html += f'<div class="not-kutu"><div class="not-baslik">💡 Emir Hocanın Notu</div><div style="font-size: 16px; white-space: pre-wrap;">{veli_ozel_not if veli_ozel_not else "Öğrencimizin planlı takibi devam etmektedir."}</div></div>'

                # HTML KODU
                v_html = f"""
                <!DOCTYPE html>
                <html lang="tr">
                <head>
                    <meta charset="UTF-8">
                    <title>{secili_ogrenci['ad_soyad']} - Veli Bilgilendirme Raporu</title>
                    <style>
                        @media print {{ body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }} }}
                        body {{ background-color: #f8fafc; line-height: 28px; font-family: 'Segoe UI', Arial, sans-serif; padding: 40px; color: #1e293b; }}
                        .header {{ text-align: center; border-bottom: 4px solid #c5a059; padding-bottom: 15px; margin-bottom: 30px; background-color: #101725; border-radius: 12px; padding: 25px; color:white; box-shadow: 0 5px 15px rgba(0,0,0,0.1);}}
                        .header h1 {{ margin: 0; color: #ebd197; font-size: 28px; letter-spacing: 1px; }}
                        .header p {{ margin: 8px 0 0 0; font-size: 17px; font-weight: 500; color: #cbd5e1; }}
                        .kutu {{ border: 1px solid #e2e8f0; border-radius: 12px; padding: 22px; margin-bottom: 25px; background-color: #ffffff; box-shadow: 0 4px 10px rgba(0,0,0,0.03); page-break-inside: avoid; }}
                        .kutu-baslik {{ font-size: 19px; font-weight: 800; color: #101725; margin-bottom: 18px; border-bottom: 2px solid #f1f5f9; padding-bottom: 10px; }}
                        .satir {{ font-size: 15px; margin-bottom: 10px; color:#334155; }}
                        .not-kutu {{ border: 2px dashed #c5a059; border-radius: 12px; padding: 22px; margin-top: 30px; background-color: #fdfbf7; page-break-inside: avoid; }}
                        .not-baslik {{ font-size: 19px; font-weight: bold; color: #b48630; margin-bottom: 12px; }}
                    </style>
                </head>
                <body onload="setTimeout(function() {{ window.print(); }}, 500);">
                    <div class="header">
                        <h1>🎓 ÖTS VELİ BİLGİLENDİRME RAPORU</h1>
                        <p>👤 Öğrenci: <b>{secili_ogrenci['ad_soyad']}</b> | 📅 Tarih: {su_an.strftime('%d.%m.%Y')}</p>
                    </div>
                    {rapor_html}
                </body>
                </html>
                """

                # Verileri sisteme kaydetme
                st.session_state[state_key_metin] = veli_metni
                st.session_state[state_key_html] = v_html
                st.session_state[state_key_hazir] = True
                
                # Gelecekte Mühürleme Butonunda kullanmak üzere ID'leri Session'a kaydet (Opsiyonel ama güvenli)
                # Sadece ilgili veriler mühürlenir.

            # HAZIRLANAN RAPORUN EKRANA BASILMASI VE ARŞİVLENMESİ
            if st.session_state.get(state_key_hazir, False):
                st.divider()
                st.markdown("#### 📱 Rapor Önizlemesi:")
                st.info(st.session_state[state_key_metin].replace('*', '').replace('_', ''))
                
                v_tel_clean = str(secili_ogrenci['veli_telefon']).replace(" ", "")
                if v_tel_clean.startswith("0"): v_tel_clean = "90" + v_tel_clean[1:]
                veli_wp_url = f"https://wa.me/{v_tel_clean}?text={urllib.parse.quote(st.session_state[state_key_metin])}"
                
                c_v1, c_v2 = st.columns(2)
                c_v1.link_button("📲 Veliye WhatsApp'tan Gönder", veli_wp_url, use_container_width=True)
                c_v2.download_button("📄 PDF Olarak Kaydet (Çıktı Al)", data=st.session_state[state_key_html], file_name=f"{secili_ogrenci['ad_soyad']}_Veli_Raporu.html", mime="text/html", use_container_width=True)

                st.markdown("---")
                st.warning("⚠️ **ÖNEMLİ:** Raporu veliye ilettikten sonra, aşağıdan **Mühürle ve Arşive Kaydet** tuşuna basarak hem bu raporu sisteme kaydedin hem de raporlanan kayıtları sistemden düşürün.")
                
                if st.button("✅ Raporu Gönderdim Olarak Mühürle ve Arşive Kaydet", type="primary"):
                    kaydedilecek_metin = st.session_state[state_key_metin].replace('*', '').replace('_', '')
                    kayit_tarihi = datetime.now().strftime('%d.%m.%Y - %H:%M')
                    
                    # Raporu arşiv tablosuna ekle
                    supabase.table("veli_raporlari").insert({
                        "ogrenci_id": int(secili_id), "tarih": kayit_tarihi, "rapor_metni": kaydedilecek_metin
                    }).execute()
                    
                    # Odev_takip mühürle
                    res_all_odev = supabase.table("odev_takip").select("id, raporlandi").eq("ogrenci_id", secili_id).execute()
                    for o in res_all_odev.data:
                        if o.get("raporlandi") == 0 or o.get("raporlandi") is None:
                            supabase.table("odev_takip").update({"raporlandi": 1}).eq("id", o["id"]).execute()
                            
                    # Denemeler mühürle
                    res_all_deneme = supabase.table("denemeler").select("id, raporlandi").eq("ogrenci_id", secili_id).execute()
                    for d in res_all_deneme.data:
                        if d.get("raporlandi") == 0 or d.get("raporlandi") is None:
                            supabase.table("denemeler").update({"raporlandi": 1}).eq("id", d["id"]).execute()
                    
                    st.session_state[state_key_hazir] = False
                    st.success("✅ Rapor başarıyla arşive eklendi ve sistem sıfırlandı!")
                    st.rerun()

            # GEÇMİŞ RAPORLAR LİSTESİ BÖLÜMÜ (YAZDIRILABİLİR BUTONLAR EKLENDİ)
            st.divider()
            st.markdown("#### 🗂️ Geçmiş Veli Raporları Arşivi")
            res_gecmis = supabase.table("veli_raporlari").select("*").eq("ogrenci_id", secili_id).order("id", desc=True).execute()
            df_gecmis = pd.DataFrame(res_gecmis.data) if res_gecmis.data else pd.DataFrame()
            
            if not df_gecmis.empty:
                for idx, rapor in df_gecmis.iterrows():
                    with st.expander(f"📄 Rapor Tarihi: {rapor['tarih']}"):
                        st.text(rapor['rapor_metni'])
                        
                        # Geçmiş Raporu PDF/HTML olarak indirebilmek için tasarım şablonu
                        arsiv_html = f"""
                        <!DOCTYPE html>
                        <html lang="tr">
                        <head>
                            <meta charset="UTF-8">
                            <title>{secili_ogrenci['ad_soyad']} - Arşiv Raporu</title>
                            <style>
                                @media print {{ body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }} }}
                                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 40px; color: #1e293b; line-height: 1.6; background-color: #f8fafc; }}
                                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }}
                                h2 {{ color: #0f172a; border-bottom: 3px solid #c5a059; padding-bottom: 10px; text-align: center; }}
                                pre {{ font-family: inherit; font-size: 16px; white-space: pre-wrap; padding: 15px; }}
                            </style>
                        </head>
                        <body onload="setTimeout(function() {{ window.print(); }}, 500);">
                            <div class="container">
                                <h2>📂 {secili_ogrenci['ad_soyad']} - Arşiv Raporu<br><span style="font-size: 16px; color: #64748b; font-weight: normal;">Tarih: {rapor['tarih']}</span></h2>
                                <pre>{rapor['rapor_metni']}</pre>
                            </div>
                        </body>
                        </html>
                        """
                        st.download_button("🖨️ Bu Raporun Çıktısını Al (PDF Olarak Kaydet)", data=arsiv_html, file_name=f"{secili_ogrenci['ad_soyad']}_Gecmis_Rapor_{rapor['id']}.html", mime="text/html", key=f"dl_arsiv_{rapor['id']}")
            else:
                st.info("Bu öğrenci için henüz kaydedilmiş bir geçmiş rapor arşivi bulunmuyor. Gönderdiğiniz ve mühürlediğiniz raporlar burada listelenecektir.")
        else:
            st.error("🔒 **Giriş Yetkiniz Yok:** Bu alan sadece öğretmen kullanımı içindir. Veli bilgilendirme raporlarına erişim izniniz bulunmamaktadır.")
            
    # --- 8. GÜNCELLE ---
    with tab9:
        if st.session_state['rol'] == "ADMIN":
            st.markdown("### ✏️ Öğrenci Bilgilerini Güncelle")
            with st.form("guncelle_form"):
                mevcut_turler = secili_ogrenci['sinav_turu'].split(", ") if secili_ogrenci['sinav_turu'] else []
                gecerli_mevcut_turler = [t for t in mevcut_turler if t in secenekler]
                
                y_no = st.text_input("No", value=secili_ogrenci.get('ogrenci_no', ''))
                y_ad = st.text_input("Ad Soyad", value=secili_ogrenci.get('ad_soyad', ''))
                y_turler = st.multiselect("Sınav Grupları (Müfredat)", secenekler, default=gecerli_mevcut_turler)
                y_tel = st.text_input("Öğrenci Tel", value=secili_ogrenci.get('telefon', ''))
                y_vad = st.text_input("Veli Ad", value=secili_ogrenci.get('veli_ad', ''))
                y_vtel = st.text_input("Veli Tel", value=secili_ogrenci.get('veli_telefon', ''))
                y_hedef = st.number_input("Hedef Toplam Net", min_value=0, max_value=120, value=int(secili_ogrenci.get('hedef_net', 80) or 80))
                
                if st.form_submit_button("Bilgileri Güncelle"):
                    if y_ad:
                        yeni_tur_str = ", ".join(y_turler)
                        
                        guncel_data = {
                            "ogrenci_no": y_no,
                            "ad_soyad": y_ad,
                            "sinav_turu": yeni_tur_str,
                            "telefon": y_tel,
                            "veli_ad": y_vad,
                            "veli_telefon": y_vtel,
                            "hedef_net": int(y_hedef)
                        }
                        
                        supabase.table("ogrenciler").update(guncel_data).eq("id", int(secili_id)).execute()
                        
                        # Güncelleme tuşuna basınca yeni sınav grubunun eksik konularını anında atar
                        konulari_ata(secili_id, yeni_tur_str)
                        
                        st.success("Öğrenci bilgileri başarıyla güncellendi!")
                        st.rerun()
                    else:
                        st.error("Öğrenci adı boş olamaz!")
        else:
            # Öğrenci girdiğinde sadece bu uyarıyı görecek
            st.error("🔒 **Giriş Yetkiniz Yok:** Bu alan sadece öğretmen kullanımı içindir. Bilgi güncelleme yetkiniz bulunmamaktadır.")


    # --- 9. SİL ---
    with tab10:
        if st.session_state['rol'] == "ADMIN":
            st.markdown("### 🗑️ Öğrenciyi Sistemden Sil")
            st.error("⚠️ **DİKKAT:** Öğrenciye ait tüm veriler (denemeler, ödevler, çalışma programları) kalıcı olarak silinecektir!")
            if st.button("Kalıcı Olarak Sil", type="primary"):
                ogrenci_sil(int(secili_id))
                st.rerun()
        else:
            # Öğrenci girdiğinde sadece bu uyarıyı görecek
            st.error("🔒 **Giriş Yetkiniz Yok:** Bu alan sadece öğretmen kullanımı içindir. Silme yetkiniz bulunmamaktadır.")
