#!/usr/bin/env python3
"""Exhaustive local decoder gate plus full real wo_a rank-slice software check."""
import argparse,hashlib,json,struct,subprocess,sys,tempfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import hdc_golden_v41 as G

def main(snapshot,out):
    codes=np.tile(np.arange(256,dtype=np.uint8),256); scales=np.repeat(np.arange(256,dtype=np.uint8),256)
    invalid=((codes&127)==127)|(scales==255)
    with np.errstate(all='ignore'):
        ref=(G.to_bf16((G.E4M3[codes]*np.exp2(scales.astype(np.int32)-127)).astype(np.float32)).view(np.uint32)>>16).astype(np.uint16)
    ref[invalid]=0
    with tempfile.TemporaryDirectory(prefix='v41_woa_decode_') as tmp:
        t=Path(tmp);lines=[f'{int(v)<<32|int(s)<<24|int(c)<<16|int(r):09x}' for c,s,r,v in zip(codes,scales,ref,invalid)]
        (t/'vectors.hex').write_text('\n'.join(lines)+'\n')
        (t/'tb.sv').write_text('''module tb; reg clk=0;always #5 clk=~clk;reg rst_n=0,in_v=0;reg[7:0]code,scale;wire out_v,fault;wire[15:0]value;reg[32:0]vec[0:65535];integer i;ot_chip_v41x_woa_fp8_decode d(.*);initial begin $readmemh("vectors.hex",vec);@(negedge clk);rst_n=1;for(i=0;i<65536;i=i+1)begin code=vec[i][23:16];scale=vec[i][31:24];in_v=1;@(posedge clk);#1;if(!out_v||fault!==vec[i][32]||value!==vec[i][15:0])$fatal(1,"mismatch %0d %h %h",i,value,vec[i][15:0]);@(negedge clk);end $display("PASS 65536");$finish;end endmodule''')
        subprocess.run(['iverilog','-g2012','-s','tb','-o',str(t/'sim'),str(ROOT/'rtl/chip/ot_chip_v41x_woa_fp8_decode.sv'),str(t/'tb.sv')],check=True)
        run=subprocess.run(['vvp',str(t/'sim')],cwd=t,check=True,capture_output=True,text=True)
    idx=json.loads((snapshot/'model.safetensors.index.json').read_text())['weight_map'];pins={}
    def arr(k):
        p=snapshot/idx[k]
        with p.open('rb') as f:n=struct.unpack('<Q',f.read(8))[0];h=f.read(n)
        m=json.loads(h)[k];pins[k]={'shape':m['shape'],'dtype':m['dtype'],'header_sha256':hashlib.sha256(h).hexdigest(),'blob':p.resolve().name}
        return np.memmap(p,dtype=np.uint8,mode='r',offset=8+n+m['data_offsets'][0],shape=tuple(m['shape']))
    w=arr('layers.25.attn.wo_a.weight')[:2048];s=arr('layers.25.attn.wo_a.scale')[:64]
    ex=np.repeat(np.repeat(s,32,axis=0),32,axis=1)
    got=ref[ex.astype(np.uint16)*256+w.astype(np.uint16)]
    want=G.to_bf16(G._blocked(w,s.astype(np.int32)-127,'wo_a').dense()).view(np.uint32)>>16
    bad=int(np.count_nonzero(got!=want));assert not bad
    d=dict(schema='opentallas.v41.woa_compact_decode.v1',status='standalone_exact_not_integrated_or_routed',exhaustive_pairs=65536,valid_pairs=int((~invalid).sum()),fault_pairs=int(invalid.sum()),real_rank_values=int(w.size),real_mismatches=bad,checkpoint_pins=pins,checkpoint_output_sha256=hashlib.sha256(got.tobytes()).hexdigest(),source_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ['rtl/chip/ot_chip_v41x_woa_fp8_decode.sv','tools/hdc_golden_v41.py','tools/hdc_golden.py']},cycle_contract='1-cycle registered decoder, II1; ROM latency and scale selection excluded',bandwidth=dict(values_per_local_ME_beat=64,expanded_BF16_bits_per_beat=1024,code_bits_per_beat=512,scale_upper_bound_bits_per_beat=512,compact_per32word_bits=264,local_scale_mapping='checkpoint32x32 scales must be retained/reused or duplicated per row; not yet connected'),simulation_stdout=run.stdout)
    out.write_text(json.dumps(d,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.snapshot,a.output)
