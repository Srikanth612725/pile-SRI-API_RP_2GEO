"""
Basic tests to validate module imports.
"""
import pytest


def test_calculations_import():
    """Test that calculations_v2_1 module can be imported."""
    try:
        import calculations_v2_1
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import calculations_v2_1: {e}")


def test_calculations_classes():
    """Test that main classes can be imported."""
    try:
        from calculations_v2_1 import (
            SoilType, PileType, LoadingType, AnalysisType,
            SoilLayer, PileProperties, SoilProfile,
            AxialCapacity, LateralCapacity, LoadDisplacementTables,
            PileDesignAnalysis
        )
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import classes: {e}")


def test_discretization_functions():
    """Test that discretization functions exist."""
    try:
        from calculations_v2_1 import (
            discretize_tz_curve_5points,
            discretize_qz_curve_5points,
            discretize_py_curve_4points
        )
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import discretization functions: {e}")


def test_basic_calculations():
    """Test basic calculation functionality."""
    from calculations_v2_1 import (
        SoilType, PileType, SoilLayer, PileProperties, SoilProfile
    )

    # Create a simple test case
    layer = SoilLayer(
        name="Test Sand",
        soil_type=SoilType.SAND,
        top_depth_m=0.0,
        thickness_m=20.0,
        gamma_kN_m3=18.0,
        phi_degrees=35.0
    )

    profile = SoilProfile([layer])
    assert len(profile.layers) == 1

    pile = PileProperties(
        diameter_m=1.5,
        wall_thickness_m=0.05,
        length_m=15.0,
        pile_type=PileType.DRIVEN_PIPE_OPEN
    )

    assert pile.diameter_m == 1.5
    assert pile.length_m == 15.0
