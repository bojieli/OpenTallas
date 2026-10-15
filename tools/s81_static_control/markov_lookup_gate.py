"""Full506-real-ROM static lookup: released fulltable and fixedslot bit proof."""
from pathlib import Path
import argparse,json,subprocess,hashlib
from markov_static_image import generate
ROOT=Path(__file__).resolve().parents[2]
TOKENS=[0,255,256,511,512,8191,8192,129023,129024,129279]

def run(args):
 out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
 meta=generate(args.payload,args.source,out/'images');raw=args.payload.read_bytes()
 values=[]
 for token in TOKENS:
  row=raw[token*512:(token+1)*512]
  values.extend(int.from_bytes(row[b*32:(b+1)*32],'little')for b in range(16))
 (out/'expected.hex').write_text(''.join(f'{w:064x}\n'for w in values))
 macro=ROOT/'physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v'
 # Actual physical macro model, with its measured SS clk->q for this gate.
 timed=out/'macro_ss.v';timed.write_text(macro.read_text().replace('rd_out <= word_read(addr_in)','rd_out <= #0.744 word_read(addr_in)'))
 tb=out/'tb.sv';tb.write_text('''`timescale 1ns/1ps
module tb;
 reg clk=0;always #0.4165 clk=~clk;reg rst_n=0,request_slot=0;
 reg[16:0]token=0;reg[59:0]identity=0;
 wire word_v,fault;wire[255:0]word_data;wire[3:0]word_beat;wire[16:0]word_token;wire[59:0]word_identity;
 ot_dsrom_markov_embed_static dut(.clk(clk),.rst_n(rst_n),.clk_pair({253{clk}}),.clk_group({16{clk}}),
 .request_slot(request_slot),.token(token),.identity(identity),.word_v(word_v),.word_data(word_data),.word_beat(word_beat),.word_token(word_token),.word_identity(word_identity),.fault(fault));
 reg[255:0]expected[0:159];integer tokens[0:9];integer j,seen=0,cycle=0,reqcycle=0,mode=0,invalidseen=0;
 initial begin
  if($value$plusargs("mode=%d",mode))begin end
  $readmemh("expected.hex",expected);TOKENS
  repeat(6)@(negedge clk);rst_n=1;repeat(5)@(negedge clk);
  for(j=0;j<10;j=j+1)begin
   request_slot=1;token=tokens[j];identity=60'h123456700000000+j;
   @(negedge clk);request_slot=0;token=131071;identity=0;
   repeat(23)@(negedge clk);
  end
  if(seen!=160||fault)$fatal(1,"full lookup data/fault seen%0d fault%0d",seen,fault);
  // Invalid identity produces the same16scheduledbeats and stickyfault;
  // it cannot silently turn into a valid in-range embedding request.
  token=129280;identity=60'hbad;request_slot=1;@(negedge clk);request_slot=0;
  repeat(24)@(negedge clk);
  if(!fault||invalidseen!=16)$fatal(1,"invalidtoken fixedfault timeline %0d",invalidseen);
  $display("PASS staticfull506ROM lookup tokens10 releasedbeats160 invalidbeats16 first6 last21 noqueue nocredits");$finish;
 end
 always @(posedge clk)begin
  cycle=cycle+1;if(request_slot)reqcycle=cycle;#0.001;
  if(word_v)begin
   if(cycle!=reqcycle+6+word_beat)$fatal(1,"fixed lookup edge shifted cycle%0d request%0d beat%0d",cycle,reqcycle,word_beat);
   if(word_token==129280)invalidseen=invalidseen+1;
   else begin
    if(seen>=160||word_token!=tokens[seen/16]||word_identity!=60'h123456700000000+seen/16||word_beat!=seen%16)$fatal(1,"lookup prefix identity/order");
    if(word_data!==(expected[seen]^(mode==1&&seen==0?256'd1:256'd0)))$fatal(1,"lookup realreleasedpayload beat%0d",seen);
    seen=seen+1;
   end
  end
 end
 initial begin #1000;$fatal(1,"timeout");end
endmodule
'''.replace('TOKENS','\n'.join(f'tokens[{i}]={token};'for i,token in enumerate(TOKENS))))
 src=ROOT/'rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_embed_static.sv'
 cmd=['verilator','--binary','--timing','-j',str(args.jobs),'-Wno-fatal','--top-module','tb','--Mdir',str(out/'obj'),str(src),str(timed),str(tb)]
 with (out/'build.log').open('w')as log:
  rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
 if rc:raise SystemExit(rc)
 cases=[]
 for mode in (0,1):
  p=subprocess.run([str(out/'obj/Vtb'),f'+OT_ROM_DIR={out}/images',f'+mode={mode}'],cwd=out,capture_output=True,text=True)
  (out/f'mode{mode}.log').write_text(p.stdout+p.stderr);print(p.stdout,flush=True)
  passed=p.returncode==0 if mode==0 else p.returncode!=0 and 'lookup realreleasedpayload beat0'in p.stdout
  cases.append(dict(mode=mode,exit=p.returncode,passed=passed))
  if not passed:raise SystemExit(1)
 # Independently decode all true released rows from every physical via map.
 spread_inverse=[b*8 for b in range(256)]
 digest=hashlib.sha256()
 physical={m:(out/'images'/f'macro{m:03}.viamap.hex').read_text().splitlines()for m in range(506)}
 for global_word in range(129280*16):
  bank,offset=divmod(global_word,8192);macroindex=2*bank+offset%2;addr=offset//2
  row=int(physical[macroindex][addr//8],16);par=addr%8
  value=sum(((row>>(b*8+par))&1)<<b for b in range(256));digest.update(value.to_bytes(32,'little'))
 if digest.hexdigest()!=meta['payload_sha256']:raise ValueError('fullphysicaltable readback differs releasedbytes')
 receipt=dict(scope='actual full506ROM Etable staticlookup; realWtable/headlogit callers and physical clocks remain separate',native_full_head=False,physical_qualified=False,full_table_independent_via_readback_sha256=digest.hexdigest(),released=meta,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in (src,macro,Path(__file__),ROOT/'tools/s81_static_control/markov_static_image.py')},timed_model_sha256=hashlib.sha256(timed.read_bytes()).hexdigest(),cases=cases,tokens=TOKENS,first_word_edges=6,last_word_edges=21)
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--payload',type=Path,required=True);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--jobs',type=int,default=4);run(ap.parse_args())
