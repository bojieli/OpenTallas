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
python3 - $T <<'PY' || { echo "COLL_GSZ ERROR group fixtures"; exit 3; }
import sys; from pathlib import Path
sys.path.insert(0, 'tools'); import ha2_ar_fixture as HF
import numpy as np, hdc_golden as G
_b = HF.build
def nb(shape, seed):                    # + -0 contributors (review-0427 HF-5): every contributor -0 on lanes 224..239,
    s, parts, zr = _b(shape, seed)      # even contributors -0 / odd +0 on 240..255; golden recomputed (canonical +0)
    nc, nog = s['NC'], s['NOG']
    parts[:, 224:240] = np.float32(-0.0)
    if nc == 1: parts[:, 0:16] = np.float32(-0.0)
    parts[0::2, 240:256] = np.float32(-0.0); parts[1::2, 240:256] = np.float32(0.0)
    for og in range(nog):
        q = [parts[og * nc + j].copy() for j in range(nc)]
        while len(q) > 1:
            q = [G.add(q[i], q[i + 1]) for i in range(0, len(q), 2)]
        if nc == 1: q[0] = G.add(q[0], np.zeros_like(q[0])) # U2 canonical +0 with inactive columns
        zr[og] = G.to_bf16(q[0]) if s['BF16'] else q[0]
    return s, parts, zr
import os
if os.environ.get('NEGZ', '1') == '1':
    HF.build = nb
for n in (2, 4, 8):
    HF.SHAPES[f'g{n}'] = dict(GS=n, NG=96 // n, NC=n, NOG=96 // n, E=128 if n == 1 else 256, LANES=16, ONESHOT=0, BF16=1)
    HF.build = nb if os.environ.get('NEGZ', '1') == '1' else _b
    HF.write(Path(sys.argv[1]) / 'fx' / f'g{n}', f'g{n}', 20261009 + n)
HF.SHAPES['ar96'] = dict(GS=8,NG=12,NC=8,NOG=12,E=1024,LANES=16,ONESHOT=0,BF16=1)
HF.write(Path(sys.argv[1]) / 'fx' / 'ar96', 'ar96', 20261009)
PY
M=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
SRC="rtl/link/ot_link_afifo.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv $M rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv rtl/hbm_accel/tu/ot_hcoll_port.sv rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_ps.sv rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_psg.sv rtl/hbm_accel/tu/tb_cx_coll_global_mcast.sv"
D="+define+TU_DUT=ot_hbm_accel_tu_endpoint_psg"; CK="+define+TU_PCLK_IS_CLK -GT_PHY=0.833333"
build() { n=$1; shift; $V --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --x-assign fast --x-initial fast \
  --top-module tb_cx_coll_global_mcast --Mdir $T/b/$n $D "$@" $SRC > $T/build_$n.log 2>&1 || { echo "BUILD_FAIL $n"; exit 3; }; }
build ds +define+TU_LOCKSTEP +define+TU_NC=8 +define+TU_NOG=12 +define+TU_BF16=1 +define+TU_GSZPORT=15 +define+TU_PFMAX=64 $CK
for n in 2 4 8; do
  case $n in 2) l=1;;4) l=2;;8) l=3;;esac
  build g$n +define+TU_NC=$n +define+TU_NOG=$((96/n)) +define+TU_BF16=1 +define+TU_GSZ +define+TU_REDUCE +define+TU_GSZPORT=$l +define+TU_MCAST_ALL +define+TU_PFMAX=64 $CK
  build m$n +define+TU_NC=$n +define+TU_NOG=$((96/n)) +define+TU_BF16=1 +define+TU_GSZ +define+TU_REDUCE +define+TU_GSZPORT=$l +define+TU_MCAST_ALL +define+TU_PFMAX=64 $CK +define+CX_MUT_LOCAL_ONLY
done
python3 - "$T" <<'PYC'
import subprocess,sys,json,re
from pathlib import Path
t=Path(sys.argv[1]); rows=[]
for n in (2,4,8):
 for rank in range(96):
  for seed in (1,2): rows.append((f'g{n}','positive',16,rank,seed,f'g{n}'))
 for rank in (0,n-1,95): rows.append((f'm{n}','negative',16,rank,1,f'g{n}'))
for rank in (0,7,8,31,63,95):
 for seed in (1,2):rows.append(('ds','positive',64,rank,seed,'ar96'))
records=[]
for i,(build,kind,pf,rank,seed,fixture) in enumerate(rows):
 args=[str(t/'b'/build/'Vtb_cx_coll_global_mcast'),f'+VEC={t}/fx/{fixture}',f'+PF={pf}',f'+RANK={rank}',f'+SEED={seed}']
 log=t/f'run_{i:03}.log'
 with log.open('w') as f:rc=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT).returncode
 txt=log.read_text(); done=re.search(r'TUDONE .*got=(\d+) own_exact=(\d+) mismatches=0 faults=0 ',txt)
 passed=(rc==0 and bool(done)) if kind=='positive' else (rc!=0 and 'GLOBAL_MCAST_MISSING_AFTER_TRANSPORT_DRAIN' in txt and 'MUTANT_NOT_SENSITIVE' not in txt)
 records.append(dict(build=build,kind=kind,pf=pf,rank=rank,seed=seed,rc=rc,passed=passed,log=log.name,completion=done.group(0) if done else None))
 (t.parent/'receipt.json').write_text(json.dumps(dict(schema='cx.global-mcast.exact.v1',source_base='89380f9f7',records=records,complete=False),indent=2)+'\n')
 if not passed:print('FAILED',records[-1],flush=True);sys.exit(1)
 print('PASS',build,kind,rank,seed,flush=True)
(t.parent/'receipt.json').write_text(json.dumps(dict(schema='cx.global-mcast.exact.v1',source_base='89380f9f7',records=records,complete=True,positive_runs=sum(r['kind']=='positive' for r in records),mutants=sum(r['kind']=='negative' for r in records)),indent=2)+'\n')
print('GLOBAL_MCAST PASS',len(records),flush=True)
PYC
