#!/usr/bin/env python3
"""Minimum component gate: actual tensor rows, real macro clkq, stalls/bounds/identity."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from dsrom_markov_embed_image import generate,DEFAULT
from uarch_model_dsrom_markov_embed import model
ROOT=Path(__file__).resolve().parents[1]
TOKENS=[0,255,256,511,512,8191,8192,129023,129024,129279]

def run(out,snapshot):
    out.mkdir(parents=True,exist_ok=False)
    (out/'model.json').write_text(json.dumps(model(),indent=2)+'\n')
    meta=generate(snapshot,out/'images',TOKENS)
    rtl=ROOT/'rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_embed_port.sv'
    (out/'rtl_pin.json').write_text(json.dumps(dict(source=str(rtl.relative_to(ROOT)),sha256=hashlib.sha256(rtl.read_bytes()).hexdigest()),indent=2)+'\n')
    sources=[rtl,Path(__file__).resolve(),ROOT/'tools/dsrom_markov_embed_image.py',ROOT/'tools/uarch_model_dsrom_markov_embed.py',ROOT/'tools/uarch_model.py']
    (out/'source_pins.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},indent=2)+'\n')
    rows=[]
    for tok in TOKENS:
        row=bytes.fromhex(meta['selected_rows'][str(tok)])
        rows.extend(f'{int.from_bytes(row[i*32:(i+1)*32],"little"):064x}' for i in range(16))
    (out/'expected.hex').write_text('\n'.join(rows)+'\n')
    tb=['''`timescale 1ns/1ps
module macro4096 #(parameter FILE="")(input clk,re,input [11:0] addr,output reg [255:0] q);
 reg [2191:0] mem[0:511];initial $readmemh(FILE,mem);
 reg[255:0] data;integer b;always @(posedge clk) if(re)begin
 for(b=0;b<256;b=b+1)data[b]=mem[addr/8][b*8+addr%8];q<=#0.744 data;end
endmodule
module tb;
 reg clk=0;always #0.4165 clk=~clk;
 reg rst_n=0,req_valid=0,out_ready=0;reg[16:0] req_token;reg[31:0] req_id;
 wire req_ready,fault_valid;wire[31:0] fault_id;wire[252:0] bank_re;wire[207:0] bank_addr;
 wire[64767:0] bank_q;wire out_valid,out_last;wire[255:0] out_data;wire[31:0] out_id;wire[3:0] out_beat;
 ot_dsrom_markov_embed_port #(.ENABLE(1)) d(.*);
 wire disabled_ready;ot_dsrom_markov_embed_port disabled(.clk(clk),.rst_n(rst_n),.req_valid(1'b1),.req_ready(disabled_ready),.req_token(17'd0),.req_id(32'd0),.bank_q(bank_q),.out_ready(1'b1));
 reg[255:0] expected[0:159];integer tokens[0:9];integer j,k,seen=0,cycles=0,seed=77;
 reg[292:0] held;reg stalled=0;integer highwater=0,full_stop=0;
 always @(posedge clk) if(rst_n) begin
  cycles=cycles+1;if(cycles>3000)$fatal(1,"timeout");
  if(disabled_ready)$fatal(1,"default opt-in violated");
  if(d.reserved>highwater)highwater=d.reserved;
  if(d.reserved==8 && !d.issue)full_stop=full_stop+1;
  if(d.reserved>8 || d.count>d.reserved)$fatal(1,"reservation overflow");
  if(stalled && {out_id,out_beat,out_last,out_data}!==held)$fatal(1,"backpressure changed beat");
  stalled=out_valid&&!out_ready;held={out_id,out_beat,out_last,out_data};
  if(out_valid&&out_ready) begin
   if(out_data!==expected[seen])$fatal(1,"payload beat %0d",seen);
   if(out_id!==32'habc000+seen/16 || out_beat!==seen%16 || out_last!==(seen%16==15))$fatal(1,"identity/order");
   seen=seen+1;
  end
 end
 always @(negedge clk) if(rst_n) out_ready<=($random(seed)&3)!=0 && cycles%50>15;
''']
    for bank in range(253):
        if (out/'images'/f'macro{bank*2:03}.hex').exists() or (out/'images'/f'macro{bank*2+1:03}.hex').exists():
            for m in [0,1]:
                image=out/'images'/f'macro{bank*2+m:03}.viamap.hex'
                if not image.exists():image.write_text(('0'*548+'\n')*512)
                tb.append(f' wire[255:0] q{bank}_{m}; macro4096 #(.FILE("{image}")) m{bank}_{m}(.clk(clk),.re(bank_re[{bank}] && bank_addr[{bank//16*13+12}]==1\'b{m}),.addr(bank_addr[{bank//16*13}+:12]),.q(q{bank}_{m}));\n')
            tb.append(f' reg s{bank};always @(posedge clk) if(bank_re[{bank}]) s{bank}<=bank_addr[{bank//16*13+12}];assign bank_q[{bank*256}+:256]=s{bank}?q{bank}_1:q{bank}_0;\n')
        else:tb.append(f' assign bank_q[{bank*256}+:256]=0;\n')
    tb.append(' initial begin\n')
    tb.append(f' $readmemh("{out}/expected.hex",expected);\n')
    tb.extend(f' tokens[{i}]={t};\n' for i,t in enumerate(TOKENS))
    tb.append(''' repeat(4)@(negedge clk);rst_n=1;
 for(j=0;j<10;j=j+1)begin
  while(!req_ready)@(negedge clk);
  req_valid=1;req_token=tokens[j];req_id=32'habc000+j;@(negedge clk);req_valid=0;
  while(seen<(j+1)*16)@(negedge clk);
 end
 while(!req_ready)@(negedge clk);
 req_valid=1;req_token=129280;req_id=32'hbad;@(negedge clk);req_valid=0;
 if(!fault_valid || fault_id!=32'hbad)$fatal(1,"negative bounds not rejected");
 req_valid=1;req_token=131071;req_id=32'hbad2;@(negedge clk);req_valid=0;
 if(!fault_valid || fault_id!=32'hbad2)$fatal(1,"max token bounds not rejected");
 repeat(20)@(negedge clk);if(seen!=160 || bank_re!=0 || out_valid)$fatal(1,"invalid address caused reads");
 if(highwater!=8 || full_stop==0)$fatal(1,"full reservation bound not exercised");
 $display("COVER reserved highwater=%0d full-stop cycles=%0d",highwater,full_stop);
 $display("PASS actual released embedding 160 beats, macro744ps, stalls, IDs, bounds, default-off cycles=%0d",cycles);$finish;
 end
endmodule
''')
    bench=out/'tb.sv';bench.write_text(''.join(tb))
    cmd=['iverilog','-g2012','-s','tb','-o',str(out/'sim'),str(rtl),str(bench)]
    p=subprocess.run(cmd,capture_output=True,text=True);(out/'compile.log').write_text(p.stdout+p.stderr)
    if p.returncode:raise RuntimeError(p.stderr)
    p=subprocess.run(['vvp',str(out/'sim')],capture_output=True,text=True);(out/'sim.log').write_text(p.stdout+p.stderr)
    verdict=dict(passed=p.returncode==0 and 'PASS actual released' in p.stdout,scope='minimum component; no SS/FF physical closure; no full-head adoption',tokens=TOKENS,checked_beats=160,clk_period_ps=833,macro_clkq_ss_ps=744)
    negative_rows=rows.copy();negative_rows[0]=f'{int(negative_rows[0],16)^1:064x}'
    (out/'expected_negative.hex').write_text('\n'.join(negative_rows)+'\n')
    negative_bench=out/'tb_negative.sv'
    negative_bench.write_text(bench.read_text().replace(str(out/'expected.hex'),str(out/'expected_negative.hex')))
    np=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(out/'sim_negative'),str(rtl),str(negative_bench)],capture_output=True,text=True)
    (out/'compile_negative.log').write_text(np.stdout+np.stderr)
    if np.returncode:raise RuntimeError(np.stderr)
    np=subprocess.run(['vvp',str(out/'sim_negative')],capture_output=True,text=True)
    (out/'sim_negative.log').write_text(np.stdout+np.stderr)
    negative=dict(passed=False,expected_failure=True,detected=np.returncode!=0 and 'payload beat 0' in np.stdout,mechanism='flip one released golden BF16 bit')
    (out/'negative_verdict.json').write_text(json.dumps(negative,indent=2)+'\n')
    verdict['negative_control_detected']=negative['detected'];verdict['passed'] &= negative['detected']
    (out/'verdict.json').write_text(json.dumps(verdict,indent=2)+'\n')
    print(p.stdout);return verdict
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--snapshot',type=Path,default=DEFAULT)
    a=ap.parse_args();raise SystemExit(0 if run(a.out.resolve(),a.snapshot)['passed'] else 1)
