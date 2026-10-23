#!/bin/bash
# frame_seam_bench.sh <outroot> [M=h9|h10] (cwd = repo root; run on the FLEET via ot-run, ~6 GB / ~12 min per build):
# S81-P7 10-23 -- FRAMED-TRAFFIC seam bench for the banded frame with plan-width seams (vgcs twin,
# rtl/dsrom_sys/s81_dv/frame_lp/vgcs/col_<M>_l4_lp_rf3r.sv).  The per-element frame bench (SET=each) and the random-x
# lockstep (tb_col_*_l4_lp) are blind to seam timing (S81-P6 13:32): +1 edge on the 536-b seams, a seam-wide 1-edge-early
# seam and the landing mutants all PASS there.  This bench drives the frame as the die does: SET=plan (all 12 q elements
# in one K-split phase, x streamed per beat, rows placed by the frame return legaliser on the source-pinned landed
# schedule results/arch/s81_dv_1016/frame_l4_cluster/compiler/col_<M>_schedule.json), and requires every ret word to equal
# the compiler's calendar (edge, tag, value) exactly plus every xo word.  Mutants (each must FAIL):
#   late<N>  : one 536-b band seam (x chain) re-timed +1 edge (u_lpl_<N>_r K 2 -> 3); h9 N = 9, 13; h10 N = 17, 32
#   short    : every seam 1 edge early (ot_pl_seam_r without its flop-last register; SEAM_SV mutant)
#   unland   : LP_MUT 1, the r1->r0 return seam bypassed (twin MUT == 1)
#   landread : LP_MUT 2, the r1->r0 return seam +1 edge (twin MUT == 2)
#   reset    : LP_MUT 4, one reset-forest leaf 400 edges late (twin MUT == 4)
# TWIN = the frame RTL under test (default the vgcs twin; the plan contents bench twin: frame_band_plan.py --bench-top).
# SEAM_REF (always on): tools/s81_dv/frame_seam_ref.py adds the vgch reference twin and compares every seam output every
# edge from SEAM_T0 (default 0) -- the ret calendar alone missed the x-seam mutants (x lands with slack before go).
# Env: MUTS (default: base + all), J (build jobs), PAR (parallel builds, default 1), BFVEC (BF phase vector dir: also run
# the BF framed traffic on each build -- required to exercise the 536-b x2 payload seams).  Exit 0 = base PASS and every mutant FAIL.
set -u
O=$1; M=${2:-h9}; MASTER=col_$M; mkdir -p $O
TW=${TWIN:-rtl/dsrom_sys/s81_dv/frame_lp/vgcs/${MASTER}_l4_lp_rf3r.sv}
case $M in h9) LATE="9 13";; h10) LATE="17 32";; *) echo "unknown M=$M"; exit 3;; esac
ALL="base"; for n in $LATE; do ALL="$ALL late$n"; done; ALL="$ALL short unland landread reset"
MUTS=${MUTS:-$ALL}
run_one() {   # $1 = mutant name
  local mu=$1 od=$O/$1 lmut=0 lpsv=$TW seam=rtl/common/landed_parent/ot_pl_seam.sv
  mkdir -p $od
  case $mu in
    base) ;;
    late*) n=${mu#late}; lpsv=$od/${MASTER}_l4_lp_rf3r.sv
           sed -E "/ u_lpl_${n}_r /s/\.K\(2\)/.K(3)/" $TW > $lpsv
           [ $(diff $TW $lpsv | grep -c '^>') = 1 ] || { echo "$mu: MUTANT_EMIT_FAILED"; return 3; } ;;
    short) seam=$od/ot_pl_seam_short.sv
           python3 - rtl/common/landed_parent/ot_pl_seam.sv $seam <<'PY' || { echo "$mu: MUTANT_EMIT_FAILED"; return 3; }
import re, sys
s = open(sys.argv[1]).read(); n = 0
for mod, early in (('ot_pl_seam_r', 'pad[CK-2]'), ('ot_pl_seam_r_pl', 'pk')):
    m = re.search(r'module %s #.*?endmodule' % mod, s, re.S)
    if not m: continue
    b = m.group(0).replace("assign o[c*CHUNK_BITS +: CW] = oq;", "assign o[c*CHUNK_BITS +: CW] = warm ? %s : {CW{1'b0}};" % early)
    n += b != m.group(0); s = s[:m.start()] + b + s[m.end():]
assert n >= 1; open(sys.argv[2], 'w').write(s)
PY
           ;;
    unland|landread|reset) lmut=$mu ;;
    *) echo "unknown mutant $mu"; return 3 ;;
  esac
  # seam observer (SEAM_REF): the vgch reference twin on the same traffic, every seam output compared every edge
  python3 tools/s81_dv/frame_seam_ref.py --master $MASTER --dut $lpsv --ref rtl/dsrom_sys/s81_dv/frame_lp/vgch/${MASTER}_l4_lp_rf3r.sv \
    --out-ref $od/ref_twin.sv --out-svh $od/seam_ref.svh --t0 ${SEAM_T0:-0} > $od/seam_ref.log 2>&1 || { echo "$mu: SEAM_REF_FAILED"; return 3; }
  FRAME_LP=1 SET=plan FRAME_LP_SV=$lpsv SEAM_SV=$seam LK=2 VFLAGS="-DSEAM_REF +incdir+$od $od/ref_twin.sv" \
    bash tools/s81_dv/frame_bench.sh $od $MASTER $lmut > $od/frame_bench.log 2>&1
  local line; line=$(grep -m1 '^FRAME_SET' $od/frame_bench.log)
  local chk; chk=$(grep -h -m2 -E 'PLAN_MISMATCH|MISMATCH|FAULT|COVERAGE|BAD_' $od/check_plan.log 2>/dev/null | head -2 | cut -c1-200 | tr '\n' ' ')
  local nsm; nsm=$(grep -c 'SEAM_MISMATCH' $od/run_plan.log 2>/dev/null); chk="seam_mismatch_lines=${nsm:-0} $chk"
  # BF framed traffic (BFVEC: an xs_place.py gen BF phase vector dir, e.g. attn.wo_a phase 65 of this master's frame): the
  # 536-b x2 payload seams (h9 9/13, h10 17/32) only carry data in BF phases -- the q-only plan set leaves them at 0
  # toggles (SEAM_ACT).  Same build; caught = seam mismatches or a frame FAULT (the BF programme check faults on a late word)
  local bf=""
  if [ -n "${BFVEC:-}" ] && [ -x $od/obj/Vtb_s81dv_frame ]; then
    $od/obj/Vtb_s81dv_frame $(sed "s#+OT_ROM_DIR=[^ ]*#+OT_ROM_DIR=$(realpath $BFVEC)#" $BFVEC/ARGS) > $od/run_bf.log 2>&1
    local bsm bft bact; bsm=$(grep -c 'SEAM_MISMATCH' $od/run_bf.log); bft=$(grep -m1 '^END' $od/run_bf.log | sed -E 's/.* fault=([0-9]+).*/\1/')
    bact=$(grep -E 'SEAM_ACT' $od/run_bf.log | awk '$4 > 0' | wc -l)
    bf="bf_seam_mismatch_lines=$bsm bf_fault=${bft:-NA} bf_active_seams=$bact"
  fi
  echo "SEAM_BENCH $M $mu: ${line:-NO_RESULT $(tail -n 2 $od/frame_bench.log | tr '\n' ' ')} ${chk} ${bf}"
}
export -f run_one 2>/dev/null
for mu in $MUTS; do
  if [ "${PAR:-1}" -gt 1 ]; then run_one $mu > $O/$mu.res & while [ $(jobs -rp | wc -l) -ge ${PAR} ]; do wait -n; done
  else run_one $mu > $O/$mu.res; fi
done
wait
rc=0
for mu in $MUTS; do
  r=$(cat $O/$mu.res); echo "$r"
  if [ $mu = base ]; then echo "$r" | grep -q 'pass=1 fail=0 seam_mismatch_lines=0' || rc=1
    [ -z "${BFVEC:-}" ] || echo "$r" | grep -q 'bf_seam_mismatch_lines=0 bf_fault=0' || rc=1
  else echo "$r" | grep -qE 'fail=1|bf_seam_mismatch_lines=[1-9]|bf_fault=[1-9]' || rc=1; fi
done
echo "SEAM_BENCH_EXIT $M $rc"; exit $rc
