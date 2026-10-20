
import yfinance as yf
import pandas as pd
import numpy as np
import requests

API_KEY = 'STm6gxQHw0d3C2SLjqlvvaBQ99PJ2WV8'
BASE_PATH = r"C:\Users\liamm\OneDrive\Analytics\Python Projects\QuantTerminal\Comps Engine"

# =========================
# STOCK UNIVERSE / DATABASE 
# ========================= 

def read_stock_universe():
    path = BASE_PATH + r'\stock_universe.xlsx'
    screen_df = pd.read_excel(path)
    screen_df.columns = ['Ticker']
    stock_universe = screen_df['Ticker'].tolist()

    return stock_universe

def get_new_tickers(stock_universe):

    path = BASE_PATH + r'\peer_financials.xlsx'

    peer_financials_excel = pd.read_excel(path)

    existing_tickers = peer_financials_excel['Ticker'].tolist()

    existing_tickers = set(existing_tickers)
    stock_universe = set(stock_universe)

    new_tickers = list(stock_universe - existing_tickers)

    return new_tickers

def get_new_ticker_data(new_tickers):

    universe_data = []
    for ticker in new_tickers:
        Ticker = yf.Ticker(ticker)
        info = Ticker.info
        company_name = info.get('longName')
        share_price = info.get('currentPrice')
        market_cap = info.get('marketCap')

        dct = {
            'Ticker': ticker,
            'companyName': company_name,
            'price': share_price,
            'mktCap': market_cap
        }

        universe_data.append(dct)

    universe_df = pd.DataFrame(universe_data)

    return universe_df

# =========================
# RETRIEVE COMPANY DATA
# =========================  

def input_ticker():
    Ticker = input('Enter Ticker: ')
    Ticker = Ticker.upper().strip()
    return Ticker   

def get_company_data(Ticker):

    company_data = []
    ticker = yf.Ticker(Ticker)
    info = ticker.info
    company_name = info.get('longName')
    share_price = info.get('currentPrice')
    market_cap = info.get('marketCap')
   

    dct = {
        'Ticker': Ticker,
        'companyName': company_name,
        'price': share_price,
        'mktCap': market_cap
    }

    company_data.append(dct)

    company_df = pd.DataFrame(company_data)

    return company_df

# =========================
# PEER IDENTIFICATION
# =========================  

def identify_peers(Ticker):
    url = f'https://financialmodelingprep.com/stable/stock-peers?symbol={Ticker}&apikey={API_KEY}'
    response = requests.get(url)
    if response.status_code != 200 or response.text.strip() == '':
        print(f"Error: Unable to retrieve peers for {Ticker} - status code {response.status_code}")
        return None

    data = response.json()

    df_peers = pd.DataFrame(data)

    df_peers = df_peers.rename(columns={'symbol':'Ticker'})

    return df_peers


def concat_dfs(company_df, df_peers,universe_df):

    df_peers = pd.concat([company_df,df_peers], axis=0)

    df_peers = pd.concat([df_peers,universe_df])
    
    df_peers = df_peers.drop_duplicates(subset=['Ticker'])

    return df_peers


def add_industry_and_sector_to_peers(df_peers):

    industry_data = []

    for ticker in df_peers['Ticker']:

        Ticker = yf.Ticker(ticker)
        info = Ticker.info

        industry = info.get('industry')
        sector = info.get('sector')

        dct = {'Ticker':ticker,'Industry':industry,'Sector':sector}

        industry_data.append(dct)

    industry_data_df = pd.DataFrame(industry_data)

    return industry_data_df


def merging_dataframes(df_peers,industry_data_df):

    df_peers = pd.merge(df_peers,industry_data_df)

    new_column_order = ['Ticker','companyName','Sector','Industry','price','mktCap']

    df_peers = df_peers.reindex(columns=new_column_order)

    return df_peers


def get_peer_financials(df_peers): 

    peer_data = []

    for ticker in df_peers['Ticker']:
        Ticker = yf.Ticker(ticker)
        info = Ticker.info
        total_revenue = info.get('totalRevenue')
        ebitda_ttm = info.get('ebitda')
        net_income_ttm = info.get('netIncomeToCommon')
        enterprise_value = info.get('enterpriseValue')
        rev_growth_qy = info.get('revenueGrowth')
        diluted_shares = info.get('impliedSharesOutstanding')
        total_debt = info.get('totalDebt')
        total_cash = info.get('totalCash')

        dct = {'Ticker': ticker, 
               'Total Revenue': total_revenue, 
               'EBITDA TTM': ebitda_ttm, 
               'Net Income TTM': net_income_ttm, 
               'Enterprise Value': enterprise_value, 
               'Revenue Growth Q/Q': rev_growth_qy,
               'Diluted Shares':diluted_shares,
               'Total Debt': total_debt,
               'Total Cash':total_cash
               }
        
        peer_data.append(dct)

        peer_financials = pd.DataFrame(peer_data)

    
        peer_financials['Net Debt'] = peer_financials['Total Debt'] - peer_financials['Total Cash']

    peer_financials = pd.merge(df_peers,peer_financials,how='inner',on='Ticker')

    return peer_financials


def data_validation(peer_financials):

    revenue_condition =  (peer_financials['Total Revenue'] <= 0) | (peer_financials['Total Revenue'].isna())
    mktcap_condition = (peer_financials['mktCap'] <= 0) | (peer_financials['mktCap'].isna())
    ev_condition = (peer_financials['Enterprise Value'] <= 0) | (peer_financials['Enterprise Value'].isna())
    diluted_shares_condition = (peer_financials['Diluted Shares'] <= 0) | (peer_financials['Diluted Shares'].isna())

    peer_financials.loc[revenue_condition,'Total Revenue'] = np.nan 
    peer_financials.loc[mktcap_condition,'mktCap'] = np.nan 
    peer_financials.loc[ev_condition,'Enterprise Value'] = np.nan
    peer_financials.loc[diluted_shares_condition,'Diluted Shares'] = np.nan

    peer_financials['EBITDA Margin'] = peer_financials['EBITDA TTM'] / peer_financials['Total Revenue']

    return peer_financials


def calculate_peer_multiples(peer_financials):
    peer_financials['EV/Revenue'] = peer_financials['Enterprise Value'] / peer_financials['Total Revenue']
    peer_financials['EV/EBITDA'] = peer_financials['Enterprise Value'] / peer_financials['EBITDA TTM']
    peer_financials['P/E'] = peer_financials['mktCap'] / peer_financials['Net Income TTM']

    return peer_financials

def mulitiple_validation(peer_financials):
    peer_financials['P/E'] = pd.to_numeric(peer_financials['P/E'],errors='coerce')

    ev_revenue_condition = (peer_financials['EV/Revenue'] <= 0) | (~np.isfinite(peer_financials['EV/Revenue']))
    ev_ebitda_condition = (peer_financials['EV/EBITDA'] <= 0) | (~np.isfinite(peer_financials['EV/EBITDA']))
    pe_condition = (peer_financials['P/E'] <= 0) | (~np.isfinite(peer_financials['P/E']))

    peer_financials.loc[ev_revenue_condition,'EV/Revenue'] = np.nan 
    peer_financials.loc[ev_ebitda_condition,'EV/EBITDA'] = np.nan 
    peer_financials.loc[pe_condition,'P/E'] = np.nan 

    return peer_financials



def export_peer_financials(peer_financials):

    path = BASE_PATH + r'\peer_financials.xlsx'

    peer_financials_excel = pd.read_excel(path)

    peer_financials = pd.concat([peer_financials_excel,peer_financials],ignore_index=True)

    peer_financials = peer_financials.drop_duplicates(subset=['Ticker'])

    peer_financials.to_excel(path,index=False)

    return peer_financials

# =========================
# FILTERING UNIVERSE
# =========================  

def filter_sector(peer_financials,Ticker):

    mask = peer_financials['Ticker'] == Ticker

    target_ticker = peer_financials[mask].iloc[0]

    target_industry = target_ticker['Industry']

    mask = peer_financials['Industry'] == target_industry

    filtered_universe = peer_financials[mask]

    return filtered_universe,target_ticker


def filter_peers(filtered_universe,target_ticker):


    target_ticker_ebitda_margin = target_ticker['EBITDA Margin']
    target_ticker_rev_growth = target_ticker['Revenue Growth Q/Q']
    target_ticker_market_cap = target_ticker['mktCap']

    peer_financials = filtered_universe[filtered_universe['Ticker'] != target_ticker['Ticker']].copy()

    peer_financials = peer_financials.dropna(subset=['EBITDA Margin','Revenue Growth Q/Q','mktCap'])

    peer_financials['EBITDA Margin Difference'] = (target_ticker_ebitda_margin - peer_financials['EBITDA Margin']).abs()

    ebitda_margin_conditions = [
        (peer_financials['EBITDA Margin Difference'] <= 0.10),
        (peer_financials['EBITDA Margin Difference'] <= 0.25),
        (peer_financials['EBITDA Margin Difference'] <= 0.50),
        (peer_financials['EBITDA Margin Difference'] <= 0.75),
        (peer_financials['EBITDA Margin Difference'] <= 1.0),
        (peer_financials['EBITDA Margin Difference'] > 1.0)
    ]

    ebitda_margin_points = [40,32,24,16,8,0]
    peer_financials['EBITDA Margin Points'] = np.select(ebitda_margin_conditions, ebitda_margin_points, default=0)

    peer_financials['Revenue Growth Difference'] = (target_ticker_rev_growth - peer_financials['Revenue Growth Q/Q']).abs()

    revenue_growth_conditions = [
        (peer_financials['Revenue Growth Difference'] <= 0.02),
        (peer_financials['Revenue Growth Difference'] <= 0.05),
        (peer_financials['Revenue Growth Difference'] <= 0.10),
        (peer_financials['Revenue Growth Difference'] <= 0.20),
        (peer_financials['Revenue Growth Difference'] <= 0.30)
    ]

    revenue_growth_points = [35,28,21,14,7]
    peer_financials['Revenue Growth Points'] = np.select(revenue_growth_conditions, revenue_growth_points, default=0)


    peer_financials['mktCap Difference'] = ((target_ticker_market_cap - peer_financials['mktCap']) / target_ticker_market_cap).abs()

    mktcap_conditions = [
        (peer_financials['mktCap Difference'] <= 0.25),
        (peer_financials['mktCap Difference'] <= 0.50),
        (peer_financials['mktCap Difference'] <= 1.00),
        (peer_financials['mktCap Difference'] <= 2.00),
        (peer_financials['mktCap Difference'] <= 4.00)
    ]

    mktcap_points = [25,20,15,10,5]
    peer_financials['mktCap Points'] = np.select(mktcap_conditions, mktcap_points, default=0)


    peer_financials['Total Score'] = peer_financials['EBITDA Margin Points'] + peer_financials['Revenue Growth Points'] + peer_financials['mktCap Points'] 

    return peer_financials


def clean_peer_financials(peer_financials):

    peer_financials = peer_financials.sort_values(by='Total Score', ascending=False)

    peer_financials = peer_financials.nlargest(5, "Total Score")

    peer_count = len(peer_financials['Ticker'])

    if peer_count == 0:
        print('Error: No eligible peers found.')
        return None

    elif peer_count <3:
        print(f'Warning: Only {peer_count} eligible peers found. Insufficient for valuation')
        return None

    elif peer_count < 5:
        print(f'Warning: Only {peer_count} eligible peers found. Consider expanding peer universe for more robust valuation.')

    else:
        print(f'{peer_count} eligible peers selected.')


    print(peer_financials)

    return peer_financials

# =========================
# VALUATION SUMMARY
# =========================  

def summarize_valuation_multiples(peer_financials):

    median_ev_revenue = peer_financials['EV/Revenue'].median()
    median_ev_ebitda = peer_financials['EV/EBITDA'].median()
    median_pe = peer_financials['P/E'].median()

    ev_revenue_count = peer_financials['EV/Revenue'].count()
    ev_ebitda_count = peer_financials['EV/EBITDA'].count()
    pe_count = peer_financials['P/E'].count()

    if ev_revenue_count < 3:
        median_ev_revenue = np.nan

    if ev_ebitda_count < 3:
        median_ev_ebitda = np.nan

    if pe_count < 3:
        median_pe = np.nan 

    return median_ev_revenue, median_ev_ebitda, median_pe

def implied_valuation(median_ev_revenue, median_ev_ebitda, median_pe, target_ticker):

    # EV/Revenue Intrinsic Value
    enterprise_value_ev_revenue = median_ev_revenue * target_ticker['Total Revenue']
    equity_value_ev_revenue = enterprise_value_ev_revenue - target_ticker['Net Debt']
    implied_share_price_ev_revenue = equity_value_ev_revenue/target_ticker['Diluted Shares']

    # EV/EBITDA Intrinsic Value
    enterprise_value_ev_ebitda = median_ev_ebitda * target_ticker['EBITDA TTM']
    equity_value_ev_ebitda = enterprise_value_ev_ebitda - target_ticker['Net Debt']
    implied_share_price_ev_ebitda = equity_value_ev_ebitda/target_ticker['Diluted Shares']

    # P/E Intrinsic Value
    equity_value_pe = median_pe * target_ticker['Net Income TTM']
    implied_share_price_pe = equity_value_pe/target_ticker['Diluted Shares']

    return implied_share_price_ev_revenue, implied_share_price_ev_ebitda, implied_share_price_pe

def valuation_summary(target_ticker, median_ev_revenue, median_ev_ebitda, median_pe, implied_share_price_ev_revenue, implied_share_price_ev_ebitda, implied_share_price_pe):

    summary_dct = {'ValuationMethod': ['EV/Revenue','EV/EBITDA','P/E'],
                   'PeerMedian':[median_ev_revenue,median_ev_ebitda,median_pe],
                   'ImpliedSharePrice':[implied_share_price_ev_revenue,implied_share_price_ev_ebitda,implied_share_price_pe]}

    summary_df = pd.DataFrame(summary_dct)

    summary_df['CurrentPrice'] = target_ticker['price']
    summary_df['Upside_Downside'] = (summary_df['ImpliedSharePrice'] / summary_df['CurrentPrice']) - 1
 

    new_structure = ['ValuationMethod','PeerMedian','CurrentPrice','ImpliedSharePrice','Upside_Downside']

    summary_df = summary_df.reindex(columns=new_structure)

    summary_df.loc[len(summary_df)] = ['Average',np.nan,target_ticker['price'],summary_df['ImpliedSharePrice'].mean(),summary_df['Upside_Downside'].mean()]

    return summary_df

# =========================
# OUTPUT LAYER 
# =========================  

def summary_output(summary_df):

    RED = '\033[91m'
    GREEN = '\033[92m'
    RESET = '\033[0m'

    print(
        f'{'Valuation Method':<10} {'Peer Median':>15} {'Current Price':>17} {'Implied Share Price':>23} {'Upsdie/(Downside)':>21}'
    )


    for row in summary_df.itertuples():

        upside_downside = GREEN if row.Upside_Downside > 0 else RED if row.Upside_Downside < 0 else RESET 

        print(
            f'{row.ValuationMethod:<16} {row.PeerMedian:>11.2f} {row.CurrentPrice:>17.2f} {row.ImpliedSharePrice:>18.2f} {upside_downside}{row.Upside_Downside * 100:>23.2f}%{RESET}'
        )   



def execution():

    stock_universe = read_stock_universe()
    new_tickers = get_new_tickers(stock_universe)
    universe_df = get_new_ticker_data(new_tickers)
    Ticker = input_ticker()
    company_df = get_company_data(Ticker)
    df_peers = identify_peers(Ticker)
    df_peers = concat_dfs(company_df, df_peers, universe_df)
    industry_data_df = add_industry_and_sector_to_peers(df_peers)
    df_peers = merging_dataframes(df_peers,industry_data_df)
    peer_financials = get_peer_financials(df_peers)
    peer_financials = data_validation(peer_financials)
    peer_financials = calculate_peer_multiples(peer_financials)
    peer_financials = mulitiple_validation(peer_financials)
    peer_financials = export_peer_financials(peer_financials)

    filtered_universe,target_ticker = filter_sector(peer_financials,Ticker)
    peer_financials = filter_peers(filtered_universe,target_ticker)

    peer_financials = clean_peer_financials(peer_financials)

    if peer_financials is None:
        return 

    median_ev_revenue, median_ev_ebitda, median_pe = summarize_valuation_multiples(peer_financials)
    implied_share_price_ev_revenue, implied_share_price_ev_ebitda, implied_share_price_pe = implied_valuation(median_ev_revenue, median_ev_ebitda, median_pe, target_ticker)
    summary_df = valuation_summary(target_ticker, median_ev_revenue, median_ev_ebitda, median_pe, implied_share_price_ev_revenue, implied_share_price_ev_ebitda, implied_share_price_pe)
    summary_output(summary_df)


execution()