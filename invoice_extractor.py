import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import PyPDF2
import json
import re
from datetime import datetime
import openai
from typing import Dict, List, Optional

# Initialize OpenAI API key
openai.api_key = st.secrets["OPENAI_API_KEY_Invoice"]

# Constants from secrets
TREE_ABSORPTION_RATE = st.secrets["emissions"]["TREE_ABSORPTION_RATE"]
CAR_EMISSIONS_PER_KM = st.secrets["emissions"]["CAR_EMISSIONS_PER_KM"]
HOME_ANNUAL_EMISSIONS = st.secrets["emissions"]["HOME_ANNUAL_EMISSIONS"]

ELECTRICITY_FACTORS = {
    int(year): factor 
    for year, factor in st.secrets["conversion_factors"]["ELECTRICITY_FACTORS"].items()
}

GAS_FACTORS = {
    int(year): factor 
    for year, factor in st.secrets["conversion_factors"]["GAS_FACTORS"].items()
}



# Constants
MAX_FILES = 5



class InvoiceProcessor:
    @staticmethod
    def redact_sensitive_data(text: str) -> str:
        """Redact sensitive information from text."""
        patterns = {
            'email': r'\b[\w\.-]+@[\w\.-]+\.\w+\b',
            'uk_phone': r'\b(?:(?:\+44|0)\s?\d{4}\s?\d{6}|\d{3}[-\.\s]?\d{4}[-\.\s]?\d{4})\b',
            'postcode': r'\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b',
            'account_number': r'\b\d{8,12}\b',
            'sort_code': r'\b\d{2}[-\s]?\d{2}[-\s]?\d{2}\b',
            'address': r'\d+\s+[A-Za-z\s]+(?:Road|Street|Ave|Avenue|Close|Lane|Drive|Rd|St|Ave)\b',
            'credit_card': r'\b(?:\d[ -]*?){13,16}\b',
            'national_insurance': r'\b[A-CEGHJ-PR-TW-Z]{1}[A-CEGHJ-NPR-TW-Z]{1}[0-9]{6}[A-DFM]{1}\b',
            'company_number': r'\b\d{8}\b'
        }
        redacted_text = text
        for key, pattern in patterns.items():
            redacted_text = re.sub(pattern, f'[{key.upper()}_REDACTED]', redacted_text, flags=re.IGNORECASE)
        return redacted_text

    @staticmethod
    def extract_invoice_data(text: str, energy_type: str) -> Dict:
        """Extract data using OpenAI API with enhanced error handling."""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a precise invoice data extraction assistant. 
                        Extract the following from {energy_type} invoices and return ONLY a valid JSON object:
                        - Total kWh usage (sum of day and night if applicable)
                        - Billing period dates
                        - Provider name"""
                    },
                    {
                        "role": "user",
                        "content": f"""Extract these fields from the invoice and return them in this exact JSON format:
                        {{
                            "kwh": <number>,
                            "billing_period_start": "DD/MM/YYYY",
                            "billing_period_end": "DD/MM/YYYY",
                            "provider": "provider_name",
                            "type": "{energy_type}"
                        }}

                        For day/night tariffs, sum the kWh values.
                        Format all dates as DD/MM/YYYY.
                        If any field is not found, use null.

                        Invoice text:
                        {text}"""
                    }
                ],
                temperature=0
            )
            
            content = response.choices[0].message.content.strip()
            st.session_state['last_api_response'] = content
            
            try:
                result = json.loads(content)
                required_fields = ['kwh', 'billing_period_start', 'billing_period_end', 'provider', 'type']
                for field in required_fields:
                    if field not in result:
                        result[field] = energy_type if field == 'type' else None
                return result
            
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON response from OpenAI: {content}")
                return {
                    'kwh': None,
                    'billing_period_start': None,
                    'billing_period_end': None,
                    'provider': None,
                    'type': energy_type
                }
                
        except Exception as e:
            st.error(f"Error processing with OpenAI: {str(e)}")
            return {
                'kwh': None,
                'billing_period_start': None,
                'billing_period_end': None,
                'provider': None,
                'type': energy_type
            }

    @staticmethod
    def process_pdf(uploaded_file, energy_type: str) -> Optional[Dict]:
        """Process PDF, redact sensitive information, and extract data."""
        try:
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = " ".join(page.extract_text() for page in pdf_reader.pages)
            redacted_text = InvoiceProcessor.redact_sensitive_data(text)
            
            if st.session_state.get('debug_mode', False):
                st.text_area("Redacted Text", redacted_text, height=200)
            
            result = InvoiceProcessor.extract_invoice_data(redacted_text, energy_type)
            if result:
                result['filename'] = uploaded_file.name
            return result
            
        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {str(e)}")
            return None

class CarbonCalculator:
    @staticmethod
    def get_factor(year: int, energy_type: str) -> float:
        """Get DEFRA conversion factor for the given year and energy type."""
        return ELECTRICITY_FACTORS.get(year) if energy_type == 'electricity' else GAS_FACTORS.get(year)

    @staticmethod
    def calculate_metrics(df: pd.DataFrame) -> Dict:
        """Calculate carbon emissions and related metrics for gas and electricity."""
        df['year'] = pd.to_datetime(df['billing_period_start']).dt.year
        df['carbon_factor'] = df.apply(lambda x: CarbonCalculator.get_factor(x['year'], x['type']), axis=1)
        df['emissions_kg'] = df['kwh'] * df['carbon_factor']
        df['emissions_tonnes'] = df['emissions_kg'] / 1000

        # Calculate year-over-year changes
        df['year_month'] = pd.to_datetime(df['billing_period_start']).dt.to_period('M')
        yoy_changes = df.groupby(['type', df['billing_period_start'].dt.year]).agg({
            'kwh': ['sum', 'mean'],
            'emissions_tonnes': ['sum', 'mean']
        }).pct_change()

        # Scope emissions calculations
        scope1_emissions = df[df['type'] == 'gas']['emissions_tonnes'].sum()
        scope2_emissions = df[df['type'] == 'electricity']['emissions_tonnes'].sum()
        total_emissions_tonnes = scope1_emissions + scope2_emissions

        return {
            'total_emissions_tonnes': total_emissions_tonnes,
            'scope1_emissions_tonnes': scope1_emissions,
            'scope2_emissions_tonnes': scope2_emissions,
            'yoy_changes': yoy_changes
        }

    @staticmethod
    def set_reduction_targets(baseline_emissions: float) -> Dict:
        """Set science-based reduction targets."""
        yearly_reduction = 0.045  # 4.5% annual reduction (Science Based Targets initiative)
        target_years = range(1, 6)  # 5-year projection
        
        return {
            year: baseline_emissions * (1 - yearly_reduction) ** year
            for year in target_years
        }

class Dashboard:
    def __init__(self):
        self.chart_type = st.sidebar.selectbox(
            "Select Chart Type",
            ["Line Chart", "Bar Chart", "Area Chart"]
        )
        self.color_scheme = {
            'electricity': '#1f77b4',
            'gas': '#ff7f0e'
        }

    def create_usage_chart(self, df: pd.DataFrame):
        """Generate energy usage trend chart."""
        fig = go.Figure()
        
        for energy_type in df['type'].unique():
            type_df = df[df['type'] == energy_type]
            
            # Main usage line
            fig.add_trace(go.Scatter(
                x=type_df['billing_period_start'],
                y=type_df['kwh'],
                name=f"{energy_type.capitalize()} Usage",
                mode='lines+markers',
                line=dict(color=self.color_scheme[energy_type])
            ))
            
            # Add moving average
            type_df['MA3'] = type_df['kwh'].rolling(window=3).mean()
            fig.add_trace(go.Scatter(
                x=type_df['billing_period_start'],
                y=type_df['MA3'],
                name=f"{energy_type.capitalize()} 3-Month MA",
                line=dict(
                    dash='dash',
                    color=self.color_scheme[energy_type]
                )
            ))
        
        fig.update_layout(
            title='Energy Usage Trend with Moving Average',
            xaxis_title='Date',
            yaxis_title='Usage (kWh)',
            hovermode='x unified',
            showlegend=True
        )
        return fig

    def create_emissions_charts(self, df: pd.DataFrame):
        """Create emissions-related visualizations."""
        # Monthly emissions trend
        emissions_trend = go.Figure()
        
        for energy_type in df['type'].unique():
            type_df = df[df['type'] == energy_type]
            emissions_trend.add_trace(go.Scatter(
                x=type_df['billing_period_start'],
                y=type_df['emissions_tonnes'],
                name=f"{energy_type.capitalize()} Emissions",
                mode='lines+markers',
                line=dict(color=self.color_scheme[energy_type])
            ))
        
        emissions_trend.update_layout(
            title='Monthly Carbon Emissions',
            xaxis_title='Date',
            yaxis_title='Emissions (tCO2e)',
            hovermode='x unified'
        )

        # Usage vs Emissions scatter plot
        emissions_vs_usage = go.Figure()
        
        for energy_type in df['type'].unique():
            type_df = df[df['type'] == energy_type]
            emissions_vs_usage.add_trace(go.Scatter(
                x=type_df['kwh'],
                y=type_df['emissions_tonnes'],
                name=f"{energy_type.capitalize()}",
                mode='markers',
                marker=dict(color=self.color_scheme[energy_type])
            ))
        
        emissions_vs_usage.update_layout(
            title='Energy Usage vs Carbon Emissions',
            xaxis_title='Energy Usage (kWh)',
            yaxis_title='Emissions (tCO2e)',
            hovermode='closest'
        )

        return emissions_trend, emissions_vs_usage

    def display_monthly_comparison(self, df: pd.DataFrame):
        """Display monthly usage and emissions comparison."""
        monthly_df = df.copy()
        monthly_df['month_year'] = monthly_df['billing_period_start'].dt.strftime('%B %Y')
        
        st.subheader("Monthly Comparison by Energy Type")

        # Create monthly comparison chart
        fig = go.Figure()
        
        for energy_type in df['type'].unique():
            type_df = monthly_df[monthly_df['type'] == energy_type]
            fig.add_trace(go.Bar(
                x=type_df['month_year'],
                y=type_df['kwh'],
                name=f"{energy_type.capitalize()} Usage",
                marker_color=self.color_scheme[energy_type]
            ))
        
        fig.update_layout(
            title='Monthly Energy Usage Comparison',
            xaxis_title='Month',
            yaxis_title='Usage (kWh)',
            barmode='group',
            xaxis={'tickangle': 45}
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # Monthly statistics by energy type
        for energy_type in ['electricity', 'gas']:
            type_df = monthly_df[monthly_df['type'] == energy_type]
            
            st.subheader(f"{energy_type.capitalize()} Monthly Statistics")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    "Average Monthly Usage",
                    f"{type_df['kwh'].mean():,.0f} kWh"
                )
            with col2:
                st.metric(
                    "Average Monthly Emissions",
                    f"{type_df['emissions_tonnes'].mean():,.2f} tCO2e"
                )

    def display_environmental_impact(self, df: pd.DataFrame):
        """Display environmental impact metrics."""
        total_emissions = df['emissions_tonnes'].sum()
        
        trees_needed = int(total_emissions / TREE_ABSORPTION_RATE)
        car_km = int(df['emissions_kg'].sum() / CAR_EMISSIONS_PER_KM)
        homes_equivalent = int(total_emissions / HOME_ANNUAL_EMISSIONS)

        # Display key metrics
        st.subheader("Environmental Impact")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Trees Needed for Offset", f"{trees_needed:,d}")
            st.markdown(f"🌳 Equivalent to planting {trees_needed:,d} trees")
        
        with col2:
            st.metric("Car Travel Equivalent", f"{car_km:,d} km")
            st.markdown(f"🚗 Equal to driving {car_km:,d} kilometers")
        
        with col3:
            st.metric("Home Energy Equivalent", f"{homes_equivalent:,d}")
            st.markdown(f"🏠 Equal to {homes_equivalent:,d} homes' annual usage")

        # Display emissions breakdown
        st.subheader("Emissions Breakdown")
        
        # Create pie chart for emissions by type
        emissions_by_type = df.groupby('type')['emissions_tonnes'].sum()
        
        fig = go.Figure(data=[go.Pie(
            labels=emissions_by_type.index,
            values=emissions_by_type.values,
            hole=.3,
            marker_colors=['#1f77b4', '#ff7f0e']
        )])
        
        fig.update_layout(
            title='Emissions Distribution by Energy Type',
            showlegend=True
        )
        
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate="Energy Type: %{label}<br>Emissions: %{value:.1f} tCO2e<br>Percentage: %{percent}"
        )
        
        st.plotly_chart(fig, use_container_width=True)

    def display_reduction_targets(self, carbon_metrics: Dict):
        """Display emission reduction targets and progress."""
        baseline_emissions = carbon_metrics['total_emissions_tonnes']
        targets = CarbonCalculator.set_reduction_targets(baseline_emissions)
        
        st.subheader("Emission Reduction Targets")
        
        # Create target visualization
        fig = go.Figure()
        
        # Current emissions
        fig.add_trace(go.Scatter(
            x=[0],
            y=[baseline_emissions],
            mode='markers',
            name='Current Emissions',
            marker=dict(size=15, color='#1f77b4')
        ))
        
        # Target line
        years = list(targets.keys())
        emissions = list(targets.values())
        fig.add_trace(go.Scatter(
            x=years,
            y=emissions,
            mode='lines+markers',
            name='Reduction Targets',
            line=dict(dash='dash', color='#ff7f0e')
        ))
        
        fig.update_layout(
            title='5-Year Emission Reduction Targets',
            xaxis_title='Years from Now',
            yaxis_title='Emissions (tCO2e)',
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display target table
        target_df = pd.DataFrame({
            'Year': [datetime.now().year + year for year in years],
            'Target Emissions (tCO2e)': emissions,
            'Required Reduction (tCO2e)': [baseline_emissions - e for e in emissions],
            'Reduction Percentage': [(baseline_emissions - e) / baseline_emissions * 100 for e in emissions]
        })
        
        st.dataframe(target_df.round(2))
    def display_dashboard(self, df: pd.DataFrame, carbon_metrics: Dict):
        """Display dashboard metrics, charts, and recommendations."""
        st.header("Energy & Carbon Dashboard")
        
        # Top-level metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Total Carbon Emissions",
                f"{carbon_metrics['total_emissions_tonnes']:,.1f} tCO2e"
            )
        with col2:
            st.metric(
                "Total Electricity Usage",
                f"{df[df['type'] == 'electricity']['kwh'].sum():,.0f} kWh"
            )
        with col3:
            st.metric(
                "Total Gas Usage",
                f"{df[df['type'] == 'gas']['kwh'].sum():,.0f} kWh"
            )

        # Display metrics for each energy type
        for energy_type in ["electricity", "gas"]:
            type_df = df[df['type'] == energy_type]
            st.subheader(f"{energy_type.capitalize()} Metrics")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Usage", f"{type_df['kwh'].sum():,.0f} kWh")
            with col2:
                st.metric("Average Monthly", f"{type_df['kwh'].mean():,.0f} kWh")
            with col3:
                st.metric("Highest Month", f"{type_df['kwh'].max():,.0f} kWh")

        # Display emissions metrics
        st.subheader("Emissions Breakdown")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Scope 1 Emissions (Gas)", f"{carbon_metrics['scope1_emissions_tonnes']:,.1f} tCO2e")
        with col2:
            st.metric("Scope 2 Emissions (Electricity)", f"{carbon_metrics['scope2_emissions_tonnes']:,.1f} tCO2e")

        # Create tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Usage & Emissions",
            "Monthly Comparison",
            "Environmental Impact",
            "Reduction Targets",
            "Raw Data"
        ])
        
        with tab1:
            st.plotly_chart(self.create_usage_chart(df), use_container_width=True)
            emissions_trend, emissions_vs_usage = self.create_emissions_charts(df)
            st.plotly_chart(emissions_trend, use_container_width=True)
            st.plotly_chart(emissions_vs_usage, use_container_width=True)

        with tab2:
            self.display_monthly_comparison(df)

        with tab3:
            self.display_environmental_impact(df)

        with tab4:
            self.display_reduction_targets(carbon_metrics)

        with tab5:
            self.display_raw_data(df)

    def display_raw_data(self, df: pd.DataFrame):
        """Display raw data with enhanced filtering and download options."""
        st.subheader("Raw Data Analysis")
        
        # Add filters
        energy_type = st.selectbox("Filter by Energy Type", ['All'] + list(df['type'].unique()))
        date_range = st.date_input(
            "Select Date Range",
            [df['billing_period_start'].min(), df['billing_period_start'].max()]
        )
        
        # Filter data
        filtered_df = df.copy()
        if energy_type != 'All':
            filtered_df = filtered_df[filtered_df['type'] == energy_type]
        filtered_df = filtered_df[
            (filtered_df['billing_period_start'].dt.date >= date_range[0]) &
            (filtered_df['billing_period_start'].dt.date <= date_range[1])
        ]
        
        # Display data
        st.dataframe(
            filtered_df[[
                'filename', 'billing_period_start', 'kwh',
                'emissions_tonnes', 'carbon_factor', 'type'
            ]].round(2)
        )
        
        # Download options
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Filtered Data (CSV)",
            data=csv,
            file_name="energy_data.csv",
            mime="text/csv"
        )   
    def display_raw_data(self, df: pd.DataFrame):
        """Display raw data with enhanced filtering and download options."""
        st.subheader("Raw Data Analysis")
        
        # Add filters
        energy_type = st.selectbox("Filter by Energy Type", ['All'] + list(df['type'].unique()))
        date_range = st.date_input(
            "Select Date Range",
            [df['billing_period_start'].min(), df['billing_period_start'].max()]
        )
        
        # Filter data
        filtered_df = df.copy()
        if energy_type != 'All':
            filtered_df = filtered_df[filtered_df['type'] == energy_type]
        filtered_df = filtered_df[
            (filtered_df['billing_period_start'].dt.date >= date_range[0]) &
            (filtered_df['billing_period_start'].dt.date <= date_range[1])
        ]
        
        # Display data
        st.dataframe(
            filtered_df[[
                'filename', 'billing_period_start', 'kwh',
                'emissions_tonnes', 'carbon_factor', 'type'
            ]].round(2)
        )
        
        # Download options
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Filtered Data (CSV)",
            data=csv,
            file_name="energy_data.csv",
            mime="text/csv"
        )

def validate_data(df: pd.DataFrame) -> Dict:
    """Validate input data for common issues."""
    validation_results = {
        'missing_values': df.isnull().sum().to_dict(),
        'negative_values': (df['kwh'] < 0).sum(),
        'future_dates': (df['billing_period_start'] > datetime.now()).sum(),
        'duplicates': df.duplicated().sum()
    }
    return validation_results

def load_sample_data() -> List[Dict]:
    """Load sample data for demonstration."""
    sample_data = []
    start_date = datetime.now().replace(day=1) - pd.DateOffset(months=12)
    
    # Define seasonal patterns
    electricity_patterns = [
        12000, 11500, 11000, 10500,  # Winter/Spring
        10000, 9500, 9000, 8500,     # Spring/Summer
        8000, 8500, 9000, 9500       # Summer/Fall
    ]
    
    gas_patterns = [
        7000, 7500, 7200, 7100,      # Winter/Spring
        7000, 6900, 6800, 6700,      # Spring/Summer
        6600, 6700, 6800, 6900       # Summer/Fall
    ]
    
    for i in range(12):
        date = start_date + pd.DateOffset(months=i)
        
        # Electricity data
        sample_data.append({
            'filename': f'sample_electricity_{i+1}',
            'kwh': electricity_patterns[i],
            'billing_period_start': date.strftime('%d/%m/%Y'),
            'billing_period_end': (date + pd.DateOffset(months=1) - pd.DateOffset(days=1)).strftime('%d/%m/%Y'),
            'type': 'electricity'
        })
        
        # Gas data
        sample_data.append({
            'filename': f'sample_gas_{i+1}',
            'kwh': gas_patterns[i],
            'billing_period_start': date.strftime('%d/%m/%Y'),
            'billing_period_end': (date + pd.DateOffset(months=1) - pd.DateOffset(days=1)).strftime('%d/%m/%Y'),
            'type': 'gas'
        })
    
    return sample_data

def main():
    st.set_page_config(page_title="Energy & Carbon Dashboard", page_icon="⚡",layout="wide")
    st.title("Energy & Carbon Dashboard")
    
    # Add settings to sidebar
    with st.sidebar:
        st.header("Settings")
        st.session_state['debug_mode'] = st.checkbox("Debug Mode", False)
    
    input_method = st.radio(
        "Select Input Method",
        ["Upload Invoices", "Manual Input", "Sample Data"],
        horizontal=True
    )
    
    dashboard = Dashboard()

    if input_method == "Upload Invoices":
        st.write("Upload your energy invoices to analyze usage and carbon emissions.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Electricity Invoices")
            electricity_files = st.file_uploader(
                "Choose Electricity PDF files",
                type="pdf",
                accept_multiple_files=True,
                key="electricity_files"
            )
            
        with col2:
            st.subheader("Gas Invoices")
            gas_files = st.file_uploader(
                "Choose Gas PDF files",
                type="pdf",
                accept_multiple_files=True,
                key="gas_files"
            )

        if electricity_files or gas_files:
            data = []
            
            # Process electricity invoices
            if electricity_files:
                for file in electricity_files:
                    result = InvoiceProcessor.process_pdf(file, 'electricity')
                    if result:
                        data.append(result)
            
            # Process gas invoices
            if gas_files:
                for file in gas_files:
                    result = InvoiceProcessor.process_pdf(file, 'gas')
                    if result:
                        data.append(result)

            if data:
                df = pd.DataFrame(data)
                df['billing_period_start'] = pd.to_datetime(df['billing_period_start'], format='%d/%m/%Y')
                df['billing_period_end'] = pd.to_datetime(df['billing_period_end'], format='%d/%m/%Y')
                df = df.sort_values('billing_period_start')
                
                # Validate data
                validation_results = validate_data(df)
                if st.session_state.get('debug_mode', False):
                    st.write("Data Validation Results:", validation_results)
                
                carbon_metrics = CarbonCalculator.calculate_metrics(df)
                dashboard.display_dashboard(df, carbon_metrics)

    elif input_method == "Manual Input":
        st.write("Enter your monthly electricity and gas usage data:")
        
        manual_data = []
        n_months = st.number_input("Number of months to enter", min_value=1, max_value=24, value=12)
        
        for i in range(n_months):
            st.subheader(f"Month {i+1}")
            col1, col2 = st.columns(2)
            
            month_date = st.date_input(f"Select Date for Month {i+1}", key=f"date_{i}")
            
            with col1:
                st.write("Electricity Usage")
                elec_kwh = st.number_input(
                    "Electricity Usage (kWh)",
                    min_value=0.0,
                    value=0.0,
                    key=f"elec_kwh_{i}"
                )
                
            with col2:
                st.write("Gas Usage")
                gas_kwh = st.number_input(
                    "Gas Usage (kWh)",
                    min_value=0.0,
                    value=0.0,
                    key=f"gas_kwh_{i}"
                )
            
            if elec_kwh > 0:
                manual_data.append({
                    'filename': f'manual_electricity_{i+1}',
                    'kwh': elec_kwh,
                    'billing_period_start': month_date,
                    'billing_period_end': month_date + pd.DateOffset(months=1) - pd.DateOffset(days=1),
                    'type': 'electricity'
                })
            
            if gas_kwh > 0:
                manual_data.append({
                    'filename': f'manual_gas_{i+1}',
                    'kwh': gas_kwh,
                    'billing_period_start': month_date,
                    'billing_period_end': month_date + pd.DateOffset(months=1) - pd.DateOffset(days=1),
                    'type': 'gas'
                })

        if st.button("Generate Dashboard") and manual_data:
            df = pd.DataFrame(manual_data)
            df['billing_period_start'] = pd.to_datetime(df['billing_period_start'])
            df['billing_period_end'] = pd.to_datetime(df['billing_period_end'])
            carbon_metrics = CarbonCalculator.calculate_metrics(df)
            dashboard.display_dashboard(df, carbon_metrics)

    else:  # Sample Data
        sample_data = load_sample_data()
        df = pd.DataFrame(sample_data)
        df['billing_period_start'] = pd.to_datetime(df['billing_period_start'], format='%d/%m/%Y')
        df['billing_period_end'] = pd.to_datetime(df['billing_period_end'], format='%d/%m/%Y')
        df = df.sort_values('billing_period_start')
        
        carbon_metrics = CarbonCalculator.calculate_metrics(df)
        dashboard.display_dashboard(df, carbon_metrics)

if __name__ == "__main__":
    main()

