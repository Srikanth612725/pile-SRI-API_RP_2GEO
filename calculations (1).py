"""
calculations.py - Pile Foundation Design Engine
================================================

Implements API RP 2GEO Section 8 design methods for offshore pile foundations.

Key Features:
- Axial capacity (compression & tension) in clay and sand
- Lateral capacity (p-y curves) for soft clay, stiff clay, and sand
- t-z and Q-z curves for load-displacement analysis
- Scour effects on capacity
- Layered soil profile support
- Combined loading analysis

Reference: API RP 2GEO (Geotechnical and Foundation Design Considerations)
           Section 8: Pile Foundation Design

Author: Dr. Chitti S S U Srikanth
Version: 1.0.0
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


# Constants per API RP 2GEO
ALPHA_METHOD_LIMITS = {
    "highly_plastic_clay": {"min_su": 0, "max_su": 96},  # kPa
    "other_clay_upper": {"min_su": 0, "max_su": 24},  # kPa
    "other_clay_mid": {"min_su": 24, "max_su": 72},  # kPa
    "other_clay_lower": {"min_su": 72, "max_su": np.inf}  # kPa
}

BEARING_CAPACITY_FACTORS = {
    "sand": {
        "30": {"Nq": 18.4, "Ng": 18.1, "Nc": 30.1},
        "35": {"Nq": 33.3, "Ng": 48.0, "Nc": 46.1},
        "40": {"Nq": 64.2, "Ng": 109.4, "Nc": 75.3},
        "45": {"Nq": 134.9, "Ng": 299.5, "Nc": 133.9},
    }
}

# CPT correlation constants
CPT_COMPRESSION_PARAMS = {
    "Method_1": {"u": 0.023, "b": 0.2, "c": 0.4, "d": 1, "e": 0, "v": 0.016},
    "Method_2": {"u": 0.030, "b": 0.3, "c": 0.5, "d": 1, "e": 0, "v": 2},
    "Method_3": {"u": 0.043, "b": 0.45, "c": 0.90, "d": 0, "e": 1, "v": 2},
}


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

    # Profiles: List of (depth, value) tuples - interpolated between points
    gamma_prime_kNm3: List[SoilPoint] = field(default_factory=list)  # Submerged unit weight
    su_kPa: List[SoilPoint] = field(default_factory=list)  # Undrained shear strength (clay)
    phi_prime_deg: List[SoilPoint] = field(default_factory=list)  # Friction angle (sand)
    E50_kPa: List[SoilPoint] = field(default_factory=list)  # Secant modulus (optional)

    # Special properties
    is_cemented: bool = False  # For carbonate soils
    carbonate_content_pct: float = 0.0
    OCR: float = 1.0  # Overconsolidation ratio
    PI: float = 0.0  # Plasticity index

    def __post_init__(self):
        if self.depth_bot_m <= self.depth_top_m:
            raise ValueError(f"depth_bot must be > depth_top")

        # Sort all profiles by depth
        for profile in [self.gamma_prime_kNm3, self.su_kPa, self.phi_prime_deg, self.E50_kPa]:
            profile.sort(key=lambda p: p.depth_m)

    def get_property_at_depth(self, depth_m: float,
                              property_name: str) -> float:
        """
        Interpolate property value at given depth.

        Parameters:
        -----------
        depth_m : float
            Depth below soil layer top
        property_name : str
            One of: 'gamma_prime', 'su', 'phi_prime', 'E50'

        Returns:
        --------
        float
            Interpolated property value
        """
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

        # Get absolute depth in soil layer
        abs_depth = self.depth_top_m + depth_m

        if not profile:
            return np.nan

        # Limit to layer bounds
        if abs_depth <= profile[0].depth_m:
            return profile[0].value
        if abs_depth >= profile[-1].depth_m:
            return profile[-1].value

        # Linear interpolation
        for i in range(1, len(profile)):
            if profile[i-1].depth_m <= abs_depth <= profile[i].depth_m:
                z1, v1 = profile[i-1].depth_m, profile[i-1].value
                z2, v2 = profile[i].depth_m, profile[i].value

                if z2 == z1:  # Avoid division by zero
                    return v1

                return v1 + (abs_depth - z1) * (v2 - v1) / (z2 - z1)

        return np.nan


@dataclass
class PileProperties:
    """Pile geometric and material properties."""
    diameter_m: float  # Outer diameter
    wall_thickness_m: float = 0.0  # For pipe piles
    length_m: float = 0.0  # Embedded length (may vary during installation)
    material: str = "steel"  # steel, concrete, timber
    pile_type: PileType = PileType.DRIVEN_PIPE_OPEN

    # Calculated properties
    area_gross_m2: float = field(init=False)
    area_shaft_m2: float = field(init=False)
    inner_diameter_m: float = field(init=False)

    def __post_init__(self):
        if self.diameter_m <= 0:
            raise ValueError("Pile diameter must be positive")

        # Calculate derived properties
        self.area_gross_m2 = np.pi * (self.diameter_m ** 2) / 4.0
        self.area_shaft_m2 = np.pi * self.diameter_m * self.length_m  # Lateral surface area
        self.inner_diameter_m = self.diameter_m - 2 * self.wall_thickness_m


@dataclass
class SoilProfile:
    """Complete soil profile for site."""
    site_name: str
    layers: List[SoilLayer] = field(default_factory=list)
    water_depth_m: float = 0.0
    seafloor_elevation_m: float = 0.0  # Relative to MSL

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
        """
        Calculate effective vertical stress at depth by integration.

        Parameters:
        -----------
        depth_m : float
            Depth in meters
        dz : float
            Integration step size (m)

        Returns:
        --------
        float
            Effective vertical stress in kPa
        """
        if depth_m <= 0:
            return 0.0

        depths = np.arange(0, depth_m + dz, dz)
        gamma_primes = np.array([self.get_property_at_depth(z, "gamma_prime")
                                 for z in depths])

        # Remove NaN values
        valid_mask = ~np.isnan(gamma_primes)
        gamma_primes = gamma_primes[valid_mask]
        depths = depths[valid_mask]

        if len(gamma_primes) < 2:
            return 0.0

        # Trapezoidal integration
        return float(np.trapz(gamma_primes, depths))


# ============================================================================
# DESIGN METHODS - AXIAL CAPACITY
# ============================================================================

class AxialCapacity:
    """Compute axial pile capacity per API RP 2GEO Section 8.1."""

    @staticmethod
    def clay_shaft_friction(depth_m: float, profile: SoilProfile,
                            pile: PileProperties, method: str = "alpha") -> float:
        """
        Unit shaft friction in clay per Equation 17.

        f(z) = α * su

        where α is computed from Equation 18:
        α = 0.5 * ψ^(-0.5) for ψ ≤ 1.0
        α = 0.5 * ψ^(-0.25) for ψ > 1.0

        with ψ = su / p'o(z) and α ≤ 1.0

        Parameters:
        -----------
        depth_m : float
            Depth below seafloor (m)
        profile : SoilProfile
            Soil profile
        pile : PileProperties
            Pile properties
        method : str
            "alpha" (default), "beta", or "CPT-based"

        Returns:
        --------
        float
            Unit shaft friction in kPa
        """
        su = profile.get_property_at_depth(depth_m, "su")

        if not np.isfinite(su) or su <= 0:
            return 0.0

        # Calculate effective overburden stress
        p_o_prime = profile.calculate_overburden_stress(depth_m)

        if p_o_prime <= 0:
            p_o_prime = 1.0  # Avoid division by zero

        # Alpha factor calculation (Equation 18)
        psi = su / p_o_prime

        if psi <= 1.0:
            alpha = 0.5 * (psi ** -0.5)
        else:
            alpha = 0.5 * (psi ** -0.25)

        alpha = min(alpha, 1.0)  # Cap at 1.0

        return alpha * su

    @staticmethod
    def sand_shaft_friction(depth_m: float, profile: SoilProfile,
                            method: str = "beta") -> float:
        """
        Unit shaft friction in sand per Equation 21.

        f(z) = β * p'o(z)

        where β = K * tan(δ_cv)
        K typically 0.8-1.2 for driven piles
        δ_cv is constant-volume friction angle

        Parameters:
        -----------
        depth_m : float
            Depth below seafloor (m)
        profile : SoilProfile
            Soil profile
        method : str
            "beta" (default) or "CPT-based"

        Returns:
        --------
        float
            Unit shaft friction in kPa
        """
        phi_prime = profile.get_property_at_depth(depth_m, "phi_prime")

        if not np.isfinite(phi_prime) or phi_prime <= 0:
            return 0.0

        p_o_prime = profile.calculate_overburden_stress(depth_m)

        if p_o_prime <= 0:
            return 0.0

        # Beta factor (K * tan δ)
        # Conservative default for offshore driven piles
        K = 1.0  # Could be site-specific
        delta_cv = 0.7 * phi_prime  # Typical reduction from peak

        beta = K * np.tan(np.deg2rad(delta_cv))

        return beta * p_o_prime

    @staticmethod
    def end_bearing_clay(depth_m: float, profile: SoilProfile,
                         pile: PileProperties) -> float:
        """
        Unit end bearing in clay per Equation 20.

        q = 9 * su

        with limit of 2-3 diameters penetration into bearing layer
        """
        su = profile.get_property_at_depth(depth_m, "su")

        if not np.isfinite(su) or su <= 0:
            return 0.0

        # Nc factor (simplified)
        Nc = 9.0  # Per Equation 20

        return Nc * su

    @staticmethod
    def end_bearing_sand(depth_m: float, profile: SoilProfile,
                         pile: PileProperties, method: str = "bearing_factor") -> float:
        """
        Unit end bearing in sand per Equation 22.

        q = Nq * p'o_tip

        Parameters:
        -----------
        depth_m : float
            Depth of pile tip
        profile : SoilProfile
            Soil profile
        method : str
            "bearing_factor" (default) or "relative_density"

        Returns:
        --------
        float
            Unit end bearing pressure in kPa
        """
        phi_prime = profile.get_property_at_depth(depth_m, "phi_prime")

        if not np.isfinite(phi_prime) or phi_prime <= 0:
            return 0.0

        p_o_tip = profile.calculate_overburden_stress(depth_m)

        if p_o_tip <= 0:
            return 0.0

        # Bearing capacity factor (simplified Meyerhof)
        phi_rad = np.deg2rad(phi_prime)
        Nq = np.exp(np.pi * np.tan(phi_rad)) * np.tan(np.pi/4 + phi_rad/2)**2

        return Nq * p_o_tip

    @classmethod
    def total_axial_compression(cls, profile: SoilProfile, pile: PileProperties,
                                depth_m: float) -> float:
        """
        Total axial pile capacity in compression.

        Qc = Qf,c + Qp = ∫ f(z) * dAs + q * Ap

        (Equation 16 from API RP 2GEO)
        """
        if depth_m <= 0 or depth_m > max(layer.depth_bot_m for layer in profile.layers):
            return 0.0

        # Shaft friction by integration
        dz = 0.25  # Integration step
        depths = np.arange(0, depth_m, dz)

        layer = profile.get_layer_at_depth(depth_m)

        total_friction_kN = 0.0

        for z in depths:
            current_layer = profile.get_layer_at_depth(z)

            if current_layer.soil_type == SoilType.CLAY:
                f_z = cls.clay_shaft_friction(z, profile, pile)
            elif current_layer.soil_type == SoilType.SAND:
                f_z = cls.sand_shaft_friction(z, profile)
            else:
                f_z = 0.0

            # Circumference at this depth
            perimeter = np.pi * pile.diameter_m

            # Add friction over interval
            total_friction_kN += f_z * perimeter * dz

        # End bearing
        if layer.soil_type == SoilType.CLAY:
            q = cls.end_bearing_clay(depth_m, profile, pile)
        else:
            q = cls.end_bearing_sand(depth_m, profile, pile)

        end_bearing_kN = q * pile.area_gross_m2

        return total_friction_kN + end_bearing_kN


# ============================================================================
# DESIGN METHODS - LATERAL CAPACITY (p-y CURVES)
# ============================================================================

class LateralCapacity:
    """Compute lateral pile capacity using p-y curve methods per API RP 2GEO Section 8.5."""

    @staticmethod
    def matlock_soft_clay(depth_m: float, profile: SoilProfile,
                          pile: PileProperties, analysis_type: AnalysisType = AnalysisType.STATIC) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate p-y curve for soft clay (su ≤ 100 kPa) using Matlock method.

        Per API RP 2GEO Section 8.5.2-8.5.3

        Ultimate lateral bearing capacity:
        pu*D = 3*su*D near surface
        pu*D = 9*su*D at depth

        with transition zone parameterized by J (empirical constant)

        Parameters:
        -----------
        depth_m : float
            Depth of pile section (m)
        profile : SoilProfile
            Soil profile
        pile : PileProperties
            Pile properties
        analysis_type : AnalysisType
            Static or cyclic loading

        Returns:
        --------
        tuple (y_disp, p_resist)
            Lateral displacement (m) and resistance (kPa)
        """
        su = profile.get_property_at_depth(depth_m, "su")
        gamma_prime = profile.get_property_at_depth(depth_m, "gamma_prime")

        if not np.isfinite(su) or su <= 0 or su > 100:
            return np.array([]), np.array([])

        # Ultimate lateral capacity (Equation 23-24)
        D = pile.diameter_m
        J = 0.5  # Gulf of Mexico clays (can be 0.25-0.5)

        # Depth to transition zone (Equation 25)
        denom = D * gamma_prime / su + J
        z_R = (6 * D) / max(denom, 0.01)

        if depth_m <= z_R:
            pu_D = 3 * su * D + gamma_prime * depth_m * D + J * su * depth_m
        else:
            pu_D = 9 * su * D

        # p-y curve coordinates (Table 3 for static, Table 4 for cyclic)
        if analysis_type == AnalysisType.STATIC:
            p_ratios = np.array([0.0, 0.23, 0.33, 0.50, 0.72, 1.00, 1.00])
            y_ratios = np.array([0.0, 0.1, 0.3, 1.0, 3.0, 8.0, np.inf])
        else:  # Cyclic
            if depth_m <= z_R:
                p_ratios = np.array([0.0, 0.23, 0.33, 0.50, 0.72, 0.72])
                y_ratios = np.array([0.0, 0.1, 0.3, 1.0, 3.0, np.inf])
            else:
                p_ratios = np.array([0.0, 0.23, 0.33, 0.50, 0.72, 1.00, 1.00])
                y_ratios = np.array([0.0, 0.1, 0.3, 1.0, 3.0, 8.0, np.inf])

        # Strain parameter
        # Simplified: εc = 0.02 (2% strain) typical for Gulf of Mexico
        epsilon_c = 0.02
        y_peak = epsilon_c * D

        # Generate curve
        p_resist = p_ratios * pu_D
        y_disp = y_ratios * y_peak

        # Clip to reasonable values
        y_disp = np.minimum(y_disp, 1.0)  # Max 1.0m displacement

        return y_disp, p_resist

    @staticmethod
    def reese_stiff_clay(depth_m: float, profile: SoilProfile,
                         pile: PileProperties, analysis_type: AnalysisType = AnalysisType.STATIC) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate p-y curve for stiff clay (su > 100 kPa) using Reese et al. method.

        Per API RP 2GEO Section 8.5.4-8.5.5

        Stiff clays are more brittle than soft clays.

        Parameters:
        -----------
        depth_m : float
            Depth of pile section (m)
        profile : SoilProfile
            Soil profile
        pile : PileProperties
            Pile properties
        analysis_type : AnalysisType
            Static or cyclic loading

        Returns:
        --------
        tuple (y_disp, p_resist)
            Lateral displacement (m) and resistance (kPa)
        """
        su = profile.get_property_at_depth(depth_m, "su")
        gamma_prime = profile.get_property_at_depth(depth_m, "gamma_prime")

        if not np.isfinite(su) or su <= 100:
            return np.array([]), np.array([])

        D = pile.diameter_m

        # Similar to soft clay but with brittle behavior
        # Ultimate capacity remains similar
        pu_D = min(3 + 0.3*depth_m/D, 9) * su * D

        # Stiff clay p-y curves show more brittle behavior
        # Steeper initial slope, rapid deterioration

        # Generate trilinear approximation
        epsilon_c = 0.015  # Smaller strain for stiff clay
        y_peak = epsilon_c * D

        if analysis_type == AnalysisType.STATIC:
            # Steeper for stiff clay
            p_ratios = np.array([0.0, 0.25, 0.50, 0.75, 0.95, 0.95])
            y_ratios = np.array([0.0, 0.3, 1.0, 3.0, 10.0, np.inf])
        else:  # Cyclic - more deterioration
            p_ratios = np.array([0.0, 0.25, 0.50, 0.50])
            y_ratios = np.array([0.0, 0.3, 1.0, np.inf])

        p_resist = p_ratios * pu_D
        y_disp = y_ratios * y_peak
        y_disp = np.minimum(y_disp, 1.0)

        return y_disp, p_resist

    @staticmethod
    def sand_py_curve(depth_m: float, profile: SoilProfile,
                      pile: PileProperties, analysis_type: AnalysisType = AnalysisType.STATIC) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate p-y curve for sand using API RP 2GEO Section 8.5.6-8.5.7.

        Ultimate lateral resistance (minimum of shallow and deep):
        pu_s = (C1*z + C2*D) * γ' * z  (shallow)
        pu_d = C3 * D * γ' * z  (deep)

        Non-linear p-y relationship per Equation 28:
        p = A * pu * tanh(k*z*y / (A*pu))
        """
        phi_prime = profile.get_property_at_depth(depth_m, "phi_prime")
        gamma_prime = profile.get_property_at_depth(depth_m, "gamma_prime")

        if not np.isfinite(phi_prime) or phi_prime <= 0:
            return np.array([]), np.array([])

        D = pile.diameter_m
        z = depth_m

        # Calculate C1, C2, C3 coefficients (functions of φ')
        # Simplified for common friction angles
        phi_rad = np.deg2rad(phi_prime)
        K0 = 0.4
        Kp = np.tan(np.pi/4 + phi_rad/2)**2

        C1 = Kp
        C2 = K0 * Kp * D / 2.0
        C3 = 3.0 + 0.4 * z / D

        # Shallow and deep ultimate pressures
        pu_shallow = (C1 * z + C2) * gamma_prime * z
        pu_deep = C3 * gamma_prime * z

        # Use minimum per Equation 26-27
        pu = min(pu_shallow, pu_deep)

        # k = rate of increase of modulus (Table 5)
        k_values = {25: 5.4, 30: 11, 35: 22, 40: 45}
        k = min(k_values.values(), key=lambda v: abs(45 - phi_prime))  # Approximate
        k = k * 1000  # Convert to kPa/m

        # Cyclic reduction factor A
        if analysis_type == AnalysisType.CYCLIC:
            A = 0.9
        else:
            A = 3.0 - 0.8 * z / D
            A = max(A, 0.9)

        # Generate non-linear p-y curve (Equation 28)
        y_disp = np.linspace(0, 1.0, 20)  # Max 1m displacement
        p_resist = A * pu * np.tanh(k * z * y_disp / (A * pu + 0.01))

        return y_disp, p_resist


# ============================================================================
# DESIGN METHODS - LOAD-DISPLACEMENT CURVES (t-z and Q-z)
# ============================================================================

class LoadDisplacementCurves:
    """Compute t-z and Q-z curves per API RP 2GEO Section 8.4."""

    @staticmethod
    def tz_curve_clay(depth_m: float, profile: SoilProfile,
                      pile: PileProperties) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate t-z (axial shear transfer-displacement) curve for clay.

        Per API RP 2GEO Section 8.4.2 and Table 2

        Typical peak displacement z_peak = 0.01 * D (1% of diameter)
        Residual ratio t_res/t_max = 0.7-0.9 for clay
        """
        su = profile.get_property_at_depth(depth_m, "su")

        if not np.isfinite(su) or su <= 0:
            return np.array([]), np.array([])

        # Maximum shaft friction
        t_max = AxialCapacity.clay_shaft_friction(depth_m, profile, pile)

        if t_max <= 0:
            return np.array([]), np.array([])

        # Peak displacement (1% of diameter typical)
        z_peak = 0.01 * pile.diameter_m

        # Residual adhesion (Table 2)
        t_residual = 0.8 * t_max  # Average of 0.7-0.9 range

        # t-z curve coordinates (Table 2)
        z_ratios = np.array([0.0, 0.16, 0.31, 0.57, 0.80, 1.00, 2.00, np.inf])
        t_ratios = np.array([0.0, 0.30, 0.50, 0.75, 0.90, 1.00, t_residual/t_max, t_residual/t_max])

        # Generate curve
        z_disp = z_ratios * z_peak
        t_resist = t_ratios * t_max

        # Limit to reasonable max displacement
        z_disp = np.minimum(z_disp, 0.5)

        return z_disp, t_resist

    @staticmethod
    def tz_curve_sand(depth_m: float, profile: SoilProfile,
                      pile: PileProperties) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate t-z curve for sand.

        Per API RP 2GEO Table 2
        Sand typically maintains full capacity (t_res = t_max)
        """
        # Maximum shaft friction
        t_max = AxialCapacity.sand_shaft_friction(depth_m, profile)

        if t_max <= 0:
            return np.array([]), np.array([])

        # Peak displacement
        z_peak = 0.01 * pile.diameter_m

        # t-z curve coordinates (Table 2)
        z_ratios = np.array([0.0, 0.16, 0.31, 0.57, 0.80, 1.00, np.inf])
        t_ratios = np.array([0.0, 0.30, 0.50, 0.75, 0.90, 1.00, 1.00])

        # Generate curve
        z_disp = z_ratios * z_peak
        t_resist = t_ratios * t_max

        z_disp = np.minimum(z_disp, 0.5)

        return z_disp, t_resist

    @staticmethod
    def qz_curve(depth_m: float, profile: SoilProfile,
                 pile: PileProperties) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate Q-z (end bearing-displacement) curve.

        Per API RP 2GEO Section 8.4.3 and Figure 3

        Large tip movements (up to 10% D) required to fully mobilize
        """
        layer = profile.get_layer_at_depth(depth_m)

        if layer.soil_type == SoilType.CLAY:
            Q_p = AxialCapacity.end_bearing_clay(depth_m, profile, pile) * pile.area_gross_m2
        else:
            Q_p = AxialCapacity.end_bearing_sand(depth_m, profile, pile) * pile.area_gross_m2

        if Q_p <= 0:
            return np.array([]), np.array([])

        # Q-z curve coordinates (Figure 3, Table in Section 8.4.3)
        z_D_ratios = np.array([0.0, 0.002, 0.013, 0.042, 0.073, 0.100, np.inf])
        Q_ratios = np.array([0.0, 0.25, 0.50, 0.75, 0.90, 1.00, 1.00])

        # Generate curve
        z_disp = z_D_ratios * pile.diameter_m
        Q_resist = Q_ratios * Q_p

        return z_disp, Q_resist


# ============================================================================
# UTILITIES
# ============================================================================

def calculate_scour_effect(depth_m: float, scour_depth_m: float,
                           profile: SoilProfile) -> float:
    """
    Calculate reduction factor for scour effect on capacity.

    Per API RP 2GEO Section C.8.5

    Scour reduces both ultimate pressure and stiffness.
    """
    if scour_depth_m <= 0:
        return 1.0

    # Simple linear reduction (conservative)
    reduction = 1.0 - (scour_depth_m / max(depth_m, 1.0))

    return max(reduction, 0.5)  # Don't reduce by more than 50%


def check_safety_factors(capacity_kN: float, design_load_kN: float,
                         safety_factor: float = 2.5) -> Tuple[bool, float]:
    """
    Check if design meets safety factor requirement.

    Returns:
    --------
    (meets_requirement, actual_SF)
    """
    if capacity_kN <= 0:
        return False, 0.0

    actual_SF = capacity_kN / max(design_load_kN, 0.1)

    return actual_SF >= safety_factor, actual_SF


# ============================================================================
# ANALYSIS ENGINE
# ============================================================================

class PileDesignAnalysis:
    """Main analysis engine combining all design methods."""

    def __init__(self, profile: SoilProfile, pile: PileProperties):
        self.profile = profile
        self.pile = pile
        self.results = {}

    def compute_axial_capacity_profile(self, max_depth_m: float,
                                       dz: float = 0.5) -> pd.DataFrame:
        """
        Compute axial capacity at multiple depths.

        Returns DataFrame with capacity vs depth
        """
        depths = np.arange(0, max_depth_m + dz, dz)

        results_list = []

        for z in depths:
            layer = self.profile.get_layer_at_depth(z)
            if layer is None:
                continue

            if layer.soil_type == SoilType.CLAY:
                capacity = AxialCapacity.total_axial_compression(self.profile, self.pile, z)
            else:
                capacity = AxialCapacity.total_axial_compression(self.profile, self.pile, z)

            results_list.append({
                'depth_m': z,
                'soil_type': layer.soil_type.value,
                'capacity_kN': capacity,
            })

        return pd.DataFrame(results_list)

    def compute_py_curves(self, depths_m: List[float],
                          analysis_type: AnalysisType = AnalysisType.STATIC) -> Dict[float, Tuple]:
        """
        Compute p-y curves at specified depths.

        Returns dict mapping depth -> (y_disp, p_resist) arrays
        """
        py_curves = {}

        for z in depths_m:
            layer = self.profile.get_layer_at_depth(z)
            if layer is None:
                continue

            if layer.soil_type == SoilType.CLAY:
                if layer.su is not None and layer.get_property_at_depth(z - layer.depth_top_m, "su") <= 100:
                    y, p = LateralCapacity.matlock_soft_clay(z, self.profile, self.pile, analysis_type)
                else:
                    y, p = LateralCapacity.reese_stiff_clay(z, self.profile, self.pile, analysis_type)
            else:
                y, p = LateralCapacity.sand_py_curve(z, self.profile, self.pile, analysis_type)

            if len(y) > 0:
                py_curves[z] = (y, p)

        return py_curves


# Export key classes and functions
__all__ = [
    'SoilType', 'PileType', 'LoadingType', 'AnalysisType',
    'SoilPoint', 'SoilLayer', 'PileProperties', 'SoilProfile',
    'AxialCapacity', 'LateralCapacity', 'LoadDisplacementCurves',
    'PileDesignAnalysis',
    'calculate_scour_effect', 'check_safety_factors',
]
