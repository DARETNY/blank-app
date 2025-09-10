import random
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from google_play_scraper import reviews_all, Sort

# --- Sayfa Ayarları ve Başlık ---
st.set_page_config(
    page_title="Racing Kingdom - Analitik Dashboard",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🎮 Racing Kingdom - Gelişmiş Analitik Dashboard")
st.markdown("""
Bu dashboard, **Racing Kingdom** uygulamasının Google Play yorumlarını analitik bir perspektifle sunar.
Ülke kodlarını seçerek yorumları getirebilir ve görselleştirebilirsiniz.
""")

# --- Sabitler ve Veri Kaynakları ---
APP_ID = 'com.supergears.racingkingdom'
COUNTRIES = {
    'tr': 'Türkiye', 'us': 'Amerika', 'de': 'Almanya', 'gb': 'İngiltere',
    'fr': 'Fransa', 'jp': 'Japonya', 'kr': 'Güney Kore', 'ru': 'Rusya',
    'br': 'Brezilya', 'in': 'Hindistan', 'ca': 'Kanada', 'au': 'Avustralya',
    'es': 'İspanya', 'it': 'İtalya', 'mx': 'Meksika', 'id': 'Endonezya'
}
LANG_MAP = {
    'tr': 'tr', 'us': 'en', 'de': 'de', 'gb': 'en', 'fr': 'fr', 'jp': 'ja',
    'kr': 'ko', 'ru': 'ru', 'br': 'pt', 'in': 'en', 'ca': 'en', 'au': 'en',
    'es': 'es', 'it': 'it', 'mx': 'es', 'id': 'id'
}


# --- Fonksiyonlar ---
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_reviews(country_code: str) -> pd.DataFrame:
    """Belirtilen ülke için Google Play'den yorumları çeker."""
    lang = LANG_MAP.get(country_code, "en")
    try:
        review_data = reviews_all(
            APP_ID,
            lang=lang,
            country=country_code,
            sort=Sort.NEWEST,
            sleep_milliseconds=random.randint(200, 500)
        )
        if not review_data:
            return pd.DataFrame()

        df = pd.DataFrame(review_data)
        df_processed = pd.DataFrame({
            'Kullanıcı Adı': df.get('userName'),
            'Yorum': df.get('content'),
            'Puan': df.get('score'),
            'Tarih': pd.to_datetime(df.get('at'), errors='coerce'),
            'Ülke': COUNTRIES.get(country_code),
            'ISO': country_code
        })
        df_processed['Tarih'] = df_processed['Tarih'].dt.tz_localize(None)
        return df_processed.dropna(subset=['Yorum', 'Puan', 'Tarih'])

    except Exception as e:
        st.warning(f"⚠️ **{COUNTRIES.get(country_code)}** için veri çekilemedi: {e}")
        return pd.DataFrame()


# --- Sidebar ---
st.sidebar.header("⚙️ Analiz Ayarları")
selected_countries_source = st.sidebar.multiselect(
    "Verisi çekilecek ülkeleri seçin:",
    options=list(COUNTRIES.keys()),
    format_func=lambda x: f"{x.upper()} - {COUNTRIES[x]}",
    default=['tr', 'us', 'de']
)

# Çeviri checkbox'ı kaldırıldı

col1, col2 = st.sidebar.columns(2)
if col1.button("📊 Veriyi Getir & Analiz Et", use_container_width=True, type="primary"):
    if not selected_countries_source:
        st.error("Lütfen en az bir ülke seçin.")
    else:
        with st.spinner("Yorum verileri çekiliyor..."):
            all_data = [fetch_reviews(iso) for iso in selected_countries_source]
            all_data = [df for df in all_data if not df.empty]

        if not all_data:
            st.warning("Seçilen ülkeler için hiç yorum bulunamadı.")
        else:
            df_reviews_raw = pd.concat(all_data, ignore_index=True)

            # Çeviri adımı tamamen kaldırıldı, veri doğrudan kullanılıyor
            df_final = df_reviews_raw.copy()

            st.session_state.df_reviews = df_final.sort_values(by="Tarih", ascending=False)
            st.success(f"Analiz tamamlandı! Toplam {len(df_final)} yorum işlendi.")

if col2.button("🧹 Temizle", use_container_width=True):
    st.session_state.clear()
    st.rerun()

# --- Ana Panel ---
if 'df_reviews' not in st.session_state:
    st.info("Analizi başlatmak için soldaki menüden ülke seçip butona tıklayın.")
else:
    df = st.session_state.df_reviews

    st.markdown("---")
    st.subheader("Global Filtreler")
    all_countries_available = sorted(df['Ülke'].unique())
    selected_countries_filter = st.multiselect(
        "Grafikleri ülkeye göre filtrele:",
        options=all_countries_available,
        default=all_countries_available
    )

    if not selected_countries_filter:
        df_main = df.copy()
        st.warning("Tüm ülkeler gösteriliyor. Filtrelemek için en az bir ülke seçin.")
    else:
        df_main = df[df['Ülke'].isin(selected_countries_filter)]

    st.markdown("---")

    if df_main.empty:
        st.error("Mevcut filtreler için gösterilecek veri bulunamadı.")
    else:
        st.header("📌 Genel Metrikler (Filtrelenmiş)")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Ortalama Puan", f"{df_main['Puan'].mean():.2f} ⭐")
        col2.metric("Medyan Puan", f"{df_main['Puan'].median():.1f} ⭐")
        col3.metric("Toplam Yorum", f"{len(df_main):,}")
        col4.metric("Filtrelenen Ülke Sayısı", len(df_main['Ülke'].unique()))

        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Genel Bakış", "📈 Zaman Serisi Analizi", "🌐 Karşılaştırmalı Analiz", "💬 Yorum Detayları"
        ])

        with tab1:
            st.subheader("Puan Dağılımı ve Duygu Analizi")
            st.markdown("##### Duygu Analizi Karnesi")
            total_reviews = len(df_main)
            positive_reviews = len(df_main[df_main['Puan'] >= 4])
            neutral_reviews = len(df_main[df_main['Puan'] == 3])
            negative_reviews = len(df_main[df_main['Puan'] <= 2])
            pos_perc = (positive_reviews / total_reviews) * 100 if total_reviews > 0 else 0
            neu_perc = (neutral_reviews / total_reviews) * 100 if total_reviews > 0 else 0
            neg_perc = (negative_reviews / total_reviews) * 100 if total_reviews > 0 else 0
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("👍 Pozitif Yorumlar (4-5 ⭐)", f"{pos_perc:.1f}%", f"{positive_reviews:,} Yorum")
            kpi2.metric("🤔 Nötr Yorumlar (3 ⭐)", f"{neu_perc:.1f}%", f"{neutral_reviews:,} Yorum")
            kpi3.metric("👎 Negatif Yorumlar (1-2 ⭐)", f"{neg_perc:.1f}%", f"{negative_reviews:,} Yorum")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### Puanların Sayısal Dağılımı")

            puan_counts = df_main['Puan'].value_counts().sort_index()
            puan_counts_df = puan_counts.reset_index()
            puan_counts_df.columns = ['Puan', 'Sayı']

            color_map = {5: '#2ca02c', 4: '#98df8a', 3: '#ff7f0e', 2: '#d62728', 1: '#ff9896'}

            fig_bar_puan = px.bar(
                puan_counts_df,
                x='Puan',
                y='Sayı',
                title="Yorumların Puanlara Göre Dağılımı",
                labels={'Sayı': 'Toplam Yorum Sayısı', 'Puan': 'Verilen Puan'},
                text='Sayı',
                color='Puan',
                color_discrete_map=color_map
            )
            fig_bar_puan.update_layout(xaxis=dict(tickmode='linear'))
            st.plotly_chart(fig_bar_puan, use_container_width=True)

        with tab2:
            st.subheader("Zaman İçindeki Değişimler")
            min_date = df_main['Tarih'].min().date()
            max_date = df_main['Tarih'].max().date()

            start_date, end_date = st.date_input("Tarih aralığı seçin:",
                                                 value=(max_date - timedelta(days=90), max_date), min_value=min_date,
                                                 max_value=max_date, key="date_range_selector")

            if start_date and end_date and start_date <= end_date:
                df_time_filtered = df_main[
                    (df_main['Tarih'].dt.date >= start_date) & (df_main['Tarih'].dt.date <= end_date)]

                if df_time_filtered.empty:
                    st.warning("Seçilen tarih aralığında veri bulunamadı.")
                else:
                    df_time_grouped = df_time_filtered.copy()
                    df_time_grouped['Gün'] = df_time_grouped['Tarih'].dt.date

                    daily_avg = df_time_grouped.groupby('Gün')['Puan'].mean().reset_index()
                    daily_avg = daily_avg.sort_values(by='Gün')
                    daily_avg['7 Günlük Ortalama'] = daily_avg['Puan'].rolling(window=7, min_periods=1).mean()

                    fig = go.Figure()

                    fig.add_trace(go.Bar(
                        x=daily_avg['Gün'],
                        y=daily_avg['Puan'],
                        name='Günlük Ortalama (Ham)',
                        marker_color='lightblue',
                        opacity=0.6
                    ))

                    fig.add_trace(go.Scatter(
                        x=daily_avg['Gün'],
                        y=daily_avg['7 Günlük Ortalama'],
                        name='7 Günlük Ortalama Trendi',
                        mode='lines+markers',
                        line=dict(color='royalblue', width=3)
                    ))

                    fig.update_layout(
                        title='Günlük Ortalama Puan Trendi (7 Günlük Kayan Ortalama)',
                        yaxis_title='Ortalama Puan',
                        xaxis_title='Tarih',
                        yaxis_range=[1, 5]
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    daily_count = df_time_grouped.groupby('Gün').size().reset_index(name='Yorum Sayısı')
                    fig_bar = px.bar(daily_count, x='Gün', y='Yorum Sayısı', title="Günlük Yorum Sayısı")
                    st.plotly_chart(fig_bar, use_container_width=True)

        with tab3:
            st.subheader("Ülkeler Arası Karşılaştırma")
            if len(df_main['Ülke'].unique()) > 1:
                st.markdown("##### Ülke Performans Özeti")
                summary_list = []
                for country in sorted(df_main['Ülke'].unique()):
                    df_country = df_main[df_main['Ülke'] == country]
                    total = len(df_country)
                    avg_score = df_country['Puan'].mean()
                    positive_perc = (len(df_country[df_country['Puan'] >= 4]) / total) * 100
                    negative_perc = (len(df_country[df_country['Puan'] <= 2]) / total) * 100
                    summary_list.append({'Ülke': country, 'Toplam Yorum': total, 'Ortalama Puan': f"{avg_score:.2f}",
                                         '👍 Pozitif Yorum (%)': f"{positive_perc:.1f}%",
                                         '👎 Negatif Yorum (%)': f"{negative_perc:.1f}%"})

                df_summary = pd.DataFrame(summary_list).set_index('Ülke')
                st.dataframe(df_summary, use_container_width=True)

                st.markdown("##### Ülkelere Göre Puan Dağılım Yüzdeleri")
                country_score_counts = df_main.groupby(['Ülke', 'Puan']).size().reset_index(name='Sayı')
                country_totals = df_main.groupby('Ülke').size().reset_index(name='Toplam')
                merged = pd.merge(country_score_counts, country_totals, on='Ülke')
                merged['Yüzde'] = (merged['Sayı'] / merged['Toplam']) * 100

                fig_stacked_bar = px.bar(merged, x='Ülke', y='Yüzde', color='Puan',
                                         title="Ülkelere Göre Puan Dağılımı (%)",
                                         labels={'Yüzde': 'Yorum Yüzdesi (%)', 'Ülke': 'Ülke', 'Puan': 'Puan'},
                                         text=merged['Puan'].astype(str) + "⭐")
                fig_stacked_bar.update_traces(textposition='inside')
                st.plotly_chart(fig_stacked_bar, use_container_width=True)
            else:
                st.info("Karşılaştırma grafikleri için lütfen global filtreden en az iki ülke seçin.")

        with tab4:
            st.subheader("Kullanıcı Yorumları (Detaylı Filtreleme)")
            col1, col2 = st.columns(2)

            filter_puan = col1.multiselect(
                'Puana göre filtrele:', sorted(df_main['Puan'].unique()), default=sorted(df_main['Puan'].unique())
            )
            filter_ulke = col2.multiselect(
                'Ülkeye göre filtrele:', sorted(df_main['Ülke'].unique()), default=sorted(df_main['Ülke'].unique())
            )
            df_display = df_main[df_main['Puan'].isin(filter_puan) & df_main['Ülke'].isin(filter_ulke)]

            # Yorum_TR sütunu kaldırıldı
            st.dataframe(df_display[['Tarih', 'Kullanıcı Adı', 'Puan', 'Yorum', 'Ülke']],
                         use_container_width=True, height=500)

            st.markdown(f"**Toplam Gösterilen Yorum: {len(df_display)}**")
            csv = df_display.to_csv(index=False).encode("utf-8-sig")
            st.download_button(label="⬇️ Filtrelenmiş Yorumları CSV Olarak İndir", data=csv,
                               file_name=f"racing_kingdom_reviews_{datetime.now().strftime('%Y%m%d')}.csv",
                               mime="text/csv")
