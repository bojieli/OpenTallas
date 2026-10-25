#!/usr/bin/env python3
"""Same-cycle native W128 bank/pair composition miter plus bad-write mutant.
HC arithmetic leaves and SRAMs are unchanged black boxes. Every leaf/SRAM input
and every original bank output is compared. Checked lockstep points strengthen
unchanged parent control state; no proof ports enter the physical ABI.
"""
import argparse,json,os,re,subprocess
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--top',required=True);ap.add_argument('--root',type=Path,default=Path('.'));a=ap.parse_args();r=a.root.resolve();os.chdir(r);o=r/'miter';o.mkdir(exist_ok=True);y=str(Path.home()/'.local/opentallas-tools/bin/yosys')
def run(name,script):
 p=o/(name+'.ys');p.write_text(script);return subprocess.run([y,'-ql',str(o/(name+'.log')),'-s',str(p)]).returncode
prep=f'''read_json native128.json
blackbox ot_hdc_v41x_hcp_lanes
hierarchy -top {a.top}
flatten
write_json {o}/gold_flat.json
design -reset
read_json pair_compact/compact128.json
blackbox ot_hdc_v41x_hcp_lanes
hierarchy -top {a.top}
flatten
write_json {o}/gate_flat.json
'''
assert run('prep',prep)==0
gold=json.loads((o/'gold_flat.json').read_text());gate=json.loads((o/'gate_flat.json').read_text());gm=gold['modules'][a.top];m=gate['modules'][a.top];d={}
for n,c in m['cells'].items():
 mm=re.match(r'^ot_hbm_hc_bank128_pair([0-7])\\?\.(.*)$',n)
 if mm and c['type'] in ('ot_hdc_v41x_hcp_lanes','ot_sram_1r1w_1024x256_m2_r2c2','ot_sram_1r1w_128x256_m1_r2c2'):
  k=int(mm[1]);n=mm[2]
  for tag,off in [('g_grp',2*k),('g_w',2*k),('g_x',k)]:n=re.sub(re.escape(tag)+r'\[(\d+)\]',lambda q:tag+'['+str(int(q[1])+off)+']',n)
 assert n not in d,n
 d[n]=c
m['cells']=d;points=[]
for n in sorted(set(gm['cells'])&set(m['cells'])):
 x,z=gm['cells'][n],m['cells'][n]
 if x['type'].startswith('$') and x['port_directions'].get('Q')=='output':
  assert x['type']==z['type'] and x.get('parameters')==z.get('parameters'),n
  assert len(x['connections']['Q'])==len(z['connections']['Q']),n
  pn='proof_state_'+str(len(points));points.append(n)
  gm['ports'][pn]=dict(direction='output',bits=x['connections']['Q']);m['ports'][pn]=dict(direction='output',bits=z['connections']['Q'])
(o/'gold.json').write_text(json.dumps(gold));(o/'gate.json').write_text(json.dumps(gate));(o/'state_points.json').write_text(json.dumps(points,indent=2)+'\n');mut=json.loads(json.dumps(gate));mut['modules'][a.top]['cells']['u_c.u_b.g_w[0].u_m']['connections']['w_ce_in']=['0'];(o/'mutant.json').write_text(json.dumps(mut))
result=dict(schema='opentallas.hbm.hc128.pair_miter.v1',top=a.top,source_sha='591bcf802',defines=['SYNTHESIS','OT_FP_DATA_NORST'],scope='all original bank outputs + every unchanged HC-leaf/SRAM boundary input, same-cycle; parent control state checked',state_points=len(points),arithmetic_leaf='unchanged ot_hdc_v41x_hcp_lanes',split_cycles=0,checks={})
for mode in ['gate','mutant']:
 script=f'''read_json {o}/gold.json
expose -evert t:ot_hdc_v41x_hcp_lanes t:ot_sram_1r1w_1024x256_m2_r2c2 t:ot_sram_1r1w_128x256_m1_r2c2
rename -hide
rename {a.top} gold
write_rtlil {o}/gold.il
design -reset
read_json {o}/{mode}.json
expose -evert t:ot_hdc_v41x_hcp_lanes t:ot_sram_1r1w_1024x256_m2_r2c2 t:ot_sram_1r1w_128x256_m1_r2c2
rename -hide
rename {a.top} gate
write_rtlil {o}/{mode}.il
design -reset
read_rtlil {o}/gold.il
read_rtlil {o}/{mode}.il
async2sync
equiv_make gold gate eq
hierarchy -top eq
opt -full
equiv_simple -seq 2
equiv_induct -seq 24
tee -o {o}/{mode}_status.txt equiv_status
equiv_status -assert
'''
 rc=run(mode,script);s=(o/(mode+'_status.txt')).read_text();ma=re.search(r'Of those cells (\d+) are proven and (\d+) are unproven',s);assert ma,('no equivalence status',mode,rc);pr,un=map(int,ma.groups());verdict=('PASS' if mode=='gate' and rc==0 and un==0 else 'CAUGHT' if mode=='mutant' and rc!=0 and un==1 and "1'0" in s else 'FAIL');result['checks'][mode]=dict(verdict=verdict,rc=rc,proven=pr,unproven=un,mutation='first weight SRAM write-enable tied0' if mode=='mutant' else None);assert verdict!='FAIL',result
result['verdict']='PASS';(o/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
