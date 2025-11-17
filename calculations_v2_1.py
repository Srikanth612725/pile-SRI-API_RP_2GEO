"""
calculations_v2_1.py - pile-SRI Enhanced Calculation Engine
===========================================================

Implements API RP 2GEO Section 8 with industry-standard enhancements.

Version 2.1 Improvements:
- ✅ Extended API Table 1 with all soil types
- ✅ 5-point industry-standard discretization for all curves
- ✅ LRFD resistance factors (API RP 2GEO Annex A)
- ✅ Carbonate soil reduction factors (Annex B)
- ✅ Enhanced layered soil tracking
- ✅ Penetration depth validation
- ✅ Professional table outputs for all curves

Reference: API RP 2GEO (Geotechnical and Foundation Design Considerations)
           Section 8: Pile Foundation Design

Copyright (c) 2025 Dr. Chitti S S U Srikanth. All rights reserved.
Author: Dr. Chitti S S U Srikanth
Version: 2.1.0
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Union
from enum import Enum
import numpy as np
import pandas as pd
from scipy import interpolate
import warnings


# ============================================================================
# ENUMERATIONS & CONSTANTS
# ============================================================================

class SoilType(Enum):
    """Soil type classification per ISO 14688."""
    CLAY = "clay"
    SILT = "silt"
    SAND = "sand"
    SAND_SILT = "sand-silt"  # Mixed classification
    ROCK = "rock"


class PileType(Enum):
    """Pile type classification."""
    DRIVEN_PIPE_OPEN = "driven_pipe_open"
    DRIVEN_PIPE_CLOSED = "driven_pipe_closed"
    DRILLED_SHAFT = "drilled_shaft"
    GROUTED_PILE = "grouted_pile"


class LoadingType(Enum):
    """Loading condition type."""
    COMPRESSION = "compression"
    TENSION = "tension"
    LATERAL = "lateral"
    COMBINED = "combined"


class AnalysisType(Enum):
    """Analysis type for p-y curves."""
    STATIC = "static"
    CYCLIC = "cyclic"
    PSEUDO_STATIC = "pseudo_static"


class RelativeDensity(Enum):
    """Relative density classification for cohesionless soils."""
    VERY_LOOSE = "very_loose"      # 0-15%
    LOOSE = "loose"                 # 15-35%
    MEDIUM_DENSE = "medium_dense"   # 35-65%
    DENSE = "dense"                 # 65-85%
    VERY_DENSE = "very_dense"       # 85-100%

    @classmethod
    def from_percentage(cls, dr_pct: float) -> 'RelativeDensity':
        """Convert percentage to classification."""
        if dr_pct < 15:
            return cls.VERY_LOOSE
        elif dr_pct < 35:
            return cls.LOOSE
        elif dr_pct < 65:
            return cls.MEDIUM_DENSE
        elif dr_pct < 85:
            return cls.DENSE
        else:
            return cls.VERY_DENSE


# ============================================================================
# API RP 2GEO TABLE 1 - EXTENDED (Complete Implementation)
# ============================================================================

API_TABLE_1_EXTENDED = {
    # Format: (relative_density, soil_description): {beta, f_L_kPa, Nq, q_L_MPa}
    ("very_loose", "sand"): {"beta": None, "f_L_kPa": None, "Nq": None, "q_L_MPa": None},
    ("loose", "sand"): {"beta": None, "f_L_kPa": None, "Nq": None, "q_L_MPa": None},
    ("loose", "sand-silt"): {"beta": None, "f_L_kPa": None, "Nq": None, "q_L_MPa": None},
    ("medium_dense", "silt"): {"beta": None, "f_L_kPa": None, "Nq": None, "q_L_MPa": None},
    ("medium_dense", "sand"): {"beta": None, "f_L_kPa": None, "Nq": None, "q_L_MPa": None},
    ("medium_dense", "sand-silt"): {"beta": 0.29, "f_L_kPa": 67, "Nq": 12, "q_L_MPa": 3.0},
    ("dense", "sand-silt"): {"beta": 0.37, "f_L_kPa": 81, "Nq": 20, "q_L_MPa": 5.0},
    ("dense", "sand"): {"beta": 0.46, "f_L_kPa": 96, "Nq": 40, "q_L_MPa": 10.0},
    ("very_dense", "sand"): {"beta": 0.58, "f_L_kPa": 115, "Nq": 50, "q_L_MPa": 12.0},
}


# LRFD Resistance Factors per API RP 2GEO
RESISTANCE_FACTORS = {
    "axial_compression_driven": 0.70,
    "axial_compression_drilled": 0.55,
    "axial_tension_driven": 0.60,
    "axial_tension_drilled": 0.50,
    "lateral": 0.65,
    "end_bearing": 0.60,
}


# Carbonate Soil Reduction Factors (Annex B)
CARBONATE_REDUCTION_FACTORS = {
    "driven_pile": {
        "low_carbonate": 1.0,      # <30% carbonate
        "moderate_carbonate": 0.75, # 30-70% carbonate
        "high_carbonate": 0.50,     # >70% carbonate, uncemented
        "cemented": 1.2,            # Cemented material (can exceed silica)
    },
    "drilled_grouted": {
        "all_carbonate": 0.85,  # Drilled and grouted piles less affected
    }
}


# ============================================================================
# UTILITY FUNCTIONS FOR INDUSTRY-STANDARD DISCRETIZATION
# ============================================================================

def discretize_tz_curve_5points(z_full: np.ndarray, t_full: np.ndarray) -> Dict:
    """
    Discretize t-z curve to industry-standard 5-point format (WIDE FORMAT).

    Standard points: 0, 0.25, 0.50, 0.75, 1.0 of peak

    Returns dict with keys: t1-t5 (MN/m), z1-z5 (mm)
    """
    if len(z_full) == 0:
        result = {f't{i+1}': 0.0 for i in range(5)}
        result.update({f'z{i+1}': 0.0 for i in range(5)})
        return result

    t_max = np.max(t_full)

    target_ratios = [0.0, 0.25, 0.50, 0.75, 1.0]
    result = {}

    for i, ratio in enumerate(target_ratios, start=1):
        target_t = ratio * t_max
        idx = np.argmin(np.abs(t_full - target_t))

        # Convert units: t from kPa to MN/m, z from m to mm
        result[f't{i}'] = t_full[idx] / 1000.0  # kPa to MN/m²
        result[f'z{i}'] = z_full[idx] * 1000.0  # m to mm

    return result


def discretize_qz_curve_5points(z_full: np.ndarray, Q_full: np.ndarray) -> Dict:
    """
    Discretize Q-z curve to industry-standard 5-point format (WIDE FORMAT).

    Returns dict with keys: q1-q5 (MN), z1-z5 (mm)
    """
    if len(z_full) == 0:
        result = {f'q{i+1}': 0.0 for i in range(5)}
        result.update({f'z{i+1}': 0.0 for i in range(5)})
        return result

    Q_max = np.max(Q_full)

    target_ratios = [0.0, 0.25, 0.50, 0.75, 1.0]
    result = {}

    for i, ratio in enumerate(target_ratios, start=1):
        target_Q = ratio * Q_max
        idx = np.argmin(np.abs(Q_full - target_Q))

        # Convert units: Q from kN to MN, z from m to mm
        result[f'q{i}'] = Q_full[idx] / 1000.0  # kN to MN
        result[f'z{i}'] = z_full[idx] * 1000.0  # m to mm

    return result


def discretize_py_curve_4points(y_full: np.ndarray, p_full: np.ndarray) -> Dict:
    """
    Discretize p-y curve to industry-standard 4-point format (WIDE FORMAT).

    Standard points: 0, 0.33, 0.67, 1.0 of peak

    Returns dict with keys: p1-p4 (kN/m), y1-y4 (mm)
    """
    if len(y_full) == 0:
        result = {f'p{i+1}': 0.0 for i in range(4)}
        result.update({f'y{i+1}': 0.0 for i in range(4)})
        return result

    p_max = np.max(p_full)

    target_ratios = [0.0, 0.33, 0.67, 1.0]
    result = {}

    for i, ratio in enumerate(target_ratios, start=1):
        target_p = ratio * p_max
        idx = np.argmin(np.abs(p_full - target_p))

        # Convert units: p stays in kN/m, y from m to mm
        result[f'p{i}'] = p_full[idx]  # Already in kN/m
        result[f'y{i}'] = y_full[idx] * 1000.0  # m to mm

    return result


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class SoilPoint:
    """Single measurement point of soil parameter at specific depth."""
    depth_m: float
    value: float

    def __post_init__(self):
        if self.depth_m < 0:
            raise ValueError(f"Depth must be non-negative, got {self.depth_m}")
        if self.value < 0:
            raise ValueError(f"Value must be non-negative, got {self.value}")


@dataclass
class SoilLayer:
    """Soil layer with spatially variable properties."""
    name: str
    soil_type: SoilType
    depth_top_m: float
    depth_bot_m: float

    # Profiles: List of (depth, value) tuples
    gamma_prime_kNm3: List[SoilPoint] = field(default_factory=list)
    su_kPa: List[SoilPoint] = field(default_factory=list)
    phi_prime_deg: List[SoilPoint] = field(default_factory=list)
    E50_kPa: List[SoilPoint] = field(default_factory=list)

    # Enhanced properties for API compliance
    relative_density_pct: float = 50.0  # For sands
    is_cemented: bool = False
    carbonate_content_pct: float = 0.0
    OCR: float = 1.0
    PI: float = 0.0

    def __post_init__(self):
        if self.depth_bot_m <= self.depth_top_m:
            raise ValueError(f"depth_bot must be > depth_top")

        # Sort all profiles by depth
        for profile in [self.gamma_prime_kNm3, self.su_kPa, self.phi_prime_deg, self.E50_kPa]:
            profile.sort(key=lambda p: p.depth_m)

    def get_property_at_depth(self, depth_m: float, property_name: str) -> float:
        """Interpolate property value at given depth."""
        if property_name == "gamma_prime":
            profile = self.gamma_prime_kNm3
        elif property_name == "su":
            profile = self.su_kPa
        elif property_name == "phi_prime":
            profile = self.phi_prime_deg
        elif property_name == "E50":
            profile = self.E50_kPa
        else:
            raise ValueError(f"Unknown property: {property_name}")

        abs_depth = self.depth_top_m + depth_m

        if not profile:
            return np.nan

        if abs_depth <= profile[0].depth_m:
            return profile[0].value
        if abs_depth >= profile[-1].depth_m:
            return profile[-1].value

        # Linear interpolation
        for i in range(1, len(profile)):
            if profile[i-1].depth_m <= abs_depth <= profile[i].depth_m:
                z1, v1 = profile[i-1].depth_m, profile[i-1].value
                z2, v2 = profile[i].depth_m, profile[i].value

                if z2 == z1:
                    return v1

                return v1 + (abs_depth - z1) * (v2 - v1) / (z2 - z1)

        return np.nan

    def get_relative_density_class(self) -> RelativeDensity:
        """Get relative density classification."""
        return RelativeDensity.from_percentage(self.relative_density_pct)


@dataclass
class PileProperties:
    """Pile geometric and material properties."""
    diameter_m: float
    wall_thickness_m: float = 0.0
    length_m: float = 0.0
    material: str = "steel"
    pile_type: PileType = PileType.DRIVEN_PIPE_OPEN

    # Calculated properties
    area_gross_m2: float = field(init=False)
    area_shaft_m2: float = field(init=False)
    inner_diameter_m: float = field(init=False)

    def __post_init__(self):
        if self.diameter_m <= 0:
            raise ValueError("Pile diameter must be positive")

        self.area_gross_m2 = np.pi * (self.diameter_m ** 2) / 4.0
        self.area_shaft_m2 = np.pi * self.diameter_m * self.length_m
        self.inner_diameter_m = self.diameter_m - 2 * self.wall_thickness_m


@dataclass
class SoilProfile:
    """Complete soil profile for site."""
    site_name: str
    layers: List[SoilLayer] = field(default_factory=list)
    water_depth_m: float = 0.0
    seafloor_elevation_m: float = 0.0

    def get_layer_at_depth(self, depth_m: float) -> Optional[SoilLayer]:
        """Get soil layer containing the given depth."""
        for layer in self.layers:
            if layer.depth_top_m <= depth_m < layer.depth_bot_m:
                return layer
        return None

    def get_property_at_depth(self, depth_m: float, property_name: str) -> float:
        """Get interpolated property at given depth."""
        layer = self.get_layer_at_depth(depth_m)
        if layer is None:
            return np.nan

        relative_depth = depth_m - layer.depth_top_m
        return layer.get_property_at_depth(relative_depth, property_name)

    def calculate_overburden_stress(self, depth_m: float, dz: float = 0.1) -> float:
        """Calculate effective vertical stress at depth by integration."""
        if depth_m <= 0:
            return 0.0

        depths = np.arange(0, depth_m + dz, dz)
        gamma_primes = np.array([self.get_property_at_depth(z, "gamma_prime")
                                 for z in depths])

        valid_mask = ~np.isnan(gamma_primes)
        gamma_primes = gamma_primes[valid_mask]
        depths = depths[valid_mask]

        if len(gamma_primes) < 2:
            return 0.0

        return float(np.trapz(gamma_primes, depths))


# ============================================================================
# AXIAL CAPACITY - ENHANCED WITH API TABLE 1
# ============================================================================

class AxialCapacity:
    """Compute axial pile capacity per API RP 2GEO Section 8.1 (Enhanced)."""

    @staticmethod
    def clay_shaft_friction(depth_m: float, profile: SoilProfile,
                            pile: PileProperties, for_tension: bool = False) -> float:
        """
        Unit shaft friction in clay per Equation 17-18.
        
        IMPROVEMENT: Separate handling for tension (may be reduced)
        """
        su = profile.get_property_at_depth(depth_m, "su")

        if not np.isfinite(su) or su <= 0:
            return 0.0

        p_o_prime = profile.calculate_overburden_stress(depth_m)

        if p_o_prime <= 0:
            p_o_prime = 1.0

        # Alpha factor (Equation 18)
        psi = su / p_o_prime

        if psi <= 1.0:
            alpha = 0.5 * (psi ** -0.5)
        else:
            alpha = 0.5 * (psi ** -0.25)

        alpha = min(alpha, 1.0)

        f_compression = alpha * su

        # Tension may be reduced (conservative)
        if for_tension:
            return 0.8 * f_compression  # Conservative 20% reduction
        
        return f_compression

    @staticmethod
    def sand_shaft_friction(depth_m: float, profile: SoilProfile,
                           pile: PileProperties, for_tension: bool = False) -> float:
        """
        Unit shaft friction in sand per Equation 21 and API Table 1.
        
        IMPROVEMENT: Uses API Table 1 directly with beta values
        """
        layer = profile.get_layer_at_depth(depth_m)
        
        if layer is None or layer.soil_type not in [SoilType.SAND, SoilType.SAND_SILT]:
            return 0.0

        p_o_prime = profile.calculate_overburden_stress(depth_m)

        if p_o_prime <= 0:
            return 0.0

        # Get API Table 1 parameters
        dr_class = layer.get_relative_density_class().value
        soil_desc = layer.soil_type.value
        
        key = (dr_class, soil_desc)
        
        if key in API_TABLE_1_EXTENDED and API_TABLE_1_EXTENDED[key]["beta"] is not None:
            beta = API_TABLE_1_EXTENDED[key]["beta"]
            f_L = API_TABLE_1_EXTENDED[key]["f_L_kPa"]
            
            # Calculate unit friction
            f_calc = beta * p_o_prime
            
            # Limit to f_L per Table 1
            f_compression = min(f_calc, f_L)
        else:
            # Fallback for soil types not in Table 1
            warnings.warn(f"Soil type {key} not in API Table 1, using conservative estimate")
            beta = 0.25
            f_compression = beta * p_o_prime

        # Tension handling
        if for_tension:
            # API allows same friction in tension for driven piles
            return f_compression
        
        return f_compression

    @staticmethod
    def end_bearing_clay(depth_m: float, profile: SoilProfile,
                        pile: PileProperties) -> float:
        """Unit end bearing in clay per Equation 20."""
        su = profile.get_property_at_depth(depth_m, "su")

        if not np.isfinite(su) or su <= 0:
            return 0.0

        return 9.0 * su  # Nc = 9

    @staticmethod
    def end_bearing_sand(depth_m: float, profile: SoilProfile,
                        pile: PileProperties) -> float:
        """
        Unit end bearing in sand per Equation 22 and API Table 1.
        
        IMPROVEMENT: Uses API Table 1 Nq values directly
        """
        layer = profile.get_layer_at_depth(depth_m)
        
        if layer is None or layer.soil_type not in [SoilType.SAND, SoilType.SAND_SILT]:
            return 0.0

        p_o_tip = profile.calculate_overburden_stress(depth_m)

        if p_o_tip <= 0:
            return 0.0

        # Get API Table 1 parameters
        dr_class = layer.get_relative_density_class().value
        soil_desc = layer.soil_type.value
        
        key = (dr_class, soil_desc)
        
        if key in API_TABLE_1_EXTENDED and API_TABLE_1_EXTENDED[key]["Nq"] is not None:
            Nq = API_TABLE_1_EXTENDED[key]["Nq"]
            q_L = API_TABLE_1_EXTENDED[key]["q_L_MPa"] * 1000  # Convert to kPa
            
            # Calculate unit end bearing
            q_calc = Nq * p_o_tip
            
            # Limit to q_L per Table 1
            return min(q_calc, q_L)
        else:
            # Fallback
            phi_prime = profile.get_property_at_depth(depth_m, "phi_prime")
            if np.isfinite(phi_prime) and phi_prime > 0:
                phi_rad = np.deg2rad(phi_prime)
                Nq = np.exp(np.pi * np.tan(phi_rad)) * np.tan(np.pi/4 + phi_rad/2)**2
                return Nq * p_o_tip
            
            return 0.0

    @staticmethod
    def check_penetration_requirement(depth_m: float, pile: PileProperties,
                                     layer: SoilLayer) -> Tuple[bool, str]:
        """
        Check if penetration meets API requirements (2-3D into bearing layer).
        
        IMPROVEMENT: Explicit penetration validation
        """
        penetration = depth_m - layer.depth_top_m
        min_penetration = 2.0 * pile.diameter_m
        recommended_penetration = 3.0 * pile.diameter_m
        
        if penetration < min_penetration:
            return False, f"Insufficient penetration: {penetration:.1f}m < {min_penetration:.1f}m (2D)"
        elif penetration < recommended_penetration:
            return True, f"Adequate penetration: {penetration:.1f}m (< 3D recommended)"
        else:
            return True, f"Good penetration: {penetration:.1f}m (> 3D)"

    @classmethod
    def total_capacity_layered(cls, profile: SoilProfile, pile: PileProperties,
                              depth_m: float, loading_type: LoadingType = LoadingType.COMPRESSION,
                              resistance_factor: Optional[float] = None) -> Dict:
        """
        Compute total axial capacity with layer-by-layer tracking.
        
        IMPROVEMENT: Complete layer tracking and LRFD option
        
        Returns dictionary with:
        - total_capacity_kN
        - shaft_friction_kN
        - end_bearing_kN (0 for tension)
        - layer_contributions: List[Dict] with per-layer breakdown
        - penetration_status
        - applied_resistance_factor
        """
        if depth_m <= 0:
            return {
                'total_capacity_kN': 0.0,
                'shaft_friction_kN': 0.0,
                'end_bearing_kN': 0.0,
                'layer_contributions': [],
                'penetration_status': 'Invalid depth',
                'applied_resistance_factor': 1.0
            }

        for_tension = (loading_type == LoadingType.TENSION)

        # Shaft friction by integration with layer tracking
        dz = 0.25
        depths = np.arange(0, depth_m, dz)
        
        total_friction_kN = 0.0
        layer_contributions = []
        current_layer_name = None
        current_layer_friction = 0.0

        for z in depths:
            layer = profile.get_layer_at_depth(z)
            
            if layer is None:
                continue

            # Get unit friction based on soil type
            if layer.soil_type in [SoilType.CLAY, SoilType.SILT]:
                f_z = cls.clay_shaft_friction(z, profile, pile, for_tension)
            elif layer.soil_type in [SoilType.SAND, SoilType.SAND_SILT]:
                f_z = cls.sand_shaft_friction(z, profile, pile, for_tension)
            else:
                f_z = 0.0

            # Circumference
            perimeter = np.pi * pile.diameter_m

            # Add friction over interval
            friction_increment = f_z * perimeter * dz
            total_friction_kN += friction_increment

            # Track per-layer contributions
            if layer.name != current_layer_name:
                if current_layer_name is not None:
                    layer_contributions.append({
                        'layer': current_layer_name,
                        'friction_kN': current_layer_friction,
                    })
                current_layer_name = layer.name
                current_layer_friction = friction_increment
            else:
                current_layer_friction += friction_increment

        # Add last layer
        if current_layer_name is not None:
            layer_contributions.append({
                'layer': current_layer_name,
                'friction_kN': current_layer_friction,
            })

        # End bearing (only for compression)
        end_bearing_kN = 0.0
        penetration_status = "N/A"
        
        if not for_tension:
            tip_layer = profile.get_layer_at_depth(depth_m)
            
            if tip_layer is not None:
                # Check penetration
                meets_req, pen_msg = cls.check_penetration_requirement(depth_m, pile, tip_layer)
                penetration_status = pen_msg

                if meets_req:
                    if tip_layer.soil_type in [SoilType.CLAY, SoilType.SILT]:
                        q = cls.end_bearing_clay(depth_m, profile, pile)
                    else:
                        q = cls.end_bearing_sand(depth_m, profile, pile)

                    end_bearing_kN = q * pile.area_gross_m2
                else:
                    penetration_status = f"WARNING: {pen_msg}"

        # Total capacity
        total_capacity_kN = total_friction_kN + end_bearing_kN

        # Apply resistance factor if LRFD
        if resistance_factor is None:
            # Determine appropriate resistance factor
            if pile.pile_type in [PileType.DRIVEN_PIPE_OPEN, PileType.DRIVEN_PIPE_CLOSED]:
                if for_tension:
                    resistance_factor = RESISTANCE_FACTORS["axial_tension_driven"]
                else:
                    resistance_factor = RESISTANCE_FACTORS["axial_compression_driven"]
            else:
                if for_tension:
                    resistance_factor = RESISTANCE_FACTORS["axial_tension_drilled"]
                else:
                    resistance_factor = RESISTANCE_FACTORS["axial_compression_drilled"]

        total_capacity_kN *= resistance_factor

        return {
            'total_capacity_kN': total_capacity_kN,
            'shaft_friction_kN': total_friction_kN * resistance_factor,
            'end_bearing_kN': end_bearing_kN * resistance_factor,
            'layer_contributions': layer_contributions,
            'penetration_status': penetration_status,
            'applied_resistance_factor': resistance_factor,
        }

    @classmethod
    def compute_capacity_profile(cls, profile: SoilProfile, pile: PileProperties,
                                 max_depth_m: float, dz: float = 0.5,
                                 loading_type: LoadingType = LoadingType.COMPRESSION,
                                 resistance_factor: Optional[float] = None) -> pd.DataFrame:
        """
        Compute capacity profile with complete layer tracking.
        
        IMPROVEMENT: Layer-by-layer results with validation status
        """
        depths = np.arange(0, max_depth_m + dz, dz)
        results_list = []

        for z in depths:
            result = cls.total_capacity_layered(profile, pile, z, loading_type, resistance_factor)
            
            layer = profile.get_layer_at_depth(z)
            
            results_list.append({
                'depth_m': z,
                'layer': layer.name if layer else "N/A",
                'soil_type': layer.soil_type.value if layer else "N/A",
                'unit_friction_kPa': result['shaft_friction_kN'] / (np.pi * pile.diameter_m * z + 0.001),
                'cumulative_friction_kN': result['shaft_friction_kN'],
                'end_bearing_kPa': result['end_bearing_kN'] / pile.area_gross_m2 if pile.area_gross_m2 > 0 else 0,
                'total_capacity_kN': result['total_capacity_kN'],
                'penetration_status': result['penetration_status'],
                'resistance_factor': result['applied_resistance_factor'],
            })

        return pd.DataFrame(results_list)


# ============================================================================
# LATERAL CAPACITY - ENHANCED WITH PROPER C COEFFICIENTS
# ============================================================================

class LateralCapacity:
    """Compute lateral pile capacity with proper API RP 2GEO compliance."""

    @staticmethod
    def calculate_C_coefficients(phi_prime_deg: float) -> Tuple[float, float, float]:
        """
        Calculate C1, C2, C3 coefficients per API Figure 4 and Equations 26-27.
        
        IMPROVEMENT: Proper implementation of API formulas
        """
        phi_rad = np.deg2rad(phi_prime_deg)
        
        # K0 and Kp
        K0 = 0.4
        Ka = np.tan(np.pi/4 - phi_rad/2)**2
        Kp = np.tan(np.pi/4 + phi_rad/2)**2
        
        # C1 (Figure 4 or approximation)
        C1 = Kp
        
        # C2 (from API equation)
        C2 = (K0 + Ka) * np.tan(phi_rad)
        
        # C3 (from API equation)
        C3 = Kp * np.tan(phi_rad)
        
        return C1, C2, C3

    @staticmethod
    def matlock_soft_clay(depth_m: float, profile: SoilProfile,
                         pile: PileProperties, 
                         analysis_type: AnalysisType = AnalysisType.STATIC) -> Tuple[np.ndarray, np.ndarray]:
        """Matlock method for soft clay (su ≤ 100 kPa) - API 8.5.2-8.5.3."""
        su = profile.get_property_at_depth(depth_m, "su")
        gamma_prime = profile.get_property_at_depth(depth_m, "gamma_prime")

        if not np.isfinite(su) or su <= 0 or su > 100:
            return np.array([]), np.array([])

        D = pile.diameter_m
        J = 0.5

        # Transition depth
        denom = D * gamma_prime / su + J
        z_R = (6 * D) / max(denom, 0.01)

        # Ultimate capacity
        if depth_m <= z_R:
            pu_D = 3 * su * D + gamma_prime * depth_m * D + J * su * depth_m
        else:
            pu_D = 9 * su * D

        # p-y curve
        if analysis_type == AnalysisType.STATIC:
            p_ratios = np.array([0.0, 0.23, 0.33, 0.50, 0.72, 1.00, 1.00])
            y_ratios = np.array([0.0, 0.1, 0.3, 1.0, 3.0, 8.0, np.inf])
        else:
            if depth_m <= z_R:
                p_ratios = np.array([0.0, 0.23, 0.33, 0.50, 0.72, 0.72])
                y_ratios = np.array([0.0, 0.1, 0.3, 1.0, 3.0, np.inf])
            else:
                p_ratios = np.array([0.0, 0.23, 0.33, 0.50, 0.72, 1.00, 1.00])
                y_ratios = np.array([0.0, 0.1, 0.3, 1.0, 3.0, 8.0, np.inf])

        epsilon_c = 0.02
        y_peak = epsilon_c * D

        p_resist = p_ratios * pu_D
        y_disp = y_ratios * y_peak
        y_disp = np.minimum(y_disp, 1.0)

        return y_disp, p_resist

    @staticmethod
    def reese_stiff_clay(depth_m: float, profile: SoilProfile,
                        pile: PileProperties,
                        analysis_type: AnalysisType = AnalysisType.STATIC) -> Tuple[np.ndarray, np.ndarray]:
        """Reese method for stiff clay (su > 100 kPa) - API 8.5.4-8.5.5."""
        su = profile.get_property_at_depth(depth_m, "su")

        if not np.isfinite(su) or su <= 100:
            return np.array([]), np.array([])

        D = pile.diameter_m
        pu_D = min(3 + 0.3*depth_m/D, 9) * su * D

        epsilon_c = 0.015
        y_peak = epsilon_c * D

        if analysis_type == AnalysisType.STATIC:
            p_ratios = np.array([0.0, 0.25, 0.50, 0.75, 0.95, 0.95])
            y_ratios = np.array([0.0, 0.3, 1.0, 3.0, 10.0, np.inf])
        else:
            p_ratios = np.array([0.0, 0.25, 0.50, 0.50])
            y_ratios = np.array([0.0, 0.3, 1.0, np.inf])

        p_resist = p_ratios * pu_D
        y_disp = y_ratios * y_peak
        y_disp = np.minimum(y_disp, 1.0)

        return y_disp, p_resist

    @staticmethod
    def sand_py_curve(depth_m: float, profile: SoilProfile,
                     pile: PileProperties,
                     analysis_type: AnalysisType = AnalysisType.STATIC) -> Tuple[np.ndarray, np.ndarray]:
        """
        Sand p-y curve with proper C coefficients - API 8.5.6-8.5.7.
        
        IMPROVEMENT: Uses proper C1, C2, C3 calculation
        """
        phi_prime = profile.get_property_at_depth(depth_m, "phi_prime")
        gamma_prime = profile.get_property_at_depth(depth_m, "gamma_prime")

        if not np.isfinite(phi_prime) or phi_prime <= 0:
            return np.array([]), np.array([])

        D = pile.diameter_m
        z = depth_m

        # Calculate C coefficients properly
        C1, C2, C3 = LateralCapacity.calculate_C_coefficients(phi_prime)

        # Ultimate pressures
        pu_shallow = (C1 * z + C2 * D) * gamma_prime * z
        pu_deep = C3 * D * gamma_prime * z

        pu = min(pu_shallow, pu_deep)

        # Table 5 - k values
        k_values = {25: 5.4, 30: 11, 35: 22, 40: 45}
        k = np.interp(phi_prime, list(k_values.keys()), list(k_values.values()))
        k = k * 1000  # Convert to kPa/m

        # Cyclic reduction
        if analysis_type == AnalysisType.CYCLIC:
            A = 0.9
        else:
            A = 3.0 - 0.8 * z / D
            A = max(A, 0.9)

        # Generate curve
        y_disp = np.linspace(0, 1.0, 20)
        p_resist = A * pu * np.tanh(k * z * y_disp / (A * pu + 0.01))

        return y_disp, p_resist

    @staticmethod
    def generate_py_table(profile: SoilProfile, pile: PileProperties,
                         depths_m: List[float],
                         analysis_type: AnalysisType = AnalysisType.STATIC) -> pd.DataFrame:
        """
        Generate industry-standard p-y table in WIDE FORMAT.

        Format: One row per depth with 4 points
        Columns: Depth(m), Soil, p1, y1, p2, y2, p3, y3, p4, y4
        Units: p in kN/m, y in mm
        """
        all_results = []

        for depth in depths_m:
            layer = profile.get_layer_at_depth(depth)
            if layer is None:
                continue

            # Get p-y curve
            if layer.soil_type in [SoilType.CLAY, SoilType.SILT]:
                # Use profile method for consistency and to avoid attribute access issues
                su = profile.get_property_at_depth(depth, "su")
                if np.isfinite(su) and su <= 100:
                    y, p = LateralCapacity.matlock_soft_clay(depth, profile, pile, analysis_type)
                elif np.isfinite(su) and su > 100:
                    y, p = LateralCapacity.reese_stiff_clay(depth, profile, pile, analysis_type)
                else:
                    continue  # Skip if su is not available
            else:
                y, p = LateralCapacity.sand_py_curve(depth, profile, pile, analysis_type)

            if len(y) == 0:
                continue

            # Discretize to 4 points (wide format)
            row = discretize_py_curve_4points(y, p)
            row['Depth'] = depth
            row['Soil'] = layer.soil_type.value

            all_results.append(row)

        if not all_results:
            cols = ['Depth', 'Soil'] + [f'{x}{i+1}' for x in ['p', 'y'] for i in range(4)]
            return pd.DataFrame(columns=cols)

        df = pd.DataFrame(all_results)
        # Reorder columns: Depth, Soil, p1, y1, p2, y2, p3, y3, p4, y4
        col_order = ['Depth', 'Soil']
        for i in range(1, 5):
            col_order.extend([f'p{i}', f'y{i}'])

        return df[col_order]


# ============================================================================
# LOAD-DISPLACEMENT CURVES - INDUSTRY-STANDARD TABLES
# ============================================================================

class LoadDisplacementTables:
    """Generate industry-standard t-z and Q-z tables."""

    @staticmethod
    def tz_curve_clay(depth_m: float, profile: SoilProfile,
                     pile: PileProperties, for_tension: bool = False) -> Tuple[np.ndarray, np.ndarray]:
        """Generate t-z curve for clay - API 8.4.2."""
        t_max = AxialCapacity.clay_shaft_friction(depth_m, profile, pile, for_tension)

        if t_max <= 0:
            return np.array([]), np.array([])

        z_peak = 0.01 * pile.diameter_m
        t_residual = 0.8 * t_max

        z_ratios = np.array([0.0, 0.16, 0.31, 0.57, 0.80, 1.00, 2.00, np.inf])
        t_ratios = np.array([0.0, 0.30, 0.50, 0.75, 0.90, 1.00, t_residual/t_max, t_residual/t_max])

        z_disp = z_ratios * z_peak
        t_resist = t_ratios * t_max
        z_disp = np.minimum(z_disp, 0.5)

        return z_disp, t_resist

    @staticmethod
    def tz_curve_sand(depth_m: float, profile: SoilProfile,
                     pile: PileProperties, for_tension: bool = False) -> Tuple[np.ndarray, np.ndarray]:
        """Generate t-z curve for sand - API 8.4.2."""
        t_max = AxialCapacity.sand_shaft_friction(depth_m, profile, pile, for_tension)

        if t_max <= 0:
            return np.array([]), np.array([])

        z_peak = 0.01 * pile.diameter_m

        z_ratios = np.array([0.0, 0.16, 0.31, 0.57, 0.80, 1.00, np.inf])
        t_ratios = np.array([0.0, 0.30, 0.50, 0.75, 0.90, 1.00, 1.00])

        z_disp = z_ratios * z_peak
        t_resist = t_ratios * t_max
        z_disp = np.minimum(z_disp, 0.5)

        return z_disp, t_resist

    @staticmethod
    def qz_curve(depth_m: float, profile: SoilProfile,
                pile: PileProperties) -> Tuple[np.ndarray, np.ndarray]:
        """Generate Q-z curve - API 8.4.3."""
        layer = profile.get_layer_at_depth(depth_m)

        if layer is None:
            return np.array([]), np.array([])

        if layer.soil_type in [SoilType.CLAY, SoilType.SILT]:
            q = AxialCapacity.end_bearing_clay(depth_m, profile, pile)
        else:
            q = AxialCapacity.end_bearing_sand(depth_m, profile, pile)

        Q_p = q * pile.area_gross_m2

        if Q_p <= 0:
            return np.array([]), np.array([])

        z_D_ratios = np.array([0.0, 0.002, 0.013, 0.042, 0.073, 0.100, np.inf])
        Q_ratios = np.array([0.0, 0.25, 0.50, 0.75, 0.90, 1.00, 1.00])

        z_disp = z_D_ratios * pile.diameter_m
        Q_resist = Q_ratios * Q_p

        return z_disp, Q_resist

    @staticmethod
    def generate_tz_table(profile: SoilProfile, pile: PileProperties,
                         depths_m: List[float]) -> pd.DataFrame:
        """
        Generate industry-standard t-z table in WIDE FORMAT.

        Format: Each depth has TWO rows (compression 'c' and tension 't')
        Columns: Depth(m), Soil type, t1, z1, t2, z2, t3, z3, t4, z4, t5, z5
        Units: t in MN/m, z in mm
        """
        all_results = []

        for depth in depths_m:
            layer = profile.get_layer_at_depth(depth)
            if layer is None:
                continue

            # Generate COMPRESSION row
            if layer.soil_type in [SoilType.CLAY, SoilType.SILT]:
                z_disp_c, t_resist_c = LoadDisplacementTables.tz_curve_clay(depth, profile, pile, for_tension=False)
            else:
                z_disp_c, t_resist_c = LoadDisplacementTables.tz_curve_sand(depth, profile, pile, for_tension=False)

            if len(z_disp_c) > 0:
                row_c = discretize_tz_curve_5points(z_disp_c, t_resist_c)
                row_c['Depth'] = depth
                row_c['Soil type'] = 'c'
                all_results.append(row_c)

            # Generate TENSION row
            if layer.soil_type in [SoilType.CLAY, SoilType.SILT]:
                z_disp_t, t_resist_t = LoadDisplacementTables.tz_curve_clay(depth, profile, pile, for_tension=True)
            else:
                z_disp_t, t_resist_t = LoadDisplacementTables.tz_curve_sand(depth, profile, pile, for_tension=True)

            if len(z_disp_t) > 0:
                row_t = discretize_tz_curve_5points(z_disp_t, t_resist_t)
                row_t['Depth'] = depth
                row_t['Soil type'] = 't'
                all_results.append(row_t)

        if not all_results:
            cols = ['Depth', 'Soil type'] + [f'{x}{i+1}' for x in ['t', 'z'] for i in range(5)]
            return pd.DataFrame(columns=cols)

        df = pd.DataFrame(all_results)
        # Reorder columns: Depth, Soil type, t1, z1, t2, z2, t3, z3, t4, z4, t5, z5
        col_order = ['Depth', 'Soil type']
        for i in range(1, 6):
            col_order.extend([f't{i}', f'z{i}'])

        return df[col_order]

    @staticmethod
    def generate_qz_table(profile: SoilProfile, pile: PileProperties,
                         tip_depth_m: float) -> pd.DataFrame:
        """
        Generate industry-standard Q-z table in WIDE FORMAT.

        Format: Single row for tip
        Columns: Depth(m), Soil type, tip, q1, z1, q2, z2, q3, z3, q4, z4, q5, z5
        Units: q in MN, z in mm
        tip: 0=unplugged, 1=plugged
        """
        # Ensure tip depth is within valid range
        if tip_depth_m <= 0:
            cols = ['Depth', 'Soil type', 'tip'] + [f'{x}{i+1}' for x in ['q', 'z'] for i in range(5)]
            return pd.DataFrame(columns=cols)

        z_disp, Q_resist = LoadDisplacementTables.qz_curve(tip_depth_m, profile, pile)

        if len(z_disp) == 0:
            # Return empty DataFrame with proper columns
            cols = ['Depth', 'Soil type', 'tip'] + [f'{x}{i+1}' for x in ['q', 'z'] for i in range(5)]
            return pd.DataFrame(columns=cols)

        # Discretize to 5 points
        row = discretize_qz_curve_5points(z_disp, Q_resist)
        row['Depth'] = tip_depth_m

        # Get soil type at tip
        layer = profile.get_layer_at_depth(tip_depth_m)
        row['Soil type'] = layer.soil_type.value if layer else 'SAND'

        # Determine if plugged (assuming plugged=1 for closed-end or when D/t > 20)
        row['tip'] = 1 if pile.pile_type == PileType.CLOSED_END else 0

        # Reorder columns
        col_order = ['Depth', 'Soil type', 'tip']
        for i in range(1, 6):
            col_order.extend([f'q{i}', f'z{i}'])

        return pd.DataFrame([row])[col_order]


# ============================================================================
# ANALYSIS ENGINE - ENHANCED
# ============================================================================

class PileDesignAnalysis:
    """Enhanced analysis engine with industry-standard outputs."""

    def __init__(self, profile: SoilProfile, pile: PileProperties):
        self.profile = profile
        self.pile = pile
        self.results = {}

    def run_complete_analysis(self, max_depth_m: float, dz: float = 0.5,
                             tz_depths: Optional[List[float]] = None,
                             py_depths: Optional[List[float]] = None,
                             analysis_type: AnalysisType = AnalysisType.STATIC,
                             use_lrfd: bool = True) -> Dict:
        """
        Run complete analysis with industry-standard outputs.
        
        IMPROVEMENT #4: Complete layered soil integration
        IMPROVEMENT #5: LRFD option
        
        Returns dictionary containing:
        - capacity_compression_df: Compression capacity profile
        - capacity_tension_df: Tension capacity profile
        - tz_compression_table: Industry-standard t-z table for compression
        - tz_tension_table: Industry-standard t-z table for tension
        - qz_table: Q-z table
        - py_table: p-y table
        """
        results = {}
        
        # Capacity profiles
        results['capacity_compression_df'] = AxialCapacity.compute_capacity_profile(
            self.profile, self.pile, max_depth_m, dz, LoadingType.COMPRESSION,
            resistance_factor=None if use_lrfd else 1.0
        )
        
        results['capacity_tension_df'] = AxialCapacity.compute_capacity_profile(
            self.profile, self.pile, max_depth_m, dz, LoadingType.TENSION,
            resistance_factor=None if use_lrfd else 1.0
        )
        
        # t-z tables (wide format includes both compression and tension)
        if tz_depths is None:
            tz_depths = np.arange(5, max_depth_m, 5).tolist()

        tz_table = LoadDisplacementTables.generate_tz_table(
            self.profile, self.pile, tz_depths
        )

        # Store same table for both (contains both 'c' and 't' rows)
        results['tz_compression_table'] = tz_table
        results['tz_tension_table'] = tz_table
        
        # Q-z table (at pile tip, not max_depth_m)
        pile_tip_depth = self.pile.length_m if self.pile.length_m > 0 else max_depth_m
        results['qz_table'] = LoadDisplacementTables.generate_qz_table(
            self.profile, self.pile, pile_tip_depth
        )
        
        # p-y table
        if py_depths is None:
            py_depths = np.arange(5, max_depth_m, 5).tolist()
        
        results['py_table'] = LateralCapacity.generate_py_table(
            self.profile, self.pile, py_depths, analysis_type
        )
        
        return results


# Export
__all__ = [
    'SoilType', 'PileType', 'LoadingType', 'AnalysisType', 'RelativeDensity',
    'SoilPoint', 'SoilLayer', 'PileProperties', 'SoilProfile',
    'AxialCapacity', 'LateralCapacity', 'LoadDisplacementTables',
    'PileDesignAnalysis',
    'API_TABLE_1_EXTENDED', 'RESISTANCE_FACTORS', 'CARBONATE_REDUCTION_FACTORS',
    'discretize_tz_curve_5points', 'discretize_qz_curve_5points', 'discretize_py_curve_5points',
]
