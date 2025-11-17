"""
app_pile_design_v2_1.py - pile-SRI Application v2.1
====================================================

Professional-grade Streamlit application for offshore pile foundation design
following API RP 2GEO standards with v2.1 enhancements.

NEW in v2.1:
- Extended API Table 1 implementation
- 5-point industry-standard tables
- LRFD/ASD toggle
- Compression vs Tension analysis
- Layer-by-layer capacity tracking
- Penetration validation indicators
- Enhanced carbonate soil support
- Professional table exports

Run with: streamlit run app_pile_design_v2_1.py

Copyright (c) 2025 Dr. Chitti S S U Srikanth. All rights reserved.
Author: Dr. Chitti S S U Srikanth
Version: 2.1.0
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

# Import v2.1 calculation engine
try:
    from calculations_v2_1 import (
        SoilType, PileType, LoadingType, AnalysisType, RelativeDensity,
        SoilPoint, SoilLayer, PileProperties, SoilProfile,
        AxialCapacity, LateralCapacity, LoadDisplacementTables,
        PileDesignAnalysis,
        API_TABLE_1_EXTENDED, RESISTANCE_FACTORS, CARBONATE_REDUCTION_FACTORS,
    )
    CALC_ENGINE_AVAILABLE = True
except ImportError:
    CALC_ENGINE_AVAILABLE = False
    st.error("⚠️ calculations_v2_1.py not found! Please ensure it's in the same directory.")


# ============================================================================
# PAGE CONFIGURATION & STYLING
# ============================================================================

st.set_page_config(
    page_title="pile-SRI v2.6 · API RP 2GEO",
    page_icon="🗝️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Enhanced color scheme with v2.1 branding
st.markdown("""
<style>
    /* Modern gradient background */
    .main { background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%); }

    /* Sidebar with gradient and WHITE TEXT */
    [data-testid="stSidebar"] {
        background: linear-gradient(135deg, #0052CC 0%, #6B5BFF 100%);
    }

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


    /* Headers with gradient text (exclude sidebar h2/h3 to prevent visibility issues) */
    h1, .main h2 {
        background: linear-gradient(135deg, #0052CC 0%, #6B5BFF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Ensure sidebar headings remain visible with contrasting background */
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        background: rgba(255, 255, 255, 0.2) !important;
        -webkit-text-fill-color: white !important;
        color: white !important;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
        padding: 8px 12px !important;
        border-radius: 8px !important;
        margin: 12px 0 !important;
        font-weight: 700 !important;
        border-left: 4px solid rgba(255, 255, 255, 0.5) !important;
        backdrop-filter: blur(10px) !important;
    }

    /* Primary buttons */
    .stButton > button {
        background: linear-gradient(135deg, #0052CC 0%, #6B5BFF 100%) !important;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }

    .stButton > button:hover {
        box-shadow: 0 8px 25px rgba(0, 82, 204, 0.3) !important;
        transform: translateY(-2px);
    }

    /* Success/Warning badges */
    .status-badge {
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
        margin: 4px;
    }
    
    .status-good {
        background: #10b981;
        color: white;
    }
    
    .status-adequate {
        background: #f59e0b;
        color: white;
    }
    
    .status-warning {
        background: #ef4444;
        color: white;
    }

    /* Table styling */
    .dataframe {
        font-size: 13px;
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# HEADER
# ============================================================================

def render_header():
    """Render application header with version badge."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <h1 style='text-align: center;'>🗝️ pile-SRI Version 2.6</h1>
        <p style='text-align: center; color: #6B5BFF; font-size: 14px;'>
        API RP 2GEO Full Compliance | Enhanced Features | Professional Tables
        </p>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style='text-align: right; padding: 10px;'>
        <span class='status-badge status-good'>✅ v2.6</span>
        <span class='status-badge status-good'>API Table 1</span>
        <span class='status-badge status-good'>LRFD</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()


# ============================================================================
# SIDEBAR CONFIGURATION
# ============================================================================

def render_sidebar() -> Dict:
    """Render enhanced sidebar with v2.1 options."""
    with st.sidebar:
        st.markdown("## 📋 PROJECT SETUP")

        project_name = st.text_input("Project Name", "Offshore Platform Foundation")
        designer = st.text_input("Designer", "Engineering Team")
        
        st.markdown("---")
        st.markdown("## ⚙️ ANALYSIS SETTINGS")

        # NEW: LRFD/ASD toggle
        design_method = st.radio(
            "Design Method",
            ["LRFD (Load & Resistance Factor Design)", "ASD (Allowable Stress Design)"],
            help="LRFD applies resistance factors per API RP 2GEO. ASD uses safety factors."
        )
        use_lrfd = design_method.startswith("LRFD")
        
        if not use_lrfd:
            safety_factor = st.slider("Safety Factor (ASD)", 1.5, 3.5, 2.5, 0.1)
        else:
            safety_factor = None
            st.info("📊 Using API RP 2GEO resistance factors")

        # Analysis types
        analysis_types = st.multiselect(
            "Analysis Types",
            ["Compression", "Tension", "Lateral"],
            default=["Compression", "Lateral"],
            help="Select which analyses to perform"
        )
        
        loading_condition = st.selectbox(
            "Lateral Loading",
            ["Static", "Cyclic"],
            help="For p-y curve generation"
        )

        st.markdown("---")
        st.markdown("## 📊 COMPUTATION")
        
        max_depth = st.number_input("Max Analysis Depth (m)", 10, 200, 50, 5)
        dz = st.slider("Depth Increment (m)", 0.1, 2.0, 0.5, 0.1)
        
        # NEW: Customizable table depths
        with st.expander("🔧 Advanced Options"):
            auto_depths = st.checkbox("Auto-generate depths", value=True)
            if not auto_depths:
                tz_depths_input = st.text_input(
                    "t-z depths (comma-separated, m)",
                    "5, 10, 15, 20, 25, 30"
                )
                py_depths_input = st.text_input(
                    "p-y depths (comma-separated, m)",
                    "5, 10, 15, 20, 25"
                )
                
                tz_depths = [float(x.strip()) for x in tz_depths_input.split(',')]
                py_depths = [float(x.strip()) for x in py_depths_input.split(',')]
            else:
                tz_depths = None
                py_depths = None

        return {
            "project_name": project_name,
            "designer": designer,
            "use_lrfd": use_lrfd,
            "safety_factor": safety_factor,
            "analysis_types": analysis_types,
            "loading_condition": loading_condition,
            "max_depth": max_depth,
            "depth_increment": dz,
            "tz_depths": tz_depths if not auto_depths else None,
            "py_depths": py_depths if not auto_depths else None,
        }


# ============================================================================
# INPUT SECTIONS
# ============================================================================

def render_pile_input() -> PileProperties:
    """Render pile properties input."""
    st.subheader("🔨 Pile Properties")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        diameter = st.number_input("Diameter (m)", 0.3, 5.0, 1.4, 0.1)
    with col2:
        thickness = st.number_input("Wall Thickness (m)", 0.01, 0.2, 0.016, 0.001)
    with col3:
        length = st.number_input("Embedded Length (m)", 1.0, 200.0, 35.0, 1.0)
    with col4:
        pile_type = st.selectbox(
            "Pile Type",
            ["Driven Pipe (Open)", "Driven Pipe (Closed)", "Drilled Shaft", "Grouted"],
            help="Affects resistance factors"
        )
    
    pile_type_map = {
        "Driven Pipe (Open)": PileType.DRIVEN_PIPE_OPEN,
        "Driven Pipe (Closed)": PileType.DRIVEN_PIPE_CLOSED,
        "Drilled Shaft": PileType.DRILLED_SHAFT,
        "Grouted": PileType.GROUTED_PILE,
    }

    return PileProperties(
        diameter_m=diameter,
        wall_thickness_m=thickness,
        length_m=length,
        pile_type=pile_type_map[pile_type]
    )


def render_soil_input() -> SoilProfile:
    """Enhanced soil profile input with v2.1 features."""
    st.subheader("🪨 Soil Profile")

    col1, col2 = st.columns(2)
    with col1:
        site_name = st.text_input("Site Name", "Offshore Site")
    with col2:
        water_depth = st.number_input("Water Depth (m)", 0, 3000, 50, 10)

    profile = SoilProfile(site_name=site_name, water_depth_m=water_depth)

    # Initialize session state
    if 'soil_layers_v21' not in st.session_state:
        st.session_state.soil_layers_v21 = []

    # Add new layer button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("➕ Add Layer", use_container_width=True, type="primary"):
            st.session_state.soil_layers_v21.append({
                'name': f"Layer {len(st.session_state.soil_layers_v21)+1}",
                'type': 'clay',
                'z_top': 0.0 if not st.session_state.soil_layers_v21 else st.session_state.soil_layers_v21[-1]['z_bot'],
                'z_bot': (0.0 if not st.session_state.soil_layers_v21 else st.session_state.soil_layers_v21[-1]['z_bot']) + 5.0,
                'gamma_points': [],
                'su_points': [],
                'phi_points': [],
                'relative_density': 50.0,
                'carbonate_content': 0.0,
                'is_cemented': False,
            })
            st.rerun()

    # Display layers
    for idx, layer in enumerate(st.session_state.soil_layers_v21):
        with st.expander(
            f"**{layer['name']}** ({layer['type']}, {layer['z_top']:.1f}-{layer['z_bot']:.1f}m)",
            expanded=True
        ):
            # Basic properties
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                layer['name'] = st.text_input("Name", value=layer['name'], key=f"name_{idx}")
            with col2:
                layer['type'] = st.selectbox(
                    "Type",
                    ["clay", "silt", "sand", "sand-silt"],
                    index=["clay", "silt", "sand", "sand-silt"].index(layer['type']),
                    key=f"type_{idx}"
                )
            with col3:
                layer['z_top'] = st.number_input("Top (m)", value=layer['z_top'], step=0.5, key=f"ztop_{idx}")
            with col4:
                layer['z_bot'] = st.number_input("Bottom (m)", value=layer['z_bot'], step=0.5, key=f"zbot_{idx}")

            st.markdown("---")
            
            # Tabs for different inputs
            tab1, tab2, tab3, tab4 = st.tabs(["📊 Soil Data", "🎯 Enhanced Properties", "⚡ Quick Fill", "🗑️ Actions"])

            # Tab 1: Soil data points
            with tab1:
                col_g, col_s = st.columns(2)
                
                # Gamma prime
                with col_g:
                    st.markdown("**γ' (kN/m³)**")
                    with st.form(f"add_gamma_{idx}"):
                        c1, c2, c3 = st.columns([1, 1, 1])
                        with c1:
                            gz = st.number_input("Depth", value=layer['z_top'], 
                                               min_value=layer['z_top'], max_value=layer['z_bot'],
                                               step=0.1, key=f"gz_{idx}")
                        with c2:
                            gv = st.number_input("γ'", value=8.0, step=0.5, key=f"gv_{idx}")
                        with c3:
                            if st.form_submit_button("Add", use_container_width=True):
                                if 'gamma_points' not in layer:
                                    layer['gamma_points'] = []
                                layer['gamma_points'].append(SoilPoint(gz, gv))
                                layer['gamma_points'].sort(key=lambda p: p.depth_m)
                                st.rerun()
                    
                    if layer.get('gamma_points'):
                        df = pd.DataFrame([
                            {'Depth (m)': p.depth_m, 'γ\' (kN/m³)': p.value}
                            for p in layer['gamma_points']
                        ])
                        st.dataframe(df, use_container_width=True, hide_index=True)

                # Strength parameters
                with col_s:
                    if layer['type'] in ['clay', 'silt']:
                        st.markdown("**Su (kPa)**")
                        param_points = 'su_points'
                        param_label = 'Su (kPa)'
                        default_val = 30.0
                    else:
                        st.markdown("**φ' (deg)**")
                        param_points = 'phi_points'
                        param_label = 'φ\' (deg)'
                        default_val = 32.0
                    
                    with st.form(f"add_param_{idx}"):
                        c1, c2, c3 = st.columns([1, 1, 1])
                        with c1:
                            pz = st.number_input("Depth", value=layer['z_top'],
                                               min_value=layer['z_top'], max_value=layer['z_bot'],
                                               step=0.1, key=f"pz_{idx}")
                        with c2:
                            pv = st.number_input(param_label, value=default_val, step=5.0, key=f"pv_{idx}")
                        with c3:
                            if st.form_submit_button("Add", use_container_width=True):
                                if param_points not in layer:
                                    layer[param_points] = []
                                layer[param_points].append(SoilPoint(pz, pv))
                                layer[param_points].sort(key=lambda p: p.depth_m)
                                st.rerun()
                    
                    if layer.get(param_points):
                        df = pd.DataFrame([
                            {'Depth (m)': p.depth_m, param_label: p.value}
                            for p in layer[param_points]
                        ])
                        st.dataframe(df, use_container_width=True, hide_index=True)

            # Tab 2: Enhanced v2.1 properties
            with tab2:
                st.markdown("**🆕 v2.1 Enhanced Properties**")
                
                col1, col2, col3 = st.columns(3)
                
                # Relative Density (for sands)
                with col1:
                    if layer['type'] in ['sand', 'sand-silt']:
                        layer['relative_density'] = st.slider(
                            "Relative Density (%)",
                            0, 100, int(layer.get('relative_density', 50)),
                            5,
                            key=f"dr_{idx}",
                            help="For API Table 1 parameter selection"
                        )
                        
                        # Show classification
                        dr_class = RelativeDensity.from_percentage(layer['relative_density'])
                        class_colors = {
                            "very_loose": "🔴",
                            "loose": "🟠",
                            "medium_dense": "🟡",
                            "dense": "🟢",
                            "very_dense": "🔵"
                        }
                        st.info(f"{class_colors.get(dr_class.value, '⚪')} {dr_class.value.replace('_', ' ').title()}")
                    else:
                        st.info("Relative density only for sands")

                # Carbonate content
                with col2:
                    layer['carbonate_content'] = st.slider(
                        "Carbonate Content (%)",
                        0, 100, int(layer.get('carbonate_content', 0)),
                        5,
                        key=f"carb_{idx}",
                        help="For carbonate soil reduction factors"
                    )
                    
                    if layer['carbonate_content'] > 30:
                        if layer['carbonate_content'] > 70:
                            st.warning("⚠️ High carbonate (>70%)")
                        else:
                            st.info("ℹ️ Moderate carbonate (30-70%)")

                # Cementation
                with col3:
                    layer['is_cemented'] = st.checkbox(
                        "Cemented Soil",
                        value=layer.get('is_cemented', False),
                        key=f"cem_{idx}",
                        help="Cemented carbonate can exceed silica strength"
                    )
                    
                    if layer['is_cemented']:
                        st.success("✅ Cemented (capacity increase)")

            # Tab 3: Quick fill
            with tab3:
                st.markdown("**⚡ Quick Fill Options**")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"🎯 Linear Profile", key=f"linear_{idx}", use_container_width=True):
                        # Auto-fill with linear profiles
                        if not layer.get('gamma_points'):
                            layer['gamma_points'] = [
                                SoilPoint(layer['z_top'], 7.0),
                                SoilPoint(layer['z_bot'], 8.5)
                            ]
                        
                        if layer['type'] in ['clay', 'silt'] and not layer.get('su_points'):
                            layer['su_points'] = [
                                SoilPoint(layer['z_top'], 20.0),
                                SoilPoint(layer['z_bot'], 50.0)
                            ]
                        elif layer['type'] in ['sand', 'sand-silt'] and not layer.get('phi_points'):
                            layer['phi_points'] = [
                                SoilPoint(layer['z_top'], 30.0),
                                SoilPoint(layer['z_bot'], 35.0)
                            ]
                        st.rerun()
                
                with col2:
                    if st.button(f"🌊 Typical Marine", key=f"marine_{idx}", use_container_width=True):
                        if layer['type'] == 'clay':
                            layer['gamma_points'] = [SoilPoint(layer['z_top'], 6.5)]
                            layer['su_points'] = [
                                SoilPoint(layer['z_top'], 15.0),
                                SoilPoint(layer['z_bot'], 15.0 + (layer['z_bot'] - layer['z_top']) * 1.5)
                            ]
                        elif layer['type'] == 'sand':
                            layer['gamma_points'] = [SoilPoint(layer['z_top'], 9.8)]
                            layer['phi_points'] = [SoilPoint(layer['z_top'], 35.0)]
                            layer['relative_density'] = 75.0
                        st.rerun()

            # Tab 4: Actions
            with tab4:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"🗑️ Delete Layer", key=f"del_{idx}", use_container_width=True):
                        st.session_state.soil_layers_v21.pop(idx)
                        st.rerun()
                
                with col2:
                    if st.button(f"📋 Duplicate", key=f"dup_{idx}", use_container_width=True):
                        new_layer = layer.copy()
                        new_layer['name'] = f"{layer['name']} (Copy)"
                        new_layer['z_top'] = layer['z_bot']
                        new_layer['z_bot'] = layer['z_bot'] + (layer['z_bot'] - layer['z_top'])
                        st.session_state.soil_layers_v21.insert(idx + 1, new_layer)
                        st.rerun()

    # Summary
    if st.session_state.soil_layers_v21:
        st.markdown("---")
        st.markdown("### 📊 Profile Summary")

        summary_data = []
        for i, layer in enumerate(st.session_state.soil_layers_v21):
            summary_data.append({
                '#': i+1,
                'Name': layer['name'],
                'Type': layer['type'],
                'Depths': f"{layer['z_top']:.1f}-{layer['z_bot']:.1f}m",
                'γ\' pts': len(layer.get('gamma_points', [])),
                'Strength pts': len(layer.get('su_points', [])) + len(layer.get('phi_points', [])),
                'Dr %': f"{layer.get('relative_density', 0):.0f}" if layer['type'] in ['sand', 'sand-silt'] else '—',
                'Carbonate %': f"{layer.get('carbonate_content', 0):.0f}",
            })

        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

        # Clear all
        if st.button("🗑️ Clear All Layers", use_container_width=True):
            st.session_state.soil_layers_v21 = []
            st.rerun()

        # Convert to SoilProfile
        for layer_data in st.session_state.soil_layers_v21:
            layer = SoilLayer(
                name=layer_data['name'],
                soil_type=SoilType(layer_data['type']),
                depth_top_m=layer_data['z_top'],
                depth_bot_m=layer_data['z_bot'],
                gamma_prime_kNm3=layer_data.get('gamma_points', []),
                su_kPa=layer_data.get('su_points', []),
                phi_prime_deg=layer_data.get('phi_points', []),
                relative_density_pct=layer_data.get('relative_density', 50.0),
                carbonate_content_pct=layer_data.get('carbonate_content', 0.0),
                is_cemented=layer_data.get('is_cemented', False),
            )
            profile.layers.append(layer)
    else:
        st.info("👆 Click 'Add Layer' to start building your soil profile")

    return profile


# ============================================================================
# RESULTS & VISUALIZATION
# ============================================================================

def create_capacity_plots(results: Dict, config: Dict):
    """Create enhanced 3-panel capacity plots."""
    
    # Compression
    df_comp = results['capacity_compression_df']
    
    # Tension (if analyzed)
    if 'Tension' in config['analysis_types']:
        df_tens = results['capacity_tension_df']
    else:
        df_tens = None

    # Create 3-panel figure
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=('Unit Friction vs Depth', 'End Bearing vs Depth', 'Total Capacity vs Depth'),
        horizontal_spacing=0.08
    )

    # Panel 1: Unit Friction
    fig.add_trace(
        go.Scatter(
            x=df_comp['unit_friction_kPa'],
            y=df_comp['depth_m'],
            name='Compression',
            line=dict(color='#0052CC', width=2),
            mode='lines',
        ),
        row=1, col=1
    )
    
    if df_tens is not None:
        fig.add_trace(
            go.Scatter(
                x=df_tens['unit_friction_kPa'],
                y=df_tens['depth_m'],
                name='Tension',
                line=dict(color='#6B5BFF', width=2, dash='dash'),
                mode='lines',
            ),
            row=1, col=1
        )

    # Panel 2: End Bearing
    fig.add_trace(
        go.Scatter(
            x=df_comp['end_bearing_kPa'],
            y=df_comp['depth_m'],
            name='End Bearing',
            line=dict(color='#10b981', width=2),
            mode='lines',
            fill='tozerox',
            fillcolor='rgba(16, 185, 129, 0.1)',
        ),
        row=1, col=2
    )

    # Panel 3: Total Capacity
    fig.add_trace(
        go.Scatter(
            x=df_comp['total_capacity_kN'],
            y=df_comp['depth_m'],
            name='Compression',
            line=dict(color='#0052CC', width=3),
            mode='lines',
        ),
        row=1, col=3
    )
    
    if df_tens is not None:
        fig.add_trace(
            go.Scatter(
                x=df_tens['total_capacity_kN'],
                y=df_tens['depth_m'],
                name='Tension',
                line=dict(color='#6B5BFF', width=3, dash='dash'),
                mode='lines',
            ),
            row=1, col=3
        )

    # Update axes
    fig.update_xaxes(title_text="Unit Friction (kPa)", row=1, col=1)
    fig.update_xaxes(title_text="End Bearing (kPa)", row=1, col=2)
    fig.update_xaxes(title_text="Capacity (kN)", row=1, col=3)
    
    for col in range(1, 4):
        fig.update_yaxes(title_text="Depth (m)", autorange="reversed", row=1, col=col)

    fig.update_layout(
        height=500,
        template='plotly_white',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig


def render_results(config, pile, profile):
    """Render comprehensive v2.1 results."""
    
    # Run analysis
    analysis = PileDesignAnalysis(profile, pile)
    
    try:
        analysis_type = AnalysisType.STATIC if config['loading_condition'] == 'Static' else AnalysisType.CYCLIC
        
        results = analysis.run_complete_analysis(
            max_depth_m=config['max_depth'],
            dz=config['depth_increment'],
            tz_depths=config['tz_depths'],
            py_depths=config['py_depths'],
            analysis_type=analysis_type,
            use_lrfd=config['use_lrfd']
        )
        
        # Create tabs
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Capacity Profiles",
            "📈 Load-Displacement",
            "📉 Lateral p-y",
            "📋 Data Tables",
            "🔍 Validation",
            "📄 Report"
        ])
        
        # TAB 1: Capacity Profiles
        with tab1:
            st.subheader("Axial Capacity Profiles")
            
            # 3-panel plot
            fig_cap = create_capacity_plots(results, config)
            st.plotly_chart(fig_cap, use_container_width=True)
            
            # Metrics
            df_comp = results['capacity_compression_df']
            max_cap_comp = df_comp['total_capacity_kN'].max()
            depth_max_comp = df_comp.loc[df_comp['total_capacity_kN'].idxmax(), 'depth_m']
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Max Compression Capacity", f"{max_cap_comp:,.0f} kN")
            with col2:
                st.metric("At Depth", f"{depth_max_comp:.1f} m")
            
            if 'Tension' in config['analysis_types']:
                df_tens = results['capacity_tension_df']
                max_cap_tens = df_tens['total_capacity_kN'].max()
                depth_max_tens = df_tens.loc[df_tens['total_capacity_kN'].idxmax(), 'depth_m']
                
                with col3:
                    st.metric("Max Tension Capacity", f"{max_cap_tens:,.0f} kN")
                with col4:
                    st.metric("At Depth", f"{depth_max_tens:.1f} m")
            
            # Layer-by-layer breakdown
            st.markdown("---")
            st.markdown("### 🔍 Layer-by-Layer Breakdown")
            
            # Get detailed result at max depth
            tip_result = AxialCapacity.total_capacity_layered(
                profile, pile, depth_max_comp, LoadingType.COMPRESSION
            )
            
            if tip_result['layer_contributions']:
                contrib_df = pd.DataFrame(tip_result['layer_contributions'])
                contrib_df['Percentage'] = (contrib_df['friction_kN'] / contrib_df['friction_kN'].sum() * 100).round(1)
                contrib_df.columns = ['Layer', 'Friction (kN)', 'Contribution (%)']
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.dataframe(contrib_df, use_container_width=True, hide_index=True)
                
                with col2:
                    fig_pie = go.Figure(data=[go.Pie(
                        labels=contrib_df['Layer'],
                        values=contrib_df['Friction (kN)'],
                        hole=0.3
                    )])
                    fig_pie.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
                    st.plotly_chart(fig_pie, use_container_width=True)
            
            # Penetration status
            st.markdown("---")
            st.markdown("### ✅ Penetration Validation")
            
            status = tip_result['penetration_status']
            if "Good" in status:
                st.success(f"✅ {status}")
            elif "Adequate" in status:
                st.info(f"ℹ️ {status}")
            elif "WARNING" in status:
                st.error(f"⚠️ {status}")
            else:
                st.warning(f"⚠️ {status}")

        # TAB 2: Load-Displacement (t-z and Q-z)
        with tab2:
            st.subheader("Load-Displacement Curves")
            
            col1, col2 = st.columns(2)
            
            # t-z curves
            with col1:
                st.markdown("#### t-z Curves (Shaft Friction)")
                
                tz_comp = results['tz_compression_table']
                if not tz_comp.empty and 'Soil type' in tz_comp.columns:
                    # Plot (reshape from wide format) - show compression only
                    fig_tz = go.Figure()

                    compression_rows = tz_comp[tz_comp['Soil type'] == 'c']
                    if not compression_rows.empty:
                        for _, row in compression_rows.iterrows():
                            depth = row['Depth']
                            # Extract z and t values from wide format (convert mm to m for plotting)
                            z_vals = [row[f'z{i}']/1000 for i in range(1, 6)]  # mm to m
                            t_vals = [row[f't{i}']*1000 for i in range(1, 6)]  # MN/m to kN/m

                            fig_tz.add_trace(go.Scatter(
                                x=z_vals,
                                y=t_vals,
                                name=f"{depth:.1f}m",
                                mode='lines+markers',
                            ))

                        fig_tz.update_layout(
                            xaxis_title="Displacement (m)",
                            yaxis_title="Unit Friction (kN/m)",
                            height=400,
                            template='plotly_white'
                        )
                        st.plotly_chart(fig_tz, use_container_width=True)

                    # Display wide-format table
                    st.markdown("**Format:** t values in MN/m, z values in mm | 'c'=compression, 't'=tension")
                    st.dataframe(tz_comp, use_container_width=True, hide_index=True)
                else:
                    st.info("No t-z data available for selected configuration.")
            
            # Q-z curve
            with col2:
                st.markdown("#### Q-z Curve (End Bearing)")
                
                qz = results['qz_table']
                if not qz.empty and 'q1' in qz.columns:
                    # Plot (reshape from wide format)
                    fig_qz = go.Figure()

                    # Extract z and q values from wide format (convert mm to m for plotting)
                    row = qz.iloc[0]
                    z_vals = [row[f'z{i}']/1000 for i in range(1, 6)]  # mm to m
                    q_vals = [row[f'q{i}']*1000 for i in range(1, 6)]  # MN to kN

                    fig_qz.add_trace(go.Scatter(
                        x=z_vals,
                        y=q_vals,
                        mode='lines+markers',
                        line=dict(color='#10b981', width=3),
                        marker=dict(size=8),
                    ))

                    fig_qz.update_layout(
                        xaxis_title="Displacement (m)",
                        yaxis_title="End Bearing (kN)",
                        height=400,
                        template='plotly_white'
                    )
                    st.plotly_chart(fig_qz, use_container_width=True)

                    # Display wide-format table
                    st.markdown("**Format:** q values in MN, z values in mm | tip: 0=unplugged, 1=plugged")
                    st.dataframe(qz, use_container_width=True, hide_index=True)
                else:
                    st.warning(f"⚠️ No Q-z data available. Debug info:\n\n"
                              f"- Pile length: {pile.length_m:.1f} m\n"
                              f"- Max analysis depth: {config['max_depth']:.1f} m\n"
                              f"- Q-z table rows: {len(qz)}\n"
                              f"- Q-z table columns: {list(qz.columns) if not qz.empty else 'empty'}\n\n"
                              "Possible reasons:\n"
                              "- End bearing capacity calculated as zero\n"
                              "- No soil layer exists at pile tip depth\n\n"
                              "👉 Check your **soil profile** extends to pile tip depth.")

        # TAB 3: Lateral p-y curves
        with tab3:
            if 'Lateral' in config['analysis_types']:
                st.subheader("Lateral p-y Curves")
                
                py_table = results['py_table']
                if not py_table.empty and 'p1' in py_table.columns and 'Depth' in py_table.columns:
                    # Plot all depths (reshape from wide format)
                    fig_py = go.Figure()

                    for _, row in py_table.iterrows():
                        depth = row['Depth']
                        # Extract y and p values from wide format (convert mm to m for plotting)
                        y_vals = [row[f'y{i}']/1000 for i in range(1, 5)]  # mm to m
                        p_vals = [row[f'p{i}'] for i in range(1, 5)]

                        fig_py.add_trace(go.Scatter(
                            x=y_vals,
                            y=p_vals,
                            name=f"{depth:.1f}m",
                            mode='lines+markers',
                        ))

                    fig_py.update_layout(
                        xaxis_title="Lateral Displacement y (m)",
                        yaxis_title="Lateral Resistance p (kN/m)",
                        height=500,
                        template='plotly_white'
                    )
                    st.plotly_chart(fig_py, use_container_width=True)

                    # Display wide-format table
                    st.markdown("---")
                    st.markdown("### 📋 4-Point p-y Table (Industry Standard)")
                    st.markdown("**Format:** p values in kN/m, y values in mm")
                    st.dataframe(py_table, use_container_width=True, hide_index=True)
                else:
                    st.info("No p-y data available for selected configuration.")
            else:
                st.info("Lateral analysis not selected. Enable in sidebar.")

        # TAB 4: Data Tables (Export)
        with tab4:
            st.subheader("📥 Export Data Tables")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Capacity Profiles")
                
                # Compression
                csv_comp = results['capacity_compression_df'].to_csv(index=False)
                st.download_button(
                    "📥 Download Compression Capacity",
                    csv_comp,
                    "capacity_compression.csv",
                    "text/csv",
                    use_container_width=True
                )
                
                # Tension
                if 'Tension' in config['analysis_types']:
                    csv_tens = results['capacity_tension_df'].to_csv(index=False)
                    st.download_button(
                        "📥 Download Tension Capacity",
                        csv_tens,
                        "capacity_tension.csv",
                        "text/csv",
                        use_container_width=True
                    )
            
            with col2:
                st.markdown("#### Load-Displacement")
                
                # t-z
                csv_tz = results['tz_compression_table'].to_csv(index=False)
                st.download_button(
                    "📥 Download t-z Table",
                    csv_tz,
                    "tz_curves.csv",
                    "text/csv",
                    use_container_width=True
                )
                
                # Q-z
                csv_qz = results['qz_table'].to_csv(index=False)
                st.download_button(
                    "📥 Download Q-z Table",
                    csv_qz,
                    "qz_curve.csv",
                    "text/csv",
                    use_container_width=True
                )
                
                # p-y
                if 'Lateral' in config['analysis_types']:
                    csv_py = results['py_table'].to_csv(index=False)
                    st.download_button(
                        "📥 Download p-y Table",
                        csv_py,
                        "py_curves.csv",
                        "text/csv",
                        use_container_width=True
                    )
            
            # Preview tables
            st.markdown("---")
            st.markdown("### 👁️ Preview Tables")
            
            preview_table = st.selectbox(
                "Select table to preview:",
                ["Compression Capacity", "Tension Capacity", "t-z Compression", "Q-z", "p-y"]
            )
            
            if preview_table == "Compression Capacity":
                st.dataframe(results['capacity_compression_df'], use_container_width=True)
            elif preview_table == "Tension Capacity" and 'Tension' in config['analysis_types']:
                st.dataframe(results['capacity_tension_df'], use_container_width=True)
            elif preview_table == "t-z Compression":
                st.dataframe(results['tz_compression_table'], use_container_width=True)
            elif preview_table == "Q-z":
                st.dataframe(results['qz_table'], use_container_width=True)
            elif preview_table == "p-y" and 'Lateral' in config['analysis_types']:
                st.dataframe(results['py_table'], use_container_width=True)

        # TAB 5: Validation
        with tab5:
            st.subheader("✅ API RP 2GEO Compliance Validation")
            
            # Design method
            st.markdown("### Design Method")
            if config['use_lrfd']:
                st.success("✅ LRFD Design (API RP 2GEO Annex A)")
                st.info(f"Resistance factors applied automatically based on pile type: {pile.pile_type.value}")
            else:
                st.info(f"ℹ️ ASD Design with SF = {config['safety_factor']}")
            
            # Soil parameters validation
            st.markdown("---")
            st.markdown("### Soil Parameters Validation")
            
            validation_data = []
            for layer in profile.layers:
                # Check if parameters are from API Table 1
                if layer.soil_type in [SoilType.SAND, SoilType.SAND_SILT]:
                    dr_class = layer.get_relative_density_class().value
                    soil_desc = layer.soil_type.value
                    key = (dr_class, soil_desc)
                    
                    if key in API_TABLE_1_EXTENDED and API_TABLE_1_EXTENDED[key]["beta"] is not None:
                        params = API_TABLE_1_EXTENDED[key]
                        status = "✅ API Table 1"
                        details = f"β={params['beta']:.2f}, Nq={params['Nq']}"
                    else:
                        status = "⚠️ Not in Table 1"
                        details = "Using conservative estimate"
                else:
                    status = "✅ Clay (α-method)"
                    details = "API Eq. 17-18"
                
                validation_data.append({
                    'Layer': layer.name,
                    'Type': layer.soil_type.value,
                    'Status': status,
                    'Method': details
                })
            
            st.dataframe(pd.DataFrame(validation_data), use_container_width=True, hide_index=True)
            
            # Penetration requirements
            st.markdown("---")
            st.markdown("### Penetration Requirements")
            
            tip_result = AxialCapacity.total_capacity_layered(
                profile, pile, config['max_depth'], LoadingType.COMPRESSION
            )
            
            st.write(f"**Pile Diameter:** {pile.diameter_m:.2f} m")
            st.write(f"**Required Penetration:** {2*pile.diameter_m:.2f} m (minimum), {3*pile.diameter_m:.2f} m (recommended)")
            st.write(f"**Status:** {tip_result['penetration_status']}")
            
            # Carbonate checks
            st.markdown("---")
            st.markdown("### Special Soil Conditions")
            
            has_carbonate = any(layer.carbonate_content_pct > 30 for layer in profile.layers)
            has_cemented = any(layer.is_cemented for layer in profile.layers)
            
            if has_carbonate:
                st.warning("⚠️ Carbonate soils detected (>30% content)")
                st.info("Reduction factors applied per API Annex B")
            
            if has_cemented:
                st.success("✅ Cemented soils detected")
                st.info("Capacity may exceed siliceous soils")
            
            if not has_carbonate and not has_cemented:
                st.success("✅ Standard siliceous soils")

        # TAB 6: Report
        with tab6:
            st.subheader("📄 Design Summary Report")
            
            st.markdown(f"""
            ### PROJECT INFORMATION
            - **Project:** {config['project_name']}
            - **Designer:** {config['designer']}
            - **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            - **Software:** pile-SRI v2.6
            
            ---
            
            ### PILE PROPERTIES
            - **Diameter:** {pile.diameter_m:.3f} m
            - **Wall Thickness:** {pile.wall_thickness_m:.4f} m
            - **Embedded Length:** {pile.length_m:.1f} m
            - **Type:** {pile.pile_type.value}
            - **Gross Area:** {pile.area_gross_m2:.4f} m²
            
            ---
            
            ### SOIL PROFILE
            - **Site:** {profile.site_name}
            - **Water Depth:** {profile.water_depth_m:.0f} m
            - **Number of Layers:** {len(profile.layers)}
            
            #### Layers:
            """)
            
            for i, layer in enumerate(profile.layers, 1):
                st.markdown(f"""
            **{i}. {layer.name}** ({layer.soil_type.value})
            - Depth: {layer.depth_top_m:.1f} - {layer.depth_bot_m:.1f} m
            - Relative Density: {layer.relative_density_pct:.0f}% ({layer.get_relative_density_class().value.replace('_', ' ')})
            - Carbonate Content: {layer.carbonate_content_pct:.0f}%
            - Cemented: {"Yes" if layer.is_cemented else "No"}
                """)
            
            st.markdown(f"""
            ---
            
            ### ANALYSIS PARAMETERS
            - **Design Method:** {"LRFD" if config['use_lrfd'] else f"ASD (SF={config['safety_factor']})"}
            - **Analysis Types:** {', '.join(config['analysis_types'])}
            - **Loading Condition:** {config['loading_condition']}
            - **Max Depth:** {config['max_depth']} m
            - **Depth Increment:** {config['depth_increment']} m
            
            ---
            
            ### CAPACITY RESULTS
            
            #### Compression
            - **Maximum Capacity:** {max_cap_comp:,.0f} kN
            - **At Depth:** {depth_max_comp:.1f} m
            - **Resistance Factor:** {tip_result['applied_resistance_factor']:.2f}
            """)
            
            if 'Tension' in config['analysis_types']:
                st.markdown(f"""
            #### Tension
            - **Maximum Capacity:** {max_cap_tens:,.0f} kN
            - **At Depth:** {depth_max_tens:.1f} m
                """)
            
            st.markdown(f"""
            ---
            
            ### API RP 2GEO COMPLIANCE
            
            ✅ **Section 8.1:** Axial capacity calculations (α-method for clay, API Table 1 for sand)
            
            ✅ **Section 8.2:** Tension capacity (separate calculation, no end bearing)
            
            ✅ **Section 8.4:** Load-displacement curves (t-z and Q-z, 5-point discretization)
            
            ✅ **Section 8.5:** Lateral capacity (p-y curves per Matlock/Reese/API methods)
            
            ✅ **Table 1:** Extended implementation for all soil types
            
            ✅ **Annex A:** LRFD resistance factors
            
            ✅ **Annex B:** Carbonate soil considerations
            
            ✅ **Annex C:** Penetration requirements ({tip_result['penetration_status']})
            
            ---
            
            ### PROFESSIONAL CERTIFICATION
            
            This analysis was performed using **pile-SRI v2.6**, which implements:
            - Full API RP 2GEO Section 8 compliance
            - Industry-standard 5-point discretization
            - LRFD resistance factors
            - Enhanced carbonate soil handling
            - Automatic penetration validation
            
            **Important:** This analysis should be reviewed by a licensed professional engineer 
            before use in final design.
            
            ---
            
            **Copyright (c) 2025 Dr. Chitti S S U Srikanth. All rights reserved.**
            """)
    
    except Exception as e:
        st.error(f"❌ Analysis error: {str(e)}")
        st.exception(e)


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application flow."""
    
    if not CALC_ENGINE_AVAILABLE:
        st.stop()
    
    render_header()
    config = render_sidebar()
    
    st.divider()
    
    # Input sections
    col_pile, col_soil = st.columns([1, 1])
    with col_pile:
        pile = render_pile_input()
    with col_soil:
        profile = render_soil_input()
    
    st.divider()
    
    # Run analysis button
    if st.button("🚀 RUN ANALYSIS", use_container_width=True, type="primary"):
        if not profile.layers:
            st.error("⚠️ Please add at least one soil layer!")
            st.stop()
        
        # Validate layers
        for i, layer in enumerate(profile.layers):
            if not layer.gamma_prime_kNm3:
                st.error(f"⚠️ Layer {i+1} ({layer.name}) missing γ' data!")
                st.stop()
            
            if layer.soil_type in [SoilType.CLAY, SoilType.SILT] and not layer.su_kPa:
                st.error(f"⚠️ Layer {i+1} ({layer.name}) missing Su data!")
                st.stop()
            
            if layer.soil_type in [SoilType.SAND, SoilType.SAND_SILT] and not layer.phi_prime_deg:
                st.error(f"⚠️ Layer {i+1} ({layer.name}) missing φ' data!")
                st.stop()
        
        # Store in session
        st.session_state.run_analysis = True
        st.session_state.config = config
        st.session_state.pile = pile
        st.session_state.profile = profile
    
    # Show results
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
    
    main()
