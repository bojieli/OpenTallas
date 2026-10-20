#!/bin/bash
set -euo pipefail
old=quant_component_03
out=quant_component_03_scorefix
if [ -e "$out" ];then echo REFUSE_EXISTING_RUN_DIR >&2;exit 2;fi
mkdir "$out"
python3 - "$old" "$out" <<'PY'
import sys,json,hashlib,shutil
from pathlib import Path
old,new=map(Path,sys.argv[1:]);v1=Path('../qnorm_program_model_v1');v2=Path('../qnorm_program_model_v2')
assert (v1/'program.json').read_bytes()==(v2/'program.json').read_bytes()
for line in (old/'inputs.sha256').read_text().splitlines():
 h,p=line.split(maxsplit=1)
 if p=='tb_qnorm_source.sv':assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
for p in old.glob('*.viamap.hex'):shutil.copy(p,new/p.name)
shutil.copy(old/'source_ctl.txt',new/'source_ctl.txt')
gold=json.loads((v2/'quantized_scoreboard.json').read_text());assert len(gold)==20
assert all(len(x['payload532'])==133 and int(x['payload532'],16).bit_length()<=532 for x in gold)
(new/'expected_xq.mem').write_text(''.join(x['payload532']+'\n' for x in gold))
receipt=dict(executable_source_unchanged=True,source_control_unchanged=True,fixture_unchanged=True,
 executable_sha256=hashlib.sha256((old/'obj/Vtb_qnorm_source').read_bytes()).hexdigest(),
 old_failed_gold_sha256=hashlib.sha256((old/'expected_xq.mem').read_bytes()).hexdigest(),
 corrected_gold_sha256=hashlib.sha256((new/'expected_xq.mem').read_bytes()).hexdigest(),
 change='Gold serializer uint8 codes,32bytes/block,532bit bound. No RTL/control/deadline change.')
(new/'reuse_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
PY
"$old/obj/Vtb_qnorm_source" +DIR="$out" +OT_ROM_DIR="$out" > "$out/baseline.log" 2>&1
tail -3 "$out/baseline.log"
for mut in 1 2 3;do
 set +e
 "$old/obj/Vtb_qnorm_source" +DIR="$out" +OT_ROM_DIR="$out" +MUT="$mut" > "$out/mut_${mut}.log" 2>&1
 rc=$?
 set -e
 if [ "$rc" = 0 ] || ! grep -q QNORM_SOURCE_FAIL "$out/mut_${mut}.log";then echo "MUTANT_NOT_CAUSAL $mut";exit 1;fi
 echo "QNORM_SOURCE_CAUSAL_MUTANT_REJECTED $mut"
done
