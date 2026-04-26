import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.callbacks import EarlyStopping
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

# --------------------------------------------------
# 1. Import SMARD time-series dataset
# --------------------------------------------------

df = pd.read_csv(
    "C:/Users/Youssef Sherif/Documents/CSV Files/Realisierter_Stromverbrauch_202603130000_202603240000_Stunde.csv",
    sep=";",
    decimal=","
)

# Clean column names
df.columns = df.columns.str.strip()

# Convert time column
df["Datum von"] = pd.to_datetime(df["Datum von"], dayfirst=True)

# Sort by time
df = df.sort_values("Datum von").reset_index(drop=True)

# --------------------------------------------------
# 2. Select demand column
# --------------------------------------------------

target_column = "Netzlast [MWh] Berechnete Auflösungen"

df[target_column] = (
    df[target_column]
    .astype(str)
    .str.replace(".", "", regex=False)
    .str.replace(",", ".", regex=False)
)

df[target_column] = pd.to_numeric(df[target_column], errors="coerce")

# Drop missing rows
df = df.dropna(subset=[target_column]).reset_index(drop=True)

# Use only one feature first = demand itself
data = df[[target_column]].values

print(df[["Datum von", target_column]].head())
print("Data shape:", data.shape)

# --------------------------------------------------
# 3. Split raw data first
# --------------------------------------------------

train_ratio = 0.8
train_size = int(len(data) * train_ratio)

train_data_raw = data[:train_size]
test_data_raw = data[train_size:]

# --------------------------------------------------
# 4. Scale using TRAIN ONLY
# --------------------------------------------------

x_scaler = MinMaxScaler()
train_data_scaled = x_scaler.fit_transform(train_data_raw)
test_data_scaled = x_scaler.transform(test_data_raw)

y_scaler = MinMaxScaler()
train_target_scaled = y_scaler.fit_transform(train_data_raw[:, [0]])
test_target_scaled = y_scaler.transform(test_data_raw[:, [0]])

# --------------------------------------------------
# 5. Create sequences
# --------------------------------------------------

# Use last 24 hours to predict next hour
time_steps = 24

def create_sequences(feature_data, target_data, time_steps):
    X, y = [], []
    for i in range(len(feature_data) - time_steps):
        X.append(feature_data[i:i + time_steps])
        y.append(target_data[i + time_steps, 0])
    return np.array(X), np.array(y)

X_train, y_train = create_sequences(train_data_scaled, train_target_scaled, time_steps)
X_test, y_test = create_sequences(test_data_scaled, test_target_scaled, time_steps)

print("Before flattening:")
print("X_train shape:", X_train.shape)
print("X_test shape:", X_test.shape)

# --------------------------------------------------
# 6. Flatten sequences for DNN
# --------------------------------------------------

# LSTM uses (samples, time_steps, features)
# DNN needs (samples, time_steps * features)

X_train = X_train.reshape(X_train.shape[0], X_train.shape[1] * X_train.shape[2])
X_test = X_test.reshape(X_test.shape[0], X_test.shape[1] * X_test.shape[2])

print("After flattening for DNN:")
print("X_train shape:", X_train.shape)
print("y_train shape:", y_train.shape)
print("X_test shape:", X_test.shape)
print("y_test shape:", y_test.shape)

input_dim = X_train.shape[1]

# --------------------------------------------------
# 7. Build DNN model
# --------------------------------------------------

model = keras.Sequential([
    layers.Input(shape=(input_dim,)),

    layers.Dense(128, activation="relu"),
    layers.Dropout(0.2),

    layers.Dense(64, activation="relu"),
    layers.Dropout(0.2),

    layers.Dense(32, activation="relu"),
    layers.Dense(1)
])

model.summary()

# --------------------------------------------------
# 8. Compile model
# --------------------------------------------------

model.compile(
    optimizer=keras.optimizers.Adam(learning_rate=0.0005),
    loss="mse",
    metrics=["mae"]
)

# --------------------------------------------------
# 9. Early stopping
# --------------------------------------------------

early_stopping = EarlyStopping(
    monitor="val_loss",
    min_delta=1e-4,
    patience=15,
    restore_best_weights=True,
    verbose=1
)

# --------------------------------------------------
# 10. Train model
# --------------------------------------------------

history = model.fit(
    X_train,
    y_train,
    epochs=100,
    batch_size=32,
    validation_split=0.2,
    shuffle=False,
    callbacks=[early_stopping],
    verbose=1
)

# --------------------------------------------------
# 11. Plot training history
# --------------------------------------------------

history_df = pd.DataFrame(history.history)

plt.figure(figsize=(10, 5))
plt.title("DNN Training Loss History")
plt.plot(history_df["loss"], label="loss")
plt.plot(history_df["val_loss"], label="val_loss")
plt.xlabel("Epoch")
plt.ylabel("MSE Loss")
plt.legend()
plt.grid(True)
plt.show()

plt.figure(figsize=(10, 5))
plt.title("DNN Training MAE History")
plt.plot(history_df["mae"], label="mae")
plt.plot(history_df["val_mae"], label="val_mae")
plt.xlabel("Epoch")
plt.ylabel("MAE")
plt.legend()
plt.grid(True)
plt.show()

# --------------------------------------------------
# 12. Predict on test data
# --------------------------------------------------

predictions_scaled = model.predict(X_test)

print("Predictions shape:", predictions_scaled.shape)

# --------------------------------------------------
# 13. Inverse transform to real demand values
# --------------------------------------------------

y_test_real = y_scaler.inverse_transform(y_test.reshape(-1, 1))
predictions_real = y_scaler.inverse_transform(predictions_scaled)

# --------------------------------------------------
# 14. Plot scaled values
# --------------------------------------------------

plt.figure(figsize=(12, 5))
plt.title("DNN Predicted vs Actual Demand (scaled values)")
plt.plot(y_test, label="Actual scaled")
plt.plot(predictions_scaled, label="Predicted scaled")
plt.xlabel("Time")
plt.ylabel("Scaled Demand")
plt.legend()
plt.grid(True)
plt.show()

# --------------------------------------------------
# 15. Plot real values
# --------------------------------------------------

plt.figure(figsize=(12, 5))
plt.title("DNN Predicted vs Actual Demand (real values)")
plt.plot(y_test_real, label="Actual Demand")
plt.plot(predictions_real, label="Predicted Demand")
plt.xlabel("Time")
plt.ylabel("Demand [MWh]")
plt.legend()
plt.grid(True)
plt.show()