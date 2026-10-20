import hashlib,importlib.util,json,shutil,sys
from pathlib import Path
r=Path.cwd();root=r/'native2'
for p in ('tools','tools/hier_contract','tools/ref_tile'):sys.path.insert(0,str(root/p))
module=root/'tools/ref_tile/ref_tile_native_successor.py';shutil.copy2(r/'ref_tile_fullclosure.py',module)
sp=importlib.util.spec_from_file_location('candidate',module);R=importlib.util.module_from_spec(sp);sp.loader.exec_module(R)
result={}
for name in ('host_order_n32_1020','host_prompt_n32_1020'):
 e=R.SOURCE_NATIVE_RESET_LANDINGS[name]
 p=root/e['source'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(r/('order.sv' if 'order' in name else 'prompt.sv'),p)
 s=dict(top=e['top'],sources=[e['source'],*e.get('source_dependencies',{})],clock_port=e['clock'],params={},defines=[],
        reset_ports=e['reset_ports'],pin_regs=dict(enable=False,reason='exact source already registers every boundary'),
        reset_landing=dict(enable=True,stages=2,clock=e['clock'],source_native=name,
                           first_copies=e['first_copies'],copies=e['copies']))
 plan=R.reset_landing_plan(s)
 assert plan['enable'] is True and plan['stages']==2 and plan['reset_release_cycles']==2
 assert R.reset_landing_vars(s)==[] and R.reset_relay_split_vars(s)==[] and not R.pin_wrapper(s)
 result[name]={'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'plan':plan,'wrapper':False,
               'claim':'exact source/profile admission only; actual balanced mapped proof still required'}
(r/'actual_native.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
