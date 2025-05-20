
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
import uuid
import time
import calendar

# --- CONSTANTS ---
TREE_ABSORPTION_RATE = 21  # kg CO2 per tree per year
CAR_EMISSIONS_PER_KM = 0.12  # kg CO2 per km
HOME_ANNUAL_EMISSIONS = 3.2  # tonnes CO2e per household annually

# DEFRA carbon conversion factors - source: UK Government GHG Conversion Factors
#Scope 3	Managed assets- electricity	Electricity generated	Electricity: UK	2020		kWh	kg CO2e
ELECTRICITY_FACTORS = {
    2022: 0.19338,
    2023:  0.207074,
    2024: 0.20705,  # updated
    2025: 0.20705  # projected (official not yet published)
}

#Scope 1	Fuels	Gaseous fuels	Natural gas			kWh (Gross CV)	kg CO2e
GAS_FACTORS = {
    2022: 0.18254,
    2023: 0.18293,
    2024: 0.18290,  # updated
    2025: 0.18290   # projected (official not yet published)
}

# Define available years for selection
AVAILABLE_YEARS = [2022, 2023, 2024, 2025]

# Reporting period types
REPORTING_PERIODS = {
    "calendar": "Calendar Year (Jan-Dec)",
    "financial": "Financial Year (Apr-Mar)"
}

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Carbon Tracker for Councils – Simple, Smart, Actionable",
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

# Added missing session state variables
if 'buildings' not in st.session_state:
    st.session_state.buildings = []

if 'selected_view' not in st.session_state:
    st.session_state.selected_view = 'all'

if 'selected_building' not in st.session_state:
    st.session_state.selected_building = None

if 'selected_years' not in st.session_state:
    st.session_state.selected_years = [datetime.now().year]

# Initialize building form data storage
if 'building_form_data' not in st.session_state:
    st.session_state.building_form_data = {}

# Add reporting period setting
if 'reporting_period' not in st.session_state:
    st.session_state.reporting_period = "calendar"

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
        st.session_state.buildings = []
        st.session_state.selected_building = None

def load_demo_data():
    """Explore what your council's carbon reporting could look like – no setup required"""
    st.session_state.data_entries = []
    
    # Create some demo buildings
    st.session_state.buildings = [
        {
            "id": "town-hall",
            "name": "Town Hall",
            "type": "Administrative Building",
            "floor_area": 3500,
            "address": "1 Council Square, Town Center"
        },
        {
            "id": "community-center",
            "name": "Community Center",
            "type": "Public Building",
            "floor_area": 2200,
            "address": "15 Park Avenue, East District"
        },
        {
            "id": "leisure-center",
            "name": "Leisure Center",
            "type": "Recreational",
            "floor_area": 4800,
            "address": "8 Sports Lane, West District"
        }
    ]
    
    # Set the first building as selected
    st.session_state.selected_building = "town-hall"
    
    # Set default years for demo - include multiple years for year-on-year comparison
    st.session_state.selected_years = [2023, 2024]
    
    # Generate data for 2023
    generate_year_data(2023)
    
    # Generate data for 2024 with a 5% reduction in emissions (realistic improvement)
    generate_year_data(2024, reduction_factor=0.95)

def generate_year_data(year, reduction_factor=1.0):
    """Generate demo data for a specific year with optional reduction factor"""
    start_date = datetime(year, 1, 1)
    
    # Realistic patterns with seasonal variation
    elec_pattern = [12500, 11800, 10500, 9200, 8500, 8000, 8200, 8500, 9000, 10000, 11200, 12000]
    gas_pattern = [8000, 7500, 6500, 5000, 3500, 2500, 2000, 2200, 3000, 4500, 6500, 7800]
    
    # Apply reduction factor to simulate improvement over time
    elec_pattern = [val * reduction_factor for val in elec_pattern]
    gas_pattern = [val * reduction_factor for val in gas_pattern]
    
    # Generate data for each building
    for building in st.session_state.buildings:
        for month in range(12):
            current_date = start_date.replace(month=month+1)
            
            # Add realistic random variation
            elec_variation = random.uniform(0.92, 1.08)
            gas_variation = random.uniform(0.9, 1.1)
            
            # Vary by building size
            size_factor = building["floor_area"] / 3500  # Normalized to Town Hall
            
            elec_kwh = elec_pattern[month] * elec_variation * size_factor
            gas_kwh = gas_pattern[month] * gas_variation * size_factor
            
            emissions = calculate_emissions(elec_kwh, gas_kwh, current_date)
            
            entry = {
                "building_id": building["id"],
                "building_name": building["name"],
                "building_type": building["type"],
                "floor_area": building["floor_area"],
                "year": year,
                "month": current_date.strftime("%B %Y"),
                "month_num": current_date.month,
                "electricity_kwh": elec_kwh,
                "electricity_provider": "Council Energy Provider",
                "gas_kwh": gas_kwh,
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
    """Load improved CSS with sleek, professional, climate-friendly styling"""
    st.markdown("""
<style>
    /* Basic Typography - Improved readability */
    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #2C3E50; /* Deeper text color for better contrast */
        line-height: 1.5;
    }
    
    h1, h2, h3, h4, h5 {
        color: #2C3E50; /* Matching text color for headings */
        font-weight: 600;
        margin-top: 0.5em;
        margin-bottom: 0.5em;
    }
    
    p, li {
        color: #34495E;
        font-size: 1rem;
    }
    
    /* Professional prototype banner */
    .prototype-banner {
    background-color: #2C3E50; /* Navy professional banner */
    color: white;
    padding: 9px;
    text-align: center;
    font-weight: 600;
    position: sticky;
    top: 0;
    z-index: 1000;
    font-size: 0.9rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.15);
    letter-spacing: 0.5px;
    border-radius: 8px; /* Added rounded corners */
    margin-bottom: 2px;
    }
        
    /* Scope badges for emissions types - climate-friendly colors */
    .scope-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 8px;
        letter-spacing: 0.5px;
    }
    
    .scope1-badge {
        background-color: #CF6F42; /* Terracotta - sophisticated earth tone */
        color: white;
    }
    
    .scope2-badge {
        background-color: #2A8D60; /* Forest green - mature environmental */
        color: white;
    }
    
    /* Sleeker card styling */
    .card {
        background-color: white;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        padding: 24px;
        margin-bottom: 18px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.03);
        transition: all 0.25s ease;
    }
    
    .card:hover {
        box-shadow: 0 5px 15px rgba(0,0,0,0.05);
    }
    
    /* Feature cards with refined style */
    .feature-card {
        height: 350px;
        display: flex;
        flex-direction: column;
        background-color: white;
        border: 1px solid #E5E5E5;
        border-radius: 8px;
        padding: 28px;
        margin-bottom: 18px;
        text-align: left;
        box-shadow: 0 3px 10px rgba(0,0,0,0.04);
        transition: all 0.3s ease;
        overflow-y: auto;
    }
    
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 18px rgba(0,0,0,0.08);
    }
    
    .feature-card h3 {
        margin-bottom: 16px;
        color: #1D6A96; /* Ocean blue - trustworthy */
        text-align: center;
        font-weight: 600;
    }
    
    /* Info cards with refined style */
    .info-card {
        height: 280px;
        display: flex;
        flex-direction: column;
        background-color: white;
        border: 1px solid #E5E5E5;
        border-radius: 8px;
        padding: 24px;
        margin-bottom: 18px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.04);
        overflow-y: auto;
    }
    
    /* Feature info cards with refined style */
    .feature-info-card {
        height: 420px;
        overflow-y: auto;
    }
    
    /* Facts card with climate-friendly colors */
    .facts-card {
        background-color: #F4F6F9; /* Lighter blue-gray */
        border-left: 4px solid #1D6A96; /* Ocean blue */
        border-radius: 6px;
        padding: 20px;
        margin-bottom: 18px;
    }
    
    /* Grid layout for card rows */
    .card-row {
        display: flex;
        flex-wrap: wrap;
        gap: 18px;
        margin-bottom: 18px;
    }
    
    .card-row > div {
        flex: 1;
        min-width: 260px;
    }
    
    /* Professional hero section */
    .hero-section {
        background: linear-gradient(120deg, #16A085 0%, #1D6A96 100%); /* Teal to ocean blue gradient */
        padding: 50px 30px;
        border-radius: 10px;
        margin-bottom: 36px;
        text-align: center;
        box-shadow: 0 5px 25px rgba(0,0,0,0.1);
    }
    
    .hero-section h1 {
        color: white;
        font-size: 2.6rem;
        margin-bottom: 18px;
        font-weight: 700;
        line-height: 1.2;
        letter-spacing: -0.5px;
    }
    
    .hero-section p {
        color: white;
        font-size: 1.25rem;
        margin-bottom: 18px;
        max-width: 800px;
        margin-left: auto;
        margin-right: auto;
        line-height: 1.6;
    }
    
    /* Sophisticated metric cards */
    .metric-card {
        height: 210px;
        display: flex;
        flex-direction: column;
        background-color: white;
        border-top: 4px solid #1D6A96; /* Ocean blue */
        border-radius: 8px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.06);
        padding: 24px;
        text-align: center;
        margin-bottom: 22px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        overflow-y: auto;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.08);
    }
    
    .metric-value {
        font-size: 2.4rem;
        font-weight: bold;
        color: #1D6A96; /* Ocean blue */
        margin-bottom: 10px;
    }
    
    .metric-label {
        font-size: 1.05rem;
        color: #34495E;
        font-weight: 500;
    }
    
    /* Premium elements */
    .premium-badge {
        display: inline-block;
        background-color: #F9E8DD; /* Warm sand */
        color: #212529;
        padding: 4px 10px;
        border-radius: 4px;
        margin-left: 8px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    
    /* Contact section */
    .contact-section {
        background: #F5F9FA;
        padding: 35px;
        border-radius: 10px;
        margin: 35px 0;
        border: 2px solid #16A085; /* Teal */
        box-shadow: 0 5px 20px rgba(0,0,0,0.05);
    }
    
    /* Download button */
    .download-button {
        display: inline-block;
        background-color: #16A085; /* Teal */
        color: white;
        padding: 12px 20px;
        text-align: center;
        border-radius: 6px;
        text-decoration: none;
        font-weight: 600;
        margin: 12px 0;
        transition: all 0.25s ease;
    }
    
    .download-button:hover {
        background-color: #138D76; /* Darker teal */
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    }
    
    /* Building cards */
    .building-card {
        height: 230px;
        background-color: white;
        border-left: 4px solid #1D6A96; /* Ocean blue */
        border-radius: 8px;
        padding: 24px;
        margin-bottom: 22px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
        position: relative;
        overflow-y: auto;
    }
    
    .building-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 18px rgba(0,0,0,0.1);
    }
    
    .building-card h3 {
        color: #1D6A96; /* Ocean blue */
        margin-top: 0;
        margin-bottom: 14px;
        font-weight: 600;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px 6px 0 0;
        padding: 12px 18px;
        background-color: #F5F9FA;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #1D6A96 !important; /* Ocean blue */
        color: white !important;
    }
    
    /* Mobile responsiveness */
    @media (max-width: 768px) {
        .hero-section h1 {
            font-size: 1.9rem;
        }
        
        .hero-section p {
            font-size: 1.05rem;
        }
        
        .metric-value {
            font-size: 1.9rem;
        }
        
        .card, .feature-card, .info-card {
            padding: 18px;
        }
        
        /* Stack columns on mobile */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            margin-bottom: 18px;
        }
        
        /* Adjust card heights for mobile */
        .feature-card, .info-card, .metric-card {
            height: auto;
            min-height: 210px;
        }
    }
    
    /* Action buttons */
    .action-button {
        padding: 12px 18px;
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.25s ease;
    }
    
    .action-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 10px rgba(0,0,0,0.1);
    }
    
    /* Form styling */
    [data-testid="stForm"] {
        background-color: #F5F9FA;
        padding: 24px;
        border-radius: 10px;
        box-shadow: 0 3px 12px rgba(0,0,0,0.05);
    }
    
    /* Form field labels */
    label {
        font-weight: 500;
        color: #2C3E50;
    }
    
    /* Loading indicator */
    .loading-spinner {
        text-align: center;
        padding: 24px;
    }
    
    /* Year selector pills */
    .year-pill {
        display: inline-block;
        padding: 6px 12px;
        margin: 0 6px 6px 0;
        background-color: #E5E9F0;
        border-radius: 20px;
        font-size: 0.9rem;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .year-pill:hover {
        background-color: #D8DEE9;
    }
    
    .year-pill.active {
        background-color: #1D6A96; /* Ocean blue */
        color: white;
    }
    
    /* Status indicators */
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-indicator.red {
        background-color: #CF6F42; /* Terracotta */
    }
    
    .status-indicator.green {
        background-color: #2A8D60; /* Forest green */
    }
    
    .status-indicator.amber {
        background-color: #F9E8DD; /* Warm sand */
    }
    
    /* Table styles */
    [data-testid="stTable"] table {
        border-collapse: separate;
        border-spacing: 0;
        width: 100%;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
    }
    
    [data-testid="stTable"] th {
        background-color: #F5F9FA;
        padding: 14px 16px;
        text-align: left;
        font-weight: 600;
        color: #2C3E50;
        border-bottom: 1px solid #E5E9F0;
    }
    
    [data-testid="stTable"] td {
        padding: 12px 16px;
        border-bottom: 1px solid #E5E9F0;
    }
    
    [data-testid="stTable"] tr:hover {
        background-color: #F8FAFC;
    }
    
    /* Info box */
    .info-box {
        background-color: #EFF8F7; /* Light teal */
        border-left: 4px solid #16A085; /* Teal */
        padding: 18px;
        margin: 18px 0;
        border-radius: 6px;
    }
    
    /* Tooltip */
    .tooltip {
        position: relative;
        display: inline-block;
        cursor: help;
    }
    
    .tooltip .tooltiptext {
        visibility: hidden;
        width: 220px;
        background-color: #2C3E50;
        color: #fff;
        text-align: center;
        border-radius: 6px;
        padding: 8px 10px;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        margin-left: -110px;
        opacity: 0;
        transition: opacity 0.3s;
        font-size: 0.85rem;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    
    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 0.95;
    }
    
    /* Button styling */       
    st.form_submit_button[kind="primary"] {
        border: none !important;
        background-color: #6AB6E1 !important; /* Ocean blue */
        color: white !important;
        transition: all 0.25s ease !important;
        box-shadow: 0 3px 8px rgba(0,0,0,0.1) !important;
        font-weight: 500 !important;
        letter-spacing: 0.3px !important;
    }

    /* Hover effect for primary form buttons */
    st.form_submit_button[kind="primary"]:hover {
        background-color:  #6AE193!important; /* Darker ocean blue */
        transform: translateY(-2px) !important;
        box-shadow: 0 5px 12px rgba(0,0,0,0.15) !important;
    }       
    
    .stButton button[kind="primary"] {
        border: none !important;
        background-color: #6AB6E1 !important; /* Ocean blue */
        color: white !important;
        transition: all 0.25s ease !important;
        box-shadow: 0 3px 8px rgba(0,0,0,0.1) !important;
        font-weight: 500 !important;
        letter-spacing: 0.3px !important;
    }

    /* Hover effect for primary buttons */
    .stButton button[kind="primary"]:hover {
        background-color: #6AE193 !important; /* Darker ocean blue */
        transform: translateY(-2px) !important;
        box-shadow: 0 5px 12px rgba(0,0,0,0.15) !important;
    }
    
    .stButton button[kind="secondary"] {
        border: none !important;
        transition: all 0.25s ease !important;
        box-shadow: 0 3px 8px rgba(0,0,0,0.05) !important;
        font-weight: 500 !important;
    }

    /* Hover effect for secondary buttons */
    .stButton button[kind="secondary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 5px 12px rgba(0,0,0,0.1) !important;
    }
    
    /* Streamlit sidebar improvements */
    [data-testid="stSidebar"] {
        background-color: #F8FAFC !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        padding-top: 1.5rem;
    }
    
    /* Expandable sections */
    [data-testid="stExpander"] {
        border: 1px solid #E5E9F0;
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* Inputs and selectboxes */
    [data-testid="stTextInput"], 
    [data-testid="stNumberInput"],
    [data-testid="stSelectbox"] {
        margin-bottom: 1rem;
    }
    
    /* Footer styling */
    footer {
        visibility: hidden;
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
def get_appropriate_factor_year(date):
    """
    Determine the appropriate factor year based on the date and reporting period
    
    Logic:
    - For Calendar Year (Jan-Dec): Use factors from the same year
    - For Financial Year (Apr-Mar): Use factors from the year where most months fall
    
    Args:
        date: datetime object representing the date of energy usage
    
    Returns:
        int: The year to use for emission factors
    """
    if st.session_state.reporting_period == "calendar":
        # Calendar year - use factors from the same year
        return date.year
    
    elif st.session_state.reporting_period == "financial":
        # Financial year (Apr-Mar)
        if date.month >= 4:  # Apr-Dec
            return date.year  # Most of financial year falls in this calendar year
        else:  # Jan-Mar
            return date.year - 1  # Most of financial year fell in previous calendar year
    

    
    # Default fallback
    return date.year

def calculate_emissions(electricity_kwh, gas_kwh, date):
    """
    Calculate carbon emissions based on energy usage and date
    
    Args:
        electricity_kwh: Electricity usage in kWh
        gas_kwh: Gas usage in kWh
        date: datetime object or year as int
    
    Returns:
        dict: Calculated emissions values
    """
    # Convert year to datetime if needed
    if isinstance(date, int):
        date = datetime(date, 1, 1)
    
    # Get appropriate factor year based on reporting period
    factor_year = get_appropriate_factor_year(date)
    
    # Get conversion factors for the determined year
    electricity_factor = ELECTRICITY_FACTORS.get(factor_year, list(ELECTRICITY_FACTORS.values())[-1])
    gas_factor = GAS_FACTORS.get(factor_year, list(GAS_FACTORS.values())[-1])
    
    # Calculate emissions
    electricity_emissions_kg = electricity_kwh * electricity_factor
    gas_emissions_kg = gas_kwh * gas_factor
    
    total_emissions_kg = electricity_emissions_kg + gas_emissions_kg
    total_emissions_tonnes = total_emissions_kg / 1000
    
    return {
        "electricity_emissions_kg": electricity_emissions_kg,
        "gas_emissions_kg": gas_emissions_kg,
        "total_emissions_tonnes": total_emissions_tonnes,
        "factor_year": factor_year  # Include the factor year used for reference
    }

# --- CONTACT FORM ---
def show_contact_us_form():
    """Display contact form with improved styling"""
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
    """Explain what emissions are tracked with improved visual design"""
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
    """Show why councils need this tool with improved messaging"""
    st.markdown("<h2 style='text-align: center; margin: 1rem 0;'>Why Your Council Needs This Tool</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <img src="https://img.icons8.com/fluency/48/000000/document.png" alt="Document Icon" style="width: 48px; margin-bottom: 15px;">
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
        <div class="feature-card">
            <img src="https://img.icons8.com/fluency/48/000000/time.png" alt="Time Icon" style="width: 48px; margin-bottom: 15px;">
            <h3>Save 5+ Hours Monthly</h3>
            <ul>
                <li>Automated calculations using latest DEFRA factors</li>
                <li>No more complex spreadsheets or manual calculations</li>
                <li>Quick dashboard updates when data changes</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <img src="https://img.icons8.com/fluency/48/000000/money.png" alt="Money Icon" style="width: 48px; margin-bottom: 15px;">
            <h3>Unlock Grant Funding</h3>
            <ul>
                <li>Clear progress metrics for funding applications</li>
                <li>Evidence for decarbonisation project grants</li>
                <li>Demonstrate ROI on sustainability initiatives</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# New function for building energy comparison chart with improved visuals
# Final chart functions with professional colors that work with Streamlit

def create_building_energy_comparison_chart(comparison_data):
    """Create energy comparison chart between buildings"""
    building_summary = comparison_data.groupby(['building_name']).agg({
        'electricity_kwh': 'sum',
        'gas_kwh': 'sum',
    }).reset_index()
    
    # Melt data for plotting
    plot_data = pd.melt(
        building_summary, 
        id_vars=['building_name'],
        value_vars=['electricity_kwh', 'gas_kwh'],
        var_name='energy_type', 
        value_name='kwh'
    )
    
    # Rename energy types for better display
    plot_data['energy_type'] = plot_data['energy_type'].replace({
        'electricity_kwh': 'Electricity',
        'gas_kwh': 'Gas'
    })
    
    # Create bar chart with professional colors
    fig = px.bar(
        plot_data,
        x='building_name',
        y='kwh',
        color='energy_type',
        barmode='group',
        title="Energy Usage by Building",
        labels={
            'building_name': 'Building',
            'kwh': 'Energy Usage (kWh)',
            'energy_type': 'Energy Type'
        },
        color_discrete_map={
            'Electricity': '#2A8D60',  # Forest Green - environmental, mature
            'Gas': '#CF6F42'           # Terracotta - natural, earth tone
        }
    )
    
    fig.update_layout(
        xaxis_title="Building",
        yaxis_title="Energy (kWh)",
        legend_title="Energy Type",
        template="plotly_white",
        height=500
    )
    
    return fig

def create_building_emissions_comparison_chart(comparison_data):
    """Create emissions comparison chart between buildings"""
    building_summary = comparison_data.groupby(['building_name']).agg({
        'electricity_emissions_kg': 'sum',
        'gas_emissions_kg': 'sum',
    }).reset_index()
    
    # Convert to tonnes for better visualization
    building_summary['electricity_emissions_tonnes'] = building_summary['electricity_emissions_kg'] / 1000
    building_summary['gas_emissions_tonnes'] = building_summary['gas_emissions_kg'] / 1000
    
    # Melt data for plotting
    plot_data = pd.melt(
        building_summary, 
        id_vars=['building_name'],
        value_vars=['electricity_emissions_tonnes', 'gas_emissions_tonnes'],
        var_name='emissions_type', 
        value_name='tonnes'
    )
    
    # Rename emission types for better display
    plot_data['emissions_type'] = plot_data['emissions_type'].replace({
        'electricity_emissions_tonnes': 'Electricity',
        'gas_emissions_tonnes': 'Gas'
    })
    
    # Create bar chart with professional colors
    fig = px.bar(
        plot_data,
        x='building_name',
        y='tonnes',
        color='emissions_type',
        barmode='stack',
        title="Carbon Emissions by Building",
        labels={'building_name': 'Building',
            'tonnes': 'Carbon Emissions (tCO₂e)',
            'emissions_type': 'Source'
        },
        color_discrete_map={
            'Electricity': '#2A8D60',  # Forest Green - environmental, mature
            'Gas': '#CF6F42'           # Terracotta - natural, earth tone
        }
    )
    
    fig.update_layout(
        xaxis_title="Building",
        yaxis_title="Emissions (tCO₂e)",
        legend_title="Source",
        template="plotly_white",
        height=500
    )
    
    return fig

def create_yearly_comparison_chart(df):
    """Create year-on-year comparison chart"""
    # Group by year
    yearly_data = df.groupby('year').agg({
        'electricity_kwh': 'sum',
        'gas_kwh': 'sum',
        'total_emissions_tonnes': 'sum'
    }).reset_index()
    
    # Create a figure with secondary y-axis
    fig = go.Figure()
    
    # Add energy bars with professional colors
    fig.add_trace(go.Bar(
        x=yearly_data['year'],
        y=yearly_data['electricity_kwh'],
        name='Electricity (kWh)',
        marker_color='#2A8D60',  # Forest Green - environmental, mature
        offsetgroup=0
    ))
    
    fig.add_trace(go.Bar(
        x=yearly_data['year'],
        y=yearly_data['gas_kwh'],
        name='Gas (kWh)',
        marker_color='#CF6F42',  # Terracotta - natural, earth tone
        offsetgroup=0
    ))
    
    # Add emissions line on secondary y-axis
    fig.add_trace(go.Scatter(
        x=yearly_data['year'],
        y=yearly_data['total_emissions_tonnes'],
        name='Total Emissions (tCO₂e)',
        mode='lines+markers',
        marker=dict(size=10, color='#1D6A96'),  # Deep Blue - trustworthy, matches Streamlit
        line=dict(width=3, color='# 6096B5'),
        yaxis='y2'
    ))
    
    # Set up layout with two y-axes
    fig.update_layout(
        barmode='stack',
        title='Year-on-Year Comparison',
        yaxis=dict(
            title='Energy Usage (kWh)'
        ),
        yaxis2=dict(
            title='Emissions (tCO₂e)',
            overlaying='y',
            side='right'
        ),
        xaxis=dict(
            title='Year',
            tickvals=yearly_data['year']
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5
        ),
        hovermode='x',
        template="plotly_white",
        height=500
    )
    
    return fig

def add_building_form():
    """Form for adding a new building with improved UX and logic flow"""
    st.markdown("<h2>Add New Building</h2>", unsafe_allow_html=True)
    
    # Add explicit prototype warning
    st.warning("⚠️ PROTOTYPE: Any data entered here is for demonstration only and will not be saved.")
    
    # Initialize form fields from session state if available
    building_name = ""
    building_type = "Administrative Building"
    floor_area = 1000
    address_line1 = ""
    address_line2 = ""
    postcode = ""
    
    # Store form data in session state to persist between reruns
    if 'building_form_data' in st.session_state:
        building_name = st.session_state.building_form_data.get('name', "")
        building_type = st.session_state.building_form_data.get('type', "Administrative Building")
        floor_area = st.session_state.building_form_data.get('floor_area', 1000)
        address_line1 = st.session_state.building_form_data.get('address_line1', "")
        address_line2 = st.session_state.building_form_data.get('address_line2', "")
        postcode = st.session_state.building_form_data.get('postcode', "")
    
    # Create form with separate submit handling
    with st.form("add_building_form", clear_on_submit=False):
        st.markdown("### Building Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            building_name = st.text_input("Building Name*", 
                                         value=building_name,
                                         placeholder="e.g. Town Hall")
            
            building_type = st.selectbox(
                "Building Type*",
                options=["Administrative Building", "Public Building", "Leisure Center", "Library", "School", "Other"],
                index=["Administrative Building", "Public Building", "Leisure Center", "Library", "School", "Other"].index(building_type) if building_type in ["Administrative Building", "Public Building", "Leisure Center", "Library", "School", "Other"] else 0
            )
            
            floor_area = st.number_input("Floor Area (m²) (Optional)", 
                                        min_value=1, 
                                        value=floor_area)
        
        with col2:
            address_line1 = st.text_input("Address Line 1 (Optional)", 
                                         value=address_line1,
                                         placeholder="Street Address")
            
            address_line2 = st.text_input("Address Line 2 (Optional)", 
                                         value=address_line2,
                                         placeholder="Area/District")
            
            postcode = st.text_input("Postcode (Optional)", 
                                    value=postcode,
                                    placeholder="e.g. AB12 3CD")
        
        st.markdown("*required fields")
        st.markdown("---")
        
        # Create separate columns for buttons
        col1, col2 = st.columns([1, 3])
        
        with col1:
            cancel = st.form_submit_button("Cancel", use_container_width=True)
        
        with col2:
            submitted = st.form_submit_button("Add Building", type="primary", use_container_width=True)
    
    # Handle form submission outside the form itself
    if submitted:
        # Validate required fields
        # Updated validation check:
        if not building_name:
            st.error("Please fill in the building name (required field).")
            
            # Save the form data to session state to persist after rerun
            st.session_state.building_form_data = {
                'name': building_name,
                'type': building_type,
                'floor_area': floor_area,
                'address_line1': address_line1,
                'address_line2': address_line2,
                'postcode': postcode
            }
            
            # Don't proceed further if validation fails
            return
        
        # Show loading spinner
        with st.spinner("Adding building..."):
            # Create building ID from name (simplified for demo)
            building_id = f"{building_name.lower().replace(' ', '-')}-{str(uuid.uuid4())[:8]}"
            
            # Compile address
            address = f"{address_line1}"
            if address_line2:
                address += f", {address_line2}"
            address += f", {postcode}"
            
            # Create building object
            new_building = {
                "id": building_id,
                "name": building_name,
                "type": building_type,
                "floor_area": floor_area,
                "address": address
            }
            
            # Add to buildings list
            st.session_state.buildings.append(new_building)
            
            # Set as selected building
            st.session_state.selected_building = building_id
            
            # Clear form data from session state
            if 'building_form_data' in st.session_state:
                del st.session_state.building_form_data
            
            # Brief delay to ensure UI updates properly
            time.sleep(0.5)
        
        st.success(f"Building '{building_name}' added successfully!")
        
        # Reset entry mode with slight delay to ensure UI updates properly
        time.sleep(0.5)
        st.session_state.entry_mode = None
        st.rerun()
    
    if cancel:
        # Clear form data from session state
        if 'building_form_data' in st.session_state:
            del st.session_state.building_form_data
            
        st.session_state.entry_mode = None
        st.rerun()
    
    # Add "Back to Dashboard" button outside the form
    if st.button("← Back to Dashboard", key="back_from_add_building"):
        if 'building_form_data' in st.session_state:
            del st.session_state.building_form_data
            
        st.session_state.entry_mode = None
        st.rerun()

def building_selection_page():
    """Page for selecting or adding a building - improved UI flow and logic"""
    st.markdown("<h2>Select a Building</h2>", unsafe_allow_html=True)
    
    # Show prototype warning
    add_data_disclaimer()
    
    # Add building and demo data buttons at top with improved visibility
    st.markdown("<div style='margin-bottom: 20px;'>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Add New Building", key="add_building_button_top", type="primary", use_container_width=True):
            # Explicitly clear any old form data
            if 'building_form_data' in st.session_state:
                del st.session_state.building_form_data
                
            st.session_state.entry_mode = "add_building"
            st.rerun()
    
    with col2:
        demo_button_text = "🔍 View Demo Data" if not st.session_state.demo_mode else "❌ Clear Demo Data"
        if st.button(demo_button_text, key="demo_data_button_top", use_container_width=True):
            toggle_demo_mode()
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    
    if not st.session_state.buildings:
        # Improved empty state messaging with clear user guidance
        st.markdown("""
        <div style="text-align: center; margin: 30px 0; padding: 40px 20px; background-color: #f5f5f5; border-radius: 10px;">
            <img src="https://img.icons8.com/fluency/96/000000/building.png" alt="Building Icon" style="width: 80px; margin-bottom: 20px;">
            <h3>No Buildings Available</h3>
            <p>Add your first building to start tracking emissions data.</p>
            <p style="font-size: 0.9rem; color: #666; margin-top: 20px;">Click the "Add New Building" button above to get started.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Display existing buildings as interactive cards with improved visuals
    st.markdown("<h3>Your Buildings</h3>", unsafe_allow_html=True)
    
    # Create building cards in rows of 2 (larger cards for better readability)
    buildings_per_row = 2
    building_chunks = [st.session_state.buildings[i:i + buildings_per_row] 
                      for i in range(0, len(st.session_state.buildings), buildings_per_row)]
    
    for chunk in building_chunks:
        cols = st.columns(buildings_per_row)
        
        for i, building in enumerate(chunk):
            if i < len(cols):  # Ensure we have a building for this column
                with cols[i]:
                    # More prominent and attractive card with clear button
                    st.markdown(f"""
                    <div class="building-card">
                        <h3>{building['name']}</h3>
                        <p><strong>Type:</strong> {building['type']}</p>
                        <p><strong>Floor Area:</strong> {building['floor_area']} m²</p>
                        <p><strong>Address:</strong> {building['address']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Two buttons - one to view and one to add data directly
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📊 View Dashboard", key=f"view_{building['id']}", use_container_width=True):
                            st.session_state.selected_building = building['id']
                            st.session_state.selected_view = "all"
                            # Clear any entry mode to ensure dashboard displays
                            st.session_state.entry_mode = None
                            st.rerun()
                    
                    with col2:
                        if st.button("➕ Add Data", key=f"add_data_{building['id']}", use_container_width=True, type="primary"):
                            st.session_state.selected_building = building['id']
                            # Go directly to multiple month entry
                            st.session_state.entry_mode = "multiple"
                            st.rerun()
    
    # Add new building button at bottom as well for convenience
    st.markdown("<div style='margin-top: 30px;'>", unsafe_allow_html=True)
    if st.button("➕ Add Another Building", key="add_new_from_list", type="primary", use_container_width=True):
        # Explicitly clear any old form data
        if 'building_form_data' in st.session_state:
            del st.session_state.building_form_data
            
        st.session_state.entry_mode = "add_building"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# Complete function for the multiple month form with Clear Form button

def show_multiple_month_form():
    """Form for entering multiple months of data with improved UX and logic flow"""
    st.markdown("<h2>Enter Energy Data for Multiple Months</h2>", unsafe_allow_html=True)
    
    # Add explicit prototype warning
    st.warning("⚠️ PROTOTYPE: Any data entered here is for demonstration only and will not be saved.")
    
    # Get selected building if available
    selected_building = None
    for building in st.session_state.buildings:
        if building["id"] == st.session_state.selected_building:
            selected_building = building
            break
    
    if not selected_building:
        st.error("Please select a building first")
        if st.button("Select Building", key="select_building_first", type="primary"):
            st.session_state.selected_building = None
            st.session_state.entry_mode = None
            st.rerun()
        return
    
    # Show selected building with improved card design
    st.markdown(f"""
    <div class="card" style="border-left: 4px solid #1a73e8; margin-bottom: 20px;">
        <h3 style="color: #1a73e8; margin-top: 0;">Data for: {selected_building['name']}</h3>
        <p><strong>Type:</strong> {selected_building['type']} | <strong>Floor Area:</strong> {selected_building['floor_area']} m²</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Year selection and reporting period
    col1, col2 = st.columns(2)
    
    with col1:
        # Year selection with improved styling
        year = st.selectbox(
            "📅 Select Year",
            options=AVAILABLE_YEARS,
            index=AVAILABLE_YEARS.index(datetime.now().year) if datetime.now().year in AVAILABLE_YEARS else 0,
            key="multi_month_year"
        )
    
    with col2:
        # Reporting period selection with info tooltip
        st.markdown("""
        <div style="display: flex; align-items: center;">
            <label style="margin-bottom: 0.5rem; font-size: 0.875rem; color: rgb(73, 80, 87); font-weight: 400;">
                Reporting Period 
                <span class="tooltip" style="margin-left: 5px;">ℹ️
                    <span class="tooltiptext">
                        This affects which DEFRA emissions factors are applied to your data.
                    </span>
                </span>
            </label>
        </div>
        """, unsafe_allow_html=True)
        
        reporting_period = st.selectbox(
            "Reporting Period",
            options=list(REPORTING_PERIODS.keys()),
            format_func=lambda x: REPORTING_PERIODS[x],
            index=list(REPORTING_PERIODS.keys()).index(st.session_state.reporting_period),
            label_visibility="collapsed"
        )
        
        # Update the reporting period in session state
        if reporting_period != st.session_state.reporting_period:
            st.session_state.reporting_period = reporting_period
    
    # NEW: Add a Clear Form button before the form
    if 'clear_form_values' not in st.session_state:
        st.session_state.clear_form_values = False
        
    if st.button("🗑️ Clear Form Values", key="clear_form_multi"):
        st.session_state.clear_form_values = True
        st.rerun()
    
    # Display info about emissions factors
    with st.expander("About Emissions Factors"):
        st.markdown("""
        <div class="info-box">
            <h4 style="margin-top: 0;">Emission Factors Selection Logic</h4>
            <p>The dashboard automatically applies the appropriate DEFRA emission factors based on your reporting period:</p>
            <ul>
                <li><strong>Calendar Year (Jan-Dec):</strong> Uses factors from the same year</li>
                <li><strong>Financial Year (Apr-Mar):</strong> Uses factors from the calendar year where most months fall</li>
            </ul>
            <p>This follows DEFRA guidance that factors should correlate with the data period they're applied to.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Helper function for default values
    def get_default(key):
        # If clear is requested, return 0.0, otherwise use the custom defaults
        if st.session_state.clear_form_values:
            return 0.0
        
        # Example default values based on month - realistic patterns with seasonal variation
        elec_defaults = {
            "jan_elec": 10000.0, "feb_elec": 9500.0, "mar_elec": 9000.0, "apr_elec": 8500.0,
            "may_elec": 8000.0, "jun_elec": 7800.0, "jul_elec": 7500.0, "aug_elec": 7800.0,
            "sep_elec": 8200.0, "oct_elec": 8800.0, "nov_elec": 9500.0, "dec_elec": 10000.0
        }
        
        gas_defaults = {
            "jan_gas": 8000.0, "feb_gas": 7500.0, "mar_gas": 6500.0, "apr_gas": 5000.0,
            "may_gas": 3500.0, "jun_gas": 2500.0, "jul_gas": 2000.0, "aug_gas": 2200.0,
            "sep_gas": 3000.0, "oct_gas": 4500.0, "nov_gas": 6500.0, "dec_gas": 7800.0
        }
        
        if key in elec_defaults:
            return elec_defaults[key]
        elif key in gas_defaults:
            return gas_defaults[key]
        return 0.0  # Default fallback
    
    # Form for data entry with improved layout and logic
    with st.form("multiple_month_form", clear_on_submit=True):
        # Create tabs for months with improved styling
        tabs = st.tabs(["Jan-Apr", "May-Aug", "Sep-Dec"])
        
        with tabs[0]:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("January")
                jan_elec = st.number_input("Electricity (kWh)", min_value=0.0, value=get_default("jan_elec"), key="jan_elec")
                jan_gas = st.number_input("Gas (kWh)", min_value=0.0, value=get_default("jan_gas"), key="jan_gas")
            
            with col2:
                st.subheader("February")
                feb_elec = st.number_input("Electricity (kWh)", min_value=0.0, value=get_default("feb_elec"), key="feb_elec")
                feb_gas = st.number_input("Gas (kWh)", min_value=0.0, value=get_default("feb_gas"), key="feb_gas")
            
            col3, col4 = st.columns(2)
            with col3:
                st.subheader("March")
                mar_elec = st.number_input("Electricity (kWh)", min_value=0.0, value=get_default("mar_elec"), key="mar_elec")
                mar_gas = st.number_input("Gas (kWh)", min_value=0.0, value=get_default("mar_gas"), key="mar_gas")
            
            with col4:
                st.subheader("April")
                apr_elec = st.number_input("Electricity (kWh)", min_value=0.0, value=get_default("apr_elec"), key="apr_elec")
                apr_gas = st.number_input("Gas (kWh)", min_value=0.0, value=get_default("apr_gas"), key="apr_gas")
        
        with tabs[1]:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("May")
                may_elec = st.number_input("Electricity (kWh)", min_value=0.0, value=get_default("may_elec"), key="may_elec")
                may_gas = st.number_input("Gas (kWh)", min_value=0.0, value=get_default("may_gas"), key="may_gas")
            
            with col2:
                st.subheader("June")
                jun_elec = st.number_input("Electricity (kWh)", min_value=0.0, value=get_default("jun_elec"), key="jun_elec")
                jun_gas = st.number_input("Gas (kWh)", min_value=0.0, value=get_default("jun_gas"), key="jun_gas")
            
            col3, col4 = st.columns(2)
            with col3:
                st.subheader("July")
                jul_elec = st.number_input("Electricity (kWh)", min_value=0.0, value=get_default("jul_elec"), key="jul_elec")
                jul_gas = st.number_input("Gas (kWh)", min_value=0.0, value=get_default("jul_gas"), key="jul_gas")
            
            with col4:
                st.subheader("August")
                aug_elec = st.number_input("Electricity (kWh)", min_value=0.0, value=get_default("aug_elec"), key="aug_elec")
                aug_gas = st.number_input("Gas (kWh)", min_value=0.0, value=get_default("aug_gas"), key="aug_gas")
        
        with tabs[2]:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("September")
                sep_elec = st.number_input("Electricity (kWh)", min_value=0.0, value=get_default("sep_elec"), key="sep_elec")
                sep_gas = st.number_input("Gas (kWh)", min_value=0.0, value=get_default("sep_gas"), key="sep_gas")
            
            with col2:
                st.subheader("October")
                oct_elec = st.number_input("Electricity (kWh)", min_value=0.0, value=get_default("oct_elec"), key="oct_elec")
                oct_gas = st.number_input("Gas (kWh)", min_value=0.0, value=get_default("oct_gas"), key="oct_gas")
            
            col3, col4 = st.columns(2)
            with col3:
                st.subheader("November")
                nov_elec = st.number_input("Electricity (kWh)", min_value=0.0, value=get_default("nov_elec"), key="nov_elec")
                nov_gas = st.number_input("Gas (kWh)", min_value=0.0, value=get_default("nov_gas"), key="nov_gas")
            
            with col4:
                st.subheader("December")
                dec_elec = st.number_input("Electricity (kWh)", min_value=0.0, value=get_default("dec_elec"), key="dec_elec")
                dec_gas = st.number_input("Gas (kWh)", min_value=0.0, value=get_default("dec_gas"), key="dec_gas")
        
        # Provider information with clearer grouping
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<h3>Energy Supplier Information (Optional)</h3>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            elec_provider = st.text_input("Electricity Supplier", value="", placeholder="e.g. EDF Energy")
        with col2:
            gas_provider = st.text_input("Gas Supplier", value="", placeholder="e.g. British Gas")
        
        # Buttons for processing or cancelling with improved layout and feedback
        st.markdown("<hr>", unsafe_allow_html=True)
        
        # Create separate columns for buttons
        col1, col2 = st.columns([1, 3])
        
        with col1:
            cancel = st.form_submit_button("Cancel", use_container_width=True)
        
        with col2:
            submitted = st.form_submit_button("Process All Data", type="primary", use_container_width=True)
    
    # Reset clear flag after form is rendered
    st.session_state.clear_form_values = False
    
    # Handle form submission outside the form
    if submitted:
        # Show processing indicator
        with st.spinner("Processing data..."):
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
            entries_added = 0
            
            for month_num, (elec, gas, month_name) in month_data.items():
                if elec > 0 or gas > 0:  # Only add if there's data
                    date = datetime(year, month_num, 1)
                    emissions = calculate_emissions(elec, gas, date)
                    
                    entry = {
                        "building_id": selected_building["id"],
                        "building_name": selected_building["name"],
                        "building_type": selected_building["type"],
                        "floor_area": selected_building["floor_area"],
                        "year": year,
                        "month": date.strftime("%B %Y"),
                        "month_num": month_num,
                        "electricity_kwh": elec,
                        "electricity_provider": elec_provider,
                        "gas_kwh": gas,
                        "gas_provider": gas_provider,
                        "electricity_emissions_kg": emissions["electricity_emissions_kg"],
                        "gas_emissions_kg": emissions["gas_emissions_kg"],
                        "total_emissions_tonnes": emissions["total_emissions_tonnes"],
                        "factor_year": emissions["factor_year"]
                    }
                    
                    st.session_state.data_entries.append(entry)
                    entries_added += 1
            
            # Add the year to selected years if not already there
            if year not in st.session_state.selected_years:
                st.session_state.selected_years.append(year)
            
            # Brief delay to ensure UI updates properly
            time.sleep(0.5)
        
        # Show verification of which emission factors were used
        if entries_added > 0:
            factor_year = calculate_emissions(1000, 1000, datetime(year, 6, 1))["factor_year"]
            st.success(f"Added data for {entries_added} months in {year} using {factor_year} emission factors (for this demonstration session only)")
        else:
            st.warning("No data was added. Please enter at least one month's data.")
        
        # Reset entry mode with a slight delay to ensure UI updates properly
        time.sleep(0.5)
        st.session_state.entry_mode = None
        st.rerun()
    
    if cancel:
        st.session_state.entry_mode = None
        st.rerun()
    
    # Add "Back to Dashboard" button outside the form
    if st.button("← Back to Dashboard", key="back_from_multi_month"):
        st.session_state.entry_mode = None
        st.rerun()

# Complete function for the single month form with Clear Form button

def show_single_month_form():
    """Form for entering a single month of data with improved UX and logic flow"""
    st.markdown("<h2>Enter Energy Data for a Single Month</h2>", unsafe_allow_html=True)
    
    # Add explicit prototype warning
    st.warning("⚠️ PROTOTYPE: Any data entered here is for demonstration only and will not be saved.")
    
    # Get selected building if available
    selected_building = None
    for building in st.session_state.buildings:
        if building["id"] == st.session_state.selected_building:
            selected_building = building
            break
    
    if not selected_building:
        st.error("Please select a building first")
        if st.button("Select Building", key="select_building_single", type="primary"):
            st.session_state.selected_building = None
            st.session_state.entry_mode = None
            st.rerun()
        return
    
    # Show selected building with improved card design
    st.markdown(f"""
    <div class="card" style="border-left: 4px solid #1a73e8; margin-bottom: 20px;">
        <h3 style="color: #1a73e8; margin-top: 0;">Data for: {selected_building['name']}</h3>
        <p><strong>Type:</strong> {selected_building['type']} | <strong>Floor Area:</strong> {selected_building['floor_area']} m²</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Reporting period selection
    st.markdown("""
    <div style="display: flex; align-items: center;">
        <label style="margin-bottom: 0.5rem; font-size: 0.875rem; color: rgb(73, 80, 87); font-weight: 400;">
            Reporting Period 
            <span class="tooltip" style="margin-left: 5px;">ℹ️
                <span class="tooltiptext">
                    This affects which DEFRA emissions factors are applied to your data.
                </span>
            </span>
        </label>
    </div>
    """, unsafe_allow_html=True)
    
    reporting_period = st.selectbox(
        "Reporting Period",
        options=list(REPORTING_PERIODS.keys()),
        format_func=lambda x: REPORTING_PERIODS[x],
        index=list(REPORTING_PERIODS.keys()).index(st.session_state.reporting_period),
        label_visibility="collapsed"
    )
    
    # Update the reporting period in session state
    if reporting_period != st.session_state.reporting_period:
        st.session_state.reporting_period = reporting_period
    
    # NEW: Add a Clear Form button before the form
    if 'clear_single_form' not in st.session_state:
        st.session_state.clear_single_form = False
        
    if st.button("🗑️ Clear Form Values", key="clear_form_single"):
        st.session_state.clear_single_form = True
        st.rerun()
    
    # Form with improved layout and logic
    with st.form("single_month_form", clear_on_submit=True):
        st.markdown("### Reporting Month Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            month = st.date_input("📅 Reporting Month", datetime.now())
            # Use 0.0 as default if clear form is requested
            electricity_usage = st.number_input(
                "⚡ Electricity Usage (kWh)", 
                min_value=0.0, 
                value=0.0 if st.session_state.clear_single_form else 9000.0
            )
            electricity_provider = st.text_input("Electricity Provider (optional)", "", placeholder="e.g. EDF Energy")
        
        with col2:
            # Use 0.0 as default if clear form is requested
            gas_usage = st.number_input(
                "🔥 Gas Usage (kWh)", 
                min_value=0.0, 
                value=0.0 if st.session_state.clear_single_form else 5000.0
            )
            gas_provider = st.text_input("Gas Provider (optional)", "", placeholder="e.g. British Gas")
        
        st.markdown("---")
        st.markdown("### Calculated Emissions (Preview)")
        
        # Preview calculation
        emissions_preview = calculate_emissions(electricity_usage, gas_usage, month)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Electricity Emissions", f"{emissions_preview['electricity_emissions_kg']/1000:.2f} tCO₂e")
        
        with col2:
            st.metric("Gas Emissions", f"{emissions_preview['gas_emissions_kg']/1000:.2f} tCO₂e")
        
        with col3:
            st.metric("Total Emissions", f"{emissions_preview['total_emissions_tonnes']:.2f} tCO₂e")
        
        st.markdown("<div class='info-box'>Using emissions factors from <strong>{}</strong> based on your reporting period.</div>".format(
            emissions_preview['factor_year']), unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Create separate columns for buttons
        col1, col2 = st.columns([1, 3])
        
        with col1:
            cancel = st.form_submit_button("Cancel", use_container_width=True)
        
        with col2:
            submitted = st.form_submit_button("Save Data", type="primary", use_container_width=True)
    
    # Reset the clear flag after form is rendered
    st.session_state.clear_single_form = False
    
    # Handle form submission outside the form
    if submitted:
        # Show processing indicator
        with st.spinner("Saving data..."):
            # Calculate emissions
            emissions = calculate_emissions(electricity_usage, gas_usage, month)
            
            # Create new entry
            new_entry = {
                "building_id": selected_building["id"],
                "building_name": selected_building["name"],
                "building_type": selected_building["type"],
                "floor_area": selected_building["floor_area"],
                "year": month.year,
                "month": month.strftime("%B %Y"),
                "month_num": month.month,
                "electricity_kwh": electricity_usage,
                "electricity_provider": electricity_provider,
                "gas_kwh": gas_usage,
                "gas_provider": gas_provider,
                "electricity_emissions_kg": emissions["electricity_emissions_kg"],
                "gas_emissions_kg": emissions["gas_emissions_kg"],
                "total_emissions_tonnes": emissions["total_emissions_tonnes"],
                "factor_year": emissions["factor_year"]
            }
            
            # Add to data entries
            st.session_state.data_entries.append(new_entry)
            
            # Add the year to selected years if not already there
            if month.year not in st.session_state.selected_years:
                st.session_state.selected_years.append(month.year)
                
            # Brief delay to ensure UI updates properly
            time.sleep(0.5)
        
        st.success(f"Data saved successfully using {emissions['factor_year']} emission factors (for this demonstration session only)")
        
        # Reset entry mode with a slight delay to ensure UI updates properly
        time.sleep(0.5)
        st.session_state.entry_mode = None
        st.rerun()
    
    if cancel:
        st.session_state.entry_mode = None
        st.rerun()
    
    # Add "Back to Dashboard" button outside the form
    if st.button("← Back to Dashboard", key="back_from_single_month"):
        st.session_state.entry_mode = None
        st.rerun()
# Function to show dashboard metrics with improved visual design
def show_dashboard_metrics(df):
    """Display key metrics at the top of the dashboard"""
    
    # Calculate metrics
    total_electricity = df['electricity_kwh'].sum()
    total_gas = df['gas_kwh'].sum()
    total_emissions = df['total_emissions_tonnes'].sum()
    
    # Create metrics row with improved visuals
    st.markdown("<h3>Key Metrics</h3>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_electricity:,.0f}</div>
            <div class="metric-label">Total Electricity (kWh)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_gas:,.0f}</div>
            <div class="metric-label">Total Gas (kWh)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_emissions:,.2f}</div>
            <div class="metric-label">Total Emissions (tCO₂e)</div>
        </div>
        """, unsafe_allow_html=True)

def show_buildings_comparison():
    """Show comparison between buildings with improved UX"""
    st.markdown("<h2>Buildings Comparison</h2>", unsafe_allow_html=True)
    
    if len(st.session_state.buildings) <= 1:
        # Improved empty state message
        st.markdown("""
        <div class="card" style="text-align: center; padding: 30px 20px;">
            <img src="https://img.icons8.com/color/96/000000/compare.png" alt="Compare Icon" style="width: 70px; margin-bottom: 15px;">
            <h3>Comparison Requires Multiple Buildings</h3>
            <p>You need at least 2 buildings to make a comparison.</p>
            <p style="margin-top: 15px; color: #666; font-size: 0.9rem;">Add another building to enable comparison features.</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Return to Dashboard", type="primary"):
            st.session_state.selected_view = "all"
            st.rerun()
        return
    
    # Building filter setup with improved UI
    st.markdown("""
    <div class="card">
        <h3 style="margin-top: 0;">Comparison Settings</h3>
    """, unsafe_allow_html=True)
    
    buildings_to_compare = st.multiselect(
        "Select buildings to compare",
        options=[b["name"] for b in st.session_state.buildings],
        default=[b["name"] for b in st.session_state.buildings]
    )
    
    if not buildings_to_compare:
        st.warning("Please select at least one building to display.")
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    # Year selection with improved UI
    compare_year = st.selectbox(
        "Select year to compare",
        options=sorted(st.session_state.selected_years, reverse=True),
        index=0
    )
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Create building ID mapping
    building_names_to_ids = {b["name"]: b["id"] for b in st.session_state.buildings}
    building_ids = [building_names_to_ids[name] for name in buildings_to_compare]
    
    # Filter data
    df = pd.DataFrame(st.session_state.data_entries)
    
    if df.empty:
        st.warning("No data available for comparison.")
        return
    
    comparison_data = df[
        (df["building_id"].isin(building_ids)) &
        (df["year"] == compare_year)
    ]
    
    if comparison_data.empty:
        # More helpful empty state message
        st.markdown(f"""
        <div class="card" style="text-align: center; padding: 20px;">
            <h3>No Data Available</h3>
            <p>No data available for the selected buildings in {compare_year}.</p>
            <p>Please add data for {compare_year} or select a different year.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Create comparison visualizations with improved design
    st.markdown("<h3>Energy Usage Comparison</h3>", unsafe_allow_html=True)
    fig1 = create_building_energy_comparison_chart(comparison_data)
    st.plotly_chart(fig1, use_container_width=True)
    
    st.markdown("<h3>Carbon Emissions Comparison</h3>", unsafe_allow_html=True)
    fig2 = create_building_emissions_comparison_chart(comparison_data)
    st.plotly_chart(fig2, use_container_width=True)
    
    # Building comparison table with improved design
    st.markdown("""
    <div class="card">
        <h3 style="margin-top: 0;">Building Comparison Details</h3>
    """, unsafe_allow_html=True)
    
    # Group by building
    building_summary = comparison_data.groupby(['building_name', 'building_type', 'floor_area']).agg({
        'electricity_kwh': 'sum',
        'gas_kwh': 'sum',
        'electricity_emissions_kg': 'sum',
        'gas_emissions_kg': 'sum',
        'total_emissions_tonnes': 'sum'
    }).reset_index()
    
    # Add intensity metrics
    building_summary['energy_intensity'] = (building_summary['electricity_kwh'] + building_summary['gas_kwh']) / building_summary['floor_area']
    building_summary['carbon_intensity'] = building_summary['total_emissions_tonnes'] * 1000 / building_summary['floor_area']
    
    # Create readable comparison table
    comparison_table = building_summary[[
        'building_name', 'building_type', 'floor_area', 
        'electricity_kwh', 'gas_kwh', 'total_emissions_tonnes',
        'energy_intensity', 'carbon_intensity'
    ]].rename(columns={
        'building_name': 'Building',
        'building_type': 'Type',
        'floor_area': 'Floor Area (m²)',
        'electricity_kwh': 'Electricity (kWh)',
        'gas_kwh': 'Gas (kWh)',
        'total_emissions_tonnes': 'Total Emissions (tCO₂e)',
        'energy_intensity': 'Energy Intensity (kWh/m²)',
        'carbon_intensity': 'Carbon Intensity (kgCO₂e/m²)'
    })
    
    # Round numeric columns
    numeric_cols = ['Electricity (kWh)', 'Gas (kWh)', 'Total Emissions (tCO₂e)', 
                   'Energy Intensity (kWh/m²)', 'Carbon Intensity (kgCO₂e/m²)']
    comparison_table[numeric_cols] = comparison_table[numeric_cols].round(2)
    
    # Display table
    st.dataframe(comparison_table)
    
    # Download button for comparison data
    st.markdown(
        get_csv_download_link(comparison_table, f"building_comparison_{compare_year}.csv", "📥 Download Comparison Data"),
        unsafe_allow_html=True
    )
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Return button with improved styling
    if st.button("← Return to Dashboard", type="primary"):
        st.session_state.selected_view = "all"
        st.rerun()

# Additional chart functions with updated colors

# Additional chart functions with sleek, professional climate colors

# Additional chart functions with professional colors for Streamlit

def create_usage_chart(dashboard_df):
    """Create energy usage chart with professional colors"""
    # Sort data by month
    try:
        dashboard_df['month_dt'] = pd.to_datetime(dashboard_df['month'], format='%B %Y')
        dashboard_df = dashboard_df.sort_values('month_dt')
        dashboard_df['month'] = dashboard_df['month_dt'].dt.strftime('%b %Y')
        dashboard_df = dashboard_df.drop('month_dt', axis=1)
    except:
        pass  # If sort fails, use original order
    
    fig = go.Figure()
    
    # Add electricity data with professional color
    fig.add_trace(go.Bar(
        x=dashboard_df["month"],
        y=dashboard_df["Electricity"],
        name="Electricity (kWh)",
        marker_color="#2A8D60"  # Forest Green - environmental
    ))
    
    # Add gas data with earth tone
    fig.add_trace(go.Bar(
        x=dashboard_df["month"],
        y=dashboard_df["Gas"],
        name="Gas (kWh)",
        marker_color="#CF6F42"  # Terracotta - natural
    ))
    
    # Add trend line if enough data
    if len(dashboard_df) >= 3:
        fig.add_trace(go.Scatter(
            x=dashboard_df["month"],
            y=dashboard_df["Electricity"].rolling(3, min_periods=1).mean(),
            name="Electricity 3-Month Average",
            line=dict(color="#2A8D60", dash="dash", width=2)  # Forest Green
        ))
        
        fig.add_trace(go.Scatter(
            x=dashboard_df["month"],
            y=dashboard_df["Gas"].rolling(3, min_periods=1).mean(),
            name="Gas 3-Month Average",
            line=dict(color="#CF6F42", dash="dash", width=2)  # Terracotta
        ))
    
    fig.update_layout(
        title="Monthly Energy Usage",
        xaxis_title="Month",
        yaxis_title="Usage (kWh)",
        legend_title="Energy Type",
        hovermode="x unified",
        barmode="group",
        template="plotly_white",
        height=450
    )
    
    return fig

def create_emissions_chart(dashboard_df):
    """Create emissions chart with professional colors"""
    # Sort data by month
    try:
        dashboard_df['month_dt'] = pd.to_datetime(dashboard_df['month'], format='%B %Y')
        dashboard_df = dashboard_df.sort_values('month_dt')
        dashboard_df['month'] = dashboard_df['month_dt'].dt.strftime('%b %Y')
        dashboard_df = dashboard_df.drop('month_dt', axis=1)
    except:
        pass  # If sort fails, use original order
    
    fig = go.Figure()
    
    # Add electricity emissions with professional colors
    fig.add_trace(go.Scatter(
        x=dashboard_df["month"],
        y=dashboard_df["Electricity Emissions"],
        name="Electricity (tCO₂e)",
        mode="lines+markers",
        line=dict(color="#2A8D60", width=3),  # Forest Green - environmental
        marker=dict(size=8, color="#2A8D60")
    ))
    
    # Add gas emissions with earth tone
    fig.add_trace(go.Scatter(
        x=dashboard_df["month"],
        y=dashboard_df["Gas Emissions"],
        name="Gas (tCO₂e)",
        mode="lines+markers",
        line=dict(color="#CF6F42", width=3),  # Terracotta - natural
        marker=dict(size=8, color="#CF6F42")
    ))
    
    # Add total emissions with streamlit-friendly blue
    fig.add_trace(go.Scatter(
        x=dashboard_df["month"],
        y=dashboard_df["Electricity Emissions"] + dashboard_df["Gas Emissions"],
        name="Total Emissions (tCO₂e)",
        mode="lines",
        line=dict(color="#1D6A96", width=4)  # Deep Blue - trustworthy, matches Streamlit
    ))
    
    fig.update_layout(
        title="Monthly Carbon Emissions",
        xaxis_title="Month",
        yaxis_title="Emissions (tCO₂e)",
        legend_title="Source",
        hovermode="x unified",
        template="plotly_white",
        height=450
    )
    
    return fig

def create_emissions_pie_chart(df):
    """Create emissions breakdown pie chart with professional colors"""
    emissions_data = [
        df["electricity_emissions_kg"].sum() / 1000,
        df["gas_emissions_kg"].sum() / 1000
    ]
    
    # Calculate percentages for labels
    total = sum(emissions_data)
    elec_percent = (emissions_data[0] / total * 100) if total > 0 else 0
    gas_percent = (emissions_data[1] / total * 100) if total > 0 else 0
    
    # Custom text for better readability
    custom_text = [
        f"Electricity: {emissions_data[0]:.2f} tCO₂e ({elec_percent:.1f}%)",
        f"Gas: {emissions_data[1]:.2f} tCO₂e ({gas_percent:.1f}%)"
    ]
    
    fig = px.pie(
        values=emissions_data,
        names=["Electricity", "Gas"],
        title="Emissions Breakdown by Source",
        color_discrete_sequence=["#2A8D60", "#CF6F42"],  # Forest Green and Terracotta
        hole=0.4
    )
    
    fig.update_traces(
        textinfo='percent',
        hovertext=custom_text,
        hoverinfo='text'
    )
    
    fig.update_layout(
        template="plotly_white",
        height=400,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    
    return fig
# def show_environmental_impact(total_emissions):
#     """Show environmental impact metrics with improved visuals"""
#     st.subheader("Environmental Impact")
    
#     # # Calculate impact metrics
#     # trees_needed = int(total_emissions * 1000 / TREE_ABSORPTION_RATE)
#     # car_km = int((total_emissions * 1000) / CAR_EMISSIONS_PER_KM)
#     # homes_equivalent = int(total_emissions / HOME_ANNUAL_EMISSIONS)
    
#     # Display impact cards with improved design
#     col1, col2, col3 = st.columns(3)
    
#     with col1:
#         st.markdown(f"""
#         <div class="metric-card" style="border-top-color: #4caf50;">
#             <div class="metric-value" style="color: #4caf50;">{trees_needed:,d}</div>
#             <div class="metric-label">Trees Needed</div>
#             <p style="margin-top: 0.5rem; font-size: 0.85rem; color: #666;">Trees required to offset your annual emissions</p>
#         </div>
#         """, unsafe_allow_html=True)
    
#     with col2:
#         st.markdown(f"""
#         <div class="metric-card" style="border-top-color: #ff9800;">
#             <div class="metric-value" style="color: #ff9800;">{car_km:,d}</div>
#             <div class="metric-label">Car Kilometers</div>
#             <p style="margin-top: 0.5rem; font-size: 0.85rem; color: #666;">Equivalent to this many kilometers of driving</p>
#         </div>
#         """, unsafe_allow_html=True)
    
#     with col3:
#         st.markdown(f"""
#         <div class="metric-card" style="border-top-color: #1a73e8;">
#             <div class="metric-value" style="color: #1a73e8;">{homes_equivalent:,d}</div>
#             <div class="metric-label">Homes</div>
#             <p style="margin-top: 0.5rem; font-size: 0.85rem; color: #666;">Equivalent to annual usage of this many homes</p>
#         </div>
#         """, unsafe_allow_html=True)
    
#     # Add interpretation note
#     st.markdown("""
#     <div class="card" style="margin-top: 20px;">
#         <h4 style="margin-top: 0;">What Does This Mean?</h4>
#         <p>These metrics help visualize your carbon impact in more tangible terms. 
#         They show the equivalent environmental impact of your organization's emissions compared to everyday activities and natural carbon absorption.</p>
#         <p style="font-size: 0.9rem; color: #666;">
#             <strong>Note:</strong> Tree absorption is based on mature trees over the course of a year. 
#             Car emissions are based on average emissions from a medium-sized petrol car.
#         </p>
#     </div>
#     """, unsafe_allow_html=True)

# Year-on-Year Analysis feature

def show_yearly_analysis():
    """Dedicated page for comprehensive year-on-year analysis"""
    st.markdown("<h1>Year-on-Year Analysis</h1>", unsafe_allow_html=True)
    
    # Show prototype warning
    add_data_disclaimer()
    
    # Create DataFrame from entries
    df = pd.DataFrame(st.session_state.data_entries)
    
    if df.empty:
        # Display a helpful message if no data is available
        st.markdown("""
        <div style="text-align: center; margin: 30px 0; padding: 40px 20px; background-color: #f5f5f5; border-radius: 10px;">
            <img src="https://img.icons8.com/fluency/96/000000/calendar.png" alt="Calendar Icon" style="width: 70px; margin-bottom: 15px;">
            <h2>No Data Available for Analysis</h2>
            <p>Please add data for at least one building to see year-on-year analysis.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # FIX: Simplify the button logic to directly navigate to data entry
        if st.button("Add Data Now", type="primary"):
            st.session_state.current_page = 'data_entry'
            st.session_state.entry_mode = "multiple"
            # If we have buildings, select the first one
            if st.session_state.buildings:
                st.session_state.selected_building = st.session_state.buildings[0]["id"]
            # If no buildings exist, set entry mode to add building first
            else:
                st.session_state.entry_mode = "add_building"
            st.rerun()
        return
    
    # If we have less than 2 years of data, provide guidance
    available_years = sorted(df['year'].unique())
    if len(available_years) < 2:
        st.warning(f"You currently only have data for {available_years[0]}. Add data for multiple years to enable year-on-year analysis.")
        
        # Show option to add another year's data
        if st.button("Add Data for Another Year", type="primary"):
            if st.session_state.buildings:
                st.session_state.selected_building = st.session_state.buildings[0]["id"]
                st.session_state.entry_mode = "multiple"
                st.rerun()
        
        # Still show statistics for the single year
        st.markdown(f"<h3>Statistics for {available_years[0]}</h3>", unsafe_allow_html=True)
    else:
        st.markdown("<h3>Select Years to Compare</h3>", unsafe_allow_html=True)
        
        # Let the user select which years to compare (default to the most recent two years)
        default_years = sorted(available_years, reverse=True)[:2]
        years_to_compare = st.multiselect(
            "Select years to compare",
            options=available_years,
            default=default_years
        )
        
        if len(years_to_compare) < 2:
            st.warning("Please select at least two years to compare.")
            years_to_compare = default_years  # Use default if user selects fewer than 2
    
    # Building selector
    st.markdown("<h3>Select Buildings</h3>", unsafe_allow_html=True)
    
    # Default to all buildings
    available_buildings = sorted(df['building_name'].unique())
    selected_buildings = st.multiselect(
        "Select buildings to include in analysis",
        options=available_buildings,
        default=available_buildings
    )
    
    if not selected_buildings:
        st.warning("Please select at least one building to analyze.")
        selected_buildings = available_buildings  # Use all if none selected
    
    # Filter data based on selections
    filtered_df = df[
        (df['year'].isin(available_years if len(available_years) < 2 else years_to_compare)) & 
        (df['building_name'].isin(selected_buildings))
    ]
    
    # Total yearly emissions chart
    st.markdown("<h2>Total Yearly Emissions</h2>", unsafe_allow_html=True)
    
    # Aggregate data by year
    yearly_emissions = filtered_df.groupby('year').agg({
        'electricity_emissions_kg': 'sum',
        'gas_emissions_kg': 'sum',
        'total_emissions_tonnes': 'sum',
        'electricity_kwh': 'sum',
        'gas_kwh': 'sum'
    }).reset_index()
    
    # Convert kg to tonnes for consistency
    yearly_emissions['electricity_emissions_tonnes'] = yearly_emissions['electricity_emissions_kg'] / 1000
    yearly_emissions['gas_emissions_tonnes'] = yearly_emissions['gas_emissions_kg'] / 1000
    
    # Calculate year-on-year percent changes
    yearly_emissions['elec_emissions_change'] = yearly_emissions['electricity_emissions_tonnes'].pct_change() * 100
    yearly_emissions['gas_emissions_change'] = yearly_emissions['gas_emissions_tonnes'].pct_change() * 100
    yearly_emissions['total_emissions_change'] = yearly_emissions['total_emissions_tonnes'].pct_change() * 100
    yearly_emissions['elec_usage_change'] = yearly_emissions['electricity_kwh'].pct_change() * 100
    yearly_emissions['gas_usage_change'] = yearly_emissions['gas_kwh'].pct_change() * 100
    
    # Create bar chart for yearly emissions
    fig_yearly = go.Figure()
    
    # Add bars for electricity emissions
    fig_yearly.add_trace(go.Bar(
        x=yearly_emissions['year'],
        y=yearly_emissions['electricity_emissions_tonnes'],
        name='Electricity Emissions',
        marker_color='#2e7d32'  # Green
    ))
    
    # Add bars for gas emissions
    fig_yearly.add_trace(go.Bar(
        x=yearly_emissions['year'],
        y=yearly_emissions['gas_emissions_tonnes'],
        name='Gas Emissions',
        marker_color='#d32f2f'  # Red
    ))
    
    # Add line for total emissions
    fig_yearly.add_trace(go.Scatter(
        x=yearly_emissions['year'],
        y=yearly_emissions['total_emissions_tonnes'],
        name='Total Emissions',
        mode='lines+markers',
        marker=dict(size=10, color='#1a73e8'),
        line=dict(width=3, color='#1a73e8')
    ))
    
    # Update layout
    fig_yearly.update_layout(
        barmode='stack',
        title='Annual Carbon Emissions',
        xaxis_title='Year',
        yaxis_title='Emissions (tCO₂e)',
        legend_title='Source',
        hovermode='x unified',
        template='plotly_white',
        height=500
    )
    
    st.plotly_chart(fig_yearly, use_container_width=True)
    
    # Display changes as a metrics table
    st.markdown("<h3>Year-on-Year Changes</h3>", unsafe_allow_html=True)
    
    # Only show changes if we have multiple years
    if len(available_years) >= 2:
        # Create a tabular view of changes
        changes_df = yearly_emissions[yearly_emissions['year'] > yearly_emissions['year'].min()]
        
        # Create a clean dataframe for display
        display_changes = pd.DataFrame({
            'Year': changes_df['year'],
            'Electricity Emissions Change (%)': changes_df['elec_emissions_change'].round(1),
            'Gas Emissions Change (%)': changes_df['gas_emissions_change'].round(1),
            'Total Emissions Change (%)': changes_df['total_emissions_change'].round(1),
            'Electricity Usage Change (%)': changes_df['elec_usage_change'].round(1),
            'Gas Usage Change (%)': changes_df['gas_usage_change'].round(1)
        })
        
        st.dataframe(display_changes, use_container_width=True)
        
        # Visual indicators of progress
        latest_year_changes = changes_df.iloc[-1]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if latest_year_changes['total_emissions_change'] < 0:
                change_color = "green"
                icon = "↓"
                message = "Emissions are decreasing"
            elif abs(latest_year_changes['total_emissions_change']) < 1:
                change_color = "orange"
                icon = "→"
                message = "Emissions are stable"
            else:
                change_color = "red"
                icon = "↑"
                message = "Emissions are increasing"
                
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: {change_color};">{icon} {abs(latest_year_changes['total_emissions_change']):.1f}%</div>
                <div class="metric-label">Total Emissions Change</div>
                <p style="margin-top: 0.5rem; font-size: 0.85rem; color: #666;">{message} from previous year</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            emissions_rate = yearly_emissions.iloc[-1]['total_emissions_tonnes']
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{emissions_rate:.1f}</div>
                <div class="metric-label">Current Annual Rate (tCO₂e)</div>
                <p style="margin-top: 0.5rem; font-size: 0.85rem; color: #666;">Based on most recent year's data</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            # Calculate how many years of data we have
            data_years = len(yearly_emissions)
            avg_change = yearly_emissions['total_emissions_change'].mean(skipna=True)
            
            if pd.isna(avg_change):
                avg_change = 0
                
            trend_message = "decreasing" if avg_change < 0 else "increasing"
            
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: {'green' if avg_change < 0 else 'red'};">{abs(avg_change):.1f}%</div>
                <div class="metric-label">Average Annual Change</div>
                <p style="margin-top: 0.5rem; font-size: 0.85rem; color: #666;">Emissions are {trend_message} by this rate on average</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Monthly pattern analysis
    st.markdown("<h2>Monthly Patterns</h2>", unsafe_allow_html=True)
    
    # Allow selecting a specific year for monthly analysis
    selected_year = st.selectbox(
        "Select year for monthly breakdown",
        options=sorted(filtered_df['year'].unique(), reverse=True),
        index=0
    )
    
    # Filter for selected year
    year_data = filtered_df[filtered_df['year'] == selected_year]
    
    # Extract month from the date string and convert to month number
    year_data['month_name'] = year_data['month'].str.split(' ').str[0]
    
    # Mapping month names to numbers for sorting
    month_to_num = {month: i+1 for i, month in enumerate(calendar.month_name[1:])}
    year_data['month_num'] = year_data['month_name'].map(month_to_num)
    
    # Aggregate by month
    monthly_data = year_data.groupby('month_num').agg({
        'electricity_kwh': 'sum',
        'gas_kwh': 'sum',
        'electricity_emissions_kg': 'sum',
        'gas_emissions_kg': 'sum',
        'total_emissions_tonnes': 'sum',
        'month_name': 'first'  # Keep month name for display
    }).reset_index().sort_values('month_num')
    
    # Create monthly emissions chart
    fig_monthly = go.Figure()
    
    # Add bars for electricity emissions
    fig_monthly.add_trace(go.Bar(
        x=monthly_data['month_name'],
        y=monthly_data['electricity_emissions_kg'] / 1000,  # Convert to tonnes
        name='Electricity Emissions',
        marker_color='#2e7d32'  # Green
    ))
    
    # Add bars for gas emissions
    fig_monthly.add_trace(go.Bar(
        x=monthly_data['month_name'],
        y=monthly_data['gas_emissions_kg'] / 1000,  # Convert to tonnes
        name='Gas Emissions',
        marker_color='#d32f2f'  # Red
    ))
    
    # Update layout
    fig_monthly.update_layout(
        barmode='stack',
        title=f'Monthly Emissions for {selected_year}',
        xaxis_title='Month',
        yaxis_title='Emissions (tCO₂e)',
        legend_title='Source',
        hovermode='x unified',
        template='plotly_white',
        height=500
    )
    
    st.plotly_chart(fig_monthly, use_container_width=True)
    
    # Seasonal patterns analysis
    st.markdown("<h3>Seasonal Patterns</h3>", unsafe_allow_html=True)
    
    # Define seasons
    winter_months = [12, 1, 2]
    spring_months = [3, 4, 5]
    summer_months = [6, 7, 8]
    autumn_months = [9, 10, 11]
    
    # Create season column
    monthly_data['season'] = monthly_data['month_num'].apply(
        lambda x: 'Winter' if x in winter_months else
                'Spring' if x in spring_months else
                'Summer' if x in summer_months else 'Autumn'
    )
    
    # Aggregate by season
    seasonal_data = monthly_data.groupby('season').agg({
        'electricity_kwh': 'sum',
        'gas_kwh': 'sum',
        'electricity_emissions_kg': 'sum',
        'gas_emissions_kg': 'sum'
    }).reset_index()
    
    # Convert to tonnes
    seasonal_data['electricity_emissions_tonnes'] = seasonal_data['electricity_emissions_kg'] / 1000
    seasonal_data['gas_emissions_tonnes'] = seasonal_data['gas_emissions_kg'] / 1000
    seasonal_data['total_emissions_tonnes'] = seasonal_data['electricity_emissions_tonnes'] + seasonal_data['gas_emissions_tonnes']
    
    # Ensure correct season order
    season_order = ['Winter', 'Spring', 'Summer', 'Autumn']
    seasonal_data['season'] = pd.Categorical(seasonal_data['season'], categories=season_order, ordered=True)
    seasonal_data = seasonal_data.sort_values('season')
    
    # Create seasonal emissions chart
    fig_seasonal = go.Figure()
    
    # Add bars for electricity emissions
    fig_seasonal.add_trace(go.Bar(
        x=seasonal_data['season'],
        y=seasonal_data['electricity_emissions_tonnes'],
        name='Electricity Emissions',
        marker_color='#2e7d32'  # Green
    ))
    
    # Add bars for gas emissions
    fig_seasonal.add_trace(go.Bar(
        x=seasonal_data['season'],
        y=seasonal_data['gas_emissions_tonnes'],
        name='Gas Emissions',
        marker_color='#d32f2f'  # Red
    ))
    
    # Add line for total emissions
    fig_seasonal.add_trace(go.Scatter(
        x=seasonal_data['season'],
        y=seasonal_data['total_emissions_tonnes'],
        name='Total Emissions',
        mode='lines+markers',
        marker=dict(size=10, color='#1a73e8'),
        line=dict(width=3, color='#1a73e8')
    ))
    
    # Update layout
    fig_seasonal.update_layout(
        barmode='stack',
        title=f'Seasonal Emissions for {selected_year}',
        xaxis_title='Season',
        yaxis_title='Emissions (tCO₂e)',
        legend_title='Source',
        hovermode='x unified',
        template='plotly_white',
        height=500
    )
    
    st.plotly_chart(fig_seasonal, use_container_width=True)
    
    # Seasonal insights
    highest_season = seasonal_data.loc[seasonal_data['total_emissions_tonnes'].idxmax(), 'season']
    lowest_season = seasonal_data.loc[seasonal_data['total_emissions_tonnes'].idxmin(), 'season']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="card">
            <h4 style="margin-top: 0;">Seasonal Insights</h4>
            <ul>
                <li>Highest emissions: <strong>{highest_season}</strong></li>
                <li>Lowest emissions: <strong>{lowest_season}</strong></li>
                <li>Winter-Summer difference: <strong>{abs(seasonal_data[seasonal_data['season']=='Winter']['total_emissions_tonnes'].values[0] - seasonal_data[seasonal_data['season']=='Summer']['total_emissions_tonnes'].values[0]):.2f} tCO₂e</strong></li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Calculate the percentage of annual emissions by season
        seasonal_data['percentage'] = seasonal_data['total_emissions_tonnes'] / seasonal_data['total_emissions_tonnes'].sum() * 100
        
        st.markdown(f"""
        <div class="card">
            <h4 style="margin-top: 0;">Percentage of Annual Emissions</h4>
            <ul>
                <li>Winter: <strong>{seasonal_data[seasonal_data['season']=='Winter']['percentage'].values[0]:.1f}%</strong></li>
                <li>Spring: <strong>{seasonal_data[seasonal_data['season']=='Spring']['percentage'].values[0]:.1f}%</strong></li>
                <li>Summer: <strong>{seasonal_data[seasonal_data['season']=='Summer']['percentage'].values[0]:.1f}%</strong></li>
                <li>Autumn: <strong>{seasonal_data[seasonal_data['season']=='Autumn']['percentage'].values[0]:.1f}%</strong></li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Progress Against Targets section
    st.markdown("<h2>Progress Against Targets</h2>", unsafe_allow_html=True)
    
    # Create a simple target setting and tracking interface
    st.markdown("""
    <div class="card">
        <h4 style="margin-top: 0;">Emissions Reduction Targets</h4>
        <p>Set and track your progress against annual emissions reduction targets.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Target selection
    col1, col2 = st.columns(2)
    
    with col1:
        baseline_year = st.selectbox(
            "Baseline Year",
            options=sorted(available_years),
            index=0
        )
    
    with col2:
        target_percentage = st.slider(
            "Target Reduction (%)",
            min_value=0,
            max_value=100,
            value=25,
            step=5
        )
    
    # Get baseline emissions
    baseline_emissions = yearly_emissions[yearly_emissions['year'] == baseline_year]['total_emissions_tonnes'].values[0]
    target_emissions = baseline_emissions * (1 - target_percentage/100)
    
    # Create a progress chart
    target_df = pd.DataFrame({
        'Year': list(range(baseline_year, max(available_years) + 11)),
        'Target': [baseline_emissions * (1 - (target_percentage/100) * (i-baseline_year)/(2050-baseline_year)) 
                  for i in range(baseline_year, max(available_years) + 11)]
    })
    
    # Merge with actual data
    merged_df = pd.merge(
        target_df, 
        yearly_emissions[['year', 'total_emissions_tonnes']], 
        left_on='Year', 
        right_on='year', 
        how='left'
    )
    
    # Create progress chart
    fig_target = go.Figure()
    
    # Add line for target
    fig_target.add_trace(go.Scatter(
        x=merged_df['Year'],
        y=merged_df['Target'],
        name='Target Pathway',
        mode='lines',
        line=dict(color='#ff9800', width=2, dash='dash')
    ))
    
    # Add markers for actual emissions
    fig_target.add_trace(go.Scatter(
        x=merged_df['year'],
        y=merged_df['total_emissions_tonnes'],
        name='Actual Emissions',
        mode='markers',
        marker=dict(size=12, color='#1a73e8')
    ))
    
    # Add baseline point
    fig_target.add_trace(go.Scatter(
        x=[baseline_year],
        y=[baseline_emissions],
        name='Baseline',
        mode='markers',
        marker=dict(size=15, color='#d32f2f', symbol='star')
    ))
    
    # Add target point
    fig_target.add_trace(go.Scatter(
        x=[2050],
        y=[baseline_emissions * (1 - target_percentage/100)],
        name='2050 Target',
        mode='markers',
        marker=dict(size=15, color='#2e7d32', symbol='star')
    ))
    
    # Update layout
    fig_target.update_layout(
        title=f'Progress Against {target_percentage}% Reduction Target (Baseline: {baseline_year})',
        xaxis_title='Year',
        yaxis_title='Emissions (tCO₂e)',
        legend_title='',
        hovermode='x unified',
        template='plotly_white',
        height=500
    )
    
    st.plotly_chart(fig_target, use_container_width=True)
    
    # Calculate progress metrics
    latest_year = max(yearly_emissions['year'])
    latest_emissions = yearly_emissions[yearly_emissions['year'] == latest_year]['total_emissions_tonnes'].values[0]
    
    # Calculate the target for the latest year based on a linear reduction pathway
    years_elapsed = latest_year - baseline_year
    target_years = 2050 - baseline_year  # Common target year
    expected_reduction = target_percentage * (years_elapsed / target_years)
    expected_emissions = baseline_emissions * (1 - expected_reduction/100)
    
    # Calculate actual reduction
    actual_reduction = ((baseline_emissions - latest_emissions) / baseline_emissions) * 100
    
    # Progress assessment
    on_track = actual_reduction >= expected_reduction
    
    # Display progress metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card" style="border-top-color: {'#2e7d32' if actual_reduction > 0 else '#d32f2f'};">
            <div class="metric-value" style="color: {'#2e7d32' if actual_reduction > 0 else '#d32f2f'};">{actual_reduction:.1f}%</div>
            <div class="metric-label">Current Reduction</div>
            <p style="margin-top: 0.5rem; font-size: 0.85rem; color: #666;">From {baseline_year} baseline</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="border-top-color: {'#2e7d32' if on_track else '#ff9800'};">
            <div class="metric-value" style="color: {'#2e7d32' if on_track else '#ff9800'};">{expected_reduction:.1f}%</div>
            <div class="metric-label">Expected Reduction</div>
            <p style="margin-top: 0.5rem; font-size: 0.85rem; color: #666;">Target for {latest_year}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Calculate years to target
        if latest_emissions <= target_emissions:
            status = "Target Achieved!"
            color = "#2e7d32"
        elif actual_reduction <= 0:
            status = "Off Track"
            color = "#d32f2f"
        elif on_track:
            status = "On Track"
            color = "#2e7d32"
        else:
            status = "Behind Schedule"
            color = "#ff9800"
            
        st.markdown(f"""
        <div class="metric-card" style="border-top-color: {color};">
            <div class="metric-value" style="color: {color};">{status}</div>
            <div class="metric-label">Progress Status</div>
            <p style="margin-top: 0.5rem; font-size: 0.85rem; color: #666;">Based on current reduction rate</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Recommendations section
    st.markdown("<h2>Recommendations</h2>", unsafe_allow_html=True)
    
    # Generate simple recommendations based on data analysis
    recommendations = []
    
    # Check seasonal patterns
    winter_emissions = seasonal_data[seasonal_data['season'] == 'Winter']['total_emissions_tonnes'].values[0] if 'Winter' in seasonal_data['season'].values else 0
    summer_emissions = seasonal_data[seasonal_data['season'] == 'Summer']['total_emissions_tonnes'].values[0] if 'Summer' in seasonal_data['season'].values else 0
    
    if winter_emissions > summer_emissions * 1.5:
        recommendations.append("Significant seasonal variation detected. Consider upgrading heating systems or improving building insulation to reduce winter emissions.")
    
    # Check if gas or electricity is the larger contributor
    latest_gas_emissions = yearly_emissions[yearly_emissions['year'] == latest_year]['gas_emissions_tonnes'].values[0]
    latest_elec_emissions = yearly_emissions[yearly_emissions['year'] == latest_year]['electricity_emissions_tonnes'].values[0]
    
    if latest_gas_emissions > latest_elec_emissions * 1.2:
        recommendations.append("Gas emissions are significantly higher than electricity. Consider heat pump installations or other low-carbon heating alternatives.")
    elif latest_elec_emissions > latest_gas_emissions * 1.2:
        recommendations.append("Electricity emissions are significantly higher than gas. Consider solar PV installations or switching to a renewable energy tariff.")
    
    # Progress recommendations
    if not on_track and actual_reduction > 0:
        recommendations.append(f"Current reduction rate of {actual_reduction:.1f}% is behind the target pathway. Consider accelerating emissions reduction measures.")
    elif not on_track and actual_reduction <= 0:
        recommendations.append("Emissions have increased from the baseline year. Urgent intervention is needed to reverse this trend.")
    
    # Display recommendations
    if recommendations:
        st.markdown("""
        <div class="card">
            <h4 style="margin-top: 0;">Suggested Actions</h4>
            <p>Based on your data, here are some recommendations:</p>
        """, unsafe_allow_html=True)
        
        for i, rec in enumerate(recommendations):
            st.markdown(f"""
            <div style="display: flex; align-items: flex-start; margin-bottom: 12px;">
                <div style="background-color: #1a73e8; color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; margin-right: 10px; flex-shrink: 0;">{i+1}</div>
                <p style="margin: 0;">{rec}</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="card">
            <h4 style="margin-top: 0;">Great Progress!</h4>
            <p>Based on your data, you're on track to meet your emissions reduction targets.</p>
            <p>Continue with your current strategies and consider setting more ambitious targets.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Report export section
    st.markdown("<h2>Export Analysis</h2>", unsafe_allow_html=True)
    
    # Create a simple report export feature
    st.markdown("""
    <div class="card">
        <h4 style="margin-top: 0;">Download Year-on-Year Analysis Report</h4>
        <p>Generate a comprehensive report of your emissions data and progress.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        report_format = st.selectbox(
            "Report Format",
            options=["CSV Data Export", "PDF Report (Premium)"],
            index=0
        )
    
    with col2:
        if report_format == "CSV Data Export":
            # Prepare data for export
            export_data = pd.DataFrame({
                'Year': yearly_emissions['year'],
                'Total Emissions (tCO2e)': yearly_emissions['total_emissions_tonnes'],
                'Electricity Emissions (tCO2e)': yearly_emissions['electricity_emissions_tonnes'],
                'Gas Emissions (tCO2e)': yearly_emissions['gas_emissions_tonnes'],
                'Electricity Usage (kWh)': yearly_emissions['electricity_kwh'],
                'Gas Usage (kWh)': yearly_emissions['gas_kwh']
            })
            
            # Add export button
            st.markdown(
                get_csv_download_link(export_data, f"yearly_emissions_analysis.csv", "📥 Download CSV Analysis"),
                unsafe_allow_html=True
            )
        else:
            st.markdown("""
            <p><span class="premium-badge">Premium</span> PDF reports include additional insights and executive summaries.</p>
            """, unsafe_allow_html=True)
            
            # Disabled button for premium feature
            st.button("Generate PDF Report", disabled=True)
    
    # Add a button to return to the main dashboard
    if st.button("← Return to Dashboard", type="primary"):
        st.session_state.current_page = 'data_entry'
        st.rerun()

def data_entry_page():
    """Display data entry page with improved UX flow and state management"""
    st.markdown("<h1>Carbon Data Dashboard</h1>", unsafe_allow_html=True)
    
    # Show prototype warning
    add_data_disclaimer()
    
    # Quick action buttons at top for easy access - improved layout
    st.markdown("<div style='margin-bottom: 20px;'>", unsafe_allow_html=True)
    action_col1, action_col2, action_col3, action_col4, action_col5 = st.columns([1, 1, 1, 1, 1])
    
    with action_col1:
        if st.button("➕ Add Building", key="quick_add_building", use_container_width=True):
            # Clear any existing form data
            if 'building_form_data' in st.session_state:
                del st.session_state.building_form_data
                
            st.session_state.entry_mode = "add_building"
            st.rerun()
            
    with action_col2:
        if st.button("📊 Enter Energy Data", key="quick_add_data", use_container_width=True, type="primary"):
            # Only proceed if we have buildings
            if not st.session_state.buildings:
                st.warning("Please add a building first before entering data.")
                return
                
            # If no building is selected but buildings exist, select the first one
            if not st.session_state.selected_building and st.session_state.buildings:
                st.session_state.selected_building = st.session_state.buildings[0]["id"]
                
            st.session_state.entry_mode = "multiple"
            st.rerun()
            
    with action_col3:
        if st.button("🔄 Compare Buildings", key="quick_compare", use_container_width=True):
            if len(st.session_state.buildings) > 1:
                st.session_state.selected_view = "compare"
                st.rerun()
            else:
                st.warning("You need at least 2 buildings to make a comparison.")
                
    with action_col4:
        if st.button("📈 Year Analysis", key="yearly_analysis", use_container_width=True):
            st.session_state.current_page = "yearly_analysis"
            st.rerun()
                
    with action_col5:
        demo_button_text = "🔍 View Demo" if not st.session_state.demo_mode else "❌ Clear Demo"
        if st.button(demo_button_text, key="quick_demo_toggle", use_container_width=True):
            toggle_demo_mode()
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Display different pages based on state
    if 'entry_mode' in st.session_state and st.session_state.entry_mode is not None:
        if st.session_state.entry_mode == "add_building":
            add_building_form()
            return
        elif st.session_state.entry_mode == "single":
            show_single_month_form()
            return
        elif st.session_state.entry_mode == "multiple":
            show_multiple_month_form()
            return
    
    # Check if we need to select a building first
    if not st.session_state.selected_building:
        building_selection_page()
        return
    
    # Create DataFrame from entries
    df = pd.DataFrame(st.session_state.data_entries)
    
    # Show dashboard if data exists and we have a selected building
    if not df.empty and st.session_state.selected_building in df['building_id'].values:
        show_dashboard(df)
    else:
        # No data for this building yet - improved empty state
        selected_building = None
        for building in st.session_state.buildings:
            if building["id"] == st.session_state.selected_building:
                selected_building = building
                break
        
        if selected_building:
            # Improved empty state for selected building with no data
            st.markdown(f"""
            <div style="text-align: center; margin: 20px 0; padding: 30px 20px; background-color: #f5f5f5; border-radius: 10px;">
                <img src="https://img.icons8.com/fluency/96/000000/add-file.png" alt="Add Data Icon" style="width: 70px; margin-bottom: 15px;">
                <h2>No Data for {selected_building['name']}</h2>
                <p>This building has been added but doesn't have any energy data yet.</p>
                <p style="color: #666; font-size: 0.9rem; margin-top: 10px;">Add energy data to generate reports and visualizations.</p>
            </div>
            
            <div class="card">
                <h3 style="margin-top: 0;">{selected_building['name']} Details</h3>
                <p><strong>Type:</strong> {selected_building['type']} | <strong>Floor Area:</strong> {selected_building['floor_area']} m²</p>
                <p><strong>Address:</strong> {selected_building['address']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Add data options - large, prominent buttons with improved design
        st.markdown("""
        <div style="text-align: center; margin: 30px 0 20px 0;">
            <h2>Add Energy Data</h2>
            <p>Choose how you want to enter data for this building:</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <div class="feature-card">
                <img src="https://img.icons8.com/fluency/48/000000/calendar-month.png" alt="Calendar Icon" style="width: 48px; margin-bottom: 15px;">
                <h3>Single Month Entry</h3>
                <p>Enter data for one specific month at a time</p>
                <p style="font-size: 0.85rem; color: #666; margin-top: 10px;">Ideal for entering recent bills or making corrections</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Add Single Month", key="add_single_month_empty", type="primary", use_container_width=True):
                st.session_state.entry_mode = "single"
                st.rerun()
        
        with col2:
            st.markdown("""
            <div class="feature-card">
                <img src="https://img.icons8.com/fluency/48/000000/calendar.png" alt="Calendar Icon" style="width: 48px; margin-bottom: 15px;">
                <h3>Multiple Months Entry</h3>
                <p>Enter data for multiple months at once</p>
                <p style="font-size: 0.85rem; color: #666; margin-top: 10px;">Best for initial setup or bulk data entry</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Add Multiple Months", key="add_multiple_months_empty", use_container_width=True, type="primary"):
                st.session_state.entry_mode = "multiple"
                st.rerun()
        
        # Option to select different building
        st.markdown("<div style='text-align: center; margin: 20px 0;'>", unsafe_allow_html=True)
        if st.button("← Select Different Building", key="select_diff_building_empty"):
            st.session_state.selected_building = None
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# The error is occurring in the show_dashboard function around line 2906
# Here's a fix to handle the missing 'factor_year' column

def show_dashboard(df):
    """Display the dashboard with all visualisations - improved UX"""
    st.markdown("<h2>Carbon Emissions Dashboard</h2>", unsafe_allow_html=True)
    
    # Show sample data notice if in demo mode
    if st.session_state.demo_mode:
        st.info("📊 Sample data shown for demonstration purposes only. All data is temporary and not saved.")
    
    # Determine if we're comparing or looking at a single building
    if st.session_state.selected_view == "compare":
        show_buildings_comparison()
        return
    
    # Get selected building info
    selected_building = None
    for building in st.session_state.buildings:
        if building["id"] == st.session_state.selected_building:
            selected_building = building
            break
    
    if not selected_building:
        st.error("No building selected. Please select or add a building first.")
        if st.button("Select Building", type="primary"):
            st.session_state.selected_building = None
            st.rerun()
        return
    
    # Filter data for selected building
    building_data = df[df["building_id"] == selected_building["id"]]
    
    # Check if we have years selected
    if not st.session_state.selected_years:
        st.session_state.selected_years = [datetime.now().year]
        st.rerun()
    
    # Filter by selected years
    building_data = building_data[building_data["year"].isin(st.session_state.selected_years)]
    
    # Create exportable data (do this regardless of whether building_data is empty)
    if not building_data.empty:
        export_data = building_data.copy()
        
        # Format export data for better readability
        export_columns = {
            "building_name": "Building",
            "building_type": "Building Type",
            "floor_area": "Floor Area (m²)",
            "year": "Year",
            "month": "Month",
            "electricity_kwh": "Electricity Usage (kWh)",
            "electricity_provider": "Electricity Provider",
            "gas_kwh": "Gas Usage (kWh)",
            "gas_provider": "Gas Provider",
            "electricity_emissions_kg": "Electricity Emissions (kg CO₂e)",
            "gas_emissions_kg": "Gas Emissions (kg CO₂e)",
            "total_emissions_tonnes": "Total Emissions (tonnes CO₂e)"
        }
        
        # Only include columns that exist in the DataFrame
        available_columns = [col for col in export_columns.keys() if col in export_data.columns]
        export_data = export_data[available_columns].rename(columns={col: export_columns[col] for col in available_columns})
    
    # Building info with action buttons - improved card design
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(f"""
        <div class="card" style="border-left: 4px solid #1a73e8;">
            <h3 style="color: #1a73e8; margin-top: 0;">{selected_building['name']}</h3>
            <p><strong>Type:</strong> {selected_building['type']} | <strong>Floor Area:</strong> {selected_building['floor_area']} m²</p>
            <p><strong>Address:</strong> {selected_building['address']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Action buttons in the header
        if st.button("← Change Building", key="select_diff_building", use_container_width=True):
            st.session_state.selected_building = None
            st.rerun()
        
        if st.button("🔄 Compare Buildings", key="compare_buildings_btn", use_container_width=True):
            st.session_state.selected_view = "compare"
            st.rerun()
    
    # Add data buttons - Always visible at the top for easy access
    st.markdown("<h3>Add Data</h3>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Add Single Month", key="add_single_month_top", use_container_width=True):
            st.session_state.entry_mode = "single"
            st.rerun()
    
    with col2:
        if st.button("Add Multiple Months", key="add_multiple_months_top", use_container_width=True, type="primary"):
            st.session_state.entry_mode = "multiple"
            st.rerun()
    
    if building_data.empty:
        # Improved empty state with better guidance
        st.markdown(f"""
        <div style="text-align: center; margin: 30px 0; padding: 40px 20px; background-color: #f5f5f5; border-radius: 10px;">
            <img src="https://img.icons8.com/fluency/96/000000/add-file.png" alt="Add Data Icon" style="width: 70px; margin-bottom: 15px;">
            <h2>No Data Available</h2>
            <p>No data available for {selected_building['name']} in the selected years ({', '.join(str(y) for y in st.session_state.selected_years)}).</p>
            <p style="color: #666; font-size: 0.9rem; margin-top: 15px;">You can add data using the buttons above or select different years in the sidebar.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Add CSV download button - only if we have data - improved design
    st.markdown("""
    <div style="margin: 20px 0;">
    """, unsafe_allow_html=True)
    st.markdown(
        get_csv_download_link(export_data, f"{selected_building['name'].replace(' ','_')}_carbon_data.csv", "📥 Download Data as CSV"),
        unsafe_allow_html=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Show which emission factors were used - FIX: Handle missing 'factor_year' column
    if 'factor_year' in building_data.columns:
        factor_years = building_data['factor_year'].unique()
        factor_info = ", ".join([str(year) for year in factor_years])
        
        st.markdown(f"""
        <div class="info-box">
            <strong>Reporting Information:</strong> Using {st.session_state.reporting_period.capitalize()} Year reporting period with {factor_info} DEFRA emission factors.
        </div>
        """, unsafe_allow_html=True)
    else:
        # Alternative message when factor_year is not available
        st.markdown(f"""
        <div class="info-box">
            <strong>Reporting Information:</strong> Using {st.session_state.reporting_period.capitalize()} Year reporting period with latest DEFRA emission factors.
        </div>
        """, unsafe_allow_html=True)

    # Rest of function remains unchanged
    # Visualisation data format
    dashboard_data = []
    for entry in building_data.to_dict('records'):
        dashboard_data.append({
            "month": entry["month"],
            "Electricity": entry["electricity_kwh"],
            "Gas": entry["gas_kwh"],
            "Electricity Emissions": entry["electricity_emissions_kg"]/1000,
            "Gas Emissions": entry["gas_emissions_kg"]/1000,
            "year": entry["year"]
        })
    
    dashboard_df = pd.DataFrame(dashboard_data)
    
    # Show dashboard metrics
    show_dashboard_metrics(building_data)
    
    # Create tabs for different visualisations - improved tab design
    tabs = st.tabs(["📈 Energy Usage", "💨 Emissions", "📊 Yearly Comparison"])
    
    
    with tabs[0]:
        # Usage chart
        st.subheader("Energy Usage Trends")
        
        # Show year filter if multiple years
        if len(st.session_state.selected_years) > 1:
            selected_year = st.selectbox(
                "📅 Select year to view",
                options=sorted(dashboard_df["year"].unique()),
                index=0,
                key="usage_year_selector"
            )
            year_data = dashboard_df[dashboard_df["year"] == selected_year]
        else:
            year_data = dashboard_df
        
        if not year_data.empty:
            fig = create_usage_chart(year_data)
            st.plotly_chart(fig, use_container_width=True)
            
            # Add simple insights with improved design
            if len(year_data) >= 3:
                highest_month = year_data.loc[year_data["Electricity"].idxmax(), "month"]
                lowest_month = year_data.loc[year_data["Electricity"].idxmin(), "month"]
                avg_elec = year_data["Electricity"].mean()
                avg_gas = year_data["Gas"].mean()
                
                st.markdown(f"""
                <div class="card">
                    <h4 style="margin-top: 0;">Key Usage Insights</h4>
                    <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                        <div style="flex: 1; min-width: 200px;">
                            <p><strong>Electricity Highlights:</strong></p>
                            <ul>
                                <li>Highest usage: <strong>{highest_month}</strong> ({year_data["Electricity"].max():,.0f} kWh)</li>
                                <li>Lowest usage: <strong>{lowest_month}</strong> ({year_data["Electricity"].min():,.0f} kWh)</li>
                                <li>Average monthly usage: <strong>{avg_elec:,.0f} kWh</strong></li>
                            </ul>
                        </div>
                        <div style="flex: 1; min-width: 200px;">
                            <p><strong>Gas Highlights:</strong></p>
                            <ul>
                                <li>Highest usage: <strong>{year_data.loc[year_data["Gas"].idxmax(), "month"]}</strong> ({year_data["Gas"].max():,.0f} kWh)</li>
                                <li>Lowest usage: <strong>{year_data.loc[year_data["Gas"].idxmin(), "month"]}</strong> ({year_data["Gas"].min():,.0f} kWh)</li>
                                <li>Average monthly usage: <strong>{avg_gas:,.0f} kWh</strong></li>
                            </ul>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    with tabs[1]:
        # Emissions chart
        st.subheader("Carbon Emissions Analysis")
        
        # Show year filter if multiple years
        if len(st.session_state.selected_years) > 1:
            selected_year = st.selectbox(
                "📅 Select year to view",
                options=sorted(dashboard_df["year"].unique()),
                index=0,
                key="emissions_year_selector"
            )
            year_data = dashboard_df[dashboard_df["year"] == selected_year]
        else:
            year_data = dashboard_df
        
        if not year_data.empty:
            fig = create_emissions_chart(year_data)
            st.plotly_chart(fig, use_container_width=True)
            
            # Add emissions breakdown pie chart with improved design
            st.subheader("Emissions Source Breakdown")
            year_building_data = building_data[building_data["year"] == selected_year] if len(st.session_state.selected_years) > 1 else building_data
            fig = create_emissions_pie_chart(year_building_data)
            st.plotly_chart(fig)
            
            # Add scope explanation with improved design
            st.markdown("""
            <div class="card">
                <h4 style="margin-top: 0;">Carbon Emissions by Scope</h4>
                <p>
                    <span class="scope-badge scope1-badge">SCOPE 1</span> Direct emissions from gas usage for heating
                </p>
                <p>
                    <span class="scope-badge scope2-badge">SCOPE 2</span> Indirect emissions from purchased electricity
                </p>
                <p style="font-size: 0.9rem; color: #666; margin-top: 10px;">
                    <strong>Note:</strong> Based on latest DEFRA conversion factors. Scope 3 emissions (such as supply chain, business travel, and waste) 
                    are not included in this dashboard yet.
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    with tabs[2]:
        # Yearly comparison with improved visuals
        st.subheader("Year-on-Year Comparison")
        
        if len(st.session_state.selected_years) > 1:
            yearly_fig = create_yearly_comparison_chart(building_data)
            st.plotly_chart(yearly_fig, use_container_width=True)
            
            # Calculate year-on-year change
            yearly_totals = building_data.groupby('year').agg({
                'electricity_kwh': 'sum',
                'gas_kwh': 'sum',
                'total_emissions_tonnes': 'sum'
            }).reset_index()
            
            if len(yearly_totals) > 1:
                yearly_totals = yearly_totals.sort_values('year')
                
                # Calculate percentage changes
                yearly_totals['elec_change'] = yearly_totals['electricity_kwh'].pct_change() * 100
                yearly_totals['gas_change'] = yearly_totals['gas_kwh'].pct_change() * 100
                yearly_totals['emissions_change'] = yearly_totals['total_emissions_tonnes'].pct_change() * 100
                
                # Create comparison table with improved design
                st.markdown("""
                <div class="card">
                    <h4 style="margin-top: 0;">Year-on-Year Changes</h4>
                """, unsafe_allow_html=True)
                
                yearly_totals_filtered = yearly_totals[yearly_totals['year'] > yearly_totals['year'].min()]
                
                # Create a table layout
                st.markdown("""
                <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                    <thead>
                        <tr style="background-color: #f1f1f1;">
                            <th style="padding: 8px; text-align: left; border-bottom: 1px solid #ddd;">Years</th>
                            <th style="padding: 8px; text-align: center; border-bottom: 1px solid #ddd;">Electricity Change</th>
                            <th style="padding: 8px; text-align: center; border-bottom: 1px solid #ddd;">Gas Change</th>
                            <th style="padding: 8px; text-align: center; border-bottom: 1px solid #ddd;">Emissions Change</th>
                        </tr>
                    </thead>
                    <tbody>
                """, unsafe_allow_html=True)
                
                for _, row in yearly_totals_filtered.iterrows():
                    elec_change = row['elec_change']
                    gas_change = row['gas_change']
                    emissions_change = row['emissions_change']
                    
                    elec_color = 'green' if elec_change < 0 else ('#ff9800' if abs(elec_change) < 1 else 'red')
                    gas_color = 'green' if gas_change < 0 else ('#ff9800' if abs(gas_change) < 1 else 'red')
                    emissions_color = 'green' if emissions_change < 0 else ('#ff9800' if abs(emissions_change) < 1 else 'red')
                    
                    elec_icon = '↓' if elec_change < 0 else ('→' if abs(elec_change) < 1 else '↑')
                    gas_icon = '↓' if gas_change < 0 else ('→' if abs(gas_change) < 1 else '↑')
                    emissions_icon = '↓' if emissions_change < 0 else ('→' if abs(emissions_change) < 1 else '↑')
                    
                    prev_year = row['year'] - 1
                    
                    st.markdown(f"""
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{prev_year} to {row['year']}</td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: center;">
                            <span style="color: {elec_color}; font-weight: bold;">{elec_icon} {elec_change:.1f}%</span>
                        </td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: center;">
                            <span style="color: {gas_color}; font-weight: bold;">{gas_icon} {gas_change:.1f}%</span>
                        </td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: center;">
                            <span style="color: {emissions_color}; font-weight: bold;">{emissions_icon} {emissions_change:.1f}%</span>
                        </td>
                    </tr>
                    """, unsafe_allow_html=True)
                
                st.markdown("""
                    </tbody>
                </table>
                """, unsafe_allow_html=True)
                
                # Add interpretation
                avg_emissions_change = yearly_totals_filtered['emissions_change'].mean()
                
                if avg_emissions_change < 0:
                    interpretation = f"Overall, emissions are trending downward with an average reduction of {abs(avg_emissions_change):.1f}% per year."
                elif abs(avg_emissions_change) < 1:
                    interpretation = "Overall, emissions are remaining relatively stable year-over-year."
                else:
                    interpretation = f"Overall, emissions are trending upward with an average increase of {avg_emissions_change:.1f}% per year."
                
                st.markdown(f"""
                <p style="margin-top: 15px;"><strong>Interpretation:</strong> {interpretation}</p>
                """, unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Add link to detailed analysis page
                st.markdown("""
                <div class="card" style="text-align: center; padding: 15px; margin-top: 15px;">
                    <h4 style="margin-top: 0;">Need More Detailed Analysis?</h4>
                    <p>Visit our Year-on-Year Analysis page for comprehensive emissions analytics and trends.</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("📈 Go to Detailed Analysis", type="primary", use_container_width=True):
                    st.session_state.current_page = "yearly_analysis"
                    st.rerun()
                
        else:
            # Improved empty state for year comparison
            st.markdown("""
            <div style="text-align: center; padding: 30px; background-color: #f5f5f5; border-radius: 10px; margin: 20px 0;">
                <img src="https://img.icons8.com/fluency/96/000000/calendar-plus.png" alt="Calendar Icon" style="width: 60px; margin-bottom: 15px;">
                <h3>Select Multiple Years to Compare</h3>
                <p>Year-on-year comparison requires data from multiple years.</p>
            </div>
            
            <div class="card">
                <h4 style="margin-top: 0;">How to Compare Multiple Years:</h4>
                <ol>
                    <li>In the sidebar, use the "Year Selection" dropdown to choose multiple years</li>
                    <li>Add data for multiple years using the "Add Multiple Months Data" button</li>
                    <li>Return to this tab to see the comparison</li>
                </ol>
            </div>
            """, unsafe_allow_html=True)
    
    # with tabs[3]:
    #     # Environmental impact with improved design
    #     total_emissions = building_data["total_emissions_tonnes"].sum()
    #     show_environmental_impact(total_emissions)
    
    # # Add tabular view of the data with improved design
    # with st.expander("View Detailed Data Table", expanded=False):
    #     st.markdown("""
    #     <p style="margin-bottom: 10px; font-size: 0.9rem;">
    #         The table below shows all recorded data for the selected building and time period. 
    #         You can sort and filter this data directly in the table.
    #     </p>
    #     """, unsafe_allow_html=True)
    #     st.dataframe(export_data, use_container_width=True)

def invoice_processing_page():
    """Display the invoice processing premium feature page with improved UX"""
    st.markdown("<h1>Invoice Processing</h1>", unsafe_allow_html=True)
    
    # Add prototype banner
    add_data_disclaimer()
    
    # Premium feature message with improved design
    st.markdown("""
    <div class="card" style="text-align: center; padding: 2rem; border: 2px dashed #ffc107; margin-bottom: 30px;">
        <h2 style="margin-bottom: 1rem;">Premium Feature <span class="premium-badge">Coming Soon</span></h2>
        <p style="margin-bottom: 1.5rem; max-width: 700px; margin-left: auto; margin-right: auto;">
            This is an optional premium feature. Complete our questionnaire to opt in or learn more.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show preview of feature with improved design
    st.markdown("""
    <div class="card">
        <h3 style="margin-top: 0;">Upload Your Energy Invoices</h3>
        <p>Our system will automatically extract usage data, saving time and ensuring accuracy.</p>
        <p><strong>Note:</strong> This is a preview of the premium invoice processing feature.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="card" style="height: 260px;">
            <h3 style="margin-top: 0;">Electricity Invoices</h3>
            <p style="color: #666;">Upload PDF invoices from your electricity supplier</p>
            <div style="text-align: center; padding: 20px 0;">
                <img src="https://img.icons8.com/fluency/96/000000/pdf.png" alt="PDF Icon" style="width: 60px;">
                <p style="margin-top: 10px; color: #888; font-style: italic;">Drag and drop files here (Premium Feature)</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Disabled uploader
        st.file_uploader(
            "Choose Electricity PDF files",
            type="pdf",
            accept_multiple_files=True,
            key="electricity_files",
            disabled=True,
            label_visibility="collapsed"
        )
    
    with col2:
        st.markdown("""
        <div class="card" style="height: 260px;">
            <h3 style="margin-top: 0;">Gas Invoices</h3>
            <p style="color: #666;">Upload PDF invoices from your gas supplier</p>
            <div style="text-align: center; padding: 20px 0;">
                <img src="https://img.icons8.com/fluency/96/000000/pdf.png" alt="PDF Icon" style="width: 60px;">
                <p style="margin-top: 10px; color: #888; font-style: italic;">Drag and drop files here (Premium Feature)</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Disabled uploader
        st.file_uploader(
            "Choose Gas PDF files",
            type="pdf",
            accept_multiple_files=True,
            key="gas_files",
            disabled=True,
            label_visibility="collapsed"
        )
    
    # Disabled process button with better styling
    st.button("Process Invoices", type="primary", disabled=True, use_container_width=True)
    
    # Premium features list with improved design
    st.markdown("""
    <div class="card" style="margin-top: 30px;">
        <h3 style="margin-top: 0;">Premium Features Include:</h3>
        <div style="display: flex; flex-wrap: wrap; gap: 20px; margin-top: 20px;">
            <div style="flex: 1; min-width: 200px;">
                <div style="display: flex; align-items: center; margin-bottom: 15px;">
                    <img src="https://img.icons8.com/fluency/48/000000/automatic.png" alt="Automatic Icon" style="width: 30px; margin-right: 10px;">
                    <strong>Automatic Data Extraction</strong>
                </div>
                <p style="margin-left: 40px; color: #666; font-size: 0.9rem;">Save hours of manual data entry with AI-powered extraction</p>
            </div>
            <div style="flex: 1; min-width: 200px;">
                <div style="display: flex; align-items: center; margin-bottom: 15px;">
                    <img src="https://img.icons8.com/fluency/48/000000/pdf-2.png" alt="PDF Icon" style="width: 30px; margin-right: 10px;">
                    <strong>PDF Invoice Processing</strong>
                </div>
                <p style="margin-left: 40px; color: #666; font-size: 0.9rem;">Support for all major UK energy suppliers' invoice formats</p>
            </div>
            <div style="flex: 1; min-width: 200px;">
                <div style="display: flex; align-items: center; margin-bottom: 15px;">
                    <img src="https://img.icons8.com/fluency/48/000000/check-all.png" alt="Validation Icon" style="width: 30px; margin-right: 10px;">
                    <strong>Data Validation</strong>
                </div>
                <p style="margin-left: 40px; color: #666; font-size: 0.9rem;">Built-in error checking and anomaly detection</p>
            </div>
            <div style="flex: 1; min-width: 200px;">
                <div style="display: flex; align-items: center; margin-bottom: 15px;">
                    <img src="https://img.icons8.com/fluency/48/000000/repository.png" alt="Bulk Icon" style="width: 30px; margin-right: 10px;">
                    <strong>Bulk Processing</strong>
                </div>
                <p style="margin-left: 40px; color: #666; font-size: 0.9rem;">Upload and process multiple invoices at once</p>
            </div>
        </div>
        <div style="margin-top: 20px; text-align: center; padding-top: 15px; border-top: 1px solid #eee;">
            <p style="font-weight: 500;">Complete our questionnaire to opt in for these premium features.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Contact form
    show_contact_us_form()

def landing_page():
    """Display landing page with improved UX, more engaging content, and UK council-specific focus without unverified claims"""
    # Hero Section with more engaging design and UK focus
    st.markdown("""
    <div class="hero-section">
        <h1>Make Your Council a Climate Leader</h1>
        <p>Track, analyse, and report your carbon emissions to meet UK Net Zero commitments</p>
        <p style="font-size: 1.1rem; margin-top: 10px;">Simple • Accurate • Actionable</p>
        <p style="font-size: 0.9rem; background: rgba(0,0,0,0.2); padding: 0.5rem; border-radius: 0.3rem; max-width: 600px; margin: 1rem auto;">
            Prototype Version: For demonstration only. No data will be saved.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get started button - prominent CTA
    if st.button("Get Started", type="primary", key="get_started_hero", use_container_width=True):
        navigate_to('data_entry')
        st.rerun()
    
    # NEW: Educational section for councils
    st.markdown("""
    <div class="card" style="margin-bottom: 2rem;">
        <h2 style="margin-top: 0;">Why Civic Carbon Tracking Matters Now</h2>
        <div style="display: flex; flex-wrap: wrap; gap: 1.5rem; margin-top: 1rem;">
            <div style="flex: 1; min-width: 250px;">
                <h4 style="color: #33d476; margin-top: 0;">Your Buildings, Your Impact</h4>
                <p>Council-owned buildings contribute significantly to your local authority's direct emissions through electricity and gas usage.</p>
                <p>Tracking this energy consumption helps identify opportunities to reduce both emissions and energy costs.</p>
            </div>
            <div style="flex: 1; min-width: 250px;">
                <h4 style="color: #33d476; margin-top: 0;">From Declaration to Action</h4>
                <p>Many UK local authorities have declared climate emergencies and are looking for ways to translate these commitments into measurable action.</p>
                <p>Carbon tracking creates accountability, helps inform funding decisions, and demonstrates progress to your residents and councillors.</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Direct benefits to council leaders/managers - NEW section
    st.markdown("""
    <h2 style="text-align: center; margin: 2rem 0 1.5rem;">Benefits for Your Council</h2>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <img src="https://img.icons8.com/fluency/48/000000/money-bag-pound.png" alt="Money Icon" style="width: 48px; margin-bottom: 15px;">
            <h3>Financial Benefits</h3>
            <ul>
                <li>Identify energy waste that's costing your council money</li>
                <li>Prioritise upgrades with potential for cost savings</li>
                <li>Create better business cases for retrofitting projects</li>
                <li>Reduce exposure to energy price fluctuations</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#33d476" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom: 15px;">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
            </svg>
            <h3>Compliance Support</h3>
            <ul>
                <li>Help meet SECR reporting requirements</li>
                <li>Support climate emergency declaration commitments</li>
                <li>Generate reports for committee meetings</li>
                <li>Track progress toward UK Net Zero targets</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <img src="https://img.icons8.com/fluency/48/000000/prize.png" alt="Leadership Icon" style="width: 48px; margin-bottom: 15px;">
            <h3>Leadership & Reputation</h3>
            <ul>
                <li>Show residents you're taking climate action seriously</li>
                <li>Demonstrate fiscal responsibility with energy tracking</li>
                <li>Share progress with other councils and partners</li>
                <li>Build towards a low-carbon future for your community</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Informational section on carbon emissions and councils
    st.markdown("""
    <div class="facts-card" style="margin: 2rem 0;">
        <h3 style="margin-top: 0;">Understanding Your Carbon Emissions</h3>
        <p>Council buildings typically generate carbon emissions through energy usage - primarily electricity consumption and gas for heating. By tracking these emissions, councils can:</p>
        <div style="display: flex; flex-wrap: wrap; gap: 1.5rem; margin-top: 1rem;">
            <div style="flex: 1; min-width: 200px;">
                <p><strong>Identify</strong> which buildings are using the most energy</p>
            </div>
            <div style="flex: 1; min-width: 200px;">
                <p><strong>Monitor</strong> the impact of energy efficiency measures</p>
            </div>
            <div style="flex: 1; min-width: 200px;">
                <p><strong>Report</strong> on progress toward climate commitments</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Emissions scope explanation - improved with UK context and council focus
    st.markdown("""
    <div class="card">
        <h3>What We Track for Your Council</h3>
        <p>This dashboard focuses on the emissions you can monitor and potentially reduce:</p>
        <p>
            <span class="scope-badge scope1-badge">SCOPE 1</span> Direct emissions from council buildings including gas for heating
        </p>
        <p>
            <span class="scope-badge scope2-badge">SCOPE 2</span> Indirect emissions from purchased electricity for buildings
        </p>
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 15px;">
            <h4 style="margin-top: 0;">New to Carbon Emissions Tracking?</h4>
            <p style="margin-bottom: 5px;"><strong>Scope 1</strong> = Direct emissions you create and control (like burning gas for heating)</p>
            <p style="margin-bottom: 5px;"><strong>Scope 2</strong> = Indirect emissions from the electricity you purchase</p>
            <p style="margin-bottom: 0; font-style: italic;">UK councils are increasingly focusing on tracking and reducing both Scope 1 and 2 emissions as part of their climate commitments.</p>
        </div>
        <p style="margin-top: 15px;"><strong>Coming Soon:</strong> Fleet vehicle emissions tracking, business travel, and waste management reporting options.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # How it works section - Council specific with clearer benefits
    st.markdown("<h2 style='text-align: center; margin: 2rem 0 1.5rem;'>How It Works for Councils</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <img src="https://img.icons8.com/fluency/48/000000/add-file.png" alt="Input Icon" style="width: 48px; margin-bottom: 15px;">
            <h3>1. Input Your Utility Data</h3>
            <p>Enter electricity and gas consumption from your council utility bills</p>
            <p class="small-text" style="font-size: 0.85rem; color: #666;">No special expertise required - just the kWh figures from your bills</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <img src="https://img.icons8.com/fluency/48/000000/automatic.png" alt="Calculate Icon" style="width: 48px; margin-bottom: 15px;">
            <h3>2. Automatic Calculations</h3>
            <p>We apply the latest DEFRA conversion factors to your energy data</p>
            <p class="small-text" style="font-size: 0.85rem; color: #666;">No more complex spreadsheets or manual calculations</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <img src="https://img.icons8.com/fluency/48/000000/decision.png" alt="Report Icon" style="width: 48px; margin-bottom: 15px;">
            <h3>3. Make Informed Decisions</h3>
            <p>See which buildings need attention and track your progress</p>
            <p class="small-text" style="font-size: 0.85rem; color: #666;">Export reports for council committees and leadership</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Features comparison with council value proposition
    st.markdown("""
    <h2 style='text-align: center; margin: 2rem 0 1.5rem;'>Features for Councils</h2>
    <div class="card">
        <div style="display: flex; flex-wrap: wrap; gap: 1.5rem;">
            <div style="flex: 1; min-width: 250px;">
                <h3 style="color: #2E86C1;">Included Features</h3>
                <ul>
                    <li>Multiple building energy tracking</li>
                    <li>Automatic DEFRA emissions calculations</li>
                    <li>Building comparison tools</li>
                    <li>Year-on-year carbon reduction tracking</li>
                    <li>CSV export for committee reports</li>
                    <li>Seasonal trend analysis</li>
                </ul>
            </div>
            <div style="flex: 1; min-width: 250px;">
                <h3 style="color: #2E86C1;">Premium Features <span class="premium-badge">Coming Soon</span></h3>
                <ul>
                    <li>Automatic bill processing from major UK energy suppliers</li>
                    <li>SECR-ready reports with one click</li>
                    <li>Carbon reduction roadmap planning tools</li>
                    <li>Multi-council benchmarking</li>
                    <li>Fleet vehicle and waste emissions tracking</li>
                </ul>
                <p style="margin-top: 1rem;"><strong>Complete our questionnaire to opt in for premium features</strong></p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Take Action section - actionable CTAs
    st.markdown("""
    <h2 style='text-align: center; margin: 1.5rem 0 1rem;'>Ready to Take Action?</h2>
    <p style='text-align: center; margin-bottom: 2rem;'>Start tracking your council's carbon emissions today</p>
    """, unsafe_allow_html=True)
    
    # Action buttons in a row
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Try the Demo", key="try_demo_landing", use_container_width=True, type="primary"):
            st.session_state.demo_mode = True
            load_demo_data()
            navigate_to('data_entry')
            st.rerun()
        st.markdown("<p style='text-align: center; font-size: 0.85rem;'>See how it works with sample data</p>", unsafe_allow_html=True)
    
    with col2:
        if st.button("Get Started", key="get_started_bottom", use_container_width=True):
            navigate_to('data_entry')
            st.rerun()
        st.markdown("<p style='text-align: center; font-size: 0.85rem;'>Add your own council buildings</p>", unsafe_allow_html=True)
    
    with col3:
        if st.button("Contact Us", key="contact_us", use_container_width=True):
            navigate_to('contact_us')
            st.rerun()
        st.markdown("<p style='text-align: center; font-size: 0.85rem;'>Learn more about our solutions</p>", unsafe_allow_html=True)
    
    # Contact form
    show_contact_us_form()

def contact_us_page():
    """Display the contact us page with improved UX"""
    st.markdown("<h1>Contact Us</h1>", unsafe_allow_html=True)
    # Add prototype banner
    add_data_disclaimer()
    # Add a more engaging introduction - fixed to properly render HTML
    st.markdown("""
        <div class="card" style="margin-bottom: 30px;">
        <h3 style="margin-top: 0;">Get in Touch</h3>
        <p>Have questions about our carbon reporting solution? Looking to unlock premium features?</p>
        <p>Complete the form below and our team will get back to you within 24 hours.</p>
        <p>Email us directly at <a href="mailto:hello@civiccarbon.com">hello@civiccarbon.com</a></p>
        </div>
        """, unsafe_allow_html=True)
    # Use columns instead of flex layout for better compatibility
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
            <div style="text-align: center;">
            <img src="https://img.icons8.com/fluency/48/000000/support.png" alt="Support Icon" style="width: 40px; margin-bottom: 10px;">
            <h4 style="margin: 5px 0;">Dedicated Support</h4>
            <p style="color: #666; font-size: 0.9rem;">Our team of carbon reporting experts is ready to help</p>
            </div>
            """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
            <div style="text-align: center;">
            <img src="https://img.icons8.com/fluency/48/000000/calendar-26.png" alt="Calendar Icon" style="width: 40px; margin-bottom: 10px;">
            <h4 style="margin: 5px 0;">Quick Response</h4>
            <p style="color: #666; font-size: 0.9rem;">We aim to respond to all inquiries within 24 hours</p>
            </div>
            """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
            <div style="text-align: center;">
            <img src="https://img.icons8.com/fluency/48/000000/training.png" alt="Training Icon" style="width: 40px; margin-bottom: 10px;">
            <h4 style="margin: 5px 0;">Free Consultation</h4>
            <p style="color: #666; font-size: 0.9rem;">Get a free 30-minute consultation on your reporting needs</p>
            </div>
            """, unsafe_allow_html=True)
    # Add some spacing before the contact form
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    # Contact form
    show_contact_us_form()

# --- MAIN APP ---
def main():
    """Main application function with updated navigation"""
    # Load CSS for styling
    load_css()
    
    # Add prototype banner
    add_prototype_banner()
    
    # Sidebar navigation with improved design
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/000000/natural-food.png", width=80)
        st.markdown("<h1 style='margin-top: 0;'>Civic Carbon</h1>", unsafe_allow_html=True)
        
        # Prototype notice
        st.warning("🔔 PROTOTYPE VERSION: No data will be saved. For demonstration only.")
        
        # Demo mode indicator
        if st.session_state.demo_mode:
            st.success("✓ Demo data loaded")
        
        st.markdown("<h3>Navigation</h3>", unsafe_allow_html=True)
        
        # Navigation buttons with improved styling
        if st.button("🏠 Home", key="nav_home", use_container_width=True):
            navigate_to('landing')
        
        if st.button("📊 Dashboard", key="nav_dashboard", use_container_width=True):
            navigate_to('data_entry')
        
        if st.button("📈 Year Analysis", key="nav_yearly", use_container_width=True):
            navigate_to('yearly_analysis')
        
        if st.button("📄 Invoice Processing", key="nav_invoice", use_container_width=True):
            navigate_to('invoice_processing')
        
        if st.button("📞 Contact Us", key="nav_contact", use_container_width=True):
            navigate_to('contact_us')
        
        # Demo data toggle
        st.markdown("<hr>", unsafe_allow_html=True)
        
        st.write("Sample Data:")
        if st.button(
            "🔍 Load Demo Data" if not st.session_state.demo_mode else "❌ Clear Demo Data", 
            key="toggle_demo",
            use_container_width=True
        ):
            toggle_demo_mode()
            st.rerun()
        
        # Building and Year selection - improved UI
        if st.session_state.buildings:
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("<h4>Data Selection</h4>", unsafe_allow_html=True)
            
            # Building quick select with improved styling
            if len(st.session_state.buildings) > 0:
                st.markdown("<p style='margin-bottom: 5px;'><strong>Building:</strong></p>", unsafe_allow_html=True)
                
                building_names = [b["name"] for b in st.session_state.buildings]
                building_ids = [b["id"] for b in st.session_state.buildings]
                
                selected_index = 0
                if st.session_state.selected_building:
                    try:
                        selected_index = building_ids.index(st.session_state.selected_building)
                    except ValueError:
                        selected_index = 0
                
                selected_building_name = st.selectbox(
                    "Select Building",
                    options=building_names,
                    index=selected_index,
                    label_visibility="collapsed"
                )
                
                # Set selected building ID
                selected_idx = building_names.index(selected_building_name)
                if building_ids[selected_idx] != st.session_state.selected_building:
                    st.session_state.selected_building = building_ids[selected_idx]
                    st.session_state.selected_view = "all"
                    st.rerun()
            
            # Year selection with improved UI
            st.markdown("<p style='margin-bottom: 5px; margin-top: 15px;'><strong>Years to Display:</strong></p>", unsafe_allow_html=True)
            
            years = st.multiselect(
                "Year Selection",
                options=AVAILABLE_YEARS,
                default=st.session_state.selected_years,
                label_visibility="collapsed"
            )
            
            if years and years != st.session_state.selected_years:
                st.session_state.selected_years = years
                st.rerun()
            
            # Reporting period settings
            st.markdown("<p style='margin-bottom: 5px; margin-top: 15px;'><strong>Reporting Period:</strong></p>", unsafe_allow_html=True)
            
            reporting_period = st.selectbox(
                "Reporting Period",
                options=list(REPORTING_PERIODS.keys()),
                format_func=lambda x: REPORTING_PERIODS[x],
                index=list(REPORTING_PERIODS.keys()).index(st.session_state.reporting_period),
                key="sidebar_reporting_period",
                label_visibility="collapsed"
            )
            
            # Update the reporting period in session state
            if reporting_period != st.session_state.reporting_period:
                st.session_state.reporting_period = reporting_period
                st.rerun()
        
        # Help information with improved styling
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
                <ul style="padding-left: 20px; margin-top: 0;">
                    <li>Based on latest DEFRA conversion factors</li>
                    <li>Supports SECR reporting requirements</li>
                    <li>Updated annually with latest factors</li>
                    <li>Compliant with Greenhouse Gas Protocol</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        with st.expander("About Emissions Factors"):
            st.markdown("""
            <div>
                <p>Factors are applied based on your reporting period:</p>
                <ul style="padding-left: 20px; margin-top: 0;">
                    <li><strong>Calendar Year:</strong> Same year's factors</li>
                    <li><strong>Financial Year (Apr-Mar):</strong> Factors from year with most months</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        # Add version information
        st.markdown("<div style='margin-top: 30px; font-size: 0.8rem; color: #888; text-align: center;'>v1.0.0 - Prototype</div>", unsafe_allow_html=True)
    
    # Main content based on current page
    if st.session_state.current_page == 'landing':
        landing_page()
    elif st.session_state.current_page == 'data_entry':
        data_entry_page()
    elif st.session_state.current_page == 'yearly_analysis':
        show_yearly_analysis()
    elif st.session_state.current_page == 'invoice_processing':
        invoice_processing_page()
    elif st.session_state.current_page == 'contact_us':
        contact_us_page()

if __name__ == "__main__":
    main()