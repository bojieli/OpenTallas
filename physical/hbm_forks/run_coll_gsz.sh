#!/bin/bash
# hbm-forks 2026-10-09 (review-0412 S4): collective group sizes {1, 2, 4, 8} + 96 on ot_hbm_accel_tu_endpoint_psg.
#   CF-1 (DS, gsz = 4'hF): the hbm-coll-rtl ps bench set (ar p1 / p6, gathers, die-view shapes, SAMECOL) on the fork
#        in legacy mode: every delivered word = the golden fixtures (tools/dshbm_1m_coll.py);
#   groups n = 2, 4, 8 (gsz 1, 2, 3; NC 8 hardware): all-reduce fixtures of n contributors (tools/ha2_ar_fixture.py,
#        hdc_golden pairwise tree in rank order + to_bf16), every rank, 2 seeds: PASS;
#   mutant OT_COLL_MUT_GSZ_PAD (inactive columns feed stale slots instead of +0) at n = 2 / 4: must FAIL.
#   run_coll_gsz.sh <out dir>   (from the source root)
set -u
mkdir -p $1; O=$(readlink -f $1); T=$O/t; rm -rf $T; mkdir -p $T/b
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=$(command -v verilator)
python3 tools/dshbm_1m_coll.py fixtures $T > $T/fx.log 2>&1 || { echo "COLL_GSZ ERROR fixtures"; exit 3; }
python3 - $T <<'PY' || { echo "COLL_GSZ ERROR group fixtures"; exit 3; }
import sys; from pathlib import Path
sys.path.insert(0, 'tools'); import ha2_ar_fixture as HF
import numpy as np, hdc_golden as G
_b = HF.build
def nb(shape, seed):                    # + -0 contributors (review-0427 HF-5): every contributor -0 on lanes 224..239,
    s, parts, zr = _b(shape, seed)      # even contributors -0 / odd +0 on 240..255; golden recomputed (canonical +0)
    nc, nog = s['NC'], s['NOG']
    parts[:, 224:240] = np.float32(-0.0)
    parts[0::2, 240:256] = np.float32(-0.0); parts[1::2, 240:256] = np.float32(0.0)
    for og in range(nog):
        q = [parts[og * nc + j].copy() for j in range(nc)]
        while len(q) > 1:
            q = [G.add(q[i], q[i + 1]) for i in range(0, len(q), 2)]
        zr[og] = G.to_bf16(q[0]) if s['BF16'] else q[0]
    return s, parts, zr
import os
if os.environ.get('NEGZ', '1') == '1':
    HF.build = nb
for n in (1, 2, 4, 8):
    HF.SHAPES[f'g{n}'] = dict(GS=n, NG=max(1, 8 // n), NC=n, NOG=8 // n, E=256, LANES=16, ONESHOT=0, BF16=1)
    HF.build = _b if n == 1 else (nb if os.environ.get('NEGZ', '1') == '1' else _b)
    HF.write(Path(sys.argv[1]) / 'fx' / f'g{n}', f'g{n}', 20261009 + n)
PY
M=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
SRC="rtl/link/ot_link_afifo.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv $M rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv rtl/hbm_accel/tu/ot_hcoll_port.sv rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_psg.sv rtl/hbm_accel/tu/tb_hbm_accel_tu_endpoint.sv"
D="+define+TU_DUT=ot_hbm_accel_tu_endpoint_psg"; CK="+define+TU_PCLK_IS_CLK -GT_PHY=0.833333"
build() { n=$1; shift; $V --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --x-assign fast --x-initial fast \
  --top-module tb_hbm_accel_tu_endpoint --Mdir $T/b/$n $D "$@" $SRC > $T/build_$n.log 2>&1 || echo "BUILD_FAIL $n"; }
AR="+define+TU_NC=8 +define+TU_NOG=8 +define+TU_BF16=1 +define+TU_GSZPORT=15"; GA="+define+TU_NC=1 +define+TU_NOG=96 +define+TU_BF16=0 +define+TU_GSZPORT=15"
build ar $AR +define+TU_PFMAX=384 $CK; build ga $GA +define+TU_PFMAX=384 $CK; build arblk $AR +define+TU_PFMAX=64 $CK;
for n in 1 2 4 8; do l=$(python3 -c "print({1:0,2:1,4:2,8:3}[$n])")
  build g$n +define+TU_NC=$n +define+TU_NOG=$((8 / n)) +define+TU_BF16=1 +define+TU_GSZ +define+TU_REDUCE +define+TU_GSZPORT=$l +define+TU_PFMAX=64 $CK;
done
for n in 2 4; do l=$(python3 -c "print({2:1,4:2}[$n])")
  build m$n +define+TU_NC=$n +define+TU_NOG=$((8 / n)) +define+TU_BF16=1 +define+TU_GSZ +define+TU_REDUCE +define+TU_GSZPORT=$l +define+TU_PFMAX=64 $CK +define+OT_COLL_MUT_GSZ_PAD;
done
build leak +define+TU_NC=2 +define+TU_NOG=4 +define+TU_BF16=1 +define+TU_GSZ +define+TU_REDUCE +define+TU_GSZPORT=1 +define+TU_PFMAX=64 $CK +define+OT_COLL_MUT_GROUP_ISOLATION
wait
J=$T/jobs.txt; : > $J
for r in 0 13 63; do echo "ar pos +VEC=fx/ar_p1 +PF=64 +RANK=$r +SEED=1" >> $J; done
echo "ar pos +VEC=fx/ar_p6 +PF=384 +RANK=3 +SEED=1 +SAMECOL=1" >> $J
for pf in 1 64; do for r in 0 95; do echo "ga pos +VEC=fx/gather_pf$pf +PF=$pf +RANK=$r +SEED=1" >> $J; done; done
for r in 0 62; do echo "arblk pos +VEC=fx/ar_p1 +PF=64 +RANK=$r +SEED=1" >> $J; done
for n in 1 2 4 8; do for r in $(seq 0 7); do for s in 1 2; do echo "g$n pos +VEC=fx/g$n +PF=16 +RANK=$r +SEED=$s" >> $J; done; done; done
for n in 2 4; do for r in 0 1; do echo "m$n neg +VEC=fx/g$n +PF=16 +RANK=$r +SEED=1" >> $J; done; done
for r in 0 3 7;do echo "leak neg +VEC=fx/g2 +PF=16 +RANK=$r +SEED=1" >> $J;done
i=0; while read b kind args; do i=$((i+1)); echo "cd $T && b/$b/Vtb_hbm_accel_tu_endpoint $args > run_$i.log 2>&1; echo \"$b $kind $args\" >> run_$i.log"; done < $J > $T/cmds.txt
xargs -P ${PAR:-16} -I{} bash -c '{}' < $T/cmds.txt
bad=0; negok=0; neg=0
for f in $T/run_*.log; do k=$(tail -n 1 $f | cut -d' ' -f2)
  if grep -q "TUDONE .* mismatches=0 faults=0 " $f; then [ $k = neg ] && { echo "MUTANT PASSED: $(tail -n 1 $f)"; bad=$((bad+1)); }
  else [ $k = neg ] && negok=$((negok+1)) || { bad=$((bad+1)); echo "FAILED: $(tail -n 1 $f): $(grep -h 'TUDONE\|TUTIMEOUT\|TUMISMATCH' $f | head -2)"; }; fi
  [ $k = neg ] && neg=$((neg+1))
done
grep -h TUDONE $T/run_*.log | cut -c1-160 > $O/summary.txt
[ $bad -eq 0 ] && [ $negok -eq $neg ] && { echo "COLL_GSZ PASS runs=$(wc -l < $J) negatives=$neg caught"; exit 0; }
echo "COLL_GSZ FAIL bad=$bad negatives_caught=$negok/$neg"; exit 1
