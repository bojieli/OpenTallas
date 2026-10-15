#!/usr/bin/env python3
"""Generic RTL state census only; run through ot-run on frozen staged source."""
import hashlib,json,pathlib,subprocess,sys
p=pathlib.Path.cwd();kind=sys.argv[1]
assert kind in ('bank','vector','ctrl')
top={'bank':'ot_qwen_xdelivery_ack_bank','vector':'ot_qwen_xdelivery_ack_vector','ctrl':'ot_qwen_xdelivery_lifetime_ctrl'}[kind]
params={'ENABLE':1,'N':48,'SEQ_W':40,'COUNT_W':7} if kind!='ctrl' else {'ENABLE':1,'TILES':768,'BANKS':16,'TOKEN_W':16}
source=p/'ot_qwen_xdelivery_lifetime.sv'
commands=['read_verilog -sv '+str(source),'hierarchy -top '+top+' '+' '.join('-chparam %s %s'%x for x in params.items()),'proc','opt','memory_map','opt','stat','write_json '+kind+'.json']
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
 'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'top':top,'params':params,
 'command':cmd,'yosys':subprocess.check_output(['yosys','-V'],text=True).strip(),
 'sequential_Q_bits':qbits,'cell_types':types,'ports':{k:{'direction':v['direction'],'bits':len(v['bits'])} for k,v in j['ports'].items()}}
(p/(kind+'_census_receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt),flush=True)
