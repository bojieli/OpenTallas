#!/usr/bin/env python3
"""Emit a minimum native SRAM/stream/FIFO lockstep vehicle, run via plain ot-run.

The baseline is an actual routed kit's ot_s81hd_ctl_hsf0_static.sv. This checks
that mechanism, not the entire controller. --sram-model must name its production
64x512 behavioral model. Generated run.sh checks default-off separately and the
+1 N/S output cycle, read count, FIFO identity, earliest legal START, reset, and
select/go/bank/extra-read mutants. Physical locality, full kit LEC and compiler
latency adoption remain separate gates.
"""
from pathlib import Path
import argparse, re, hashlib, json
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--baseline',type=Path,required=True)
ap.add_argument('--sram-model',type=Path,required=True)
ap.add_argument('--out',type=Path,required=True)
ap.add_argument('--mode',choices=['raw','partial'],default='raw')
ap.add_argument('--raw-baseline',type=Path)
a=ap.parse_args(); assert a.mode != 'partial' or a.raw_baseline is not None; O=a.out; O.mkdir(parents=True,exist_ok=False)
T=Path(__file__).resolve().parents[2]/'rtl/dsrom_sys/s81_head'
old=a.baseline.read_text();new=(T/'ot_s81hd_ctl_hsf0_static.sv').read_text()
(O/'sram.v').write_bytes(a.sram_model.read_bytes())
(O/'INPUTS.json').write_text(json.dumps(dict(baseline=str(a.baseline),baseline_sha256=hashlib.sha256(a.baseline.read_bytes()).hexdigest(),sram_sha256=hashlib.sha256(a.sram_model.read_bytes()).hexdigest(),mode=a.mode,raw_baseline=str(a.raw_baseline) if a.raw_baseline else None,raw_baseline_sha256=hashlib.sha256(a.raw_baseline.read_bytes()).hexdigest() if a.raw_baseline else None,scope='actual native SRAM/stream/tag-FIFO mechanism only; not full-controller LEC'),indent=1)+'\n')
def vehicle(text,name,newer=False):
 block=text.split('    // ================================================================== X STORE',1)[1].split('    // ================================================================== N/S FINAL',1)[0]
 block=block[block.index('\n'):].replace('    reg ctlf_q;','').replace('    wire nsf_fire;','').replace('    reg [13:0] n;','')
 drain=''
 if newer:drain=text.split('    reg sram_drain;',1)[1].split('    reg mt_v;',1)[0];drain='    reg sram_drain;'+drain
 return '''module NAME #(parameter SRAM_RAW_CAPTURE=0, parameter SRAM_PARTIAL_CAPTURE=0)(input ck,rst_n,start,wv2,ctlf_q,nsf_fire,input[6:0]wa2,input[1023:0]wd2,input[30:0]mt_tag,input mt_v,output[564:0]sn_o,ss_o,output busy_o,read_o,output[11:0]addr_o,output[30:0]tag_o,output[1:0]count_o);
 localparam integer SK=11, NSL=8192+7*SK, NEND=5+NSL;
 wire[23:0]rr={24{rst_n}};wire wa_xa=wa2<7'd64;
 reg busy;reg[13:0]n;reg[20:0]upos;genvar k,g;integer i;
 DRAIN
 BLOCK
 assign busy_o=BUSY;assign read_o=xv0;assign addr_o={m0[7:2],2'b00,m0[5:2]};assign tag_o=tf_head;assign count_o=tfn;
 endmodule
 '''.replace('NAME',name).replace('DRAIN',drain).replace('BLOCK',block).replace('BUSY','stream_busy' if newer else 'busy')
oldv=vehicle(old,'old_stream');newv=vehicle(new,'new_stream',True)
util=(T/'ot_s81hd_util.sv').read_text();kf=re.search(r'module ot_s81hd_kf\b.*?endmodule',util,re.S).group(0)
(O/'old.v').write_text(oldv+'\n'+kf+'\n')
(O/'new.v').write_text(newv)
if a.mode == 'partial':
 rawv=vehicle(a.raw_baseline.read_text(),'raw_stream',True)
 (O/'raw.v').write_text(rawv)

variants={
 'select':newv.replace('.d(sa_c[z])','.d(sa_n[z%4])').replace('.d(sb_c[z])','.d(sb_n[z%4])'),
 'go':newv.replace('SRAM_RAW_CAPTURE != 0 ? go3 : go2','SRAM_RAW_CAPTURE != 0 ? go2 : go2').replace('(SRAM_RAW_CAPTURE != 0 || SRAM_PARTIAL_CAPTURE != 0) ? go3 : go2','(SRAM_RAW_CAPTURE != 0 || SRAM_PARTIAL_CAPTURE != 0) ? go2 : go2'),
 'bank':newv.replace('rb0_q <= rb0','rb0_q <= rb1'),
 'extra_read':newv.replace('wire xv0 = busy &&','wire xv0 = (busy || sram_drain) &&'),
}
if a.mode == 'partial':
 variants['select']=newv.replace('(sa_c[4*(t/32)+0] & ra0[t])','(sa_n[0] & ra0[t])')
 variants['bank']=newv.replace('(sb_c[4*(t/32)+0] & rb0[t])','(sb_c[4*(t/32)+0] & rb1[t])')
 variants['go']=newv.replace('(SRAM_RAW_CAPTURE != 0 || SRAM_PARTIAL_CAPTURE != 0) ? go3 : go2','(SRAM_RAW_CAPTURE != 0 || SRAM_PARTIAL_CAPTURE != 0) ? go2 : go2')
for n,s in variants.items():assert s!=newv;(O/('new_'+n+'.v')).write_text(s)
tb=r'''module tb;
reg ck=0;always #5 ck=~ck;
reg rst_n=0,start=0,wv2=0,ctlf_q=0,pop0=0,pop1=0,prevpop=0,prevread=0;
reg[6:0]wa2=0;reg[1023:0]wd2=0;reg[30:0]mt_tag=0;reg mt_v=1;
wire[564:0]a,b,c,aa,bb,cc;wire ba,bbusy,bc,ra,rb,rc;wire[11:0]ad,bd,cd;wire[30:0]ta,tbtag,tc;wire[1:0]ca,cb,ccc;
old_stream u0(ck,rst_n,start,wv2,ctlf_q,pop0,wa2,wd2,mt_tag,mt_v,a,aa,ba,ra,ad,ta,ca);
new_stream #(.SRAM_RAW_CAPTURE(1)) u1(ck,rst_n,start,wv2,ctlf_q,pop1,wa2,wd2,mt_tag,mt_v,b,bb,bbusy,rb,bd,tbtag,cb);
new_stream #(.SRAM_RAW_CAPTURE(0)) u2(ck,rst_n,start,wv2,ctlf_q,pop0,wa2,wd2,mt_tag,mt_v,c,cc,bc,rc,cd,tc,ccc);
reg[564:0]delay_a=0,delay_aa=0;reg[30:0]tags[0:7];integer checks=0,cycles=0,warm=0,popdelay=0,p0n=0,p1n=0,reads0=0,reads1=0,issued=0,j,z;
task tick;
begin
 @(negedge ck);
 pop1=prevpop;pop0=0;
 if(prevread&&!ra)popdelay=20;
 prevread=ra;
 if(popdelay>0)begin popdelay=popdelay-1;if(popdelay==0)pop0=1;end
 prevpop=pop0;
 @(posedge ck);
 if(rst_n&&pop0)begin if(ta!==tags[p0n])$fatal(1,"old tag identity %d",p0n);p0n=p0n+1;end
 if(rst_n&&pop1)begin if(tbtag!==tags[p1n])$fatal(1,"new tag identity %d",p1n);p1n=p1n+1;end
 #1;cycles=cycles+1;
 if(!rst_n)warm=0;else warm=warm+1;
 if(ra)reads0=reads0+1;if(rb)reads1=reads1+1;
 if(warm>6)begin
  if(c!==a||cc!==aa||rc!==ra||cd!==ad||bc!==ba||tc!==ta||ccc!==ca)$fatal(1,"default-off mismatch cycle %d",cycles);
  if(rb!==ra||bd!==ad)$fatal(1,"extra/read address mismatch cycle %d",cycles);
  if(b[564:512]!==delay_a[564:512]||bb[564:512]!==delay_aa[564:512])$fatal(1,"go/valid/fault alignment cycle %d",cycles);
  if(delay_a[513]||delay_a[512])begin
   if(b!==delay_a||bb!==delay_aa)$fatal(1,"payload/select/bank alignment cycle %d",cycles);
   checks=checks+1;
  end
 end
 delay_a=a;delay_aa=aa;
end endtask
initial begin
 for(j=0;j<8;j=j+1)tick;rst_n=1;
 for(j=0;j<80;j=j+1)begin
  wv2=1;wa2=j;
  for(z=0;z<32;z=z+1)wd2[z*32+:32]=32'h9e3779b9*(j+1)+z*32'h01010101;
  tick;
 end
 wv2=0;repeat(8)tick;
 for(j=0;j<3;j=j+1)begin
  tags[j]=31'h123400+j*73;mt_tag=tags[j];start=1;tick;start=0;issued=issued+1;
  // Earliest START allowed after the new transport-drain flag clears.
  while(bbusy)begin ctlf_q=cycles%41==0;tick;end
 end
 repeat(40)tick;
 if(p0n!=3||p1n!=3||ca!=0||cb!=0)$fatal(1,"FIFO pop/occupancy failure %d %d %d %d",p0n,p1n,ca,cb);
 if(reads0!=3*(8192+7*11)||reads1!=reads0)$fatal(1,"read count %d %d",reads0,reads1);
 // Reset during an active stream cancels valid work and clears FIFO state.
 mt_tag=31'h445566;start=1;tick;start=0;repeat(25)tick;
 rst_n=0;repeat(5)tick;rst_n=1;repeat(10)tick;
 if(ca!=0||cb!=0||ba||bbusy)$fatal(1,"reset cancellation failed");
 $display("PASS capture lockstep checks=%0d cycles=%0d reads=%0d default_off=PASS tags=%0d/%0d reset=PASS",checks,cycles,reads0,p0n,p1n);$finish;
end
endmodule
'''
if a.mode == 'partial':
 tb=tb.replace('new_stream #(.SRAM_RAW_CAPTURE(1))','new_stream #(.SRAM_PARTIAL_CAPTURE(1))')
 tb=tb.replace('reg[564:0]delay_a', '''wire[564:0]raw_a,raw_aa;wire raw_busy,raw_read;wire[11:0]raw_addr;wire[30:0]raw_tag;wire[1:0]raw_count;
raw_stream #(.SRAM_RAW_CAPTURE(1)) u3(ck,rst_n,start,wv2,ctlf_q,pop1,wa2,wd2,mt_tag,mt_v,raw_a,raw_aa,raw_busy,raw_read,raw_addr,raw_tag,raw_count);
reg[564:0]delay_a''')
 tb=tb.replace('  if(c!==a', '''  if(b[564:512]!==raw_a[564:512]||bb[564:512]!==raw_aa[564:512]||bbusy!==raw_busy||rb!==raw_read||bd!==raw_addr||tbtag!==raw_tag||cb!==raw_count)$fatal(1,"actual-vE raw control/FIFO mismatch cycle %d",cycles);
  if((b[513]||b[512]) && (b!==raw_a||bb!==raw_aa))$fatal(1,"actual-vE raw payload mismatch cycle %d",cycles);
  if(c!==a''')
(O/'tb.sv').write_text(tb)
(O/'run.sh').write_text('''#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
for x in positive select go bank extra_read; do
 f=new.v; [ "$x" = positive ] || f=new_$x.v
 iverilog -g2012 -s tb -o sim_$x old.v "$f" ${raw_file:-} sram.v tb.sv > build_$x.log 2>&1
 if vvp sim_$x > run_$x.log 2>&1; then
   test "$x" = positive || { echo "MUTANT SURVIVED $x"; exit 1; }
   grep -q 'PASS capture lockstep' run_$x.log
 else
   test "$x" != positive || { cat run_$x.log; exit 1; }
   grep -q 'FATAL:' run_$x.log
 fi
 echo "CHECK $x";tail -n 2 run_$x.log
done
''')
if a.mode == 'partial':
 p=O/'run.sh';s=p.read_text().replace('for x in positive','raw_file=raw.v\nfor x in positive');p.write_text(s)
print('Created actual-vD extracted native SRAM/stream/FIFO proof, default-off control, four mutants')
