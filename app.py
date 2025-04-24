import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import date ,timedelta
import numpy as np
from scipy.stats import norm
import plotly.graph_objects as go




st.set_page_config(page_title="Kursy Walut NBP", layout="wide")
st.title("📈 Kursy walut NBP Tabela A")
def compute_RSI(prices, n=14):
    # 1. Oblicz zmiany
    delta = prices.diff()

    # 2. Podziel na zyski i straty
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # 3. Pierwsze avg gain/loss – średnie arytmetyczne
    avg_gain = gain.rolling(window=n, min_periods=n).mean().rename('avg_gain')
    avg_loss = loss.rolling(window=n, min_periods=n).mean().rename('avg_loss')

    # 4. Wilder smoothing
    # Pozycje od n+1:
    gain_smooth = avg_gain.copy()
    loss_smooth = avg_loss.copy()
    for i in range(n, len(prices)):
        gain_smooth.iat[i] = (gain_smooth.iat[i-1] * (n-1) + gain.iat[i]) / n
        loss_smooth.iat[i] = (loss_smooth.iat[i-1] * (n-1) + loss.iat[i]) / n

    # 5. Oblicz RS i RSI
    RS = gain_smooth / loss_smooth
    RSI = 100 - (100 / (1 + RS))
    RSI.name = 'RSI'

    return RSI


# Formularz wyboru
yesterday = date.today() - timedelta(days=90)
currency = st.sidebar.selectbox("Wybierz walutę:", ["EUR", "USD", "CHF", "GBP"])
start_date = st.sidebar.date_input("Data początkowa", value=yesterday)
end_date = st.sidebar.date_input("Data końcowa", value=date.today())
n = st.sidebar.number_input("długość okna ruchomego" ,value =10,min_value=2,step=1)
n2 = st.sidebar.number_input("długość okna RSI" ,value =14,min_value=2,step=1)

# Pobieranie danych
if start_date < end_date:
    url = f"http://api.nbp.pl/api/exchangerates/rates/A/{currency}/{start_date}/{end_date}/?format=json"
    try :
        
        response = requests.get(url)


        if response.status_code == 200:
            data = response.json()
            rates = data["rates"]
            df = pd.DataFrame(rates)
            df["effectiveDate"] = pd.to_datetime(df["effectiveDate"])
            df = df.rename(columns={"effectiveDate": "Data", "mid": "Kurs średni"})
            df['Rt_percent'] = (df['Kurs średni'] - df['Kurs średni'].shift(1)) / df['Kurs średni'].shift(1) * 100
            df['volatility'] = df['Rt_percent'].rolling(window=n).std()

            # Wykres
            col1, col2 = st.columns(2)
            with col1:
                fig = px.line(df, x="Data", y="Kurs średni", title=f"Kurs {currency} w okresie")
                st.plotly_chart(fig)

                fig3 = px.bar(df, x="Data", y="Rt_percent", title=f"Dzienne zmiany procentowe w okresie")
                st.plotly_chart(fig3)


                fig5 = px.line(
                    df,
                    y='volatility',
                    labels={'volatility': 'Zmienność [%]', 'index': 'Data'},
                    title=f'{n}-dniowa zmienność (rolling volatility)'
    )

                st.plotly_chart(fig5, use_container_width=True)

            with col2:
                xx = pd.Series(df["Kurs średni"]).rolling(window=n).mean().iloc[n-1:].values
                fig2 = px.line(df, x=range(len(xx)), y=xx, title=f"srednia krocząca {currency} w oknie {n} dni")
                st.plotly_chart(fig2)
                
                mu = df['Rt_percent'].mean()
                sigma = df['Rt_percent'].std()
                x = np.linspace(df['Rt_percent'].min() - 0.5, df['Rt_percent'].max() + 0.5, 100)
                pdf = norm.pdf(x, mu, sigma)
                fig4 = px.histogram(df['Rt_percent'], nbins=30, histnorm='probability density', opacity=0.6,     labels={'Rt': 'Zwrot [%]'},
                title='Histogram dziennych zwrotów EUR/PLN z krzywą normalną')
                fig4.add_trace(
                        go.Scatter(
                    x=x,
                    y=pdf,
                    mode='lines',
                    name='Rozkład normalny',
                    line=dict(width=2)
                        )
                    )
                
                fig4.add_vline(x=mu, line_dash="dash", line_color="red", annotation_text="μ", annotation_position="top left")
                fig4.add_vline(x=mu+sigma, line_dash="dot", line_color="gray", annotation_text="μ+σ", annotation_position="top right")
                fig4.add_vline(x=mu-sigma, line_dash="dot", line_color="gray", annotation_text="μ−σ", annotation_position="bottom right")

                st.plotly_chart(fig4)
                df['RSI'] = compute_RSI(df['Kurs średni'], n=n2)
                fig = px.line(
                df,
                x=df.index,
                y='RSI',
                labels={'x': 'Data', 'RSI': 'RSI'},
                title=f'{n2}-dniowy RSI dla EUR/PLN'
            )

                # 5. Dodaj linie 30 i 70
                fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="70 (overbought)", annotation_position="top left")
                fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="30 (oversold)", annotation_position="bottom left")

                # 6. Wyświetl
                st.plotly_chart(fig, use_container_width=True)

                        
            # Statystyki
            st.subheader("📊 Statystyki:")
            st.write(f"Średni kurs: {df['Kurs średni'].mean():.4f} PLN")
            st.write(f"Max: {df['Kurs średni'].max():.4f} PLN")
            st.write(f"Min: {df['Kurs średni'].min():.4f} PLN")

            # Eksport
            st.download_button("📥 Pobierz dane jako CSV", df.to_csv(index=False), file_name="kursy.csv", mime="text/csv")
        else:
            st.error("❌ Błąd pobierania danych z API NBP.")
    except requests.exceptions.ConnectionError:
        
        st.text("Connection lost, please verify network")
else:
    st.warning("Wybierz poprawny zakres dat.")

