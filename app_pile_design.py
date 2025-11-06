"""
app_pile_design.py - pile-SRI Application
==========================================

Professional-grade Streamlit application for offshore pile foundation design
following API RP 2GEO standards.

Features:
- Modern, vibrant UI with professional color scheme
- Enhanced soil profile input with multiple data points per parameter
- Axial and lateral capacity calculations
- Interactive visualization and plotting
- Design report generation
- Export capabilities (CSV, Excel, PDF)

Run with: streamlit run app_pile_design.py

Copyright (c) 2025 Dr. Chitti S S U Srikanth. All rights reserved.
Author: Dr. Chitti S S U Srikanth
Version: 1.0.1
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

# Modern color scheme styling with fixed sidebar visibility
st.markdown("""
<style>
    /* Modern gradient background */
    .main { background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%); }

    /* Sidebar with gradient and WHITE TEXT for visibility */
    [data-testid="stSidebar"] {
        background: linear-gradient(135deg, #0052CC 0%, #6B5BFF 100%);
    }

    /* ALL sidebar text white and bold for better visibility */
    [data-testid="stSidebar"] * {
        color: white !important;
    }

    [data-testid="stSidebar"] label {
        color: white !important;
        font-weight: 600 !important;
    }

    [data-testid="stSidebar"] .stMarkdown {
        color: white !important;
    }

    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: white !important;
        font-weight: 700 !important;
    }

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
        max_depth = st.number_input("Max Depth (m)", 10, 200, 50, 5)
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
        diameter = st.number_input("Diameter (m)", 0.3, 5.0, 1.4, 0.1)
    with col2:
        thickness = st.number_input("Wall Thickness (m)", 0.01, 0.2, 0.016, 0.001)
    with col3:
        length = st.number_input("Embedded Length (m)", 1.0, 200.0, 35.0, 1.0)

    return PileProperties(
        diameter_m=diameter,
        wall_thickness_m=thickness,
        length_m=length,
        pile_type=PileType.DRIVEN_PIPE_OPEN
    )


# ============================================================================
# ENHANCED SOIL PROFILE INPUT (from spud-SRI)
# ============================================================================

def _convert_to_layers(layers_data):
    """Convert layer data to SoilLayer objects."""

    soil_layers = []

    for data in layers_data:
        # Get data points (they should already be SoilPoint objects)
        gamma_points = data.get('gamma_points', [])
        su_points = data.get('su_points', [])
        phi_points = data.get('phi_points', [])

        # Create SoilLayer object
        layer = SoilLayer(
            name=data['name'],
            soil_type=SoilType(data['type']),
            depth_top_m=data['z_top'],
            depth_bot_m=data['z_bot'],
            gamma_prime_kNm3=gamma_points,
            su_kPa=su_points,
            phi_prime_deg=phi_points
        )

        soil_layers.append(layer)

    return soil_layers


def render_soil_input() -> SoilProfile:
    """Enhanced soil profile input with multiple data points per parameter (spud-SRI style)."""
    st.subheader("🪨 Soil Profile")

    site_name = st.text_input("Site Name", "Offshore Site")
    water_depth = st.number_input("Water Depth (m)", 0, 3000, 50, 10)

    profile = SoilProfile(site_name=site_name, water_depth_m=water_depth)

    # Initialize session state for enhanced input
    if 'soil_layers_enhanced' not in st.session_state:
        st.session_state.soil_layers_enhanced = []

    # Add new layer button
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("➕ Add New Layer", use_container_width=True, type="primary"):
            st.session_state.soil_layers_enhanced.append({
                'name': f"Layer {len(st.session_state.soil_layers_enhanced)+1}",
                'type': 'clay',
                'z_top': 0.0 if not st.session_state.soil_layers_enhanced else st.session_state.soil_layers_enhanced[-1]['z_bot'],
                'z_bot': (0.0 if not st.session_state.soil_layers_enhanced else st.session_state.soil_layers_enhanced[-1]['z_bot']) + 2.0,
                'gamma_points': [],
                'su_points': [],
                'phi_points': []
            })
            st.rerun()

    # Display and edit layers
    for idx, layer in enumerate(st.session_state.soil_layers_enhanced):
        with st.expander(f"**{layer['name']}** ({layer['type']}, {layer['z_top']:.1f}-{layer['z_bot']:.1f}m)", expanded=True):

            # Basic layer properties
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                layer['name'] = st.text_input("Layer name", value=layer['name'], key=f"name_enh_{idx}")

            with col2:
                layer['type'] = st.selectbox("Type", ["clay", "silt", "sand"],
                                            index=["clay", "silt", "sand"].index(layer['type']),
                                            key=f"type_enh_{idx}")

            with col3:
                layer['z_top'] = st.number_input("Top (m)", value=layer['z_top'], step=0.1, key=f"ztop_enh_{idx}")

            with col4:
                layer['z_bot'] = st.number_input("Bottom (m)", value=layer['z_bot'], step=0.1, key=f"zbot_enh_{idx}")

            st.markdown("---")

            # Data points for each parameter
            tabs = st.tabs(["γ' (kN/m³)", "Su (kPa)" if layer['type'] in ['clay', 'silt'] else "φ' (deg)", "Actions"])

            # Gamma prime tab
            with tabs[0]:
                st.markdown("**Submerged unit weight data points**")

                # Add data point form
                with st.form(f"add_gamma_{idx}"):
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        new_z = st.number_input("Depth (m)", value=layer['z_top'],
                                              min_value=layer['z_top'], max_value=layer['z_bot'],
                                              step=0.1, key=f"gamma_z_new_{idx}")
                    with col2:
                        new_val = st.number_input("γ' (kN/m³)", value=8.0, step=0.5, key=f"gamma_v_new_{idx}")
                    with col3:
                        if st.form_submit_button("Add Point", use_container_width=True):
                            if 'gamma_points' not in layer:
                                layer['gamma_points'] = []
                            layer['gamma_points'].append(SoilPoint(new_z, new_val))
                            layer['gamma_points'].sort(key=lambda p: p.depth_m)
                            st.rerun()

                # Display existing points
                if layer.get('gamma_points'):
                    df_gamma = pd.DataFrame([
                        {'Depth (m)': p.depth_m, 'γ\' (kN/m³)': p.value}
                        for p in layer['gamma_points']
                    ])
                    st.dataframe(df_gamma, use_container_width=True, hide_index=True)

                    # Delete point
                    if len(layer['gamma_points']) > 0:
                        col_d1, col_d2 = st.columns([1, 1])
                        with col_d1:
                            del_idx = st.number_input("Delete point #", min_value=1,
                                                     max_value=len(layer['gamma_points']),
                                                     value=1, step=1, key=f"del_gamma_{idx}")
                        with col_d2:
                            if st.button(f"Delete #{del_idx}", key=f"del_gamma_btn_{idx}"):
                                layer['gamma_points'].pop(del_idx - 1)
                                st.rerun()
                else:
                    st.info("No data points yet. Add points above.")

            # Strength parameter tab
            with tabs[1]:
                if layer['type'] in ['clay', 'silt']:
                    st.markdown("**Undrained shear strength data points**")
                    param_name = 'su_points'
                    param_label = 'Su (kPa)'
                    default_val = 30.0
                else:
                    st.markdown("**Friction angle data points**")
                    param_name = 'phi_points'
                    param_label = 'φ\' (deg)'
                    default_val = 30.0

                # Add data point form
                with st.form(f"add_param_{idx}"):
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        new_z = st.number_input("Depth (m)", value=layer['z_top'],
                                              min_value=layer['z_top'], max_value=layer['z_bot'],
                                              step=0.1, key=f"param_z_new_{idx}")
                    with col2:
                        new_val = st.number_input(param_label, value=default_val, step=5.0, key=f"param_v_new_{idx}")
                    with col3:
                        if st.form_submit_button("Add Point", use_container_width=True):
                            if param_name not in layer:
                                layer[param_name] = []
                            layer[param_name].append(SoilPoint(new_z, new_val))
                            layer[param_name].sort(key=lambda p: p.depth_m)
                            st.rerun()

                # Display existing points
                if layer.get(param_name):
                    df_param = pd.DataFrame([
                        {'Depth (m)': p.depth_m, param_label: p.value}
                        for p in layer[param_name]
                    ])
                    st.dataframe(df_param, use_container_width=True, hide_index=True)

                    # Delete point
                    if len(layer[param_name]) > 0:
                        col_d1, col_d2 = st.columns([1, 1])
                        with col_d1:
                            del_idx = st.number_input("Delete point #", min_value=1,
                                                     max_value=len(layer[param_name]),
                                                     value=1, step=1, key=f"del_param_{idx}")
                        with col_d2:
                            if st.button(f"Delete #{del_idx}", key=f"del_param_btn_{idx}"):
                                layer[param_name].pop(del_idx - 1)
                                st.rerun()
                else:
                    st.info("No data points yet. Add points above.")

            # Actions tab
            with tabs[2]:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"🗑️ Delete Layer", key=f"del_layer_{idx}", use_container_width=True):
                        st.session_state.soil_layers_enhanced.pop(idx)
                        st.rerun()

                with col2:
                    # Add quick fill option
                    if st.button(f"🎯 Auto-fill with linear profile", key=f"autofill_{idx}", use_container_width=True):
                        # Auto-fill with top and bottom values
                        if not layer.get('gamma_points'):
                            layer['gamma_points'] = [
                                SoilPoint(layer['z_top'], 7.0),
                                SoilPoint(layer['z_bot'], 8.0)
                            ]

                        if layer['type'] in ['clay', 'silt'] and not layer.get('su_points'):
                            layer['su_points'] = [
                                SoilPoint(layer['z_top'], 20.0),
                                SoilPoint(layer['z_bot'], 50.0)
                            ]
                        elif layer['type'] == 'sand' and not layer.get('phi_points'):
                            layer['phi_points'] = [
                                SoilPoint(layer['z_top'], 30.0),
                                SoilPoint(layer['z_bot'], 35.0)
                            ]
                        st.rerun()

    # Summary of all layers
    if st.session_state.soil_layers_enhanced:
        st.markdown("---")
        st.markdown("### Profile Summary")

        summary_data = []
        for i, layer in enumerate(st.session_state.soil_layers_enhanced):
            summary_data.append({
                '#': i+1,
                'Name': layer['name'],
                'Type': layer['type'],
                'Depths': f"{layer['z_top']:.1f}-{layer['z_bot']:.1f}m",
                'γ\' points': len(layer.get('gamma_points', [])),
                'Su points': len(layer.get('su_points', [])) if layer['type'] in ['clay', 'silt'] else '—',
                'φ\' points': len(layer.get('phi_points', [])) if layer['type'] == 'sand' else '—'
            })

        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

        # Clear all button
        if st.button("🗑️ Clear All Layers", use_container_width=True):
            st.session_state.soil_layers_enhanced = []
            st.rerun()

        # Convert to SoilProfile
        layers = _convert_to_layers(st.session_state.soil_layers_enhanced)
        for layer in layers:
            profile.layers.append(layer)
    else:
        st.info("👆 Click 'Add New Layer' to start building your soil profile")

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
            default=[5, 10, 20] if config['max_depth'] >= 20 else [5])

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

        ---
        **Copyright (c) 2025 Dr. Chitti S S U Srikanth. All rights reserved.**
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
        if not profile.layers:
            st.error("⚠️ Please add at least one soil layer before running the analysis!")
            st.stop()

        # Validate that each layer has required data
        for i, layer in enumerate(profile.layers):
            if not layer.gamma_prime_kNm3:
                st.error(f"⚠️ Layer {i+1} ({layer.name}) is missing γ' data points!")
                st.stop()

            if layer.soil_type in [SoilType.CLAY, SoilType.SILT] and not layer.su_kPa:
                st.error(f"⚠️ Layer {i+1} ({layer.name}) is missing Su data points!")
                st.stop()

            if layer.soil_type == SoilType.SAND and not layer.phi_prime_deg:
                st.error(f"⚠️ Layer {i+1} ({layer.name}) is missing φ' data points!")
                st.stop()

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
