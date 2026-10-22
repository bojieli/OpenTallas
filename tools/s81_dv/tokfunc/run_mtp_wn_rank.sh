#!/bin/bash
# Fleet-only minimum real rank0/WN projection of an existing six-position image.
# Retains all four actual WN lane/PHY/relay/landing channels and every input date.
set -euo pipefail
: "${XSTAGE:?source-pinned xdie stage}"
: "${FULL_OUT:?existing full6 emitted input directory}"
OUT=${OUT:-wn_rank_replay}
mkdir -p "$OUT"
O=$(realpath "$OUT")
python3 - "$FULL_OUT" "$O" <<'PY'
from pathlib import Path
import collections,hashlib,json,math,sys
s=Path(sys.argv[1]);o=Path(sys.argv[2]);g=s/'golden'
stim=[x for x in (g/'stim.hex').read_text().splitlines() if int(x[-278:-276],16)==2]
cmds=[x for x in (g/'mu.hex').read_text().splitlines() if int(x[8:10],16)==2]
assert len(stim)==3840 and len(cmds)==48, 'actual six-position rank0 inventory changed'
(o/'stim.hex').write_text('\n'.join(stim)+'\n');(o/'mu.hex').write_text('\n'.join(cmds)+'\n')
full=json.loads((s/'capacity.json').read_text())
capacity=dict(NSMAX=len(stim)+1,NMMAX=len(cmds)+1,QD=len(stim)+1,MAXCYC=full['MAXCYC'])
p=dict(scope='single real WN rank A/B circuit, four complete lanes; exact six-position schedule',
       excluded='other independent ranks and orthogonal idle TP mesh; no required WN logic removed',
       source_input_sha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in (g/'stim.hex',g/'mu.hex')},
       projected_sha256={x:hashlib.sha256((o/x).read_bytes()).hexdigest() for x in ('stim.hex','mu.hex')},
       rank=0,dp=2,beats=len(stim),commands=len(cmds),capacity=capacity,
       exact_projection='byte-identical original rows selected by dp2; original absolute issue/command/deadline cycles retained',
       date_first=int(stim[0][8:16],16),date_last=int(stim[-1][8:16],16))
(o/'projection.json').write_text(json.dumps(p,indent=2)+'\n')
# Exact source list from the preserved full bench build; change only the bench.
line=(s/'position6/build_cmd.txt').read_text().split(' | ',1)[1]
files=[x for x in line.split() if x!='rtl/test/xdie_s81_2/tb_xdie_s81_2.sv']
files.append('rtl/test/xdie_s81_2/tb_mtp_wn_positions.sv')
(o/'sources.f').write_text('\n'.join(files)+'\n')
PY
read -r NS NM QD MC < <(python3 - "$O/projection.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))['capacity'];print(r['NSMAX'],r['NMMAX'],r['QD'],r['MAXCYC'])
PY
)
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p "$O/build"
if [ ! -x "$O/build/obj/Vtb_mtp_wn_positions" ]; then
  (cd "$XSTAGE" && sha256sum $(cat "$O/sources.f") > "$O/build/sources.sha256"
   /usr/bin/time -v -o "$O/build/time.log" "$V" --binary --timing -O1 -Wno-fatal \
    -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style \
    +incdir+rtl/dsrom_sys/s81_link +define+OT_S81PH_GBX_FMT1 +define+OT_S81PH_EP_PIPE2 \
    --top-module tb_mtp_wn_positions -Mdir "$O/build/obj" -f "$O/sources.f" \
    -GNSMAX="$NS" -GNMMAX="$NM" -GQD="$QD" -GMAXCYC="$MC" -GD_ST=258 \
    --build-jobs ${JOBS:-8} -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0') > "$O/build/build.log" 2>&1
fi
"$V" --version > "$O/build/verilator_version.txt"
(cd "$O" && /usr/bin/time -v -o time_run.log build/obj/Vtb_mtp_wn_positions \
  +NS=$((NS-1)) +NM=$((NM-1)) > run.log 2>&1)
grep -E '^WN_CFG|^WN_STATS|^PASS|^FAIL|^MISMATCH|^TAGBAD' "$O/run.log"
grep -q '^PASS mtp_wn_positions' "$O/run.log"
