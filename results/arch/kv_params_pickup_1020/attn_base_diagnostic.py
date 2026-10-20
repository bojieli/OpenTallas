#!/usr/bin/env python3
# Diagnostic only. Reuse exact terminal j0 prelude; do not qualify an induction failure.
from pathlib import Path
import re,json,shutil,subprocess,hashlib
src=Path('/srv/opentallas-scratch/claude/kv-attn3-1020/work_j0')
out=Path('/srv/opentallas-scratch2/claude/codex-kv-params-audit-1020/attn_base_diagnostic')
out.mkdir(exist_ok=True)
for n in ['cells.v','gate.v','gold1.il','equiv.ys']:
 shutil.copy2(src/n,out/n)
pre=(out/'equiv.ys').read_text().split('async2sync\n')[0]
gate=set(re.findall(r'wire (S__\w+);',(out/'gate.v').read_text()))
gold=set(re.findall(r'add -wire (S__\w+) 1',pre))
paired=sorted(x for x in gate&gold if '__rep__' not in x)
wit=sorted(x for x in gold if x.startswith('S__wit_'))
assert len(paired)==6528, ('paired mismatch',len(paired))
assert len(wit)==913, ('witness mismatch',len(wit))
sets=' '.join(f'-set-at {i} in_rst_n 0' for i in range(1,7))
sets+=' '+' '.join(f'-set-at 1 gold.{x} gate.{x}' for x in paired+wit)
base=pre+'async2sync\nexpose gold/w:S__* gate/w:S__*\nmiter -equiv -flatten -make_assert gold gate miter\nhierarchy -top miter\nopt_clean\nsat -seq 14 -prove-asserts -prove-skip 6 -set-def-inputs '+sets+' -dump_json base_cex.json -verify\n'
(out/'base.ys').write_text(base)
(out/'RECIPE.json').write_text(json.dumps({'purpose':'DIAGNOSTIC_ONLY_BASE; original induction remains failed; never receipt','original_prelude_sha256':hashlib.sha256((out/'equiv.ys').read_bytes()).hexdigest(),'paired_initial':len(paired),'replicas_free':len(gate&gold)-len(paired),'witness_initial':len(wit),'reset_edges':6,'checked_steps':[7,14],'source':'terminal original ATTN3 j0 unchanged inputs; SAME native base mechanics'},indent=2))
with (out/'base.out').open('w') as log:
 p=subprocess.run(['/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys','-l','base.log','-q','-s','base.ys'],cwd=out,stdout=log,stderr=subprocess.STDOUT)
(out/'base.rc').write_text(str(p.returncode)+'\n')
