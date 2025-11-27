# pile-SRI v2.6.1 Update Summary
## Critical Fixes & Major Enhancements

**Date:** 2025-01-27
**Status:** ✅ Calculation Engine Complete | ⏳ App UI Updates Needed

---

## 🚨 CRITICAL BUGS FIXED

### 1. **Limiting Capacity Bug (CRITICAL)**
**Problem**: End bearing and skin friction exceeded API Table 1 limits
- Example: End bearing went to 12,000 kPa when limit should be 5,000 kPa
- Root cause: Fallback cases in `sand_shaft_friction()` and `end_bearing_sand()` used theoretical formulas WITHOUT applying f_L and q_L limits

**Fix Applied**:
```python
# calculations_v2_1.py lines 584-594
else:
    # Fallback with conservative limit
    warnings.warn(f"Soil type {key} not in API Table 1, using conservative estimate with limit")
    phi_prime = profile.get_property_at_depth(depth_m, "phi_prime")
    if np.isfinite(phi_prime) and phi_prime > 0:
        phi_rad = np.deg2rad(phi_prime)
        Nq = np.exp(np.pi * np.tan(phi_rad)) * np.tan(np.pi/4 + phi_rad/2)**2
        q_calc = Nq * p_o_tip
        # Apply conservative limit even in fallback (5 MPa)
        q_L_conservative = 5000.0  # kPa
        return min(q_calc, q_L_conservative)
```

**Impact**: All capacities now properly limited per API RP 2GEO Table 1

---

## ✅ MAJOR ENHANCEMENTS

### 2. **Complete API Table 1**
**Before**: Many entries had `None` values, triggering unlimited fallback calculations

**After**: All entries filled with appropriate values
```python
API_TABLE_1_EXTENDED = {
    ("very_loose", "sand"): {"beta": 0.25, "f_L_kPa": 47, "Nq": 8, "q_L_MPa": 2.0},
    ("loose", "sand"): {"beta": 0.27, "f_L_kPa": 57, "Nq": 10, "q_L_MPa": 2.5},
    # ... 14 total entries (complete coverage)
}
```

---

### 3. **8-Point Table Discretization**
**Before**: 5 points for t-z/Q-z, 4 points for p-y
**After**: 8 points for all curves with unique values

**Ratios Used**: 0.10, 0.20, 0.30, 0.40, 0.50, 0.65, 0.80, 1.0 of peak

**Benefits**:
- ✅ More accurate curve representation
- ✅ No duplicate values (fixes z1=z2 bug)
- ✅ Uses interpolation for precision
- ✅ Better matches industry standards

**Updated Functions**:
- `discretize_tz_curve_8points()`
- `discretize_qz_curve_8points()`
- `discretize_py_curve_8points()`

---

### 4. **User-Configurable Depth Intervals**
**Before**: Fixed 5m intervals
**After**: Configurable with 1m default

**New Parameter**:
```python
def run_complete_analysis(self, max_depth_m: float, dz: float = 0.5,
                         depth_interval: float = 1.0,  # NEW!
                         tz_depths: Optional[List[float]] = None,
                         ...):
```

**Usage**:
```python
# 1m intervals (default)
results = analysis.run_complete_analysis(max_depth_m=50, depth_interval=1.0)

# 2m intervals (coarser)
results = analysis.run_complete_analysis(max_depth_m=50, depth_interval=2.0)

# Custom depths
results = analysis.run_complete_analysis(max_depth_m=50,
                                         tz_depths=[1, 2, 5, 10, 20, 50])
```

---

### 5. **Separate Compression/Tension Tables**
**Before**: Single combined t-z table with 'c' and 't' rows
**After**: Two separate tables

**Output**:
```python
results['tz_compression_table']  # Only compression rows
results['tz_tension_table']      # Only tension rows
```

**Implementation**:
```python
# Split the combined table
tz_table_combined = LoadDisplacementTables.generate_tz_table(profile, pile, tz_depths)
results['tz_compression_table'] = tz_table_combined[tz_table_combined['Soil type'] == 'c'].copy()
results['tz_tension_table'] = tz_table_combined[tz_table_combined['Soil type'] == 't'].copy()
```

---

## 📝 APP UI UPDATES NEEDED

### **Required Changes to `app_pile_design_v2_1.py`**

#### 1. Update Version Strings
```python
# Line 2: Update title
"""app_pile_design_v2_1.py - pile-SRI Application v2.6.1"""

# Line 55: Update page config
st.set_page_config(
    page_title="pile-SRI v2.6.1 · API RP 2GEO",
    ...
)

# Line 169: Update header
st.markdown("<h1>🗝️ pile-SRI Version 2.6.1</h1>", ...)

# Line 178: Update version badge
<span class='status-badge status-good'>✅ v2.6.1</span>
```

#### 2. Add Depth Interval Control (Sidebar)
```python
# Add after line ~200 in render_sidebar()
st.markdown("## 📐 TABLE SETTINGS")

depth_interval = st.selectbox(
    "Depth Interval for Tables",
    options=[0.5, 1.0, 2.0, 5.0],
    index=1,  # Default to 1.0m
    help="Spacing between depths in t-z, Q-z, and p-y tables"
)

return {
    ...
    'depth_interval': depth_interval,
}
```

#### 3. Update Analysis Call
```python
# Find the run_complete_analysis call (~line 450)
results = analysis.run_complete_analysis(
    max_depth_m=config['pile_length'],
    dz=0.5,
    depth_interval=config['depth_interval'],  # NEW!
    analysis_type=analysis_type,
    use_lrfd=(config['design_method'] == 'LRFD')
)
```

#### 4. Display Separate t-z Tables
```python
# Replace combined t-z table display with separate tabs

st.markdown("### 📊 t-z Curves (Load-Transfer)")

tab1, tab2 = st.tabs(["Compression", "Tension"])

with tab1:
    st.markdown("#### Compression t-z Table (8 points)")
    st.dataframe(results['tz_compression_table'], use_container_width=True)

with tab2:
    st.markdown("#### Tension t-z Table (8 points)")
    st.dataframe(results['tz_tension_table'], use_container_width=True)
```

#### 5. Add Gridlines to All Plots
```python
# For EVERY plotly figure, add this after fig.update_layout():

fig.update_xaxes(
    showgrid=True,
    gridwidth=1,
    gridcolor='lightgray',
    showline=True,
    linewidth=2,
    linecolor='black'
)

fig.update_yaxes(
    showgrid=True,
    gridwidth=1,
    gridcolor='lightgray',
    showline=True,
    linewidth=2,
    linecolor='black'
)
```

**Apply to these figures**:
- Capacity profile plot (~line 600)
- Unit friction plot (~line 620)
- End bearing plot (~line 640)
- t-z curve plots
- Q-z curve plots
- p-y curve plots

#### 6. Fix Light Mode Styling
```python
# Update CSS styling (~line 62-157)
# Add light mode compatibility

st.markdown("""
<style>
    /* Detect light mode and adjust */
    @media (prefers-color-scheme: light) {
        .main {
            background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%);
        }

        /* Make text readable in light mode */
        h1, h2, h3 {
            color: #0052CC !important;
        }

        /* Table styling for light mode */
        .dataframe {
            background-color: white;
            border: 1px solid #e0e0e0;
        }
    }

    /* Existing dark mode styles */
    [data-testid="stSidebar"] {
        background: linear-gradient(135deg, #0052CC 0%, #6B5BFF 100%);
    }

    /* ... rest of existing styles ... */
</style>
""", unsafe_allow_html=True)
```

---

## 🧪 TESTING CHECKLIST

### Calculation Engine (✅ Complete)
- [x] Limiting capacities enforced
- [x] API Table 1 complete
- [x] 8-point discretization
- [x] Unique values (no duplicates)
- [x] Configurable depth intervals
- [x] Separate compression/tension tables
- [x] Instantaneous unit friction

### App UI (⏳ Pending)
- [ ] Version updated to v2.6.1
- [ ] Depth interval control added
- [ ] Analysis call uses depth_interval
- [ ] Separate t-z tables displayed
- [ ] Gridlines on all plots
- [ ] Light mode styling fixed
- [ ] Test with known cases

---

## 📊 EXPECTED RESULTS

### Unit Friction (Sandy Layers)
**Before v2.6.1**: Straight line (averaged values)
**After v2.6.1**:
- Linear increase with depth (f = β × σ'ᵥ)
- Plateaus at f_L limit
- Sharp transitions at layer boundaries

### End Bearing
**Before v2.6.1**: Could exceed 12 MPa
**After v2.6.1**:
- Properly limited to q_L from API Table 1
- Example: Dense sand-silt limited to 5 MPa (5000 kPa)

### Tables
**Before v2.6.1**: 5 or 4 points, 5m intervals, combined c/t
**After v2.6.1**:
- 8 unique points per curve
- 1m intervals (configurable)
- Separate compression/tension

---

## 🚀 DEPLOYMENT STEPS

1. **Calculation Engine** ✅ DONE
   - File: `calculations_v2_1.py`
   - Commit: `a50abf2`
   - Status: Committed and pushed

2. **App UI Updates** ⏳ PENDING
   - File: `app_pile_design_v2_1.py`
   - Actions needed: See section above
   - Estimated time: 30-45 minutes

3. **Testing**
   - Run known test cases
   - Verify limiting capacities
   - Check table formats
   - Test light/dark modes

4. **Documentation**
   - Update README
   - Update user guide
   - Add changelog

---

## 📞 QUESTIONS TO RESOLVE

1. **p-y Curve Validation**: User reported values not matching - need specific test case to debug
2. **Tension Capacity**: User wants verification - appears correct but needs test case confirmation
3. **Custom Depths**: Should we add UI for fully custom depth lists?

---

## 🎯 SUCCESS CRITERIA

✅ **ACHIEVED**:
- Limiting capacities properly enforced
- 8-point tables with unique values
- Configurable depth intervals
- Separate compression/tension tables
- Complete API Table 1

⏳ **REMAINING**:
- App UI updated with all controls
- Gridlines added to plots
- Light mode styling fixed
- Full test validation

---

**Next Steps**: Update `app_pile_design_v2_1.py` per sections above, then test thoroughly with user's known cases.
