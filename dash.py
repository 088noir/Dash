import io
import re
import requests
from datetime import datetime, timezone

import ccxt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Dependências do ReportLab para geração do relatório PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# ==================== CONFIGURAÇÃO DA PÁGINA ====================
st.set_page_config(
    page_title="Crypto Macro, Relative Strength & Volatility Dashboard", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialização de múltiplas exchanges via CCXT para fallback universal
exchanges_fallback = [
    ccxt.binance({'enableRateLimit': True}),
    ccxt.bybit({'enableRateLimit': True}),
    ccxt.kucoin({'enableRateLimit': True}),
    ccxt.mexc({'enableRateLimit': True})
]

# ==================== SELETOR DE IDIOMA E DICIONÁRIO DE TEXTOS ====================
TEXTS = {
    "PT": {
        "title": " Crypto Macro, Relative Strength & Volatility Dashboard",
        "refresh": " Forçar Atualização",
        "connection": "Conexão",
        "last_update": "Última Atualização",
        "tab1": " 1. Ativo Individual & Fórmulas",
        "tab2": " 2. Detector de Compressão & Narrativas",
        "tab3": " 3. Duelo & Correlação de Pearson (A vs B)",
        "tab4": " 4. Top 10 Highlights & Rotatividade de Liquidez",
        "tab5": " 5. Relatório Detalhado da Moeda & Exportação",
        "tab1_title": "ANÁLISE TÉCNICA E MATRIZ DE VALORIZAÇÃO RELATIVA",
        "tab1_expander_title": " Legenda e Guia de Leitura da Aba 1",
        "tab1_expander_body": """
        - **Tendência Macro (SMA 200):** Se o preço estiver acima da Média Móvel de 200 períodos, a estrutura de longo prazo é de alta (**Bullish**).
        - **Distância SMA 200 (%):** Mede a extensão do movimento. Valores > **+50%** indicam sobrecompra. Valores negativos indicam desconto.
        - **5 Fórmulas Relativas:** Medem o valor do ativo frente a denominadores macro. Se o rácio estiver a subir, o ativo gera **Alfa**.
        - **Indicadores Técnicos Incluídos:** VWAP, ATR (14), OBV, RSI (14), Volume Ratio (vs MA20), SMA 50 e SMA 200.
        """,
        "input_ticker": "Introduza o Ticker (Ex: SOL/USDC, DEEP, BTCUSD):",
        "select_tf": "Timeframe do Gráfico:",
        "log_scale": "Escala Logarítmica",
        "curr_price": "Preço Atual",
        "macro_trend": "Tendência Macro (SMA 200)",
        "inter_trend": "Tendência Intermédia (SMA 50)",
        "dist_sma200": "Distância SMA 200",
        "bullish": " Bullish (Alta)",
        "bearish": " Bearish (Baixa)",
        "rel_val_header": " Valorização Relativa pelas 5 Fórmulas Macro",
        "chart_title": "Gráfico de Preço e Indicadores",
        "no_data_all": "Não foi possível obter dados para o ticker introduzido em nenhuma das exchanges suportadas (Binance, Bybit, KuCoin, MEXC).",
        
        "tab2_title": " Detector de Compressão BBW Squeeze & Filtro de Narrativas",
        "tab2_expander_title": " Legenda e Interpretação de Filtros & Compressão",
        "tab2_expander_body": """
        - **Filtro de Narrativas:** Seleciona setores específicos (ex: *Layer 1*, *DeFi*, *Artificial Intelligence*).
        - **Compressão BBW (%):**
          - ** Extrema (80% a 100%):** MÁXIMA COMPRESSÃO. Um movimento explosivo (*Breakout*) está iminente.
          - ** Moderada (50% a 79%):** Consolidação normal.
        - **Alerta de Rotatividade (Liquidez ⚡🔄):** Ativos onde o Volume Diário representa mais de **15% do Market Cap** indicam interesse comprador anómalo.
        """,
        "select_cat": " Selecionar Categoria / Narrativa (CoinGecko):",
        "all_cats": "Todas as Categorias",
        "search_coin": " Pesquisar moeda específica:",
        "all_coins": "Todas as moedas",
        
        "tab3_title": " Duelo de Força Relativa & Matriz de Correlação (Pearson r)",
        "tab3_expander_title": " Legenda e Interpretação da Correlação de Pearson (r)",
        "tab3_expander_body": """
        - **Coeficiente de Correlação de Pearson ($r$):**
          - **$r \\in [+0.7, +1.0]$ (Forte Correlação Positiva):** Os dois ativos movem-se na mesma direção.
          - **$r \\in [-0.3, +0.3]$ (Descorrelação / Independência):** Os ativos movem-se de forma independente.
          - **$r \\in [-1.0, -0.4]$ (Correlação Inversa):** Movem-se em direções opostas.
        """,
        "asset_a": "Ativo A:",
        "asset_b": "Ativo B:",
        "duel_tf": "Timeframe do Duelo:",
        "pearson_metric": "Correlação de Pearson r",
        "narrative_reading": "Leitura da Narrativa",
        "corr_strong": " Forte Correlação Positiva (Movem-se juntos)",
        "corr_inverse": " Correlação Inversa (Movem-se em sentidos opostos)",
        "corr_uncorrelated": " Descorrelação de Narrativa (Movimentos Independentes)",
        "scorecard": "Placar do Duelo",
        "strongest": "Mais Forte",
        "winner": "Vencedor",
        
        "tab4_title": " Top 10 Highlights & Rotatividade de Liquidez (Low/Mid Cap Pump Alerts)",
        "tab4_expander_title": " Legenda e Rotatividade de Liquidez",
        "tab4_expander_body": """
        - **Alerta de Pump em Low/Mid Caps:** Identifica moedas com capitalização modesta cujo volume diário disparou em relação ao seu tamanho (Rácio Vol/MC elevado).
        """,
        "top10_pump": " Low/Mid Cap Pump Alerts (Maior Rotatividade Vol/MC)",
        "top10_bbw": " Top 10 Maior Compressão BBW",
        "top10_accum": " Top 10 Maior Acumulação (7D)",
        "top10_dist": " Top 10 Maior Distribuição (7D)",
        
        "tab5_title": " Relatório Detalhado da Moeda & Exportação (PDF / PNG)",
        "select_report_coin": "Selecione a Moeda Principal do Relatório:",
        "include_duel": "Incluir Comparação / Duelo no Relatório PDF",
        "select_versus": "Selecione o Ativo B para Duelo:",
        "download_options": " Opções de Descarregamento",
        "download_pdf": " Descarregar Relatório Completo em PDF",
        "png_info": " Para descarregar qualquer gráfico em **PNG**, utiliza o ícone da câmara no canto superior direito de cada gráfico.",
        "consolidated_metrics": " Métricas Consolidadas para",
        "multi_tf_title": " Painel de Gráficos Multitimeframe para",
        "log_scale_rep": "Escala Logarítmica nos Gráficos do Relatório",
        
        "audit": " Auditoria de Dados: Filtro rigoroso anti-RWA/Dívida/USD1/USD.AI ativado.",
        "execution": " Execução via:"
    },
    "EN": {
        "title": " Crypto Macro, Relative Strength & Volatility Dashboard",
        "refresh": " Force Refresh",
        "connection": "Connection",
        "last_update": "Last Update",
        "tab1": " 1. Individual Asset & Formulas",
        "tab2": " 2. Compression Detector & Narratives",
        "tab3": " 3. Duel & Pearson Correlation (A vs B)",
        "tab4": " 4. Top 10 Highlights & Liquidity Turnover",
        "tab5": " 5. Detailed Coin Report & Export",
        "tab1_title": "TECHNICAL ANALYSIS & RELATIVE VALUATION MATRIX",
        "tab1_expander_title": " Legend & Reading Guide for Tab 1",
        "tab1_expander_body": """
        - **Macro Trend (SMA 200):** If price is above 200-period Moving Average, long-term structure is **Bullish**.
        - **SMA 200 Distance (%):** Measures trend extension. Values > **+50%** indicate overbought. Negative values indicate discount.
        - **5 Relative Formulas:** Measure asset value against macro benchmarks. Rising ratio indicates **Alpha** generation.
        - **Technical Indicators:** VWAP, ATR (14), OBV, RSI (14), Volume Ratio (vs MA20), SMA 50 and SMA 200.
        """,
        "input_ticker": "Enter Ticker (e.g. SOL/USDC, DEEP, BTCUSD):",
        "select_tf": "Chart Timeframe:",
        "log_scale": "Logarithmic Scale",
        "curr_price": "Current Price",
        "macro_trend": "Macro Trend (SMA 200)",
        "inter_trend": "Intermediate Trend (SMA 50)",
        "dist_sma200": "SMA 200 Distance",
        "bullish": " Bullish (Up)",
        "bearish": " Bearish (Down)",
        "rel_val_header": " Relative Valuation via 5 Macro Formulas",
        "chart_title": "Price Chart & Indicators",
        "no_data_all": "Could not fetch data for the entered ticker on any supported exchange.",
        
        "tab2_title": " BBW Squeeze Compression Detector & Narrative Filter",
        "tab2_expander_title": " Legend & Interpretation of Filters & Compression",
        "tab2_expander_body": """
        - **Narrative Filter:** Select specific sectors (e.g. *Layer 1*, *DeFi*, *Artificial Intelligence*).
        - **BBW Compression (%):**
          - ** Extreme (80% to 100%):** MAXIMUM COMPRESSION. An explosive move (*Breakout*) is imminent.
          - ** Moderate (50% to 79%):** Normal consolidation.
        - **Turnover Alert (Liquidity ⚡🔄):** Assets where Daily Volume exceeds **15% of Market Cap** show anomalous buying interest.
        """,
        "select_cat": " Select Category / Narrative (CoinGecko):",
        "all_cats": "All Categories",
        "search_coin": " Search specific coin:",
        "all_coins": "All coins",
        
        "tab3_title": " Relative Strength Duel & Correlation Matrix (Pearson r)",
        "tab3_expander_title": " Legend & Interpretation of Pearson Correlation (r)",
        "tab3_expander_body": """
        - **Pearson Correlation Coefficient ($r$):**
          - **$r \\in [+0.7, +1.0]$ (Strong Positive Correlation):** Both assets move in the same direction.
          - **$r \\in [-0.3, +0.3]$ (Uncorrelated / Independent):** Assets move independently.
          - **$r \\in [-1.0, -0.4]$ (Inverse Correlation):** Move in opposite directions.
        """,
        "asset_a": "Asset A:",
        "asset_b": "Asset B:",
        "duel_tf": "Duel Timeframe:",
        "pearson_metric": "Pearson Correlation r",
        "narrative_reading": "Narrative Reading",
        "corr_strong": " Strong Positive Correlation (Moving together)",
        "corr_inverse": " Inverse Correlation (Moving in opposite directions)",
        "corr_uncorrelated": " Narrative Uncorrelation (Independent movements)",
        "scorecard": "Duel Scorecard",
        "strongest": "Strongest",
        "winner": "Winner",
        
        "tab4_title": " Top 10 Highlights & Liquidity Turnover (Low/Mid Cap Pump Alerts)",
        "tab4_expander_title": " Legend & Liquidity Turnover",
        "tab4_expander_body": """
        - **Low/Mid Cap Pump Alert:** Identifies coins with modest market cap whose daily volume spiked relative to their size (High Vol/MC Ratio).
        """,
        "top10_pump": " Low/Mid Cap Pump Alerts (Highest Vol/MC Turnover)",
        "top10_bbw": " Top 10 Highest BBW Squeeze",
        "top10_accum": " Top 10 Highest Accumulation (7D)",
        "top10_dist": " Top 10 Highest Distribution (7D)",
        
        "tab5_title": " Detailed Coin Report & Export (PDF / PNG)",
        "select_report_coin": "Select Main Report Coin:",
        "include_duel": "Include Comparison / Duel in PDF Report",
        "select_versus": "Select Asset B for Duel:",
        "download_options": " Download Options",
        "download_pdf": " Download Full PDF Report",
        "png_info": " To download any chart as **PNG**, click the camera icon at the top right of each chart.",
        "consolidated_metrics": " Consolidated Metrics for",
        "multi_tf_title": " Multi-timeframe Chart Panel for",
        "log_scale_rep": "Logarithmic Scale on Report Charts",
        
        "audit": " Data Audit: Strict anti-RWA/Debt/USD1/USD.AI filter enabled.",
        "execution": " Execution via:"
    }
}

st.sidebar.title(" Configurações / Settings")
lang = st.sidebar.radio("Idioma / Language:", ["PT", "EN"], index=0)
t = TEXTS[lang]

# ==================== FUNÇÃO DE FORMATAÇÃO DINÂMICA ====================
def smart_format(val):
    if val is None or pd.isna(val):
        return "N/A"
    try:
        num = float(val)
    except (ValueError, TypeError):
        return str(val)
    
    if num == 0:
        return "0.00"
        
    abs_num = abs(num)
    if abs_num < 0.0001:
        return f"{num:.4e}"
    elif abs_num < 0.01:
        return f"{num:.6f}"
    elif abs_num < 1.0:
        return f"{num:.4f}"
    elif abs_num < 1000:
        return f"{num:,.2f}"
    else:
        return f"{num:,.2f}"

# ==================== FUNÇÕES DE INDICADORES TÉCNICOS E ALERTAS ====================

def calcular_indicadores_tecnicos(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or len(df) < 5:
        return df

    df = df.copy()
    tp = (df['high'] + df['low'] + df['close']) / 3
    df['vwap'] = (tp * df['volume']).cumsum() / df['volume'].cumsum().replace(0, np.nan)

    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr_14'] = df['tr'].rolling(window=14, min_periods=1).mean()

    df['obv'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
    df['sma_50'] = df['close'].rolling(window=min(50, len(df)), min_periods=1).mean()
    df['sma_200'] = df['close'].rolling(window=min(200, len(df)), min_periods=1).mean()

    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi_14'] = 100 - (100 / (1 + rs))

    df['vol_ma20'] = df['volume'].rolling(window=20, min_periods=1).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma20'].replace(0, np.nan)

    return df


def calcular_forca_relativa_e_comparacao(df_ativo: pd.DataFrame, df_benchmark: pd.DataFrame) -> dict:
    if df_ativo.empty or df_benchmark.empty:
        return {
            "var_ativo_24h": 0.0, "var_bench_24h": 0.0, "alpha_24h": 0.0, "alpha_tf": 0.0,
            "var_ativo_7d": 0.0, "var_bench_7d": 0.0, "status_rs": " NEUTRAL",
            "correlacao": 0.0
        }

    min_len = min(len(df_ativo), len(df_benchmark))
    p_ativo = df_ativo['close'].iloc[-min_len:]
    p_bench = df_benchmark['close'].iloc[-min_len:]

    idx_tf = -2 if min_len >= 2 else 0
    ret_ativo_tf = ((p_ativo.iloc[-1] - p_ativo.iloc[idx_tf]) / p_ativo.iloc[idx_tf]) * 100 if p_ativo.iloc[idx_tf] > 0 else 0
    ret_bench_tf = ((p_bench.iloc[-1] - p_bench.iloc[idx_tf]) / p_bench.iloc[idx_tf]) * 100 if p_bench.iloc[idx_tf] > 0 else 0
    alpha_tf = ret_ativo_tf - ret_bench_tf

    idx_24h = -24 if min_len >= 24 else -2
    idx_7d = -168 if min_len >= 168 else 0

    ret_ativo_24h = ((p_ativo.iloc[-1] - p_ativo.iloc[idx_24h]) / p_ativo.iloc[idx_24h]) * 100
    ret_bench_24h = ((p_bench.iloc[-1] - p_bench.iloc[idx_24h]) / p_bench.iloc[idx_24h]) * 100

    ret_ativo_7d = ((p_ativo.iloc[-1] - p_ativo.iloc[idx_7d]) / p_ativo.iloc[idx_7d]) * 100
    ret_bench_7d = ((p_bench.iloc[-1] - p_bench.iloc[idx_7d]) / p_bench.iloc[idx_7d]) * 100

    rs_series = p_ativo / p_bench
    rs_atual = rs_series.iloc[-1]
    rs_ma20 = rs_series.rolling(window=min(20, len(rs_series))).mean().iloc[-1]

    if rs_atual > rs_ma20 and ret_ativo_24h > ret_bench_24h:
        status_rs = " OUTPERFORMING"
    elif rs_atual < rs_ma20 and ret_ativo_24h < ret_bench_24h:
        status_rs = " UNDERPERFORMING"
    else:
        status_rs = " NEUTRAL"

    correlacao = p_ativo.tail(30).pct_change().corr(p_bench.tail(30).pct_change())
    if pd.isna(correlacao):
        correlacao = 0.0

    return {
        "var_ativo_24h": ret_ativo_24h,
        "var_bench_24h": ret_bench_24h,
        "alpha_24h": ret_ativo_24h - ret_bench_24h,
        "alpha_tf": alpha_tf,
        "var_ativo_7d": ret_ativo_7d,
        "var_bench_7d": ret_bench_7d,
        "status_rs": status_rs,
        "correlacao": correlacao
    }


def avaliar_status_e_alertas(row: pd.Series, suporte: float = None, resistencia: float = None, alpha_val: float = None, label_tempo: str = "nas últimas 24h", vol_mc_ratio: float = None) -> list:
    alertas = []
    preco_atual = row.get('close', 0.0)

    if vol_mc_ratio is not None and not pd.isna(vol_mc_ratio):
        if vol_mc_ratio >= 15.0:
            alertas.append(f" ⚡🔄 [ALERTA DE ROTATIVIDADE]: Volume Diário representa {vol_mc_ratio:.1f}% do Market Cap (>15% - Interesse anómalo)")

    vol_ratio = row.get('vol_ratio', 1.0)
    if not pd.isna(vol_ratio) and vol_ratio >= 2.0:
        var_preco = ((row['close'] - row['open']) / row['open']) * 100 if row.get('open', 0) > 0 else 0
        if var_preco >= 3.0:
            alertas.append(f"  [HIGH PUMP ALERT]: Volume {vol_ratio:.1f}x acima da média (+{var_preco:.2f}%)")
        elif var_preco <= -3.0:
            alertas.append(f"  [HIGH DUMP ALERT]: Queda de {var_preco:.2f}% com volume atípico ({vol_ratio:.1f}x)")
        else:
            alertas.append(f"  [PICO DE VOLUME]: Volume {vol_ratio:.1f}x superior à média")

    rsi_val = row.get('rsi_14')
    if rsi_val is not None and not pd.isna(rsi_val):
        if rsi_val >= 70:
            alertas.append(f" [RSI OVERBOUGHT]: Nível em {rsi_val:.1f} (Risco de correção)")
        elif rsi_val <= 30:
            alertas.append(f" [RSI OVERSOLD]: Nível em {rsi_val:.1f} (Potencial zona de fundo)")

    atr_val = row.get('atr_14')
    if atr_val is not None and not pd.isna(atr_val) and preco_atual > 0:
        pct_atr = (atr_val / preco_atual) * 100
        if pct_atr > 4.0:
            alertas.append(f" [ALTA VOLATILIDADE]: ATR de {pct_atr:.2f}%")

    if alpha_val is not None:
        if alpha_val >= 0.5:  
            alertas.append(f" [OUTPERFORMING]: Alfa de +{alpha_val:.2f}% sobre o BTC {label_tempo}")
        elif alpha_val <= -0.5:
            alertas.append(f" [UNDERPERFORMING]: Perda de {abs(alpha_val):.2f}% face ao BTC {label_tempo}")

    return alertas

# ==================== FUNÇÕES DE FILTRAGEM E DADOS DE MERCADO ====================

def is_unwanted_asset(symbol, name, volume=None, market_cap=None):
    sym = str(symbol).lower().strip()
    nm = str(name).lower().strip()
    
    if re.match(r'^pc\\d+', sym):
        return True
        
    exact_blacklisted_symbols = [
        'usd1', 'usd.ai', 'usdai', 'cusd', 'usdt', 'usdc', 'usde', 'dai', 
        'fdusd', 'pyusd', 'tusd', 'usdd', 'frax', 'bsc-usd', 'usda'
    ]
    if sym in exact_blacklisted_symbols or nm in exact_blacklisted_symbols:
        return True

    blacklisted_keywords = [
        'usd1', 'usd.ai', 'usdai', 'cap usd', 'eur', 'reur', 'gbp', 'cad', 'chf', 'jpy', 'aud',
        'tradable', 'receivables', 'financing', 'lender', 'neobank', 'latam', 'pos lender',
        'middle-market', 'settlement', 'rent financing', 'apac diversified', 'legal financing',
        'capital-as-a-service', 'warrants', 'bonds', 'treasury', 't-bill', 'tbill', 'yield',
        'clo', 'securitize', 'anemoy', 'spiko', 'janus', 'invesco', 'ondo', 'midas', 'usyc',
        'fund', 'money market', 'index', 'tokenized', 'gold', 'xau', 'heloc', 'blockchain capital'
    ]
    
    for kw in blacklisted_keywords:
        if kw in sym or kw in nm:
            return True
            
    if volume is not None and volume < 10000:
        return True
            
    return False

@st.cache_data(ttl=300)
def fetch_coingecko_categories():
    url = "https://api.coingecko.com/api/v3/coins/categories/list"
    try:
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return []

@st.cache_data(ttl=300)
def fetch_top_500_coingecko_live(category_id=None):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    data = []
    pages = [1, 2] if not category_id else [1]
    
    for page in pages:
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 250,
            "page": page,
            "sparkline": "true",
            "price_change_percentage": "7d"
        }
        if category_id:
            params["category"] = category_id
            
        try:
            res = requests.get(url, params=params, timeout=12)
            if res.status_code == 200:
                data.extend(res.json())
        except Exception:
            pass
            
    fetch_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    df = pd.DataFrame(data)
    
    if not df.empty:
        if 'price_change_percentage_7d_in_currency' in df.columns:
            df['price_change_percentage_7d'] = df['price_change_percentage_7d_in_currency']
        elif 'price_change_percentage_7d' not in df.columns:
            df['price_change_percentage_7d'] = 0.0

    return df, fetch_time

def get_dynamic_denominators(df_cg):
    default_denoms = {
        "TOTAL3": 650_000_000_000, 
        "OTHERS": 280_000_000_000, 
        "BTCUSD": 90_000,
        "ETHUSD": 3_300,
        "XAUUSD": 2_650
    }
    
    if df_cg.empty:
        return default_denoms
    
    try:
        btc_row = df_cg[df_cg['symbol'].str.lower() == 'btc']
        eth_row = df_cg[df_cg['symbol'].str.lower() == 'eth']
        
        btc_mc = btc_row['market_cap'].values[0] if not btc_row.empty else 0
        eth_mc = eth_row['market_cap'].values[0] if not eth_row.empty else 0
        btc_price = btc_row['current_price'].values[0] if not btc_row.empty else 90000
        eth_price = eth_row['current_price'].values[0] if not eth_row.empty else 3300
        
        total_mc = df_cg['market_cap'].sum()
        total3 = max(1, total_mc - (btc_mc + eth_mc))
        
        top10_mc = df_cg.head(10)['market_cap'].sum()
        others = max(1, total_mc - top10_mc)
        
        return {
            "TOTAL3": total3,
            "OTHERS": others,
            "BTCUSD": btc_price,
            "ETHUSD": eth_price,
            "XAUUSD": 2_650
        }
    except Exception:
        return default_denoms

def calculate_relative_formulas(price, denoms):
    return {
        "vs TOTAL3 (*1B)": (price / denoms["TOTAL3"]) * 1_000_000_000,
        "vs OTHERS (*1B)": (price / denoms["OTHERS"]) * 1_000_000_000,
        "vs BTCUSD": price / denoms["BTCUSD"],
        "vs ETHUSD": price / denoms["ETHUSD"],
        "vs XAUUSD (Ouro)": price / denoms["XAUUSD"]
    }

def calculate_bbw_squeeze(sparkline_prices):
    if not sparkline_prices or len(sparkline_prices) < 20:
        return 0.0
    
    s = pd.Series(sparkline_prices)
    sma = s.rolling(20).mean()
    std = s.rolling(20).std()
    upper = sma + (2 * std)
    lower = sma - (2 * std)
    
    bbw = (upper - lower) / sma
    current_bbw = bbw.iloc[-1]
    min_bbw = bbw.min()
    max_bbw = bbw.max()
    
    if max_bbw == min_bbw or pd.isna(current_bbw):
        return 0.0
    
    compression_score = (1 - ((current_bbw - min_bbw) / (max_bbw - min_bbw))) * 100
    return round(float(np.clip(compression_score, 0, 100)), 2)

def calculate_beta_to_btc(alt_prices, btc_prices):
    if len(alt_prices) < 5 or len(btc_prices) < 5:
        return 1.0
    
    min_len = min(len(alt_prices), len(btc_prices))
    a_ret = pd.Series(alt_prices[-min_len:]).pct_change().dropna()
    b_ret = pd.Series(btc_prices[-min_len:]).pct_change().dropna()
    
    cov = np.cov(a_ret, b_ret)[0][1]
    btc_var = np.var(b_ret)
    
    if btc_var == 0 or np.isnan(cov):
        return 1.0
    
    return round(float(cov / btc_var), 2)

def get_fear_and_greed_index():
    try:
        res = requests.get("https://api.alternative.me/fng/", timeout=5)
        if res.status_code == 200:
            data = res.json()['data'][0]
            return int(data['value']), data['value_classification']
    except Exception:
        pass
    return 55, "Neutral"

def fetch_ohlcv(symbol, timeframe='4h', limit=200):
    """Função universal com Fallback Multi-Exchange (Binance, Bybit, KuCoin, MEXC)."""
    clean_sym = symbol.upper().replace('/USDC', '').replace('/USDT', '').replace('/USD', '').replace('USDC', '').replace('USDT', '').replace('USD', '').replace('/', '').strip()
    
    tf_map = {
        "15m": ("15m", 200),
        "1h": ("1h", 240),
        "4h": ("4h", 200),
        "1d": ("1d", 200),
        "1w": ("1w", 100),
        "1M": ("1M", 60),
        "90d": ("1d", 90),
        "Total": ("1M", 1000)
    }
    ccxt_tf, fetch_limit = tf_map.get(timeframe, ("4h", 200))
    
    quotes = ['USDT', 'USDC', 'USD']
    for ex in exchanges_fallback:
        for q in quotes:
            formatted = f"{clean_sym}/{q}"
            try:
                ohlcv = ex.fetch_ohlcv(formatted, timeframe=ccxt_tf, limit=fetch_limit)
                if ohlcv and len(ohlcv) > 0:
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                    fetch_time = f"{ex.id.upper()} ({formatted})"
                    return df, clean_sym, fetch_time
            except Exception:
                continue
                
    return pd.DataFrame(), clean_sym, "N/A"

# ==================== GERADOR COMPLETO DE RELATÓRIO PDF ====================

def generate_pdf_report(
    coin_symbol, current_price, bbw, beta, vol_mc, metrics_dict, 
    duel_data=None, lang="PT", sma50=None, sma200=None, dist_sma200=None,
    tech_data=None, active_alerts=None
):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor("#1A365D"), spaceAfter=6)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=9, textColor=colors.gray, spaceAfter=12)
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=11, textColor=colors.HexColor("#2B6CB0"), spaceBefore=10, spaceAfter=6)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor("#2D3748"))
    legend_style = ParagraphStyle('Legend', parent=styles['Italic'], fontSize=8, leading=10, textColor=colors.HexColor("#4A5568"))
    alert_style = ParagraphStyle('Alert', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor("#9B2C2C"))

    is_pt = (lang == "PT")
    
    title_text = f"Relatório de Análise Técnica & Macro: {coin_symbol}" if is_pt else f"Technical & Macro Analysis Report: {coin_symbol}"
    gen_time_text = f"Gerado em: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}" if is_pt else f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
    story.append(Paragraph(title_text, title_style))
    story.append(Paragraph(gen_time_text, subtitle_style))
    story.append(Spacer(1, 5))

    risk_label = "Médio"
    risk_color = colors.orange
    if beta > 1.3:
        risk_label, risk_color = ("Alto", colors.red)
    elif beta < 0.8:
        risk_label, risk_color = ("Baixo", colors.green)

    bbw_label = f"{bbw:.2f}% (Moderada)"
    if bbw > 80: bbw_label = f"{bbw:.2f}% (MÁXIMA COMPRESSÃO!)"
    
    vol_mc_label = f"{vol_mc:.2f}%"
    if vol_mc > 15: vol_mc_label = f"{vol_mc:.2f}% (⚡🔄 ROTATIVIDADE >15% )"

    summary_data = [
        ["Preço Atual" if is_pt else "Current Price", "Beta vs BTC", "BBW Squeeze", "Vol/MarketCap Diário", "Risco Geral" if is_pt else "Overall Risk"],
        [f"${current_price:,.4f}", f"{beta:.2f}", bbw_label, vol_mc_label, risk_label]
    ]
    t1 = Table(summary_data, colWidths=[90, 80, 150, 130, 80])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('TEXTCOLOR', (4,1), (4,1), risk_color),
    ]))
    story.append(t1)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Valorização Relativa (5 Fórmulas Macro)" if is_pt else "Relative Valuation (5 Macro Formulas)", heading_style))
    rel_data = [["Denominador Macro", "Rácio Relativo"]]
    for k, v in metrics_dict.items():
        rel_data.append([k, f"{v:,.8f}" if v < 1 else f"{v:,.4f}"])
    
    t2 = Table(rel_data, colWidths=[200, 150])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
    ]))
    story.append(t2)
    story.append(Spacer(1, 10))

    if sma50 is not None and sma200 is not None:
        story.append(Paragraph("Estrutura de Tendência e Osciladores" if is_pt else "Trend Structure & Oscillators", heading_style))
        trend_status = "Bullish" if current_price > sma200 else "Bearish"
        tech_summary = [
            ["Métrica", "Valor", "Diagnóstico"],
            ["SMA 50", f"${sma50:,.4f}", "Acima" if current_price > sma50 else "Abaixo"],
            ["SMA 200", f"${sma200:,.4f}", f"{trend_status} (Distância: {dist_sma200:.2f}%)"]
        ]
        
        if tech_data:
            rsi = tech_data.get('rsi')
            atr = tech_data.get('atr')
            vol_rt = tech_data.get('vol_ratio')
            if rsi is not None:
                tech_summary.append(["RSI (14)", f"{rsi:.1f}", "Sobrecomprado" if rsi > 70 else ("Sobrevendido" if rsi < 30 else "Neutro")])
            if atr is not None:
                tech_summary.append(["ATR", f"${atr:,.4f}", f"{(atr/current_price)*100:.2f}%"])
            if vol_rt is not None:
                tech_summary.append(["Vol Ratio vs MA20", f"{vol_rt:.2f}x", "Anómalo" if vol_rt > 2.0 else "Normal"])

        t_tech = Table(tech_summary, colWidths=[180, 100, 150])
        t_tech.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ]))
        story.append(t_tech)
        story.append(Spacer(1, 10))

    if active_alerts:
        story.append(Paragraph("Alertas e Sinais Ativos" if is_pt else "Active Alerts", heading_style))
        for al in active_alerts:
            story.append(Paragraph(f"• {al}", alert_style))
        story.append(Spacer(1, 10))

    if duel_data:
        asset_a = duel_data.get('asset_a', 'Ativo A')
        asset_b = duel_data.get('asset_b', 'Ativo B')
        story.append(Paragraph(f"Duelo: {asset_a} vs {asset_b}", heading_style))
        duel_summary = [
            ["Período", f"{asset_a}", f"{asset_b}", "Vantagem"],
            ["24h", f"{duel_data.get('var_a_24h', 0):+.2f}%", f"{duel_data.get('var_b_24h', 0):+.2f}%", duel_data.get('winner_24h', '-')],
            ["7 Dias", f"{duel_data.get('var_a_7d', 0):+.2f}%", f"{duel_data.get('var_b_7d', 0):+.2f}%", duel_data.get('winner_7d', '-')]
        ]
        t3 = Table(duel_summary, colWidths=[120, 90, 90, 100])
        t3.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ]))
        story.append(t3)
        story.append(Spacer(1, 10))

    doc.build(story)
    return buffer

# ==================== CARREGAMENTO PRINCIPAL DE DADOS (CACHE) ====================
with st.spinner("A carregar dados do mercado..."):
    df_cg_raw, last_fetch_time = fetch_top_500_coingecko_live()
    categories_list = fetch_coingecko_categories()
    fng_value, fng_class = get_fear_and_greed_index()

if not df_cg_raw.empty:
    df_cg_raw = df_cg_raw[~df_cg_raw.apply(
        lambda r: is_unwanted_asset(r['symbol'], r['name'], r.get('total_volume', 0), r.get('market_cap', 0)), 
        axis=1
    )]
    
    df_cg_raw['bbw_score'] = 0.0
    df_cg_raw['beta_to_btc'] = 1.0
    
    btc_row = df_cg_raw[df_cg_raw['symbol'].str.lower() == 'btc']
    btc_sparkline = btc_row['sparkline_in_7d'].values[0]['price'] if not btc_row.empty and 'sparkline_in_7d' in btc_row and isinstance(btc_row['sparkline_in_7d'].values[0], dict) else []

    for i, row in df_cg_raw.iterrows():
        if isinstance(row.get('sparkline_in_7d'), dict) and 'price' in row['sparkline_in_7d']:
            prices = row['sparkline_in_7d']['price']
            df_cg_raw.at[i, 'bbw_score'] = calculate_bbw_squeeze(prices)
            if btc_sparkline:
                df_cg_raw.at[i, 'beta_to_btc'] = calculate_beta_to_btc(prices, btc_sparkline)

    df_cg = df_cg_raw.copy()
    denominators = get_dynamic_denominators(df_cg)
else:
    df_cg = pd.DataFrame()
    denominators = get_dynamic_denominators(pd.DataFrame())

col_title, col_fng, col_btn = st.columns([6, 2, 2])
with col_title:
    st.title(f"{t['title']}")
    st.caption(f"{t['audit']} | {t['last_update']}: {last_fetch_time}")
with col_fng:
    fng_color = "red" if fng_value <= 40 else "green" if fng_value >= 60 else "orange"
    st.markdown(f"**Fear & Greed:** <span style='color:{fng_color}; font-size:1.1em'>{fng_value} - {fng_class}</span>", unsafe_allow_html=True)
with col_btn:
    if st.button(f"{t['refresh']}"):
        st.cache_data.clear()
        st.rerun()

tab1, tab2, tab3, tab4, tab5 = st.tabs([t['tab1'], t['tab2'], t['tab3'], t['tab4'], t['tab5']])

# =====================================================================
# ABA 1: ATIVO INDIVIDUAL, TIME FRAMES E MATRIZ RELATIVA
# =====================================================================
with tab1:
    st.header(t['tab1_title'])
    with st.expander(f"{t['tab1_expander_title']}", expanded=False):
        st.markdown(t['tab1_expander_body'])

    c_ticker, c_tf, c_log = st.columns([3, 2, 1])
    with c_ticker:
        user_ticker = st.text_input(t['input_ticker'], value="SOL", max_chars=15).upper()
    with c_tf:
        timeframe = st.selectbox(
            t['select_tf'],
            ["15m", "1h", "4h", "1d", "1w", "1M", "90d", "Total"],
            index=3
        )
    with c_log:
        st.write("")
        st.write("")
        log_scale = st.checkbox(t['log_scale'], value=False)
        
    df_single, base_sym, fetch_source = fetch_ohlcv(user_ticker, timeframe=timeframe)
    df_btc_tf, _, _ = fetch_ohlcv("BTCUSD", timeframe=timeframe)
    df_eth_tf, _, _ = fetch_ohlcv("ETHUSD", timeframe=timeframe)
    
    if not df_single.empty:
        df_single = calcular_indicadores_tecnicos(df_single)
        last_row = df_single.iloc[-1]
        last_price = last_row['close']
        
        sma_200 = last_row.get('sma_200', None)
        sma_50 = last_row.get('sma_50', None)
        
        dist_sma_200 = 0.0
        macro_label = "N/A"
        if not pd.isna(sma_200) and sma_200 > 0:
            dist_sma_200 = ((last_price - sma_200) / sma_200) * 100
            macro_label = f"{t['bullish']}" if last_price > sma_200 else f"{t['bearish']}"

        timeframe_labels = {
            '15m': 'nos últimos 15 min',
            '1h': 'na última hora',
            '4h': 'nas últimas 4h',
            '1d': 'nas últimas 24h',
            '1w': 'na última semana',
            '1M': 'no último mês',
            '90d': 'nos últimos 90 dias',
            'Total': 'no período selecionado'
        }
        lbl_tempo = timeframe_labels.get(timeframe, 'no período selecionado')

        cg_single_row = df_cg[df_cg['symbol'].str.lower() == base_sym.lower()] if not df_cg.empty else pd.DataFrame()
        single_vol = cg_single_row['total_volume'].values[0] if not cg_single_row.empty else 0
        single_mc = cg_single_row['market_cap'].values[0] if not cg_single_row.empty else 1
        single_vol_mc_ratio = (single_vol / single_mc) * 100 if single_mc > 0 else 0

        fr_data = calcular_forca_relativa_e_comparacao(df_single, df_btc_tf if not df_btc_tf.empty else df_single)
        alertas_single = avaliar_status_e_alertas(last_row, alpha_val=fr_data.get('alpha_tf', 0.0), label_tempo=lbl_tempo, vol_mc_ratio=single_vol_mc_ratio)
        
        st.markdown(f"**{base_sym} | {t['execution']} {fetch_source}**")
        
        m_cols = st.columns(4)
        m_cols[0].metric(t['curr_price'], smart_format(last_price))
        m_cols[1].metric(t['macro_trend'], macro_label, f"${sma_200:,.4f}" if not pd.isna(sma_200) else "N/A")
        m_cols[2].metric(t['inter_trend'], f"${sma_50:,.4f}" if not pd.isna(sma_50) else "N/A")
        m_cols[3].metric(f"{t['dist_sma200']} (%)", f"{dist_sma_200:+.2f}%")
        
        if alertas_single:
            st.markdown("#### ⚡ Alertas e Status Ativos")
            for al in alertas_single:
                if "OUTPERFORMING" in al or "HIGH PUMP" in al or "ROTATIVIDADE" in al or "OVERSOLD" in al:
                    st.success(al)
                elif "UNDERPERFORMING" in al or "HIGH DUMP" in al or "OVERBOUGHT" in al:
                    st.error(al)
                else:
                    st.info(al)
        
        st.markdown(f"### 📊 {t['rel_val_header']}")
        perspectiva = st.radio("Perspetiva:", ["Curto Prazo (ST - SMA 20)", "Longo Prazo (LT - SMA 200)"], horizontal=True)
        use_st = "Curto" in perspectiva

        if not df_btc_tf.empty and not df_eth_tf.empty:
            df_merged = df_single[['datetime', 'close']].copy()
            df_btc_sub = df_btc_tf[['datetime', 'close']].rename(columns={'close': 'btc_close'})
            df_eth_sub = df_eth_tf[['datetime', 'close']].rename(columns={'close': 'eth_close'})
            df_merged = pd.merge(df_merged, df_btc_sub, on='datetime', how='left')
            df_merged = pd.merge(df_merged, df_eth_sub, on='datetime', how='left')
            df_merged['btc_close'] = df_merged['btc_close'].ffill().bfill()
            df_merged['eth_close'] = df_merged['eth_close'].ffill().bfill()
            
            r_total3 = (df_single['close'] / denominators.get("TOTAL3", 1)) * 1_000_000_000
            r_others = (df_single['close'] / denominators.get("OTHERS", 1)) * 1_000_000_000
            r_btc = df_single['close'] / df_merged['btc_close']
            r_eth = df_single['close'] / df_merged['eth_close']
            r_xau = df_single['close'] / denominators.get("XAUUSD", 2650)
            
            ratios_data = {
                "vs TOTAL3 (*1B)": r_total3,
                "vs OTHERS (*1B)": r_others,
                "vs BTCUSD": r_btc,
                "vs ETHUSD": r_eth,
                "vs XAUUSD": r_xau
            }
            
            ma_window = 20 if use_st else 200
            f_cols = st.columns(5)
            for idx, (label, series) in enumerate(ratios_data.items()):
                val_now = series.iloc[-1]
                sma_series = series.rolling(ma_window, min_periods=1).mean()
                val_sma = sma_series.iloc[-1]
                pct_change = ((val_now - series.iloc[-ma_window]) / series.iloc[-ma_window] * 100) if len(series) >= ma_window and series.iloc[-ma_window] > 0 else 0
                status_icon = "🚀" if val_now > val_sma else "📉"
                f_cols[idx].metric(label=label, value=smart_format(val_now), delta=f"{pct_change:+.2f}% | {status_icon}")
        
        st.markdown(f"### 📈 {t['chart_title']}")
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df_single['datetime'], open=df_single['open'], high=df_single['high'],
            low=df_single['low'], close=df_single['close'], name="Preço"
        ))
        if not df_single['sma_50'].isna().all():
            fig.add_trace(go.Scatter(x=df_single['datetime'], y=df_single['sma_50'], line=dict(color='orange', width=1.5), name="SMA 50"))
        if not df_single['sma_200'].isna().all():
            fig.add_trace(go.Scatter(x=df_single['datetime'], y=df_single['sma_200'], line=dict(color='blue', width=1.5), name="SMA 200"))
        if not df_single['vwap'].isna().all():
            fig.add_trace(go.Scatter(x=df_single['datetime'], y=df_single['vwap'], line=dict(color='purple', width=1, dash='dot'), name="VWAP"))
            
        fig.update_layout(
            height=600, margin=dict(l=0, r=0, t=30, b=0),
            yaxis_type="log" if log_scale else "linear",
            xaxis_rangeslider_visible=False, template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(t['no_data_all'])

# =====================================================================
# ABA 2: DETECTOR DE COMPRESSÃO E NARRATIVAS (IMPLEMENTADO)
# =====================================================================
with tab2:
    st.header(t['tab2_title'])
    with st.expander(f"{t['tab2_expander_title']}", expanded=False):
        st.markdown(t['tab2_expander_body'])
        
    c1, c2 = st.columns([1, 2])
    with c1:
        cat_options = [(None, t['all_cats'])]
        if categories_list:
            for c in categories_list:
                if 'category_id' in c and 'name' in c:
                    cat_options.append((c['category_id'], c['name']))
        
        selected_cat_tuple = st.selectbox(t['select_cat'], cat_options, format_func=lambda x: x[1])
        selected_cat_id = selected_cat_tuple[0]
        
    with c2:
        search_query = st.text_input(t['search_coin'], placeholder="Ex: Solana, deep, btc")
        
    if selected_cat_id is not None:
        with st.spinner("A carregar moedas da narrativa..."):
            df_cat, _ = fetch_top_500_coingecko_live(category_id=selected_cat_id)
            if not df_cat.empty:
                df_cat = df_cat[~df_cat.apply(lambda r: is_unwanted_asset(r['symbol'], r['name'], r.get('total_volume', 0), r.get('market_cap', 0)), axis=1)]
                for i, row in df_cat.iterrows():
                    if isinstance(row.get('sparkline_in_7d'), dict) and 'price' in row['sparkline_in_7d']:
                        df_cat.at[i, 'bbw_score'] = calculate_bbw_squeeze(row['sparkline_in_7d']['price'])
                    else:
                        df_cat.at[i, 'bbw_score'] = 0.0
                df_show = df_cat
            else:
                df_show = pd.DataFrame()
    else:
        df_show = df_cg.copy()
        
    if not df_show.empty:
        if search_query:
            q = search_query.lower()
            df_show = df_show[df_show['symbol'].str.lower().str.contains(q) | df_show['name'].str.lower().str.contains(q)]
            
        df_show['vol_mc_ratio'] = (df_show['total_volume'] / df_show['market_cap']) * 100
        
        # KPIs da Narrativa
        total_ativos = len(df_show)
        extremos_squeeze = len(df_show[df_show['bbw_score'] >= 80])
        turnover_alerts = len(df_show[df_show['vol_mc_ratio'] >= 15])
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Ativos Filtrados na Narrativa", total_ativos)
        kpi2.metric("Squeeze Extremo (BBW ≥ 80%)", extremos_squeeze)
        kpi3.metric("Alertas de Rotatividade (Vol/MC ≥ 15%) ⚡🔄", turnover_alerts)
        st.markdown("---")
        
        display_cols = ['market_cap_rank', 'symbol', 'name', 'current_price', 'price_change_percentage_24h', 'total_volume', 'market_cap', 'bbw_score', 'vol_mc_ratio']
        available_cols = [c for c in display_cols if c in df_show.columns]
        
        df_table = df_show[available_cols].copy()
        df_table.rename(columns={
            'market_cap_rank': 'Rank',
            'symbol': 'Ticker',
            'name': 'Nome',
            'current_price': 'Preço ($)',
            'price_change_percentage_24h': 'Var 24h (%)',
            'total_volume': 'Volume 24h ($)',
            'market_cap': 'Market Cap ($)',
            'bbw_score': 'BBW Compressão (%)',
            'vol_mc_ratio': 'Vol/MC (%) ⚡🔄'
        }, inplace=True)
        
        st.dataframe(
            df_table.style.format({
                'Preço ($)': '{:,.4f}',
                'Var 24h (%)': '{:+.2f}%',
                'Volume 24h ($)': '{:,.0f}',
                'Market Cap ($)': '{:,.0f}',
                'BBW Compressão (%)': '{:.1f}%',
                'Vol/MC (%) ⚡🔄': '{:.1f}%'
            }).background_gradient(subset=['BBW Compressão (%)'], cmap='Reds', vmin=0, vmax=100),
            height=600,
            use_container_width=True
        )
    else:
        st.info("Nenhuma moeda encontrada para os filtros selecionados.")

# =====================================================================
# ABA 3: DUELO
# =====================================================================
with tab3:
    st.header(t['tab3_title'])
    with st.expander(f"{t['tab3_expander_title']}", expanded=False):
        st.markdown(t['tab3_expander_body'])
        
    c_a, c_b, c_tf2 = st.columns(3)
    with c_a:
        asset_a = st.text_input(t['asset_a'], value="SOL").upper()
    with c_b:
        asset_b = st.text_input(t['asset_b'], value="ETH").upper()
    with c_tf2:
        tf_duel = st.selectbox(t['duel_tf'], ["1h", "4h", "1d", "1w"], index=2)
        
    if asset_a and asset_b:
        df_a, clean_a, _ = fetch_ohlcv(asset_a, timeframe=tf_duel)
        df_b, clean_b, _ = fetch_ohlcv(asset_b, timeframe=tf_duel)
        
        if not df_a.empty and not df_b.empty:
            comp = calcular_forca_relativa_e_comparacao(df_a, df_b)
            st.markdown(f"### {t['scorecard']}: {clean_a} vs {clean_b}")
            cc1, cc2, cc3 = st.columns(3)
            cc1.metric(f"Variação 24h ({clean_a})", f"{comp['var_ativo_24h']:+.2f}%")
            cc1.metric(f"Variação 24h ({clean_b})", f"{comp['var_bench_24h']:+.2f}%")
            cc2.metric(f"Variação 7d ({clean_a})", f"{comp['var_ativo_7d']:+.2f}%")
            cc2.metric(f"Variação 7d ({clean_b})", f"{comp['var_bench_7d']:+.2f}%")
            
            w_24 = clean_a if comp['var_ativo_24h'] > comp['var_bench_24h'] else clean_b
            w_7d = clean_a if comp['var_ativo_7d'] > comp['var_bench_7d'] else clean_b
            cc3.info(f"**{t['strongest']} 24h:** {w_24}")
            cc3.info(f"**{t['strongest']} 7d:** {w_7d}")
            
            st.markdown("---")
            corr = comp['correlacao']
            leitura = f" {t['corr_strong']}" if corr > 0.7 else (f" {t['corr_inverse']}" if corr < -0.4 else f" {t['corr_uncorrelated']}")
            st.metric(t['pearson_metric'], f"{corr:.2f}")
            st.markdown(f"**{t['narrative_reading']}:** {leitura}")
            
            min_len = min(len(df_a), len(df_b))
            df_a_sync = df_a.iloc[-min_len:].copy()
            df_b_sync = df_b.iloc[-min_len:].copy()
            df_a_sync['norm'] = (df_a_sync['close'] / df_a_sync['close'].iloc[0]) * 100
            df_b_sync['norm'] = (df_b_sync['close'] / df_b_sync['close'].iloc[0]) * 100
            
            fig_duel = go.Figure()
            fig_duel.add_trace(go.Scatter(x=df_a_sync['datetime'], y=df_a_sync['norm'], mode='lines', name=clean_a))
            fig_duel.add_trace(go.Scatter(x=df_b_sync['datetime'], y=df_b_sync['norm'], mode='lines', name=clean_b))
            fig_duel.update_layout(title=f"Desempenho Normalizado (Base 100) - {tf_duel}", template="plotly_white", height=500)
            st.plotly_chart(fig_duel, use_container_width=True)

# =====================================================================
# ABA 4: HIGHLIGHTS & ROTATIVIDADE
# =====================================================================
with tab4:
    st.header(t['tab4_title'])
    with st.expander(f"{t['tab4_expander_title']}", expanded=False):
        st.markdown(t['tab4_expander_body'])
        
    if not df_cg.empty:
        df_cg['vol_mc_ratio'] = (df_cg['total_volume'] / df_cg['market_cap']) * 100
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"⚡ {t['top10_pump']}")
            df_turnover = df_cg[df_cg['market_cap'] > 50_000_000].sort_values('vol_mc_ratio', ascending=False).head(10)
            st.dataframe(df_turnover[['symbol', 'name', 'vol_mc_ratio', 'price_change_percentage_24h']].style.format({'vol_mc_ratio': '{:.2f}%', 'price_change_percentage_24h': '{:+.2f}%'}).background_gradient(subset=['vol_mc_ratio'], cmap='Oranges'), use_container_width=True, hide_index=True)
            
            st.subheader(f"🎯 {t['top10_bbw']}")
            df_bbw = df_cg.sort_values('bbw_score', ascending=False).head(10)
            st.dataframe(df_bbw[['symbol', 'name', 'bbw_score']].style.format({'bbw_score': '{:.2f}%'}).background_gradient(subset=['bbw_score'], cmap='Reds'), use_container_width=True, hide_index=True)
            
        with col2:
            st.subheader(f"🚀 {t['top10_accum']}")
            df_accum = df_cg.sort_values('price_change_percentage_7d', ascending=False).head(10)
            st.dataframe(df_accum[['symbol', 'name', 'price_change_percentage_7d', 'price_change_percentage_24h']].style.format({'price_change_percentage_7d': '{:+.2f}%', 'price_change_percentage_24h': '{:+.2f}%'}).background_gradient(subset=['price_change_percentage_7d'], cmap='Greens'), use_container_width=True, hide_index=True)
            
            st.subheader(f"📉 {t['top10_dist']}")
            df_dist = df_cg.sort_values('price_change_percentage_7d', ascending=True).head(10)
            st.dataframe(df_dist[['symbol', 'name', 'price_change_percentage_7d', 'price_change_percentage_24h']].style.format({'price_change_percentage_7d': '{:+.2f}%', 'price_change_percentage_24h': '{:+.2f}%'}).background_gradient(subset=['price_change_percentage_7d'], cmap='Reds_r'), use_container_width=True, hide_index=True)

# =====================================================================
# ABA 5: RELATÓRIO & EXPORTAÇÃO
# =====================================================================
with tab5:
    st.header(t['tab5_title'])
    rc1, rc2 = st.columns(2)
    with rc1:
        selected_report_coin = st.text_input(t['select_report_coin'], value="SOL").upper()
    with rc2:
        include_duel = st.checkbox(t['include_duel'], value=True)
        report_duel_asset = st.text_input(t['select_versus'], value="ETH").upper() if include_duel else None
        
    st.info(t['png_info'])
        
    if st.button("Gerar Relatório / Generate Report", type="primary"):
        with st.spinner("A compilar dados completos..."):
            df_report_ohlcv, clean_rep, _ = fetch_ohlcv(selected_report_coin, timeframe="1d", limit=200)
            df_btc_ohlcv, _, _ = fetch_ohlcv("BTCUSD", timeframe="1d", limit=200)
            
            if not df_report_ohlcv.empty:
                df_report_ohlcv = calcular_indicadores_tecnicos(df_report_ohlcv)
                rep_last = df_report_ohlcv.iloc[-1]
                rep_price = rep_last['close']
                
                cg_row = df_cg[df_cg['symbol'].str.lower() == clean_rep.lower()]
                bbw_val = cg_row['bbw_score'].values[0] if not cg_row.empty else 0.0
                beta_val = cg_row['beta_to_btc'].values[0] if not cg_row.empty else 1.0
                vol = cg_row['total_volume'].values[0] if not cg_row.empty else 0
                mc = cg_row['market_cap'].values[0] if not cg_row.empty else 1
                vol_mc = (vol / mc) * 100 if mc > 0 else 0
                
                fr_rep = calcular_forca_relativa_e_comparacao(df_report_ohlcv, df_btc_ohlcv)
                rep_alerts = avaliar_status_e_alertas(rep_last, alpha_val=fr_rep.get('alpha_tf', 0), label_tempo="nas últimas 24h", vol_mc_ratio=vol_mc)
                formulas_rep = calculate_relative_formulas(rep_price, denominators)
                
                duel_data_dict = None
                if include_duel and report_duel_asset:
                    df_duel, _, _ = fetch_ohlcv(report_duel_asset, timeframe="1d", limit=200)
                    if not df_duel.empty:
                        comp_rep = calcular_forca_relativa_e_comparacao(df_report_ohlcv, df_duel)
                        duel_data_dict = {
                            'asset_a': clean_rep, 'asset_b': report_duel_asset,
                            'var_a_24h': comp_rep['var_ativo_24h'], 'var_b_24h': comp_rep['var_bench_24h'],
                            'winner_24h': clean_rep if comp_rep['var_ativo_24h'] > comp_rep['var_bench_24h'] else report_duel_asset,
                            'var_a_7d': comp_rep['var_ativo_7d'], 'var_b_7d': comp_rep['var_bench_7d'],
                            'winner_7d': clean_rep if comp_rep['var_ativo_7d'] > comp_rep['var_bench_7d'] else report_duel_asset,
                            'correlation': comp_rep['correlacao']
                        }
                
                sma_200_val = rep_last.get('sma_200', None)
                sma_50_val = rep_last.get('sma_50', None)
                dist_200_val = ((rep_price - sma_200_val) / sma_200_val * 100) if sma_200_val else 0
                tech_dict = {'rsi': rep_last.get('rsi_14'), 'atr': rep_last.get('atr_14'), 'vol_ratio': rep_last.get('vol_ratio')}
                
                pdf_buffer = generate_pdf_report(
                    coin_symbol=clean_rep, current_price=rep_price, bbw=bbw_val, beta=beta_val,
                    vol_mc=vol_mc, metrics_dict=formulas_rep, duel_data=duel_data_dict, lang=lang,
                    sma50=sma_50_val, sma200=sma_200_val, dist_sma200=dist_200_val,
                    tech_dict=tech_dict, active_alerts=rep_alerts
                )
                
                st.success("Relatório gerado com sucesso!")
                st.download_button(label=f" {t['download_pdf']}", data=pdf_buffer.getvalue(), file_name=f"Relatorio_Macro_{clean_rep}.pdf", mime="application/pdf", type="primary")
                
                st.markdown("---")
                st.subheader(f"{t['consolidated_metrics']} {clean_rep}")
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("Beta vs BTC", f"{beta_val:.2f}")
                mc2.metric("BBW Squeeze", f"{bbw_val:.2f}%")
                mc3.metric("Rácio Vol/MC", f"{vol_mc:.2f}%")
                mc4.metric("RSI (14)", f"{tech_dict['rsi']:.1f}" if not pd.isna(tech_dict['rsi']) else "N/A")
            else:
                st.error("Falha ao obter dados para geração do relatório.")