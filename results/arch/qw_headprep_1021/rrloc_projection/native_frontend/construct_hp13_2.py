import sys,json,re,hashlib
from pathlib import Path
sys.path.insert(0,'tools/qwen_dv');import ctlm6_bound_macro as B
O=Path('/work/constructed2');O.mkdir(exist_ok=True);raw=Path('/work/generic/parent.json').read_bytes();d=json.loads(raw);manifest=json.load(open('physical_abstracts.json'));known={m['module']:m for m in manifest};contracts={}
for name,mod in d['modules'].items():
 if not int(str(mod.get('attributes',{}).get('blackbox','0')),2):continue
 if name not in known:raise ValueError('UNOWNED BLACKBOX '+name)
 actual=(Path(known[name]['source'])).read_bytes()
 assert hashlib.sha256(actual).hexdigest()==known[name]['source_sha256']
 string_params=re.findall(r'parameter\s+string\s+(\w+)',actual.decode())
 contracts[name]=dict(kind='physical_macro',source_sha256=known[name]['source_sha256'],
   ports={p:dict(direction=row['direction'],width=len(row['bits']),clock=p in ('ck','clk','CLK','CK','ck_head','ck_pm0','ck_pm1')) for p,row in mod['ports'].items()},
   parameter_types={p:'string' for p in string_params})
typ='ot_qfd_tt_ctlm_static_hr_safe32_native32_1r'
assert typ in contracts
params={'STAGE_ME':1,'SEGCAL':1}
source_contract={'status':'SOURCE_BOUND_NEW_CHILD_VIEW_UNQUALIFIED','top':typ,'params':params,'source_sha256':known[typ]['source_sha256']}
specpath=Path('h16za_source_contract.json');specpath.write_text(json.dumps(source_contract,indent=2)+'\n')
contracts[typ].update(simulation_parameters={k:format(v,'032b') for k,v in params.items()},simulation_source={'path':str(specpath),'sha256':hashlib.sha256(specpath.read_bytes()).hexdigest()})
(O/'contracts.json').write_text(json.dumps(contracts,indent=2)+'\n')
try:
 rtl,helpers,record=B.build(raw,'qfd_tt_ctlm_dv_lpf_hp13_lp','qfd_tt_ctlm_dv_hp13_rrloc_native32',load_cap=32,transparent_inverters=True,retain_mux=True,shared_helpers=True,retain_all_comb=True,fuse_ao=True,macro_contracts=contracts)
except Exception as error:
 tb=error.__traceback__
 while tb and tb.tb_frame.f_code.co_name!='build':tb=tb.tb_next
 if tb:
  st=tb.tb_frame.f_locals;cs=st.get('cells',{});b=st.get('b');terms=st.get('terminal_sinks',{}).get(b,[])
  summary=dict(error=str(error),bit=b,terms=[dict(cost=x[0],kind=x[1],cell=x[2],pin=x[3],index=x[4],type=cs.get(x[2],{}).get('type')) for x in terms],iterations=st.get('iteration'),cell_count=len(cs))
  (O/'construct_failure.json').write_text(json.dumps(summary,indent=2)+'\n');print('FAIL_SUMMARY',len(terms),st.get('iteration'),len(cs),flush=True)
 raise
(O/'qfd_tt_ctlm_dv_hp13_rrloc_native32.sv').write_text(rtl);(O/'qfd_tt_ctlm_dv_hp13_rrloc_helpers.sv').write_text('\n'.join(helpers)+'\n');(O/'record.json').write_text(json.dumps(record,indent=2)+'\n')
print('CTLM_CONSTRUCT',record['original_cells'],record['final_cells'],'passes',record['passes'],'macros',len(record['retained_macro_terminals']),'added',record['added_by_type'])
