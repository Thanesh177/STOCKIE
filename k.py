import numpy as np
import matplotlib.pyplot as plt
import pandas_datareader as web
import datetime as dt
import yfinance as yf
import pandas as pd
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.initializers import glorot_uniform

# Define the company and time range
company = 'SHOP'
start = dt.datetime(2012, 1, 1)
end = dt.datetime(2020, 1, 1)

# Download historical stock data
data = yf.download(tickers=[company], start=start, end=end)


# Scale the data
scaler = MinMaxScaler(feature_range=(0, 1))
scaled_data = scaler.fit_transform(data['Close'].values.reshape(-1, 1))

# Define the prediction window
prediction_day = 30

# Prepare the training data
x_train = []
y_train = []
 
for x in range(prediction_day, len(scaled_data)):
    x_train.append(scaled_data[x - prediction_day:x, 0])
    y_train.append(scaled_data[x, 0])

x_train, y_train = np.array(x_train), np.array(y_train)
x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1], 1))
model = Sequential()

# Build the LSTM model
model.add(LSTM(units=50, return_sequences=True, input_shape=(x_train.shape[1], 1)))
model.add(Dropout(0.2))
model.add(LSTM(units=50, return_sequences=True))
model.add(Dropout(0.2))
model.add(LSTM(units=50))
model.add(Dropout(0.2))
model.add(Dense(units=1))
model.compile(optimizer='adam', loss='mean_squared_error')

model.fit(x_train, y_train, epochs=25, batch_size=15, verbose=0)

test_start = dt.datetime(2020, 1, 1)
test_end = dt.datetime.now()

test_data = yf.download(tickers=[company], start=test_start, end=test_end)
actual_prices = test_data['Close'].values

total_dataset = pd.concat((data['Close'], test_data['Close']), axis=0)

model_inputs = total_dataset[len(total_dataset) - len(test_data) - prediction_day:].values
model_inputs = model_inputs.reshape(-1, 1)
model_inputs = scaler.transform(model_inputs)

# Prepare the test data
x_test = []
for x in range(prediction_day, len(model_inputs)):
    x_test.append(model_inputs[x - prediction_day:x, 0])

x_test = np.array(x_test)
x_test = np.reshape(x_test, (x_test.shape[0], x_test.shape[1], 1))

# Make predictions
predicted_prices = model.predict(x_test)

# Inverse transform the predicted prices
predicted_prices = scaler.inverse_transform(predicted_prices)

plt.ioff()

plt.plot(actual_prices, color='black')
plt.plot(predicted_prices, color='green')
plt.legend()
plt.show()

real_data = [model_inputs[len(model_inputs) - prediction_day:len(model_inputs), 0]]  # Adjusted indexing
real_data = np.array(real_data)
real_data = np.reshape(real_data, (real_data.shape[0], real_data.shape[1], 1))

prediction = model.predict(real_data)
prediction = scaler.inverse_transform(prediction)
print(prediction)

model = model.save('stoc.h5')