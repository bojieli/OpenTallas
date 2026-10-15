#!/usr/bin/env python3
"""Actual SRAM->row packet codec->actual SRAM/decode component gate.

This local codec gate is not the nine-rank endpoint/FEC operation proof.
"""
import argparse,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[2]
TB=r'''`timescale 1ns/1ps
module tb;
 reg clk=0,rst_n=0,epoch=0;
 integer cycle,phase,e,mut=0,rawchecks=0,checks=0,packets=0;
 reg[255:0] sectors[0:431];reg[511:0] golden[0:383];
 reg sw=0,sr=0,dr=0;reg[4:0]swrow,srrow,drrow;reg[3:0]swsec,srsec,drsec;reg[255:0]swd;
 wire rv;wire[4:0]rr;wire[3:0]rs;wire[255:0]rd;wire sf;
 reg rexp,low,pub;reg[4:0]prow;reg[2:0]pair;
 wire pv;wire[544:0]pd;wire pf;
 reg avexp;reg[4:0]arow;reg[2:0]apair;
 wire av;wire[4:0]awrow;wire[3:0]awsec;wire[255:0]awd;wire af;
 wire dv,drv;wire[4:0]drow,drrowo;wire[2:0]db;wire[3:0]drseco;wire[511:0]dd;wire[255:0]drd;wire df;
 wire[544:0]wiredata=pd ^ ((mut==1 && pd[527:512]%5==4)?(545'b1<<300):545'b0);
 ot_hbm_engram_row_store_decode #(.DECODE_ENABLE(0)) source(.clk(clk),.rst_n(rst_n),.epoch_begin(epoch),
 .write_v(sw),.write_row(swrow),.write_sector(swsec),.write_data(swd),.read_v(sr),.read_row(srrow),.read_sector(srsec),
 .out_v(),.out_row(),.out_block(),.out_data(),.raw_v(rv),.raw_row(rr),.raw_sector(rs),.raw_data(rd),.fault(sf));
 ot_hcoll_engram_row_packetizer packet(.clk(clk),.rst_n(rst_n),.epoch_begin(epoch),.raw_v(rv),.raw_row(rr),.raw_sector(rs),.raw_data(rd),
 .expect_raw_v(rexp),.capture_low(low),.publish_v(pub),.publish_row(prow),.publish_pair(pair),.out_v(pv),.out_flit(pd),.fault(pf));
 ot_hcoll_engram_row_assembler assemble(.clk(clk),.rst_n(rst_n),.epoch_begin(epoch),.in_v(pv && !(mut==2&&phase==313)),.in_flit(wiredata),
 .expect_v(avexp),.expect_row(arow),.expect_pair(apair),.expect_home(8'b0),.write_v(av),.write_row(awrow),.write_sector(awsec),.write_data(awd),.fault(af));
 ot_hbm_engram_row_store_decode consumer(.clk(clk),.rst_n(rst_n),.epoch_begin(epoch),.write_v(av),.write_row(awrow),.write_sector(awsec),.write_data(awd),
 .read_v(dr),.read_row(drrow),.read_sector(drsec),.out_v(dv),.out_row(drow),.out_block(db),.out_data(dd),
 .raw_v(drv),.raw_row(drrowo),.raw_sector(drseco),.raw_data(drd),.fault(df));
 initial begin
  if($value$plusargs("mut=%d",mut))begin end
  $readmemh("external_hbm_sectors.hex",sectors);$readmemh("expected_bf16.hex",golden);
  for(cycle=0;cycle<1800;cycle=cycle+1)begin
   e=cycle/900;phase=cycle%900;rst_n=cycle>=8;epoch=phase==12;
   sw=0;sr=0;dr=0;rexp=0;low=0;pub=0;avexp=0;prow=0;pair=0;arow=0;apair=0;
   if(phase>=20&&phase<236)begin sw=1;swrow=5'((phase-20)/9);swsec=4'((phase-20)%9);swd=sectors[e*216+phase-20];end
   for(integer row=0;row<24;row=row+1)begin
    for(integer s=0;s<9;s=s+1)begin
     if(phase==300+row*12+(s==8?9:s))begin sr=1;srrow=5'(row);srsec=4'(s);end
     if(phase==304+row*12+(s==8?9:s))begin
      rexp=1;low=(s<8 && s%2==0);pub=(s==8 || s%2==1);prow=5'(row);pair=3'(s/2);
     end
     if((s==8||s%2==1)&&phase==306+row*12+(s==8?9:s))begin avexp=1;arow=5'(row);apair=3'(s/2);end
     if(phase==620+row*9+s)begin dr=1;drrow=5'(row);drsec=4'(s==0?8:s-1);end
    end
   end
   #4;clk=1;#1;
   if(pv)packets=packets+1;
   if(drv)begin
    if(drd!==sectors[e*216+drrowo*9+drseco])$fatal(1,"rawcodec mismatch row%0d sec%0d",drrowo,drseco);
    rawchecks=rawchecks+1;
   end
   if(dv)begin
    if(dd!==golden[e*192+drow*8+db])$fatal(1,"decode mismatch row%0d block%0d",drow,db);
    checks=checks+1;
   end
   if(mut==0&&(sf||pf||af||df))$fatal(1,"codec fault cycle%0d %b%b%b%b",cycle,sf,pf,af,df);
   if(phase==860)begin
    if(mut==1&&!af)$fatal(1,"tailmutant escaped");
    if(mut==2&&!af)$fatal(1,"missingpacket mutant escaped");
   end
   #5;clk=0;
  end
  if(checks!=384||rawchecks!=432||packets!=240)$fatal(1,"coverage%0d/%0d/%0d",checks,rawchecks,packets);
  $display("ENGRAM_CODEC PASS mut%0d actual4SRAM epochs2 rows48 packets240 sectors432 blocks384 BF1612288",mut);$finish;
 end
endmodule
'''
def run(out,inputs):
 out=out.resolve();out.mkdir(parents=True,exist_ok=True)
 receipt=json.loads((inputs/'receipt.json').read_text())
 for name in ['external_hbm_sectors.hex','expected_bf16.hex']:
  data=(inputs/name).read_bytes();assert hashlib.sha256(data).hexdigest()==receipt['data_sha256'][name]
  (out/name).write_bytes(data)
 (out/'tb.sv').write_text(TB)
 paths=['physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v','rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv','rtl/hdc/v41/ot_hdc_engram_gather.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_row_store_decode.sv','rtl/hbm_accel/generic/collective/p2p/ot_hcoll_engram_row_transport.sv']
 cp=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(out/'sim'),*[str(ROOT/x) for x in paths],str(out/'tb.sv')],capture_output=True,text=True)
 (out/'build.log').write_text(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stderr
 runs=[]
 for mutant in [0,1,2]:
  rp=subprocess.run(['vvp',str(out/'sim'),f'+mut={mutant}'],cwd=out,capture_output=True,text=True)
  (out/f'm{mutant}.log').write_text(rp.stdout+rp.stderr);assert rp.returncode==0,rp.stdout+rp.stderr
  runs.append(dict(mutant=mutant,returncode=rp.returncode,output=rp.stdout.strip()))
 r=dict(status='PASS codec component only',rows=48,epochs=2,native_SRAMs=4,packets=240,raw_sectors=432,decoded_blocks=384,BF16_values=12288,runs=runs,source_sha256={x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in paths},qualification='Local native SRAM/codec/decode only; no nine-rank endpoint/FEC/clock/physical/wholeROW_GATHER claim')
 (out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=pathlib.Path);p.add_argument('--inputs',type=pathlib.Path,required=True);a=p.parse_args();run(a.out,a.inputs)
