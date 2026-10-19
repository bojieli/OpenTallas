#!/bin/bash
# LAYERBENCH-QWEN G-K1: the KV die programme load (full authenticated HOST boot) on the cut boot vehicle.
# One Verilator 5.050 build of tb_<top> (tools/qwen_layerbench/slice_smoke.py + drive_qwk_slice_boot.svh), then:
#   asbuilt_s1/_s2  the AS-BUILT HOST loader, images IMG (two random initial states)
#   fix_s1/_s2      DIAGNOSTIC: HOST loader copy with target_words(10) = 77, images IMG (two random initial states)
#   fixalt_s1       DIAGNOSTIC: as fix_s1 with the image set IMG_ALT (another target-1 compile)
#   fixA_s1         DIAGNOSTIC: as fix_s1 with the literal HOST order (+KVB_ORDER_A: re-reset, then BEGIN target 1)
#   mut1..mut3      bench mutants on the DIAGNOSTIC loader (drive_qwk_slice_boot.svh header); each must FAIL
# usage: run_kv_boot.sh SLICE_DIR WORK KSRC IMG IMG_ALT
# QW-KVATTN 10-18: KVB_LD=<loader .sv> overrides the KSRC loader (e.g. the F-K1-fixed loader of claude/kv-hroot-1018);
#   KVB_ALT=77 (default): alternate copy = LD with target_words(10) 76 -> 77 (DIAGNOSTIC, the run list above);
#   KVB_ALT=76: LD is the FIXED loader; alternate copy = LD with 77 -> 76 (the OLD loader = mutant old76); runs:
#     asbuilt_s1/_s2 (must PASS), old76_s1 (must FAIL), mut1..mut3 on the as-built loader (must FAIL).
set -u
SL=$(readlink -f "$1"); W=$(mkdir -p "$2" && readlink -f "$2"); KSRC=$3; IMG=$(readlink -f "$4"); IMG_ALT=$(readlink -f "$5")
H=$(cd "$(dirname "$0")" && pwd)
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
TOP=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['top'])" $SL/slice.json)
python3 $H/slice_smoke.py $SL/slice.json --out $W/tb_$TOP.sv --src 'i_pad_por_n=por_n' --src 'i_n_clk_hbm_.*=hck@0.512' || exit 2
LD=${KVB_LD:-$KSRC/rtl/qwen_sys/host_20261013/qkd_host_program_loader_target.sv}; ALT=${KVB_ALT:-77}
SRAM=$KSRC/physical/asap7_memory_macros_v2/ot_sram_1rw_256x64_m4_r2c2/ot_sram_1rw_256x64_m4_r2c2.v
# alternate loader copy: the one ABI line changed (module renamed so both are in one build)
if [ "$ALT" = 76 ]; then FROM='10:target_words=77;'; TO='10:target_words=76;'; else FROM='10:target_words=76;'; TO='10:target_words=77;'; fi
sed -e 's/^module qkd_host_program_loader_target /module qkd_host_program_loader_target_alt /' \
    -e "s/$FROM/$TO/" $LD > $W/qkd_host_program_loader_target_alt.sv
[ "$(diff $LD $W/qkd_host_program_loader_target_alt.sv | grep -c '^>')" = 2 ] || { echo "loader copy: expected 2 changed lines"; exit 2; }
verilator --version > $W/verilator.version
O=$W/obj
if [ ! -x $O/Vtb_$TOP ] || [ -n "${KVB_REBUILD:-}" ]; then
/usr/bin/time -f "%e s %M KB" -o $W/build.time verilator --binary --timing -j ${KVB_J:-16} -O1 -Wno-fatal -Wno-lint -Wno-style \
    -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT -Wno-MULTIDRIVEN --x-assign unique --x-initial unique \
    --top-module tb_$TOP -GMUT=0 -Mdir $O +define+SLICE_DRIVE=\"$H/drive_qwk_slice_boot.svh\" +incdir+$H \
    -f $SL/$TOP.f $LD $W/qkd_host_program_loader_target_alt.sv $SRAM $W/tb_$TOP.sv > $W/build.log 2>&1
fi
echo "build: $(cat $W/build.time 2>/dev/null)"
if [ ! -x $O/Vtb_$TOP ]; then echo "KVB_BUILD_FAIL $TOP (see $W/build.log)"; grep -m20 -E '%Error' $W/build.log; exit 3; fi
run() { local n=$1 s=$2; shift 2; /usr/bin/time -f "%e s %M KB" -o $W/run_$n.time $O/Vtb_$TOP +verilator+rand+reset+2 +verilator+seed+$s +verilator+error+limit+1000000 "$@" > $W/run_$n.log 2>&1; echo "exit $?" >> $W/run_$n.log
    # %Error lines after the reset mark (KVB_TRACE_ON) fail the run; earlier ones = random pre-reset state (counted)
    python3 - $W/run_$n.log >> $W/run_$n.log <<'PY'
import re, sys
mark, pre, post = None, 0, []
for l in open(sys.argv[1]):
    m = re.match(r'KVB_TRACE_ON t=(\d+)', l)
    if m: mark = int(m.group(1))
    e = re.match(r'\[(\d+)\] %Error', l)
    if e:
        if mark is None or int(e.group(1)) < mark: pre += 1
        else: post.append(l.strip())
print(f'KVB_RTL_ASSERT pre_reset {pre} after_reset {len(post)}')
for l in post[:5]: print('KVB_RTL_ASSERT_AFTER_RESET ' + l)
PY
}
if [ "$ALT" = 76 ]; then
RUNS="asbuilt_s1 asbuilt_s2 old76_s1 mut1 mut2 mut3"
run asbuilt_s1 1 +KVIMG=$IMG & run asbuilt_s2 2 +KVIMG=$IMG &
run old76_s1 1 +KVIMG=$IMG +KVB_T10FIX +KVB_ALT_DESC=MUTANT_old76_pre_FK1_loader &
for m in 1 2 3; do run mut$m 1 +KVIMG=$IMG +KVB_MUT=$m & done
else
RUNS="asbuilt_s1 asbuilt_s2 fix_s1 fix_s2 fixalt_s1 fixA_s1 mut1 mut2 mut3"
run asbuilt_s1 1 +KVIMG=$IMG & run asbuilt_s2 2 +KVIMG=$IMG &
run fix_s1 1 +KVIMG=$IMG +KVB_T10FIX & run fix_s2 2 +KVIMG=$IMG +KVB_T10FIX &
run fixalt_s1 1 +KVIMG=$IMG_ALT +KVB_T10FIX & run fixA_s1 1 +KVIMG=$IMG +KVB_T10FIX +KVB_ORDER_A &
for m in 1 2 3; do run mut$m 1 +KVIMG=$IMG +KVB_T10FIX +KVB_MUT=$m & done
fi
wait
# reset completeness / determinism of the two initial states (as run_smoke.sh) + the boot event cycles
det() {
python3 - $W/run_$1.log $W/run_$2.log <<'PY'
import re, sys
def rd(f):
    out, ph, cyc = {}, 'idle', []
    for l in open(f):
        if l.startswith('SMOKE_FOLD programme'): ph = 'programme'
        m = re.match(r'SMOKE_OFOLD (\S+) (\S+) act (\d+)', l)
        if m: out[(ph if (ph, m.group(1)) not in out else 'programme', m.group(1))] = m.group(2)
        if l.startswith('KVB_CYCLES') or l.startswith('KVB_EVT'): cyc.append(l.strip())
    return out, cyc
(a, ca), (b, cb) = rd(sys.argv[1]), rd(sys.argv[2])
diff = sorted({p for k, p in a if a[(k, p)] != b.get((k, p))})
print(f'RESET_DET ports {len({p for _, p in a})} nondet {len(diff)} cycles_equal {ca == cb} events {len(ca)}')
for p in diff[:20]: print('  NONDET ' + p)
PY
}
for r in $RUNS; do
    v=$(grep -hE 'SMOKE_(PASS|FAIL)' $W/run_$r.log | head -1); grep -q 'KVB_RTL_ASSERT_AFTER_RESET' $W/run_$r.log && v="KVB_FAIL rtl assertion after reset; $v"
    echo "== $r: $v ($(cat $W/run_$r.time 2>/dev/null | tr '\n' ' '))"
    grep -hE 'KVB_(ERR|CYCLES|RTL_ASSERT)|SMOKE_ERR' $W/run_$r.log | head -8
done
echo "== determinism asbuilt: $(det asbuilt_s1 asbuilt_s2 | head -1)"
[ "$ALT" = 76 ] || echo "== determinism fix: $(det fix_s1 fix_s2 | tee $W/det_fix.txt | head -1)"
