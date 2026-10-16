#!/usr/bin/env python3
"""Actual full128-row c9 / opt-in host RVT mapping and per-root FF census.

Area/count evidence only. No outline, phase, pin or physical-view inheritance.
"""
import argparse,collections,hashlib,json,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--top',choices=['dsfd_stage_seq_static_c9','dsfd_host_c'],required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[2];out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
static=['ot_s81_fixed_issue.sv','ot_s81_fixed_mailbox.sv','dsfd_stage_seq_static_c.sv','dsfd_stage_seq_static_c9.sv','ot_s81_pq_boot_control.sv']
host=['rtl/dsrom_sys/s81_ingest/dsfd_host_c.sv','rtl/lib/ot_async_fifo.sv','rtl/lib/ot_reset_sync.sv','rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv','rtl/lib/ot_rst_relay.sv','rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv','rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv','rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv','physical/rom_host_ingest/rtl/dsfd_host.sv','rtl/hdc/ingest/ot_rom_host_ingest.sv','rtl/link/ot_link_afifo.sv','rtl/hdc/ingest/ot_hdc_kv_ingest.sv','rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv']
sources=[root/'rtl/dsrom_sys/s81_static_control'/x for x in static] if a.top.endswith('c9')else[root/x for x in host]
libs=sorted(Path('/home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM').glob('*RVT_TT_nldm*.lib'));assert len(libs)==5
seq=next(x for x in libs if 'SEQ_' in x.name);flags=' '.join('-liberty '+str(x)for x in libs)
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
provenance=dict(sources_sha256={str(x.relative_to(root)):sha(x)for x in sources},library_sha256={x.name:sha(x)for x in libs},script_sha256=sha(Path(__file__)),yosys=subprocess.check_output(['yosys','-V'],text=True).strip(),top=a.top,parameters={'NOPS':128}if a.top.endswith('c9')else{'NS':1},scope='source-pinned mapped area and clocks only; no route/native pin/clock/parent qualification')
(out/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
y='read_verilog -sv -DSYNTHESIS -DDSFD_HOST_C_STATIC -DDSFD_HOST_PQ_BOOT '+' '.join(map(str,sources))+'\n'
y+=f'hierarchy -check -top {a.top}\nsynth -top {a.top} -flatten -noabc\n'
y+=''.join('read_liberty -lib '+str(x)+'\n'for x in libs)
y+=f'dfflibmap -liberty {seq}\nabc {flags} -D 833\nclean\ncheck -assert\nstat {flags}\nwrite_json {out}/mapped.json\n'
(out/'map.ys').write_text(y)
with(out/'map.log').open('w')as f:rc=subprocess.run(['yosys','-s',str(out/'map.ys')],stdout=f,stderr=subprocess.STDOUT).returncode
if rc:raise SystemExit(rc)
m=json.loads((out/'mapped.json').read_text())['modules'][a.top]
areas={}
for lib in libs:
 for name,body in re.findall(r'cell\s*\(\s*(\S+)\s*\)\s*\{(.*?)(?=\n  cell|\Z)',lib.read_text(),re.S):
  q=re.search(r'\barea\s*:\s*([\d.]+)',body)
  if q:areas[name]=float(q[1])
cells=collections.Counter(c['type']for c in m['cells'].values()if c['type']!='$scopeinfo');unknown={k:v for k,v in cells.items()if k not in areas}
roots={name+(f'[{i}]'if len(port['bits'])>1 else''):bit for name,port in m['ports'].items()if name in ['ck','ckv','ck_ingest']for i,bit in enumerate(port['bits'])};ff=collections.Counter();unrooted=[]
for name,c in m['cells'].items():
 if 'DFF' not in c['type']:continue
 clk=c['connections'].get('CLK',c['connections'].get('CK',[]))
 match=[n for n,b in roots.items()if clk==[b]]
 if len(match)!=1:unrooted.append(dict(name=name,type=c['type'],clock=clk))
 else:ff[match[0]]+=1
result=dict(provenance=provenance,ports={n:dict(direction=v['direction'],width=len(v['bits']))for n,v in m['ports'].items()},total_pin_bits=sum(len(v['bits'])for v in m['ports'].values()),cells=dict(cells),cell_count=sum(cells.values()),mapped_area_um2=sum(areas.get(k,0)*v for k,v in cells.items()),mapped_ff_per_clock=dict(ff),unrooted_ff=unrooted,unknown_cells=unknown,new_rom_macros=0,new_sram_macros=0,physical_qualified=False)
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ['provenance','ports','cells','unrooted_ff']},indent=2))
if unknown or unrooted:raise SystemExit(2)
