"""
app_pile_design.py - Entry Point for Streamlit Deployment
=========================================================

This file serves as the main entry point for Streamlit Cloud deployment.
It executes the current version (v2.1) of the pile design application.

For local development, you can run either:
- streamlit run app_pile_design.py (uses this file)
- streamlit run app_pile_design_v2_1.py (runs v2.1 directly)

Copyright (c) 2025 Dr. Chitti S S U Srikanth. All rights reserved.
"""

# Execute the current version (v2.1) directly
# This ensures all Streamlit code runs properly
import os
import sys

# Get the directory of this file
current_dir = os.path.dirname(os.path.abspath(__file__))

# Path to the v2.1 file
v2_1_path = os.path.join(current_dir, 'app_pile_design_v2_1.py')

# Read and execute the v2.1 file
with open(v2_1_path, 'r', encoding='utf-8') as f:
    code = f.read()
    exec(code, globals())
