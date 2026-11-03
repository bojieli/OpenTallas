#!/usr/bin/env bash
# DH55-HSPLIT: lockstep of the split HOST pair (hd_host_w + hd_host_e) against the original ot_s81hd_host_ep_core,
# with real peer safe8 lanes; MODE 0 = TEST boot profile + real ctl cores, MODE 1 = open-loop random frames + lane1
# fault. The TB models the two generated wrapper boundary flops per seam port; expected die-level seam offsets
# E2W +3 / W2E +3 (plan lane cycles 3 = boundary 2 + fixed 1). Mutants 1-4 (no landing register, swapped bits, extra W->E cycle,
# lane1 fault not landed) must each be caught. Run through ot-run / a fleet host, never localhost.
set -euo pipefail
ROOT=${OT_SOURCE_ROOT:-$(git -C "$(dirname "$(readlink -f "$0")")" rev-parse --show-toplevel)}
O=$(realpath -m "${1:?fresh output directory}")
if [ -e "$O" ];then echo "refusing existing output $O" >&2;exit 2;fi
mkdir -p "$O";cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version >"$O/verilator_version.txt"
python3 tools/s81_dv/hostctx_1021/gen_vectors.py "$O/vec" >"$O/gen.log"
python3 - "$O" <<'PY'
from pathlib import Path
import sys
sys.path.insert(0,'tools/s81_head')
from head_control_plan_delta import CTL_SOURCES
from head_host_split_delta import W_SOURCES,E_SOURCES
ps=list(dict.fromkeys(CTL_SOURCES+W_SOURCES+E_SOURCES+['rtl/dsrom_sys/s81_head/test/tb_s81hd_host_split_lockstep.sv']))
missing=[p for p in ps if not Path(p).is_file()]
if missing:raise SystemExit('source closure missing: '+str(missing))
(Path(sys.argv[1])/'sources.f').write_text('\n'.join(ps)+'\n')
PY
SEED=${SEED:-11}
for mut in 0 1 2 3 4;do
 for mode in 0 1;do
  "$V" --binary --timing -O1 -Wno-fatal -Wno-TIMESCALEMOD --top-module tb_s81hd_host_split_lockstep -GSPLIT_MUT="$mut" -GMODE="$mode" \
   +define+OT_COLL_NATIVE32 +define+OT_COLL_NATIVE32_OFF -Mdir "$O/obj_${mut}_${mode}" -f "$O/sources.f" --build-jobs "${J:-4}" \
   >"$O/build_${mut}_${mode}.log" 2>&1
  set +e
  "$O/obj_${mut}_${mode}/Vtb_s81hd_host_split_lockstep" +VEC="$O/vec" +SEED="$SEED" >"$O/run_${mut}_${mode}.log" 2>&1
  echo "mut$mut mode$mode rc$?" >>"$O/rc.txt"
  set -e
 done
done
python3 - "$O" <<'PY'
import sys,re,json
from pathlib import Path
o=Path(sys.argv[1]);rc={}
for l in (o/'rc.txt').read_text().split('\n'):
  m=re.match(r'mut(\d) mode(\d) rc(\d+)',l)
  if m:rc[(int(m[1]),int(m[2]))]=int(m[3])
res={f'{k[0]}_{k[1]}':v for k,v in rc.items()}
ok=all(rc[(0,m)]==0 and 'LOCKSTEP PASS' in (o/f'run_0_{m}.log').read_text() for m in (0,1))
caught={m:any(rc[(m,x)]!=0 and 'LOCKSTEP' in (o/f'run_{m}_{x}.log').read_text() for x in (0,1)) for m in (1,2,3,4)}
v=dict(schema='opentallas.head_host_split_lockstep.v1',rc=res,production_pass=ok,mutants_caught=caught,
       verdict='PASS' if ok and all(caught.values()) else 'FAIL',offsets=dict(E2W=3,W2E=3))
(o/'verdict.json').write_text(json.dumps(v,indent=1)+'\n');print(json.dumps(v))
sys.exit(0 if v['verdict']=='PASS' else 3)
PY
echo HEAD_HOST_SPLIT_BENCH_PASS
