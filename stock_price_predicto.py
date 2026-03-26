import pandas as pd
import numpy as np
import matplotlib.pyplot as plt  # Fixed import
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from sklearn.ensemble import RandomForestRegressor # Fixed typo (Regressor not Regresser)
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

# --- CONFIGURATION ---
# REPLACE THESE WITH YOUR ACTUAL KEYS
API_KEY = "PKEQBKP4PK7B6LLWOTO7HS456P"
API_SECRET = "2bfKZC9agU4FHaaHveHwKDcsur7xXsTfAy8zgmWxf2ua"

SYMBOL = "NVDA" # Ticker symbol, not company name
START_DATE = "2022-01-01"
END_DATE = "2024-01-15" # Adjusted to a past date so data exists

# --- DATA FETCHING ---
client = StockHistoricalDataClient(API_KEY, API_SECRET) # Fixed typo (Stocl -> Stock)

request_params = StockBarsRequest( # Fixed typo (StockBar -> StockBars)
    symbol_or_symbols=SYMBOL,
    timeframe=TimeFrame.Day,
    start=START_DATE,
    end=END_DATE
)

print("Fetching data...")
bars = client.get_stock_bars(request_params)
df = bars.df.reset_index()

# Filter for the specific symbol in case multiple were fetched
df = df[df["symbol"] == SYMBOL].copy()

# --- FEATURE ENGINEERING ---
# Fixed typo: per_change -> pct_change
df["return"] = df["close"].pct_change()
df["volatility"] = df["return"].rolling(5).std()
df["ma_5"] = df["return"].rolling(5).mean()
df["ma_10"] = df["return"].rolling(10).mean()
df["ma_20"] = df["return"].rolling(20).mean()

# The target is the close price of the NEXT day
df["target"] = df["close"].shift(-1)

# --- CRITICAL FIX: DROP NANS ---
# Rolling windows create NaNs at the start. shift(-1) creates a NaN at the end.
# Models cannot handle NaNs.
df.dropna(inplace=True)

features = [
    "close",
    "volume",
    "volatility",
    "ma_5",
    "ma_10",
    "ma_20"
]

X = df[features]
y = df["target"]

# --- TRAINING ---
# shuffle=False is CRITICAL for time series. You can't train on tomorrow to predict yesterday.
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, shuffle=False
)

model = RandomForestRegressor(
    n_estimators=300,
    max_depth=10,
    random_state=42
)

print("Training model...")
model.fit(X_train, y_train)

# --- PREDICTION & EVALUATION ---
preds = model.predict(X_test)
mae = mean_absolute_error(y_test, preds)

print(f"Mean Absolute Error: ${mae:.2f}")

# --- PLOTTING ---
plt.figure(figsize=(12, 6))
plt.plot(y_test.values, label="Actual Price")
plt.plot(preds, label="Predicted Price", linestyle="--")
plt.title(f"{SYMBOL} Price Prediction")
plt.xlabel("Time (Days in Test Set)")
plt.ylabel("Price ($)")
plt.legend()
plt.show()

# --- FORECAST ---
# To predict "tomorrow", we need the very last row of data we have.
# Note: In a real scenario, you would fetch fresh data up to "today" to predict "tomorrow".
latest_data = X.iloc[[-1]] 
prediction = model.predict(latest_data)[0]
print(f"Next trading day predicted close for {SYMBOL}: ${prediction:.2f}")