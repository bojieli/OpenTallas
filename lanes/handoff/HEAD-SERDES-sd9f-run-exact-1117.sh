#!/bin/bash
set -euo pipefail
L=/srv/opentallas-scratch2/claude/fable-fix-head-serdes/sd9f_lane/bench
cd "$L"
python3 -I - <<'PY'
from pathlib import Path
p=Path('src/tb_kp4_enc_la.sv');s=p.read_text();assert s.count('.H0_SEQ_ONLY(1)')==2
p.write_text(s.replace('.H0_SEQ_ONLY(1)', '.H0_SEQ_ONLY(0)'))
PY
# Flatten the define-OFF reference first. A current origin/main reference
# still contains LA conditionals and a global -D would otherwise enable both.
iverilog -g2012 -E -Isrc -o src/ref_flat.sv src/ot_s81_kp4_enc.sv
python3 -I - <<'PY'
from pathlib import Path
p=Path('src/ref_flat.sv');s=p.read_text();a='module ot_s81_kp4_enc #';assert s.count(a)==1
s=s.replace(a,'module ot_s81_kp4_enc_ref #',1)
import re
assert re.search(r'^\s*`(?:ifdef|ifndef|elsif|else|endif)\b',s,re.M) is None
assert 'e_ar[gr < 10 ? gr + 10 : gr]' not in s
Path('src/ot_s81_kp4_enc_ref.sv').write_text(s)
PY
docker run --rm --cpus=8 -v "$L:$L" -w "$L" --entrypoint bash verilator/verilator:v5.032 -c '
set -euo pipefail
for mode in base lane; do
 flags=""; [ "$mode" = base ] || flags=-DRCKRF_MUT_LA_LANE
 verilator --binary -j 8 -O3 --x-assign fast --x-initial unique -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH \
  -Isrc -DOT_S81_KP4_ENC_LA $flags -GPPCYC=0 -GPIN_FAULT=0 -GNCYC=30000 \
  --top-module tb_kp4_enc_la -Mdir obj_$mode src/ot_s81_kp4_common.sv src/ot_s81_kp4_enc_ref.sv \
  src/ot_s81_kp4_enc.sv src/tb_kp4_enc_la.sv > build_$mode.log 2>&1
 ./obj_$mode/Vtb_kp4_enc_la > run_$mode.log 2>&1
 grep "^KP4_ENC_LA" run_$mode.log
done
'
python3 -I - <<'PY'
from pathlib import Path
import re,json,hashlib
base=Path('run_base.log').read_text();mut=Path('run_lane.log').read_text()
assert re.search(r'KP4_ENC_LA PASS .*mismatches=0',base)
m=re.search(r'KP4_ENC_LA FAIL .*mismatches=(\d+)',mut);assert m and int(m[1])>0
rec=dict(source_sha256=hashlib.sha256(Path('src/ot_s81_kp4_enc.sv').read_bytes()).hexdigest(),shape=dict(PPCYC=0,PIN_FAULT=0,H0_SEQ_ONLY=0,cycles=30000),baseline_reference='preprocessed define-off source before candidate flags',positive=[x for x in base.splitlines() if x.startswith('KP4_ENC_LA')],negative=[x for x in mut.splitlines() if x.startswith('KP4_ENC_LA')],latency_delta=0,verdict='PASS')
Path('result.json').write_text(json.dumps(rec,indent=2)+'\n')
print('HEAD_ENCODER_LA_EXACT_PASS MUTANT_DETECTED')
PY
