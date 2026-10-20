from pathlib import Path
import hashlib,json,time
import textbook_lint as t
roots={'qgate':Path('/srv/opentallas-scratch/claude/s81-pinreg4/qgate/gate_run'),'bfgate':Path('/srv/opentallas-scratch/claude/s81-pinreg4/bfgate/gate_run'),'lpk4':Path('/srv/opentallas-scratch/claude/ref_gate/s81lk_serdes_col_lp4-20261019-225834/routes/gate/work/orfs')}
for name,root in roots.items():
 paths=list(root.glob('**/results/**/1_2_yosys.v'))
 if len(paths)!=1:raise RuntimeError((name,paths))
 net=paths[0]
 r=t.run(str(net),None,dict(hf_report=32,hf_max=32,hf_port_refuse=32,hf_reset_refuse=32,hf_refuse=32),mode='refuse')
 r['sha256']=hashlib.sha256(net.read_bytes()).hexdigest()
 r['purpose']='Binding mapped fanout <=32 including reset; existing progressing gates preserved. No geometry dump: reach/storage/pin registration still require separate evidence.'
 Path(name+'.json').write_text(json.dumps(r,indent=1)+'\n')
 print(name,r['verdict'],'cells',r['cells'],'flops',r['flops'],'maxima',{k:v for k,v in r['metrics'].items() if k.startswith('hf_')},flush=True)
