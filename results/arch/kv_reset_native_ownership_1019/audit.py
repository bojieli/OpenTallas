#!/usr/bin/env python3
"""Read-only exact GEN7 reset ownership; no physical admission or timing guesses."""
import argparse,collections,hashlib,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--artifact-dir',type=Path,required=True);p.add_argument('--tools',type=Path,required=True);p.add_argument('--table',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.tools));import die_port_bind as P
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
die=a.artifact_dir/'die_bound.v';assert sha(die)=='7006cbd0d11ffb755902c588eec474a1a7c27d7ad77212cebe3be1fcae5aae7e'
n,_,_,ins=P.parse_die(str(die));cells={i:dict(master=m,parameters=p,ports=c) for m,i,p,c in ins}
bits=lambda e:[tuple(x) for x in P.expr_bits(e,n)]
edges={}
for i,v in cells.items():
 c=v['ports']
 if v['master']=='qkd_rlys_1':
  b=bits(c['b']);aa=bits(c['a']);assert len(b)==len(aa)==1 and b[0] not in edges
  edges[b[0]]=dict(instance=i,input=aa[0],output=b[0],clock=c['ck'])
def trace(expr):
 b=bits(expr);assert len(b)==1;b=b[0];seen=set();chain=[]
 while b in edges:
  assert b not in seen;seen.add(b);entry=edges[b];chain.append(entry);b=entry['input']
 owners=[dict(instance=i,**v) for i,v in cells.items() if (i=='host' or v['master'] in ('qkd_rst_region','qkd_rst_region_pr')) and any(b in bits(e) for port,e in v['ports'].items() if port in ('b','die_rst_n'))]
 return dict(root_bit=b,registered_depth=len(chain),chain=chain,owners=owners)
consumers={i:dict(master=cells[i]['master'],clock=cells[i]['ports']['ck'],reset_net=cells[i]['ports']['rst_n'],reset=trace(cells[i]['ports']['rst_n'])) for i in ('ahub','kvs_attn','seq__u_core')}
regional=[]
for i,v in cells.items():
 if v['master'] not in ('qkd_rst_region','qkd_rst_region_pr'):continue
 c=v['ports'];d=P.expr_bits(c['dly'],n);regional.append(dict(instance=i,master=v['master'],clock=c['ck'],por=c['por_n'],delay_expression=c['dly'],input_chain=trace(c['a']),output=c['b']))
table=json.loads(a.table.read_text());buses=[b for b in table['buses'] if b['src']['inst']=='ahub' and b['src']['port']=='hf'];assert {b['age_edges'] for b in buses}=={34,37}
loads=json.loads((a.artifact_dir/'gen7/reset_loads.json').read_text());roots={v['root_details']['id']:v['root_details'] for v in loads['loads'] if v['root_details']}
candidate=json.loads((a.artifact_dir/'gen7/reset_branch_candidate.json').read_text())
out=dict(schema='opentallas.kv_reset_native_prerequisites.v1',qualified_release=False,source_commit='4db097403',inputs={str(x):sha(x) for x in [die,a.table,a.artifact_dir/'gen7/reset_branch_candidate.json',a.artifact_dir/'gen7/reset_loads.json']},consumer_ownership=consumers,regional_roots=regional,fault_candidate_roots=roots,hf_paths=buses,source_files={x.name:sha(x) for x in sorted((a.artifact_dir/'source').glob('*'))},candidate_depth=dict(final=273,inherited=11,diagnostic_skew=64,installed=False),native_bounds=dict(parent_reset_clock_phase_bound=None,loaded_reset_assertion_release_sta=None,cross_root_assertion_skew_cycles=None,reason='No installed candidate clock/reset tree or exact loaded native cross-root receipt in pinned inputs'),counter_contract=dict(ign_bits=9,ignore_max_representable=511,dly_bits=8,cnt_bits=8,dly_max=255,hold_bits=8,hold_expression='HOLD[7:0] - 8\'d1',hold_width_change_requires_source_proof=True),prerequisites=[dict(id=i,status='OPEN',requires=r) for i,r in [('NATIVE_ROOT_PHASE','Actual loaded clock/reset arrivals for host.ck_rst, ES regional root and central/stack reset relays; TT/FF bound and exact source/leaf binding'),('AHUB_CLEAR','Reset AHUB own ES-rooted port; outer ot_rst_pipe assertion2/release4, internal hub ot_rst_pipe assertion2/release4; hold low through every feedback/source clear, reciprocal/ZH return, no start reassertion'),('HF_DRAIN','After final AHUB hf low, flush 34 plain edges to attention and37 to seq under proven clock phase; consumer reset alone cannot clear source'),('BOOT_ADMISSION','Fixed all-root POR/reset pulse, latest source-clear+drain and all273-depth candidate reset releases priced before first admission; counter widths explicitly sized'),('STATUS_RETIREMENT','Source-pinned operation cutoff plus entire fault graph/AFR/TX/link/landing/consumer age and native phases; continuous sticky health remains live')]])
a.out.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(consumers={k:dict(depth=v['reset']['registered_depth'],root=v['reset']['root_bit'],clock=v['clock']) for k,v in consumers.items()},regional_roots=len(regional),candidate_roots=len(roots),qualified_release=False)))
