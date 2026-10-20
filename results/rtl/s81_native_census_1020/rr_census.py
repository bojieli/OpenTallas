from pathlib import Path
import json,hashlib
import textbook_lint as t
p=Path('/srv/opentallas-scratch/claude/ref_gate/s81sf_bfcol_c199rr-20261019-122534/routes/gate/work/orfs/results/asap7/opentallas_ot_v41_bf_col_asap7_ref_gate/base/1_2_yosys.v')
r=t.run(str(p),None,dict(hf_report=32,hf_max=32,hf_port_refuse=32,hf_reset_refuse=32,hf_refuse=32),mode='refuse')
r['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
Path('rr.json').write_text(json.dumps(r,indent=1)+'\n')
print(r['verdict'],len(r['refuse'].get('high_fanout',[])),{k:v for k,v in r['metrics'].items() if k.startswith('hf_')},flush=True)
