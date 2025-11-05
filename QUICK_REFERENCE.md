# Pile Foundation Designer - Quick Reference Guide
## API RP 2GEO Compliance Application v1.0

---

## 🚀 QUICK START

### Installation
```bash
pip install -r requirements.txt
streamlit run app_pile_design.py
```

### Basic Workflow
1. **Define Project** → Sidebar: Project name, designer, analysis type
2. **Enter Pile** → Pile diameter, wall thickness, embedded length
3. **Build Soil Profile** → Add layers, define soil properties
4. **Run Analysis** → Click "RUN ANALYSIS" button
5. **Review Results** → View capacity plots, p-y curves, reports

---

## 📋 SOIL PROFILE INPUT

### Required for Each Layer
| Property | Units | Typical Range | Notes |
|----------|-------|---------------|-------|
| **Layer Name** | — | — | Descriptive (e.g., "Soft Clay") |
| **Soil Type** | — | Clay/Sand/Silt | Determines calculation method |
| **Depth Top** | m | 0-1000 | From seafloor (or MSL) |
| **Depth Bottom** | m | 0-1000 | Bottom of layer |
| **γ' (submerged)** | kN/m³ | 5-12 | Effective unit weight |
| **Su** (if clay) | kPa | 10-500 | Undrained shear strength |
| **φ'** (if sand) | ° | 25-45 | Angle of internal friction |

### Example Layer Entry
**Clay Layer (0-20m depth):**
- γ' top: 7.0 kN/m³, γ' bot: 8.0 kN/m³
- Su top: 20 kPa, Su bot: 50 kPa

**Sand Layer (20-40m depth):**
- γ' top: 9.0 kN/m³, γ' bot: 9.5 kN/m³
- φ' top: 32°, φ' bot: 35°

---

## 🔨 PILE PROPERTIES

### Key Parameters

| Parameter | Typical | Range |
|-----------|---------|-------|
| **Outer Diameter** | 1.4 m | 0.3 - 3.0 m |
| **Wall Thickness** | 16 mm | 10 - 100 mm |
| **Embedded Length** | 35 m | 5 - 100 m |
| **Material** | Steel | Steel, Concrete |
| **Pile Type** | Driven Pipe | Driven (O/C), Drilled |

### Design Considerations
- **Wall Thickness**: Affects shaft friction distribution
- **Embedded Length**: Longer = higher capacity but more cost
- **Diameter**: Larger area increases end bearing
- **Material**: Steel typical for offshore; concrete for onshore

---

## 📊 ANALYSIS METHODS IMPLEMENTED

### 1. AXIAL CAPACITY (API RP 2GEO Section 8.1)

#### In Clay (Cohesive Soils)
**Shaft Friction:**
- Formula: f(z) = α × Su
- Alpha factor: α = 0.5 × ψ^(-0.5) for ψ ≤ 1.0
- where ψ = Su / p'o(z)

**End Bearing:**
- Formula: q = 9 × Su (per Equation 20)
- Nc = 9.0 (bearing capacity factor)

#### In Sand (Cohesionless Soils)
**Shaft Friction:**
- Formula: f(z) = β × p'o(z)
- Beta factor: β = K × tan(δ_cv)
- K ≈ 1.0 for driven offshore piles

**End Bearing:**
- Formula: q = Nq × p'o_tip
- Nq from Meyerhof bearing capacity factors

**Total Capacity:**
```
Qc = Qf,c + Qp = ∫ f(z) × As dz + q × Ap
```

### 2. LATERAL CAPACITY (API RP 2GEO Section 8.5)

#### Matlock Method (Soft Clay: Su ≤ 100 kPa)
**Ultimate Lateral Bearing:**
- At surface: pu·D = 3·Su·D
- At depth: pu·D = 9·Su·D
- Transition zone: Depth zR = 6D / (D·γ'/Su + J)
- J = 0.5 for Gulf of Mexico clays

**p-y Curve (Table 3 - Static Loading):**
| p/pu | y/y_peak |
|------|----------|
| 0.00 | 0.0 |
| 0.23 | 0.1 |
| 0.33 | 0.3 |
| 0.50 | 1.0 |
| 0.72 | 3.0 |
| 1.00 | 8.0 |

#### Reese Method (Stiff Clay: Su > 100 kPa)
- Similar to Matlock but with brittle behavior
- Steeper p-y curve slopes
- Lower displacement to peak resistance
- Rapid capacity deterioration post-peak

#### Sand p-y Curves (Section 8.5.6-8.5.7)
**Ultimate Pressure (minimum of shallow/deep):**
- Shallow: pu_s = (C1·z + C2·D) × γ' × z
- Deep: pu_d = C3 × D × γ' × z

**Non-Linear Relationship (Eq. 28):**
```
p = A·pu·tanh(k·z·y / A·pu)
```
- A = 0.9 (cyclic) or 3.0 - 0.8·z/D (static)
- k = subgrade modulus gradient

### 3. LOAD-DISPLACEMENT CURVES (API RP 2GEO Section 8.4)

#### t-z Curves (Axial Shaft Friction)
**Peak Displacement:** z_peak = 0.01 × D (1% of diameter)

**Clay t-z (Table 2):**
| z/z_peak | t/t_max |
|----------|---------|
| 0.00 | 0.00 |
| 0.16 | 0.30 |
| 0.31 | 0.50 |
| 0.57 | 0.75 |
| 1.00 | 1.00 |
| 2.00+ | 0.70-0.90 |

**Sand t-z (Table 2):**
- Similar curve but maintains full capacity (no residual drop)

#### Q-z Curves (End Bearing)
**Mobilization (Figure 3):**
| z/D | Q/Qp |
|-----|------|
| 0.000 | 0.00 |
| 0.002 | 0.25 |
| 0.013 | 0.50 |
| 0.042 | 0.75 |
| 0.073 | 0.90 |
| 0.100+ | 1.00 |

---

## ⚠️ IMPORTANT PARAMETERS & DEFAULTS

### Safety Factors (Per API RP 2GEO)
- **Axial Static:** 2.5 to 3.0x
- **Axial Cyclic:** 3.0 to 3.5x
- **Lateral Static:** 2.0 to 2.5x
- **Lateral Cyclic:** 2.5 to 3.0x

### Strain Parameters
| Soil Type | εc (Strain at ½ max stress) |
|-----------|---------------------------|
| Soft Clay | 0.02 (2%) |
| Stiff Clay | 0.015 (1.5%) |
| Sand | 0.01 (1%) |

### Typical Unit Weights (γ')
| Material | kN/m³ |
|----------|-------|
| Clay (submerged) | 8-9 |
| Sand (submerged) | 9-10 |
| Silt (submerged) | 8.5-9.5 |

---

## 🔧 TROUBLESHOOTING

### No Capacity Calculated
- ✓ Check soil profile has proper γ' values for all depths
- ✓ Verify Su (clay) or φ' (sand) is defined
- ✓ Ensure depth increments aren't too large

### p-y Curves Empty
- ✓ Selected depths must be within soil layers
- ✓ Clay Su must be > 0 kPa
- ✓ Sand φ' must be > 0°

### Unrealistic Results
- ✓ Review input parameter ranges (see tables above)
- ✓ Check soil layer depths don't overlap
- ✓ Verify pile diameter reasonable (0.3-3.0m)

---

## 📈 INTERPRETING RESULTS

### Capacity Plots
- **X-axis:** Capacity in kN
- **Y-axis:** Depth in meters (inverted)
- **Color coding:** Different soil types
- **Interpret:** Higher capacity = can support more load at that depth

### p-y Curves
- **X-axis:** Lateral displacement (meters)
- **Y-axis:** Lateral pressure (kPa)
- **Shape:** Stiff then softens (S-curve)
- **Interpret:** Area under curve = energy dissipation

### Load-Displacement Curves
- **t-z:** Shaft friction mobilization with pile movement
- **Q-z:** Tip bearing mobilization (large displacements needed)
- **Interpret:** Design displacement requirements for serviceability

---

## 📚 REFERENCES

### Key Equations by Section

**Equation 16:** Total Axial Capacity
```
Qc = ∫ f(z) × As dz + q × Ap
```

**Equation 17-18:** Clay Shaft Friction with Alpha Method
```
f(z) = α × Su
α = 0.5 × ψ^(-0.5) for ψ ≤ 1.0
```

**Equation 20:** Clay End Bearing
```
q = 9 × Su
```

**Equation 21:** Sand Shaft Friction
```
f(z) = β × p'o(z)
```

**Equation 22:** Sand End Bearing
```
q = Nq × p'o
```

**Equation 23-24:** Soft Clay Ultimate Lateral Pressure
```
pu·D = 3·Su·D to 9·Su·D (transition at zR)
```

**Equation 28:** Sand p-y Curve (Non-linear)
```
p = A·pu·tanh(k·z·y / A·pu)
```

---

## 🎯 BEST PRACTICES

### Input Data Quality
1. Use site-specific data when available
2. Interpolate conservatively between borehole locations
3. Consider uncertainty in soil parameters (typically ±20%)
4. Always include multiple layers, even thin ones

### Analysis Setup
1. Start with conservative safety factors (3.0x)
2. Use static loading unless cyclic effects dominate
3. Analyze at 0.5m depth increments for accuracy
4. Verify results against industry benchmarks

### Results Validation
1. Check sanity of capacity vs depth (should generally increase)
2. Compare with similar projects if available
3. Verify p-y curves match expected soil behavior
4. Confirm load-displacement curves are smooth

### Documentation
1. Always document input assumptions
2. Record soil investigation dates and locations
3. Note any special site conditions (seismic, scour)
4. Keep record of safety factors applied

---

## 📞 SUPPORT & LIMITATIONS

### What This App CAN Do
- ✅ Calculate axial pile capacity in clay and sand
- ✅ Generate p-y curves per API methods
- ✅ Analyze layered soil profiles
- ✅ Export results for reporting
- ✅ Quick scoping calculations

### What This App CANNOT Do
- ❌ Pile groups (uses single-pile calculations)
- ❌ Tension capacity (only compression)
- ❌ Special soils (carbonate, weak rock)
- ❌ Dynamic pile driving analysis
- ❌ Soil-structure interaction (SSI)

### Known Limitations
- Single pile analysis only
- Uses simplified soil models
- Limited scour effect calculation
- No rate-dependent effects
- No cyclic degradation models

---

## 📝 QUICK REFERENCE - COMMON QUESTIONS

**Q: What safety factor should I use?**
A: API RP 2GEO recommends 2.5-3.0x for axial, 2.0-2.5x for lateral. Use higher for uncertainty.

**Q: How deep do I need to analyze?**
A: Until capacity stabilizes or reaches project max depth (typically 50-100m offshore).

**Q: Can I use this for onshore piles?**
A: Mostly yes, but note some methods (Matlock) are specifically for offshore. Adjust parameters.

**Q: What if soil properties vary non-linearly?**
A: Add more data points. App interpolates linearly between points.

**Q: How do I account for scour?**
A: Reduce effective stress and capacity by scour depth. Future version will have dedicated scour calculator.

**Q: What about pore pressure effects?**
A: App uses γ' (effective unit weight) which implicitly includes pore pressure.

---

**Last Updated:** January 2025  
**Version:** 1.0.0  
**API Reference:** API RP 2GEO (2014)
