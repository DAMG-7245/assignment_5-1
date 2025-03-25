import yfinance as yf
import pandas as pd

# Define the ticker symbol and date range
ticker = "NVDA"
start_date = '2025-03-19'
end_date = '2025-03-25'

# Fetch stock data using yfinance
stock_data = yf.download(ticker, start=start_date, end=end_date)

# Add the ticker column and reset the index
stock_data['Symbol'] = ticker
stock_data.reset_index(inplace=True)

if isinstance(stock_data.columns, pd.MultiIndex):
    stock_data.columns = stock_data.columns.get_level_values(-2)

transformed_data = stock_data[['Symbol', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']]

transformed_data = transformed_data.rename(columns={'Price': 'Index'})

# Display the updated DataFrame
print(transformed_data)

