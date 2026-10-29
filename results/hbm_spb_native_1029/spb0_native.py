"""Opt-in SPB0 native transport, exact source graph + explicit instance/clock/reset contract.
usage: spb0_native.py BOUND.sv ACTUAL_SPB_GRAPH.json CONTRACT.json OUT_DIR
Never changes the input. Consumer-side insertion on exactly three direct, identity-wired nets.
The caller must remove/disable prior station realization on these nets before invoking this transform.
"""
import hashlib,json,re,shutil,sys
from pathlib import Path

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def close(s,start):
 assert s[start]=='(';depth=0
 for i in range(start,len(s)):
  if s[i]=='(':depth+=1
  elif s[i]==')':
   depth-=1
   if depth==0:return i
 raise ValueError('unbalanced parentheses')
def ports(s,inst):
 hits=list(re.finditer(r'(?<![\w$])'+re.escape(inst)+r'\s*\(',s))
 if len(hits)!=1:raise ValueError(f'expected one instance {inst}, found {len(hits)}')
 a=s.index('(',hits[0].start());b=close(s,a);out={}
 for m in re.finditer(r'\.([A-Za-z_]\w*)\s*\(',s[a+1:b]):
  st=a+1+m.end()-1;en=close(s,st);out[m.group(1)]=(st+1,en,s[st+1:en].strip())
 return out
def norm(s):return re.sub(r'\s+','',s)
def run(bound,graph,contract,out):
 bound,graph,contract,out=map(Path,(bound,graph,contract,out));C=json.loads(contract.read_text());G=json.loads(graph.read_text());s=bound.read_text()
 if out.exists():raise ValueError('output directory exists; preserve previous results')
 if any(n in s for n in ('u_hbm_spb0_rx','u_hbm_spb0_tx','hbm_spb0_rx_q','hbm_spb0_tx_q')):raise ValueError('SPB0 native transport already present')
 if C.get('prior_station_realization')!='NONE':raise ValueError('must explicitly attest prior source has no station realization on these three nets')
 if C['rx_depth']!=4 or C['tx_depth']!=4:raise ValueError('this reviewed slice supports RX4/TX4 only')
 lk,ep=C['lk_instance'],C['ep_instance'];L,E=ports(s,lk),ports(s,ep)
 expect={(ep,'sd_tx',lk,'tx',512),(lk,'rx',ep,'sd_rx',512),(lk,'st',ep,'sd_st',2)}
 for partition in C['partitions']:
  for inst,master in ((lk,C['lk_module']),(ep,C['ep_module'])):
   cells=[x for x in G['cells'] if x.get('partition')==partition and x.get('plan_instance')==inst]
   if len(cells)!=1 or cells[0]['module']!=master:raise ValueError('actual selected source master does not match declared physical endpoint')
 for partition in C['partitions']:
  found=set()
  for e in G['edges']:
   if e['src_partition']!=partition or e['dst_partition']!=partition:continue
   sig=(e['src_plan_instance'],e['src_port'],e['dst_plan_instance'],e['dst_port'],e['width'])
   if sig in expect:
    if e['bit_pairs']!=[[i,i] for i in range(e['width'])]:raise ValueError('non-identity SPB pin permutation')
    found.add(sig)
  if found!=expect:raise ValueError(f'{partition}: exact three-net graph missing {expect-found}')
 for a,b in ((L['rx'],E['sd_rx']),(L['st'],E['sd_st']),(E['sd_tx'],L['tx'])):
  if norm(a[2])!=norm(b[2]):raise ValueError('source/consumer are not one direct shared expression; no inferred alias traversal')
 clk=C['clock_expression'];rst=C['reset_expression']
 for who,pn in ((L,C['lk_clock_port']),(E,C['ep_clock_port'])):
  if norm(who[pn][2])!=norm(clk):raise ValueError('core clock expressions differ from the declared common clock')
 for who,pn in ((L,C['lk_reset_port']),(E,C['ep_reset_port'])):
  if norm(who[pn][2])!=norm(rst):raise ValueError('reset expressions differ from declared synchronous delivered reset')
 for x in (clk,rst):
  if not re.fullmatch(r'[A-Za-z_$][\w$]*(?:\[\d+\])?',x):raise ValueError('clock/reset contract must name an existing scalar net')
 replacements=[(E['sd_rx'][0],E['sd_rx'][1],'hbm_spb0_rx_q[511:0]'),(E['sd_st'][0],E['sd_st'][1],'hbm_spb0_rx_q[513:512]'),(L['tx'][0],L['tx'][1],'hbm_spb0_tx_q')]
 for a,b,v in sorted(replacements,reverse=True):s=s[:a]+v+s[b:]
 if len(re.findall(r'\bendmodule\b',s))!=1:raise ValueError('expected one bound partition module')
 body=f'''\n  // Exact selected-RTL SPB0 nets; fixed latency is priced by the plan contract.
  wire [513:0] hbm_spb0_rx_q;
  wire [511:0] hbm_spb0_tx_q;
  ot_hbm_spb0_regs #(.W(514),.N(4),.CW(2)) u_hbm_spb0_rx
    (.clk({clk}),.rst_n({rst}),.d({{{L['st'][2]}, {L['rx'][2]}}}),.q(hbm_spb0_rx_q));
  ot_hbm_spb0_regs #(.W(512),.N(4),.CW(0)) u_hbm_spb0_tx
    (.clk({clk}),.rst_n({rst}),.d({E['sd_tx'][2]}),.q(hbm_spb0_tx_q));
'''
 s=s.replace('endmodule',body+'\nendmodule')
 placement_path=contract.parent/C['placement_file'];place=json.loads(placement_path.read_text())
 if place['actual_graph_sha256']!=digest(graph) or place['plan_sha256']!=C['plan_sha256']:raise ValueError('native bank geometry belongs to a different source graph or plan')
 if len(place['entries'])!=8 or sum(e['width'] for e in place['entries'])!=4104:raise ValueError('native bank FF count mismatch')
 lines=['# Exact native SPB banks, plan-owned lower-left cell coordinates.','set spb_native_sites {}']
 for e in place['entries']:
  if e['module']!='ot_hbm_spb0_regs' or len(e['sites_um'])!=e['width']:raise ValueError('unsupported bank module/width')
  for bit,(x,y) in enumerate(e['sites_um']):lines.append(f'dict set spb_native_sites {{{e["instance"]},{e["stage"]},{bit}}} {{{x:.9g} {y:.9g}}}')
 out.mkdir(parents=True);(out/bound.name).write_text(s);shutil.copy2(Path(__file__).with_name('ot_hbm_spb0_regs.sv'),out/'ot_hbm_spb0_regs.sv')
 (out/'spb_native_sites.tcl').write_text('\n'.join(lines)+'\n')
 shutil.copy2(Path(__file__).with_name('exact_spb_banks.tcl'),out/'spb_native_banks.tcl')
 shutil.copy2(placement_path,out/'placement.json')
 R={'schema':'opentallas.hbm.spb0_native.v1','source_bound_sha256':digest(bound),'actual_graph_sha256':digest(graph),'contract_sha256':digest(contract),'source_has_no_prior_realization':True,'nets':[{'source':f'{lk}.rx/st','sink':f'{ep}.sd_rx/sd_st','width':514,'actual_source_depth':0,'actual_rtl_added_cycles':4,'old_planned_depth':2,'new_depth':4,'model_added_cycles':2},{'source':f'{ep}.sd_tx','sink':f'{lk}.tx','width':512,'actual_source_depth':0,'actual_rtl_added_cycles':4,'old_planned_depth':4,'new_depth':4,'model_added_cycles':0}],'station_modules':[{'module':'ot_hbm_spb0_regs','instance':'u_hbm_spb0_rx','W':514,'N':4,'CW':2},{'module':'ot_hbm_spb0_regs','instance':'u_hbm_spb0_tx','W':512,'N':4,'CW':0}],'placement_file':'placement.json','placement_sha256':digest(placement_path),'actual_new_ff_per_partition':4104,'model_extra_ff_per_partition':1028,'warning':'candidate requires plan/site receipt, shifted lockstep, source binding and routed signoff; no P&R approval'}
 (out/'receipt.json').write_text(json.dumps(R,indent=1)+'\n');print(json.dumps(R,indent=1))
if __name__=='__main__':run(*sys.argv[1:5])
