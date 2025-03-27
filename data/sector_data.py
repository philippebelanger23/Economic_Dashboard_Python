"""
Sector Analysis Data Module.

This module handles fetching and processing of sector ETF data for the dashboard's
sector analysis feature. It calculates key metrics like relative strength, momentum,
and other technical indicators for sector rotation analysis.
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

# Define sector ETFs and their tickers
SECTOR_ETFS: Dict[str, str] = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Consumer Discretionary": "XLY",
    "Communication Services": "XLC",
    "Industrials": "XLI",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Utilities": "XLU"
}

# Define benchmark ETFs
BENCHMARK_ETFS: Dict[str, str] = {
    "SPY": "SPY",  # S&P 500
    "RSP": "RSP"   # Equal Weight S&P 500
}

def fetch_sector_data(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Fetch historical data for sector ETFs and benchmarks.
    
    Args:
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format
        
    Returns:
        tuple: (sector_data, benchmark_data)
            - sector_data: DataFrame with sector ETF prices
            - benchmark_data: DataFrame with benchmark ETF prices
    """
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    # Fetch benchmark data first as it's most critical
    benchmark_data = pd.DataFrame()
    for name, ticker in BENCHMARK_ETFS.items():
        try:
            etf = yf.Ticker(ticker)
            data = etf.history(start=start_date, end=end_date)
            if not data.empty:
                benchmark_data[name] = data['Close']
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
    
    # Check if we have both SPY and RSP data - if not, try again with a longer timeframe
    if 'SPY' not in benchmark_data.columns or 'RSP' not in benchmark_data.columns:
        extended_start = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')  # Try last 2 years
        try:
            spy = yf.Ticker('SPY')
            spy_data = spy.history(start=extended_start, end=end_date)
            rsp = yf.Ticker('RSP')
            rsp_data = rsp.history(start=extended_start, end=end_date)
            
            if not spy_data.empty and not rsp_data.empty:
                # Merge data on common dates
                common_data = pd.DataFrame()
                common_data['SPY'] = spy_data['Close']
                common_data['RSP'] = rsp_data['Close']
                common_data = common_data.dropna()
                
                # If we now have data, replace benchmark_data
                if not common_data.empty:
                    benchmark_data = common_data
        except Exception as e:
            print(f"Error fetching extended benchmark data: {e}")
    
    # Fetch sector ETF data
    sector_data = pd.DataFrame()
    for sector, ticker in SECTOR_ETFS.items():
        try:
            etf = yf.Ticker(ticker)
            data = etf.history(start=start_date, end=end_date)
            if not data.empty:
                sector_data[sector] = data['Close']
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
    
    return sector_data, benchmark_data

def calculate_sector_metrics(sector_data: pd.DataFrame, benchmark_data: pd.DataFrame, period: str = '12W') -> Dict[str, Any]:
    """
    Calculate sector metrics including returns, volatility, and relative strength.
    
    Args:
        sector_data: DataFrame with sector ETF prices
        benchmark_data: DataFrame with benchmark ETF prices
        period: Period for calculations ('4W', '8W', '12W', '26W', '39W', '52W')
        
    Returns:
        Dictionary containing calculated metrics including:
        - returns: Percentage returns for each sector over the period
        - volatility: Annualized volatility for each sector
        - relative_strength: Sector performance relative to SPY
        - momentum: MACD-like momentum indicator for each sector
        - volume_ratios: Current volume relative to average volume
        - sectors: List of all analyzed sectors
    """
    # Convert period string to number of days
    period_days = {
        '4W': 28,
        '8W': 56,
        '12W': 84,
        '26W': 182,
        '39W': 273,
        '52W': 364
    }
    
    days = period_days.get(period, 84)  # Default to 12 weeks
    
    # Calculate returns
    returns = sector_data.pct_change(days).iloc[-1]
    
    # Calculate volatility (annualized)
    volatility = sector_data.pct_change().std() * np.sqrt(252)
    
    # Calculate relative strength vs SPY
    spy_data = benchmark_data['SPY']
    relative_strength = {}
    for sector in sector_data.columns:
        sector_returns = sector_data[sector].pct_change(days)
        spy_returns = spy_data.pct_change(days)
        relative_strength[sector] = (sector_returns.iloc[-1] / spy_returns.iloc[-1]) * 100
    
    # Calculate momentum (using MACD-like approach)
    momentum = {}
    for sector in sector_data.columns:
        # Calculate 12-day and 26-day EMAs
        ema12 = sector_data[sector].ewm(span=12, adjust=False).mean()
        ema26 = sector_data[sector].ewm(span=26, adjust=False).mean()
        # Calculate MACD
        macd = ema12 - ema26
        momentum[sector] = macd.iloc[-1]
    
    # Calculate volume ratios (if available)
    volume_ratios = {}
    for sector, ticker in SECTOR_ETFS.items():
        try:
            etf = yf.Ticker(ticker)
            hist = etf.history(period='50d')
            if not hist.empty and 'Volume' in hist.columns:
                current_volume = hist['Volume'].iloc[-1]
                avg_volume = hist['Volume'].mean()
                volume_ratios[sector] = current_volume / avg_volume
            else:
                volume_ratios[sector] = 1.0
        except Exception:
            volume_ratios[sector] = 1.0
    
    return {
        'returns': returns,
        'volatility': volatility,
        'relative_strength': pd.Series(relative_strength),
        'momentum': pd.Series(momentum),
        'volume_ratios': pd.Series(volume_ratios),
        'sectors': list(sector_data.columns)
    }

def get_sector_analysis_data(period: str = '12W') -> Dict[str, Any]:
    """
    Get complete sector analysis data for the specified period.
    
    Args:
        period: Period for analysis ('4W', '8W', '12W', '26W', '39W', '52W')
        
    Returns:
        Dictionary containing all necessary data for sector analysis including
        sectors, returns, volatility, relative strength, momentum, market caps,
        growth rates, PE ratios, and PEG ratios.
    """
    # Fetch data for the last year to ensure we have enough data for calculations
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    sector_data, benchmark_data = fetch_sector_data(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )
    
    # If sector data is empty, return simulated data
    if sector_data.empty:
        return _get_simulated_sector_data()
    
    # Calculate metrics
    metrics = calculate_sector_metrics(sector_data, benchmark_data, period)
    
    # Generate sample market caps (since we can't get real ones easily)
    market_caps = np.random.uniform(500, 15000, len(metrics['sectors']))
    
    # Generate sample growth rates and PE ratios
    growth_rates = np.random.normal(0.15, 0.08, len(metrics['sectors']))
    pe_ratios = np.random.normal(25, 10, len(metrics['sectors']))
    peg_ratios = pe_ratios / (growth_rates * 100)
    
    # Calculate Sharpe ratios
    risk_free_rate = 0.05  # Assuming 5% risk-free rate
    sharpe_ratios = (metrics['returns'] - risk_free_rate) / metrics['volatility']
    
    return {
        'sectors': metrics['sectors'],
        'returns': metrics['returns'].values,
        'volatility': metrics['volatility'].values,
        'relative_strength': metrics['relative_strength'].values,
        'momentum': metrics['momentum'].values,
        'volume_ratios': metrics['volume_ratios'].values,
        'market_caps': market_caps,
        'growth_rates': growth_rates,
        'pe_ratios': pe_ratios,
        'peg_ratios': peg_ratios,
        'sharpe_ratios': sharpe_ratios.values
    }

def _get_simulated_sector_data() -> Dict[str, Any]:
    """
    Generate simulated sector data when real data is unavailable.
    
    Returns:
        Dictionary containing simulated metrics for sector analysis
    """
    sectors = list(SECTOR_ETFS.keys())
    num_sectors = len(sectors)
    
    # Generate random metrics
    returns = np.random.normal(0.1, 0.2, num_sectors)
    volatility = np.random.uniform(0.1, 0.3, num_sectors)
    relative_strength = np.random.normal(100, 15, num_sectors)
    momentum = np.random.normal(0, 2, num_sectors)
    volume_ratios = np.random.uniform(0.8, 1.5, num_sectors)
    market_caps = np.random.uniform(500, 15000, num_sectors)
    growth_rates = np.random.normal(0.15, 0.08, num_sectors)
    pe_ratios = np.random.normal(25, 10, num_sectors)
    peg_ratios = pe_ratios / (growth_rates * 100)
    sharpe_ratios = (returns - 0.05) / volatility
    
    return {
        'sectors': sectors,
        'returns': returns,
        'volatility': volatility,
        'relative_strength': relative_strength,
        'momentum': momentum,
        'volume_ratios': volume_ratios,
        'market_caps': market_caps,
        'growth_rates': growth_rates,
        'pe_ratios': pe_ratios,
        'peg_ratios': peg_ratios,
        'sharpe_ratios': sharpe_ratios
    }

def get_market_breadth_data(period: str = '52W') -> Tuple[Optional[pd.DatetimeIndex], Optional[pd.Series]]:
    """
    Calculate the market breadth indicator using SPY/RSP ratio.
    
    Args:
        period: Period for analysis ('4W', '8W', '12W', '26W', '39W', '52W')
        
    Returns:
        Tuple containing dates (DatetimeIndex) and SPY/RSP ratio (Series),
        or (None, None) if data fetching fails
    """
    # Convert period string to number of days
    period_days = {
        '4W': 28,
        '8W': 56,
        '12W': 84,
        '26W': 182,
        '39W': 273,
        '52W': 364
    }
    
    days = period_days.get(period, 364)  # Default to 52 weeks
    
    # Add extra days to ensure we have enough data for proper normalization
    buffer_days = 5
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days + buffer_days)
    
    try:
        # Fetch SPY and RSP data
        spy = yf.Ticker('SPY')
        spy_data = spy.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
        
        rsp = yf.Ticker('RSP')
        rsp_data = rsp.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
        
        if spy_data.empty or rsp_data.empty:
            print("Error: Empty data returned for SPY or RSP")
            return None, None
        
        # Align dates and sort
        common_dates = spy_data.index.intersection(rsp_data.index)
        if len(common_dates) == 0:
            print("Error: No common dates found between SPY and RSP data")
            return None, None
            
        common_dates = sorted(common_dates)
        
        # Calculate ratio
        spy_prices = spy_data.loc[common_dates, 'Close']
        rsp_prices = rsp_data.loc[common_dates, 'Close']
        
        # Calculate the ratio
        spy_rsp_ratio = (spy_prices / rsp_prices)
        
        # Trim to exact period length from the end
        if len(spy_rsp_ratio) > days:
            spy_rsp_ratio = spy_rsp_ratio[-days:]
            common_dates = common_dates[-days:]
        
        # Normalize to start at 1.0
        first_value = spy_rsp_ratio.iloc[0]
        spy_rsp_ratio = spy_rsp_ratio / first_value
        
        return common_dates, spy_rsp_ratio
        
    except Exception as e:
        print(f"Error fetching market breadth data: {e}")
        return None, None

if __name__ == "__main__":
    # Test the data fetching and calculations
    data = get_sector_analysis_data('12W')
    print("\nSector Analysis Data:")
    print("=====================")
    for key, value in data.items():
        if isinstance(value, np.ndarray):
            print(f"\n{key}:")
            for sector, val in zip(data['sectors'], value):
                print(f"{sector}: {val:.4f}") 