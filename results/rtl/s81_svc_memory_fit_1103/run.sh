#!/bin/bash
# MEM v2 fit gate: positive + 5 independent negative controls (each mutant must FAIL).
set -euo pipefail
ulimit -c 0
G=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$G/../../.." && pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
M=$ROOT/physical/asap7_memory_macros_v2
R=$ROOT/results/rtl
OLD="$R/s81_T7_LAND_bound_cut_1102/ot_t7_land_capture_candidate.sv $R/s81_T7_pmem_bound_cut_0900/ot_t7_pmem_capture_candidate.sv
     $R/s81_T7_pvq_bound_cut_1040/ot_t7_pvq_capture_candidate.sv $R/s81_T7_STAGE_macro_gate_1102/staging.sv"
MAC=""
for m in ot_sram_1r1w_256x256_m2_r2c2 ot_sram_1r1w_32x64_m1 ot_sram_1r1w_160x256_m1_r0c0 ot_sram_1r1w_256x256_m1_r0c0 \
         ot_sram_1r1w_160x265_m1_r0c0 ot_sram_1r1w_32x128_m1_r0c0; do MAC="$MAC $M/$m/$m.v"; done
NEW="ot_t7_land_capture_v2.sv ot_t7_pmem_capture_v2.sv ot_t7_pvq_capture_v2.sv ot_hdc_v41x_attn_staging_fit.sv"
W=${WORK:-$G/work}
rm -rf "$W"; mkdir -p "$W"
cd "$G"
sha256sum $OLD $MAC $NEW tb.sv run.sh > inputs.sha256
mk() {  # $1 = name, $2 = file, $3 = old text, $4 = new text
  mkdir -p "$W/$1"; for f in $NEW; do cp "$f" "$W/$1/"; done
  python3 -I - "$W/$1/$2" "$3" "$4" <<'EOF'
import sys
p, a, b = sys.argv[1:4]; s = open(p).read(); assert s.count(a) == 1, (p, a); open(p, "w").write(s.replace(a, b))
EOF
}
mkdir -p "$W/pos"; for f in $NEW; do cp "$f" "$W/pos/"; done
mk m1 ot_t7_land_capture_v2.sv 'assign mq[4*w+b] = mraw & {256{r_in_q}};' 'assign mq[4*w+b] = mraw;'
mk m2 ot_t7_land_capture_v2.sv "rbase[7:0] < 8'd160" "rbase[7:0] < 8'd159"
mk m3 ot_t7_pmem_capture_v2.sv 'bank==0?even_a:odd_a' 'bank==0?odd_a:odd_a'
mk m4 ot_t7_pvq_capture_v2.sv 'assign q[2*n+1]=qq[127:64];' 'assign q[2*n+1]=qq[63:0];'
mk m5 ot_hdc_v41x_attn_staging_fit.sv '.rd_out(rd_data[l*ROWW +: ROWW]),' '.rd_out(rd_data[(NL-1-l)*ROWW +: ROWW]),'
ok=1
for c in pos m1 m2 m3 m4 m5; do
  ( cd "$W/$c" && "$V" --binary --timing -O1 -j 2 --x-assign 0 --x-initial 0 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint \
      -Wno-style --top-module tb -Mdir obj $OLD $MAC $NEW "$G/tb.sv" > build.log 2>&1 )
  set +e; "$W/$c/obj/Vtb" > "$c.log" 2>&1; rc=$?; set -e
  if [[ $c == pos ]]; then { [[ $rc == 0 ]] && grep -q '^FIT_PASS ' pos.log; } || ok=0
  else { [[ $rc != 0 ]] && grep -q '^FIT_FAIL ' "$c.log"; } || ok=0; fi
  echo "$c rc=$rc $(grep -m1 '^FIT_' "$c.log")"
done
echo "GATE_OK=$ok"
[[ $ok == 1 ]]
