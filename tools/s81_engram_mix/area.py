#!/usr/bin/env python3
"""Map a physical Engram leaf to real ASAP7 RVT TT cells; report LEF area.
This is a cell-area census only, never route/STA/DRC qualification.
"""
import sys,subprocess,json,hashlib,re,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/s81_suhc'))
import hc_gate as H
blackboxes=[x.split('=',1)[1] for x in sys.argv if x.startswith('--blackbox=')]
leaf=sys.argv[1];out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
extras=['rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv','rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv','rtl/dsrom_sys/engram/mix/dsfd_engram_mix_c.sv','rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_c.sv','rtl/dsrom_sys/s81_ctrl/ot_s81_slab_ep.sv','rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv','rtl/lib/ot_async_fifo.sv','rtl/lib/ot_reset_sync.sv']
src=[ROOT/x for x in H.FP['rtl']+[x for x in H.RTL if '/hdc/' in x]+extras]
pdk=Path('/home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM');libs=sorted(pdk.glob('*RVT_TT_nldm*.lib'));assert len(libs)==5,libs
seq=next(p for p in libs if 'SEQ_' in p.name)
libflags=' '.join('-liberty '+str(p) for p in libs)
blackbox_ys=''.join('blackbox '+x+'\n' for x in blackboxes)
ys='read_verilog -sv -DSYNTHESIS '+' '.join(map(str,src))+'\n'+blackbox_ys+f'hierarchy -check -top {leaf}\nsynth -top {leaf} -flatten -noabc\ndfflibmap -liberty {seq}\nabc {libflags} -D 833\nclean\nstat {libflags}\nwrite_json {out}/mapped.json\n'
(out/'map.ys').write_text(ys)
(out/'sources.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in src},indent=2)+'\n')
if '--report-only' not in sys.argv:
 with (out/'map.log').open('w') as log:r=subprocess.run(['yosys','-s',str(out/'map.ys')],stdout=log,stderr=subprocess.STDOUT)
 if r.returncode:sys.exit(r.returncode)
z=json.loads((out/'mapped.json').read_text());cells=collections.Counter(c['type'] for c in z['modules'][leaf]['cells'].values() if c['type']!='$scopeinfo' and not z['modules'].get(c['type'],{}).get('attributes',{}).get('blackbox'))
metadata=sum(c['type']=='$scopeinfo' for c in z['modules'][leaf]['cells'].values())
lef=ROOT/'asap7_1x.lef';text=lef.read_text();areas={}
for m in re.finditer(r'MACRO\s+(\S+)\s+(.*?)(?=\nMACRO|\Z)',text,re.S):
 q=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',m.group(2))
 if q:areas[m.group(1)]=float(q[1])*float(q[2])
unknown={t:n for t,n in cells.items() if t not in areas};area=sum(areas.get(t,0)*n for t,n in cells.items())
res={'top':leaf,'excluded_blackbox_modules':blackboxes,'status':'PASS' if not unknown else 'UNMAPPED','scope':'ABC RVT TT mapping and actual 1x LEF cell area only; not placed/routed area or timing qualification','abc_target_ps':833,'cell_area_um2':area,'cell_count':sum(cells.values()),'excluded_nonhardware_scope_metadata':metadata,'unmapped_cells':unknown,'cells':dict(cells),'lef_sha256':hashlib.sha256(lef.read_bytes()).hexdigest(),'libraries_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in libs}}
(out/'area.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({k:v for k,v in res.items() if k not in ('cells','libraries_sha256')},indent=2));sys.exit(0 if not unknown else 1)
