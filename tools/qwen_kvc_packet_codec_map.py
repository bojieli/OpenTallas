#!/usr/bin/env python3
import argparse,gzip,json,re,subprocess,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--library-root',type=Path,required=True);p.add_argument('--yosys',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);r=Path(__file__).resolve().parents[1]
b=a.library_root/'results/uarch/topk_station_SSFF_cell_model_20261002/inputs';seq=b/'asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib';inv=gzip.decompress((b/'asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz').read_bytes()).decode();simple=gzip.decompress((b/'asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz').read_bytes()).decode();lib=a.out/'comb.lib';lib.write_text(inv[:inv.rfind('}')]+simple[simple.index('cell ('):simple.rfind('}')]+ '\n}\n');areas={n:float(v) for t in [seq.read_text(),inv,simple] for n,v in re.findall(r'cell\s*\(([^)]+)\)\s*\{.*?area\s*:\s*([0-9.eE+-]+)',t,re.S)};rows=[]
for parallel in [False,True]:
 for name in ['encode','decode']:
  suffix='_parallel' if parallel else '';top='ot_qwen_kvc_packet_'+name+suffix;src=r/('rtl/physical/ot_qwen_kvc_packet_codec'+suffix+'.sv');net=a.out/(top+'.json')
  script=f'read_verilog -sv {src}; chparam -set ENABLE 1 {top}; synth -top {top}; dfflibmap -liberty {seq}; abc -liberty {lib}; opt_clean; read_liberty -lib {seq}; read_liberty -lib {lib}; check -assert; write_json {net}'
  z=subprocess.run([a.yosys,'-Q','-T','-p',script],text=True,capture_output=True);(a.out/(top+'.log')).write_text(z.stdout+z.stderr);assert z.returncode==0,z.stderr
  mod=json.loads(net.read_text())['modules'][top];cells=mod['cells'];unknown=[c['type'] for c in cells.values() if c['type'] not in areas];assert not unknown,unknown
  drivers={bit:c for c in cells.values() if not c['type'].startswith('DFF') for port,dr in c['port_directions'].items() if dr=='output' for bit in c['connections'][port]};cache={}
  def depth(bit):
   if bit in cache:return cache[bit]
   c=drivers.get(bit)
   if c is None:return 0
   v=1+max([depth(b) for port,dr in c['port_directions'].items() if dr=='input' for b in c['connections'][port]] or [0]);cache[bit]=v;return v
  ends=[bit for c in cells.values() if c['type'].startswith('DFF') for bit in c['connections'].get('D',[])];row=dict(module=top,area_um2=sum(areas[c['type']] for c in cells.values()),FFs=sum(c['type'].startswith('DFF') for c in cells.values()),max_input_to_D_cell_levels=max(map(depth,ends)),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),mapped_sha256=hashlib.sha256(net.read_bytes()).hexdigest());rows.append(row);print(json.dumps(row),flush=True)
x={'rows':rows,'scope':'Actual production ASAP7 SS mapped cellarea and logicdepth only. Wire/fanout/clock/SSFF timing not qualified.','tool':subprocess.check_output([a.yosys,'-V'],text=True).strip()};(a.out/'result.json').write_text(json.dumps(x,indent=2)+'\n')
