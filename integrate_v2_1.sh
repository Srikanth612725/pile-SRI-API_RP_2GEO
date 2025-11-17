#!/bin/bash
# integrate_v2_1.sh - Automated Integration Script for pile-SRI v2.1
# ==================================================================
#
# This script automates the integration of calculations_v2_1.py and
# app_pile_design_v2_1.py into your existing pile-SRI application.
#
# Usage:
#   chmod +x integrate_v2_1.sh
#   ./integrate_v2_1.sh [option]
#
# Options:
#   --direct      Direct replacement (make v2.1 the default)
#   --sidebyside  Keep both versions for comparison
#   --test        Test integration without changes
#
# Author: Dr. Chitti S S U Srikanth
# Date: 2025-11-06

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project directories
PROJECT_DIR="/mnt/project"
OUTPUT_DIR="/mnt/user-data/outputs"
BACKUP_DIR="/mnt/project/backup_$(date +%Y%m%d_%H%M%S)"

# Function to print colored messages
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to create backup
create_backup() {
    print_info "Creating backup in $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
    
    if [ -f "$PROJECT_DIR/calculations.py" ]; then
        cp "$PROJECT_DIR/calculations.py" "$BACKUP_DIR/"
        print_success "Backed up calculations.py"
    fi
    
    if [ -f "$PROJECT_DIR/app_pile_design.py" ]; then
        cp "$PROJECT_DIR/app_pile_design.py" "$BACKUP_DIR/"
        print_success "Backed up app_pile_design.py"
    fi
}

# Function to verify files exist
verify_files() {
    print_info "Verifying v2.1 files..."
    
    if [ ! -f "$OUTPUT_DIR/calculations_v2_1.py" ]; then
        print_error "calculations_v2_1.py not found in $OUTPUT_DIR"
        exit 1
    fi
    
    if [ ! -f "$OUTPUT_DIR/app_pile_design_v2_1.py" ]; then
        print_error "app_pile_design_v2_1.py not found in $OUTPUT_DIR"
        exit 1
    fi
    
    print_success "All required files found"
}

# Function to test imports
test_imports() {
    print_info "Testing Python imports..."
    
    cd "$PROJECT_DIR"
    
    # Test calculations_v2_1
    python3 -c "from calculations_v2_1 import *; print('✅ calculations_v2_1 imports OK')" 2>&1
    
    if [ $? -eq 0 ]; then
        print_success "calculations_v2_1.py imports successfully"
    else
        print_error "Import test failed for calculations_v2_1.py"
        exit 1
    fi
}

# Integration Mode 1: Direct Replacement
integration_direct() {
    print_info "Starting DIRECT REPLACEMENT integration..."
    
    # Create backup
    create_backup
    
    # Copy v2.1 files
    print_info "Copying v2.1 files to project directory..."
    cp "$OUTPUT_DIR/calculations_v2_1.py" "$PROJECT_DIR/"
    cp "$OUTPUT_DIR/app_pile_design_v2_1.py" "$PROJECT_DIR/"
    print_success "Files copied"
    
    # Test imports
    test_imports
    
    # Rename old files
    print_info "Renaming old files..."
    if [ -f "$PROJECT_DIR/calculations.py" ]; then
        mv "$PROJECT_DIR/calculations.py" "$PROJECT_DIR/calculations_v1_old.py"
    fi
    if [ -f "$PROJECT_DIR/app_pile_design.py" ]; then
        mv "$PROJECT_DIR/app_pile_design.py" "$PROJECT_DIR/app_pile_design_v1_old.py"
    fi
    
    # Make v2.1 the default
    print_info "Making v2.1 the default version..."
    mv "$PROJECT_DIR/calculations_v2_1.py" "$PROJECT_DIR/calculations.py"
    mv "$PROJECT_DIR/app_pile_design_v2_1.py" "$PROJECT_DIR/app_pile_design.py"
    
    print_success "Integration complete! v2.1 is now the default."
    print_info "Backup saved to: $BACKUP_DIR"
    print_info "Old files renamed with '_v1_old' suffix"
    print_info ""
    print_info "To run the app:"
    print_info "  cd $PROJECT_DIR"
    print_info "  streamlit run app_pile_design.py"
}

# Integration Mode 2: Side-by-side
integration_sidebyside() {
    print_info "Starting SIDE-BY-SIDE integration..."
    
    # Create backup
    create_backup
    
    # Copy v2.1 files (keep separate names)
    print_info "Copying v2.1 files to project directory..."
    cp "$OUTPUT_DIR/calculations_v2_1.py" "$PROJECT_DIR/"
    cp "$OUTPUT_DIR/app_pile_design_v2_1.py" "$PROJECT_DIR/"
    print_success "Files copied"
    
    # Test imports
    test_imports
    
    print_success "Integration complete! Both versions available."
    print_info "Backup saved to: $BACKUP_DIR"
    print_info ""
    print_info "To run v1 (old):"
    print_info "  streamlit run app_pile_design.py --server.port 8501"
    print_info ""
    print_info "To run v2.1 (new):"
    print_info "  streamlit run app_pile_design_v2_1.py --server.port 8502"
}

# Integration Mode 3: Test only
integration_test() {
    print_info "Running TEST MODE (no changes to existing files)..."
    
    # Copy to temporary location
    TEMP_DIR="/tmp/pile_sri_test"
    mkdir -p "$TEMP_DIR"
    
    print_info "Copying v2.1 files to test directory..."
    cp "$OUTPUT_DIR/calculations_v2_1.py" "$TEMP_DIR/"
    cp "$OUTPUT_DIR/app_pile_design_v2_1.py" "$TEMP_DIR/"
    
    # Test imports
    cd "$TEMP_DIR"
    python3 -c "from calculations_v2_1 import *; print('✅ Import test passed')" 2>&1
    
    if [ $? -eq 0 ]; then
        print_success "Import test PASSED"
    else
        print_error "Import test FAILED"
        exit 1
    fi
    
    # Run simple analysis
    print_info "Running simple analysis test..."
    
    cat > "$TEMP_DIR/test_analysis.py" << 'EOF'
from calculations_v2_1 import *

# Create simple profile
profile = SoilProfile("Test Site")
layer = SoilLayer(
    "Dense Sand", SoilType.SAND, 0, 20,
    gamma_prime_kNm3=[SoilPoint(0, 9.0)],
    phi_prime_deg=[SoilPoint(0, 35)],
    relative_density_pct=75.0
)
profile.layers.append(layer)

# Create pile
pile = PileProperties(diameter_m=1.4, wall_thickness_m=0.016, length_m=20)

# Run analysis
analysis = PileDesignAnalysis(profile, pile)
results = analysis.run_complete_analysis(max_depth_m=20, use_lrfd=True)

print(f"✅ Analysis complete!")
print(f"Max capacity: {results['capacity_compression_df']['total_capacity_kN'].max():.0f} kN")
print(f"Tables generated: {len(results)}")
EOF
    
    python3 "$TEMP_DIR/test_analysis.py"
    
    if [ $? -eq 0 ]; then
        print_success "Analysis test PASSED"
    else
        print_error "Analysis test FAILED"
        exit 1
    fi
    
    # Cleanup
    rm -rf "$TEMP_DIR"
    
    print_success "All tests passed!"
    print_info "Your project files were NOT modified."
    print_info "To integrate, run with --direct or --sidebyside"
}

# Main execution
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║  pile-SRI v2.1 Integration Script                     ║"
    echo "║  Automated setup for calculations_v2_1.py             ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo ""
    
    # Verify files exist
    verify_files
    
    # Check integration mode
    MODE="${1:---test}"
    
    case "$MODE" in
        --direct)
            print_warning "DIRECT REPLACEMENT will make v2.1 the default version"
            read -p "Continue? (y/N) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                integration_direct
            else
                print_info "Integration cancelled"
                exit 0
            fi
            ;;
        --sidebyside)
            integration_sidebyside
            ;;
        --test)
            integration_test
            ;;
        *)
            print_error "Invalid option: $MODE"
            echo ""
            echo "Usage: $0 [option]"
            echo ""
            echo "Options:"
            echo "  --direct      Direct replacement (make v2.1 the default)"
            echo "  --sidebyside  Keep both versions for comparison"
            echo "  --test        Test integration without changes (default)"
            echo ""
            exit 1
            ;;
    esac
    
    echo ""
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║  ✅ Integration Complete!                             ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo ""
}

# Run main function
main "$@"
