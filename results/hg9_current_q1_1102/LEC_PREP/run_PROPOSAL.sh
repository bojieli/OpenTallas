#!/usr/bin/env bash
set -euo pipefail
[[ ${HG9_Q1_LEC_REVIEWED:-0} == 1 ]] || { echo 'PREP ONLY: q1 official native LEC not admitted' >&2; exit 2; }
R=$(cd -- "$(dirname -- "$0")" && pwd)
python3 "$R/verify_inputs.py" "$R"
mkdir "$R/proof"
docker run --rm --cpus=4 --memory=16g --memory-swap=16g -e OT_LEC_RESET_CYCLES=4 -v "$R/kit":/work:ro -v "$R/checker":/checker:ro -v "$R/proof":/lecout sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /usr/bin/time -v -o /lecout/resource.time python3 -I /checker/lec.py /work --netlist /work/1_2_yosys.v --out /lecout --gold-frontend slang --jobs 1
python3 - "$R/proof/lec.json" <<'CHECK'
import json,sys
r=json.load(open(sys.argv[1]));c=r['counts'];x=r['reset_contract']
assert r['verdict']=='EQUIVALENT' and c['differs']==0 and c['undecided']==0 and c['proved']==c['compare_points']
assert x['requested']==4 and x['used']==4 and x['contract']['edges']==16 and not x['debug_overrides'] and not x.get('refused')
assert set(r['black_boxes'])=={'ot_sram_1r1w_128x256_m1_r2c2'},r['black_boxes']
print('HG9_Q1_CURRENT_SYNTH_NATIVE4_OFFICIAL_LEC_PASS')
CHECK
