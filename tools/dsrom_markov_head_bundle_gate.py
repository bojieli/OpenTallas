#!/usr/bin/env python3
"""Admitted remote minimum full bundle: real B, 4 A, shared lookup, 4 Markov.
Manifest-bound actual released interior and21/22-row shard ends. No die simulation.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import hdc_golden_v41 as G
from dsrom_markov_head_binding_gate import viamap,packed
from dsrom_markov_head_bundle_image import build
from uarch_model_dsrom_markov_head_binding import model

def main(out,manifest,windows,cases=None):
 out.mkdir(parents=True,exist_ok=False);(out/'model.json').write_text(json.dumps(model(),indent=2))
 receipt=json.loads((ROOT/'input/released_inputs.json').read_text());token=receipt['token']
 e=np.fromfile(ROOT/'input/embed.bin',dtype='<u2');z=np.load(ROOT/'input/head_ref.npz')
 xf=(z['xf'].astype(np.float32).reshape(-1).view(np.uint32)>>16).astype('<u2')
 if xf.size!=5120:raise ValueError('activation shape')
 f32=lambda x:(x.astype(np.uint32)<<16).view(np.float32)
 G.set_arith('chunk8');results=[]
 for die,bundle in (cases or [(0,83),(0,84),(2,84)]):
  case=out/f'd{die}_b{bundle}';images=case/'images';case.mkdir()
  image=build(Path('.'),manifest,images,die,bundle,windows=windows);nv=image['B_VALID_ROWS'];r0=image['global_row0']
  h=np.zeros((128,5120),dtype='<u2');w=np.zeros((128,256),dtype='<u2');wd=windows/f'd{die}_b{bundle}'
  h[:nv]=np.fromfile(wd/'head.bin',dtype='<u2').reshape(nv,5120);w[:nv]=np.fromfile(wd/'markov.bin',dtype='<u2').reshape(nv,256)
  hf=f32(h);xa=f32(xf[:4096]);xb=f32(xf[4096:]);ra=G.csum(G.mul(hf[:,:4096],xa));rb=G.add(G.add(G.csum(G.mul(hf[:,4096:],xb)),np.float32(0)),np.float32(0))
  hl=G.add(ra,rb);mk=G.csum(G.mul(f32(w),f32(e)));joined=G.add(hl,mk);best=int(np.argmax(joined[:nv]));assert np.count_nonzero(mk[:nv])>0
  perm=np.array([32*q+k for k in range(32) for q in range(4)])
  for name,arr in [('a',ra),('b',rb[perm]),('head',hl),('joined',joined)]:
   (case/f'{name}.hex').write_text(''.join(f'{int(v):08x}\n' for v in arr.view(np.uint32)))
  for name,vec,words in [('xa',xf[:4096],256),('xb',xf[4096:],64)]:
   (case/f'{name}.hex').write_text(''.join(f'{packed(vec[16*i:16*i+16]):064x}\n' for i in range(words)))
  ew={token*16+b:packed(e[b*16:b*16+16]) for b in range(16)}
  viamap(images/'zero.viamap.hex',{})
  for macro in range(506):
   words={a%4096:v for a,v in ew.items() if a//4096==macro}
   if words:viamap(images/f'macro{macro:03}.viamap.hex',words)
   else:(images/f'macro{macro:03}.viamap.hex').symlink_to('zero.viamap.hex')
  macro=case/'macro_ss.v';macro.write_text((ROOT/'input/macro_source.v').read_text().replace('rd_out <= word_read(addr_in)','rd_out <= #0.744 word_read(addr_in)'))
  tb=case/'tb.sv';tb.write_text('''`timescale 1ns/1ps
module tb;
 reg clk=0;always #0.4165 clk=~clk;reg rst_n=0,start=0;wire start_ready;
 reg[16:0]row0=ROW0,d_i=TOKEN;reg[31:0]transaction=32'h12345;reg[255:0]xa=0,xb=0;
 wire head_go,done,best_valid,fault;wire[3:0]joined_valid;wire[127:0]joined_bits;wire[67:0]joined_row;wire[16:0]best_row;wire[31:0]best_bits;
 ot_dsrom_markov_head_bundle #(.ENABLE(1),.PINREG(2),.CACHE_PINREG(1),.VALID_ROWS(NVALID),.A_INPUT_STAGES(4))dut(.*);
 reg[255:0]am[0:255],bm[0:63];reg[31:0]ag[0:127],bg[0:127],hg[0:127],jg[0:127];
 integer cyc=0,g0=-1,q,k,nb=0,njoin=0,na[0:3],nh[0:3],nj[0:3];integer bmax[0:3],amax[0:3],headmax[0:3];
 integer first_b=-1,last_b=-1,first_a=-1,last_a=-1,first_join=-1,last_join=-1;reg[8*1024-1:0]dir;
 always @(posedge clk)cyc<=cyc+1;
 always @(negedge clk)if(rst_n)begin
  if(head_go&&g0<0)g0=cyc;
  if(g0>=0&&cyc-g0>=5)begin xa=am[(cyc-g0-5)%256];xb=bm[(cyc-g0-5)%64];end
  if(fault)$fatal(1,"bundle fault");
  if(dut.bo)begin
   if(nb>=128||dut.bd!==bg[nb])$fatal(1,"actual B root/row order %0d",nb);
   if(first_b<0)first_b=cyc;last_b=cyc;nb=nb+1;
  end
  MONITORS
  if(done)begin
   if(nb!=128||njoin!=NVALID||!best_valid||best_row!=BESTROW||best_bits!==BESTBITS)$fatal(1,"masked bundle argmax");
   for(q=0;q<4;q=q+1)if(na[q]!=32||nh[q]!=32)$fatal(1,"scheduled padding completion");
   $display("BUNDLEMETRICS valid=%0d headgo=%0d firstB=%0d lastB=%0d firstA=%0d lastA=%0d firstjoin=%0d lastjoin=%0d done=%0d Bfifo=%0d,%0d,%0d,%0d Afifo=%0d,%0d,%0d,%0d headqueue=%0d,%0d,%0d,%0d",NVALID,g0,first_b,last_b,first_a,last_a,first_join,last_join,cyc,bmax[0],bmax[1],bmax[2],bmax[3],amax[0],amax[1],amax[2],amax[3],headmax[0],headmax[1],headmax[2],headmax[3]);
   $display("PASS actualB fourA fourMarkov sharedlookup staged4 maskedargmax valid=%0d",NVALID);$finish;
  end
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR");
  $readmemh({dir,"/xa.hex"},am);$readmemh({dir,"/xb.hex"},bm);$readmemh({dir,"/a.hex"},ag);$readmemh({dir,"/b.hex"},bg);$readmemh({dir,"/head.hex"},hg);$readmemh({dir,"/joined.hex"},jg);
  for(q=0;q<4;q=q+1)begin na[q]=0;nh[q]=0;nj[q]=0;bmax[q]=0;amax[q]=0;headmax[q]=0;end
  repeat(5)@(negedge clk);rst_n=1;repeat(3)@(negedge clk);while(!start_ready)@(negedge clk);start=1;@(negedge clk);start=0;
 end
 initial begin #30000;$fatal(1,"timeout");end
endmodule
''')
  monitors=[]
  for q in range(4):
   a=f'dut.g_a[{q}].a';m=f'dut.g_a[{q}].markov'
   monitors.append(f'''if({a}.o_v)begin k=32*{q}+na[{q}];if(na[{q}]>=32||{a}.o_d!==ag[k])$fatal(1,"Aroot q{q} row%0d",k);na[{q}]=na[{q}]+1;if(first_a<0)first_a=cyc;last_a=cyc;end
 if(dut.g_a[{q}].hv)begin k=32*{q}+nh[{q}];if(nh[{q}]>=32||dut.g_a[{q}].hb!==hg[k])$fatal(1,"actual A/B join q{q}");nh[{q}]=nh[{q}]+1;end
 if({a}.g_join.fb_n>bmax[{q}])bmax[{q}]={a}.g_join.fb_n;if({a}.g_join.fa_n>amax[{q}])amax[{q}]={a}.g_join.fa_n;
 if({m}.hn>headmax[{q}])headmax[{q}]={m}.hn;
 if(joined_valid[{q}])begin k=32*{q}+nj[{q}];if(k>=NVALID||joined_row[17*{q}+:17]!=ROW0+k||joined_bits[32*{q}+:32]!==jg[k])$fatal(1,"Markov rowidentity/padding q{q}");nj[{q}]=nj[{q}]+1;njoin=njoin+1;if(first_join<0)first_join=cyc;last_join=cyc;end''')
  txt=tb.read_text().replace('MONITORS','\n'.join(monitors)).replace('NVALID',str(nv)).replace('ROW0',str(r0)).replace('TOKEN',str(token)).replace('BESTROW',str(r0+best)).replace('BESTBITS',f"32'h{int(joined.view(np.uint32)[best]):08x}");tb.write_text(txt)
  src=['rtl/hdc/ot_hdc_delay.sv','rtl/common/ot_prefix.sv','rtl/v41rom/ot_v41_bmul2.sv','rtl/v41rom/ot_dsrom_bmul3.sv','rtl/v41rom/ot_v41_fadd.sv','rtl/v41rom/ot_dsrom_head_elem.sv','rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_row.sv','rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_embed_port.sv','rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_head_A.sv','rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_head_bundle.sv']
  obj=case/'obj';p=subprocess.run(['verilator','--binary','--timing','-j','8','-Wno-fatal','--top-module','tb','--Mdir',str(obj),*[str(ROOT/s) for s in src],str(macro),str(tb)],capture_output=True,text=True);(case/'compile.log').write_text(p.stdout+p.stderr)
  if p.returncode:raise RuntimeError(p.stderr)
  p=subprocess.run([str(obj/'Vtb'),f'+DIR={case}',f'+OT_ROM_DIR={images}'],capture_output=True,text=True);(case/'sim.log').write_text(p.stdout+p.stderr);print(p.stdout,flush=True)
  results.append(dict(die=die,bundle=bundle,valid_rows=nv,exit=p.returncode,passed=p.returncode==0 and 'PASS actualB' in p.stdout,image_manifest=image))
  if p.returncode:break
 record=dict(passed=len(results)==len(cases or [(0,83),(0,84),(2,84)]) and all(x['passed'] for x in results),scope='one actual 4A+1B+4Markov successor bundle; shared lookup; A_INPUT_STAGES4; manifest interior and shard ends21/22; not full die/physical closure',results=results,activation_and_embedding=receipt,manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),window_provenance=json.loads((windows/'transfer_provenance.json').read_text()),source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in src},physical_qualified=False)
 (out/'verdict.json').write_text(json.dumps(record,indent=2)+'\n');return record['passed']
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--case',type=int,nargs=2,action='append');ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--windows',type=Path,required=True);a=ap.parse_args();raise SystemExit(0 if main(a.out.resolve(),a.manifest,a.windows,a.case) else 1)
