#!/usr/bin/env python3
"""Directed padded-row masking on minimumdriver: actual last16 Markov rows."""
import argparse,json,subprocess,hashlib,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import hdc_golden_v41 as G
from dsrom_markov_head_binding_gate import viamap,packed

def main(out):
 out.mkdir(parents=True,exist_ok=False);img=out/'images';img.mkdir()
 w=np.fromfile(ROOT/'input/weight_last16.bin',dtype='<u2').reshape(16,256)
 e=np.fromfile(ROOT/'input/embed.bin',dtype='<u2')
 G.set_arith('chunk8');mk=G.csum(G.mul((w.astype(np.uint32)<<16).view(np.float32),(e.astype(np.uint32)<<16).view(np.float32)))
 gold=G.add(np.float32(-1048576),mk);assert np.all(gold<0)
 (out/'gold.hex').write_text(''.join(f'{int(v):08x}\n' for v in gold.view(np.uint32)))
 (out/'embed.hex').write_text(''.join(f'{packed(e[b*16:b*16+16]):064x}\n' for b in range(16)))
 w=np.concatenate([w,np.zeros((16,256),dtype=np.uint16)]).reshape(512,16)
 for half in (0,1):viamap(img/f'mk_{half}.viamap.hex',{a:packed(w[2*a+half]) for a in range(256)})
 macro=out/'macro_ss.v';macro.write_text((ROOT/'input/macro_source.v').read_text().replace('rd_out <= word_read(addr_in)','rd_out <= #0.744 word_read(addr_in)'))
 tb=out/'tb_mask.sv';tb.write_text('''`timescale 1ns/1ps
module tbmask #(parameter SHARDTAIL=0);
 reg clk=0;always #0.4165 clk=~clk;reg rst_n=0,start=0;wire start_ready;
 reg[16:0]row0=0;reg[31:0]transaction=32'h55;reg embed_valid=0;wire embed_ready;
 reg[255:0]embed_data=0;reg[3:0]embed_beat=0;reg[31:0]embed_id=32'h55;reg embed_last=0;
 wire head_go;reg head_valid=0;reg[31:0]head_bits=0;reg head_fault=0;
 wire joined_valid,done,best_valid,fault;wire[31:0]joined_bits,best_bits;wire[16:0]joined_row,best_row;
 ot_dsrom_markov_head_driver #(.ENABLE(1),.PINREG(1),.VALID_ROWS(SHARDTAIL?6:32)) dut(.*);
 reg[255:0]vec[0:15];reg[31:0]gold[0:15];integer i,n,transaction_case=0,wanted=0,got=0,best=0;
 reg[8*1024-1:0]dir;
 always @(negedge clk)if(rst_n)begin
  if(fault)$fatal(1,"mask driverfault");
  if(joined_valid)begin
   if(got>=wanted||joined_row!=row0+got||joined_row>=129280||joined_bits!==gold[got])$fatal(1,"padded row reached join %0d %0d",got,joined_row);
   got=got+1;
  end
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR");
  $readmemh({dir,"/embed.hex"},vec);$readmemh({dir,"/gold.hex"},gold);
  for(transaction_case=0;transaction_case<2;transaction_case=transaction_case+1)begin
   rst_n=0;start=0;head_valid=0;embed_valid=0;got=0;
   row0=transaction_case==1?129280:(SHARDTAIL?21920:129264);
   wanted=transaction_case==1?0:(SHARDTAIL?6:16);
   best=BEST16;if(SHARDTAIL)best=BEST6;
   repeat(5)@(negedge clk);rst_n=1;repeat(3)@(negedge clk);start=1;@(negedge clk);start=0;
   for(i=0;i<16;i=i+1)begin
    while(!embed_ready)@(negedge clk);embed_valid=1;embed_data=vec[i];embed_beat=i;embed_last=i==15;@(negedge clk);
   end
   embed_valid=0;embed_last=0;repeat(3)@(negedge clk);
   // Valid rows have all-negative logits; scheduledpadding haszero, which wouldwin.
   for(n=0;n<32;n=n+1)begin
    head_valid=1;head_bits=n<wanted?32'hc9800000:32'b0;@(negedge clk);head_valid=0;
    repeat(255)@(negedge clk);
   end
   while(!done)@(negedge clk);
   if(got!=wanted||best_valid!=(wanted!=0))$fatal(1,"valid rowcount %0d %0d",got,wanted);
   if(wanted!=0&&(best_row!=row0+best||best_bits!==gold[best]||best_bits[31]!=1))$fatal(1,"zero padding won overnegative realrows");
   $display("PASS paddedmask shardtail=%0d row0=%0d valid=%0d skipped=%0d bestvalid=%0d",SHARDTAIL,row0,got,32-got,best_valid);
  end
  $finish;
 end
 initial begin #40000;$fatal(1,"timeout");end
endmodule
'''.replace('BEST16',str(int(np.argmax(gold)))).replace('BEST6',str(int(np.argmax(gold[:6])))))
 src=['rtl/common/ot_prefix.sv','rtl/v41rom/ot_v41_bmul2.sv','rtl/v41rom/ot_dsrom_bmul3.sv','rtl/v41rom/ot_v41_fadd.sv','rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_row.sv','rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_head_A.sv']
 results=[]
 for case in (0,1):
  obj=out/f'obj{case}'
  p=subprocess.run(['verilator','--binary','--timing','-j','8','-Wno-fatal','--top-module','tbmask',f'-GSHARDTAIL={case}','--Mdir',str(obj),*[str(ROOT/s) for s in src],str(macro),str(tb)],capture_output=True,text=True)
  (out/f'compile{case}.log').write_text(p.stdout+p.stderr)
  if p.returncode:raise RuntimeError(p.stderr)
  p=subprocess.run([str(obj/'Vtbmask'),f'+DIR={out}',f'+OT_ROM_DIR={img}'],capture_output=True,text=True)
  (out/f'sim{case}.log').write_text(p.stdout+p.stderr);print(p.stdout,flush=True)
  results.append(dict(case=case,passed=p.returncode==0 and p.stdout.count('PASS paddedmask')==2,exit=p.returncode))
  if p.returncode:break
 record=dict(passed=len(results)==2 and all(x['passed'] for x in results),scope='directed driver mask; actual last16 Markov rows, injected allnegative headlogits versuszero scheduledpadding; lastvocab, allpadding, sixrowshardtail',results=results,released=json.loads((ROOT/'input/last_rows_receipt.json').read_text()),source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in src})
 (out/'verdict.json').write_text(json.dumps(record,indent=2)+'\n');return record['passed']
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();raise SystemExit(0 if main(a.out.resolve()) else 1)
