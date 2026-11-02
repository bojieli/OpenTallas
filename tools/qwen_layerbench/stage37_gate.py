#!/usr/bin/env python3
"""Prepare the smallest native loader gate for the unadopted HEAD37 event.

Synthetic per-user PROG/CROM data exercise transport, not HEAD arithmetic or a
production address allocation. The unchanged real ROM read model is required.
"""
import argparse
import json
from pathlib import Path
import programme_store as P
import monitor_tail as M
from test_stage37_store import head_manifest


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--reference',type=Path,required=True)
    ap.add_argument('--rom-model',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[2]
    m=head_manifest();images=P.logical_images(m,head_stage37=True);tail=M.tails(m,head_stage37=True)
    for lane in range(4):
        old=('\n'.join(f'{w:0532x}' for w in P.physical_rows(images[1],lane))+'\n').encode()
        (a.out/f'table_s1_m{lane}.viamap.hex').write_bytes(M.repack(old,tail[1],lane,tail_base=3922))
    expected=[];counts=[]
    for stage in (1,36,37):
        for user in range(4):
            row=P.read_rows(stage,user,head_stage37=True)
            words=[images[1][r] for r in row]+tail[1][2*user:2*user+2]
            words=[P.relocate_word(w,user,btab_compact=True,head=stage==37) for w in words if w]
            expected+=words;counts.append(len(words))
    (a.out/'expected.hex').write_text(''.join(f'{w:0266x}\n' for w in expected))
    source=(root/'rtl/qwen_dv/qfd_dv_table_rom_loader.sv').read_text()
    (a.out/'candidate.sv').write_text(source)
    original=a.reference.read_text().split('endmodule',1)[0]+'endmodule\n'
    (a.out/'reference.sv').write_text(original.replace('qfd_dv_table_rom_loader','reference_loader'))
    (a.out/'rom.v').write_bytes(a.rom_model.read_bytes())
    sv='''`timescale 1ns/1fs
module tb_stage37;
reg ck=0;always #0.4165 ck=~ck;reg rst_n=0,start=0;reg[5:0]stage=0;reg[1:0]user_id=0;
wire[3:0]we,busy,done,fault;wire[23:0]addr[0:3];wire[1:0]kind[0:3];wire[1023:0]data[0:3];
reg[1063:0]expected[0:TOTAL-1];integer pos=0,n=0,cyc=0,origin=0,firstw,lastw,last0,done0,done1;
integer st,u,checks=0,windows=0;reg checking=0;reg[1063:0]got;
qfd_dv_table_rom_loader #(.SLICE(1),.BTAB_COMPACT(1),.WE_COPIES(34),.HEAD_STAGE37(1),.MONITOR_TAIL(1)) h
(.ck(ck),.rst_n(rst_n),.start(start),.stage(stage),.user_id(user_id),.other_table_write(1'b0),.tw_we(we[0]),.tw_addr(addr[0]),.tw_kind(kind[0]),.tw_data(data[0]),.busy(busy[0]),.done(done[0]),.fault(fault[0]),.tw_we_k());
qfd_dv_table_rom_loader #(.SLICE(1),.BTAB_COMPACT(1),.WE_COPIES(34),.HEAD_STAGE37(1)) s
(.ck(ck),.rst_n(rst_n),.start(start),.stage(stage),.user_id(user_id),.other_table_write(1'b0),.tw_we(we[1]),.tw_addr(addr[1]),.tw_kind(kind[1]),.tw_data(data[1]),.busy(busy[1]),.done(done[1]),.fault(fault[1]),.tw_we_k());
qfd_dv_table_rom_loader #(.SLICE(1),.BTAB_COMPACT(1),.WE_COPIES(34)) d
(.ck(ck),.rst_n(rst_n),.start(start),.stage(stage),.user_id(user_id),.other_table_write(1'b0),.tw_we(we[2]),.tw_addr(addr[2]),.tw_kind(kind[2]),.tw_data(data[2]),.busy(busy[2]),.done(done[2]),.fault(fault[2]),.tw_we_k());
reference_loader #(.SLICE(1),.BTAB_COMPACT(1),.WE_COPIES(34)) r
(.ck(ck),.rst_n(rst_n),.start(start),.stage(stage),.user_id(user_id),.other_table_write(1'b0),.tw_we(we[3]),.tw_addr(addr[3]),.tw_kind(kind[3]),.tw_data(data[3]),.busy(busy[3]),.done(done[3]),.fault(fault[3]),.tw_we_k());
initial begin
 $readmemh("EXPECTED",expected);
 #0.001;
 if($test$plusargs("MUT_GAIN"))begin h.m0.arr[486][2]=~h.m0.arr[486][2];end
 if($test$plusargs("MUT_MONITOR"))begin h.m0.arr[490][2]=~h.m0.arr[490][2];end
 if($test$plusargs("MUT_SHARED"))begin h.m3.arr[480][1832]=~h.m3.arr[480][1832];end
 for(st=0;st<3;st=st+1)for(u=0;u<4;u=u+1)begin
  checking=0;rst_n=0;repeat(8)@(negedge ck);rst_n=1;repeat(8)@(negedge ck);
  stage=(st==0)?1:(st==1?36:37);user_id=2'(u);start=1;checking=1;
  n=0;firstw=-1;lastw=-1;last0=-1;done0=-1;done1=-1;origin=cyc+1;
  @(negedge ck);start=0;repeat(110)@(negedge ck);
  if(n!=(st==2?82:90)||fault[1:0]!=0)$fatal(1,"HEAD_COUNT_FAULT %0d %b",n,fault);
  if(firstw!=4||lastw!=93||last0!=(st==2?83:91)||done0!=93||done1!=91)$fatal(1,"DATES first%0d last%0d/%0d done%0d/%0d",firstw,lastw,last0,done0,done1);
  if(st==2&&fault[3:2]!=2'b11)$fatal(1,"DEFAULT_STAGE37_NOT_REJECTED");
  $display("HEAD37_CASE stage%0d user%0d writes%0d sharedBTAB50 first4 last93 defaultLOCKSTEP",stage,u,n);windows=windows+1;
 end
 $display("HEAD37_LOADER_PASS windows%0d writes%0d nativeROM_readpath333? period833ps defaultLOCKSTEP",windows,checks);$finish;
end
always @(posedge ck)begin
 cyc=cyc+1;
 if(checking&&rst_n)begin
  if({we[2],busy[2],done[2],fault[2]}!=={we[3],busy[3],done[3],fault[3]})$fatal(1,"DEFAULT_CONTROL_LOCKSTEP");
  if(we[2]&&{kind[2],addr[2],data[2]}!=={kind[3],addr[3],data[3]})$fatal(1,"DEFAULT_PAYLOAD_LOCKSTEP");
  if(stage<=36)begin
   if({we[1],busy[1],done[1],fault[1]}!=={we[3],busy[3],done[3],fault[3]})$fatal(1,"PREFIX_CONTROL_LOCKSTEP");
   if(we[1]&&{kind[1],addr[1],data[1]}!=={kind[3],addr[3],data[3]})$fatal(1,"PREFIX_PAYLOAD_LOCKSTEP");
  end
  if(done[0])done0=cyc-origin;if(done[1])done1=cyc-origin;if(we[1])last0=cyc-origin;
  if(we[0])begin
   if(n==0)firstw=cyc-origin;lastw=cyc-origin;
   got={13'd0,addr[0],kind[0],1'b1,data[0]};
   if(got!==expected[pos])$fatal(1,"HEAD_PAYLOAD stage%0d user%0d n%0d got%h exp%h",stage,user_id,n,got,expected[pos]);
   pos=pos+1;n=n+1;checks=checks+1;
  end
 end
end
endmodule
'''
    sv=sv.replace('TOTAL',str(len(expected))).replace('EXPECTED',str(a.out/'expected.hex')).replace('readpath333?','readpath')
    (a.out/'tb.sv').write_text(sv)
    (a.out/'scope.json').write_text(json.dumps(dict(status='PREP_ONLY',synthetic_transport_fixture=True,
        reference=str(a.reference),expected_writes=len(expected),stages=[1,36,37],users=4,
        native_head_arithmetic='NOT_RUN',production_allocation='NOT_SELECTED'),indent=2)+'\n')

if __name__=='__main__':main()
