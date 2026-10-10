#!/usr/bin/env python3
"""Remote-only minimum actual A+lookup+fullKdot+argmax gate; no die simulation."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import hdc_golden_v41 as G
from uarch_model_dsrom_markov_head_binding import model

def write_words(path,words):path.write_text(''.join(f'{int(w):064x}\n' for w in words))
def viamap(path,words):
    spread=[sum(((b>>k)&1)<<(8*k) for k in range(8)) for b in range(256)]
    physical=[0]*512
    for a,word in words.items():
        word=int(word);expanded=sum(spread[(word>>(8*j))&255]<<(64*j) for j in range(32))
        physical[a//8]|=expanded<<(a%8)
    path.write_text(''.join(f'{r:0548x}\n' for r in physical))
def packed(row):return sum(int(x)<<(16*l) for l,x in enumerate(row))
def main(out,pinreg=1,cache_pinreg=0,metrics_only=False):
    out.mkdir(parents=True,exist_ok=False);images=out/'images';images.mkdir()
    (out/'model.json').write_text(json.dumps(model(),indent=2)+'\n')
    inp=ROOT/'input';receipt=json.loads((inp/'released_inputs.json').read_text())
    r0,token=receipt['row0'],receipt['token']
    w=np.fromfile(inp/'weight.bin',dtype='<u2').reshape(32,256)
    e=np.fromfile(inp/'embed.bin',dtype='<u2').reshape(256)
    h=np.fromfile(inp/'head.bin',dtype='<u2').reshape(32,5120)
    z=np.load(inp/'head_ref.npz');print('reference keys',z.files,flush=True);xf=z['xf'].astype(np.float32)
    if xf.size!=5120:raise ValueError('fullheadactivation shape')
    xf=xf.reshape(-1)
    x16=(xf.view(np.uint32)>>16).astype(np.uint16);xf=(x16.astype(np.uint32)<<16).view(np.float32)
    G.set_arith('chunk8');hf=(h.astype(np.uint32)<<16).view(np.float32)
    ra=G.csum(G.mul(hf[:,:4096],xf[:4096]));rb=G.csum(G.mul(hf[:,4096:],xf[4096:]));rb=G.add(G.add(rb,np.float32(0)),np.float32(0))
    hl=G.add(ra,rb);mk=G.csum(G.mul((w.astype(np.uint32)<<16).view(np.float32),(e.astype(np.uint32)<<16).view(np.float32)))
    logits=G.add(hl,mk);best=int(np.argmax(logits));assert np.count_nonzero(mk)>0
    for name,arr in [('root',ra),('b',rb),('head',hl),('markov',mk),('joined',logits)]:
        (out/f'{name}.hex').write_text(''.join(f'{int(v):08x}\n' for v in arr.view(np.uint32)))
    # Actual A skewedROM, preserving releasedBF16 bits.
    logical=h[:,:4096].reshape(8192,16);j=np.arange(16)[None,:];p=np.arange(8192)[:,None]
    physical=logical[(p-11*(j%8))%8192,np.broadcast_to(j,(8192,16))]
    for half in (0,1):viamap(images/f'ha_{half}.viamap.hex',{a:packed(physical[2*a+half]) for a in range(4096)})
    wm=w.reshape(512,16)
    for half in (0,1):viamap(images/f'mk_{half}.viamap.hex',{a:packed(wm[2*a+half]) for a in range(256)})
    # Reallookup mapping from source43e847b7d (contiguoushalf; physicallyunqualified).
    embed_words={token*16+b:packed(e[b*16:b*16+16]) for b in range(16)}
    for macro in range(506):
        words={a%4096:v for a,v in embed_words.items() if a//4096==macro}
        if words:viamap(images/f'macro{macro:03}.viamap.hex',words)
        else:
            zero=images/'zero.viamap.hex'
            if not zero.exists():viamap(zero,{})
            (images/f'macro{macro:03}.viamap.hex').symlink_to(zero.name)
    xa=x16[:4096].reshape(256,16)
    write_words(out/'x_skew.hex',[packed(xa[(p-11*(np.arange(16)%8))%256,np.arange(16)]) for p in range(256)])
    # Same realmacro read equations; Icarus untypedparameters and calibratedSSclkq.
    original=(inp/'macro_source.v').read_text()
    macro=out/'macro_ss.v';macro.write_text(original.replace('rd_out <= word_read(addr_in)','rd_out <= #0.744 word_read(addr_in)'))
    tb=out/'tb.sv';tb.write_text('''`timescale 1ns/1ps
module tb #(parameter MUTANT=0);
 reg clk=0;always #0.4165 clk=~clk;reg rst_n=0,start=0;wire start_ready;
 reg[16:0]d_i=TOKEN,row0=ROW0;reg[31:0]transaction=32'h12345;
 reg[255:0]x=0;reg b_v=0;reg[31:0]b_d=0;wire head_go,root_valid,joined_valid,done,fault,best_valid;
 wire[31:0]root_bits,joined_bits,best_bits;wire[16:0]joined_row,best_row;
 ot_dsrom_markov_head_lookup_A #(.ENABLE(1),.PINREG(PINREG_VALUE),.CACHE_PINREG(CACHE_PINREG_VALUE),.MUTANT_FOLD(MUTANT))dut(.*);
 reg[255:0]xm[0:255];reg[31:0]roots[0:31],bm[0:31],gold[0:31];
 integer cyc=0,g0=-1,nroot=0,njoin=0,first_tail=-1,last_tail=-1,highwater=0,head_cycle[0:31];
 integer query0=-1,first_root=-1,last_root=-1,first_head=-1,last_head=-1,first_join=-1,last_join=-1,previous_join=-1,join_II_min=99999,join_II_max=0,head_stall_cycles=0,head_wait_cycles=0;
 reg[8*1024-1:0]dir;
 always @(posedge clk)begin cyc<=cyc+1;if(start&&start_ready)query0<=cyc+1;end
 always @(negedge clk)begin
  b_v=0;
  if(head_go&&g0<0)g0=cyc;
  if(g0>=0&&cyc-g0>=5)x=xm[(cyc-g0-5)%256];
  if(root_valid)begin
   if(first_root<0)first_root=cyc;last_root=cyc;
   if(root_bits!==roots[nroot])$fatal(1,"actual Aroot mismatch row%0d got%h gold%h",nroot,root_bits,roots[nroot]);
   b_v=1;b_d=bm[nroot];nroot=nroot+1;
  end
  if(dut.successor.hv)begin head_cycle[dut.successor.driver.emitted]=cyc;if(first_head<0)first_head=cyc;last_head=cyc;end
  if(dut.successor.driver.hn==2)head_stall_cycles=head_stall_cycles+1;
  if(dut.successor.driver.hn!=0&&!dut.successor.driver.launch)head_wait_cycles=head_wait_cycles+1;
  if(dut.successor.driver.hn>highwater)highwater=dut.successor.driver.hn;
  if(joined_valid)begin
   if(first_join<0)first_join=cyc;last_join=cyc;
   if(previous_join>=0)begin if(cyc-previous_join<join_II_min)join_II_min=cyc-previous_join;if(cyc-previous_join>join_II_max)join_II_max=cyc-previous_join;end
   previous_join=cyc;
   if(joined_bits!==gold[njoin]||joined_row!==ROW0+njoin)$fatal(1,"postMarkov mismatch row%0d got%h gold%h",njoin,joined_bits,gold[njoin]);
   if(first_tail<0)first_tail=cyc-head_cycle[njoin];last_tail=cyc-head_cycle[njoin];njoin=njoin+1;
  end
  if(fault)$fatal(1,"successor fault");
  if(done)begin
   if(!best_valid||nroot!=32||njoin!=32||best_row!=BESTROW||best_bits!==BESTBITS)$fatal(1,"argmax mismatch");
   $display("METRICS query=%0d headgo=%0d firstroot=%0d lastroot=%0d firsthead=%0d lasthead=%0d firstjoin=%0d lastjoin=%0d argmax=%0d joinIImin=%0d joinIImax=%0d headstall=%0d headwait=%0d queuehigh=%0d",query0,g0,first_root,last_root,first_head,last_head,first_join,last_join,cyc,join_II_min,join_II_max,head_stall_cycles,head_wait_cycles,highwater);
   $display("PASS actualAroot lookup256dot separatejoin argmax roots=%0d rows=%0d firsttail=%0d lasttail=%0d headqueuehighwater=%0d",nroot,njoin,first_tail,last_tail,highwater);$finish;
  end
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR");
  $readmemh({dir,"/x_skew.hex"},xm);$readmemh({dir,"/root.hex"},roots);$readmemh({dir,"/b.hex"},bm);$readmemh({dir,"/joined.hex"},gold);
  repeat(5)@(negedge clk);rst_n=1;repeat(3)@(negedge clk);while(!start_ready)@(negedge clk);
  start=1;@(negedge clk);start=0;
 end
 initial begin #30000;$fatal(1,"timeout");end
endmodule
'''.replace('CACHE_PINREG_VALUE',str(cache_pinreg)).replace('PINREG_VALUE',str(pinreg)).replace('TOKEN',str(token)).replace('ROW0',str(r0)).replace('BESTROW',str(r0+best)).replace('BESTBITS',f"32'h{int(logits.view(np.uint32)[best]):08x}"))
    sources=['rtl/common/ot_prefix.sv','rtl/v41rom/ot_v41_bmul2.sv','rtl/v41rom/ot_dsrom_bmul3.sv','rtl/v41rom/ot_v41_fadd.sv','rtl/v41rom/ot_dsrom_head_elem.sv','rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_row.sv','rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_embed_port.sv','rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_head_A.sv']
    results=[]
    for mutant in ((0,) if metrics_only else (0,1)):
        obj=out/f'obj{mutant}';exe=obj/'Vtb'
        p=subprocess.run(['verilator','--binary','--timing','-j','8','-Wno-fatal','--top-module','tb',f'-GMUTANT={mutant}','--Mdir',str(obj),*[str(ROOT/s) for s in sources],str(macro),str(tb)],capture_output=True,text=True)
        (out/f'compile{mutant}.log').write_text(p.stdout+p.stderr)
        if p.returncode:raise RuntimeError(p.stderr)
        p=subprocess.run([str(exe),f'+DIR={out}',f'+OT_ROM_DIR={images}'],capture_output=True,text=True)
        (out/f'sim{mutant}.log').write_text(p.stdout+p.stderr);print(p.stdout,flush=True)
        results.append(dict(mutant=mutant,exit=p.returncode,passed=p.returncode==0 and 'PASS actualAroot' in p.stdout))
        if (not mutant and not results[-1]['passed']) or (mutant and p.returncode==0):break
    success=bool(results) and results[0]['passed'] and (metrics_only or (len(results)==2 and results[1]['exit']!=0))
    record=dict(passed=success,metrics_only=metrics_only,PINREG=pinreg,CACHE_PINREG=cache_pinreg,scope='one actual32-row A, real tokenlookup, fullK256 Markov dot, separatejoin, localargmax; not fullshard/die closure',released=receipt,results=results,nonzero_markov_rows=int(np.count_nonzero(mk)),source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources},macro_model_patch=['744ps SSclkq'],physical_qualified=False)
    import re
    line=next((x for x in (out/'sim0.log').read_text().splitlines() if x.startswith('METRICS ')),None)
    if line:
        met={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}
        met.update(firstroot_to_lastjoined=met['lastjoin']-met['firstroot'],firsthead_to_lastjoined=met['lastjoin']-met['firsthead'],lasthead_to_argmax=met['argmax']-met['lasthead'],embedding_warmup=met['headgo']-met['query'])
        record['measured_cycles']=met
    (out/'verdict.json').write_text(json.dumps(record,indent=2)+'\n');return success
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--pinreg',type=int,choices=[0,1,2],default=1);ap.add_argument('--cache-pinreg',type=int,choices=[0,1],default=0);ap.add_argument('--metrics-only',action='store_true');a=ap.parse_args();raise SystemExit(0 if main(a.out.resolve(),a.pinreg,a.cache_pinreg,a.metrics_only) else 1)
