# Authenticate: https://gspread.readthedocs.io/en/latest/oauth2.html
# Edit spreadsheet: https://gspread.readthedocs.io/en/latest/index.html

import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def upload_gsheet(df, key_file, spreadsheet_name, worksheet_name, clear_area = ''):
    gc = gspread.service_account(filename = key_file)
    spreadsheet = gc.open(spreadsheet_name)
    
    if(clear_area != ''): # Clear a predefined range before updating sheet
        spreadsheet.values_clear(worksheet_name + '!' + clear_area)

    worksheet = spreadsheet.worksheet(worksheet_name)
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())

def update_worksheet(df, key_file, spreadsheet_name, worksheet_name, from_cell, to_cell, title = '', header=True):
    gc = gspread.service_account(filename = key_file)
    worksheet = gc.open(spreadsheet_name).worksheet(worksheet_name)
    
    if(title): # Update the range with a title row above the table
        start_row = int(''.join(filter(str.isdigit, from_cell)))
        start_col = ''.join(filter(str.isalpha, from_cell))
        worksheet.update(from_cell, title)
        update_range = start_col + str(start_row + 1) + ':' + to_cell
    else:
        update_range = from_cell + ':' + to_cell

    if(header):
        data = [df.columns.values.tolist()] + df.values.tolist()
    else:
        data = df.values.tolist()

    worksheet.update(update_range, data)

def update_cell(key_file, spreadsheet_name, worksheet_name, cell, cell_value):
    gc = gspread.service_account(filename = key_file)
    worksheet = gc.open(spreadsheet_name).worksheet(worksheet_name)
    worksheet.update(cell, cell_value)

def worksheet_to_df(key_file, spreadsheet_name, worksheet_name):
    try:    
        gc = gspread.service_account(filename = key_file)
        worksheet = gc.open(spreadsheet_name).worksheet(worksheet_name)
        df = pd.DataFrame(worksheet.get_all_records())
    except:
        print('Failed to load worksheet')
        return None
    return df

def clear_worksheet(key_file, spreadsheet_name, worksheet_name):
    gc = gspread.service_account(filename = key_file)
    worksheet = gc.open(spreadsheet_name).worksheet(worksheet_name)
    worksheet.clear()



