#!/usr/bin/env bash
# Lockstep bench (HBM-NATIVE 10-17): host_phy pin stages vs the closed dcfed59ab RTL. Usage: run_host_phy_pin_stage.sh OUT [mut] [seed]
# mut=1 builds OT_HOST_PHY_STAGE_MUT. Exit 0 iff HOST_PHY_PIN_STAGE PASS.
set -u
out=${1:-$(mktemp -d)}; mut=${2:-0}; seed=${3:-7}; mkdir -p "$out"; D=rtl/hbm_accel/host_static_20261015
X=(); [ "$mut" = 1 ] && X=(-DOT_HOST_PHY_STAGE_MUT)
iverilog -g2012 -DSEED=$seed "${X[@]}" -o "$out/hp$mut" $D/tb_host_phy_pin_stage.sv $D/ot_hbm_host_phy_adapt.sv $D/ref_hbm_host_phy_adapt_dcfed.sv > "$out/build$mut.log" 2>&1 || { echo BUILD FAIL; cat "$out/build$mut.log"; exit 2; }
r=$(vvp -n "$out/hp$mut" 2>&1 | grep -Ev '\$finish|^VCD' | tail -6); echo "MUT=$mut $r"
case "$r" in *"HOST_PHY_PIN_STAGE PASS"*) exit 0;; *) exit 1;; esac
