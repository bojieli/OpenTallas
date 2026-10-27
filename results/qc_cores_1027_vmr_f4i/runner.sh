#!/bin/bash
set -euo pipefail
K=$1
T=/srv/opentallas-scratch2/claude/codex-qc-cores-0815/source_tools/die_plan
cp -a --reflink=auto "$K/baseline_run" "$K/run"
B=$K/run/results/asap7/kq_qfd_dv_s8x_vmr_f4a_m0/base
mkdir -p "$K/eco_out"
docker run --rm --name codex-vmr-f4j-eco --cpus 8 --memory 24g -v "$K":/work -v "$K/baseline_run/results/asap7/kq_qfd_dv_s8x_vmr_f4a_m0/base":/base:ro -v "$K/baseline_signoff/ff/sdcdir":/sdc:ro -v "$K/eco_out":/out openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 8 -exit /work/eco.tcl' > "$K/eco.log" 2>&1
grep -q F4J_DONE "$K/eco.log"
# DRC must actually be empty; never inherit the baseline verdict.
python3 - "$K" <<'PY'
import sys,re,json,pathlib
k=pathlib.Path(sys.argv[1]);s=(k/'eco.log').read_text();v=re.findall(r'Number of violations\s*=\s*(\d+)',s)
if not v or int(v[-1])!=0:raise SystemExit('F4J DRC FAIL '+str(v[-1:]))
p=k/'run/logs/asap7/kq_qfd_dv_s8x_vmr_f4a_m0/base/5_2_route.json';d=json.loads(p.read_text());d['detailedroute__route__drc_errors']=int(v[-1]);p.write_text(json.dumps(d,indent=2)+'\n')
PY
cp "$K/eco_out/6_final.odb" "$K/eco_out/6_final.spef" "$K/eco_out/6_final.v" "$B/"
python3 -I "$T/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --ff-vclk auto --out "$K/signoff_f4j" > "$K/signoff_f4j.log" 2>&1 || SO=$?
docker run --rm --cpus 8 --memory 24g -v "$K":/work -v "$T":/tools:ro openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /tools/lec.py /work --netlist /work/run/results/asap7/kq_qfd_dv_s8x_vmr_f4a_m0/base/6_final.v --out /work/lec_f4j' > "$K/lec_f4j.log" 2>&1 || LEC=$?
echo "F4J_CHAIN_DONE signoff=${SO:-0} lec=${LEC:-0} $(date -Is)" > "$K/f4j_chain.txt"
exit "${SO:-0}"
