#!/bin/bash
# hc128_pair_gen.sh PROFILE OUT [SRC_COMMIT]   (DIE-HBM-54 2026-10-31)
# Repo-relative generator of the exact native W128 HC bank pair masters (8 per bank, 250.56 x 267.84):
#   PROFILE plain -> ot_hbm_hc_bank128_pair_core        (ot_hbm_hc_bankq_static  #(W128 CPI1 CPO1), 14 banks x 8 pairs)
#   PROFILE first -> ot_hbm_hc_bank128_pair_first_core  (ot_hbm_hc_bankq0_static #(W128 DRLY2 CPO1), 2 banks x 8 pairs)
# Chain = the one the HC-native lane ran by hand on the retired epyc1 (codex-hbm-hc-native-1026 native_{plain,first} +
# export_drst_masters; masters_drst), the same shape as hc128_subtree32_gen.sh, from this checkout only:
#   1 elab    read_slang the bank tile top, HC lane leaves ot_hdc_v41x_hcp_lanes kept, SRAMs = blackbox macro views
#   2 split   hc128_split_capture.py: wide wdat/xdat capture $dff split at the exact pair boundary (same D/Q bits)
#   3 cut     hc128_physical_cut.py -> yosys submod of 8 pair tiles (2 lane leaves + 2 weight + 1 x SRAM + 768 capture bits)
#   4 compact hc128_pair_compact.py -> one reusable master (unread input bits dropped)
#   5 export  hc128_export.py -> OUT/master/<master>.sv + _receipt.json (plain instance identifiers, ruling 5)
# Sources are taken from git SRC_COMMIT (default HEAD) with `git show`, so OUT is a function of the commit alone.
# Needs ~/.local/opentallas-tools/bin/yosys (slang plugin).  Zero added cycles: a pure cut of the elaborated tile.
set -euo pipefail
P=$1; OUT=$(mkdir -p "$2" && cd "$2" && pwd); C=${3:-HEAD}
R=$(git -C "$(dirname "$0")" rev-parse --show-toplevel); SHA=$(git -C "$R" rev-parse --short=10 "$C")
case $P in
  plain) TOP=ot_hbm_hc_bankq_static;  G="-G W=128 -G CPI=1 -G CPO=1";  M=ot_hbm_hc_bank128_pair_core;;
  first) TOP=ot_hbm_hc_bankq0_static; G="-G W=128 -G DRLY=2 -G CPO=1"; M=ot_hbm_hc_bank128_pair_first_core;;
  *) echo "profile plain|first" >&2; exit 2;;
esac
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
mkdir -p "$OUT/src"; S=$OUT/src; FILES=""
for f in rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_bankq_static.sv rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_bank_static.sv \
         rtl/hdc/v41x/ot_hdc_v41x_hcp.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv \
         rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/lib/ot_rst_relay.sv \
         physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v \
         physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v; do
  git -C "$R" show "$C:$f" > "$S/$(basename $f)"; FILES="$FILES $S/$(basename $f)"
done
cat > "$OUT/elab.ys" <<YS
read_slang --keep-hierarchy --compat=vcs --ignore-assertions --top $TOP $G $FILES
setattr -mod -unset keep_hierarchy
setattr -set keep_hierarchy 1 t:ot_hdc_v41x_hcp_lanes*
proc
flatten
memory -nomap
memory_map
opt_clean
write_json $OUT/native128.json
stat
YS
T=$R/tools/hbm_b2
yosys -Q -s "$OUT/elab.ys" > "$OUT/elab.log" 2>&1
python3 -I "$T/hc128_split_capture.py" "$OUT/native128.json" --top $TOP --out "$OUT/split_in.json" > "$OUT/split.log" 2>&1
python3 -I "$T/hc128_physical_cut.py" --source-commit "$SHA" "$OUT/split_in.json" --top $TOP --out "$OUT/cut" > "$OUT/cut.log" 2>&1
yosys -Q -s "$OUT/cut/cut.ys" > "$OUT/submod.log" 2>&1
python3 -I "$T/hc128_pair_compact.py" "$OUT/cut/split128.json" --top $TOP --master $M --out "$OUT/compact" > "$OUT/compact.log" 2>&1
python3 -I "$T/hc128_export.py" --netlist "$OUT/compact/compact128.json" --master $M \
  --blackbox ot_sram_1r1w_1024x256_m2_r2c2 --blackbox ot_sram_1r1w_128x256_m1_r2c2 \
  --out "$OUT/master" --source-commit "$SHA" > "$OUT/export.log" 2>&1
rm -f "$OUT/split_in.json" "$OUT/cut/split128.json" "$OUT/cut/split128.v"     # large intermediates (native128.json kept for the miter)
sha256sum "$OUT/master/$M.sv"
