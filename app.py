"""
╔══════════════════════════════════════════════════════════════╗
║  app.py — Painel de Cobertura Vacinal no Piauí             ║
║  Projeto: Daniele Alcoforado — Tecnólogo em Ciência de Dados      ║
║  Deploy: Streamlit Community Cloud                          ║
╚══════════════════════════════════════════════════════════════╝

Estrutura:
  🏠 Início         — apresentação e contexto
  🗺️  Mapa do Piauí  — doses por município (gestores)
  📊 Parnaíba       — painel histórico e alertas
  📚 Aprenda        — seção educativa (população geral)
  🧮 Calculadora    — calcula cobertura vacinal
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json, os, requests
from io import StringIO

# ── Configuração da página ─────────────────────────────────────
st.set_page_config(
    page_title="Vacinação no Piauí",
    page_icon="💉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Paleta ────────────────────────────────────────────────────
COR_PIAUI    = "#2196F3"
COR_PARNAIBA = "#FF6B35"
COR_META     = "#4CAF50"
COR_ALERTA   = "#F44336"
COR_COVID    = "#9C27B0"

# ══════════════════════════════════════════════════════════════
# CARREGAMENTO DE DADOS
# ══════════════════════════════════════════════════════════════

@st.cache_data
def carregar_dados():
    """Carrega os parquets gerados pelo 02_limpeza e 03_analise."""
    base = os.path.dirname(__file__)

    df_uni = pd.read_parquet(os.path.join(base, "data", "pni_piaui_unificado.parquet"))
    df_det = pd.read_parquet(os.path.join(base, "data", "pni_piaui_clean.parquet"))

    # Garantir flag
    if "dado_incompleto" not in df_uni.columns:
        df_uni["dado_incompleto"] = df_uni["ano"] == 2019

    return df_uni, df_det


@st.cache_data
def carregar_geojson_piaui():
    """Baixa o GeoJSON dos municípios do Piauí (IBGE) — cacheado."""
    url = (
        "https://raw.githubusercontent.com/tbrugz/geodata-br/"
        "master/geojson/geojs-22-mun.json"
    )
    try:
        r = requests.get(url, timeout=15)
        return r.json()
    except Exception:
        return None


# Tentar carregar; mostrar erro amigável se falhar
try:
    df_uni, df_det = carregar_dados()
    DADOS_OK = True
except Exception as e:
    DADOS_OK = False
    ERRO_DADOS = str(e)

COD_PARNAIBA = "220770"
META = 95.0
ANOS_VALIDOS = [2015, 2016, 2017, 2018, 2020, 2021, 2022]

# ══════════════════════════════════════════════════════════════
# CSS CUSTOMIZADO
# ══════════════════════════════════════════════════════════════

st.markdown("""
<style>
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #1a237e; }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stSidebar"] .stRadio label { color: white !important; }

    /* Métricas */
    [data-testid="stMetric"] {
        background: #f0f4ff;
        border-radius: 12px;
        padding: 16px;
        border-left: 4px solid #2196F3;
    }
    [data-testid="stMetricValue"] { font-size: 2rem !important; font-weight: 700; }

    /* Alerta */
    .alerta-box {
        background: #fff3e0;
        border-left: 5px solid #FF6B35;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 12px 0;
    }
    .critico-box {
        background: #ffebee;
        border-left: 5px solid #F44336;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 12px 0;
    }
    .ok-box {
        background: #e8f5e9;
        border-left: 5px solid #4CAF50;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 12px 0;
    }

    /* Cards educativos */
    .vacina-card {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px;
        margin: 8px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .vacina-card h4 { color: #1a237e; margin-bottom: 8px; }

    /* Hero */
    .hero {
        background: linear-gradient(135deg, #1a237e 0%, #1565C0 50%, #0288D1 100%);
        color: white;
        padding: 40px 32px;
        border-radius: 16px;
        margin-bottom: 24px;
    }
    .hero h1 { font-size: 2.2rem; margin-bottom: 8px; }
    .hero p  { font-size: 1.1rem; opacity: 0.9; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# SIDEBAR — NAVEGAÇÃO
# ══════════════════════════════════════════════════════════════

with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/"
        "Bandeira_do_Piau%C3%AD.svg/320px-Bandeira_do_Piau%C3%AD.svg.png",
        width=120,
    )
    st.markdown("## 💉 Vacinação no Piauí")
    st.markdown("---")

    pagina = st.radio(
        "Navegação",
        options=[
            "🏠 Início",
            "🗺️ Mapa do Piauí",
            "📊 Painel de Parnaíba",
            "📚 Aprenda sobre vacinas",
            "🧮 Calculadora de cobertura",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown(
        "<small>Dados: SI-PNI/DATASUS (2015–2022)<br>"
        "Tecnólogo em Ciência de Dados</small>",
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════
# VERIFICAR DADOS
# ══════════════════════════════════════════════════════════════

if not DADOS_OK:
    st.error(f"⚠️ Não foi possível carregar os dados: {ERRO_DADOS}")
    st.info(
        "Certifique-se de que a pasta `data/` contém:\n"
        "- `pni_piaui_unificado.parquet`\n"
        "- `pni_piaui_clean.parquet`"
    )
    st.stop()

# ══════════════════════════════════════════════════════════════
# 🏠 INÍCIO
# ══════════════════════════════════════════════════════════════

if pagina == "🏠 Início":

    st.markdown("""
    <div class="hero">
        <h1>💉 Vacinação no Piauí</h1>
        <p>Análise da cobertura vacinal infantil (2015–2022) com foco no município de Parnaíba</p>
    </div>
    """, unsafe_allow_html=True)

    # Métricas de destaque
    df_ok = df_uni[df_uni["dado_incompleto"] == False]

    col1, col2, col3, col4 = st.columns(4)

    doses_2022 = df_ok[df_ok["ano"] == 2022]["doses_infantil"].sum()
    doses_2018 = df_ok[df_ok["ano"] == 2018]["doses_infantil"].sum()
    var_covid = (doses_2022 / doses_2018 - 1) * 100

    cob_media = df_det["cobertura_pct"].dropna().mean()
    mun_criticos = (
        df_det[df_det["cobertura_pct"].notna()]
        .groupby("cod_municipio")["cobertura_pct"]
        .mean()
        .lt(META)
        .sum()
    )

    with col1:
        st.metric("📅 Período analisado", "2015–2022", "8 anos de dados")
    with col2:
        st.metric("🏙️ Municípios", "224", "todo o Piauí")
    with col3:
        st.metric(
            "💉 Doses infantis 2022",
            f"{doses_2022/1e6:.2f}M",
            f"{var_covid:+.1f}% vs 2018",
        )
    with col4:
        st.metric(
            "⚠️ Municípios abaixo da meta",
            str(int(mun_criticos)),
            f"de 224 (meta: {META}%)",
            delta_color="inverse",
        )

    st.markdown("---")

    col_a, col_b = st.columns([2, 1])

    with col_a:
        st.subheader("📈 Evolução das doses infantis no Piauí")

        ev = df_ok.groupby(["ano", "fonte"], as_index=False)["doses_infantil"].sum()
        pre = ev[ev["fonte"] == "PySUS"]
        pos = ev[ev["fonte"] == "TabNet_doses"]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pre["ano"], y=pre["doses_infantil"],
            mode="lines+markers", name="PySUS (2015–2018)",
            line=dict(color=COR_PIAUI, width=3), marker=dict(size=8),
            hovertemplate="%{x}: %{y:,.0f} doses<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=list(pre["ano"])[-1:] + list(pos["ano"]),
            y=list(pre["doses_infantil"])[-1:] + list(pos["doses_infantil"]),
            mode="lines+markers", name="TabNet (2020–2022)",
            line=dict(color=COR_COVID, width=3, dash="dash"),
            marker=dict(size=8, symbol="diamond"),
            hovertemplate="%{x}: %{y:,.0f} doses<extra></extra>",
        ))
        fig.add_vrect(
            x0=2019.5, x1=2022.5,
            fillcolor=COR_COVID, opacity=0.07,
            layer="below", line_width=0,
            annotation_text="COVID-19",
            annotation_font_color=COR_COVID,
        )
        fig.add_hline(
            y=doses_2018, line_dash="dot", line_color="gray", opacity=0.5,
            annotation_text=f"Baseline 2018",
        )
        fig.update_layout(
            height=380, margin=dict(t=40, b=40, l=60, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            xaxis=dict(dtick=1), yaxis_title="Doses (< 5 anos)",
            plot_bgcolor="white",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("📋 O que é este painel?")
        st.markdown("""
        Este painel apresenta os dados de **vacinação infantil no Piauí** 
        entre 2015 e 2022.

        **Para quem é este painel:**
        - 👨‍👩‍👧 **Famílias** — saiba se Parnaíba está vacinando bem
        - 🏥 **Gestores** — monitore a cobertura por município
        - 🎓 **Pesquisadores** — explore os dados do SI-PNI

        **Use o menu à esquerda para navegar.**
        """)

        st.markdown("""
        <div class="alerta-box">
        <b>⚠️ Impacto da COVID-19</b><br>
        Em 2021, o Piauí registrou queda de 9,5% nas doses infantis 
        comparado a 2018. A recuperação chegou em 2022 (+6,3%).
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# 🗺️ MAPA DO PIAUÍ
# ══════════════════════════════════════════════════════════════

elif pagina == "🗺️ Mapa do Piauí":

    st.header("🗺️ Mapa de doses infantis por município")
    st.caption("Visualização destinada a gestores e profissionais de saúde")

    df_ok = df_uni[df_uni["dado_incompleto"] == False]

    col_f1, col_f2 = st.columns([1, 1])
    with col_f1:
        ano_sel = st.select_slider(
            "Selecione o ano",
            options=ANOS_VALIDOS,
            value=2022,
        )
    with col_f2:
        metrica_sel = st.radio(
            "Métrica",
            ["Doses infantis (< 5 anos)", "Total de doses"],
            horizontal=True,
        )

    col_metrica = "doses_infantil" if "infantil" in metrica_sel else "doses_total"

    df_mapa = df_ok[df_ok["ano"] == ano_sel][
        ["cod_municipio", "nome_municipio", col_metrica, "cobertura_media"]
    ].copy()
    df_mapa["cod_ibge7"] = df_mapa["cod_municipio"].apply(lambda x: str(x) + "0")

    # Tentar carregar GeoJSON
    geojson = carregar_geojson_piaui()

    if geojson:
        fig_mapa = px.choropleth(
            df_mapa,
            geojson=geojson,
            locations="cod_ibge7",
            featureidkey="properties.id",
            color=col_metrica,
            hover_name="nome_municipio",
            hover_data={
                col_metrica: ":,.0f",
                "cobertura_media": ":.1f",
                "cod_ibge7": False,
            },
            color_continuous_scale=[
                [0.0,  "#B71C1C"],
                [0.3,  "#FF8A65"],
                [0.7,  "#90CAF9"],
                [1.0,  "#1565C0"],
            ],
            title=f"{metrica_sel} — Piauí {ano_sel}",
        )
        fig_mapa.update_geos(
            fitbounds="locations", visible=False,
            bgcolor="rgba(0,0,0,0)",
        )
        fig_mapa.update_layout(
            height=560, margin=dict(t=50, b=10, l=0, r=0),
            coloraxis_colorbar=dict(title="Doses"),
        )
        st.plotly_chart(fig_mapa, use_container_width=True)
    else:
        st.info(
            "🌐 GeoJSON não disponível (sem conexão com o repositório). "
            "Exibindo tabela alternativa."
        )

# Tabela com ranking
    st.subheader(f"Ranking de municípios — {ano_sel}")
    df_rank = (
        df_mapa
        .sort_values(col_metrica, ascending=False)
        .reset_index(drop=True)
    )
    df_rank.index += 1

    # Highlight ANTES do rename — cod_municipio ainda existe
    def highlight_parnaiba(row):
        if row["cod_municipio"] == COD_PARNAIBA:
            return ["background-color: #fff3e0"] * len(row)
        return [""] * len(row)

    df_display = df_rank[["nome_municipio", "cod_municipio", col_metrica, "cobertura_media"]].copy()

    styled = (
        df_display
        .style
        .apply(highlight_parnaiba, axis=1)
    )

    # Renomear só para exibição — depois do style
    styled = styled.relabel_index(
        ["Município", "Cód.", col_metrica.replace("_", " ").title(), "Cobertura média %"],
        axis="columns"
    )

    st.dataframe(styled, height=400, use_container_width=True)

    # Estatísticas rápidas
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        top1 = df_rank.iloc[0]
        st.metric("🥇 Maior volume", top1["nome_municipio"],
                  f"{top1[col_metrica]:,.0f} doses")
    with c2:
        media = df_rank[col_metrica].mean()
        st.metric("📊 Média estadual", f"{media:,.0f} doses", "por município")
    with c3:
        par_val = df_rank[df_rank["cod_municipio"] == COD_PARNAIBA][col_metrica]
        if len(par_val):
            rank_par = df_rank[df_rank["cod_municipio"] == COD_PARNAIBA].index[0]
            st.metric("📍 Parnaíba", f"{par_val.values[0]:,.0f} doses",
                      f"{rank_par}º lugar")


# ══════════════════════════════════════════════════════════════
# 📊 PAINEL DE PARNAÍBA
# ══════════════════════════════════════════════════════════════

elif pagina == "📊 Painel de Parnaíba":

    st.header("📊 Painel de Parnaíba")

    df_ok  = df_uni[df_uni["dado_incompleto"] == False]
    df_par = df_ok[df_ok["cod_municipio"] == COD_PARNAIBA].sort_values("ano")
    df_pi  = df_ok.groupby("ano", as_index=False).agg(
        doses_infantil=("doses_infantil", "sum"),
        cobertura_media=("cobertura_media", "mean"),
    )
    df_pi["doses_media_mun"] = df_pi["doses_infantil"] / 224

    # ── Alertas dinâmicos ─────────────────────────────────────
    ultimo_ano = df_par["ano"].max()
    doses_ult  = df_par[df_par["ano"] == ultimo_ano]["doses_infantil"].values[0]
    doses_base = df_par[df_par["ano"] == 2018]["doses_infantil"].values[0]
    var_par    = (doses_ult / doses_base - 1) * 100

    cob_par = (
        df_det[df_det["cod_municipio"] == COD_PARNAIBA]["cobertura_pct"]
        .dropna().mean()
    )

    if cob_par < 50:
        box_class, icon, msg_cob = "critico-box", "🚨", f"CRÍTICO — cobertura média {cob_par:.1f}%"
    elif cob_par < META:
        box_class, icon, msg_cob = "alerta-box", "⚠️", f"ABAIXO DA META — cobertura média {cob_par:.1f}%"
    else:
        box_class, icon, msg_cob = "ok-box", "✅", f"DENTRO DA META — cobertura média {cob_par:.1f}%"

    st.markdown(f"""
    <div class="{box_class}">
    <b>{icon} Situação de Parnaíba</b><br>
    {msg_cob} (meta nacional: {META}%)<br>
    Doses infantis em {ultimo_ano}: {doses_ult:,.0f}
    ({var_par:+.1f}% vs 2018 — baseline pré-COVID)
    </div>
    """, unsafe_allow_html=True)

    # ── Métricas ──────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("💉 Doses infantis 2022",
                  f"{df_par[df_par['ano']==2022]['doses_infantil'].values[0]:,.0f}")
    with c2:
        st.metric("📉 Pior ano COVID",
                  "2021",
                  f"{(df_par[df_par['ano']==2021]['doses_infantil'].values[0]/doses_base-1)*100:+.1f}% vs 2018")
    with c3:
        st.metric("🎯 Cobertura média (2015–18)",
                  f"{cob_par:.1f}%",
                  f"meta: {META}%",
                  delta_color="off")
    with c4:
        rank = (
            df_ok[df_ok["ano"] == 2022]
            .sort_values("doses_infantil", ascending=False)
            ["cod_municipio"].tolist()
            .index(COD_PARNAIBA) + 1
        )
        st.metric("🏆 Ranking estadual (2022)", f"{rank}º", "em doses infantis")

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📈 Histórico de doses", "🎯 Cobertura por vacina", "📋 Dados completos"])

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_par["ano"], y=df_par["doses_infantil"],
            mode="lines+markers", name="Parnaíba",
            line=dict(color=COR_PARNAIBA, width=3), marker=dict(size=9),
            hovertemplate="Parnaíba %{x}: %{y:,.0f} doses<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=df_pi["ano"], y=df_pi["doses_media_mun"],
            mode="lines+markers", name="Média estadual/município",
            line=dict(color=COR_PIAUI, width=2, dash="dot"), marker=dict(size=7),
            hovertemplate="PI médio %{x}: %{y:,.0f} doses<extra></extra>",
        ))
        fig.add_vrect(
            x0=2019.5, x1=2022.5,
            fillcolor=COR_COVID, opacity=0.07,
            layer="below", line_width=0,
            annotation_text="COVID-19", annotation_font_color=COR_COVID,
        )
        fig.update_layout(
            height=400, plot_bgcolor="white",
            xaxis=dict(dtick=1), yaxis_title="Doses infantis (< 5 anos)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(t=40, b=40, l=60, r=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        df_par_det = df_det[
            (df_det["cod_municipio"] == COD_PARNAIBA) &
            (df_det["cobertura_pct"].notna())
        ]
        if len(df_par_det) == 0:
            st.info("Dados de cobertura % disponíveis apenas para 2015–2019 (PySUS).")
        else:
            cob_vac = (
                df_par_det
                .groupby("vacina_nome", as_index=False)["cobertura_pct"]
                .mean()
                .sort_values("cobertura_pct")
            )
            cob_vac["cor"] = cob_vac["cobertura_pct"].apply(
                lambda x: COR_ALERTA if x < META else COR_META
            )
            cob_vac["status"] = cob_vac["cobertura_pct"].apply(
                lambda x: f"⚠️ {x:.1f}%" if x < META else f"✅ {x:.1f}%"
            )

            fig_vac = go.Figure(go.Bar(
                x=cob_vac["cobertura_pct"],
                y=cob_vac["vacina_nome"],
                orientation="h",
                marker_color=cob_vac["cor"],
                text=cob_vac["status"],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Cobertura média: %{x:.1f}%<extra></extra>",
            ))
            fig_vac.add_vline(
                x=META, line_dash="dash", line_color=COR_META, line_width=2,
                annotation_text=f"Meta: {META}%", annotation_font_color=COR_META,
            )
            fig_vac.update_layout(
                height=max(400, len(cob_vac) * 28),
                plot_bgcolor="white", showlegend=False,
                xaxis_title="Cobertura média (%)", yaxis_title="",
                xaxis_range=[0, 130],
                margin=dict(t=20, b=40, l=220, r=80),
            )
            st.plotly_chart(fig_vac, use_container_width=True)

    with tab3:
        df_show = df_par[["ano", "fonte", "doses_infantil", "doses_total", "cobertura_media"]].copy()
        df_show.columns = ["Ano", "Fonte", "Doses infantis", "Doses total", "Cobertura média %"]
        df_show["Doses infantis"] = df_show["Doses infantis"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "—")
        df_show["Doses total"]    = df_show["Doses total"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "—")
        df_show["Cobertura média %"] = df_show["Cobertura média %"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/D (TabNet)")
        st.dataframe(df_show.set_index("Ano"), use_container_width=True)
        st.caption("N/D = dado não disponível nesta fonte. Cobertura % disponível apenas via PySUS (2015–2018).")


# ══════════════════════════════════════════════════════════════
# 📚 APRENDA SOBRE VACINAS
# ══════════════════════════════════════════════════════════════

elif pagina == "📚 Aprenda sobre vacinas":

    st.header("📚 Aprenda sobre vacinas")
    st.markdown(
        "Esta seção é para **famílias e comunidade**. "
        "Linguagem simples, sem termos técnicos."
    )

    # ── Por que vacinar? ──────────────────────────────────────
    with st.expander("❓ Por que vacinar meu filho?", expanded=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("""
            Vacinas **protegem contra doenças graves** que podem matar ou deixar 
            sequelas para sempre. Elas funcionam "ensinando" o corpo a reconhecer 
            e combater o vírus ou bactéria antes que a criança fique doente.

            **Quando muitas crianças são vacinadas, todos ficam mais protegidos** — 
            inclusive bebês pequeninhos que ainda não podem tomar vacinas e pessoas 
            com doenças que enfraquecem a imunidade. Isso se chama **imunidade coletiva**.

            A meta nacional é que **95% das crianças** sejam vacinadas para que 
            doenças como poliomielite e sarampo não voltem a circular.
            """)
        with col2:
            st.info("💡 **Sabia que?**\n\nO Brasil erradicou a poliomielite em 1989 graças à vacinação. Mas se as taxas caírem, o vírus pode voltar.")

    # ── O calendário vacinal ──────────────────────────────────
    st.subheader("📅 Calendário vacinal infantil")
    st.markdown("As principais vacinas que seu filho deve tomar:")

    VACINAS_INFO = [
        {
            "nome": "BCG",
            "quando": "Ao nascer",
            "protege": "Tuberculose grave (meningite tuberculosa)",
            "local": "Maternidade ou UBS",
            "icon": "🍼",
        },
        {
            "nome": "Hepatite B",
            "quando": "Ao nascer + 2 meses",
            "protege": "Hepatite B (doença grave do fígado)",
            "local": "Maternidade ou UBS",
            "icon": "🍼",
        },
        {
            "nome": "Pentavalente (DTP + Hib + HepB)",
            "quando": "2, 4 e 6 meses",
            "protege": "Difteria, Coqueluche, Tétano, Meningite por Hib, Hepatite B",
            "local": "UBS",
            "icon": "👶",
        },
        {
            "nome": "VIP — Poliomielite inativada",
            "quando": "2, 4 e 6 meses",
            "protege": "Poliomielite (paralisia infantil)",
            "local": "UBS",
            "icon": "👶",
        },
        {
            "nome": "VOP — Poliomielite oral",
            "quando": "Reforços aos 15 meses e 4 anos",
            "protege": "Poliomielite (paralisia infantil)",
            "local": "UBS e campanhas",
            "icon": "💧",
        },
        {
            "nome": "Pneumocócica 10V",
            "quando": "2, 4 meses + reforço aos 12 meses",
            "protege": "Pneumonia, meningite e otite por pneumococo",
            "local": "UBS",
            "icon": "👶",
        },
        {
            "nome": "Rotavírus (VORH)",
            "quando": "2 e 4 meses",
            "protege": "Diarreia grave por rotavírus",
            "local": "UBS",
            "icon": "👶",
        },
        {
            "nome": "Meningocócica C",
            "quando": "3 e 5 meses + reforço aos 12 meses",
            "protege": "Meningite meningocócica C",
            "local": "UBS",
            "icon": "👶",
        },
        {
            "nome": "Tríplice Viral (SCR)",
            "quando": "12 meses e 15 meses",
            "protege": "Sarampo, Caxumba e Rubéola",
            "local": "UBS",
            "icon": "🧒",
        },
        {
            "nome": "Febre Amarela",
            "quando": "9 meses e 4 anos",
            "protege": "Febre Amarela",
            "local": "UBS",
            "icon": "🌿",
        },
        {
            "nome": "Varicela",
            "quando": "15 meses",
            "protege": "Catapora",
            "local": "UBS",
            "icon": "🧒",
        },
        {
            "nome": "HPV",
            "quando": "9 a 14 anos (meninas e meninos)",
            "protege": "Câncer de colo do útero e outras doenças por HPV",
            "local": "UBS e escolas",
            "icon": "🏫",
        },
    ]

    for v in VACINAS_INFO:
        with st.container():
            st.markdown(f"""
            <div class="vacina-card">
                <h4>{v['icon']} {v['nome']}</h4>
                <b>Quando:</b> {v['quando']}<br>
                <b>Protege contra:</b> {v['protege']}<br>
                <b>Onde tomar:</b> {v['local']}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ── FAQ ───────────────────────────────────────────────────
    st.subheader("❓ Perguntas frequentes")

    with st.expander("Vacina pode causar a doença?"):
        st.markdown("""
        **Não.** As vacinas são feitas com vírus ou bactérias mortos, inativados ou 
        apenas pedaços deles — não têm a capacidade de causar a doença. 
        O que pode aparecer são reações leves como febrinha ou dorzinha no braço, 
        que são sinais de que o corpo está criando proteção.
        """)

    with st.expander("Meu filho tomou a vacina e ficou doente — foi a vacina?"):
        st.markdown("""
        Provavelmente não. Reações como febre baixa, choro e vermelhidão no local 
        da aplicação são normais e passam em 1–2 dias. Se aparecerem sintomas 
        mais sérios, procure a UBS ou pronto-socorro e informe que a criança foi vacinada.
        """)

    with st.expander("Onde vacinar em Parnaíba?"):
        st.markdown("""
        Todas as **Unidades Básicas de Saúde (UBS)** de Parnaíba oferecem 
        vacinas gratuitamente. Leve a **caderneta de vacinação** da criança. 
        
        Para campanhas especiais (como Polio e Influenza), fique de olho nas 
        datas divulgadas pela Secretaria Municipal de Saúde de Parnaíba.
        """)

    with st.expander("O que é a meta de 95% e por que ela importa?"):
        st.markdown("""
        O Programa Nacional de Imunizações (PNI) estabelece que **95% das crianças** 
        de cada município devem ser vacinadas para que as doenças não circulem.

        Quando essa meta não é atingida, surgem **bolsões de crianças desprotegidas** 
        que podem ser afetadas em surtos. Foi o que aconteceu com o sarampo no Brasil 
        em 2018–2019, quando cidades que tinham erradicado a doença voltaram a ter casos.
        """)


# ══════════════════════════════════════════════════════════════
# 🧮 CALCULADORA DE COBERTURA
# ══════════════════════════════════════════════════════════════

elif pagina == "🧮 Calculadora de cobertura":

    st.header("🧮 Calculadora de cobertura vacinal")

    col_intro, col_form = st.columns([1, 1])

    with col_intro:
        st.markdown("""
        ### Para gestores e profissionais de saúde

        A **cobertura vacinal** é calculada dividindo o número de doses 
        aplicadas pela população-alvo estimada, multiplicado por 100.

        **Fórmula:**
        """)
        st.latex(r"\text{Cobertura}(\%) = \frac{\text{Doses aplicadas}}{\text{População-alvo}} \times 100")

        st.markdown("""
        A meta nacional do PNI é de **95%** para a maioria das vacinas 
        do calendário infantil básico.

        > ⚠️ Valores acima de 100% são possíveis quando o município recebe 
        > doses de moradores de outras localidades (campanhas). O DATASUS 
        > registra esse comportamento normalmente.
        """)

    with col_form:
        st.markdown("### Calcule agora")

        vacina_nome = st.text_input("Nome da vacina (opcional)", placeholder="ex: Poliomielite")
        doses = st.number_input("Doses aplicadas", min_value=0, step=1, value=0)
        pop   = st.number_input("População-alvo estimada", min_value=1, step=1, value=100)
        meta_calc = st.slider("Meta de cobertura (%)", 50, 100, 95)

        if doses > 0 and pop > 0:
            cobertura = (doses / pop) * 100

            st.markdown("---")
            st.markdown(f"### Resultado")

            if cobertura >= meta_calc:
                st.success(f"✅ **{cobertura:.1f}%** — Acima da meta ({meta_calc}%)")
                st.balloons()
            elif cobertura >= meta_calc * 0.9:
                st.warning(f"⚠️ **{cobertura:.1f}%** — Próximo da meta, mas ainda abaixo de {meta_calc}%")
            else:
                st.error(f"🚨 **{cobertura:.1f}%** — Abaixo da meta ({meta_calc}%)")

            # Visualização
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=cobertura,
                delta={"reference": meta_calc, "suffix": "%"},
                title={"text": vacina_nome or "Cobertura vacinal"},
                gauge={
                    "axis": {"range": [0, max(150, cobertura + 10)], "ticksuffix": "%"},
                    "bar": {"color": COR_META if cobertura >= meta_calc else COR_ALERTA},
                    "steps": [
                        {"range": [0, 50],        "color": "#FFCDD2"},
                        {"range": [50, meta_calc], "color": "#FFE0B2"},
                        {"range": [meta_calc, max(150, cobertura + 10)], "color": "#C8E6C9"},
                    ],
                    "threshold": {
                        "line": {"color": COR_META, "width": 3},
                        "thickness": 0.75,
                        "value": meta_calc,
                    },
                },
                number={"suffix": "%", "font": {"size": 40}},
            ))
            fig_gauge.update_layout(height=300, margin=dict(t=60, b=20, l=30, r=30))
            st.plotly_chart(fig_gauge, use_container_width=True)

            # Quantas doses faltam
            if cobertura < meta_calc:
                doses_faltam = int(np.ceil(pop * meta_calc / 100)) - doses
                st.info(f"📌 Faltam **{doses_faltam:,} doses** para atingir a meta de {meta_calc}%")
        else:
            st.info("👆 Preencha doses e população para calcular.")

    st.markdown("---")

    # ── Comparativo com os dados reais ────────────────────────
    st.subheader("📊 Compare com dados reais do Piauí (2015–2018)")

    df_comp = (
        df_det[df_det["cobertura_pct"].notna()]
        .groupby(["vacina_nome", "ano"], as_index=False)["cobertura_pct"]
        .mean()
        .rename(columns={"cobertura_pct": "cobertura_media"})
    )

    vacinas_disp = sorted(df_comp["vacina_nome"].unique().tolist())
    vacina_sel   = st.selectbox("Selecione uma vacina", vacinas_disp)

    df_vac = df_comp[df_comp["vacina_nome"] == vacina_sel]

    if len(df_vac):
        fig_comp = px.bar(
            df_vac, x="ano", y="cobertura_media",
            color="cobertura_media",
            color_continuous_scale=[
                [0,   "#B71C1C"],
                [0.5, "#FF8A65"],
                [0.95,"#A5D6A7"],
                [1,   "#1B5E20"],
            ],
            range_color=[0, 120],
            title=f"Cobertura média estadual — {vacina_sel}",
            labels={"cobertura_media": "Cobertura (%)", "ano": "Ano"},
            text=df_vac["cobertura_media"].apply(lambda x: f"{x:.1f}%"),
        )
        fig_comp.add_hline(
            y=META, line_dash="dash", line_color=COR_META, line_width=2,
            annotation_text=f"Meta: {META}%", annotation_font_color=COR_META,
        )
        fig_comp.update_traces(textposition="outside")
        fig_comp.update_layout(
            height=380, plot_bgcolor="white", coloraxis_showscale=False,
            xaxis=dict(dtick=1), yaxis_range=[0, 130],
            margin=dict(t=60, b=40, l=60, r=20),
        )
        st.plotly_chart(fig_comp, use_container_width=True)
