#!/usr/bin/env python3
"""Generic RTL state census only; run through ot-run on frozen staged source."""
import hashlib,json,pathlib,subprocess,sys
p=pathlib.Path.cwd();kind=sys.argv[1]
assert kind in ('provenance','row')
top={'provenance':'ot_qfd_vm_producer_lease_provenance','row':'ot_qfd_vm_producer_row_binding_seq40'}[kind]
params={'ENABLE':1,'MUT':0} if kind=='provenance' else {'LAW':8,'MUT':0}
sources=[p/'ot_qfd_vm_producer_lease_seq40.sv',p/'ot_qfd_vm_producer_lease_provenance.sv']
commands=['read_verilog -sv '+' '.join(map(str,sources)),'hierarchy -top '+top+' '+' '.join('-chparam %s %s'%x for x in params.items()),'proc','opt','flatten','opt','memory_map','opt','stat','write_json '+kind+'.json']
cmd=['yosys','-p','; '.join(commands)]
with (p/(kind+'_census.log')).open('w') as f:
 r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
if r.returncode:raise SystemExit(r.returncode)
j=json.loads((p/(kind+'.json')).read_text())['modules'][top]
types={};qbits=0
for cell in j['cells'].values():
 typ=cell['type'];types[typ]=types.get(typ,0)+1
 if 'dff' in typ.lower():qbits+=len(cell['connections']['Q'])
receipt={'status':'GENERIC_POST_PROC_OPT_MEMORY_MAP_CENSUS_NOT_MAPPED_AREA_OR_CTS',
 'sources':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in sources},'top':top,'params':params,
 'command':cmd,'yosys':subprocess.check_output(['yosys','-V'],text=True).strip(),
 'sequential_Q_bits':qbits,'cell_types':types,'ports':{k:{'direction':v['direction'],'bits':len(v['bits'])} for k,v in j['ports'].items()}}
(p/(kind+'_census_receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt),flush=True)
