#!/usr/bin/env python3
"""Actual arbitrary R/W controller -> external command-only DRAM gate."""
from __future__ import annotations
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sector(pc,bank,row,col):
    s=(row<<15)|((((bank>>2)^(row>>2))&7)<<12)|(col<<7)|((bank^row)&3)
    s|=(pc^((s>>7)&31)^((s>>12)&31))<<2
    assert (((s>>2)^(s>>7)^(s>>12))&31)==pc
    assert (((((s>>12)^(row>>2))&7)<<2)|((s^row)&3))==bank
    return s

def bench():
    text='''`timescale 1ps/1fs
module tb;
reg clk=0;always #512 clk=~clk;
reg rst_n=0;reg[31:0]k_v=0,k_we=0;wire[31:0]k_rdy;
reg[959:0]k_addr=0;reg[127:0]k_len=0;reg[543:0]k_tag=0;reg[8191:0]k_wdata=0;reg[1023:0]k_wstrb='1;
wire[31:0]kr_v,k_wr_done;reg[31:0]kr_rdy='1;
wire[543:0]kr_tag;wire[127:0]kr_beat;wire[8191:0]kr_data;
wire[31:0]row_v,col_v,col_we;wire[95:0]row_op;wire[159:0]row_bank,col_bank,col_col;wire[607:0]row_row;
wire[8191:0]col_data;wire[1023:0]col_strb;reg[31:0]dram_rvalid=0;reg[8191:0]dram_rdata=0;wire fault;
ot_hbm_native_sector_stack dut(.*);
integer cyc=0,reads=0,writes=0,acks=0,responses=0,refreshes=0;
reg opened[0:31][0:31];integer current_row[0:31][0:31],act_at[0:31][0:31],pre_at[0:31][0:31],refresh_until[0:31][0:31];
reg[255:0]mem[0:31][0:1];integer memrow[0:1],membank[0:31][0:1],memcol[0:31][0:1];
reg[5:0]due_v[0:31];reg[255:0]due_data[0:31];reg[31:0]wr_posted=0;
reg[31:0]ack_seen=0,rsp_seen=0;integer round_no=0;integer accepted[0:31],max_write=0,max_read=0;
function[255:0]word(input integer pc,input integer roundid);begin word={8{32'hda710000 ^ 32'(pc*731) ^ 32'(roundid*17)}};end endfunction
always @(posedge clk)begin:external_dram
 integer p,b,kind,rr,idx;
 cyc=cyc+1;dram_rvalid<=0;
 if(rst_n)begin
  if(fault)$fatal(1,"native controller fault at%0d",cyc);
  for(p=0;p<32;p=p+1)begin
   if(k_v[p] && k_rdy[p])accepted[p]=cyc;
   if(row_v[p])begin
    b=row_bank[p*5+:5];kind=row_op[p*3+:3];rr=row_row[p*19+:19];
    if(kind==1)begin
     if(opened[p][b] || cyc-pre_at[p][b]<16 || cyc<refresh_until[p][b])$fatal(1,"illegalACT p%0d b%0d cy%0d",p,b,cyc);
     opened[p][b]=1;current_row[p][b]=rr;act_at[p][b]=cyc;
    end else if(kind==0)begin
     if(opened[p][b] && cyc-act_at[p][b]<28)$fatal(1,"earlyPRE");
     opened[p][b]=0;pre_at[p][b]=cyc;
    end else if(kind==6)begin
     if(opened[p][b] || cyc-pre_at[p][b]<16 || cyc<refresh_until[p][b])$fatal(1,"illegalREFpb p%0d b%0d cy%0d",p,b,cyc);
     refresh_until[p][b]=cyc+196;refreshes=refreshes+1;
    end else if(kind!=5)$fatal(1,"unexpectedrowcommand%0d",kind);
   end
   if(col_v[p])begin
    b=col_bank[p*5+:5];
    if(!opened[p][b] || cyc-act_at[p][b]<(col_we[p]?10:19) || cyc<refresh_until[p][b])$fatal(1,"columnbeforeactualACT/tRCD p%0d b%0d",p,b);
    idx=-1;
    for(integer j=0;j<2;j=j+1)if(current_row[p][b]==memrow[j] && b==membank[p][j] && col_col[p*5+:5]==memcol[p][j])idx=j;
    if(idx<0)$fatal(1,"actualphysicalcommandaddresswrong p%0d b%0d row%0d col%0d",p,b,current_row[p][b],col_col[p*5+:5]);
    if(col_we[p])begin
     if(col_strb[p*32+:32]!==32'hffffffff)$fatal(1,"mask");
     mem[p][idx]=col_data[p*256+:256];writes=writes+1;wr_posted[p]<=1;
    end else begin
     if(due_v[p]!=0)$fatal(1,"overlappingphysicalread");
     due_v[p]<=6'b1;due_data[p]<=mem[p][idx];reads=reads+1;
    end
   end
   if(due_v[p]!=0)begin
    due_v[p]<=due_v[p]<<1;
    if(due_v[p][5])begin dram_rvalid[p]<=1;dram_rdata[p*256+:256]<=due_data[p];end
   end
   if(k_wr_done[p])begin
    if(!wr_posted[p] || ack_seen[p])$fatal(1,"enqueueACKorWRduplicate p%0d",p);
    wr_posted[p]<=0;ack_seen[p]=1;acks=acks+1;if(cyc-accepted[p]>max_write)max_write=cyc-accepted[p];
   end
   if(kr_v[p])begin
    if(rsp_seen[p] || kr_tag[p*17+:17]!==17'(round_no*32+p) || kr_beat[p*4+:4]!=0 || kr_data[p*256+:256]!==word(p,round_no/2))$fatal(1,"actualreturnidentity/data p%0d",p);
    rsp_seen[p]=1;responses=responses+1;if(cyc-accepted[p]>max_read)max_read=cyc-accepted[p];
   end
  end
 end
end
task tick;begin @(posedge clk);#1;end endtask
initial begin
 for(integer p=0;p<32;p=p+1)begin
  due_v[p]=0;due_data[p]=0;
  for(integer b=0;b<32;b=b+1)begin opened[p][b]=0;current_row[p][b]=0;act_at[p][b]=-1000;pre_at[p][b]=-1000;refresh_until[p][b]=-1000;end
 end
'''
    for j,row in enumerate([3,821]):
        text+=f'memrow[{j}]={row};\n'
        for p in range(32):
            bank=(p*7+j*11)%32;col=(p*3+j*5)%32
            text+=f'membank[{p}][{j}]={bank};memcol[{p}][{j}]={col};mem[{p}][{j}]=0;\n'
    text+='repeat(4)tick;@(negedge clk);rst_n=1;repeat(32)tick;\n'
    for roundid in range(4):
        j=roundid//2;row=[3,821][j];we=not roundid%2
        text+=f'@(negedge clk);round_no={roundid};ack_seen=0;rsp_seen=0;k_we=32\'h{("ffffffff" if we else "00000000")};\n'
        for p in range(32):
            bank=(p*7+j*11)%32;col=(p*3+j*5)%32;s=sector(p,bank,row,col)
            text+=f'k_addr[{p}*30+:30]=30\'d{s};k_len[{p}*4+:4]=1;k_tag[{p}*17+:17]=17\'d{roundid*32+p};k_wdata[{p}*256+:256]=word({p},{j});\n'
        text+='k_v=32\'hffffffff;#1;if(k_rdy!==32\'hffffffff)$fatal(1,"fixedrequestslotnotavailable");tick;@(negedge clk);k_v=0;repeat(512)tick;\n'
        text+=('if(ack_seen!==32\'hffffffff || rsp_seen!=0)$fatal(1,"writewindow incomplete");\n' if we else 'if(rsp_seen!==32\'hffffffff || ack_seen!=0)$fatal(1,"readwindow incomplete");\n')
    text+='if(reads!=64 || writes!=64 || acks!=64 || responses!=64 || refreshes<32)$fatal(1,"fullcounts");$display("PASS nativeRW32PC physicalcommands64WR64RD ACK64 responses64 REFpb%0d cycles%0d maxWR%0d maxRD%0d",refreshes,cyc,max_write,max_read);$finish;end endmodule\n'
    return text

def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);tb=out/'tb.sv';tb.write_text(bench())
    sources=[ROOT/'rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv',ROOT/'rtl/hbm_accel/service/native_sector_20261015/ot_hbm_native_sector_stack.sv']
    raw=sources[1].read_text()
    runs=[]
    for name,edit in [('baseline',None),('enqueue_ack',('k_wr_done[p]<=0;\n                if(k_v[p]', 'k_wr_done[p]<=0;\n                if(k_v[p] && k_rdy[p] && k_we[p])k_wr_done[p]<=1;\n                if(k_v[p]')),('wrong_bank',('wire[4:0]physical_bank={((sector[14:12]^physical_row[4:2])),(sector[1:0]^physical_row[1:0])};','wire[4:0]physical_bank={((sector[14:12]^physical_row[4:2])),(sector[1:0]^physical_row[1:0])} ^ 5\'d1;'))]:
        source=sources[1]
        if edit:
            old,new=edit;assert raw.count(old)==1,(name,raw.count(old))
            source=out/(name+'.sv');source.write_text(raw.replace(old,new))
        cp=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(out/name),str(sources[0]),str(source),str(tb)],capture_output=True,text=True)
        (out/f'{name}.build.log').write_text(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stderr
        rp=subprocess.run(['vvp',str(out/name)],capture_output=True,text=True);(out/f'{name}.run.log').write_text(rp.stdout+rp.stderr)
        assert (rp.returncode==0)==(name=='baseline'),rp.stdout+rp.stderr
        runs.append(dict(name=name,returncode=rp.returncode,output=rp.stdout.strip()))
    receipt=dict(schema='opentallas.hbm.native_sector_controller.v1',status='pass',runs=runs,controller_clock_ps=1024,
        scope='Actual32PC R/W/refresh bank sequencers to externalDRAM command/data; one outstanding single-sector perPC',
        calendar='four fixed512-edge service windows, all32 PCs each; no dynamic extension',
        physical_qualified=False,full_native_qualified=False,protected_state_admitted=False,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+[Path(__file__)]})
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();print(json.dumps(run(a.out),indent=2))
