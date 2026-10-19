#!/usr/bin/env python3
"""Prepare immutable replay inputs. Run simulations/synthesis only via ot-run."""
import argparse,gzip,hashlib,json,re,shutil,subprocess,sys,tarfile
from pathlib import Path
from generate import generate,cells
root=Path(__file__).resolve().parents[2];r=root/'results/arch/kv_d2d_reset_source_1019'
a=argparse.ArgumentParser();a.add_argument('--out',required=True);x=a.parse_args();out=Path(x.out);out.mkdir(parents=True,exist_ok=True)
with tarfile.open(r/'native_original_models.tgz') as t:t.extractall(out)
for f in ['functional_cells_udp.v','native_interfaces.v','sram.v','sram_bb.v','seq.lib']:(out/f).write_bytes(gzip.decompress((r/(f+'.gz')).read_bytes()))
manifest={}
for mode,top in [('r7w','qkd_d2d_static'),('ovl','qkd_d2d_static_ovl')]:
 b=out/(mode+'_mapped.v');b.write_bytes(gzip.decompress((r/(mode+'_353_mapped.v.gz')).read_bytes()))
 candidate,proof=generate(b,top);saved=(root/'rtl/qwen_sys/d2d_static_20261015/reset24_frozen'/(mode+'_reset24.v')).read_text();assert candidate==saved,'generator/emitted source mismatch'
 for suffix in ['_reset24_kept.v','_reset24.v']:(out/(mode+suffix)).write_text(saved)
 cc=cells(b.read_text());high=next(c['pins']['H'] for c in cc if c['master'].startswith('TIEHI'))
 seq=[c for c in cc if c['master'].startswith('DFFAS')]
 assert all(c['pins']['SETN']==high or c['pins']['RESETN']==high for c in seq),'unsupported dual-active asynchronous FF binding'
 manifest[mode]=dict(source_sha256=proof['source_sha256'],emitted_sha256=hashlib.sha256(saved.encode()).hexdigest(),native_async_flops=len(seq),single_active_async_pin_proved=True)
 for kind in ['active','kept','rx','lifecycle']:shutil.copyfile(r/f'tb_{mode}_{kind}.sv',out/f'tb_{mode}_{kind}.sv')
for f in Path(__file__).parent.iterdir():
 if f.suffix in ['.sh','.py','.sv','.v']:shutil.copyfile(f,out/f.name)
# Extract native FF semantic equivalents only for the actual one-active-async-pin profile.
u=(out/'functional_cells_udp.v').read_text();i=u.index('// BSD 3-Clause License');comb=u[:i];seq=u[i:]
fast='''module DFFHQNx1_ASAP7_75t_R(output reg QN,input D,CLK); always @(posedge CLK) QN<=~D; endmodule
module DFFASRHQNx1_ASAP7_75t_R(output reg QN,input D,RESETN,SETN,CLK); always @(posedge CLK or negedge RESETN or negedge SETN) if(!SETN) QN<=0; else if(!RESETN) QN<=1; else QN<=~D; endmodule
'''
(out/'functional_cells_fast.v').write_text(comb+fast)
(out/'native_seq_reference.v').write_text(seq.replace('module DFFHQNx1_ASAP7','module native_DFFHQNx1_ASAP7').replace('module DFFASRHQNx1_ASAP7','module native_DFFASRHQNx1_ASAP7'))
manifest['files']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
(out/'inputs.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
