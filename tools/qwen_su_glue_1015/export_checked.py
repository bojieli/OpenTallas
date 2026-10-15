#!/usr/bin/env python3
"""Checked leaf export using the mandatory reference-tile flow's actual helpers."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--route',type=Path,required=True);p.add_argument('--kit',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[2]
sta_path=a.route/'corner_sta.json';sta=json.loads(sta_path.read_text());fp=json.loads((a.kit/'floorplan.json').read_text());top=fp['top']
assert fp['kind']=='tile' and not fp.get('blocks'),'this scoped helper exports actual plain SU leaves only'
a.out.mkdir(parents=True,exist_ok=True)
py=sys.executable
cmd=[py,str(root/'tools/tt_views/view_export.py'),'--orfs-dir',str(a.route/'work/orfs'),'--name',top,'--out',str(a.out),'--interface-sdc',str(a.kit/'signoff.sdc'),'--post-sdc',str(a.kit/'signoff.sdc'),'--post-sdc',str(root/'physical/common_flow/io_ref_routed.sdc'),'--corners','ss,ff,tt','--expect-tt',str(sta['setup_tt']['worst_slack_ps']),'--expect-ff',str(sta['hold_ff']['worst_slack_ps']),'--require-check']
subprocess.run(cmd,check=True)
base=next((a.route/'work/orfs').glob('results/asap7/*/base'))
subprocess.run([py,str(root/'tools/closure_loop/ck_insertion.py'),'--base',str(base),'--routed','--all-clocks','--raw-source','--output',str(a.out/'insertion.json')],check=True)
lef=a.out/(top+'.lef');subprocess.run([py,str(root/'tools/hier_contract/abstract_pin_stub.py'),str(lef),str(lef)],check=True)
sys.path.insert(0,str(root/'tools/hier_contract'));import child_lint
lint=child_lint.lint(str(lef),str(a.out));(a.out/'child_lint.json').write_text(json.dumps(lint,indent=2)+'\n');assert lint['verdict']=='PASS',lint
abstract=json.loads((a.out/'abstract.json').read_text());assert abstract['checked'] and abstract['ok']
receipt=dict(schema='opentallas.qwen-su-checked-leaf-export.v1',top=top,route=str(a.route),source_commit=(root/'SOURCE_COMMIT').read_text().strip(),corner_sta_sha256=hashlib.sha256(sta_path.read_bytes()).hexdigest(),setup_tt_ps=sta['setup_tt']['worst_slack_ps'],hold_ff_ps=sta['hold_ff']['worst_slack_ps'],setup_ss_sensitivity_ps=sta['setup_ss']['worst_slack_ps'],timing_replay_checked=True,child_lint=lint['verdict'],files={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in a.out.iterdir() if x.suffix in ['.lib','.lef'] or x.name=='insertion.json'},scope='actual routed leaf; parent clockentry wiring/phi-R/boundary pairs/die assembly remain separate')
(a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
