# Trading-Bot
Este proyecto funciona utilizando como base a interactive brokers por lo que debemos tener una cuenta creada y en especifico necesitaremos descargar la aplicación de escritorio 'Trader Workstation' que obtendremos mediante el siguiente link:
https://www.interactivebrokers.com/es/trading/download-tws.php

Una vez decargado necesitamos abrir la aplicación y activar la siguiente configuración:

<img width="425" height="315" alt="image" src="https://github.com/user-attachments/assets/184bff44-d015-4e07-979e-0d1b4d56ccc6" />

debemos dar clic a editar, despues en configuración global

<img width="1437" height="801" alt="image" src="https://github.com/user-attachments/assets/62775d50-6e29-4f72-8378-94f23e8956f1" />

luego debemos ir a API --> configuración y finalmente en la parte derecha debemos marcar la opción que dice activar clientes ActiveX y socket y con eso ya podremos conectarnos y realizar operaciones de compra y venta mediante el uso del API oficial del broker.

Lo siguiente que necesitamos es tener instalado python ya que es el lenguaje que utilizare para correr los códigos y librerias.

ahora debemos instalar en la terminal con pip install las siguientes librerias:

-ib_insync
-pytz
-yfinance
-pandas
-talib

las librerias propias que tendremos son las siguientes:

FundamentalFilter: Es el primer filtro del bot. Descarga la lista completa de empresas del S&P 500 desde Wikipedia (más SPY) y descarta las que no cumplen criterios fundamentales usando datos de Yahoo Finance. Revisa volumen promedio, capitalización de mercado, PEG ratio (solo en modo swing), variación de precio reciente y ATR%. Los umbrales cambian según el modo (swing o daytrade). El resultado es una watchlist depurada con solo las empresas que valen la pena vigilar, para no estar analizando las 500 en cada ciclo.

SignalEngine: Toma la watchlist y decide cuándo entrar. Para cada empresa pide velas de 30 minutos a IBKR y calcula indicadores técnicos con TA-Lib (EMA rápida, lenta y macro de 200, RSI, ATR y media de volumen). Si se cumplen todas las condiciones de tendencia alcista —precio sobre la EMA200, EMA rápida sobre la lenta, RSI en rango y volumen por encima de su media— devuelve una señal BUY. Si no, devuelve HOLD. La lógica de SELL (cortos) está escrita pero comentada, lista para activarse cuando quieras operar en corto.

RiskManager: El cerebro de gestión de riesgo. Tiene dos trabajos:
calculate_order(): recibe una señal y calcula cuántas acciones comprar, dónde poner el Stop Loss (1× ATR) y el Take Profit (2× ATR, o sea ratio 1:2). El tamaño de la posición se basa en arriesgar solo 1% del capital por trade en swing (0.5% en daytrade), con un tope del 20% del capital por posición.
should_exit(): en cada ciclo evalúa si hay que cerrar antes una posición abierta por señal técnica (RSI sobrecomprado, cruce bajista de EMAs o precio rompiendo bajo la EMA50). Esto es independiente del SL/TP que ya maneja IBKR.

IBKRBroker: La capa que habla directamente con Interactive Brokers. Aquí vive todo lo que ejecuta órdenes reales:
open_position(): abre la posición con un bracket order (entrada + TP + SL en una sola instrucción; si uno se ejecuta, IBKR cancela el otro automáticamente).
close_position(): cierra a mercado cuando should_exit() lo pide.
cancel_all_orders(): limpia órdenes pendientes de una empresa.
get_open_positions() y get_account_value(): consultan posiciones abiertas y el valor neto de la cuenta.

main: El orquestador que une todo. Conecta con IBKR, corre el filtro fundamental una vez al arrancar y luego entra en un loop infinito que:
Verifica si el mercado está abierto (con las funciones de horario en zona ET). Si está cerrado, calcula cuánto falta para abrir y espera.
Revisa las posiciones abiertas y cierra las que should_exit() marque.
Si hay menos de 3 posiciones abiertas, busca nuevas señales y abre las que aparezcan.
Espera 15 minutos y repite.

Este es el flujo de trabajo:

<img width="2720" height="3640" alt="flujo_bot_trading_ibkr" src="https://github.com/user-attachments/assets/69e2030f-6ac5-4c66-b6e3-9c12bfb0d909" />

Resultados:

Una vez teniendo el setup completo solo debemos correr el código main en una computadora 24/7, sin embargo como trabajo futuro sería comprar una raspberry pi 4 o 5 con 4 u 8 de ram y descargar trader workstation ahí junto con los códigos de python para correr el sistema e incluso existe otro programa más ligero que puede sustituir a trader workstation llamado 'IB Gateway'. Al probar el código con datos de mercado del pasado se obtuvo un rendimiento anual de 8%, pero hay que considerar que en mi filtro fundamental solo utilicé empresas bancarias o de tecnología ya que eran las que daban los mejores resultados con el código actual. También, se encontró que el mejor rendimiento fue usar el modo swing.

nota: ahora mismo el puerto esta colocado para la cuenta demo, si requieres hacer trading real hay que cambiar al número que aparece en api - configuración.
