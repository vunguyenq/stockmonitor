# curl --location --request POST "https://www.vndirect.com.vn/portal/thong-ke-thi-truong-chung-khoan/lich-su-gia.shtml" --data-urlencode "searchMarketStatisticsView.symbol=VCB" --data-urlencode "strFromDate=30/06/2020" --data-urlencode "strToDate=20/08/2020" > test.html
# TODO
# 1. Incremental reload
# 2. Get stock list from google sheet instead of txt file - DONE
# 3. Draw bollinger: SMA20 +-2 std
# 4. Lookup symbol => company name: https://drive.google.com/file/d/0B7ctwQgYFopHaW5OYUZJZjZYVUE/view

import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
from pandas.tseries.offsets import BDay
import StockPriceLib as sp
from GoogleSheetLib import upload_gsheet, update_worksheet, update_cell, worksheet_to_df, clear_worksheet
import math


KEY_FILE = './stockmonitor-287721-60c43f7a70f3.json'
SPREADSHEET_NAME = 'StockMonitor'
WORKSHEET_STOCK = 'Stocklist'
WORKSHEET_PEAK = 'NearestPeak'
WORKSHEET_CHART_DATA = 'ChartData'
N_LAST_DAYS = 5

# disable chained assignments
pd.options.mode.chained_assignment = None 

if __name__ == "__main__":
    #df_stocks = pd.read_csv("./monitor.csv")
    df_stocks = worksheet_to_df(KEY_FILE, SPREADSHEET_NAME, WORKSHEET_STOCK)
    df_stocks = df_stocks[df_stocks['Stock'].apply(lambda x: len(str(x)) == 3)]
    df_stocks = df_stocks[['Stock','Type','MonitorFrom','Track5Days']]

    df_monitor = pd.DataFrame(columns=['Stock','FromDate','ToDate','MaxDate','MaxPrice','LatestPrice','DiffToMax%'])
    df_latestdays = pd.DataFrame(columns=['Stock', 'Date','ClosingPrice'])

    # Compare latest stock price with nearest peak
    for _, row in df_stocks.iterrows():
        stock = row['Stock']
        fromdate = row['MonitorFrom']
        todate = datetime.date.today().strftime('%d/%m/%Y') 
        print('Loading stock {} from date {} to date {} ...'.format(stock,fromdate,todate))
        #stock = 'VCB'
        #fromdate = '01/07/2020'
        #todate = '21/08/2020' 
        
        df = sp.load_price(stock,fromdate,todate, adjusted = False)
        if(df is None):
            continue
        
        # Find nearest peak
        max_price_row = df.loc[df['price'].idxmax()]
        max_price = max_price_row['price']
        max_price_date = max_price_row['date'].strftime('%d/%m/%Y')

        lastest_row = df.loc[df['date'].idxmax()]
        latest_price = lastest_row['price']
        diff2max = round((latest_price - max_price)/max_price * 100,2)

        df_monitor.loc[len(df_monitor)] = [stock, fromdate, todate, max_price_date, max_price, latest_price, diff2max]

        # Filter price of last 5 days
        df.rename(columns={"date": "Date", "price": "ClosingPrice"}, inplace = True)
        df['Stock'] = stock
        df_latestdays = df_latestdays.append(df.nlargest(N_LAST_DAYS, 'Date'))


    df_monitor =df_monitor.sort_values(by=['DiffToMax%'])
    #print(df_monitor)
    upload_gsheet(df_monitor, KEY_FILE, SPREADSHEET_NAME, WORKSHEET_PEAK, clear_area = 'A:G')

    # Get closing price of last 5 working days for each symbol
    start_row = 1
    clear_worksheet(KEY_FILE, SPREADSHEET_NAME, WORKSHEET_CHART_DATA)
    # Filter stocks that are marked to track 5 days 
    df_stocks_5days = df_stocks[df_stocks['Track5Days'].apply(lambda x: len(str(x)) > 0)]
    for _, row in df_stocks_5days.iterrows():
        stock = row['Stock']
        df = df_latestdays[df_latestdays['Stock'] == stock]
        df = df.sort_values(by=['Date'], ascending = True)
        df['Date'] = df["Date"].dt.strftime("%d/%m")
        print('Updating latest 5 days for {}...'.format(stock))
        from_cell = 'A' + str(start_row)
        to_cell = 'B'+ str(start_row + 6)
        update_worksheet(df[['Date','ClosingPrice']], KEY_FILE, SPREADSHEET_NAME, WORKSHEET_CHART_DATA, from_cell, to_cell, title = stock, header = True)
        
        # Update y scale for charts
        min_cell = 'B' + str(start_row)
        min_y = math.floor(df['ClosingPrice'].min()) - 1
        #update_cell(KEY_FILE, SPREADSHEET_NAME, WORKSHEET_CHART_DATA, min_cell, min_y)
        max_cell = 'C' + str(start_row)
        max_y = math.ceil(df['ClosingPrice'].max()) + 1
        #update_cell(KEY_FILE, SPREADSHEET_NAME, WORKSHEET_CHART_DATA, max_cell, max_y)
        update_worksheet(pd.DataFrame([[min_y,max_y]]), KEY_FILE, SPREADSHEET_NAME, WORKSHEET_CHART_DATA, min_cell, max_cell, header = False)

        start_row += 8
        


    

    
