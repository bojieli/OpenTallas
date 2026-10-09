#!/usr/bin/env python3
"""Remote Z7 lookup: direct local capture, released bytes and token-only credits."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from dsrom_markov_embed_image_pp import generate,DEFAULT
from uarch_model_dsrom_markov_embed_localcapture import model
ROOT=Path(__file__).resolve().parents[1]
TOKENS=[0,255,256,511,512,8191,8192,129023,129024,129279]
def run(out,snapshot):
 out.mkdir(parents=True,exist_ok=False);(out/'model.json').write_text(json.dumps(model(),indent=2))
 images=out/'images';meta=generate(snapshot,images,TOKENS)
 zero=images/'zero.viamap.hex';zero.write_text(('0'*548+'\n')*512)
 for macro in range(506):
  p=images/f'macro{macro:03}.viamap.hex'
  if not p.exists():p.symlink_to(zero.name)
 rows=[]
 for tok in TOKENS:
  row=bytes.fromhex(meta['selected_rows'][str(tok)]);rows.extend(f'{int.from_bytes(row[32*b:32*(b+1)],"little"):064x}' for b in range(16))
 (out/'expected.hex').write_text('\n'.join(rows)+'\n');bad=rows.copy();bad[0]=f'{int(bad[0],16)^1:064x}';(out/'expected_negative.hex').write_text('\n'.join(bad)+'\n')
 macro=out/'macro_ss.v';macro.write_text((ROOT/'input/macro_source.v').read_text().replace('rd_out <= word_read(addr_in)','rd_out <= #0.744 word_read(addr_in)'))
 tb=out/'tb.sv';tb.write_text('''`timescale 1ns/1ps
module tb;
 reg clk=0;always #0.4165 clk=~clk;reg rst_n=0,req_valid=0,out_ready=0;reg[16:0]req_token=0;
 wire req_ready,fault_valid;wire[16:0]fault_token;wire out_valid,out_last;wire[255:0]out_data;wire[16:0]out_token;wire[3:0]out_beat;
 ot_dsrom_markov_embed_localcapture_rom #(.ENABLE(1))dut(.*);
 wire disabled_ready;ot_dsrom_markov_embed_localcapture_port off(.clk(clk),.rst_n(rst_n),.req_valid(1'b1),.req_ready(disabled_ready),.req_token(17'b0),.bank_q(64768'b0),.out_ready(1'b1));
 reg guard_re=0;reg[12:0]guard_addr=0;wire[255:0]guard_data;wire guard_valid,guard_fault;
 ot_dsrom_markov_embed_localcapture_pair #(.ENABLE(1))guard(.clk(clk),.rst_n(rst_n),.re(guard_re),.addr(guard_addr),.captured_data(guard_data),.captured_valid(guard_valid),.fault(guard_fault));
 reg[255:0]expected[0:159];integer tokens[0:9];integer j,seen=0,cyc=0,seed=77,highwater=0,full_stop=0;reg[277:0]held;reg stalled=0;
 reg[8*1024-1:0]dir;
 always @(posedge clk)if(rst_n)begin
  cyc=cyc+1;
  if(disabled_ready)$fatal(1,"default enabled");
  if(dut.port.reserved>highwater)highwater=dut.port.reserved;
  if(dut.port.reserved==8&&!dut.port.issue)full_stop=full_stop+1;
  if(dut.port.reserved>8||dut.port.count>dut.port.reserved)$fatal(1,"pipeline reservation overflow");
  if(stalled&&{out_token,out_beat,out_last,out_data}!==held)$fatal(1,"held response changed");
  stalled=out_valid&&!out_ready;held={out_token,out_beat,out_last,out_data};
  if(out_valid&&out_ready)begin
   if(seen>=160||out_data!==expected[seen])$fatal(1,"payload beat %0d",seen);
   if(out_token!==tokens[seen/16]||out_beat!==seen%16||out_last!==(seen%16==15))$fatal(1,"token/order");
   seen=seen+1;
  end
 end
 always @(negedge clk)if(rst_n)out_ready<=($random(seed)&3)!=0&&cyc%50>15;
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR");
  if($test$plusargs("MUTANT"))$readmemh({dir,"/expected_negative.hex"},expected);else $readmemh({dir,"/expected.hex"},expected);
  TOKENS
  repeat(5)@(negedge clk);rst_n=1;
  for(j=0;j<10;j=j+1)begin
   while(!req_ready)@(negedge clk);req_valid=1;req_token=tokens[j];@(negedge clk);req_valid=0;
   while(seen<16*(j+1))@(negedge clk);
  end
  while(!req_ready)@(negedge clk);req_valid=1;req_token=129280;@(negedge clk);req_valid=0;
  if(!fault_valid||fault_token!=129280)$fatal(1,"negative token bounds");
  req_valid=1;req_token=131071;@(negedge clk);req_valid=0;
  if(!fault_valid||fault_token!=131071)$fatal(1,"max token bounds");
  repeat(20)@(negedge clk);if(seen!=160||out_valid||dut.bank_re!=0)$fatal(1,"invalid address read");
  if(highwater!=8||full_stop==0)$fatal(1,"full credit bound not exercised");
  // A malformed pair caller must not overwrite a held macro output.
  guard_re=1;guard_addr=0;@(negedge clk);guard_addr=2;#0.001;
  if(guard.m0.ce_in)$fatal(1,"same-parity read reached ROM");
  @(negedge clk);guard_re=0;repeat(4)@(negedge clk);
  if(!guard_fault||guard_valid)$fatal(1,"pair interval violation not failclosed");
  if(cyc!=412)$fatal(1,"changed valid cadence versus pinned PP gate: %0d",cyc);
  $display("PASS LOCALCAP lookup actual160beats ROM744ps capture2edges stalls bounds tokenonly defaultoff creditmax=%0d fullstop=%0d cycles=%0d pairintervalfault=1",highwater,full_stop,cyc);$finish;
 end
 initial begin #60000;$fatal(1,"timeout");end
endmodule
'''.replace('TOKENS','\n'.join(f'tokens[{i}]={v};' for i,v in enumerate(TOKENS))))
 src=ROOT/'rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_embed_localcapture.sv';obj=out/'obj'
 p=subprocess.run(['verilator','--binary','--timing','-j','8','-Wno-fatal','--top-module','tb','--Mdir',str(obj),str(src),str(macro),str(tb)],capture_output=True,text=True);(out/'compile.log').write_text(p.stdout+p.stderr)
 if p.returncode:raise RuntimeError(p.stderr)
 results=[]
 for mutant in (False,True):
  p=subprocess.run([str(obj/'Vtb'),f'+DIR={out}',f'+OT_ROM_DIR={images}']+(['+MUTANT'] if mutant else []),capture_output=True,text=True);(out/f'sim{int(mutant)}.log').write_text(p.stdout+p.stderr);print(p.stdout,flush=True)
  results.append(dict(mutant=mutant,exit=p.returncode,passed=(p.returncode!=0 and 'payload beat 0' in p.stdout) if mutant else (p.returncode==0 and 'PASS LOCALCAP lookup' in p.stdout)))
 rec=dict(passed=all(r['passed'] for r in results),results=results,tokens=TOKENS,checked_beats=160,scope='released lookup component; direct local512FF pair capture and post-mux; same valid cadence412cycles, credit8 with pipeline6, token-only bounds, held output; not full-head physical closure',released=meta,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [src,Path(__file__),ROOT/'tools/dsrom_markov_embed_image_pp.py',ROOT/'tools/uarch_model_dsrom_markov_embed_localcapture.py']},physical_qualified=False)
 (out/'verdict.json').write_text(json.dumps(rec,indent=2)+'\n');return rec['passed']
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--snapshot',type=Path,default=DEFAULT);a=ap.parse_args();raise SystemExit(0 if run(a.out.resolve(),a.snapshot) else 1)
