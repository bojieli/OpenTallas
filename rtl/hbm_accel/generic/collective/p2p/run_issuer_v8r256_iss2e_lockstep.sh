#!/usr/bin/env bash
# HBM-TAPS 11-12 ISS2E (q3bc cycle form, DIE-HBM-100 ruling): proof set for ot_hgi_coll_issuer_m256v8e.
#   run_issuer_v8r256_iss2e_lockstep.sh OUT MODE [SEED] [PROGS]
# MODE pos: lock-step bench vs the unchanged ot_hgi_coll_issuer_m256v8 (EQ_CYCLE_SHIFTED: same uop (pc, iteration,
#   uop_d1) / done event sequence, sticky fault raised at most one event later); exit 0 on ISS2E_LOCKSTEP PASS.
# ISS2E_DEFS (env): extra defines, e.g. -DOT_COLL_ISS8E_BANK_RQREG (SF1 B); mutant rqreg_addr needs it.
# MODE reload|nofwd|swap|iss2e_rce|iss2e_nogate|iss2e_nofr|rqreg_addr: negative controls (OT_COLL_ISS8E_MUT_*, DUT only); exit 1
#   printing ISS2E_LOCKSTEP_MUTANT_REJECTED when the compare rejects the mutant, exit 0 + SURVIVED otherwise.
# MODE split: yosys miter, f_cs + f_fin == f_take for all inputs.  MODE formal[_nogate]: yosys k-induction of the split
#   invariant (formal_iss2e_prop.sv inserted before the first endmodule; macro outputs free); nogate = negative control.
# Tools: iverilog/vvp (bench), yosys (split/formal; e.g. inside openroad/orfs:asap7lock).
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=${HCOLL_ROOT:-$(cd "$HERE/../../../../.." && pwd)}
OUT=$(realpath -m "${1:?output directory}"); MODE=${2:-pos}; SEED=${3:-1}; PROGS=${4:-6}; mkdir -p "$OUT"
p=$ROOT/rtl/hbm_accel/generic/collective/p2p; M=$ROOT/physical/asap7_memory_macros
case $MODE in
 split) cd "$p"; yosys -q -l "$OUT/split.log" iss2e_split_eq.ys >/dev/null; grep -q 'SUCCESS' "$OUT/split.log" && echo "ISS2E_SPLIT_EQ PASS"; exit $?;;
 formal|formal_nogate)
  d=-DFORMAL; [ $MODE = formal_nogate ] && d="-DFORMAL -DOT_COLL_ISS8E_MUT_ISS2E_NOGATE"
  python3 -I - "$p/ot_hgi_coll_issuer_m256v8e.sv" "$p/formal_iss2e_prop.sv" "$OUT/issuer_iss2e_formal.sv" <<'PY'
import sys
s=open(sys.argv[1]).read(); i=s.index("endmodule"); open(sys.argv[3],"w").write(s[:i]+open(sys.argv[2]).read()+s[i:])
PY
  { echo "read_verilog -lib $M/ot_sram_1rw_256x64_m4_r2c2/ot_sram_1rw_256x64_m4_r2c2.v $M/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v"
    sed "s/-DFORMAL/$d/" "$p/formal_iss2e.ys"; } > "$OUT/$MODE.ys"; cd "$OUT"; yosys -q -l "$MODE.log" "$MODE.ys" >/dev/null 2>&1 || true
  if grep -q 'Induction step proven: SUCCESS' "$MODE.log"; then r=PROVEN; else r=NOT_PROVEN; fi
  echo "ISS2E_FORMAL $MODE $r"
  if { [ $MODE = formal ] && [ $r = PROVEN ]; } || { [ $MODE = formal_nogate ] && [ $r = NOT_PROVEN ]; }; then exit 0; fi; exit 1;;
esac
src=("$p/tb_hgi_coll_issuer_v8r256_iss2e_lockstep.sv" "$p/ot_hgi_coll_issuer_m256v8.sv" "$p/ot_hgi_coll_issuer_m256v8e.sv"
 "$M/ot_sram_1rw_256x64_m4_r2c2/ot_sram_1rw_256x64_m4_r2c2.v" "$M/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v")
sha256sum "${src[@]}" "$0" "$p/compare_iss2e_lockstep.py" > "$OUT/sources.sha256"
D=()
[ -n "${ISS2E_DEFS:-}" ] && D=($ISS2E_DEFS)   # e.g. ISS2E_DEFS=-DOT_COLL_ISS8E_BANK_RQREG
case $MODE in pos) ;; reload|nofwd|swap|iss2e_rce|iss2e_nogate|iss2e_nofr|rqreg_addr) D+=(-DOT_COLL_ISS8E_MUT_${MODE^^});;
 *) echo "unknown mode $MODE"; exit 2;; esac
iverilog -g2012 "${D[@]}" -o "$OUT/sim_$MODE" "${src[@]}"
vvp -n "$OUT/sim_$MODE" +seed=$SEED +progs=$PROGS +log_ref="$OUT/$MODE.ref.log" +log_dut="$OUT/$MODE.dut.log" > "$OUT/$MODE.log"
grep TB_DONE "$OUT/$MODE.log"
set +e; python3 -I "$p/compare_iss2e_lockstep.py" "$OUT/$MODE.ref.log" "$OUT/$MODE.dut.log" > "$OUT/$MODE.cmp"; rc=$?; set -e
tail -3 "$OUT/$MODE.cmp"; rm -f "$OUT/sim_$MODE"
if [ "$MODE" = pos ]; then [ $rc = 0 ] && echo "ISS2E_LOCKSTEP PASS seed$SEED progs$PROGS"; exit $rc; fi
if [ $rc != 0 ]; then echo "ISS2E_LOCKSTEP_MUTANT_REJECTED $MODE"; exit 1; fi
echo "ISS2E_LOCKSTEP_MUTANT_SURVIVED $MODE"; exit 0
