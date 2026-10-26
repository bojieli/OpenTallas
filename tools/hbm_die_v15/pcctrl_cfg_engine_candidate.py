#!/usr/bin/env python3
"""Consume typed PCCTRL proposal without changing S or adopting a routed view."""
import argparse,copy,hashlib,json,subprocess
from pathlib import Path
import full_die_v16 as die
ROOT=Path(__file__).resolve().parents[2]
S='a89a10d1fc2200a6f6d556dda2efc905cecbac77'
SOURCE='rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf_cfg.sv'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def source_name(p):
 try:return str(p.relative_to(ROOT))
 except ValueError:return str(p)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--binding',type=Path,required=True);ap.add_argument('--source-contract',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--specs',type=Path,default=ROOT/'tools/hbm_die_v15/v16_specs');a=ap.parse_args()
 m=json.loads(a.binding.read_text());baseline=json.loads(a.source_contract.read_text())
 assert m['schema']=='opentallas.pcctrl-cfg-binding-candidate.v1'
 assert sha(a.source_contract)==m['source_contract_sha256']
 assert m['generating_source_commit']==S
 rows={r['old_name']:r for r in m['instances']};assert len(rows)==len(m['instances'])==128
 for n,r in rows.items():
  old=baseline['instances'][n];assert old['master']==r['old_master'] and old['params']==r['old_params']
  assert r['new_master']=='ot_hbm_svc_pc_ctrl_leaf_cfg' and r['source']==SOURCE
  assert r['params']==dict(OREG=1,KREG=1,KRREG=1,RREG=1,WPAY=1)
  pc=old['params']['P'];phase=old['params'].get('PHASE',0)
  rp=(phase+pc*118//32)%118;reload=118+rp+((rp+118+pc)%2)
  straps={v['port']:v for v in r['explicit_straps']};assert len(straps)==len(r['explicit_straps'])==2
  for port,bits,value in [('pc_id',5,pc),('refresh_reload',8,reload)]:
   st=straps[port];assert (st['inst'],st['lo'],st['hi'],st['value'])==(n,0,bits,value),'Wrong literal strap: '+n+'.'+port
   assert st['bit_constants']==[(value>>b)&1 for b in range(bits)]
  assert r['clock_reference']['domain']=='hbm' and r['clock_reference']['R_ps'] is None
  assert r['dependency_sha256']==m['source_dependencies_sha256']
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 source_map={}
 for src,digest in m['source_dependencies_sha256'].items():
  blob=subprocess.check_output(['git','show',m['cfg_rtl_commit']+':'+src],cwd=ROOT)
  assert hashlib.sha256(blob).hexdigest()==digest,src
  p=out/'rtl'/src;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(blob);source_map[src]=source_name(p)
 region=die.engine_region();original=copy.deepcopy(region)
 targets={i['name'] for i in region['instances'] if i['master']=='ot_hbm_svc_pc_ctrl_leaf'}
 assert targets==set(rows)
 for i in region['instances']:
  if i['name'] not in rows:continue
  r=rows[i['name']];assert i['master']==r['old_master'] and i['params']==r['old_params']
  assert r['clock_reference']['R_ps'] is None
  i.update(master=r['new_master'],params=r['params'],source=source_map[r['source']],rtl_deps=[v for k,v in source_map.items() if k!=r['source']],note='NONADOPTED H6 typed cfg candidate; explicit strap constants; phi-R unresolved')
  assert die.Rtl().ports(i['master'],i['source'],i['params'])==r['typed_ports']
  region['straps']+=copy.deepcopy(r['explicit_straps'])
 assert region['edges']==original['edges'] and region['clocks']==original['clocks']
 die.engine_region=lambda:region
 c=die.build(a.specs,out)
 assert not c['problems'],c['problems']
 assert set(c['instances'])==set(baseline['instances'])
 assert c['edges']==baseline['edges'],'Existing typed data edges changed'
 assert c['clock_resets']==baseline['clock_resets'],'Existing clock/reset references changed'
 for n in targets:
  old=baseline['instances'][n]['ports'];new=c['instances'][n]['ports']
  assert {k:v for k,v in new.items() if k not in ['pc_id','refresh_reload']}==old
  assert len([v for v in c['straps'] if v['inst']==n and v['port'] in ['pc_id','refresh_reload']])==2
 receipt=dict(schema='opentallas.pcctrl-cfg-engine-candidate.v1',adopted=False,generating_source=S,binding_sha256=sha(a.binding),base_contract_sha256=sha(a.source_contract),candidate_contract_sha256=sha(out/'contract.json'),die_sha256=sha(out/'die.v'),controllers=len(targets),preserved_edges=len(c['edges']),new_strap_bits=128*13,source_map=source_map,excluded_canonical_definitions=[SOURCE],SRAM_consumption='Select exactly one functional or blackbox definition for the SRAM master; both pinned alternatives are provenance only',dependency_sha256=m['source_dependencies_sha256'],clock_references={n:r['clock_reference'] for n,r in rows.items()},qualification='OPEN: H6 route/native plus final insertion.json compensation and source-bound view proof required')
 (out/'candidate_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print('PCCTRL_CFG_ENGINE_CANDIDATE PASS controllers128 straps1664 preserved_data_edges/clocks; NOT ADOPTED')
if __name__=='__main__':main()
