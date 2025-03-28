import pandas as pd
import snowflake.connector
from typing import List, Dict, Any, Optional
import logging
import matplotlib.pyplot as plt
import matplotlib
import io
import base64
import os
import random
from datetime import datetime
import numpy as np
# Set font support
matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'DejaVu Sans', 'Bitstream Vera Sans', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False  # Fix minus sign display issue

from core.config import settings
from core.models import TimeRange, NvidiaValuationMetric

logger = logging.getLogger(__name__)

class SnowflakeService:
    def __init__(self):
        """Initialize Snowflake connection"""
        self.connection = None
        try:
            # Try to connect to Snowflake
            if (settings.SNOWFLAKE_ACCOUNT and 
                settings.SNOWFLAKE_USER and 
                settings.SNOWFLAKE_PASSWORD):
                logger.info("Attempting to connect to Snowflake...")
                
                # Use LANG_ROLE instead of ACCOUNTADMIN
                self.connection = snowflake.connector.connect(
                    account=settings.SNOWFLAKE_ACCOUNT,
                    user=settings.SNOWFLAKE_USER,
                    password=settings.SNOWFLAKE_PASSWORD,
                    database=settings.SNOWFLAKE_DATABASE,
                    schema=settings.SNOWFLAKE_SCHEMA,
                    warehouse=settings.SNOWFLAKE_WAREHOUSE,
                    role="LANG_ROLE"  # Use LANG_ROLE specifically
                )
                logger.info(f"Successfully connected to Snowflake: {settings.SNOWFLAKE_DATABASE}.{settings.SNOWFLAKE_SCHEMA} with LANG_ROLE")
            else:
                logger.warning("Incomplete Snowflake connection info")
        except Exception as e:
            logger.error(f"Error connecting to Snowflake: {e}")
            
    def __del__(self):
        """Close connection when object is destroyed"""
        if hasattr(self, 'connection') and self.connection:
            try:
                self.connection.close()
            except:
                pass
            
    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute SQL query and return results as pandas DataFrame"""
        try:
            if self.connection:
                cur = self.connection.cursor()
                cur.execute(query)
                result = cur.fetch_pandas_all()
                cur.close()
                return result
            else:
                logger.warning("Snowflake not connected, cannot execute query")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error executing Snowflake query: {e}")
            raise
            
    def get_valuation_metrics(self, time_range: TimeRange) -> List[NvidiaValuationMetric]:
        """Get NVIDIA valuation metrics for the specified time range"""
        if not self.connection:
            logger.error("No Snowflake connection available")
            return []
            
        try:
            # List available tables for diagnostic purposes
            tables_query = f"SHOW TABLES IN {settings.SNOWFLAKE_DATABASE}.{settings.SNOWFLAKE_SCHEMA}"
            try:
                tables_df = self.execute_query(tables_query)
                if not tables_df.empty:
                    table_names = tables_df['name'].tolist() if 'name' in tables_df.columns else []
                    logger.info(f"Available tables: {table_names}")
            except Exception as e:
                logger.warning(f"Error listing tables: {e}")
            
            # Query based only on quarter_label
            logger.info(f"Querying Snowflake for NVIDIA valuation metrics from {time_range.start_quarter} to {time_range.end_quarter}")
            
            query = f"""
            SELECT *
            FROM {settings.SNOWFLAKE_DATABASE}.{settings.SNOWFLAKE_SCHEMA}.NVIDIA_VALUATION_METRICS
            WHERE QUARTER_LABEL >= '{time_range.start_quarter}' 
            AND QUARTER_LABEL <= '{time_range.end_quarter}'
            ORDER BY QUARTER_LABEL
            """
            
            df = self.execute_query(query)
            
            if not df.empty:
                logger.info(f"Found {len(df)} rows of NVIDIA valuation metrics in Snowflake")
                
                # Convert DataFrame to list of NvidiaValuationMetric objects
                metrics = []
                for _, row in df.iterrows():
                    # Print column names for debugging
                    if _ == 0:
                        logger.info(f"DataFrame columns: {df.columns.tolist()}")
                    
                    # Extract quarter_label
                    quarter_label = row['QUARTER_LABEL'] if 'QUARTER_LABEL' in row else None
                    
                    if not quarter_label:
                        logger.warning(f"Row missing QUARTER_LABEL, skipping: {row.to_dict()}")
                        continue
                        
                    # Extract year and quarter from quarter_label
                    try:
                        year, quarter = self._parse_quarter_label(str(quarter_label))
                    except Exception as e:
                        logger.error(f"Error parsing quarter label '{quarter_label}': {e}")
                        continue
                    
                    # Helper function to safely get numerical values
                    def safe_get(df_row, column_name, default=0.0):
                        if column_name in df_row and pd.notna(df_row[column_name]):
                            try:
                                return float(df_row[column_name])
                            except:
                                return default
                        return default
                    
                    # Create metric object using the exact column names from the DataFrame
                    metric = NvidiaValuationMetric(
                        year=year,  # Derived from quarter_label
                        quarter=quarter,  # Derived from quarter_label
                        quarter_label=str(quarter_label),
                        market_cap=safe_get(row, 'MARKET_CAP'),
                        enterprise_value=safe_get(row, 'ENTERPRISE_VALUE'),
                        trailing_pe=safe_get(row, 'TRAILING_PE'),
                        forward_pe=safe_get(row, 'FORWARD_PE'),
                        price_to_sales=safe_get(row, 'PRICE_TO_SALES'),
                        price_to_book=safe_get(row, 'PRICE_TO_BOOK'),
                        enterprise_to_revenue=safe_get(row, 'ENTERPRISE_TO_REVENUE'),
                        enterprise_to_ebitda=safe_get(row, 'ENTERPRISE_TO_EBITDA')
                    )
                    metrics.append(metric)
                
                return metrics
            else:
                logger.warning("No data found in Snowflake table")
                return []
                    
        except Exception as e:
            logger.error(f"Error getting valuation metrics from Snowflake: {e}")
            return []

    def generate_metrics_charts(self, time_range: TimeRange) -> Dict[str, str]:
        """Generate charts for NVIDIA valuation metrics"""
        metrics_data = self.get_valuation_metrics(time_range)
        
        if not metrics_data:
            return {}
            
        # Convert to DataFrame for easier plotting
        df = pd.DataFrame([metric.dict() for metric in metrics_data])
        
        charts = {}
        
        try:
            # Chart 1: Market Cap Trend
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(df['quarter_label'], df['market_cap'] / 1e12, marker='o', linewidth=2, color='#76b900')  # NVIDIA green
            ax.set_title('NVIDIA Market Cap Trend (Trillions USD)', fontsize=14)
            ax.set_xlabel('Quarter', fontsize=12)
            ax.set_ylabel('Market Cap (Trillions USD)', fontsize=12)
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # Add data labels
            for i, v in enumerate(df['market_cap'] / 1e12):
                ax.text(i, v + 0.05, f'{v:.2f}', ha='center', fontsize=10)
                
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Convert to base64 string
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100)
            buffer.seek(0)
            charts['market_cap_trend'] = base64.b64encode(buffer.read()).decode('utf-8')
            plt.close()
        except Exception as e:
            logger.error(f"Error generating market cap trend chart: {e}")
        
        try:
            # Chart 2: P/E Ratio Changes
            # Ensure we have valid values (no zeros to divide by)
            valid_pe = df.copy()
            valid_pe = valid_pe[valid_pe['trailing_pe'] > 0]
            valid_pe = valid_pe[valid_pe['forward_pe'] > 0]
            
            if not valid_pe.empty:
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.plot(valid_pe['quarter_label'], valid_pe['trailing_pe'], marker='o', label='Trailing P/E (TTM)', linewidth=2, color='#76b900')
                ax.plot(valid_pe['quarter_label'], valid_pe['forward_pe'], marker='s', label='Forward P/E', linewidth=2, color='#1a9988')
                ax.set_title('NVIDIA P/E Ratio Trends', fontsize=14)
                ax.set_xlabel('Quarter', fontsize=12)
                ax.set_ylabel('P/E Ratio', fontsize=12)
                ax.grid(True, linestyle='--', alpha=0.7)
                ax.legend(loc='best', fontsize=10)
                
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                # Convert to base64 string
                buffer = io.BytesIO()
                plt.savefig(buffer, format='png', dpi=100)
                buffer.seek(0)
                charts['pe_ratios'] = base64.b64encode(buffer.read()).decode('utf-8')
                plt.close()
        except Exception as e:
            logger.error(f"Error generating P/E ratio chart: {e}")
        
        try:
            # Chart 3: Valuation Ratio Comparison
            # Make sure we have valid ratios
            valid_ratios = df.copy()
            
            # Check if sufficient data exists
            if len(valid_ratios) > 0:
                # Remove infinite values and NaNs
                for col in ['price_to_sales', 'price_to_book', 'enterprise_to_revenue', 'enterprise_to_ebitda']:
                    valid_ratios = valid_ratios[~np.isinf(valid_ratios[col])]
                    valid_ratios = valid_ratios[~np.isnan(valid_ratios[col])]
                
                # Skip if we don't have any valid data
                if not valid_ratios.empty:
                    fig, ax = plt.subplots(figsize=(10, 6))
                    
                    # Create bar chart
                    x = range(len(valid_ratios['quarter_label']))
                    width = 0.2
                    
                    # Ensure enterprise_to_ebitda is not too large compared to others
                    # If it is, scale it down for better visualization
                    ev_ebitda_scaled = valid_ratios['enterprise_to_ebitda']
                    scale_factor = 1.0
                    
                    if ev_ebitda_scaled.max() > 100:
                        scale_factor = 10.0
                        ev_ebitda_scaled = ev_ebitda_scaled / scale_factor
                    
                    ax.bar([i - width*1.5 for i in x], valid_ratios['price_to_sales'], width, label='Price/Sales', color='#76b900')
                    ax.bar([i - width/2 for i in x], valid_ratios['price_to_book'], width, label='Price/Book', color='#1a9988')
                    ax.bar([i + width/2 for i in x], valid_ratios['enterprise_to_revenue'], width, label='EV/Revenue', color='#f57c00')
                    
                    # Check if we have valid EBITDA ratios
                    if (valid_ratios['enterprise_to_ebitda'] > 0).any():
                        ax.bar([i + width*1.5 for i in x], ev_ebitda_scaled, width, 
                            label=f'EV/EBITDA {f"(÷{scale_factor})" if scale_factor > 1 else ""}', 
                            color='#c41e3a')
                    
                    ax.set_title('NVIDIA Valuation Ratios Comparison', fontsize=14)
                    ax.set_xlabel('Quarter', fontsize=12)
                    ax.set_ylabel('Ratio', fontsize=12)
                    ax.set_xticks(x)
                    ax.set_xticklabels(valid_ratios['quarter_label'], rotation=45)
                    ax.legend(loc='best', fontsize=10)
                    ax.grid(True, linestyle='--', alpha=0.4, axis='y')
                    
                    plt.tight_layout()
                    
                    # Convert to base64 string
                    buffer = io.BytesIO()
                    plt.savefig(buffer, format='png', dpi=100)
                    buffer.seek(0)
                    charts['valuation_ratios'] = base64.b64encode(buffer.read()).decode('utf-8')
                    plt.close()
        except Exception as e:
            logger.error(f"Error generating valuation ratios chart: {e}")
        
        return charts
    
    def _parse_quarter_label(self, quarter_label: str) -> tuple:
        """Parse quarter label in format YYYYqQ to year and quarter number"""
        parts = quarter_label.lower().split('q')
        return int(parts[0]), int(parts[1])