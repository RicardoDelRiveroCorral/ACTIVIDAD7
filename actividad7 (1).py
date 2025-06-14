# -*- coding: utf-8 -*-
"""Actividad7

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1m-W-roLWNofWg2zzR8XRIl46Wy678k_A
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.stattools import acf, pacf
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.vector_ar.vecm import coint_johansen
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

# Test de Dickey-Fuller Aumentado
def adf_test(series, title=''):
    print(f'Augmented Dickey-Fuller Test: {title}')
    result = adfuller(series.dropna(), autolag='AIC')
    labels = ['ADF Test Statistic', 'p-value', '# Lags Used', 'Number of Observations Used']
    out = pd.Series(result[0:4], index=labels)
    for key, value in result[4].items():
        out[f'Critical Value ({key})'] = value
    print(out.to_string())
    if result[1] <= 0.05:
        print("→ Serie estacionaria (se rechaza H0)\n")
    else:
        print("→ Serie NO estacionaria (no se rechaza H0)\n")

# Aplicar diferenciación hasta volver estacionaria la serie
def make_stationary(series, max_diff=2):
    d = 0
    temp_series = series.copy()
    while d <= max_diff:
        result = adfuller(temp_series.dropna(), autolag='AIC')
        p_value = result[1]
        if p_value <= 0.05:
            print(f"✔ Serie estacionaria tras {d} diferenciación(es).")
            return temp_series, d
        else:
            temp_series = temp_series.diff()
            d += 1
    print("✘ No se logró estacionar la serie con el número máximo de diferenciaciones.")
    return temp_series, d

# Medias móviles
def moving_average(data, window):
    return data.rolling(window=window).mean()

# Correlograma ACF y PACF
def plot_correlogram(series, lags=40, title=''):
    plt.figure(figsize=(14, 5))
    plt.subplot(121)
    sm.graphics.tsa.plot_acf(series.dropna(), lags=lags, ax=plt.gca(), title=f'ACF - {title}')
    plt.subplot(122)
    sm.graphics.tsa.plot_pacf(series.dropna(), lags=lags, ax=plt.gca(), title=f'PACF - {title}')
    plt.tight_layout()
    plt.show()

# Simulación de caminata aleatoria
def plot_random_walk(stock_data, ticker):
    stock_diff = stock_data.diff().dropna()
    step_std = stock_diff.std()
    np.random.seed(42)
    n_steps = len(stock_data)
    steps = np.random.normal(0, step_std, n_steps)
    random_walk = np.cumsum(steps) + stock_data.iloc[0]
    df = pd.DataFrame({
        'Actual': stock_data,
        'Random Walk': random_walk
    }, index=stock_data.index)
    plt.figure(figsize=(14, 7))
    plt.plot(df['Actual'], label='Actual Adjusted Close Prices', color='black')
    plt.plot(df['Random Walk'], label='Simulated Random Walk', color='red', linestyle='--')
    plt.title(f'{ticker} - Actual Prices vs. Simulated Random Walk')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.show()

# Test de cointegración de Johansen
def cointegration_test(df):
    print("\nJohansen Cointegration Test:")
    try:
        result = coint_johansen(df, det_order=0, k_ar_diff=1)
        print(f"Trace statistic: {result.lr1}")
        print(f"Critical values (90%, 95%, 99%): {result.cvt}")
        for i in range(len(result.lr1)):
            if result.lr1[i] > result.cvt[i, 1]:  # 95%
                print(f"r = {i}: Existe cointegración (95%)")
            else:
                print(f"r = {i}: No hay cointegración (95%)")
        print("\n")
    except Exception as e:
        print(f"Error en el test de Johansen: {e}\n")



# Ajuste ARIMA sobre serie diferenciada y forecast (con reintegración)
def fit_arima(series, ticker, order=(1,1,1), forecast_steps=30):
    try:
        d = order[1]  # Grado de diferenciación
        if d > 0:
            # Diferenciar la serie para volverla estacionaria
            differenced_series = series.diff(d).dropna()
        else:
            differenced_series = series.dropna()

        # Ajustar el modelo sobre la serie diferenciada
        model = ARIMA(differenced_series, order=(order[0], 0, order[2]))  # d=0 porque ya se aplicó manualmente
        results = model.fit()
        print(f'ARIMA Model Summary para {ticker} (diferenciada d={d}):')
        print(results.summary())

        # Forecast en la serie diferenciada
        forecast_diff = results.get_forecast(steps=forecast_steps)
        forecast_mean_diff = forecast_diff.predicted_mean

        # Reintegrar para volver a escala original
        last_value = series.dropna().iloc[-1]
        forecast_values = forecast_mean_diff.cumsum() + last_value

        # Crear índice futuro (business days desde el último día)
        forecast_index = pd.date_range(start=series.index[-1], periods=forecast_steps + 1, freq='B')[1:]
        forecast_series = pd.Series(forecast_values.values, index=forecast_index)

        # Graficar
        plt.figure(figsize=(14, 7))
        plt.plot(series, label='Precio Histórico')
        plt.plot(forecast_series, label='Pronóstico ARIMA (Reintegrado)', color='red')
        plt.title(f'{ticker} - ARIMA Forecast con diferenciación (d={d})')
        plt.xlabel('Fecha')
        plt.ylabel('Precio')
        plt.legend()
        plt.show()

        return results.aic
    except Exception as e:
        print(f"Error fitting ARIMA para {ticker}: {e}")
        return np.inf

# Descargar datos de Yahoo Finance
tickers = ['LLY', 'WELL', 'WFC', 'JPM']
start_date = '2024-09-02'
end_date = '2025-06-09'

data = yf.download(tickers, start=start_date, end=end_date)

# Usar precios ajustados
data = data['Adj Close'] if 'Adj Close' in data.columns else data['Close']

# Diccionario para almacenar AIC de cada modelo
aic_scores = {}

# Análisis por acción
for ticker in tickers:
    print(f'\n\n=== Análisis para {ticker} ===\n')

    stock_data = data[ticker]

    # ADF test original
    adf_test(stock_data, title=f'{ticker} - Serie original')

    # Simulación de caminata aleatoria
    plot_random_walk(stock_data, ticker)

    # Volver estacionaria la serie
    stationary_series, d = make_stationary(stock_data)

    # ADF de serie estacionaria
    adf_test(stationary_series, title=f'{ticker} - Serie diferenciada')

    # Correlograma
    plot_correlogram(stationary_series, title=f'{ticker} - Serie estacionaria (d={d})')

    # Medias móviles
    ma_9 = moving_average(stock_data, 9)
    ma_30 = moving_average(stock_data, 30)

    plt.figure(figsize=(14, 7))
    plt.plot(stock_data, label='Precios Ajustados')
    plt.plot(ma_9, label='Media móvil 9 días')
    plt.plot(ma_30, label='Media móvil 30 días')
    plt.title(f'{ticker} - Precios y Medias Móviles')
    plt.legend()
    plt.show()

    # Ajustar ARIMA
    aic_scores[ticker] = fit_arima(stock_data, ticker, order=(1, d, 1))


# Test de cointegración
coint_df = pd.DataFrame({
    'LLY': data['LLY'],
    'WELL': data['WELL'],
    'WFC': data['WFC'],
    'JPM': data['JPM']
}).dropna()
cointegration_test(coint_df)


# Comparación final
print("\n=== Comparación de inversiones ===")
print("AIC menor = mejor ajuste del modelo ARIMA.\n")
for ticker, aic in aic_scores.items():
    print(f"{ticker} → AIC: {aic:.2f}")
best_stock = min(aic_scores, key=aic_scores.get)
print(f"\n✔ Recomendación basada en ARIMA: {best_stock}")
print("Nota: Si hay cointegración, considera estrategia de 'pairs trading'.")

"""INTERPRETACIONES DE RESULTADOS AL EVALUAR LAS ACCIONES EN EL CÓDIGO:
Interpretación de los resultados de raiz unitaria, correlograma (ACF y PACF) , ADF, cointegration , random walk

# LLY
1. ANÁLISIS DE RAÍZ UNITARIA Y ESTACIONARIEDAD
Serie Original:

ADF Statistic: -2.549830 (p-value: 0.103816)
Resultado: NO estacionaria (no se rechaza H₀) EL P VALUE >0.05
Interpretación: LLY tiene raíz unitaria, confirma proceso estocástico con tendencia, sugiere que los datos de LLY probablemente exhiben un paseo aleatorio con deriva. Esta es una característica común de muchas series de tiempo financieras, donde los precios tienden a moverse

Serie Diferenciada (d=1):
ADF Statistic: -6.914764 (p-value: 1.187×10⁻⁹)
Resultado: Estacionaria (se rechaza H₀)
Interpretación: Una diferenciación es suficiente para lograr estacionariedad, esto hace que se elimine raíz y hacer que las propiedades estadísticas de la serie sean tendencia más constantes en el tiempo.
2. Correologramas:

ACF - La caída rápida y la no significancia de la mayoría de los lags en la ACF confirman la estacionariedad de la serie de LLY (d=1), ya determinado con la prueba ADF. El pico significativo en el lag 1 y luego lacaída a insignificancia en los lags subsiguientes de la ACF es un patrón indicativo de un componente de Media Móvil (MA)
PACF - muestra un patrón de corte claro o decaimiento exponencial para lags más allá del 1, sugiere que un componente autorregresivo (AR) de orden 0 o muy bajo podría ser apropiado.
3. Random walk:

Muestran movimientos erráticos y aparentemente impredecibles en el tiempo. Aunque pueden observarse tendencias generales a mediano plazo (mejor suavizadas por las medias móviles), la dirección precisa de un movimiento futuro individual de precios no puede ser pronosticada con certeza a partir de los movimientos pasados, lo cual es la esencial en mercados eficientes.
4. Arima

Los coeficientes ar.L1, ma.L1 y const no son estadísticamente significativos (sus p-valores son muy altos, cercanos a 1). Esto implica que el modelo ARIMA(1,1,1) con constante no encuentra patrones predictivos significativos en los datos diferenciados de LLY. El pronóstico muestra una leve tendencia descendente para los precios de LLY desde principios de junio hasta finales de julio de 2025. El precio proyectado final es de aproximadamente 740-745, aunque no es estadísticamente fiable, sin embargo convendria no comprar la accion por la tendencia de la gráfica.


# WELL

1. ANÁLISIS DE RAÍZ UNITARIA Y ESTACIONARIEDAD

Raíz Unitaria y Comportamiento Inicial de los Precios:
Los resultados del test de Dickey-Fuller Aumentado (ADF) muestran un p-valor alto (0.842258) y un estadístico de prueba mayor que los valores críticos, lo cual indica que no podemos rechazar la hipótesis nula de presencia de raíz unitaria. Por lo que no es estacionaria y sigue un comportamiento sugiere que la serie original no presenta patrones consistentes en media o varianza a lo largo del tiempo, lo cual limita la capacidad de predecir precios futuros directamente a partir de los precios al presentarse ser muy variables.

Después de la Diferenciación, el test ADF muestra un estadístico altamente negativo (-7.00) y un p-valor prácticamente cero (7.37e-10). Esto nos permite rechazar con confianza la hipótesis nula de raíz unitaria, lo que indica que la serie diferenciada sí es estacionaria. Esto crucial para el modelado estadístico, ya que una serie estacionaria posee una media, varianza y estructura de autocorrelación constantes en el tiempo. Esto significa que los patrones en los cambios de precios son más estables y predecibles, lo que permite aplicar con mayor precisión modelos como ARIMA para realizar pronósticos confiables.

2. Correologramas:

El análisis de la Función de Autocorrelación (ACF) muestra una estructura con memoria corta, donde la mayoría de las correlaciones están cerca de cero. Aunque hay ligeros picos en los lags 20 y 40, que podrían sugerir una estacionalidad débil, el comportamiento general indica que la serie se comporta casi como ruido blanco. Por su parte, la Función de Autocorrelación Parcial (PACF) presenta valores bajos y dispersos, sin cortes abruptos, lo que sugiere una estructura AR débil y confirma que la serie diferenciada es estacionaria.

Con base en estos patrones, se recomienda un modelo ARIMA(0,1,1) o ARIMA(1,1,0), ya que tanto ACF como PACF muestran disminuciones rápidas después del primer rezago.

3. Random walk:

Los precios se mueven de forma errática e impredecible en el corto plazo, sin patrones claros ni reversión a la media. Los shocks en el precio persisten en el tiempo, y aunque se observan tendencias generales (alcistas o bajistas), estas emergen como resultado acumulado de movimientos aleatorios. Las medias móviles suavizan ese ruido, revelando tendencias subyacentes, pero no eliminan la aleatoriedad del precio, lo que refuerza la idea de que predecir el precio futuro solo con base en el pasado es altamente incierto.

4. Arima

Aunque el modelo ARIMA(1,1,1) aplicado a los precios de WELL muestra coeficientes no estadísticamente significativos, el pronóstico generado exhibe una tendencia alcista moderada que, aunque no robusta, podría reflejar una inercia positiva del mercado. A pesar del comportamiento cercano a un random walk, el hecho de que los residuos se comporten como ruido blanco y que la serie muestre una trayectoria creciente en el gráfico sugiere que podría haber una oportunidad de corto plazo. Si se combina este indicio con señales favorables de análisis técnico y perspectivas positivas desde un análisis fundamental, es buena la decisión de compra siempre considerando el riesgo inherente a la volatilidad y la limitada capacidad predictiva del modelo.

# JPM

1. ANÁLISIS DE RAÍZ UNITARIA Y ESTACIONARIEDAD

El p-value (0.553170) es significativamente mayor que cualquier nivel de significancia común (0.01, 0.05, 0.10). Además, el ADF Test Statistic (-1.460057) es mayor que los valores críticos en todos los niveles. Esto nos lleva a no rechazar la hipótesis nula (H0) de la prueba ADF. La H0 en este contexto es que la serie tiene una raíz unitaria. JPM sigue un proceso estocástico con una tendencia o un paseo aleatorio, donde los shocks a los precios tienen un efecto permanente y la media/varianza no son constantes en el tiempo.
Una diferenciación (d=1) ha sido suficiente para lograr la estacionariedad en la serie de JPM. Esto significa que al tomar los cambios (diferencias) entre los precios consecutivos, la serie resultante tiene una media y varianza constantes a lo largo del tiempo, lo cual es fundamental para aplicar modelos de series de tiempo como los modelos ARIMA. El p-value (5.57e-26) es prácticamente cero y significativamente menor que cualquier nivel de significancia. El ADF Test Statistic (-13.91) es mucho más negativo que el Critical Value al 1% (-3.465). Esto nos permite rechazar la hipótesis nula (H0).


2. Correologramas:

El gráfico de ACF a partir del rezago 1, las autocorrelaciones caen bruscamente y se mantienen dentro de las bandas de confianza. Esto indica que no existe una autocorrelación significativa entre los valores actuales y los pasados, lo cual sugiere que no hay un componente MA en la serie. PACF luego cae rápidamente, sin mostrar valores estadísticamente significativos en los rezagos posteriores. Esto significa que no hay una relación directa entre los valores actuales y sus rezagos anteriores, una vez eliminada la influencia de los lags intermedios. Por ello, no se identifica un componente autorregresivo importante, lo que sugiere un valor de  𝑝 = 0 p=0.  Conclusión: Tanto el ACF como el PACF confirman que la serie diferenciada de JPM no presenta patrones autoregresivos ni de media móvil significativos.

3. Random walk:

Los precios ajustados fluctúan de forma errática sin un patrón claro, haciendo difícil predecir el precio futuro basándose solo en movimientos recientes. Los cambios en el precio se incorporan y mantienen en el tiempo, sin volver rápidamente a niveles previos, creando nuevos rangos o niveles.

Aunque los movimientos diarios son aleatorios, la suma de estos pasos puede generar tendencias visibles a medio-largo plazo (ej. tendencia alcista entre septiembre 2024 y marzo 2025, caída en abril y recuperación en mayo-junio).

Las medias móviles suavizan la volatilidad, ayudando a identificar estas tendencias subyacentes. Podemos ver por ejmeplo que cruces entre ellas suelen señalar cambios en la tendencia.


4. Arima

El modelo ARIMA(1,1,1) aplicado a los precios diferenciados de JPM con 190 observaciones muestra coeficientes no estadísticamente significativos (constante 0.2590, p=0.424; AR(1) -0.8913, p=0.676; MA(1) 0.8953, p=0.673), lo que indica que no se capturan patrones lineales claros en la serie. Sin embargo, la varianza de los residuos es 19.39 es significativa, y las pruebas de autocorrelación (Ljung-Box p=0.76) y homocedasticidad (p=0.25) sugieren un modelo estable y sin autocorrelación en errores. El pronóstico del modelo indica una tendencia de subida clara desde junio hasta julio de 2025, con un aumento proyectado en el precio ajustado de aproximadamente 265 a entre 275 y 280. Esta tendencia, aunque basada en coeficientes con significancia limitada, puede interpretarse como una señal positiva derivada de la reintegración y acumulación de movimientos en la serie diferenciada. Además, la ausencia de heterocedasticidad reduce riesgos asociados a volatilidad extrema en los errores del modelo. Por lo tanto, considerando la tendencia proyectada y la estabilidad del modelo, la compra de JPM podría  ser una oportunidad para aprovechar este probable crecimiento de precio en el mediano plazo.

# WFC

1. ANÁLISIS DE RAÍZ UNITARIA Y ESTACIONARIEDAD

La serie original de precios de WFC fue evaluada con la prueba de Dickey-Fuller Aumentada (ADF). El estadístico ADF fue de -1.5987 con un p-valor de 0.4842, que es mucho mayor al nivel de significancia del 0.05. Además, el valor del estadístico es menos negativo que el valor crítico al 5% (-2.8769), por lo que no se rechaza la hipótesis nula de raíz unitaria. Esto indica que la serie original es no estacionaria y se comporta como un random walk, lo que significa que los shocks son permanentes y las propiedades estadísticas como la media y la varianza cambian con el tiempo.

Tras aplicar una diferenciación de orden 1 (d=1), se realizó nuevamente la prueba ADF sobre la serie diferenciada. En este caso, el estadístico fue aproximadamente -13.22 con un p-valor prácticamente cero (1.02e-24), mucho menor que 0.05, y el estadístico es mucho más negativo que el valor crítico. Por lo tanto, se rechaza la hipótesis nula y se concluye que la serie diferenciada es estacionaria. Esto confirma que una diferenciación es suficiente para eliminar la raíz unitaria, un requisito fundamental para aplicar modelos ARIMA.

2. Correologramas:

ACF (Autocorrelación): Se observa un pico significativo en el lag 0, pero las autocorrelaciones para lags posteriores caen rápidamente y no son estadísticamente significativas, ya que todas las barras se encuentran dentro de las bandas de confianza. Esto confirma la estacionariedad y sugiere que no existe un componente de media móvil relevante, indicando un orden q=0.

PACF (Autocorrelación Parcial): Similarmente, hay un pico significativo en el lag 0, con caída rápida y ausencia de autocorrelaciones parciales significativas en lags posteriores, confirmando la estacionariedad y señalando que no hay un componente autorregresivo significativo, lo que implica un orden p=0.

3. Random walk:

Los precios ajustados de WFC muestran un patrón errático, con subidas y bajadas que no siguen una estructura clara. Esto fue confirmado por la prueba de Dickey-Fuller aumentada, donde el estadístico ADF fue de -1.5987 con un p-value de 0.4842, muy por encima del umbral de 0.05. Al no poder rechazar la hipótesis nula, se concluye que la serie presenta una raíz unitaria y es no estacionaria. Esto significa que WFC sigue un random walk, donde los shocks de precio tienen efectos permanentes y los datos pasados no son útiles para predecir los movimientos futuros.

4. Arima

Después de aplicar una diferenciación (d=1), la serie de WFC se volvió estacionaria (ADF = -13.22, p-value ≈ 0), lo que permitió ajustar un modelo ARIMA(1,1,1). Aunque los coeficientes del modelo —constante (0.0996), AR(1) (-0.0617) y MA(1) (0.0943)— no resultaron estadísticamente significativos, el comportamiento de los residuos fue adecuado (ruido blanco, sin heterocedasticidad). Además, el pronóstico muestra una tendencia moderada a la subida, con precios proyectados que suben de $76 a casi $79 entre junio y julio de 2025. Esta proyección, aunque estadísticamente moderada, puede respaldar una decisión de compra táctica.

##Cointegration

El Test de Cointegración de Johansen aplicado a las series muestra que ninguna de las estadísticas de traza (36.40, 18.59, 6.69 y 2.10) supera los valores críticos al 95% (47.85, 29.80, 15.49 y 3.84, respectivamente) para ninguno de los posibles rangos de cointegración (r = 0, 1, 2, 3). Esto indica que no existe una relación de cointegración entre las variables analizadas, es decir, no están vinculadas en el largo plazo. En términos prácticos, cada una sigue su propia trayectoria sin moverse de forma conjunta de manera estable, lo que respalda la hipótesis de que estas series siguen comportamientos independientes y aleatorios (random walks).

"""

import pandas as pd
import yfinance as yf
from statsmodels.tsa.vector_ar.vecm import coint_johansen
import itertools
import warnings
warnings.filterwarnings('ignore')

# Function to perform Johansen cointegration test for a pair
def cointegration_test(df, pair_name=''):
    if df.dropna().empty or len(df.dropna()) < 2:
        print(f"Johansen Cointegration Test for {pair_name}: Insufficient data to perform test")
        return
    print(f"\nJohansen Cointegration Test for {pair_name}:")
    try:
        result = coint_johansen(df, det_order=0, k_ar_diff=1)
        print(f"Trace statistic: {result.lr1}")
        print(f"Critical values (90%, 95%, 99%): {result.cvt}")
        cointegrated = False
        for i in range(len(result.lr1)):
            if result.lr1[i] > result.cvt[i, 1]:  # 95% critical value
                print(f"r = {i}: Cointegration exists at 95% confidence level")
                if i == 0:
                    cointegrated = True
            else:
                print(f"r = {i}: No cointegration at 95% confidence level")
        print(f"\nInterpretation for {pair_name}:")
        if cointegrated:
            print(f"The pair {pair_name} is cointegrated at the 95% confidence level. This suggests a long-term equilibrium relationship, making it suitable for pairs trading strategies, as deviations from the equilibrium are likely to revert.")
        else:
            print(f"The pair {pair_name} is not cointegrated at the 95% confidence level. The stocks likely move independently, and pairs trading may not be effective.")
        print("\n")
    except Exception as e:
        print(f"Error in Johansen test for {pair_name}: {e}\n")

# Function to perform pairwise cointegration tests
def pairwise_cointegration_test(data, tickers):
    print("\n=== Pairwise Cointegration Tests ===")
    pairs = list(itertools.combinations(tickers, 2))
    for ticker1, ticker2 in pairs:
        # Prepare DataFrame for the pair
        coint_df = pd.DataFrame({
            ticker1: data[ticker1],
            ticker2: data[ticker2]
        }).dropna()
        # Run cointegration test for the pair
        pair_name = f"{ticker1}-{ticker2}"
        cointegration_test(coint_df, pair_name)

# Load data from Yahoo Finance with retry logic
tickers = ['LLY', 'WELL', 'WFC', 'JPM']
start_date = '2024-09-02'
end_date = '2025-06-09'

def fetch_data(tickers, start_date, end_date, retries=3):
    for attempt in range(retries):
        try:
            data = yf.download(tickers, start=start_date, end=end_date, timeout=10)
            if data.empty:
                print("No data retrieved. Retrying...")
                continue
            return data
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt + 1 == retries:
                print("Max retries reached. Exiting.")
                return None
    return None

data = fetch_data(tickers, start_date, end_date)
if data is None or data.empty:
    print("Failed to retrieve data. Please check network or try later.")
    exit()

# Use Adjusted Close prices
if 'Adj Close' not in data.columns:
    data = data['Close']
else:
    data = data['Adj Close']

# Perform pairwise cointegration tests
pairwise_cointegration_test(data, tickers)

"""##Conclusión Cointegración

Con base en los resultados de los tests de cointegración de Johansen para los pares LLY-WELL, LLY-WFC, LLY-JPM, WELL-WFC, WELL-JPM y WFC-JPM, ninguno muestra evidencia de cointegración al 95% de confianza. En todos los casos, las estadísticas de traza son inferiores a los valores críticos correspondientes, lo que indica que estas acciones no mantienen una relación estable de largo plazo. Por lo tanto, las acciones analizadas tienden a moverse de forma independiente y no sería recomendable aplicar estrategias de pairs trading, ya que no se sustentan en una relación cointegrada. Es probable que sea necesario un periodo de tiempo mas largo, en el cual sea posible identificar comportamiento de integración entre si.
"""

