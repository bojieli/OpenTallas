#!/usr/bin/env bash
# usage: run_host_cfg_leaf.sh OUT [MUT] [SEED] [D4G] [MUTQ] [PLAST]   lockstep of the d4g host config leaves (ot_hbm_host_cfg_leaf) vs d4f direct
# MUT 1 dropped cfg_data bit, 2 copy one stage short, 3 ready bits swapped, 4 fault bit dropped. Prints the PASS/FAIL line.
# D4G 1 = the d4g per-quadrant masters ot_hbm_host_cfg_leaf_{sw,se,nw,ne}; D4G 2 = SE/NE re-hardened ot_hbm_host_cfg_leaf_{se,ne}2 (NT21/NF30, NT17/NF27; MUT 5/6 top status bit inverted, 7 new fault slot dropped); PLAST 1 = poison the last target of the quadrant; MUTQ = the one leaf (0 SW 1 SE 2 NW 3 NE) given MUT (-1 all).
set -uo pipefail
cd "$(dirname "$0")/../../.."
out=${1:?out}; mut=${2:-0}; seed=${3:-7}; d4g=${4:-0}; mutq=${5:--1}; plast=${6:-0}; mkdir -p "$out"
D=rtl/hbm_accel/host_static_20261015
iverilog -g2012 -Ptb_hbm_host_cfg_leaf_lockstep.MUT=$mut -Ptb_hbm_host_cfg_leaf_lockstep.SEED=$seed -Ptb_hbm_host_cfg_leaf_lockstep.D4G=$d4g -Ptb_hbm_host_cfg_leaf_lockstep.MUTQ=$mutq -Ptb_hbm_host_cfg_leaf_lockstep.PLAST=$plast \
 -s tb_hbm_host_cfg_leaf_lockstep -o "$out/sim" \
 $D/tb_hbm_host_cfg_leaf_lockstep.sv $D/ot_hbm_host_cfg_leaf.sv $D/ot_hbm_host_cfg_leaf_r2.sv $D/ot_hbm_host_static_ingress.sv $D/ot_hbm_status_join_fa.sv \
 $D/ot_hbm_status_join.sv rtl/lib/ot_rst_relay.sv > "$out/build.log" 2>&1 \
 || { echo "HOST_CFG_LEAF_LOCKSTEP_FAIL build"; cat "$out/build.log"; exit 1; }
vvp -n "$out/sim" > "$out/run.log" 2>&1
r=$(grep -E 'HOST_CFG_LEAF_LOCKSTEP_(PASS|FAIL)' "$out/run.log" | tail -1); echo "$r"
case "$r" in *PASS*) exit 0;; *) exit 1;; esac
