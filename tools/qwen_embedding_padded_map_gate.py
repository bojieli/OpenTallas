from pathlib import Path
import subprocess,gzip,json,sys,copy
import argparse
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
source=Path(__file__).resolve().parents[1];r=a.out;r.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(source/'tools'))
from check_qwen_embedding_padded_storage import check
lib=source/'results/uarch/topk_station_SSFF_cell_model_20261002/inputs'
inv=r/'invbuf.lib';inv.write_text(gzip.open(lib/'asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz','rt').read())
y=Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys';top='ot_qwen_embedding_ingress_padded';rows=[]
for w in (12,18):
 cmd=f'read_liberty -lib {inv}; read_verilog -sv {source}/rtl/physical/{top}.sv; chparam -set AW {w} {top}; synth -top {top}; dfflibmap -liberty {lib}/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib; opt_clean; write_json {r}/mapped{w}.json; write_verilog -noexpr {r}/mapped{w}.v'
 run=subprocess.run([str(y),'-Q','-T','-p',cmd],capture_output=True,text=True);(r/f'mapped{w}.log').write_text(run.stdout+run.stderr);assert run.returncode==0,run.stderr
 m=json.loads((r/f'mapped{w}.json').read_text())['modules'][top];rows.append(dict(width=w,case='positive',result=check(m,w)))
 for case in ('missing_stage','bypass_stage','disconnected_chain','merged_shadow','reset_bypass'):
  bad=copy.deepcopy(m);pads=sorted(n for n in bad['cells'] if 'g_pad' in n)
  if case=='missing_stage':del bad['cells'][pads[0]]
  elif case=='bypass_stage':bad['cells'][pads[1]]['connections']['A']=bad['cells'][pads[0]]['connections']['A']
  elif case=='disconnected_chain':
   ff=next(c for c in bad['cells'].values() if 'DFFHQN' in c['type']);ff['connections']['D']=bad['ports']['address']['bits'][:1]
  elif case=='merged_shadow':bad['ports']['address_n']['bits']=bad['ports']['address_q']['bits'];bad['netnames']['address_n']['bits']=bad['netnames']['address_q']['bits']
  else:
   ff=next(c for c in bad['cells'].values() if 'DFFASRHQN' in c['type']);p=next(p for p in ('SETN','RESETN') if any(isinstance(x,int) for x in ff['connections'].get(p,[])));ff['connections'][p]=bad['ports']['rst_n']['bits']
  try:check(bad,w)
  except AssertionError as e:rows.append(dict(width=w,case=case,rejected=True,reason=str(e)))
  else:raise AssertionError('mutant accepted '+case)
(r/'mapped_validation.json').write_text(json.dumps(rows,indent=2)+'\n');print('PASS two technology-mapped shapes and ten negative topology/storage mutants')
