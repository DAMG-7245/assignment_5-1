import yfinance as yf
from datetime import datetime
from typing import Dict, Any, Tuple

def parse_quarter_from_date(date_obj: datetime) -> Tuple[int, int, str]:
    """Helper to get year, quarter, and quarter_label from a date."""
    year = date_obj.year
    quarter = (date_obj.month - 1) // 3 + 1
    quarter_label = f"{year}Q{quarter}"
    return year, quarter, quarter_label



def get_nvda_valuation_row(as_of_date: datetime = None) -> Dict[str, Any]:
    """
    Fetch NVIDIA valuation metrics from Yahoo Finance.
    :param as_of_date: Optional. Defaults to today.
    :return: Dictionary ready for Snowflake insertion.
    """
    ticker = yf.Ticker("NVDA")
    info = ticker.info  # Use ticker.get_info() if yfinance version >= 0.2.x

    if as_of_date is None:
        as_of_date = datetime.today()

    year, quarter, quarter_label = parse_quarter_from_date(as_of_date)

    return {
        "year": year,
        "quarter": quarter,
        "quarter_label": quarter_label,
        "date": as_of_date.strftime("%Y-%m-%d"),
        "market_cap": info.get("marketCap", None) / 1e12 if info.get("marketCap") else None,
        "enterprise_value": info.get("enterpriseValue", None) / 1e12 if info.get("enterpriseValue") else None,
        "trailing_pe": info.get("trailingPE", None),
        "forward_pe": info.get("forwardPE", None),
        "peg_ratio": info.get("pegRatio", None),
        "price_to_sales": info.get("priceToSalesTrailing12Months", None),
        "price_to_book": info.get("priceToBook", None),
        "enterprise_to_revenue": info.get("enterpriseToRevenue", None),
        "enterprise_to_ebitda": info.get("enterpriseToEbitda", None)
    }
