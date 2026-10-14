import json,sys,hashlib
from pathlib import Path
p=Path(sys.argv[1]);design=json.loads(p.read_text());mods=design['modules'];top='ot_hdc_vstream_lane_h';counts={};modules={};mem=[];macros=[]
portbits={b:n for n,r in mods[top]['ports'].items()for b in r['bits'] if n=='clk'}
def walk(name,path,connections):
 m=mods[name];bind={}
 for port,info in m['ports'].items():
  if port in connections:
   for bit,external in zip(info['bits'],connections[port]):bind[bit]=external
 def net(bit):return bind.get(bit,f'{path}::bit{bit}')
 for n,c in m.get('cells',{}).items():
  t=c['type'];cp=path+'/'+n
  if t in mods and int(str(mods[t].get("attributes",{}).get("blackbox","0")),2):
   macros.append({"path":cp,"master":t,"clock_source":[net(b)for b in c["connections"].get("clk",[])],"storage_bits":32768,"physical_view":"physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2","physical_qualification":False});continue
  if t in mods:
   walk(t,cp,{k:[net(b)for b in v]for k,v in c['connections'].items()});continue
  if t.startswith('$_DFF')or t.startswith('$_SDFF')or t.startswith('$_ADFF')or t.startswith('$_DLATCH')or t in ['$dff','$dffe','$adff','$adffe','$sdff','$sdffe','$aldff','$aldffe']:
   q=len(c['connections'].get('Q',[]));clock=c['connections'].get('C',c['connections'].get('CLK',[]));root=net(clock[0])if clock else'UNKNOWN_LATCH_CLOCK';counts[root]=counts.get(root,0)+q;modules[path]=modules.get(path,0)+q
  if t.startswith('$mem'):mem.append({'path':cp,'type':t,'params':c.get('parameters',{})})
walk(top,top,{'clk':['clk']})
r={'schema':'qwen-native-head-generic-retained-census-v1','top':top,'params':{'WR':16,'AW':24,'NW':18,'KV_FP8':1,'ML':15,'RD':2,'QLA':int(sys.argv[3]),'QLM':int(sys.argv[4]),'body_ML':21},'production_profile':sys.argv[3:5]==['4','5'],'flow':'Yosys0.68 synth-noabc-noshare; genericmapped FF census, no timing/power/physical qualification','clock_roots':counts,'total_FF_bits':sum(counts.values()),'hierarchy_FF_bits':modules,'unmapped_memory':mem,'real_macro_instances':macros,'design_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'root15k_rule_debt':any(n>15000 for n in counts.values()),'slots_PG_pins_phase':'UNASSIGNED','actual300_80':'not measured; no exception implied'}
Path(sys.argv[2]).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k]for k in ['production_profile','params','clock_roots','total_FF_bits','root15k_rule_debt']}))
assert not mem,'Unmapped memory prevents complete state census'
