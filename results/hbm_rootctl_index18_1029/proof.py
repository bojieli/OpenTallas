from pathlib import Path
import subprocess,json
r=Path(__file__).parent;orig=(r/'ot_hbm_idx_vm_share_index18_r2048.sv').read_text();results=[]
variants={'positive':orig,'regularhigh_mutant':orig.replace('= index_rq[18*b +: 18]','= {index_rq[18*b+17:18*b+16],1\'b0,index_rq[18*b +: 15]}'),'mirror_mutant':orig.replace('topk_rq[17*b+15],1\'b0','topk_rq[17*b+14],1\'b0')}
# Indexed partselect keeps variable loop indices legal for the mutant.
variants['regularhigh_mutant']=variants['regularhigh_mutant'].replace('index_rq[18*b+17:18*b+16]','index_rq[18*b+16 +: 2]')
for label,text in variants.items():
 assert label=='positive' or text!=orig
 d=r/label;d.mkdir(exist_ok=True);(d/'candidate.sv').write_text(text)
 c=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(d/'sim'),str(r/'gold.sv'),str(r/'kreg.sv'),str(d/'candidate.sv'),str(r/'tb_share_index18.sv')],capture_output=True,text=True)
 (d/'compile.log').write_text(c.stdout+c.stderr);assert c.returncode==0,(label,c.stderr)
 p=subprocess.run(['vvp',str(d/'sim')],capture_output=True,text=True);(d/'run.log').write_text(p.stdout+p.stderr)
 assert (p.returncode==0)==(label=='positive'),(label,p.stdout,p.stderr)
 results.append(dict(label=label,exit=p.returncode,output=p.stdout.strip(),caught=label!='positive'))
(r/'proof.json').write_text(json.dumps(dict(results=results,VM_RT=75,F32=1,added_cycles=0,scope='Smallest actual shareleaf source vehicle, random native highregular/mirror and legacy responses/fault/reset lockstep; no whole rootctl numeric or physical adoption'),indent=2)+'\n');print(results)
