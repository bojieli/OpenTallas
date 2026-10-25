#!/usr/bin/env bash
# S81-KITS-HROW 2026-10-24: cycle-exact equivalence of dsdv_svc_sx_hrow (registered decoded selects) against a reference
# hrow source (default: the file at REF_REV, the last form that decoded role at every mux).  All 16 sids x 2 halves,
# random ports every cycle, mid-run reset; every output bit compared every cycle.
# Usage (repo root): tools/s81_dv/svc_rs/hrow_eq_bench.sh OUTDIR [base|mut1|mut2|mut3|selmut] [seed...]
#   REF_SV=<file> overrides the reference source; NEW_SV=<file> the candidate (default: the working-tree file).
set -euo pipefail
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=$1; V=${2:-base}; shift 2 || true; SEEDS=${*:-1 2}
D=rtl/dsrom_sys/s81_dv/svc_rs
REF_REV=${REF_REV:-d13ff7c78}
NEW_SV=${NEW_SV:-$D/dsdv_svc_sx_hrow.sv}
mkdir -p "$O/$V"
if [ -n "${REF_SV:-}" ]; then cp "$REF_SV" "$O/$V/ref_in.sv"; else git show "$REF_REV:$D/dsdv_svc_sx_hrow.sv" > "$O/$V/ref_in.sv"; fi
sed 's/^module dsdv_svc_sx_hrow #(/module dsdv_svc_sx_hrow_ref #(/' "$O/$V/ref_in.sv" > "$O/$V/hrow_ref.sv"
grep -q '^module dsdv_svc_sx_hrow_ref' "$O/$V/hrow_ref.sv"
DEF=()
case "$V" in
  base) ;; mut1) DEF=(-DMUT=1);; mut2) DEF=(-DMUT=2);; mut3) DEF=(-DMUT=3);;
  selmut) DEF=(-DOT_HROW_SEL_MUT);;   # negative control: one replicated select copy decodes wrong -> must FAIL
  *) echo "variant?" >&2; exit 2;;
esac
"$VL" --binary --top-module tb_dsdv_svc_sx_hrow_eq -Mdir "$O/$V/obj" -j 16 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD \
  --x-initial 0 --x-assign 0 -I$D "${DEF[@]}" rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv \
  rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv \
  "$O/$V/hrow_ref.sv" "$NEW_SV" $D/test/tb_dsdv_svc_sx_hrow_eq.sv > "$O/$V/build.log" 2>&1 || { tail -30 "$O/$V/build.log"; exit 1; }
for s in $SEEDS; do "$O/$V/obj/Vtb_dsdv_svc_sx_hrow_eq" +seed=$s > "$O/$V/run_s$s.log" 2>&1 || true
  echo "$V seed $s: $(grep -E '^HROW_EQ' "$O/$V/run_s$s.log" | tr '\n' ' ')"; done
