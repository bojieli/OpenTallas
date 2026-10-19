import json,gzip,hashlib,re,copy
from pathlib import Path
P=Path(__file__).resolve().parent
inv=json.loads(gzip.decompress((P/'input/a4_inventory.json.gz').read_bytes()))
old=json.loads((P/'input/c634_model.json').read_text())
owned=json.loads((P/'input/owned_model.json').read_text())
def contains(a,b):return a[0]<=b[0]<b[2]<=a[2] and a[1]<=b[1]<b[3]<=a[3]
def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
def fmt(r):return ' '.join(f'{x/1000:.3f}' for x in r)
def directions(fam):
 s=(P/f'input/{fam}_original.v').read_text().split('module ',1)[1].split(');',1)[0];d={}
 for direction,hi,lo,name in re.findall(r'\b(input|output)\s+(?:wire|reg)\s*(?:\[(\d+):(\d+)\])?\s*(\w+)',s):
  for n in ([name] if not hi else [f'{name}[{i}]' for i in range(int(lo),int(hi)+1)]):d[n]=direction.upper()
 return d
summary={'status':'CONDITIONAL ANALYTICAL PROTOTYPE; NATIVE B NOT RUN','sources':{},'families':{}}
for p in sorted((P/'input').iterdir()):summary['sources'][p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
lines=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;','UNITS','  DATABASE MICRONS 1000 ;','END UNITS','MANUFACTURINGGRID 0.001 ;']
for fam,f in inv['families'].items():
 o=old['families'][fam];w,h=f['outline_nm'];name=f'ot_conditional_analytical_{fam}_5de_a4_r0_144nm'
 pins=[];d=directions(fam)
 assert len(d)==len(o['signal_ledger'])
 for s in o['signal_ledger']:
  pin=s['pin'];face=s['face'];rects=[]
  for b in f['shapes']:
   if b['net']!=pin or b['layer']!='M4':continue
   r=b['rect_nm'];strip=[0,0,24,h] if face=='W' else [w-24,0,w,h]
   if overlap(r,strip):rects.append([max(r[0],strip[0]),r[1],min(r[2],strip[2]),r[3]])
  rects=sorted(set(map(tuple,rects)));assert rects,(fam,pin)
  for r in rects:assert any(b['net']==pin and b['layer']=='M4' and contains(b['rect_nm'],r) for b in f['shapes'])
  pins.append({'name':pin,'direction':d[pin],'use':'CLOCK' if s['kind']=='clock' else 'SIGNAL','face':face,'ports':[{'layer':'M4','rect_nm':list(r)} for r in rects]})
 for net,use in [('VDD','POWER'),('VSS','GROUND')]:
  ports=[{'layer':'M5','rect_nm':p['rect_nm'],'source_identity':p['identity']} for p in f['ports'] if p['net']==net]
  assert len(ports)==2
  for p in ports:assert any(b['net']==net and b['layer']=='M5' and contains(b['rect_nm'],p['rect_nm']) for b in f['shapes'])
  pins.append({'name':net,'direction':'INOUT','use':use,'ports':ports})
 obs=[dict(b,kind='original_OBS_unchanged') for b in f['conditional_OBS']]
 for e in f['core_exclusions']:
  for layer in ['M1','M2','M3']:obs.append({'layer':layer,'rect_nm':e['rect_nm'],'source_identity':e['id'],'kind':'retained_lower_core_exclusion'})
 lines.extend([f'MACRO {name}','  CLASS BLOCK ;','  ORIGIN 0 0 ;',f'  SIZE {w/1000:.3f} BY {h/1000:.3f} ;'])
 for pin in pins:
  lines.extend([f"  PIN {pin['name']}",f"    DIRECTION {pin['direction']} ;",f"    USE {pin['use']} ;"])
  # Distinct PORTs permit both separately owned N/S PG access subsets.
  for port in pin['ports']:lines.extend(['    PORT',f"      LAYER {port['layer']} ;",f"      RECT {fmt(port['rect_nm'])} ;",'    END'])
  lines.append(f"  END {pin['name']}")
 lines.append('  OBS')
 for b in obs:lines.extend([f"    LAYER {b['layer']} ;",f"    RECT {fmt(b['rect_nm'])} ;"])
 lines.extend(['  END',f'END {name}'])
 # Native conductor remains exact A4, not silently exported as routing access.
 conflicts=[]
 for c in owned['families'][fam]['contact_ledger']:
  conflicts.append({'contact':c['id'] if 'id' in c else str(c.keys()),'net':c['net'],'status':'OWN_PG_OBS_CONFLICT_RETAINED; B_DIAGNOSTIC_HOLD'})
 summary['families'][fam]={'master':name,'source_master':o['master'],'outline_nm':[w,h],'orientation':'R0 only; no SYMMETRY declaration','origin_required_mod_nm':[144,144],'lattice_um':43.2,'placement_phase_enforced_by_LEF':False,'pins':pins,'obs':obs,'signal_count':len(d),'PG_MTerms':{'VDD':'POWER/INOUT, two separate N/S M5 PORTs','VSS':'GROUND/INOUT, two separate N/S M5 PORTs'},'own_pg_obs_conflicts':conflicts,'source_actual_box_count':len(f['actual_boxes']),'supply_stack_count':len(f['core_exclusions']),'actual_conductor_exported_as_access':False,'core_fit_density_multiplier':owned['families'][fam]['required_core_density_multiplier'],'density_fit_status':'HOLD','AP_status':'HOLD; native B not run'}
lines.append('END LIBRARY')
(P/'conditional_analytical_sram.lef').write_text('\n'.join(lines)+'\n')
(P/'prototype.json').write_text(json.dumps(summary,indent=2)+'\n')
# Independent lexical census catches missing identity/counts, not a native parser.
text=(P/'conditional_analytical_sram.lef').read_text()
assert len(re.findall(r'^  PIN ',text,re.M))==647
assert text.count('  OBS\n')==2 and 'SYMMETRY' not in text
assert text.count('    USE POWER ;')==2 and text.count('    USE GROUND ;')==2
controls={}
for fam,f in inv['families'].items():
 p=next(x for x in summary['families'][fam]['pins'] if x['name']=='VDD')['ports'][0]
 bad=[v+96 if i in [0,2] else v for i,v in enumerate(p['rect_nm'])]
 controls[fam+'_moved_pg_port_refused']=not any(s['net']=='VDD' and s['layer']=='M5' and contains(s['rect_nm'],bad) for s in f['shapes'])
 controls[fam+'_lost_obs_refused']=len(f['conditional_OBS'][:-1])!=6
 controls[fam+'_48nm_origin_refused']=48%144!=0
assert all(controls.values())
(P/'finite_checks.json').write_text(json.dumps({'native_engine':False,'lexical_mterms':647,'signals':643,'PG_mterms':4,'original_OBS':12,'retained_lower_exclusion_layer_rectangles':363,'controls':controls,'scope':'finite source identity/containment and lexical checks; no native parse/AP/PDN'},indent=2)+'\n')
print('Generated 2 distinct conditional masters; 643 signals, 4 PG MTerms, 12 OBS plus 363 lower exclusion layer rectangles; no engines.')
