#!/bin/bash
# MU-TOK-KV 10-19: the KV-die attention step, 1 user and 4 users (mixed-user calendar), on the attention vehicle
# qwk_slice_attn cut from a KV die netlist (release die: the MU GEN, OT_KV_MU=1).  One Verilator 5.050 build of
# tb_qwk_slice_attn (slice_smoke.py + drive_qwk_slice_attn_mu.svh + kva_grp_map.svh + kva_ports.svh), then every run of
# the CASES file in parallel.  CASES: one line per run "name plusarg plusarg ..." (# comments allowed).
# usage: run_kv_attn_mu.sh SLICE_DIR WORK KSRC CASES
#   SLICE_DIR holds slice.json, <top>.f, kva_grp_map.svh (kv_attn_grp_map.py) and kva_ports.svh (kva_mu_ports.py).
set -u
SL=$(readlink -f "$1"); W=$(mkdir -p "$2" && readlink -f "$2"); KSRC=$3; CASES=$(readlink -f "$4")
H=$(cd "$(dirname "$0")" && pwd)
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
TOP=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['top'])" $SL/slice.json)
for f in kva_grp_map.svh kva_ports.svh; do [ -f $SL/$f ] || { echo "KVA_BUILD_FAIL missing $SL/$f"; exit 2; }; done
# MU-TOK-KV3: the bench never reaches inside a hier block: pvw_<p>.fault is read from the parent net on its port
python3 - "$SL/$TOP.sv" > $SL/kva_hier_refs.svh <<'PY' || exit 2
import re, sys
t = open(sys.argv[1]).read()
for p in (0, 1):
    m = re.search(r'\bpvw_%d\s*\((.*?)\);' % p, t, re.S)
    f = re.search(r'\.fault\(([^()]*)\)', m.group(1)) if m else None
    net = ('dut.' + f.group(1).strip()) if f and f.group(1).strip() else "1'b0"
    print('`define KVA_PW%d_F %s' % (p, net))
PY
python3 $H/slice_smoke.py $SL/slice.json --out $W/tb_$TOP.sv --src 'i_n_clk_hbm_.*=hck' || exit 2
MAC=$KSRC/physical/qkd_astk_strip/macros
verilator --version > $W/verilator.version
cp $CASES $W/cases.txt
O=$W/obj
# MU-TOK-KV2: KVA_HIER=REGEX verilates every slice master matching REGEX ONCE as a Verilator hierarchical block
# (hier_block in $W/hier.vlt; default the head-unit leaves, 7k of the vehicle's instances).  Verilator 5.050's _hier.mk
# runs a block twice under make -j (PCH race, HBM-TKM3), so the blocks are verilated serially and the C++ built -j.
VFILES="-f $SL/$TOP.f $MAC/ot_sram_1r1w_256x128_m1_r2c2/ot_sram_1r1w_256x128_m1_r2c2.v $MAC/ot_sram_1r1w_64x128_m1_r2c2/ot_sram_1r1w_64x128_m1_r2c2.v
    $KSRC/physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v $W/tb_$TOP.sv"
QKDEF=""; [ "${KVA_QK_ONLY:-0}" = 1 ] && QKDEF="+define+KVA_QK_ONLY"
VOPTS="$QKDEF -O1 ${KVA_VFLAGS:--fno-dfg} -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT -Wno-MULTIDRIVEN
    --x-assign unique --x-initial unique --top-module tb_$TOP -GMUT=0 -Mdir $O
    +define+SLICE_DRIVE=\"$H/drive_qwk_slice_attn_mu.svh\" +define+IDLE_EDGES=200 +define+TAIL_EDGES=50 +incdir+$H +incdir+$SL"
if [ ! -x $O/Vtb_$TOP ] || [ -n "${KVA_REBUILD:-}" ]; then
  if [ -n "${KVA_HIER:-}" ]; then
    python3 - "$SL/slice.json" "$KVA_HIER" > $W/hier.vlt <<'PY' || exit 2
import json, re, sys
m = sorted(x for x in json.load(open(sys.argv[1]))['masters'] if re.fullmatch(sys.argv[2], x))
if not m:
    raise SystemExit('KVA_HIER matches no slice master')
print('`verilator_config')
print('// MU-TOK-KV2: repeated leaves verilated once each (hierarchical blocks)')
for x in m:
    print(f'hier_block -module "{x}"')
PY
    echo "hier blocks: $(grep -c hier_block $W/hier.vlt)"
    export VOPTS VFILES O TOP W KJ=${KVA_J:-16}
    /usr/bin/time -f "%e s %M KB" -o $W/build.time bash -c 'verilator --cc --exe --main --timing --hierarchical -j $KJ $VOPTS \
        $W/hier.vlt $VFILES && make -C $O -f Vtb_${TOP}_hier.mk -j1 hier_verilation && make -C $O -f Vtb_${TOP}_hier.mk -j $KJ hier_build' > $W/build.log 2>&1
  else
    /usr/bin/time -f "%e s %M KB" -o $W/build.time verilator --binary --timing -j ${KVA_J:-32} $VOPTS $VFILES > $W/build.log 2>&1
  fi
fi
echo "build: $(cat $W/build.time 2>/dev/null)"
if [ ! -x $O/Vtb_$TOP ]; then echo "KVA_BUILD_FAIL $TOP (see $W/build.log)"; grep -m20 -E '%Error' $W/build.log; exit 3; fi
NAMES=()
while read -r n pa; do
    case "$n" in ''|\#*) continue;; esac
    NAMES+=("$n")
    ( /usr/bin/time -f "%e s %M KB" -o $W/run_$n.time $O/Vtb_$TOP +verilator+rand+reset+2 +verilator+seed+1 \
        +verilator+error+limit+1000000 $pa > $W/run_$n.log 2>&1; echo "exit $?" >> $W/run_$n.log ) &
done < $CASES
wait
for n in "${NAMES[@]}"; do
    echo "== $n: $(grep -hE 'SMOKE_(PASS|FAIL)' $W/run_$n.log | head -1) ($(cat $W/run_$n.time 2>/dev/null | tr '\n' ' '))"
    grep -hE '^KVA_(RESULT|DIE_ATTN|STEP_RESULT|FAULT first|ROW_ERR)|^SMOKE_ERR' $W/run_$n.log | head -24
done
