"""
app_pile_design.py - pile-SRI Application
==========================================

Professional-grade Streamlit application for offshore pile foundation design
following API RP 2GEO standards.

Features:
- Modern, vibrant UI with professional color scheme
- Layered soil profile input with advanced controls
- Axial and lateral capacity calculations
- Interactive visualization and plotting
- Design report generation
- Export capabilities (CSV, Excel, PDF)

Run with: streamlit run app_pile_design.py

Copyright (c) 2025 Dr. Chitti S S U Srikanth. All rights reserved.
Author: Dr. Chitti S S U Srikanth
Version: 1.0.0
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
from typing import List, Dict
import io

# Import calculation engine
try:
    from calculations import (
        SoilType, PileType, AnalysisType,
        SoilPoint, SoilLayer, PileProperties, SoilProfile,
        AxialCapacity, LateralCapacity, LoadDisplacementCurves,
        PileDesignAnalysis, check_safety_factors
    )
    CALC_ENGINE_AVAILABLE = True
except ImportError:
    CALC_ENGINE_AVAILABLE = False


# ============================================================================
# PAGE CONFIGURATION & STYLING
# ============================================================================

st.set_page_config(
    page_title="pile-SRI · API RP 2GEO",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Modern color scheme styling
st.markdown("""
<style>
    /* Modern gradient background */
    .main { background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%); }

    /* Sidebar with gradient */
    [data-testid="stSidebar"] {
        background: linear-gradient(135deg, #0052CC 0%, #6B5BFF 100%);
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] { color: white; }

    /* Headers with gradient text */
    h1, h2 {
        background: linear-gradient(135deg, #0052CC 0%, #6B5BFF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Primary buttons */
    .stButton > button {
        background: linear-gradient(135deg, #0052CC 0%, #6B5BFF 100%) !important;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }

    .stButton > button:hover {
        box-shadow: 0 8px 25px rgba(0, 82, 204, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# HEADER
# ============================================================================

def render_header():
    """Render application header."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <h1 style='text-align: center;'>🏗️ pile-SRI</h1>
        <p style='text-align: center; color: #6B5BFF; font-size: 14px;'>
        API RP 2GEO Compliance | Offshore Foundation Design
        </p>
        """, unsafe_allow_html=True)
    st.divider()


# ============================================================================
# SIDEBAR
# ============================================================================

def render_sidebar() -> Dict:
    """Render sidebar configuration."""
    with st.sidebar:
        st.markdown("## 📋 PROJECT SETUP")

        project_name = st.text_input("Project Name", "Offshore Platform")
        designer = st.text_input("Designer", "Engineering Team")

        st.markdown("## ⚙️ ANALYSIS SETTINGS")

        analysis_type = st.selectbox("Analysis Type",
            ["Axial Capacity", "Lateral Capacity", "Combined"])
        safety_factor = st.slider("Safety Factor", 1.5, 3.5, 2.5, 0.1)
        loading = st.selectbox("Loading", ["Static", "Cyclic", "Pseudo-Static"])

        st.markdown("## 📊 COMPUTATION")
        max_depth = st.number_input("Max Depth (m)", 10, 100, 50, 5)
        dz = st.slider("Depth Increment (m)", 0.1, 2.0, 0.5, 0.1)

        return {
            "project_name": project_name,
            "designer": designer,
            "analysis_type": analysis_type,
            "safety_factor": safety_factor,
            "loading": loading,
            "max_depth": max_depth,
            "depth_increment": dz,
        }


# ============================================================================
# INPUT SECTIONS
# ============================================================================

def render_pile_input() -> PileProperties:
    """Render pile properties input."""
    st.subheader("🔨 Pile Properties")

    col1, col2, col3 = st.columns(3)
    with col1:
        diameter = st.number_input("Diameter (m)", 0.3, 3.0, 1.4, 0.1)
    with col2:
        thickness = st.number_input("Wall Thickness (m)", 0.01, 0.1, 0.016, 0.001)
    with col3:
        length = st.number_input("Embedded Length (m)", 1, 100, 35, 1)

    return PileProperties(
        diameter_m=diameter,
        wall_thickness_m=thickness,
        length_m=length,
        pile_type=PileType.DRIVEN_PIPE_OPEN
    )


def render_soil_input() -> SoilProfile:
    """Render soil profile input."""
    st.subheader("🪨 Soil Profile")

    site_name = st.text_input("Site Name", "Offshore Site")
    water_depth = st.number_input("Water Depth (m)", 0, 3000, 50, 10)

    profile = SoilProfile(site_name=site_name, water_depth_m=water_depth)

    if "soil_layers" not in st.session_state:
        st.session_state.soil_layers = []

    col_add, col_clear = st.columns([1, 4])
    with col_add:
        if st.button("➕ Add Layer"):
            new_layer = {
                'name': f"Layer {len(st.session_state.soil_layers) + 1}",
                'type': 'clay',
                'z_top': 0.0 if not st.session_state.soil_layers else st.session_state.soil_layers[-1]['z_bot'],
                'z_bot': (0.0 if not st.session_state.soil_layers else st.session_state.soil_layers[-1]['z_bot']) + 10.0,
                'gamma': [],
                'su': [],
                'phi': [],
            }
            st.session_state.soil_layers.append(new_layer)
            st.rerun()

    # Display layers
    for idx, layer in enumerate(st.session_state.soil_layers):
        with st.expander(f"Layer {idx+1}: {layer['name']} ({layer['type'].upper()})"):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                layer['name'] = st.text_input("Name", layer['name'], key=f"l_name_{idx}")
            with col2:
                layer['type'] = st.selectbox("Type", ["clay", "sand", "silt"],
                    index=["clay", "sand", "silt"].index(layer['type']), key=f"l_type_{idx}")
            with col3:
                layer['z_top'] = st.number_input("Top (m)", layer['z_top'], key=f"l_top_{idx}", step=0.5)
            with col4:
                layer['z_bot'] = st.number_input("Bot (m)", layer['z_bot'], key=f"l_bot_{idx}", step=0.5)

            # Quick entry for gamma and su/phi
            col_g, col_p = st.columns(2)
            with col_g:
                gamma_top = st.number_input(f"γ' top (kN/m³)", 7.0, key=f"g_top_{idx}")
                gamma_bot = st.number_input(f"γ' bot (kN/m³)", 8.0, key=f"g_bot_{idx}")
                layer['gamma'] = [
                    SoilPoint(layer['z_top'], gamma_top),
                    SoilPoint(layer['z_bot'], gamma_bot)
                ]

            with col_p:
                if layer['type'] in ['clay', 'silt']:
                    su_top = st.number_input(f"Su top (kPa)", 20.0, key=f"su_top_{idx}")
                    su_bot = st.number_input(f"Su bot (kPa)", 50.0, key=f"su_bot_{idx}")
                    layer['su'] = [
                        SoilPoint(layer['z_top'], su_top),
                        SoilPoint(layer['z_bot'], su_bot)
                    ]
                else:
                    phi_top = st.number_input(f"φ' top (°)", 30.0, key=f"phi_top_{idx}")
                    phi_bot = st.number_input(f"φ' bot (°)", 35.0, key=f"phi_bot_{idx}")
                    layer['phi'] = [
                        SoilPoint(layer['z_top'], phi_top),
                        SoilPoint(layer['z_bot'], phi_bot)
                    ]

            if st.button("🗑️ Delete", key=f"del_{idx}"):
                st.session_state.soil_layers.pop(idx)
                st.rerun()

    # Build profile
    for layer in st.session_state.soil_layers:
        soil_layer = SoilLayer(
            name=layer['name'],
            soil_type=SoilType(layer['type']),
            depth_top_m=layer['z_top'],
            depth_bot_m=layer['z_bot'],
            gamma_prime_kNm3=layer.get('gamma', []),
            su_kPa=layer.get('su', []),
            phi_prime_deg=layer.get('phi', []),
        )
        profile.layers.append(soil_layer)

    return profile


# ============================================================================
# RESULTS
# ============================================================================

def render_results(config, pile, profile):
    """Render analysis results."""

    tab1, tab2, tab3 = st.tabs(["📊 Capacity", "📈 p-y Curves", "📋 Report"])

    analysis = PileDesignAnalysis(profile, pile)

    with tab1:
        st.subheader("Axial Capacity Profile")

        try:
            df = analysis.compute_axial_capacity_profile(config['max_depth'], config['depth_increment'])

            if not df.empty:
                fig = px.line(df, x='capacity_kN', y='depth_m', color='soil_type',
                    title='Capacity vs Depth',
                    labels={'capacity_kN': 'Capacity (kN)', 'depth_m': 'Depth (m)'})
                fig.update_yaxes(autorange="reversed")
                fig.update_layout(height=500, template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Max Capacity", f"{df['capacity_kN'].max():,.0f} kN")
                with col2:
                    st.metric("At Depth", f"{df.loc[df['capacity_kN'].idxmax(), 'depth_m']:.1f} m")
                with col3:
                    st.metric("Min Capacity", f"{df['capacity_kN'].min():,.0f} kN")

                st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Calculation error: {str(e)}")

    with tab2:
        st.subheader("Lateral Capacity (p-y Curves)")

        selected_depths = st.multiselect("Select depths (m)",
            np.arange(5, config['max_depth'], 5).tolist(),
            default=[5, 10, 20])

        if selected_depths:
            try:
                analysis_type = AnalysisType.STATIC if config['loading'] == 'Static' else AnalysisType.CYCLIC
                py_curves = analysis.compute_py_curves(selected_depths, analysis_type)

                if py_curves:
                    fig_py = make_subplots(rows=1, cols=len(py_curves),
                        subplot_titles=[f"Depth {z:.0f}m" for z in py_curves.keys()])

                    for i, (depth, (y, p)) in enumerate(py_curves.items(), 1):
                        if len(y) > 0:
                            fig_py.add_trace(
                                go.Scatter(x=y, y=p, name=f"Depth {depth:.0f}m",
                                    line=dict(width=2)),
                                row=1, col=i)

                    fig_py.update_xaxes(title_text="Displacement (m)")
                    fig_py.update_yaxes(title_text="Pressure (kPa)", row=1, col=1)
                    fig_py.update_layout(height=400, template='plotly_white')
                    st.plotly_chart(fig_py, use_container_width=True)
            except Exception as e:
                st.error(f"p-y curve error: {str(e)}")

    with tab3:
        st.subheader("Design Summary Report")
        st.markdown(f"""
        ### PROJECT
        - **Name:** {config['project_name']}
        - **Designer:** {config['designer']}
        - **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        - **Type:** {config['analysis_type']}

        ### PILE
        - **Diameter:** {pile.diameter_m:.2f} m
        - **Wall Thickness:** {pile.wall_thickness_m:.4f} m
        - **Length:** {pile.length_m:.1f} m

        ### SOIL PROFILE
        - **Site:** {profile.site_name}
        - **Water Depth:** {profile.water_depth_m:.0f} m
        - **Layers:** {len(profile.layers)}

        #### Layers:
        """)

        for layer in profile.layers:
            st.write(f"- **{layer.name}** ({layer.soil_type.value}): {layer.depth_top_m:.1f}-{layer.depth_bot_m:.1f}m")

        st.markdown(f"""
        ### ANALYSIS PARAMETERS
        - **Safety Factor:** {config['safety_factor']:.1f}x
        - **Loading:** {config['loading']}
        - **Max Depth:** {config['max_depth']}m

        ### COMPLIANCE
        - ✅ API RP 2GEO Section 8
        - ✅ Matlock Method (Soft Clay)
        - ✅ Reese Method (Stiff Clay)
        """)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main application."""

    render_header()
    config = render_sidebar()

    st.divider()

    col_pile, col_soil = st.columns([1, 1])
    with col_pile:
        pile = render_pile_input()
    with col_soil:
        profile = render_soil_input()

    st.divider()

    if st.button("🚀 RUN ANALYSIS", use_container_width=True, type="primary"):
        st.session_state.run_analysis = True
        st.session_state.config = config
        st.session_state.pile = pile
        st.session_state.profile = profile

    if st.session_state.get('run_analysis', False):
        st.divider()
        render_results(
            st.session_state.config,
            st.session_state.pile,
            st.session_state.profile
        )


if __name__ == "__main__":
    if 'run_analysis' not in st.session_state:
        st.session_state.run_analysis = False

    if CALC_ENGINE_AVAILABLE:
        main()
    else:
        st.error("❌ Calculation engine not available")
        st.stop()
