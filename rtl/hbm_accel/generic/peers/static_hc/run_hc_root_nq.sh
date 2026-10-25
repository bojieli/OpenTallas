#!/usr/bin/env bash
# HBM-BIND B2 (2026-10-24): HC root NQ gate (tb_hbm_hc_root_nq, Verilator 5.050, root-only: ~1-2 GB, a few min / build).
#   NQ 4 (default) vs the unchanged base root, NQ 2 (B2 2-half, TPRE 7) vs the base root fed with the 4 quarter sums:
#   MUT 0 MUTB 0 must PASS; MUTB 1 / 2 (/ 3 at NQ 2) and MUT 2 must FAIL.
#   run_hc_root_nq.sh OUT [BASE=origin/claude/hbm-bind-1024r]   (HC_ROOT_REF_SV=<base root file> instead of git show)
# Programme: tools/rtl_hbm_hc_eng_static_gate.py --split --npos 2 --rs 104 --raw0 178 + XRU_R (REF SYS_LAT 146 + XRU_R:
# raw arrival = SYS_LAT + 32, as the eng4 ring's 176 at SYS_LAT 144); the DUT programme = the same words with every
# ingest slot ingq >> 1 and emit qmask 0x3 (NQ 2 only).
set -uo pipefail
out=$(realpath -m "${1:?out}"); base=${2:-origin/claude/hbm-bind-1024r}; mkdir -p "$out"
d=$(cd "$(dirname "$0")" && pwd); root=$(cd "$d/../../../../.." && pwd); cd "$root"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
H=rtl/hbm_accel/generic/peers/static_hc; rel=$H/ot_hbm_hc_root_static.sv
if [ -n "${HC_ROOT_REF_SV:-}" ]; then cp "$HC_ROOT_REF_SV" "$out/ref_raw.sv"; else git -C "$d" show "$base:$rel" > "$out/ref_raw.sv" || { echo "no base"; exit 2; }; fi
sed -E 's/\bot_hbm_hc_root_static\b/ot_hbm_hc_root_static_ref/g' "$out/ref_raw.sv" > "$out/ref.sv"
src=($H/tb_hbm_hc_root_nq.sv $rel "$out/ref.sv" $H/ot_hbm_hc_eng_seq_static.sv $H/ot_hbm_hc_tail_unit_static.sv
 $H/ot_hdc_v41x_hcp_sys1_static.sv $H/ot_hgi_hc_tail_static.sv
 rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv rtl/hdc/v41x/ot_hdc_v41x_hcp.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41/ot_hdc_fdiv.sv
 rtl/hdc/v41/ot_hdc_sinkhorn.sv rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv rtl/lib/ot_rst_relay.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
fail=0
for nq in 4 2; do
 xru=$([ $nq = 2 ] && echo 4 || echo 0); raw0=$((178 + xru)); case_d="$out/case$nq"; mkdir -p "$case_d"
 python3 tools/rtl_hbm_hc_eng_static_gate.py --run "$case_d" --split --npos 2 --raw0 $raw0 --rs 104 > "$case_d/vectors.log" || { echo "VECTORS_FAIL"; exit 2; }
 python3 - "$case_d" $nq <<'EOF'
import sys, pathlib
d = pathlib.Path(sys.argv[1]); nq = int(sys.argv[2])
out = []
for ln in (d / 'prog.mem').read_text().split():
    v = int(ln, 16)
    if nq == 2:
        if (v >> 20) & 1:                       # ingest: slot = quarter >> 1
            q = (v >> 21) & 3; v = (v & ~(3 << 21)) | ((q >> 1) << 21)
        if (v >> 118) & 1:                      # emit: both B2 clients
            v = (v & ~(0xf << 119)) | (0x3 << 119)
    out.append('%064x' % v)
(d / 'prog_dut.mem').write_text('\n'.join(out) + '\n')
EOF
 cfgs=("0 0" "0 1" "0 2" "2 0"); [ $nq = 2 ] && cfgs+=("0 3")
 for c in "${cfgs[@]}"; do
  set -- $c; m=$1; mb=$2; tag=nq${nq}_m${m}_b${mb}; rm -rf "$out/obj_$tag"
  "$vl" --binary --timing -j "${HC_BUILD_JOBS:-16}" -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_hbm_hc_root_nq \
   -GNQ=$nq -GMUT=$m -GMUTB=$mb +define+OT_FP_DATA_NORST -Mdir "$out/obj_$tag" -o Vt "${src[@]}" > "$out/build_$tag.log" 2>&1 \
   || { echo "BUILD_FAIL $tag"; tail -30 "$out/build_$tag.log"; exit 2; }
  rd="$out/run_$tag"; mkdir -p "$rd"; cp "$case_d"/{prog.mem,tbl.mem,plus.txt} "$rd/"
  if [ $mb = 3 ]; then cp "$case_d/prog.mem" "$rd/prog_dut.mem"; else cp "$case_d/prog_dut.mem" "$rd/"; fi
  (cd "$rd" && "$out/obj_$tag/Vt" $(cat plus.txt)) > "$out/run_$tag.log" 2>&1
  v=$(grep -E '^HC_ROOT_NQ' "$out/run_$tag.log" || echo "NO_VERDICT $(tail -2 "$out/run_$tag.log" | tr '\n' ' ')"); echo "NQ=$nq MUT=$m MUTB=$mb $v"
  if [ $m = 0 ] && [ $mb = 0 ]; then echo "$v" | grep -q ' PASS ' || fail=1; else echo "$v" | grep -Eq ' FAIL checks=[0-9]+ errors=[1-9]' || fail=1; fi
  rm -rf "$out/obj_$tag"
 done
done
[ $fail = 0 ] && echo "HC_ROOT_NQ_GATE PASS" || { echo "HC_ROOT_NQ_GATE FAIL"; exit 1; }
