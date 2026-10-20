from pathlib import Path
import hashlib,json,argparse
import textbook_lint as t
ap=argparse.ArgumentParser();ap.add_argument('--source',default='9dd70facf');a=ap.parse_args()
p=Path('work/results/asap7/opentallas_ot_v41_bf_col_asap7_ref_gate/base/1_2_yosys.v')
r=t.run(str(p.resolve()),None,dict(hf_report=32,hf_max=32,hf_port_refuse=32,hf_reset_refuse=32,hf_refuse=32),mode='refuse')
r['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
r['scope']='Mapped BF native32 all-driver fanout, clocks excluded; resets included. No geometry in this pass.'
r['source_commit']=a.source
Path('native32_census.json').write_text(json.dumps(r,indent=1)+'\n')
print(r['verdict'],r['cells'],r['flops'],r['macros'],len(r['refuse'].get('high_fanout',[])),{k:v for k,v in r['metrics'].items() if k.startswith('hf_')},flush=True)
