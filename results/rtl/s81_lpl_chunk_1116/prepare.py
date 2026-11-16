from pathlib import Path
import subprocess,re,json,sys
w=Path(sys.argv[1]);o=Path(sys.argv[2]);o.mkdir(exist_ok=True)
src=subprocess.check_output(['git','-C',str(w),'show','HEAD:rtl/common/landed_parent/ot_pl_land.sv'],text=True)
(o/'source.sv').write_text(src)
tb="module tb;\nreg wclk=0,rclk=0,rsi=0;\nreg [543:0] data=0;\nwire [2175:0] bb,cb;wire[11:0] be,ce;wire[3:0] bv,cv;\nwire[543:0] bo,co;\nbase_ot_pl_land_w #(.W(544),.D(4)) bw(wclk,rsi,data,bb,be,bv);\nbase_ot_pl_land_r #(.W(544),.D(4),.K(2)) br(rclk,rsi,bb,be,bv,bo);\ncand_ot_pl_land_w #(.W(544),.D(4)) cw(wclk,rsi,data,cb,ce,cv);\ncand_ot_pl_land_r #(.W(544),.D(4),.K(2)) cr(rclk,rsi,cb,ce,cv,co);\nalways #5 wclk=~wclk;\ninitial begin #0.2;forever #5 rclk=~rclk;end\ninteger wc=0,seed=32'h52ca1734,checks=0,epochs=0;\nalways @(negedge wclk) begin\n wc=wc+1;\n for(integer j=0;j<17;j=j+1) data[j*32+:32]=$urandom(seed);\n if(wc%317==0)begin rsi=0;epochs=epochs+1;end\n if(wc%317==7)rsi=1;\nend\ninitial begin\n for(integer n=0;n<20000;n=n+1)begin\n  @(posedge rclk);#0.01;\n  if(n>3)begin\n   if(bv!==cv)$fatal(1,\"VALID cycle%0d\",n);\n   for(integer j=0;j<4;j=j+1)if(bv[j])begin\n    if(bb[j*544+:544]!==cb[j*544+:544])$fatal(1,\"BANK cycle%0d slot%0d\",n,j);\n    if(be[j*3+:3]!==ce[j*3+:3])$fatal(1,\"EPOCH cycle%0d slot%0d\",n,j);\n   end\n   if(bo!==co)$fatal(1,\"OUTPUT cycle%0d\",n);\n   checks=checks+1;\n  end\n end\n $display(\"PASS LPL_CHUNK current W544 D4 K2 checks%0d resets%0d words_per_cycle1 latency_delta0 chunks23\",checks,epochs);\n $finish;\nend\nendmodule\n"
(o/'tb.sv').write_text(chr(96)+'timescale 1ns/1ps\n'+tb)
for tag,prefix,defs in [('base','base_',[]),('chunk','cand_',['OT_S81_LPL_CHUNK']),('mutant','cand_',['OT_S81_LPL_CHUNK','LPLC_MUT_K'])]:
 for synth in (False,True) if tag!='mutant' else (False,):
  out=o/(tag+('_synth' if synth else '')+'.sv')
  subprocess.run(['iverilog','-g2012','-E',*['-D'+d for d in defs+(['SYNTHESIS','OT_S81_RCK_RELAY4'] if synth else [])],'-o',str(out),str(o/'source.sv')],check=True)
  out.write_text(re.sub(r'\bot_pl_',prefix+'ot_pl_',out.read_text()))
for tag in ('base','chunk'):
 prefix='base_' if tag=='base' else 'cand_'
 text=f'module top(input wclk,rclk,rsi,input[543:0]i,output[543:0]o);wire[2175:0]bank;wire[11:0]epo;wire[3:0]vld;{prefix}ot_pl_land_w #(.W(544),.D(4)) w(wclk,rsi,i,bank,epo,vld);{prefix}ot_pl_land_r #(.W(544),.D(4),.K(2)) r(rclk,rsi,bank,epo,vld,o);endmodule\n'
 (o/(tag+'_top.sv')).write_text(text)
