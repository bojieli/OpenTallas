#!/bin/bash
# hc128_subtree32_gen.sh OUT [SRC_COMMIT]  (HBM-CORES-RTL 2026-10-26)
# Repo-relative generator of the exact W128 HC qhub cut master ot_hbm_hc_subtree32_core (x4 per hub, 2x2 in the qhub
# slot).  Chain = the one the HC-native lane ran by hand on epyc1 codex-hbm-hc-native-1026/native_qhub (run.sh +
# export_drst_masters.sh), now from this checkout only:
#   1 elab   read_slang ot_hbm_hc_qhub_static #(W128 DRLY2 CHX11 RD_CAPTURE51 GATHER_PHASE51 DONE_LAT47), the qhub client
#            ot_hbm_hc_q_static black-boxed (subtree32/ot_hbm_hc_q_static_bb.v = its port list), fp32 adders kept
#   2 cut    hc128_qhub_cut.py -> yosys submod of four exact 32-input / 5-level adder subtrees (0 added/removed levels)
#   3 compact hc128_qhub_compact.py -> one reusable master (unread input bits dropped)
#   4 export hc128_export.py -> OUT/ot_hbm_hc_subtree32_core.sv + _receipt.json (plain instance identifiers, ruling 5)
# Sources are taken from git SRC_COMMIT (default HEAD) with `git show`, so OUT is a function of the commit alone.
# Needs ~/.local/opentallas-tools/bin/yosys (slang plugin); ~8 GB, ~5 min.  Committed output:
#   rtl/hbm_accel/cores_split/ot_hbm_hc_subtree32/ot_hbm_hc_subtree32_core.sv (+ _receipt.json)
set -euo pipefail
OUT=$(mkdir -p "$1" && cd "$1" && pwd); C=${2:-HEAD}
R=$(git -C "$(dirname "$0")" rev-parse --show-toplevel); SHA=$(git -C "$R" rev-parse --short=10 "$C")
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
mkdir -p "$OUT/src"
for f in rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_qcen_static.sv rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_qhub_static.sv \
         rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv \
         rtl/lib/ot_rst_relay.sv tools/hbm_b2/subtree32/ot_hbm_hc_q_static_bb.v; do
  git -C "$R" show "$C:$f" > "$OUT/src/$(basename $f)"
done
S=$OUT/src
cat > "$OUT/elab.ys" <<YS
read_slang --keep-hierarchy --compat=vcs --ignore-assertions --top ot_hbm_hc_qhub_static -G W=128 -G DRLY=2 -G CHX=11 -G RD_CAPTURE=51 -G GATHER_PHASE=51 -G DONE_LAT=47 $S/ot_hbm_hc_q_static_bb.v $S/ot_hbm_hc_qcen_static.sv $S/ot_hbm_hc_qhub_static.sv $S/ot_hdc_fastfp.sv $S/ot_hdc_fastfp_lat.sv $S/ot_hdc_fp32_add_lat.sv $S/ot_hdc_prefix.sv $S/ot_rst_relay.sv
setattr -mod -unset keep_hierarchy
setattr -set keep_hierarchy 1 t:ot_hdc_fp32_add_lat* t:ot_hbm_hc_qcen_static*
proc
flatten
memory -nomap
memory_map
opt_clean
write_json $OUT/qhub128.json
stat
YS
T=$R/tools/hbm_b2
yosys -Q -s "$OUT/elab.ys" > "$OUT/elab.log" 2>&1
python3 -I "$T/hc128_qhub_cut.py" --source-commit "$SHA" "$OUT/qhub128.json" --out "$OUT/cut" > "$OUT/cut.log" 2>&1
yosys -Q -s "$OUT/cut/cut.ys" > "$OUT/submod.log" 2>&1
python3 -I "$T/hc128_qhub_compact.py" "$OUT/cut/qhub_split128.json" --out "$OUT/compact" > "$OUT/compact.log" 2>&1
python3 -I "$T/hc128_export.py" --netlist "$OUT/compact/qhub_compact128.json" --master ot_hbm_hc_subtree32_core \
  --out "$OUT/master" --source-commit "$SHA" > "$OUT/export.log" 2>&1
rm -f "$OUT/qhub128.json" "$OUT/cut/qhub_split128.json" "$OUT/cut/qhub_split128.v"     # >300 MB intermediates
sha256sum "$OUT/master/ot_hbm_hc_subtree32_core.sv"
