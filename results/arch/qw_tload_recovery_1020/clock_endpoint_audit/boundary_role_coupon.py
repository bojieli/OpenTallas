from pathlib import Path
import re,json,gzip,hashlib
D=Path('/srv/opentallas-scratch/claude/ref_gate/qfd_dv_slice_tload_ns4-20261020-013443');out=D/'clock_endpoint_audit';s=json.loads((D/'native_grt/summary.json').read_text());actual=set(s['master_roles'])
def blocks(t,k):
 for m in re.finditer(r'\b'+k+r'\s*\(([^)]*)\)\s*\{',t):
  a=i=m.end();n=1
  while n:n+=(t[i]=='{')-(t[i]=='}');i+=1
  yield m[1].strip('" '),t[a:i-1]
def att(t,k):
 m=re.search(r'\b'+k+r'\s*:\s*"?([^";]+)"?\s*;',t);return m[1].strip()if m else None
seq={};libs=[]
for lp in Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM').glob('*RVT_TT*.lib*'):
 t=gzip.open(lp,'rt').read()if lp.suffix=='.gz'else lp.read_text()
 for mn,body in blocks(t,'cell'):
  if mn not in actual:continue
  f=list(blocks(body,'ff'))
  if f:
   seq[mn]={'ff_variables':f[0][0],'clocked_on':att(f[0][1],'clocked_on'),'next_state':att(f[0][1],'next_state'),'clear':att(f[0][1],'clear'),'preset':att(f[0][1],'preset'),'lib':str(lp),'lib_sha256':hashlib.sha256(lp.read_bytes()).hexdigest(),'pins':s['master_roles'][mn]['pins']}
macro={};mdir=D/'src/physical/asap7_memory_macros/ot_rom_4096x266_m8'
for c in ['tt','ff','ss']:
 p=mdir/f'ot_rom_4096x266_m8_{c}.lib';t=p.read_text();cell=list(blocks(t,'cell'));assert len(cell)==1 and cell[0][0]=='ot_rom_4096x266_m8';pins=[]
 for name,body in list(blocks(cell[0][1],'pin'))+list(blocks(cell[0][1],'bus')):
  arcs=[{'type':att(a,'timing_type'),'related_pin':att(a,'related_pin')}for _,a in blocks(body,'timing')]
  pins.append({'pin':name,'direction':att(body,'direction'),'clock':att(body,'clock'),'arcs':arcs})
 macro[c]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'cell':cell[0][0],'pins':pins,'has_max_clock_tree_path':'max_clock_tree_path'in t,'has_insertion_json':(mdir/'insertion.json').exists(),'reference_basis':'realmemoryLib definesdata readclkQ andaddr/ce setuphold directlyat clk; no hiddenchildCTSreference. Rawphysicalclk pinarrival is0reference, internalreadlatency/delay remainsfiniteLibSTA.'}
r={'sequential_actual_lib_roles':seq,'macro_actual_lib_roles':macro,'native_odb_sha256':s['odb_sha256'],'scope':'Role/clockarc provenance only; no behavioral/native sequential functionalproof.'};(out/'actual_lib_roles.json').write_text(json.dumps(r,indent=2)+'\n');print('actualLibSEQ',sorted(seq),'macroTThasclockpins',[(x['pin'],x['clock'],x['arcs'])for x in macro['tt']['pins']if x['clock']or x['arcs']])
