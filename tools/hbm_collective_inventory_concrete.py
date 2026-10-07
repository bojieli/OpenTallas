#!/usr/bin/env python3
"""Concrete-top successor avoiding Yosys top chparam re-elaboration bug."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PKG='rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv'
BANK='rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv'
CDC='rtl/hbm_accel/collective_cdc_20261007/ot_hbm_collective_protected_cdc.sv'
FIFO='rtl/hbm_accel/collective_full_20261007/ot_hbm_collective_packet_fifo.sv'
BB='physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2_bb.v'
FUNCS={'ot_gpu_w6_secded_pkg':['encode64','decode64'],'ot_hbm_w2_boundary_pkg':['raw64','check72']}
def normalize(text):
 # Functions in package definitions keep their own local names; only imported
 # module bodies are qualified. Originals remain byte-identical.
 pos=text.find('module ')
 if pos<0:return text
 head,body=text[:pos],text[pos:]
 for pkg,names in FUNCS.items():
  if 'import '+pkg+'::*;' in body:
   body=body.replace('import '+pkg+'::*;','')
   for name in names:body=re.sub(r'(?<!\w)(?<!::)'+name+r'\s*\(',pkg+'::'+name+'(',body)
 return head+body

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--block',choices=['cdc','cdc_refill','packet'],required=True);p.add_argument('--yosys',default=str(Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'));p.add_argument('--prepare-only',action='store_true');a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 selected_cdc=CDC.replace('.sv','_refill.sv') if a.block=='cdc_refill' else CDC
 files=[PKG,BANK,selected_cdc] if a.block.startswith('cdc') else [PKG,BB,FIFO]
 pins={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files};private=[]
 for i,f in enumerate(files):
  dest=a.out/(str(i)+'_'+Path(f).name);dest.write_text(normalize((ROOT/f).read_text()));private.append(dest)
 top=('ot_hbm_collective_protected_cdc_refill' if a.block=='cdc_refill' else 'ot_hbm_collective_protected_cdc') if a.block.startswith('cdc') else 'ot_hbm_collective_packet_fifo'
 if a.block.startswith('cdc'):
  wrapper=a.out/'inventory_top.sv'
  wrapper.write_text(f"module inventory_top(input wclk,wrst_n,in_v,input [544:0] in_d,output in_r,input rclk,rrst_n,out_r,output out_v,output [544:0] out_d,output wempty,rempty,fault); {top} #(.ENABLE(1),.W(545),.AW(6)) u_inventory(.wclk(wclk),.wrst_n(wrst_n),.in_v(in_v),.in_r(in_r),.in_d(in_d),.rclk(rclk),.rrst_n(rrst_n),.out_v(out_v),.out_r(out_r),.out_d(out_d),.wempty(wempty),.rempty(rempty),.fault(fault)); endmodule\n")
  private.append(wrapper);top='inventory_top'
 hierarchy=f'hierarchy -check -top {top}' + ('' if a.block.startswith('cdc') else ' -chparam ENABLE 1')
 script=a.out/'inventory.ys';script.write_text('\n'.join(['read_verilog -sv '+str(f) for f in private]+[hierarchy,f'flatten','proc','opt','memory_map','opt','techmap','opt','check',f'tee -o {a.out / "stat.json"} stat -json',f'write_json {a.out / "netlist.json"}'])+'\n')
 manifest=dict(block=a.block,top=top,source_sha256=pins,normalized_sha256={str(f.name):hashlib.sha256(f.read_bytes()).hexdigest() for f in private},normalization='Replace module wildcard imports with explicit package::function references; CDC concrete top instantiates ENABLE1/W545/AW6 instead of hierarchy top-chparam; no source RTL edits',command=[a.yosys,'-Q','-T','-s',str(script)],scope='GenericmappedFF/mux and retainedmacro inventory only; not standardcell mapping/area/clock closure')
 (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 if a.prepare_only:print('PREPARED_ONLY structural inventory');return 0
 manifest['tool_version']=subprocess.check_output([a.yosys,'-V'],text=True).strip()
 manifest['tool_sha256']=hashlib.sha256(Path(a.yosys).read_bytes()).hexdigest()
 (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 with (a.out/'yosys.log').open('w') as log:r=subprocess.run(manifest['command'],stdout=log,stderr=subprocess.STDOUT)
 (a.out/'exit').write_text(str(r.returncode)+'\n')
 if r.returncode:return r.returncode
 net=json.loads((a.out/'netlist.json').read_text());counts={}
 for c in net['modules'][top]['cells'].values():counts[c['type']]=counts.get(c['type'],0)+1
 module=net['modules'][top]
 seq_q={b for c in module['cells'].values() if 'DFF' in c['type'].upper() for b in c['connections'].get('Q',[]) if isinstance(b,int)}
 groups={}
 patterns={'storage':r'g_on\.mem\[\d+\]$', 'protected_code':r'g_on\.u_(?:write_pointer|read_pointer|head)\.code\[\d+\]$', 'gray_rails':r'g_on\.(?:wg|wgi|rg|rgi|rg_sync[01]|rgi_sync[01]|wg_sync[01]|wgi_sync[01])$'}
 for name,pattern in patterns.items():
  nets={n:v for n,v in module['netnames'].items() if re.search(pattern,n)}
  bits={b for v in nets.values() for b in v['bits'] if isinstance(b,int)}
  parity_bits={v['bits'][word*72+bit] for v in nets.values() for word in range(len(v['bits'])//72) for bit in [0,1,3,7,15,31,63,71]} if name in ['storage','protected_code'] else set()
  groups[name]=dict(net_count=len(nets),declared_bits=sum(len(v['bits']) for v in nets.values()),dynamic_unique_bits=len(bits),direct_sequential_bits=len(bits&seq_q),parity_dynamic_bits=sum(isinstance(b,int) for b in parity_bits),parity_direct_sequential_bits=len(parity_bits&seq_q),nets=sorted(nets))
 if a.block.startswith('cdc'):
  if groups['storage']['net_count']!=64 or groups['protected_code']['net_count']!=26 or groups['gray_rails']['direct_sequential_bits']!=84:raise RuntimeError('Required storage/code/rail structural retention failed')
 else:
  if counts.get('ot_sram_1r1w_256x256_m2_r2c2')!=3:raise RuntimeError('Expected three actual SRAM macro blackboxes')
 manifest.update(returncode=0,cells=counts,retention=groups,standard_cell_mapping=False,physical_fit_qualified=False)
 (a.out/'record.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(counts));return 0
if __name__=='__main__':raise SystemExit(main())
