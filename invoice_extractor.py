import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import streamlit.components.v1 as components
import random
import numpy as np
import base64
import io

# --- CONSTANTS ---
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

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Council Carbon Dashboard",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SESSION STATE INITIALISATION ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'landing'

if 'data_entries' not in st.session_state:
    st.session_state.data_entries = []

if 'demo_mode' not in st.session_state:
    st.session_state.demo_mode = False

if 'entry_mode' not in st.session_state:
    st.session_state.entry_mode = None

# --- NAVIGATION AND STATE FUNCTIONS ---
def navigate_to(page):
    st.session_state.current_page = page

def toggle_demo_mode():
    st.session_state.demo_mode = not st.session_state.demo_mode
    if st.session_state.demo_mode:
        load_demo_data()
    else:
        # Clear data when exiting demo mode
        st.session_state.data_entries = []

def load_demo_data():
    """Generate realistic sample data for demonstration"""
    st.session_state.data_entries = []
    
    start_date = datetime(2024, 1, 1)
    
    # Realistic patterns with seasonal variation
    elec_pattern = [12500, 11800, 10500, 9200, 8500, 8000, 8200, 8500, 9000, 10000, 11200, 12000]
    gas_pattern = [8000, 7500, 6500, 5000, 3500, 2500, 2000, 2200, 3000, 4500, 6500, 7800]
    
    for month in range(12):
        current_date = start_date.replace(month=month+1)
        
        # Add realistic random variation
        elec_variation = random.uniform(0.92, 1.08)
        gas_variation = random.uniform(0.9, 1.1)
        
        elec_kwh = elec_pattern[month] * elec_variation
        gas_kwh = gas_pattern[month] * gas_variation
        
        year = current_date.year
        emissions = calculate_emissions(elec_kwh, gas_kwh, year)
        
        entry = {
            "month": current_date.strftime("%B %Y"),
            "electricity_kwh": elec_kwh,
            "electricity_provider": "Council Energy Provider",
            "gas_kwh": gas_pattern[month] * gas_variation,
            "gas_provider": "Council Gas Provider",
            "electricity_emissions_kg": emissions["electricity_emissions_kg"],
            "gas_emissions_kg": emissions["gas_emissions_kg"],
            "total_emissions_tonnes": emissions["total_emissions_tonnes"]
        }
        
        st.session_state.data_entries.append(entry)

# --- CSV DOWNLOAD FUNCTION ---
def get_csv_download_link(df, filename="council_carbon_data.csv", text="Download CSV"):
    """Generate a link to download the dataframe as a CSV file"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}" class="download-button">{text}</a>'
    return href

# --- STYLING ---
def load_css():
    """Load simplified CSS with better contrast for light mode"""
    st.markdown("""
    <style>
        /* Basic Typography */
        h1, h2, h3, h4, h5 {
            color: #222;
            margin-top: 0.5em;
            margin-bottom: 0.5em;
        }
        
        p, li {
            color: #333;
        }
        
        /* Main Banner */
        .prototype-banner {
            background-color: #ff9800;
            color: #000;
            padding: 8px;
            text-align: center;
            font-weight: bold;
            position: sticky;
            top: 0;
            z-index: 1000;
            font-size: 0.9rem;
        }
        
        /* Scope badges for emissions types */
        .scope-badge {
            display: inline-block;
            padding: 3px 6px;
            border-radius: 3px;
            font-size: 0.8rem;
            font-weight: bold;
            margin-right: 6px;
        }
        
        .scope1-badge {
            background-color: #e57373;
            color: white;
        }
        
        .scope2-badge {
            background-color: #4eca8b;
            color: white;
        }
        
        /* Card styling */
        .card {
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        /* Feature cards */
        .feature-card {
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 16px;
            text-align: center;
            height: 100%;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        /* Hero section */
        .hero-section {
            background: linear-gradient(120deg, #1E8449 0%, #2E86C1 100%);
            padding: 32px 24px;
            border-radius: 8px;
            margin-bottom: 24px;
            text-align: center;
        }
        
        .hero-section h1 {
            color: white;
            font-size: 2.5rem;
            margin-bottom: 16px;
        }
        
        .hero-section p {
            color: white;
            font-size: 1.2rem;
            margin-bottom: 16px;
        }
        
        /* Facts cards */
        .facts-card {
            background-color: #f8f9fa;
            border-left: 3px solid #2E86C1;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        }
        
        .facts-card h3 {
            color: #222;
        }
        
        .facts-card ul {
            color: #333;
        }
        
        /* Metric cards */
        .metric-card {
            background-color: white;
            border-top: 3px solid #2E86C1;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 16px;
            text-align: center;
            margin-bottom: 16px;
        }
        
        .metric-value {
            font-size: 2.2rem;
            font-weight: bold;
            color: #2E86C1;
            margin-bottom: 8px;
        }
        
        .metric-label {
            font-size: 1rem;
            color: #333;
            font-weight: 500;
        }
        
        /* Premium elements */
        .premium-badge {
            display: inline-block;
            background-color: #ffc107;
            color: #212529;
            padding: 4px 8px;
            border-radius: 4px;
            margin-left: 8px;
            font-size: 0.8rem;
            font-weight: bold;
        }
        
        /* Contact section */
        .contact-section {
            background: #f8f9fa;
            padding: 24px;
            border-radius: 8px;
            margin: 24px 0;
            border: 2px solid #1E8449;
        }
        
        /* Download button */
        .download-button {
            display: inline-block;
            background-color: #1E8449;
            color: white;
            padding: 8px 16px;
            text-align: center;
            border-radius: 4px;
            text-decoration: none;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .download-button:hover {
            background-color: #166938;
            color: white;
        }
    </style>
    """, unsafe_allow_html=True)

# --- UTILITY FUNCTIONS ---
def add_prototype_banner():
    """Add a sticky prototype notice banner"""
    st.markdown("""
    <div class="prototype-banner">
        PROTOTYPE VERSION — DATA WILL NOT BE SAVED
    </div>
    """, unsafe_allow_html=True)

def add_data_disclaimer():
    """Add data disclaimer message"""
    st.warning("⚠️ PROTOTYPE: This is a demonstration version. No data will be saved or stored when you close the app.")

# --- CALCULATION FUNCTIONS ---
def calculate_emissions(electricity_kwh, gas_kwh, year):
    """Calculate carbon emissions based on energy usage"""
    # Get conversion factors for the specified year
    electricity_factor = ELECTRICITY_FACTORS.get(year, list(ELECTRICITY_FACTORS.values())[-1])
    gas_factor = GAS_FACTORS.get(year, list(GAS_FACTORS.values())[-1])
    
    # Calculate emissions
    electricity_emissions_kg = electricity_kwh * electricity_factor
    gas_emissions_kg = gas_kwh * gas_factor
    
    total_emissions_kg = electricity_emissions_kg + gas_emissions_kg
    total_emissions_tonnes = total_emissions_kg / 1000
    
    return {
        "electricity_emissions_kg": electricity_emissions_kg,
        "gas_emissions_kg": gas_emissions_kg,
        "total_emissions_tonnes": total_emissions_tonnes
    }

# --- CONTACT FORM ---
def show_contact_us_form():
    """Display contact form"""
    st.markdown("""
    <div class="contact-section">
        <h2 style="text-align: center; margin-top: 0;">Contact Us</h2>
        <p style="text-align: center; margin-bottom: 1.5rem;">
            Complete our brief questionnaire to learn more about our carbon reporting solutions and premium features.
        </p>
    """, unsafe_allow_html=True)
    
    # Embed Google Form
    google_form_html = """
    <iframe src="https://docs.google.com/forms/d/e/1FAIpQLSfwzklepnKExPn6Skhy_e74wEgrQy3iiXHvPg82Y03maIUeQg/viewform?embedded=true" 
            width="100%" height="800" frameborder="0" marginheight="0" marginwidth="0">
        Loading…
    </iframe>
    """
    
    components.html(google_form_html, height=850)
    st.markdown("</div>", unsafe_allow_html=True)

# --- EMISSIONS INFO ---
def explain_emissions_scope():
    """Explain what emissions are tracked"""
    st.markdown("""
    <div class="card">
        <h3>Current Emissions Coverage</h3>
        <p>This dashboard currently focuses on the most critical emissions sources for councils:</p>
        <p>
            <span class="scope-badge scope1-badge">SCOPE 1</span> Direct emissions from owned sources including gas for heating council buildings
        </p>
        <p>
            <span class="scope-badge scope2-badge">SCOPE 2</span> Indirect emissions from purchased electricity for buildings and street lighting
        </p>
        <p><strong>Coming Soon:</strong> Fleet vehicle emissions tracking, business travel, and additional reporting options.</p>
    </div>
    """, unsafe_allow_html=True)

# --- COUNCIL BENEFITS ---
def show_council_benefits():
    """Show why councils need this tool"""
    st.markdown("<h2 style='text-align: center; margin: 1rem 0;'>Why Your Council Needs This Tool</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="card">
            <h3>Mandatory Compliance</h3>
            <ul>
                <li>Meet SECR requirements for councils with over 250 employees</li>
                <li>Track progress on your climate emergency declaration commitments</li>
                <li>Generate ready-to-submit regulatory reports</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="card">
            <h3>Save 15+ Hours Monthly</h3>
            <ul>
                <li>Automated calculations using latest DEFRA factors</li>
                <li>No more complex spreadsheets or manual calculations</li>
                <li>Quick dashboard updates when data changes</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="card">
            <h3>Unlock Grant Funding</h3>
            <ul>
                <li>Clear progress metrics for funding applications</li>
                <li>Evidence for decarbonisation project grants</li>
                <li>Demonstrate ROI on sustainability initiatives</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# --- DASHBOARD COMPONENTS ---
def show_dashboard_metrics(df):
    """Display key dashboard metrics"""
    # Calculate totals
    total_electricity = df["electricity_kwh"].sum()
    total_gas = df["gas_kwh"].sum()
    electricity_emissions = df["electricity_emissions_kg"].sum() / 1000
    gas_emissions = df["gas_emissions_kg"].sum() / 1000
    total_emissions = df["total_emissions_tonnes"].sum()
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_emissions:.2f}</div>
            <div class="metric-label">Total Carbon Emissions (tCO₂e)</div>
            <p style="margin-top: 0.5rem; font-size: 0.8rem;">Scope 1 & 2 combined</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{electricity_emissions:.2f}</div>
            <div class="metric-label">Electricity Emissions (tCO₂e)</div>
            <p style="margin-top: 0.5rem; font-size: 0.8rem;"><span class="scope-badge scope2-badge">SCOPE 2</span> {total_electricity:,.0f} kWh</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{gas_emissions:.2f}</div>
            <div class="metric-label">Gas Emissions (tCO₂e)</div>
            <p style="margin-top: 0.5rem; font-size: 0.8rem;"><span class="scope-badge scope1-badge">SCOPE 1</span> {total_gas:,.0f} kWh</p>
        </div>
        """, unsafe_allow_html=True)

def create_usage_chart(dashboard_df):
    """Create energy usage chart"""
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
        marker_color="#4eca8b"  # Same as scope2-badge
    ))
    
    # Add gas data
    fig.add_trace(go.Bar(
        x=dashboard_df["month"],
        y=dashboard_df["Gas"],
        name="Gas (kWh)",
        marker_color="#e57373"  # Same as scope1-badge
    ))
    
    # Add trend line if enough data
    if len(dashboard_df) >= 3:
        fig.add_trace(go.Scatter(
            x=dashboard_df["month"],
            y=dashboard_df["Electricity"].rolling(3, min_periods=1).mean(),
            name="Electricity 3-Month Average",
            line=dict(color="#4eca8b", dash="dash")
        ))
    
    fig.update_layout(
        title="Monthly Energy Usage",
        xaxis_title="Month",
        yaxis_title="Usage (kWh)",
        legend_title="Energy Type",
        hovermode="x unified",
        barmode="group"
    )
    
    return fig

def create_emissions_chart(dashboard_df):
    """Create emissions chart"""
    fig = go.Figure()
    
    # Add electricity emissions
    fig.add_trace(go.Scatter(
        x=dashboard_df["month"],
        y=dashboard_df["Electricity Emissions"],
        name="Electricity (tCO₂e)",
        mode="lines+markers",
        line=dict(color="#4eca8b", width=3),  # Same as scope2-badge
        marker=dict(size=8)
    ))
    
    # Add gas emissions
    fig.add_trace(go.Scatter(
        x=dashboard_df["month"],
        y=dashboard_df["Gas Emissions"],
        name="Gas (tCO₂e)",
        mode="lines+markers",
        line=dict(color="#e57373", width=3),  # Same as scope1-badge
        marker=dict(size=8)
    ))
    
    # Add total emissions
    fig.add_trace(go.Scatter(
        x=dashboard_df["month"],
        y=dashboard_df["Electricity Emissions"] + dashboard_df["Gas Emissions"],
        name="Total Emissions (tCO₂e)",
        mode="lines",
        line=dict(color="#2E86C1", width=4, dash="dot")
    ))
    
    fig.update_layout(
        title="Monthly Carbon Emissions",
        xaxis_title="Month",
        yaxis_title="Emissions (tCO₂e)",
        legend_title="Source",
        hovermode="x unified"
    )
    
    return fig

def create_emissions_pie_chart(df):
    """Create emissions breakdown pie chart"""
    emissions_data = [
        df["electricity_emissions_kg"].sum() / 1000,
        df["gas_emissions_kg"].sum() / 1000
    ]
    
    fig = px.pie(
        values=emissions_data,
        names=["Electricity", "Gas"],
        title="Emissions Breakdown by Source",
        color_discrete_sequence=["#4eca8b", "#e57373"],  # Match scope badge colours
        hole=0.4
    )
    
    fig.update_traces(textinfo='percent+label')
    
    return fig

def show_environmental_impact(total_emissions):
    """Show environmental impact metrics"""
    st.subheader("Environmental Impact")
    
    # Calculate impact metrics
    trees_needed = int(total_emissions / TREE_ABSORPTION_RATE)
    car_km = int((total_emissions * 1000) / CAR_EMISSIONS_PER_KM)
    homes_equivalent = int(total_emissions / HOME_ANNUAL_EMISSIONS)
    
    # Display impact cards
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

# --- PAGES ---
def landing_page():
    """Display landing page"""
    # Hero Section
    st.markdown("""
    <div class="hero-section">
        <h1>Council Carbon Reporting Made Simple</h1>
        <p>Track, analyse, and report your council's carbon emissions using DEFRA standards</p>
        <p style="font-size: 0.9rem; background: rgba(0,0,0,0.2); padding: 0.5rem; border-radius: 0.3rem;">
            Prototype Version: For demonstration only. No data will be saved.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Council benefits
    show_council_benefits()
    
    # Emissions scope explanation
    explain_emissions_scope()
    
    # How it works section
    st.markdown("<h2 style='text-align: center; margin: 2rem 0 1.5rem;'>How It Works</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <h3>1. Input Your Data</h3>
            <p>Enter energy consumption manually or upload your invoices</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <h3>2. We Calculate Emissions</h3>
            <p>Automatic calculation using current DEFRA factors</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <h3>3. Get Instant Reports</h3>
            <p>Clear dashboards ready for meetings and reports</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Features comparison
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
                    <li>Multi-site analysis</li>
                </ul>
                <p style="margin-top: 1rem;"><strong>Complete our questionnaire to opt in for premium features</strong></p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Contact form
    show_contact_us_form()

def data_entry_page():
    """Display data entry page"""
    st.markdown("<h1>Carbon Data Dashboard</h1>", unsafe_allow_html=True)
    
    # Show prototype warning
    add_data_disclaimer()
    
    # Demo mode toggle
    demo_col1, demo_col2 = st.columns([3, 1])
    with demo_col2:
        if st.button(
            "View Demo Data" if not st.session_state.demo_mode else "Clear Demo Data", 
            use_container_width=True
        ):
            toggle_demo_mode()
            st.rerun()
    
    # Show no data message if needed
    if not st.session_state.demo_mode and not st.session_state.data_entries:
        st.info("No data available. Click 'View Demo Data' to see sample council energy data.")
        
        # Show data entry options
        st.markdown("<h2 style='margin-top: 2rem;'>Enter Your Own Data</h2>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="card">
                <h3>Quick Start: Enter Single Month</h3>
                <p>Add a single month of data to get started quickly.</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Enter Single Month", type="primary", use_container_width=True):
                st.session_state.entry_mode = "single"
                st.rerun()
        
        with col2:
            st.markdown("""
            <div class="card">
                <h3>Complete: Enter Full Year</h3>
                <p>Input data for multiple months to see detailed trends.</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Enter Multiple Months", type="primary", use_container_width=True):
                st.session_state.entry_mode = "multiple"
                st.rerun()
        
        # Premium features note
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("""
                <div class="card">
                    <h3>Premium Features Available <span class="premium-badge">Opt-in</span></h3>
                    <p>Upgrade to access invoice processing, custom reports, data validation and more.</p>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            if st.button("Contact Us", key="contact_us_banner", use_container_width=True):
                navigate_to('contact_us')
                st.rerun()
        

    # Show data entry forms if selected
    if 'entry_mode' in st.session_state and st.session_state.entry_mode is not None:
        if st.session_state.entry_mode == "single":
            show_single_month_form()
        elif st.session_state.entry_mode == "multiple":
            show_multiple_month_form()
    
    # Show dashboard if data exists
    if st.session_state.data_entries:
        if st.session_state.demo_mode:
            st.success("Viewing demo data - This shows 12 months of sample data for a typical council")
        show_dashboard(pd.DataFrame(st.session_state.data_entries))

    # Show contact form
    show_contact_us_form()

def show_single_month_form():
    """Form for entering a single month of data"""
    st.subheader("Enter Energy Data for a Single Month")
    
    # Add explicit prototype warning
    st.warning("⚠️ PROTOTYPE: Any data entered here is for demonstration only and will not be saved.")
    
    with st.form("single_month_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            month = st.date_input("Reporting Month", datetime.now())
            electricity_usage = st.number_input("Electricity Usage (kWh)", min_value=0.0, value=9000.0)
            electricity_provider = st.text_input("Electricity Provider (optional)", "")
        
        with col2:
            gas_usage = st.number_input("Gas Usage (kWh)", min_value=0.0, value=5000.0)
            gas_provider = st.text_input("Gas Provider (optional)", "")
        
        submitted = st.form_submit_button("Save Data", type="primary")
        cancel = st.form_submit_button("Cancel")
        
        if submitted:
            # Calculate emissions
            year = month.year
            emissions = calculate_emissions(electricity_usage, gas_usage, year)
            
            # Create new entry
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
            st.success("Data saved successfully (for this demonstration session only)")
            
            # Reset entry mode
            st.session_state.entry_mode = None
            st.rerun()
                
        if cancel:
            st.session_state.entry_mode = None
            st.rerun()

def show_multiple_month_form():
    """Form for entering multiple months of data"""
    st.subheader("Enter Energy Data for Multiple Months")
    
    # Add explicit prototype warning
    st.warning("⚠️ PROTOTYPE: Any data entered here is for demonstration only and will not be saved.")
    
    # Create tabs for months
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
    st.markdown("<h3>Supplier Information (Optional)</h3>", unsafe_allow_html=True)
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
            year = datetime.now().year
            entries_added = 0
            
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
                    entries_added += 1
            
            st.success(f"Added data for {entries_added} months (for this demonstration session only)")
            
            # Reset entry mode
            st.session_state.entry_mode = None
            st.rerun()

def show_dashboard(df):
    """Display the dashboard with all visualisations"""
    st.markdown("<h2>Carbon Emissions Dashboard</h2>", unsafe_allow_html=True)
    
    # Show sample data notice
    st.info("Sample data shown for demonstration purposes only. All data is temporary and not saved.")
    
    # Create exportable data in proper format
    export_data = pd.DataFrame(st.session_state.data_entries).copy()
    
    # Format export data for better readability
    export_data = export_data.rename(columns={
        "month": "Month",
        "electricity_kwh": "Electricity Usage (kWh)",
        "electricity_provider": "Electricity Provider",
        "gas_kwh": "Gas Usage (kWh)",
        "gas_provider": "Gas Provider",
        "electricity_emissions_kg": "Electricity Emissions (kg CO2e)",
        "gas_emissions_kg": "Gas Emissions (kg CO2e)",
        "total_emissions_tonnes": "Total Emissions (tonnes CO2e)"
    })
    
    # Add CSV download button
    st.markdown(
        get_csv_download_link(export_data, "council_carbon_data.csv", "📥 Download Data as CSV"),
        unsafe_allow_html=True
    )
    
    # Visualisation data format
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
    
    # Show dashboard metrics
    show_dashboard_metrics(df)
    
    # Display charts if we have data
    if len(st.session_state.data_entries) > 0:
        # Create tabs for different visualisations
        tab1, tab2, tab3 = st.tabs(["Energy Usage", "Emissions", "Environmental Impact"])
        
        with tab1:
            # Usage chart
            st.subheader("Energy Usage Trends")
            fig = create_usage_chart(dashboard_df)
            st.plotly_chart(fig, use_container_width=True)
            
            # Add simple insights
            if len(dashboard_df) >= 3:
                highest_month = dashboard_df.loc[dashboard_df["Electricity"].idxmax(), "month"]
                lowest_month = dashboard_df.loc[dashboard_df["Electricity"].idxmin(), "month"]
                
                st.markdown(f"""
                <div class="card">
                    <h4>Key Usage Insights:</h4>
                    <ul>
                        <li>Highest electricity usage: <strong>{highest_month}</strong></li>
                        <li>Lowest electricity usage: <strong>{lowest_month}</strong></li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
        
        with tab2:
            # Emissions chart
            st.subheader("Carbon Emissions Analysis")
            fig = create_emissions_chart(dashboard_df)
            st.plotly_chart(fig, use_container_width=True)
            
            # Add emissions breakdown pie chart
            fig = create_emissions_pie_chart(df)
            st.plotly_chart(fig)
            
            # Add scope explanation
            st.markdown("""
            <div class="card">
                <h4>Emissions by Scope:</h4>
                <p>
                    <span class="scope-badge scope1-badge">SCOPE 1</span> Direct emissions from gas usage
                </p>
                <p>
                    <span class="scope-badge scope2-badge">SCOPE 2</span> Indirect emissions from purchased electricity
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        with tab3:
            # Environmental impact
            show_environmental_impact(df["total_emissions_tonnes"].sum())
    
    # Add tabular view of the data
    st.subheader("Data Table")
    st.dataframe(export_data)
    
    # Add premium features call-to-action
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("""
            <div class="card">
                <h3>Premium Features Available <span class="premium-badge">Opt-in</span></h3>
                <p>Upgrade to access invoice processing, custom reports, data validation and more.</p>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        if st.button("Contact Us", key="contact_us_banner", use_container_width=True):
            navigate_to('contact_us')
            st.rerun()

def invoice_processing_page():
    """Display the invoice processing premium feature page"""
    st.markdown("<h1>Invoice Processing</h1>", unsafe_allow_html=True)
    
    # Add prototype banner
    add_data_disclaimer()
    
    # Premium feature message
    st.markdown("""
    <div class="card" style="text-align: center; padding: 2rem;">
        <h2 style="margin-bottom: 1rem;">Premium Feature <span class="premium-badge">Opt-in</span></h2>
        <p style="margin-bottom: 1.5rem;">
            This is an optional premium feature. Complete our questionnaire to opt in or learn more.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show preview of feature
    st.markdown("""
    <div class="card">
        <h3>Upload Your Energy Invoices</h3>
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
    
    # Premium features list
    st.markdown("""
    <div class="card">
        <h3>Premium Features Include:</h3>
        <ul>
            <li><strong>Automatic Data Extraction</strong> - Save hours of manual data entry</li>
            <li><strong>PDF Invoice Processing</strong> - Support for all major UK energy suppliers</li>
            <li><strong>Data Validation</strong> - Built-in error checking and anomaly detection</li>
            <li><strong>Bulk Processing</strong> - Upload and process multiple invoices at once</li>
        </ul>
        <p style="margin-top: 1rem;">Complete our questionnaire to opt in for these premium features.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Contact form
    show_contact_us_form()

def contact_us_page():
    """Display the contact us page"""
    st.markdown("<h1>Contact Us</h1>", unsafe_allow_html=True)
    
    # Add prototype banner
    add_data_disclaimer()
    
    # Contact form
    show_contact_us_form()

# --- MAIN APP ---
def main():
    """Main application function"""
    # Load CSS for styling
    load_css()
    
    # Add prototype banner
    add_prototype_banner()
    
    # Sidebar navigation
    with st.sidebar:

        
        # Prototype notice
        st.warning("PROTOTYPE VERSION: No data will be saved. For demonstration only.")
        
        # Demo mode indicator
        if st.session_state.demo_mode:
            st.success("✓ Demo data loaded")
        
        st.markdown("<h3>Navigation</h3>", unsafe_allow_html=True)
        
        # Navigation buttons
        if st.button("Home", key="nav_home", use_container_width=True):
            navigate_to('landing')
        
        if st.button("Dashboard", key="nav_dashboard", use_container_width=True):
            navigate_to('data_entry')
        
        if st.button("Invoice Processing", key="nav_invoice", use_container_width=True):
            navigate_to('invoice_processing')
        
        if st.button("Contact Us", key="nav_contact", use_container_width=True):
            navigate_to('contact_us')
        
        # Demo data toggle
        st.markdown("<hr>", unsafe_allow_html=True)
        
        st.write("Sample Data:")
        if st.button(
            "Load Demo Data" if not st.session_state.demo_mode else "Clear Demo Data", 
            key="toggle_demo",
            use_container_width=True
        ):
            toggle_demo_mode()
            st.rerun()
        
        # Help information
        st.markdown("<hr>", unsafe_allow_html=True)
        
        with st.expander("What We Track"):
            st.markdown("""
            <div>
                <p><span class="scope-badge scope1-badge">SCOPE 1</span> Direct emissions from gas heating</p>
                <p><span class="scope-badge scope2-badge">SCOPE 2</span> Indirect emissions from purchased electricity</p>
                <p><em>Premium features include fleet vehicles and more reporting options</em></p>
            </div>
            """, unsafe_allow_html=True)
        
        with st.expander("Reporting Standards"):
            st.markdown("""
            <div>
                <p>• Based on latest DEFRA conversion factors</p>
                <p>• Updated annually with latest factors</p>
            </div>
            """, unsafe_allow_html=True)
    
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
            