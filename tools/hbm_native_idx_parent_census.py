#!/usr/bin/env python3
"""Full source retained-state graph, preserves inferred FIFO memories explicitly."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
from hbm_native_idx_owned_census import census
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--cut',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
s=Path('tools/hbm_native_idx_parent_bench.sh').read_text()
src=re.findall(r'(?:rtl|physical)/[\w/.-]+\.(?:sv|vlt|v)',s)
src=[f for f in src if '/test/' not in f and not f.endswith('.vlt')]
if a.cut:
 src += [str(f) for f in Path('rtl/hbm_accel/index').glob('ot_hbm_idx_*native.sv') if any(t in f.name for t in ['parent_cut','score_cut','selector_cut','selector_owned','query_owned','actquant_owned','line_memory_owned','landing_fifo','landing_store'])]
 src += ['physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v']
 top='ot_hbm_idx_parent_cut_native'
else:top='ot_hbm_idx_parent_owned_native'
owned=Path('rtl/hdc/v41x/ot_hbm_idx_owned_native.sv').read_text();start=owned.index('module ot_hbm_idx_hslice_ready_native');end=owned.index(');',start)+2
(a.out/'hslice_abi.sv').write_text('(* blackbox *) '+owned[start:end]+'\nendmodule\n')
(a.out/'owned_glue.sv').write_text(owned[:start]+owned[owned.index('endmodule',start)+len('endmodule'):])
libs=[f.replace('.v','_bb.v') for f in src if f.startswith('physical/asap7_memory')]
reads=[str(a.out/'owned_glue.sv') if f.endswith('/ot_hbm_idx_owned_native.sv') else f for f in src if not f.startswith('physical/asap7_memory') and not f.endswith('/ot_hdc_v41x_idx_hslice.sv')]
ys='read_verilog -defer -sv -D SYNTHESIS -Irtl/common '+' '.join(reads)+'\nread_verilog -lib -sv '+' '.join(libs+[str(a.out/'hslice_abi.sv')])+'\nhierarchy -check -top '+top+'\nproc\nopt\nmemory_dff\nmemory_collect\nopt_clean\nwrite_json '+str(a.out/'retained.json')+'\n'
(a.out/'census.ys').write_text(ys)
with (a.out/'yosys.log').open('w') as f:r=subprocess.run([str(Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'),'-s',str(a.out/'census.ys')],stdout=f,stderr=subprocess.STDOUT)
if r.returncode:raise SystemExit(r.returncode)
x=census(a.out/'retained.json',top)
mr={}
for row in x['instances']:
 for m in row['local_memories']:
  for ck in set(m['write_clocks']):mr[ck]=mr.get(ck,0)+m['bits']
x['inferred_memory_bits_by_write_clock']=mr
x['total_inferred_memory_bits']=sum(m['bits'] for row in x['instances'] for m in row['local_memories'])
x['source_sha256']={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in src+['rtl/common/ot_secded_cols.svh']}
x['physical_qualified']=False;x['inferred_memory_note']='Inferred memories retained as actual WIDTH*SIZE state, not omitted or qualified SRAM replacements; clock root cannot be accepted based only on FF total.'
(a.out/'receipt.json').write_text(json.dumps(x,indent=2)+'\n')
print(json.dumps({'ff_bits':x['total_generic_ff_bits'],'inferred_memory_bits':x['total_inferred_memory_bits'],'ff_clock_roots':len(x['clock_ff_bits']),'blackbox_count':len(x['blackbox_macros'])}))
