import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
from pandas.tseries.offsets import BDay

# Get all listed stocks 
def get_listed_stocks():
    #https://trade-hn.vndirect.com.vn/chung-khoan/hose
    stock_exchanges = ['hose','hnx','upcom']
    base_url = 'https://trade-hn.vndirect.com.vn/chung-khoan/' # bang gia lightning

    for exchange in stock_exchanges:
        url = base_url + exchange

        retry_count = 0
        while(True):
            try:
                r = requests.get(url)
            except:
                retry_count += 1
                if(retry_count > 2):
                    print('Failed to load stock exchange {}. Aborted after 3 retries.'.format(exchange.upper()))
                    return None
                continue
            break
    return r


# Get closing price per day in a given query period
def load_price(stockid, fromdate, todate, adjusted = True):
    #pload = {'searchMarketStatisticsView.symbol':'VCB','strFromDate':'19/07/2020','strToDate':'21/08/2020'}
    if(adjusted):
        price_col = 7 # gia dong cua dieu chinh
    else:
        price_col = 5 # gia dong cua chua dieu chinh

    df_price = pd.DataFrame(columns=['date','price'])
    page_index = 0
    while(True):
        page_index += 1
        pload = {'searchMarketStatisticsView.symbol':stockid,'strFromDate':fromdate,'strToDate':todate, 'pagingInfo.indexPage':page_index}
        print('     Loading page {}...'.format(page_index))
        
        retry_count = 0
        while(True):
            try:
                r = requests.post('https://www.vndirect.com.vn/portal/thong-ke-thi-truong-chung-khoan/lich-su-gia.shtml',data = pload)
            except:
                retry_count += 1
                if(retry_count > 2):
                    print('Failed to load stock {}, from date {}, to date {}, page {}. Aborted after 3 retries.'.format(stockid, fromdate, todate, page_index))
                    return None
                continue
            break


        soup = BeautifulSoup(r.text, 'html.parser')
        table = soup.findAll('ul', {'class': 'list_tktt lichsugia'})
        rows = table[0].findAll('li', {'class': ''})

        if(len(rows) == 0):
            break
            
        for row in rows:
            columns = row.findAll('div')
            date = datetime.datetime.strptime(columns[0].getText().strip(),'%Y-%m-%d')
            price = float(columns[price_col].getText().strip()) 
            df_price.loc[len(df_price)] = [date, price]
        
        # Don't load next page if fromdate is captured by the current page
        fromdate_date = datetime.datetime.strptime(fromdate,'%d/%m/%Y') 
        previous_working_date = date - BDay(1) # in case fromdate is a weekend date
        if (date == fromdate_date or previous_working_date < fromdate_date): 
            break

    return df_price.sort_values(by=['date'], ascending=False)


# Get market result of all shares outstanding of a given date
# Query date format: dd/mm/yyyy
# Source: cafef
def get_market_result(query_date, print_log = False):
    exchanges = ['HOSE','HASTC','UPCOM']
    #exchanges = ['UPCOM']
    df = pd.DataFrame(columns=['exchange','sym', 'closing_price', 'ref_price', 'open_price', 'high_price', 'low_price', 'auction_vol', 'auction_val'])

    for ex in exchanges:
        url = 'https://s.cafef.vn/TraCuuLichSu2/1/{}/{}.chn'.format(ex, query_date)
        if(ex == 'HASTC'):
            exchange = 'HNX'
        else:
            exchange = ex
        
        if(print_log):
            print('Loading {}'.format(url))

        # Load URL
        retry_count = 0
        while(True):
            try:
                r = requests.get(url)
            except:
                retry_count += 1
                if(retry_count > 2):
                    print('Failed to load {}. Aborted after 3 retries.'.format(url))
                    return None
                continue
            break

        # Parse table
        soup = BeautifulSoup(r.text, 'html.parser')
        table = soup.findAll('table', {'id': 'table2sort'})
        rows = table[0].findAll('tr')

        for row in rows:
            cols = row.findAll('td')
            
            sym_tag = cols[0].findAll('a')
            if(len(sym_tag)==0):
                continue
            sym = sym_tag[0].getText()
            if (len(sym) != 3): # take only stock symbols (3 chars), ignore options
                continue
            closing_price = float(cols[1].getText()) # Gia dong cua
            #avg_price = float(cols[2].getText()) # Gia binh quan - not applicable for HOSE => skip
            ref_price = float(cols[5].getText()) # Gia tham chieu
            open_price = float(cols[6].getText()) # Gia mo cua
            high_price = float(cols[7].getText()) # Gia cao nhat
            low_price = float(cols[8].getText()) # Gia thap nhat
            auction_vol = int(cols[9].getText().replace(',', '')) # Khoi luong giao dich khop lenh
            auction_val = int(cols[10].getText().replace(',', '')) # Gia tri giao dich khop lenh
            
            df.loc[len(df)] = [exchange, sym, closing_price, ref_price, open_price, high_price, low_price, auction_vol, auction_val]
    return df