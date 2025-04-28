# import streamlit as st
# import pandas as pd
# import plotly.express as px
# import plotly.graph_objects as go
# import PyPDF2
# import json
# import re
# from datetime import datetime
# import openai
# from typing import Dict, List, Optional

# # Initialize OpenAI API key
# openai.api_key = st.secrets["OPENAI_API_KEY_Invoice"]

# # Constants from secrets
# TREE_ABSORPTION_RATE = st.secrets["emissions"]["TREE_ABSORPTION_RATE"]
# CAR_EMISSIONS_PER_KM = st.secrets["emissions"]["CAR_EMISSIONS_PER_KM"]
# HOME_ANNUAL_EMISSIONS = st.secrets["emissions"]["HOME_ANNUAL_EMISSIONS"]

# ELECTRICITY_FACTORS = {
#     int(year): factor 
#     for year, factor in st.secrets["conversion_factors"]["ELECTRICITY_FACTORS"].items()
# }

# GAS_FACTORS = {
#     int(year): factor 
#     for year, factor in st.secrets["conversion_factors"]["GAS_FACTORS"].items()
# }



# # Constants
# MAX_FILES = 5



# class InvoiceProcessor:
#     @staticmethod
#     def redact_sensitive_data(text: str) -> str:
#         """Redact sensitive information from text."""
#         patterns = {
#             'email': r'\b[\w\.-]+@[\w\.-]+\.\w+\b',
#             'uk_phone': r'\b(?:(?:\+44|0)\s?\d{4}\s?\d{6}|\d{3}[-\.\s]?\d{4}[-\.\s]?\d{4})\b',
#             'postcode': r'\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b',
#             'account_number': r'\b\d{8,12}\b',
#             'sort_code': r'\b\d{2}[-\s]?\d{2}[-\s]?\d{2}\b',
#             'address': r'\d+\s+[A-Za-z\s]+(?:Road|Street|Ave|Avenue|Close|Lane|Drive|Rd|St|Ave)\b',
#             'credit_card': r'\b(?:\d[ -]*?){13,16}\b',
#             'national_insurance': r'\b[A-CEGHJ-PR-TW-Z]{1}[A-CEGHJ-NPR-TW-Z]{1}[0-9]{6}[A-DFM]{1}\b',
#             'company_number': r'\b\d{8}\b'
#         }
#         redacted_text = text
#         for key, pattern in patterns.items():
#             redacted_text = re.sub(pattern, f'[{key.upper()}_REDACTED]', redacted_text, flags=re.IGNORECASE)
#         return redacted_text

#     @staticmethod
#     def extract_invoice_data(text: str, energy_type: str) -> Dict:
#         """Extract data using OpenAI API with enhanced error handling."""
#         try:
#             response = openai.ChatCompletion.create(
#                 model="gpt-4",
#                 messages=[
#                     {
#                         "role": "system",
#                         "content": f"""You are a precise invoice data extraction assistant. 
#                         Extract the following from {energy_type} invoices and return ONLY a valid JSON object:
#                         - Total kWh usage (sum of day and night if applicable)
#                         - Billing period dates
#                         - Provider name"""
#                     },
#                     {
#                         "role": "user",
#                         "content": f"""Extract these fields from the invoice and return them in this exact JSON format:
#                         {{
#                             "kwh": <number>,
#                             "billing_period_start": "DD/MM/YYYY",
#                             "billing_period_end": "DD/MM/YYYY",
#                             "provider": "provider_name",
#                             "type": "{energy_type}"
#                         }}

#                         For day/night tariffs, sum the kWh values.
#                         Format all dates as DD/MM/YYYY.
#                         If any field is not found, use null.

#                         Invoice text:
#                         {text}"""
#                     }
#                 ],
#                 temperature=0
#             )
            
#             content = response.choices[0].message.content.strip()
#             st.session_state['last_api_response'] = content
            
#             try:
#                 result = json.loads(content)
#                 required_fields = ['kwh', 'billing_period_start', 'billing_period_end', 'provider', 'type']
#                 for field in required_fields:
#                     if field not in result:
#                         result[field] = energy_type if field == 'type' else None
#                 return result
            
#             except json.JSONDecodeError as e:
#                 st.error(f"Invalid JSON response from OpenAI: {content}")
#                 return {
#                     'kwh': None,
#                     'billing_period_start': None,
#                     'billing_period_end': None,
#                     'provider': None,
#                     'type': energy_type
#                 }
                
#         except Exception as e:
#             st.error(f"Error processing with OpenAI: {str(e)}")
#             return {
#                 'kwh': None,
#                 'billing_period_start': None,
#                 'billing_period_end': None,
#                 'provider': None,
#                 'type': energy_type
#             }

#     @staticmethod
#     def process_pdf(uploaded_file, energy_type: str) -> Optional[Dict]:
#         """Process PDF, redact sensitive information, and extract data."""
#         try:
#             pdf_reader = PyPDF2.PdfReader(uploaded_file)
#             text = " ".join(page.extract_text() for page in pdf_reader.pages)
#             redacted_text = InvoiceProcessor.redact_sensitive_data(text)
            
#             if st.session_state.get('debug_mode', False):
#                 st.text_area("Redacted Text", redacted_text, height=200)
            
#             result = InvoiceProcessor.extract_invoice_data(redacted_text, energy_type)
#             if result:
#                 result['filename'] = uploaded_file.name
#             return result
            
#         except Exception as e:
#             st.error(f"Error processing {uploaded_file.name}: {str(e)}")
#             return None

# class CarbonCalculator:
#     @staticmethod
#     def get_factor(year: int, energy_type: str) -> float:
#         """Get DEFRA conversion factor for the given year and energy type."""
#         return ELECTRICITY_FACTORS.get(year) if energy_type == 'electricity' else GAS_FACTORS.get(year)

#     @staticmethod
#     def calculate_metrics(df: pd.DataFrame) -> Dict:
#         """Calculate carbon emissions and related metrics for gas and electricity."""
#         df['year'] = pd.to_datetime(df['billing_period_start']).dt.year
#         df['carbon_factor'] = df.apply(lambda x: CarbonCalculator.get_factor(x['year'], x['type']), axis=1)
#         df['emissions_kg'] = df['kwh'] * df['carbon_factor']
#         df['emissions_tonnes'] = df['emissions_kg'] / 1000

#         # Calculate year-over-year changes
#         df['year_month'] = pd.to_datetime(df['billing_period_start']).dt.to_period('M')
#         yoy_changes = df.groupby(['type', df['billing_period_start'].dt.year]).agg({
#             'kwh': ['sum', 'mean'],
#             'emissions_tonnes': ['sum', 'mean']
#         }).pct_change()

#         # Scope emissions calculations
#         scope1_emissions = df[df['type'] == 'gas']['emissions_tonnes'].sum()
#         scope2_emissions = df[df['type'] == 'electricity']['emissions_tonnes'].sum()
#         total_emissions_tonnes = scope1_emissions + scope2_emissions

#         return {
#             'total_emissions_tonnes': total_emissions_tonnes,
#             'scope1_emissions_tonnes': scope1_emissions,
#             'scope2_emissions_tonnes': scope2_emissions,
#             'yoy_changes': yoy_changes
#         }

#     @staticmethod
#     def set_reduction_targets(baseline_emissions: float) -> Dict:
#         """Set science-based reduction targets."""
#         yearly_reduction = 0.045  # 4.5% annual reduction (Science Based Targets initiative)
#         target_years = range(1, 6)  # 5-year projection
        
#         return {
#             year: baseline_emissions * (1 - yearly_reduction) ** year
#             for year in target_years
#         }

# class Dashboard:
#     def __init__(self):
#         self.chart_type = st.sidebar.selectbox(
#             "Select Chart Type",
#             ["Line Chart", "Bar Chart", "Area Chart"]
#         )
#         self.color_scheme = {
#             'electricity': '#1f77b4',
#             'gas': '#ff7f0e'
#         }

#     def create_usage_chart(self, df: pd.DataFrame):
#         """Generate energy usage trend chart."""
#         fig = go.Figure()
        
#         for energy_type in df['type'].unique():
#             type_df = df[df['type'] == energy_type]
            
#             # Main usage line
#             fig.add_trace(go.Scatter(
#                 x=type_df['billing_period_start'],
#                 y=type_df['kwh'],
#                 name=f"{energy_type.capitalize()} Usage",
#                 mode='lines+markers',
#                 line=dict(color=self.color_scheme[energy_type])
#             ))
            
#             # Add moving average
#             type_df['MA3'] = type_df['kwh'].rolling(window=3).mean()
#             fig.add_trace(go.Scatter(
#                 x=type_df['billing_period_start'],
#                 y=type_df['MA3'],
#                 name=f"{energy_type.capitalize()} 3-Month MA",
#                 line=dict(
#                     dash='dash',
#                     color=self.color_scheme[energy_type]
#                 )
#             ))
        
#         fig.update_layout(
#             title='Energy Usage Trend with Moving Average',
#             xaxis_title='Date',
#             yaxis_title='Usage (kWh)',
#             hovermode='x unified',
#             showlegend=True
#         )
#         return fig

#     def create_emissions_charts(self, df: pd.DataFrame):
#         """Create emissions-related visualizations."""
#         # Monthly emissions trend
#         emissions_trend = go.Figure()
        
#         for energy_type in df['type'].unique():
#             type_df = df[df['type'] == energy_type]
#             emissions_trend.add_trace(go.Scatter(
#                 x=type_df['billing_period_start'],
#                 y=type_df['emissions_tonnes'],
#                 name=f"{energy_type.capitalize()} Emissions",
#                 mode='lines+markers',
#                 line=dict(color=self.color_scheme[energy_type])
#             ))
        
#         emissions_trend.update_layout(
#             title='Monthly Carbon Emissions',
#             xaxis_title='Date',
#             yaxis_title='Emissions (tCO2e)',
#             hovermode='x unified'
#         )

#         # Usage vs Emissions scatter plot
#         emissions_vs_usage = go.Figure()
        
#         for energy_type in df['type'].unique():
#             type_df = df[df['type'] == energy_type]
#             emissions_vs_usage.add_trace(go.Scatter(
#                 x=type_df['kwh'],
#                 y=type_df['emissions_tonnes'],
#                 name=f"{energy_type.capitalize()}",
#                 mode='markers',
#                 marker=dict(color=self.color_scheme[energy_type])
#             ))
        
#         emissions_vs_usage.update_layout(
#             title='Energy Usage vs Carbon Emissions',
#             xaxis_title='Energy Usage (kWh)',
#             yaxis_title='Emissions (tCO2e)',
#             hovermode='closest'
#         )

#         return emissions_trend, emissions_vs_usage

#     def display_monthly_comparison(self, df: pd.DataFrame):
#         """Display monthly usage and emissions comparison."""
#         monthly_df = df.copy()
#         monthly_df['month_year'] = monthly_df['billing_period_start'].dt.strftime('%B %Y')
        
#         st.subheader("Monthly Comparison by Energy Type")

#         # Create monthly comparison chart
#         fig = go.Figure()
        
#         for energy_type in df['type'].unique():
#             type_df = monthly_df[monthly_df['type'] == energy_type]
#             fig.add_trace(go.Bar(
#                 x=type_df['month_year'],
#                 y=type_df['kwh'],
#                 name=f"{energy_type.capitalize()} Usage",
#                 marker_color=self.color_scheme[energy_type]
#             ))
        
#         fig.update_layout(
#             title='Monthly Energy Usage Comparison',
#             xaxis_title='Month',
#             yaxis_title='Usage (kWh)',
#             barmode='group',
#             xaxis={'tickangle': 45}
#         )
        
#         st.plotly_chart(fig, use_container_width=True)

#         # Monthly statistics by energy type
#         for energy_type in ['electricity', 'gas']:
#             type_df = monthly_df[monthly_df['type'] == energy_type]
            
#             st.subheader(f"{energy_type.capitalize()} Monthly Statistics")
            
#             col1, col2 = st.columns(2)
#             with col1:
#                 st.metric(
#                     "Average Monthly Usage",
#                     f"{type_df['kwh'].mean():,.0f} kWh"
#                 )
#             with col2:
#                 st.metric(
#                     "Average Monthly Emissions",
#                     f"{type_df['emissions_tonnes'].mean():,.2f} tCO2e"
#                 )

#     def display_environmental_impact(self, df: pd.DataFrame):
#         """Display environmental impact metrics."""
#         total_emissions = df['emissions_tonnes'].sum()
        
#         trees_needed = int(total_emissions / TREE_ABSORPTION_RATE)
#         car_km = int(df['emissions_kg'].sum() / CAR_EMISSIONS_PER_KM)
#         homes_equivalent = int(total_emissions / HOME_ANNUAL_EMISSIONS)

#         # Display key metrics
#         st.subheader("Environmental Impact")
#         col1, col2, col3 = st.columns(3)
        
#         with col1:
#             st.metric("Trees Needed for Offset", f"{trees_needed:,d}")
#             st.markdown(f"🌳 Equivalent to planting {trees_needed:,d} trees")
        
#         with col2:
#             st.metric("Car Travel Equivalent", f"{car_km:,d} km")
#             st.markdown(f"🚗 Equal to driving {car_km:,d} kilometers")
        
#         with col3:
#             st.metric("Home Energy Equivalent", f"{homes_equivalent:,d}")
#             st.markdown(f"🏠 Equal to {homes_equivalent:,d} homes' annual usage")

#         # Display emissions breakdown
#         st.subheader("Emissions Breakdown")
        
#         # Create pie chart for emissions by type
#         emissions_by_type = df.groupby('type')['emissions_tonnes'].sum()
        
#         fig = go.Figure(data=[go.Pie(
#             labels=emissions_by_type.index,
#             values=emissions_by_type.values,
#             hole=.3,
#             marker_colors=['#1f77b4', '#ff7f0e']
#         )])
        
#         fig.update_layout(
#             title='Emissions Distribution by Energy Type',
#             showlegend=True
#         )
        
#         fig.update_traces(
#             textposition='inside',
#             textinfo='percent+label',
#             hovertemplate="Energy Type: %{label}<br>Emissions: %{value:.1f} tCO2e<br>Percentage: %{percent}"
#         )
        
#         st.plotly_chart(fig, use_container_width=True)

#     def display_reduction_targets(self, carbon_metrics: Dict):
#         """Display emission reduction targets and progress."""
#         baseline_emissions = carbon_metrics['total_emissions_tonnes']
#         targets = CarbonCalculator.set_reduction_targets(baseline_emissions)
        
#         st.subheader("Emission Reduction Targets")
        
#         # Create target visualization
#         fig = go.Figure()
        
#         # Current emissions
#         fig.add_trace(go.Scatter(
#             x=[0],
#             y=[baseline_emissions],
#             mode='markers',
#             name='Current Emissions',
#             marker=dict(size=15, color='#1f77b4')
#         ))
        
#         # Target line
#         years = list(targets.keys())
#         emissions = list(targets.values())
#         fig.add_trace(go.Scatter(
#             x=years,
#             y=emissions,
#             mode='lines+markers',
#             name='Reduction Targets',
#             line=dict(dash='dash', color='#ff7f0e')
#         ))
        
#         fig.update_layout(
#             title='5-Year Emission Reduction Targets',
#             xaxis_title='Years from Now',
#             yaxis_title='Emissions (tCO2e)',
#             showlegend=True
#         )
        
#         st.plotly_chart(fig, use_container_width=True)
        
#         # Display target table
#         target_df = pd.DataFrame({
#             'Year': [datetime.now().year + year for year in years],
#             'Target Emissions (tCO2e)': emissions,
#             'Required Reduction (tCO2e)': [baseline_emissions - e for e in emissions],
#             'Reduction Percentage': [(baseline_emissions - e) / baseline_emissions * 100 for e in emissions]
#         })
        
#         st.dataframe(target_df.round(2))
#     def display_dashboard(self, df: pd.DataFrame, carbon_metrics: Dict):
#         """Display dashboard metrics, charts, and recommendations."""
#         st.header("Energy & Carbon Dashboard")
        
#         # Top-level metrics
#         col1, col2, col3 = st.columns(3)
#         with col1:
#             st.metric(
#                 "Total Carbon Emissions",
#                 f"{carbon_metrics['total_emissions_tonnes']:,.1f} tCO2e"
#             )
#         with col2:
#             st.metric(
#                 "Total Electricity Usage",
#                 f"{df[df['type'] == 'electricity']['kwh'].sum():,.0f} kWh"
#             )
#         with col3:
#             st.metric(
#                 "Total Gas Usage",
#                 f"{df[df['type'] == 'gas']['kwh'].sum():,.0f} kWh"
#             )

#         # Display metrics for each energy type
#         for energy_type in ["electricity", "gas"]:
#             type_df = df[df['type'] == energy_type]
#             st.subheader(f"{energy_type.capitalize()} Metrics")
#             col1, col2, col3 = st.columns(3)
#             with col1:
#                 st.metric("Total Usage", f"{type_df['kwh'].sum():,.0f} kWh")
#             with col2:
#                 st.metric("Average Monthly", f"{type_df['kwh'].mean():,.0f} kWh")
#             with col3:
#                 st.metric("Highest Month", f"{type_df['kwh'].max():,.0f} kWh")

#         # Display emissions metrics
#         st.subheader("Emissions Breakdown")
#         col1, col2 = st.columns(2)
#         with col1:
#             st.metric("Scope 1 Emissions (Gas)", f"{carbon_metrics['scope1_emissions_tonnes']:,.1f} tCO2e")
#         with col2:
#             st.metric("Scope 2 Emissions (Electricity)", f"{carbon_metrics['scope2_emissions_tonnes']:,.1f} tCO2e")

#         # Create tabs
#         tab1, tab2, tab3, tab4, tab5 = st.tabs([
#             "Usage & Emissions",
#             "Monthly Comparison",
#             "Environmental Impact",
#             "Reduction Targets",
#             "Raw Data"
#         ])
        
#         with tab1:
#             st.plotly_chart(self.create_usage_chart(df), use_container_width=True)
#             emissions_trend, emissions_vs_usage = self.create_emissions_charts(df)
#             st.plotly_chart(emissions_trend, use_container_width=True)
#             st.plotly_chart(emissions_vs_usage, use_container_width=True)

#         with tab2:
#             self.display_monthly_comparison(df)

#         with tab3:
#             self.display_environmental_impact(df)

#         with tab4:
#             self.display_reduction_targets(carbon_metrics)

#         with tab5:
#             self.display_raw_data(df)

#     def display_raw_data(self, df: pd.DataFrame):
#         """Display raw data with enhanced filtering and download options."""
#         st.subheader("Raw Data Analysis")
        
#         # Add filters
#         energy_type = st.selectbox("Filter by Energy Type", ['All'] + list(df['type'].unique()))
#         date_range = st.date_input(
#             "Select Date Range",
#             [df['billing_period_start'].min(), df['billing_period_start'].max()]
#         )
        
#         # Filter data
#         filtered_df = df.copy()
#         if energy_type != 'All':
#             filtered_df = filtered_df[filtered_df['type'] == energy_type]
#         filtered_df = filtered_df[
#             (filtered_df['billing_period_start'].dt.date >= date_range[0]) &
#             (filtered_df['billing_period_start'].dt.date <= date_range[1])
#         ]
        
#         # Display data
#         st.dataframe(
#             filtered_df[[
#                 'filename', 'billing_period_start', 'kwh',
#                 'emissions_tonnes', 'carbon_factor', 'type'
#             ]].round(2)
#         )
        
#         # Download options
#         csv = filtered_df.to_csv(index=False)
#         st.download_button(
#             label="📥 Download Filtered Data (CSV)",
#             data=csv,
#             file_name="energy_data.csv",
#             mime="text/csv"
#         )   
#     def display_raw_data(self, df: pd.DataFrame):
#         """Display raw data with enhanced filtering and download options."""
#         st.subheader("Raw Data Analysis")
        
#         # Add filters
#         energy_type = st.selectbox("Filter by Energy Type", ['All'] + list(df['type'].unique()))
#         date_range = st.date_input(
#             "Select Date Range",
#             [df['billing_period_start'].min(), df['billing_period_start'].max()]
#         )
        
#         # Filter data
#         filtered_df = df.copy()
#         if energy_type != 'All':
#             filtered_df = filtered_df[filtered_df['type'] == energy_type]
#         filtered_df = filtered_df[
#             (filtered_df['billing_period_start'].dt.date >= date_range[0]) &
#             (filtered_df['billing_period_start'].dt.date <= date_range[1])
#         ]
        
#         # Display data
#         st.dataframe(
#             filtered_df[[
#                 'filename', 'billing_period_start', 'kwh',
#                 'emissions_tonnes', 'carbon_factor', 'type'
#             ]].round(2)
#         )
        
#         # Download options
#         csv = filtered_df.to_csv(index=False)
#         st.download_button(
#             label="📥 Download Filtered Data (CSV)",
#             data=csv,
#             file_name="energy_data.csv",
#             mime="text/csv"
#         )

# def validate_data(df: pd.DataFrame) -> Dict:
#     """Validate input data for common issues."""
#     validation_results = {
#         'missing_values': df.isnull().sum().to_dict(),
#         'negative_values': (df['kwh'] < 0).sum(),
#         'future_dates': (df['billing_period_start'] > datetime.now()).sum(),
#         'duplicates': df.duplicated().sum()
#     }
#     return validation_results

# def load_sample_data() -> List[Dict]:
#     """Load sample data for demonstration."""
#     sample_data = []
#     start_date = datetime.now().replace(day=1) - pd.DateOffset(months=12)
    
#     # Define seasonal patterns
#     electricity_patterns = [
#         12000, 11500, 11000, 10500,  # Winter/Spring
#         10000, 9500, 9000, 8500,     # Spring/Summer
#         8000, 8500, 9000, 9500       # Summer/Fall
#     ]
    
#     gas_patterns = [
#         7000, 7500, 7200, 7100,      # Winter/Spring
#         7000, 6900, 6800, 6700,      # Spring/Summer
#         6600, 6700, 6800, 6900       # Summer/Fall
#     ]
    
#     for i in range(12):
#         date = start_date + pd.DateOffset(months=i)
        
#         # Electricity data
#         sample_data.append({
#             'filename': f'sample_electricity_{i+1}',
#             'kwh': electricity_patterns[i],
#             'billing_period_start': date.strftime('%d/%m/%Y'),
#             'billing_period_end': (date + pd.DateOffset(months=1) - pd.DateOffset(days=1)).strftime('%d/%m/%Y'),
#             'type': 'electricity'
#         })
        
#         # Gas data
#         sample_data.append({
#             'filename': f'sample_gas_{i+1}',
#             'kwh': gas_patterns[i],
#             'billing_period_start': date.strftime('%d/%m/%Y'),
#             'billing_period_end': (date + pd.DateOffset(months=1) - pd.DateOffset(days=1)).strftime('%d/%m/%Y'),
#             'type': 'gas'
#         })
    
#     return sample_data

# def main():
#     st.set_page_config(page_title="Energy & Carbon Dashboard", page_icon="⚡",layout="wide")
#     st.title("Energy & Carbon Dashboard")
    
#     # Add settings to sidebar
#     with st.sidebar:
#         st.header("Settings")
#         st.session_state['debug_mode'] = st.checkbox("Debug Mode", False)
    
#     input_method = st.radio(
#         "Select Input Method",
#         ["Upload Invoices", "Manual Input", "Sample Data"],
#         horizontal=True
#     )
    
#     dashboard = Dashboard()

#     if input_method == "Upload Invoices":
#         st.write("Upload your energy invoices to analyze usage and carbon emissions.")
        
#         col1, col2 = st.columns(2)
        
#         with col1:
#             st.subheader("Electricity Invoices")
#             electricity_files = st.file_uploader(
#                 "Choose Electricity PDF files",
#                 type="pdf",
#                 accept_multiple_files=True,
#                 key="electricity_files"
#             )
            
#         with col2:
#             st.subheader("Gas Invoices")
#             gas_files = st.file_uploader(
#                 "Choose Gas PDF files",
#                 type="pdf",
#                 accept_multiple_files=True,
#                 key="gas_files"
#             )

#         if electricity_files or gas_files:
#             data = []
            
#             # Process electricity invoices
#             if electricity_files:
#                 for file in electricity_files:
#                     result = InvoiceProcessor.process_pdf(file, 'electricity')
#                     if result:
#                         data.append(result)
            
#             # Process gas invoices
#             if gas_files:
#                 for file in gas_files:
#                     result = InvoiceProcessor.process_pdf(file, 'gas')
#                     if result:
#                         data.append(result)

#             if data:
#                 df = pd.DataFrame(data)
#                 df['billing_period_start'] = pd.to_datetime(df['billing_period_start'], format='%d/%m/%Y')
#                 df['billing_period_end'] = pd.to_datetime(df['billing_period_end'], format='%d/%m/%Y')
#                 df = df.sort_values('billing_period_start')
                
#                 # Validate data
#                 validation_results = validate_data(df)
#                 if st.session_state.get('debug_mode', False):
#                     st.write("Data Validation Results:", validation_results)
                
#                 carbon_metrics = CarbonCalculator.calculate_metrics(df)
#                 dashboard.display_dashboard(df, carbon_metrics)

#     elif input_method == "Manual Input":
#         st.write("Enter your monthly electricity and gas usage data:")
        
#         manual_data = []
#         n_months = st.number_input("Number of months to enter", min_value=1, max_value=24, value=12)
        
#         for i in range(n_months):
#             st.subheader(f"Month {i+1}")
#             col1, col2 = st.columns(2)
            
#             month_date = st.date_input(f"Select Date for Month {i+1}", key=f"date_{i}")
            
#             with col1:
#                 st.write("Electricity Usage")
#                 elec_kwh = st.number_input(
#                     "Electricity Usage (kWh)",
#                     min_value=0.0,
#                     value=0.0,
#                     key=f"elec_kwh_{i}"
#                 )
                
#             with col2:
#                 st.write("Gas Usage")
#                 gas_kwh = st.number_input(
#                     "Gas Usage (kWh)",
#                     min_value=0.0,
#                     value=0.0,
#                     key=f"gas_kwh_{i}"
#                 )
            
#             if elec_kwh > 0:
#                 manual_data.append({
#                     'filename': f'manual_electricity_{i+1}',
#                     'kwh': elec_kwh,
#                     'billing_period_start': month_date,
#                     'billing_period_end': month_date + pd.DateOffset(months=1) - pd.DateOffset(days=1),
#                     'type': 'electricity'
#                 })
            
#             if gas_kwh > 0:
#                 manual_data.append({
#                     'filename': f'manual_gas_{i+1}',
#                     'kwh': gas_kwh,
#                     'billing_period_start': month_date,
#                     'billing_period_end': month_date + pd.DateOffset(months=1) - pd.DateOffset(days=1),
#                     'type': 'gas'
#                 })

#         if st.button("Generate Dashboard") and manual_data:
#             df = pd.DataFrame(manual_data)
#             df['billing_period_start'] = pd.to_datetime(df['billing_period_start'])
#             df['billing_period_end'] = pd.to_datetime(df['billing_period_end'])
#             carbon_metrics = CarbonCalculator.calculate_metrics(df)
#             dashboard.display_dashboard(df, carbon_metrics)

#     else:  # Sample Data
#         sample_data = load_sample_data()
#         df = pd.DataFrame(sample_data)
#         df['billing_period_start'] = pd.to_datetime(df['billing_period_start'], format='%d/%m/%Y')
#         df['billing_period_end'] = pd.to_datetime(df['billing_period_end'], format='%d/%m/%Y')
#         df = df.sort_values('billing_period_start')
        
#         carbon_metrics = CarbonCalculator.calculate_metrics(df)
#         dashboard.display_dashboard(df, carbon_metrics)

# if __name__ == "__main__":
#     main()




import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import streamlit.components.v1 as components
import random
import numpy as np

# Constants
TREE_ABSORPTION_RATE = 21  # kg CO2 per tree per year
CAR_EMISSIONS_PER_KM = 0.12  # kg CO2 per km
HOME_ANNUAL_EMISSIONS = 3.2  # tonnes CO2e per household annually

# DEFRA carbon conversion factors - source: UK Government GHG Conversion Factors
ELECTRICITY_FACTORS = {
    2022: 0.23332,
    2023: 0.21233,
    2024: 0.20705,  # updated
    2025: 0.18543   # projected (official not yet published)
}

GAS_FACTORS = {
    2022: 0.18521,
    2023: 0.18403,
    2024: 0.18290,  # updated
    2025: 0.18150   # projected (official not yet published)
}
# Set page config
st.set_page_config(
    page_title="Council Carbon Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'landing'

if 'data_entries' not in st.session_state:
    st.session_state.data_entries = []

if 'has_submitted_form' not in st.session_state:
    st.session_state.has_submitted_form = False

if 'show_form' not in st.session_state:
    st.session_state.show_form = False

if 'demo_mode' not in st.session_state:
    st.session_state.demo_mode = False

if 'entry_mode' not in st.session_state:
    st.session_state.entry_mode = None

# Navigation function
def navigate_to(page):
    st.session_state.current_page = page

# Toggle demo mode
def toggle_demo_mode():
    st.session_state.demo_mode = not st.session_state.demo_mode
    if st.session_state.demo_mode:
        load_demo_data()
    else:
        # Clear data when exiting demo mode
        st.session_state.data_entries = []

# Generate demo data
def load_demo_data():
    # Clear existing data
    st.session_state.data_entries = []
    
    # Generate 12 months of data
    start_date = datetime(2024, 1, 1)
    
    # Electricity seasonal pattern (higher in winter months)
    elec_pattern = [12500, 11800, 10500, 9200, 8500, 8000, 8200, 8500, 9000, 10000, 11200, 12000]
    
    # Gas seasonal pattern (much higher in winter)
    gas_pattern = [8000, 7500, 6500, 5000, 3500, 2500, 2000, 2200, 3000, 4500, 6500, 7800]
    
    # Add some random variation
    for month in range(12):
        current_date = start_date.replace(month=month+1)
        
        # Add random variation of ±10%
        elec_variation = random.uniform(0.9, 1.1)
        gas_variation = random.uniform(0.9, 1.1)
        
        elec_kwh = elec_pattern[month] * elec_variation
        gas_kwh = gas_pattern[month] * gas_variation
        
        year = current_date.year
        emissions = calculate_emissions(elec_kwh, gas_kwh, year)
        
        entry = {
            "month": current_date.strftime("%B %Y"),
            "electricity_kwh": elec_kwh,
            "electricity_provider": "Demo Energy Ltd",
            "gas_kwh": gas_pattern[month] * gas_variation,
            "gas_provider": "Demo Gas Ltd",
            "electricity_emissions_kg": emissions["electricity_emissions_kg"],
            "gas_emissions_kg": emissions["gas_emissions_kg"],
            "total_emissions_tonnes": emissions["total_emissions_tonnes"]
        }
        
        st.session_state.data_entries.append(entry)

# Custom CSS
def load_css():
    st.markdown("""
    <style>
        /* Main Styles */
        .main-header {
            font-size: 2.5rem;
            font-weight: 700;
            color: #0e5c36;
            margin-bottom: 1rem;
            text-align: center;
        }
        .sub-header {
            font-size: 1.8rem;
            color: #186fa6;
            margin-bottom: 1rem;
            font-weight: 600;
        }
        
        /* Card Styles */
        .card {
            padding: 1.5rem;
            border-radius: 0.5rem;
            background-color: white;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
            margin-bottom: 1.5rem;
            border-top: 3px solid #1E8449;
        }
        
        /* Feature Cards */
        .feature-card {
            text-align: center;
            padding: 1.8rem;
            border-radius: 0.5rem;
            background-color: white;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
            margin-bottom: 1.5rem;
            height: 100%;
        }
        
        /* Hero Section */
        .hero-section {
            background: linear-gradient(120deg, #1E8449 0%, #2E86C1 100%);
            padding: 2.5rem 2rem;
            border-radius: 0.5rem;
            color: white;
            margin-bottom: 2rem;
            text-align: center;
        }
        
        /* Facts Section */
        .facts-card {
            background-color: #f9f9f9;
            border-radius: 0.5rem;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border-left: 3px solid #2E86C1;
        }
        
        /* Metric Card */
        .metric-card {
            background-color: white;
            border-radius: 0.5rem;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
            padding: 1.5rem;
            text-align: center;
            margin-bottom: 1.5rem;
            border-top: 3px solid #2E86C1;
        }
        .metric-value {
            font-size: 2.2rem;
            font-weight: bold;
            color: #2E86C1;
            margin-bottom: 0.5rem;
        }
        .metric-label {
            font-size: 1rem;
            color: #444;
            font-weight: 500;
        }
        
        /* Form Elements */
        .form-embed {
            border: none;
            width: 100%;
            height: 1000px;
            margin-top: 1rem;
            border-radius: 0.5rem;
        }
        
        /* Premium Elements */
        .premium-banner {
            background-color: #f9f9f9;
            color: #333;
            padding: 1.5rem;
            border-radius: 0.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
            border-left: 3px solid #1E8449;
        }
        
        /* Buttons */
        .cta-button {
            background: #1E8449;
            color: white;
            font-weight: bold;
            padding: 0.8rem 2rem;
            border-radius: 0.3rem;
            border: none;
            text-align: center;
            display: inline-block;
            margin: 0.5rem 0;
        }
        
        /* Sticker Element */
        .sticker {
            position: absolute;
            top: 10px;
            right: 10px;
            background: #FFC107;
            color: #333;
            padding: 0.5rem 1rem;
            border-radius: 0.3rem;
            font-weight: bold;
            z-index: 100;
        }
        
        /* Step Cards */
        .step-card {
            display: flex;
            align-items: center;
            background-color: white;
            border-radius: 0.5rem;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
            padding: 1.2rem 1.5rem;
            margin-bottom: 1rem;
        }
        .step-number {
            background-color: #1E8449;
            color: white;
            width: 2rem;
            height: 2rem;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            margin-right: 1rem;
            flex-shrink: 0;
        }
        .step-content {
            flex-grow: 1;
        }
        
        /* Custom Sidebar */
        .sidebar .sidebar-content {
            background-color: #f8f9fa;
        }
        
        /* Stat Comparison */
        .comparison-better {
            color: #28a745;
            font-weight: bold;
        }
        .comparison-worse {
            color: #dc3545;
            font-weight: bold;
        }
        
        /* Progress indicator */
        .progress-indicator {
            display: flex;
            justify-content: space-between;
            margin-bottom: 2rem;
        }
        .progress-step {
            flex: 1;
            text-align: center;
            padding: 1rem;
            position: relative;
        }
        .progress-step:not(:last-child):after {
            content: '';
            position: absolute;
            top: 2.2rem;
            right: -1rem;
            width: 2rem;
            height: 2px;
            background-color: #ddd;
            z-index: 0;
        }
        .progress-step.active .step-circle {
            background-color: #1E8449;
            color: white;
        }
        .progress-step.completed .step-circle {
            background-color: #28a745;
            color: white;
        }
        .step-circle {
            width: 2.5rem;
            height: 2.5rem;
            border-radius: 50%;
            background-color: #f1f1f1;
            color: #666;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 0.5rem;
            font-weight: bold;
            z-index: 1;
            position: relative;
        }
        .step-label {
            font-size: 0.9rem;
            color: #666;
        }
        
        /* Source citation */
        .source-citation {
            font-size: 0.8rem;
            color: #666;
            font-style: italic;
            margin-top: 0.5rem;
        }
        
        /* Semi-disabled section */
        .premium-section {
            opacity: 0.85;
        }
        
        /* Contact form */
        .contact-section {
            background: linear-gradient(120deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 2rem;
            border-radius: 0.5rem;
            margin: 2rem 0;
            border: 2px solid #1E8449;
        }
        
        /* Premium feature badge */
        .premium-badge {
            display: inline-block;
            background-color: #ffc107;
            color: #212529;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            margin-left: 0.5rem;
            font-size: 0.8rem;
            font-weight: bold;
        }
        
        /* Floating form button */
        .floating-button {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background-color: #1E8449;
            color: white;
            padding: 1rem;
            border-radius: 50%;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
            z-index: 1000;
            width: 60px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-weight: bold;
            font-size: 0.9rem;
            text-align: center;
            line-height: 1.1;
        }
    </style>
    """, unsafe_allow_html=True)

# Calculate carbon emissions for electricity and gas
def calculate_emissions(electricity_kwh, gas_kwh, year):
    # Get conversion factors for the specified year, or use latest if not available
    electricity_factor = ELECTRICITY_FACTORS.get(year, list(ELECTRICITY_FACTORS.values())[-1])
    gas_factor = GAS_FACTORS.get(year, list(GAS_FACTORS.values())[-1])
    
    # Calculate emissions
    electricity_emissions_kg = electricity_kwh * electricity_factor
    gas_emissions_kg = gas_kwh * gas_factor
    
    total_emissions_kg = electricity_emissions_kg + gas_emissions_kg
    total_emissions_tonnes = total_emissions_kg / 1000
    
    return {
        "electricity_emissions_kg": electricity_emissions_kg,
        "gas_emissions_kg": gas_emissions_kg,  # Fixed from emissions_kg
        "total_emissions_tonnes": total_emissions_tonnes
    }
# Show Contact Us form
def show_contact_us_form():
    st.markdown("""
    <div class="contact-section">
        <h2 style="text-align: center; margin-top: 0;">Contact Us</h2>
        <p style="text-align: center; margin-bottom: 1.5rem;">Complete our brief questionnaire to learn more about our carbon reporting solutions and premium features.</p>
    """, unsafe_allow_html=True)
    
    # Embed Google Form
    google_form_html = """
    <iframe src="https://docs.google.com/forms/d/e/1FAIpQLSfwzklepnKExPn6Skhy_e74wEgrQy3iiXHvPg82Y03maIUeQg/viewform?embedded=true" width="100%" height="1275" frameborder="0" marginheight="0" marginwidth="0">Loading…</iframe>
    """
    
    components.html(google_form_html, height=1300)
    
    st.markdown("</div>", unsafe_allow_html=True)

# Landing Page
def landing_page():
    # Hero Section
    st.markdown("""
    <div class="hero-section">
        <h1 style="font-size: 2.5rem; margin-bottom: 1rem;">Council Carbon Reporting Simplified</h1>
        <p style="font-size: 1.2rem; margin-bottom: 1.5rem;">Track, analyse, and report your council's carbon emissions using DEFRA standards</p>
    </div>
    """, unsafe_allow_html=True)
    
    # UK Council Carbon Facts
    st.markdown("<h2 style='text-align: center; margin-bottom: 1.5rem;'>UK Council Carbon Emissions Facts</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="facts-card">
            <h3>Key Carbon Reduction Targets</h3>
            <ul>
                <li>UK Government target: Net Zero by 2050</li>
                <li>78% reduction in emissions by 2035 compared to 1990 levels</li>
                <li>Over 300 UK councils have declared a climate emergency</li>
                <li>Many councils aiming for carbon neutrality by 2030</li>
            </ul>
            <p class="source-citation">Source: Committee on Climate Change, 2021</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="facts-card">
            <h3>Council Building Emissions</h3>
            <ul>
                <li>Council buildings account for approximately 27% of local authority emissions</li>
                <li>Average council building uses 284 kWh/m² annually</li>
                <li>LED lighting retrofits can reduce electricity consumption by up to 50%</li>
                <li>Building heating systems account for 40-60% of energy use</li>
            </ul>
            <p class="source-citation">Source: Local Government Association Carbon Accounting Tool, 2023</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="facts-card">
            <h3>DEFRA Reporting Standards</h3>
            <ul>
                <li>UK councils report using DEFRA conversion factors</li>
                <li>Annual updates to reflect changing grid mix</li>
                <li>Mandatory for councils with >250 employees under SECR regulations</li>
                <li>Scope 1, 2 and selected Scope 3 emissions required</li>
            </ul>
            <p class="source-citation">Source: Department for Environment, Food & Rural Affairs, 2024</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="facts-card">
            <h3>Council Progress</h3>
            <ul>
                <li>UK local authorities have reduced emissions by an average of 30% since 2010</li>
                <li>Transport remains the most challenging sector with only 7% reduction</li>
                <li>Renewable energy procurement has increased by 40% since 2018</li>
                <li>Building retrofits deliver average of 23% emissions reduction</li>
            </ul>
            <p class="source-citation">Source: UK100 Network Report, 2023</p>
        </div>
        """, unsafe_allow_html=True)
    
    # How it works section with minimal text
    st.markdown("<h2 style='text-align: center; margin: 2rem 0 1.5rem;'>How It Works</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <h3>Input Data</h3>
            <p>Enter energy consumption manually or upload invoices</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <h3>Automatic Calculations</h3>
            <p>Conversion to emissions using DEFRA factors</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <h3>Visual Reports</h3>
            <p>Clear visualisations and actionable insights</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Premium Features Section
    st.markdown("""
    <h2 style='text-align: center; margin: 2rem 0 1.5rem;'>Available Features</h2>
    <div class="card">
        <div style="display: flex; flex-wrap: wrap; gap: 1rem;">
            <div style="flex: 1; min-width: 250px;">
                <h3>Basic Features (Free)</h3>
                <ul>
                    <li>Manual data entry</li>
                    <li>Basic carbon calculations using DEFRA factors</li>
                    <li>Visual dashboard with usage trends</li>
                    <li>Environmental impact metrics</li>
                </ul>
            </div>
            <div style="flex: 1; min-width: 250px;">
                <h3>Premium Features <span class="premium-badge">Opt-in</span></h3>
                <ul>
                    <li>Automatic invoice processing</li>
                    <li>Detailed emissions reports</li>
                    <li>Data validation and quality checks</li>
                    <li>Custom reporting templates</li>
                    <li>Multi Site Analysis</li>
                </ul>
                <p style="margin-top: 1rem;"><strong>Complete our questionnaire to opt in for premium features</strong></p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Contact Us Form
    show_contact_us_form()

# Data Entry Page
def data_entry_page():
    st.markdown("<h1 class='sub-header'>Carbon Data Dashboard</h1>", unsafe_allow_html=True)
    
    # Demo mode toggle
    demo_col1, demo_col2 = st.columns([3, 1])
    with demo_col2:
        if st.button(
            "View Demo Data" if not st.session_state.demo_mode else "Clear Demo Data", 
            use_container_width=True
        ):
            toggle_demo_mode()
            st.rerun()  # Using st.rerun() instead of experimental_rerun
    
    # Show no data message if not in demo mode and no data entered
    if not st.session_state.demo_mode and not st.session_state.data_entries:
        st.info("No data available. Click 'View Demo Data' to see sample council energy data.")
        
        # Show data entry options
        st.markdown("<h2 style='margin-top: 2rem;'>Enter Your Own Data</h2>", unsafe_allow_html=True)
        
        # Create clear options for data entry
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="card" style="height: 100%;">
                <h3 style="margin-top: 0;">Quick Start: Enter Single Month</h3>
                <p>Add a single month of data to get started quickly.</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Enter Single Month", type="primary", use_container_width=True):
                st.session_state.entry_mode = "single"
                st.rerun()
        
        with col2:
            st.markdown("""
            <div class="card" style="height: 100%;">
                <h3 style="margin-top: 0;">Comprehensive: Enter Full Year</h3>
                <p>Input data for multiple months to see detailed trends and comparisons.</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Enter Multiple Months", type="primary", use_container_width=True):
                st.session_state.entry_mode = "multiple"
                st.rerun()
        
        # Add note about premium features
        # Premium Features Section in Python
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("""
                <h3 style="margin-top: 0;">Premium Features Available <span class="premium-badge">Opt-in</span></h3>
                <p>Upgrade to access invoice processing, custom reports, data validation and more.</p>
            """, unsafe_allow_html=True)
        with col2:
            if st.button("Contact Us", key="contact_us_banner", use_container_width=True):
                navigate_to('contact_us')
                st.rerun()

        
        # Show Contact Form
        show_contact_us_form()
    
    # If user has selected an entry mode, show the appropriate form
    if 'entry_mode' in st.session_state and st.session_state.entry_mode is not None:
        if st.session_state.entry_mode == "single":
            show_single_month_form()
        elif st.session_state.entry_mode == "multiple":
            show_multiple_month_form()
    
    # Show dashboard if there's data (demo or entered)
    if st.session_state.data_entries:
        if st.session_state.demo_mode:
            st.success("Viewing demo data - This shows 12 months of sample data for a typical council")
        show_dashboard(pd.DataFrame(st.session_state.data_entries))

# Functions for different data entry forms
def show_single_month_form():
    """Display a form for entering a single month of data"""
    st.subheader("Enter Energy Data for a Single Month")
    
    with st.form("single_month_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            month = st.date_input("Reporting Month", datetime.now())
            electricity_usage = st.number_input("Electricity Usage (kWh)", min_value=0.0, value=9000.0)
            electricity_provider = st.text_input("Electricity Provider", "")
        
        with col2:
            gas_usage = st.number_input("Gas Usage (kWh)", min_value=0.0, value=5000.0)
            gas_provider = st.text_input("Gas Provider", "")
        
        submitted = st.form_submit_button("Save Data", type="primary")
        cancel = st.form_submit_button("Cancel")
        
        if submitted:
            # Calculate carbon emissions
            year = month.year
            emissions = calculate_emissions(electricity_usage, gas_usage, year)
            
            # Create entry
            new_entry = {
                "month": month.strftime("%B %Y"),
                "electricity_kwh": electricity_usage,
                "electricity_provider": electricity_provider,
                "gas_kwh": gas_usage,
                "gas_provider": gas_provider,
                "electricity_emissions_kg": emissions["electricity_emissions_kg"],
                "gas_emissions_kg": emissions["gas_emissions_kg"],
                "total_emissions_tonnes": emissions["total_emissions_tonnes"]
            }
            
            # Add to data entries
            st.session_state.data_entries.append(new_entry)
            st.success("Data saved successfully")
            
            # Reset entry mode
            st.session_state.entry_mode = None
            st.rerun()
                
        if cancel:
            st.session_state.entry_mode = None
            st.rerun()

def show_multiple_month_form():
    """Display a form for entering multiple months of data"""
    st.subheader("Enter Energy Data for Multiple Months")
    
    tab1, tab2, tab3 = st.tabs(["Jan-Apr", "May-Aug", "Sep-Dec"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("January")
            jan_elec = st.number_input("January Electricity (kWh)", min_value=0.0, value=10000.0, key="jan_elec")
            jan_gas = st.number_input("January Gas (kWh)", min_value=0.0, value=8000.0, key="jan_gas")
        
        with col2:
            st.subheader("February")
            feb_elec = st.number_input("February Electricity (kWh)", min_value=0.0, value=9500.0, key="feb_elec")
            feb_gas = st.number_input("February Gas (kWh)", min_value=0.0, value=7500.0, key="feb_gas")
        
        col3, col4 = st.columns(2)
        with col3:
            st.subheader("March")
            mar_elec = st.number_input("March Electricity (kWh)", min_value=0.0, value=9000.0, key="mar_elec")
            mar_gas = st.number_input("March Gas (kWh)", min_value=0.0, value=6500.0, key="mar_gas")
        
        with col4:
            st.subheader("April")
            apr_elec = st.number_input("April Electricity (kWh)", min_value=0.0, value=8500.0, key="apr_elec")
            apr_gas = st.number_input("April Gas (kWh)", min_value=0.0, value=5000.0, key="apr_gas")
    
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("May")
            may_elec = st.number_input("May Electricity (kWh)", min_value=0.0, value=8000.0, key="may_elec")
            may_gas = st.number_input("May Gas (kWh)", min_value=0.0, value=3500.0, key="may_gas")
        
        with col2:
            st.subheader("June")
            jun_elec = st.number_input("June Electricity (kWh)", min_value=0.0, value=7800.0, key="jun_elec")
            jun_gas = st.number_input("June Gas (kWh)", min_value=0.0, value=2500.0, key="jun_gas")
        
        col3, col4 = st.columns(2)
        with col3:
            st.subheader("July")
            jul_elec = st.number_input("July Electricity (kWh)", min_value=0.0, value=7500.0, key="jul_elec")
            jul_gas = st.number_input("July Gas (kWh)", min_value=0.0, value=2000.0, key="jul_gas")
        
        with col4:
            st.subheader("August")
            aug_elec = st.number_input("August Electricity (kWh)", min_value=0.0, value=7800.0, key="aug_elec")
            aug_gas = st.number_input("August Gas (kWh)", min_value=0.0, value=2200.0, key="aug_gas")
    
    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("September")
            sep_elec = st.number_input("September Electricity (kWh)", min_value=0.0, value=8200.0, key="sep_elec")
            sep_gas = st.number_input("September Gas (kWh)", min_value=0.0, value=3000.0, key="sep_gas")
        
        with col2:
            st.subheader("October")
            oct_elec = st.number_input("October Electricity (kWh)", min_value=0.0, value=8800.0, key="oct_elec")
            oct_gas = st.number_input("October Gas (kWh)", min_value=0.0, value=4500.0, key="oct_gas")
        
        col3, col4 = st.columns(2)
        with col3:
            st.subheader("November")
            nov_elec = st.number_input("November Electricity (kWh)", min_value=0.0, value=9500.0, key="nov_elec")
            nov_gas = st.number_input("November Gas (kWh)", min_value=0.0, value=6500.0, key="nov_gas")
        
        with col4:
            st.subheader("December")
            dec_elec = st.number_input("December Electricity (kWh)", min_value=0.0, value=10000.0, key="dec_elec")
            dec_gas = st.number_input("December Gas (kWh)", min_value=0.0, value=7800.0, key="dec_gas")
    
    # Provider information
    st.markdown("<h3>Supplier Information</h3>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        elec_provider = st.text_input("Electricity Supplier", value="")
    with col2:
        gas_provider = st.text_input("Gas Supplier", value="")
    
    # Buttons for processing or cancelling
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Cancel", use_container_width=True):
            st.session_state.entry_mode = None
            st.rerun()
    
    with col2:
        if st.button("Process All Data", type="primary", use_container_width=True):
            # Clear existing entries if this is first data
            if len(st.session_state.data_entries) == 0:
                st.session_state.data_entries = []
            
            # Add entries for each month
            year = datetime.now().year
            
            # Create a mapping of months to their respective data
            month_data = {
                1: (jan_elec, jan_gas, "January"),
                2: (feb_elec, feb_gas, "February"),
                3: (mar_elec, mar_gas, "March"),
                4: (apr_elec, apr_gas, "April"),
                5: (may_elec, may_gas, "May"),
                6: (jun_elec, jun_gas, "June"),
                7: (jul_elec, jul_gas, "July"),
                8: (aug_elec, aug_gas, "August"),
                9: (sep_elec, sep_gas, "September"),
                10: (oct_elec, oct_gas, "October"),
                11: (nov_elec, nov_gas, "November"),
                12: (dec_elec, dec_gas, "December")
            }
            
            # Process each month
            for month_num, (elec, gas, month_name) in month_data.items():
                if elec > 0 or gas > 0:  # Only add if there's data
                    date = datetime(year, month_num, 1)
                    emissions = calculate_emissions(elec, gas, year)
                    
                    entry = {
                        "month": date.strftime("%B %Y"),
                        "electricity_kwh": elec,
                        "electricity_provider": elec_provider,
                        "gas_kwh": gas,
                        "gas_provider": gas_provider,
                        "electricity_emissions_kg": emissions["electricity_emissions_kg"],
                        "gas_emissions_kg": emissions["gas_emissions_kg"],
                        "total_emissions_tonnes": emissions["total_emissions_tonnes"]
                    }
                    
                    st.session_state.data_entries.append(entry)
            
            st.success(f"Added data for multiple months")
            
            # Reset entry mode
            st.session_state.entry_mode = None
            st.rerun()

# Show dashboard based on entered data
def show_dashboard(df):
    st.markdown("<h2 class='sub-header'>Carbon Emissions Dashboard</h2>", unsafe_allow_html=True)
    
    # Convert to proper format for visualization
    dashboard_data = []
    for entry in st.session_state.data_entries:
        dashboard_data.append({
            "month": entry["month"],
            "Electricity": entry["electricity_kwh"],
            "Gas": entry["gas_kwh"],
            "Electricity Emissions": entry["electricity_emissions_kg"]/1000,
            "Gas Emissions": entry["gas_emissions_kg"]/1000
        })
    
    dashboard_df = pd.DataFrame(dashboard_data)
    
    # Calculate totals
    total_electricity = df["electricity_kwh"].sum()
    total_gas = df["gas_kwh"].sum()
    total_emissions = df["total_emissions_tonnes"].sum()
    
    # Display summary metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_emissions:.2f}</div>
            <div class="metric-label">Total Carbon Emissions (tCO₂e)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_electricity:,.0f}</div>
            <div class="metric-label">Total Electricity Usage (kWh)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_gas:,.0f}</div>
            <div class="metric-label">Total Gas Usage (kWh)</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Display charts if we have enough data
    if len(st.session_state.data_entries) > 0:
        # Create tabs for different visualizations
        tab1, tab2, tab3 = st.tabs(["Usage", "Emissions", "Environmental Impact"])
        
        with tab1:
            # Usage chart
            st.subheader("Energy Usage Trends")
            
            # Sort data by month
            try:
                dashboard_df['month_dt'] = pd.to_datetime(dashboard_df['month'], format='%B %Y')
                dashboard_df = dashboard_df.sort_values('month_dt')
                dashboard_df['month'] = dashboard_df['month_dt'].dt.strftime('%b %Y')
                dashboard_df = dashboard_df.drop('month_dt', axis=1)
            except:
                pass  # If sort fails, use original order
            
            fig = go.Figure()
            
            # Add electricity data
            fig.add_trace(go.Bar(
                x=dashboard_df["month"],
                y=dashboard_df["Electricity"],
                name="Electricity (kWh)",
                marker_color="#1f77b4"
            ))
            
            # Add gas data
            fig.add_trace(go.Bar(
                x=dashboard_df["month"],
                y=dashboard_df["Gas"],
                name="Gas (kWh)",
                marker_color="#ff7f0e"
            ))
            
            # Add a moving average for electricity if we have enough data
            if len(dashboard_df) >= 3:
                fig.add_trace(go.Scatter(
                    x=dashboard_df["month"],
                    y=dashboard_df["Electricity"].rolling(3, min_periods=1).mean(),
                    name="Electricity 3-Month Average",
                    line=dict(color="#1f77b4", dash="dash")
                ))
            
            fig.update_layout(
                title="Monthly Energy Usage",
                xaxis_title="Month",
                yaxis_title="Usage (kWh)",
                legend_title="Energy Type",
                hovermode="x unified",
                barmode="group"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Add simple insights
            if len(dashboard_df) >= 3:
                highest_month = dashboard_df.loc[dashboard_df["Electricity"].idxmax(), "month"]
                lowest_month = dashboard_df.loc[dashboard_df["Electricity"].idxmin(), "month"]
                
                st.markdown(f"""
                <div class="card" style="background-color: #f8f9fa;">
                    <h4 style="margin-top: 0;">Key Usage Insights:</h4>
                    <ul>
                        <li>Highest electricity usage: <strong>{highest_month}</strong></li>
                        <li>Lowest electricity usage: <strong>{lowest_month}</strong></li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
        
        with tab2:
            # Emissions chart
            st.subheader("Carbon Emissions Analysis")
            
            fig = go.Figure()
            
            # Add electricity emissions
            fig.add_trace(go.Scatter(
                x=dashboard_df["month"],
                y=dashboard_df["Electricity Emissions"],
                name="Electricity (tCO₂e)",
                mode="lines+markers",
                line=dict(color="#1f77b4", width=3),
                marker=dict(size=8)
            ))
            
            # Add gas emissions
            fig.add_trace(go.Scatter(
                x=dashboard_df["month"],
                y=dashboard_df["Gas Emissions"],
                name="Gas (tCO₂e)",
                mode="lines+markers",
                line=dict(color="#ff7f0e", width=3),
                marker=dict(size=8)
            ))
            
            # Add total emissions
            fig.add_trace(go.Scatter(
                x=dashboard_df["month"],
                y=dashboard_df["Electricity Emissions"] + dashboard_df["Gas Emissions"],
                name="Total Emissions (tCO₂e)",
                mode="lines",
                line=dict(color="#2ca02c", width=4, dash="dot"),
            ))
            
            fig.update_layout(
                title="Monthly Carbon Emissions",
                xaxis_title="Month",
                yaxis_title="Emissions (tCO₂e)",
                legend_title="Source",
                hovermode="x unified"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add emissions breakdown pie chart
            emissions_data = [
                df["electricity_emissions_kg"].sum() / 1000,
                df["gas_emissions_kg"].sum() / 1000
            ]
            fig = px.pie(
                values=emissions_data,
                names=["Electricity", "Gas"],
                title="Emissions Breakdown",
                color_discrete_sequence=["#1f77b4", "#ff7f0e"],
                hole=0.4
            )
            fig.update_traces(textinfo='percent+label')
            st.plotly_chart(fig)
        
        with tab3:
            # Environmental impact
            st.subheader("Environmental Impact Assessment")
            
            # Calculate impact metrics
            trees_needed = int(total_emissions / TREE_ABSORPTION_RATE)
            car_km = int((total_emissions * 1000) / CAR_EMISSIONS_PER_KM)
            homes_equivalent = int(total_emissions / HOME_ANNUAL_EMISSIONS)
            
            # Visual impact cards
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{trees_needed:,d}</div>
                    <div class="metric-label">Trees Needed</div>
                    <p style="margin-top: 0.5rem; font-size: 0.8rem;">Trees required to offset your emissions</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{car_km:,d}</div>
                    <div class="metric-label">Car Kilometres</div>
                    <p style="margin-top: 0.5rem; font-size: 0.8rem;">Equivalent to this many km of driving</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{homes_equivalent:,d}</div>
                    <div class="metric-label">Homes</div>
                    <p style="margin-top: 0.5rem; font-size: 0.8rem;">Equivalent to annual usage of this many homes</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Add a visual comparison if we have enough data
            if len(dashboard_df) >= 3:
                st.subheader("Emissions Reduction Progress")
                
                # Calculate current vs target emissions
                current_annual_rate = total_emissions * (12 / len(dashboard_df))
                science_based_target = current_annual_rate * 0.85  # 15% reduction target
                
                # Create a gauge chart to show progress toward target
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number+delta",
                    value = current_annual_rate,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "Annual Emissions Rate (tCO₂e)", 'font': {'size': 24}},
                    delta = {'reference': science_based_target, 'decreasing': {'color': "green"}, 'increasing': {'color': "red"}},
                    gauge = {
                        'axis': {'range': [None, current_annual_rate * 1.5], 'tickwidth': 1, 'tickcolor': "darkblue"},
                        'bar': {'color': "darkblue"},
                        'bgcolor': "white",
                        'borderwidth': 2,
                        'bordercolor': "gray",
                        'steps': [
                            {'range': [0, science_based_target], 'color': 'lightgreen'},
                            {'range': [science_based_target, current_annual_rate * 1.2], 'color': 'yellow'}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': science_based_target
                        }
                    }
                ))
                
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                # st.markdown(f"""
                # <div class="card" style="background-color: #f8f9fa;">
                #     <h4 style="margin-top: 0;">Reduction Target Analysis:</h4>
                #     <ul>
                #         <li>Current annual emissions rate: <strong>{current_annual_rate:.2f} tCO₂e</strong></li>
                #         <li>Science-based target: <strong>{science_based_target:.2f} tCO₂e</strong> (15% reduction)</li>
                #         <li>Required reduction: <strong>{current_annual_rate - science_based_target:.2f} tCO₂e</strong></li>
                #     </ul>
                # </div>
                # """, unsafe_allow_html=True)
    
    # Add premium features call-to-action after the dashboard
    # Premium Features Section in Python
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("""
            <h3 style="margin-top: 0;">Premium Features Available <span class="premium-badge">Opt-in</span></h3>
            <p>Upgrade to access invoice processing, custom reports, data validation and more.</p>
        """, unsafe_allow_html=True)
    with col2:
        if st.button("Contact Us", key="contact_us_banner", use_container_width=True):
            navigate_to('contact_us')
            st.rerun()


# Invoice Processing Page (Premium Feature with Opt-in)
def invoice_processing_page():
    st.markdown("<h1 class='sub-header'>Invoice Processing</h1>", unsafe_allow_html=True)
    
    # Premium Features Message - Opt-in version
    st.markdown("""
    <div class="premium-banner" style="text-align: center; padding: 2rem;">
        <h2 style="margin-bottom: 1rem;">Premium Feature <span class="premium-badge">Opt-in</span></h2>
        <p style="margin-bottom: 1.5rem;">This is an optional premium feature. Complete our questionnaire to opt in or learn more.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show semi-disabled content
    st.markdown('<div class="premium-section">', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="card">
        <h3 style="margin-top: 0;">Upload Your Energy Invoices</h3>
        <p>Our system will automatically extract usage data, saving time and ensuring accuracy.</p>
        <p><strong>Note:</strong> This is a preview of the premium invoice processing feature.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Electricity Invoices")
        st.file_uploader(
            "Choose Electricity PDF files",
            type="pdf",
            accept_multiple_files=True,
            key="electricity_files",
            disabled=True
        )
    
    with col2:
        st.subheader("Gas Invoices")
        st.file_uploader(
            "Choose Gas PDF files",
            type="pdf",
            accept_multiple_files=True,
            key="gas_files",
            disabled=True
        )
    
    # Disabled process button
    st.button("Process Invoices", type="primary", disabled=True)
    
    st.markdown("""
    <div class="card">
        <h3 style="margin-top: 0;">Premium Features Include:</h3>
        <ul>
            <li><strong>Automatic Data Extraction</strong> - Save hours of manual data entry</li>
            <li><strong>PDF Invoice Processing</strong> - Support for all major UK energy suppliers</li>
            <li><strong>Data Validation</strong> - Built-in error checking and anomaly detection</li>
            <li><strong>Bulk Processing</strong> - Upload and process multiple invoices at once</li>
        </ul>
        <p style="margin-top: 1rem;">Complete our questionnaire to opt in for these premium features.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Contact Us Form
    st.markdown('<a name="contact"></a>', unsafe_allow_html=True)
    show_contact_us_form()
    
    # Add floating button to contact form
    st.markdown("""
    <div class="floating-button" onclick="document.getElementById('contact').scrollIntoView({behavior: 'smooth'})">
        Contact Us
    </div>
    """, unsafe_allow_html=True)


# Invoice Processing Page (Premium Feature with Opt-in)
def contact_us_page():
    st.markdown("<h1 class='sub-header'>Contact Us</h1>", unsafe_allow_html=True)
    
    
    # Contact Us Form
    st.markdown('<a name="contact"></a>', unsafe_allow_html=True)
    show_contact_us_form()
    
    # Add floating button to contact form
    st.markdown("""
    <div class="floating-button" onclick="document.getElementById('contact').scrollIntoView({behavior: 'smooth'})">
        Contact Us
    </div>
    """, unsafe_allow_html=True)

# Main app logic
def main():
    load_css()
    
    # Add ID for contact form scrolling
    st.markdown('<a id="contact"></a>', unsafe_allow_html=True)
    
    # Sidebar navigation with improved styling
    with st.sidebar:
        # st.image("https://via.placeholder.com/150x150.png?text=Logo", width=150)
        
        # User status indicator
        if st.session_state.demo_mode:
            st.info("Demo Mode Active")
        
        st.markdown("<h3>Navigation</h3>", unsafe_allow_html=True)
        
        # Navigation buttons
        if st.button("Home", key="nav_home", use_container_width=True):
            navigate_to('landing')
        
        if st.button("Dashboard", key="nav_dashboard", use_container_width=True):
            navigate_to('data_entry')
        
        if st.button("Invoice Processing", key="nav_invoice", use_container_width=True):
            navigate_to('invoice_processing')
        
        if st.button("Contact Us", key="nav_contact", use_container_width=True):
            navigate_to('contact_us')  # Use invoice page since it has the contact form prominently
        
        # Add a toggle for demo mode
        st.markdown("<hr>", unsafe_allow_html=True)
        
        st.write("View sample data:")
        if st.button(
            "View Demo Data" if not st.session_state.demo_mode else "Clear Demo Data", 
            key="toggle_demo",
            use_container_width=True
        ):
            toggle_demo_mode()
            st.rerun()
        
        # Add council compliance section
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<h4>Compliance Information</h4>", unsafe_allow_html=True)
        
        with st.expander("Reporting Standards"):
            st.write("This platform supports:")
            st.write("• Based on DEFRA conversion factors")
    
    # Main content based on current page
    if st.session_state.current_page == 'landing':
        landing_page()
    elif st.session_state.current_page == 'data_entry':
        data_entry_page()
    elif st.session_state.current_page == 'invoice_processing':
        invoice_processing_page()
    elif st.session_state.current_page == 'contact_us':
        contact_us_page()

if __name__ == "__main__":
    main()