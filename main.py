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
        fromdate = datetime.datetime.strptime(row['MonitorFrom'], '%d/%m/%Y').strftime('%Y-%m-%d') 
        todate = datetime.date.today().strftime('%Y-%m-%d') 
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
    # Javascript & html content to fill in html report
    javascript_linechart_data = []
    chart_html_p_tags = ''
    i=0
    # Filter stocks that are marked to track 5 days 
    df_stocks_5days = df_stocks[df_stocks['Track5Days'].apply(lambda x: len(str(x)) > 0)]
    chart_fromdate, chart_todate = 0, 0
    for _, row in df_stocks_5days.iterrows():
        stock = row['Stock']
        df = df_latestdays[df_latestdays['Stock'] == stock]
        df = df.sort_values(by=['Date'], ascending = True)
        df['Date_datetime'] = df['Date'] # duplicate Date column before converting to string to keep datetime format
        df['Date'] = df['Date'].dt.strftime("%d/%m") # Convert Date to string
        print('Updating latest 5 days for {}...'.format(stock))
        from_cell = 'A' + str(start_row)
        to_cell = 'B'+ str(start_row + 6)
        update_worksheet(df[['Date','ClosingPrice']], KEY_FILE, SPREADSHEET_NAME, WORKSHEET_CHART_DATA, from_cell, to_cell, title = stock, header = True)
        
        # Update y scale for charts
        min_cell = 'B' + str(start_row)
        min_y = math.floor(df['ClosingPrice'].min()) - 1
        max_cell = 'C' + str(start_row)
        max_y = math.ceil(df['ClosingPrice'].max()) + 1
        update_worksheet(pd.DataFrame([[min_y,max_y]]), KEY_FILE, SPREADSHEET_NAME, WORKSHEET_CHART_DATA, min_cell, max_cell, header = False)

        start_row += 8

        # Generate data for HTML report
        df_chartdata = df[['Date','ClosingPrice']]
        df_chartdata['Date'] = list(range(max(-len(df_chartdata)+1, -N_LAST_DAYS+1),1))
        javascript_linechart_data.append([stock, max_y, min_y, [df_chartdata.columns.values.tolist()] + df_chartdata.values.tolist()])
        chart_html_p_tags += '<p id="linechart{}" style="width: 400px; height: 200px"></p>\n'.format(i)

        if(chart_fromdate == 0): # 1st stock symbol
            chart_fromdate = df['Date_datetime'].min()
            chart_todate = df['Date_datetime'].max()
        else: # 2nd symbol forward
            chart_fromdate = min(chart_fromdate,df['Date_datetime'].min())
            chart_todate = max(chart_todate,df['Date_datetime'].max())

        i+=1
    
    # Create html report from template
    print('Creating HTML report...')
    # 1. Biến động giá trong phiên gần nhất
    #<img border="0" src="http://s.cafef.vn/chartindex/pricechart.ashx?symbol=VNM&type=price&date=01/12/2020&width=350&height=200">
    CURRENT_PRICE_IMG = '<p>{}</p><p><img border="0" src="http://s.cafef.vn/chartindex/pricechart.ashx?symbol={}&type=price&date={}&width=350&height=200"></p>\n'
    today = datetime.date.today() 
    # If today is weekend, take last Friday
    if(today.weekday() > 4):
        offset = today.weekday() - 4
        timedelta = datetime.timedelta(offset)
        today = today - timedelta
    today = today.strftime('%d/%m/%Y')
    chart_current_price_tags = '<p>Phiên giao dịch gần nhất: {}</p>\n'.format(today)
    for stock in df_stocks['Stock']:
        chart_current_price_tags += CURRENT_PRICE_IMG.format(stock,stock,today)

    # 2. Giá cổ phiếu 5 ngày gần nhất
    chart_fromdate = chart_fromdate.strftime('%d/%m/%Y')
    chart_todate = chart_todate.strftime('%d/%m/%Y')
    javascript_linechart_data = str(javascript_linechart_data)

    df_monitor = df_monitor.sort_values(by=['DiffToMax%'])
    df_monitor = df_monitor[['Stock','FromDate','MaxDate','MaxPrice','DiffToMax%']]
    df_monitor.rename(columns={'DiffToMax%': 'Diff%'}, inplace=True)

    # 3. Đỉnh giá gần nhất (nearest peak)
    nearest_peak_table_html = df_monitor.to_html(index=False)

    with open('report_template.html', 'r', encoding="utf8") as file:
        html_report = file.read()
    
    html_report = html_report.replace('|CHART_DATA_PLACEHOLDER|',javascript_linechart_data)\
                            .replace('|CURRENT_PRICE_CHARTS_PLACEHOLDER|',chart_current_price_tags)\
                            .replace('|CHART_P_TAGS_PLACEHOLDER|',chart_html_p_tags)\
                            .replace('|CHART_FROM_TO_DATE_PLACEHOLDER|','{} - {}'.format(chart_fromdate,chart_todate))\
                            .replace('|NEAREST_PEAK_TABLE_PLACEHOLDER|',nearest_peak_table_html)

    with open('stockreport.html', 'w', encoding="utf8") as filetowrite:
        filetowrite.write(html_report)
        


    

    
