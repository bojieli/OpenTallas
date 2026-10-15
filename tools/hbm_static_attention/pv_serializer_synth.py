#!/usr/bin/env python3
"""Pinned ASAP7 TT logic/macro inventory; excludes CTS, placement and wires."""
import argparse,hashlib,json,subprocess,re
from collections import Counter,defaultdict
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--profile',choices=['baseline','D','group_mux','tile','registered_gather'],required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
r=Path.cwd();out=a.out;out.mkdir(parents=True,exist_ok=False)
libs=sorted((Path.home()/'.local/opentallas-pdk-asap7/lib/NLDM').glob('*_RVT_TT_*.lib'))
assert len(libs)==5,'five pinned RVT TT library groups required'
body=[]
for f in libs:
 s=f.read_text();body.append(s[s.index('{')+1:s.rindex('}')])
lib=out/'combined.lib';lib.write_text('library (attn_pv_native_tt) {\n'+'\n'.join(body)+'\n}\n')
top={'baseline':'ot_hbm_attn_pv_serializer','D':'ot_hbm_attn_pv_serializer_local','tile':'ot_hbm_attn_pv_serializer_local_tile','group_mux':'ot_hbm_attn_pv_group_mux','registered_gather':'ot_hbm_attn_pv_group_gather_registered'}[a.profile]
src=['physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1_bb.v','rtl/hdc/v41x/static/'+('ot_hbm_attn_pv_serializer_local' if a.profile=='tile' else top)+'.sv']
rec=dict(profile=a.profile,qualification=False,physical_qualified=False,
 scope='Mapped actual TT standardcells plus native macro count; excludes CTS, clock buffers, physical wires, timing/cut/routing and throughput qualification',
 source_sha256={f:hashlib.sha256((r/f).read_bytes()).hexdigest() for f in src},library_sha256={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in libs})
(out/'source.json').write_text(json.dumps(rec,indent=2)+'\n')
y=out/'synth.ys';y.write_text('\n'.join([
 'read_verilog -sv '+' '.join(str(r/f) for f in src),
 'hierarchy -check -top '+top,
 'synth -top '+top+' -flatten -run coarse',
 'tee -o '+str(out/'coarse_stat.json')+' stat -json',
 'synth -top '+top+' -flatten -run fine:check',
 'dfflibmap -liberty '+str(lib),'abc -liberty '+str(lib),
 'clean','read_liberty -lib '+str(lib),'stat -liberty '+str(lib),
 'write_json '+str(out/'mapped.json'),'write_verilog -noattr '+str(out/'mapped.v')])+'\n')
with (out/'synth.log').open('w') as log:
 cp=subprocess.run([str(Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'),'-s',str(y)],stdout=log,stderr=subprocess.STDOUT)
rec['returncode']=cp.returncode
if cp.returncode==0:
 m=json.loads((out/'mapped.json').read_text())['modules'][top]
 count=Counter(c['type'] for c in m['cells'].values())
 clock=Counter();fan=Counter();macro_count=0
 for c in m['cells'].values():
  ismacro=c['type']=='ot_sram_1r1w_32x128_m1';macro_count+=ismacro
  for name,bits in c['connections'].items():
   if c.get('port_directions',{}).get(name)=='input':
    for bit in bits:
     if isinstance(bit,int):fan[bit]+=1
   if name in ('CLK','clk'):
    for bit in bits:
     if isinstance(bit,int):clock[bit]+=1
 rec['cell_types']=dict(count);rec['macro_count']=macro_count
 text=(out/'synth.log').read_text();area=re.findall(r'Chip area for module.*?: ([0-9.]+)',text)
 rec['mapped_standardcell_area_um2']=float(area[-1]) if area else None
 rec['mapped_clock_endpoints']={name:[dict(bit=b,sinks=clock[b]) for b in port['bits']] for name,port in m['ports'].items() if name in ('clk','bank_clk')}
 rec['highest_input_fanout']=dict(fan.most_common(20))
 assert macro_count=={'D':2048,'baseline':128,'tile':64,'group_mux':0,'registered_gather':0}[a.profile]
 rec['status']='PASS mapped TT inventory; physical clock qualification OPEN'
else:rec['status']='FAIL synth; inspect exact log'
(out/'record.json').write_text(json.dumps(rec,indent=2)+'\n');raise SystemExit(cp.returncode)
