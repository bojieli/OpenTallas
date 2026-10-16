#!/usr/bin/env python3
"""Map actual combined HC source/CPIN logic; real ROM is retained as a macro.

The blackbox is an area-only view of the exact functional macro's header. This
netlist cannot be used for native simulation. Its body/LEF remain source-pinned.
"""
import argparse,collections,hashlib,json,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parents[2];out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
sources=['rtl/dsrom_sys/s81_static_control/ot_s81_fixed_mailbox.sv','rtl/dsrom_sys/s81_static_control/ot_s81_hc_programme_source.sv','rtl/dsrom_sys/s81_static_control/ot_s81_hc_programme_endpoint.sv','rtl/dsrom_sys/s81_suhc/static/ot_s81_hc_cpin_calendar.sv','rtl/dsrom_sys/s81_suhc/static/ot_s81_hc_programme_cpin.sv']
macro='physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v'
raw=(root/macro).read_text();header=raw[raw.index('module '):raw.index(');')+2].replace('parameter string','parameter')
(out/'rom_area_only.v').write_text('(* blackbox *)\n'+header+'\nendmodule\n')
transformed=[]
for i,s in enumerate(sources):
 q=out/f'source{i}.sv';q.write_text((root/s).read_text().replace('parameter string','parameter'));transformed.append(str(q))
libs=sorted(Path('/home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM').glob('*RVT_TT_nldm*.lib'));assert len(libs)==5
seq=next(p for p in libs if 'SEQ_' in p.name)
top='ot_s81_hc_programme_cpin'
y=f'read_verilog -lib {out}/rom_area_only.v\nread_verilog -sv -DSYNTHESIS '+' '.join(transformed)+'\n'
y+=f'hierarchy -check -top {top}\nsynth -top {top} -flatten -noabc\n'
y+=''.join('read_liberty -lib '+str(p)+'\n'for p in libs)
y+=f'dfflibmap -liberty {seq}\nabc '+' '.join('-liberty '+str(p)for p in libs)+f' -D 833\nclean\nwrite_json {out}/mapped.json\nstat\n'
(out/'map.ys').write_text(y)
with (out/'map.log').open('w')as f:r=subprocess.run(['yosys','-s',str(out/'map.ys')],stdout=f,stderr=subprocess.STDOUT)
if r.returncode:raise SystemExit(r.returncode)
m=json.loads((out/'mapped.json').read_text())['modules'][top]
areas={}
for lib in libs:
 for name,body in re.findall(r'cell\s*\(\s*(\S+)\s*\)\s*\{(.*?)(?=\n  cell|\Z)',lib.read_text(),re.S):
  v=re.search(r'\barea\s*:\s*([\d.]+)',body)
  if v:areas[name]=float(v[1])
counts=collections.Counter(c['type']for c in m['cells'].values());ff=collections.Counter();unknown=[]
roots={p['bits'][0]:n for n,p in m['ports'].items()if n in ('stream_ck','sk')}
for n,c in m['cells'].items():
 if 'DFF' in c['type']:
  ck=c['connections'].get('CLK',c['connections'].get('CK',[]));ff[roots.get(ck[0],str(ck))]+=1
 elif c['type']not in areas and 'ot_rom_4096x72_m8'not in c['type']:unknown.append(c['type'])
rec=dict(top=top,params={'COMMAND_POST_AGES':1},standard_cell_area_um2=sum(areas.get(k,0)*v for k,v in counts.items()),mapped_ff_per_clock=dict(ff),macro_count=sum(v for k,v in counts.items()if 'ot_rom_4096x72_m8'in k),macro_area_um2=38.016*62.910,external_ports={n:dict(width=len(v['bits']),direction=v['direction'])for n,v in m['ports'].items()},unknown_cells=unknown,source_sha256={s:hashlib.sha256((root/s).read_bytes()).hexdigest()for s in sources+[macro]},scope='Mapped body/pin sizing only; no timing/clock/tree/place/route or native completeness proof')
(out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps({k:v for k,v in rec.items()if k not in ('external_ports','source_sha256')},indent=2))
if unknown:raise SystemExit(2)
