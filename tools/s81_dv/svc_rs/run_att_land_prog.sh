#!/usr/bin/env bash
# LAND-BENCH-2 (OPUS-FIX-S81-SVC-R6, 11-21): programme-driven lock-step of the SRAM landing store (tb_svc_att_land_prog):
# f = dsdv_svc_att (flop form) vs m = -DOT_SVC_ATT_LAND_SRAM $MDEFS vs negative controls ml (landing macros read one
# cycle late: bench copy dsdv_svc_land_mem_late) and mq (m + OT_SVC_ATT_MEM_MACRO_MUT).  ROWX=0|1, seeds $SEEDS,
# extra plusargs $ARGS.  Run from the repo root:  run_att_land_prog.sh OUT_DIR    (exit 0 = every seed LAND_PROG_VERDICT PASS)
set -euo pipefail
O=$(realpath -m "$1"); SEEDS=${SEEDS:-"1 2"}; ARGS=${ARGS:-}; ROWX=${ROWX:-1}; MDEFS=${MDEFS:-}
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
source tools/s81_dv/svc_rs/rs_files.sh
mkdir -p "$O/src"
A=rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv
AR=rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_ar.sv
mk() {  # $1 suffix, $2 sed expression applied to the body, $3.. defines
  local s=$1 x=$2; shift 2; local f="$O/src/dsdv_svc_att_$s.sv"
  { for d in "$@"; do echo "\`define $d"; done
    sed -E -e "s/^module dsdv_svc_att #\(/module dsdv_svc_att_$s #(/" -e "$x" "$A"
    for d in "$@"; do echo "\`undef $d"; done; } > "$f"
  grep -q "^module dsdv_svc_att_$s " "$f" || { echo "rename failed $s"; exit 1; }
}
mk f  's/^$//'
mk m  's/^$//' OT_SVC_ATT_LAND_SRAM $MDEFS
mk ml 's/dsdv_svc_land_mem #\(/dsdv_svc_land_mem_late #(/' OT_SVC_ATT_LAND_SRAM $MDEFS
grep -q "dsdv_svc_land_mem_late #(" "$O/src/dsdv_svc_att_ml.sv" || { echo "ml: no land_mem instance to mutate"; exit 1; }
mk mq 's/^$//' OT_SVC_ATT_LAND_SRAM $MDEFS OT_SVC_ATT_MEM_MACRO OT_SVC_ATT_MEM_MACRO_MUT
# negative control: the landing store's read data one edge late (bench copy of dsdv_svc_land_mem)
python3 -I - "$AR" "$O/src/dsdv_svc_land_mem_late.sv" <<'PY'
import re, sys
s = open(sys.argv[1]).read()
m = re.search(r"^module dsdv_svc_land_mem #\(.*?^endmodule", s, re.S | re.M); assert m, "dsdv_svc_land_mem not found"
t = m.group(0).replace("module dsdv_svc_land_mem #(", "module dsdv_svc_land_mem_late #(", 1)
old = "        assign rd[256*r +: 256] ="
assert t.count(old) == 1
t = t.replace(old, "        assign rd_n[256*r +: 256] =")
t = t.replace("    for (genvar r = 0; r < 4; r = r + 1) begin : g_res",
              "    wire [1023:0] rd_n; reg [1023:0] rd_q = 0;\n    always @(posedge clk) rd_q <= rd_n;   // MUTANT: one edge late\n"
              "    assign rd = rd_q;\n    for (genvar r = 0; r < 4; r = r + 1) begin : g_res", 1)
assert "rd_q" in t
open(sys.argv[2], "w").write(t + "\n")
PY
SRC=(); for f in "${RS_SRC[@]}"; do [ "$f" = "$A" ] || [ "$f" = "$D/dsdv_svc_rs.sv" ] || SRC+=("$f"); done
SRC+=(rtl/hdc/v41x/ot_s81c_attn_hcore.sv rtl/hdc/v41x/ot_s81c_attn_hcore_h8.sv rtl/hdc/v41x/ot_s81c_attn_h8_rt2.sv)
M=physical/asap7_memory_macros_v2
if [ ! -x "$O/obj/Vtb_svc_att_land_prog" ]; then
  /usr/bin/time -v "$VL" --binary --top-module tb_svc_att_land_prog -Mdir "$O/obj" -j 16 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD \
    -Wno-MULTIDRIVEN --unroll-count 16 --unroll-limit 131072 -CFLAGS -O1 -I"$D" -DOT_SVC_ALLQ -DOT_SVC_H8 -DOT_SVC_H8_REUSE_RT2 \
    -DOT_ATTN_HCORE -DOT_S81C_HCORE_CTLA -DOT_S81C_HCORE_RST_TIMED -DSU_SMU_T -DOT_SVC_MEM_COV -GROWX=$ROWX \
    "${RS_DEF[@]}" "$O/src/dsdv_svc_att_f.sv" "$O/src/dsdv_svc_att_m.sv" "$O/src/dsdv_svc_att_ml.sv" "$O/src/dsdv_svc_att_mq.sv" \
    "$O/src/dsdv_svc_land_mem_late.sv" "$AR" rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_la.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_lr.sv \
    $M/ot_sram_1r1w_32x128_m1_r0c0/ot_sram_1r1w_32x128_m1_r0c0.v $M/ot_sram_1r1w_160x256_m1_r0c0/ot_sram_1r1w_160x256_m1_r0c0.v \
    "${SRC[@]}" "${RS_LIB[@]}" rtl/dsrom_sys/s81_dv/svc_rs/tb_svc_att_land_prog.sv > "$O/build.log" 2>&1 || { tail -30 "$O/build.log"; exit 1; }
fi
pids=(); for s in $SEEDS; do "$O/obj/Vtb_svc_att_land_prog" +seed=$s $ARGS > "$O/run_s$s.log" 2>&1 & pids+=("$!"); done
rc=0; for p in "${pids[@]}"; do wait "$p" || rc=1; done
for s in $SEEDS; do echo "== seed $s"
  grep -E "^LAND_|^FIRST_MISMATCH|^  |^PASS|^FAIL|^CAUGHT|^MISSED|^TIMEOUT" "$O/run_s$s.log" || true
  grep -q "^LAND_PROG_VERDICT PASS " "$O/run_s$s.log" || rc=1; done
exit "$rc"
