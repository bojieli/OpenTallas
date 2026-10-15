#!/usr/bin/env python3
"""Actual hash→8 homes/CDC/native DRAM command controllers→SRAM component join.

External memory supplies only original checkpoint bytes in response to actual
DRAM commands. Home data is checked through actual SRAM registered read faces.
"""
from __future__ import annotations
import argparse,hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def bench(binding,li):
    rows=[r for r in binding['rows'] if r['layer']==[1,14][li]]
    t='''`timescale 1ps/1fs
module tb;
reg core_clk=0,hbm_clk=0;always #416.667 core_clk=~core_clk;initial begin #17;forever #512 hbm_clk=~hbm_clk;end
reg rst_n=0,epoch_begin=0,fetch_start=0,capture=0,in_valid=0,in_first=0;reg[16:0]in_cid=0;
wire[1:0]request_valid;wire[13:0]request_rank;wire[73:0]request_address;
wire[51:0]request_local_row;wire[9:0]request_staging_slot,request_list_index;
wire[39:0]gather_slot_id;wire hash_done,hash_fault;
ot_hbm_engram_hash_home_native hash(.clk(core_clk),.rst_n(rst_n),.in_valid(in_valid),.in_first(in_first),.in_cid(in_cid),
.request_valid(request_valid),.request_rank(request_rank),.request_address(request_address),.request_local_row(request_local_row),
.request_staging_slot(request_staging_slot),.gather_slot_id(gather_slot_id),.request_list_index(request_list_index),.done(hash_done),.fault(hash_fault));
reg[7:0]read_v=0;reg[4:0]read_row=0;reg[3:0]read_sector=0;
wire[7:0]raw_v,done,fault;wire[4:0]raw_row[0:7];wire[3:0]raw_sector[0:7];wire[255:0]raw_data[0:7];
wire[31:0]row_v[0:7],col_v[0:7],col_we[0:7];wire[95:0]row_op[0:7];wire[159:0]row_bank[0:7],col_bank[0:7],col_col[0:7];wire[607:0]row_row[0:7];
wire[8191:0]col_data[0:7];wire[1023:0]col_strb[0:7];reg[31:0]dram_rvalid[0:7];reg[8191:0]dram_rdata[0:7];
'''
    for h in range(8):
        t+=f'''ot_hbm_engram_home_fetch #(.HOME_RANK({li*8+h})) home{h}(.core_clk(core_clk),.hbm_clk(hbm_clk),.rst_n(rst_n),.epoch_begin(epoch_begin),
.descriptor_v(request_valid[{li}] && capture),.descriptor_rank(request_rank[{li*7}+:7]),.descriptor_index(request_list_index[{li*5}+:5]),.descriptor_address(request_address[{li*37}+:37]),
.fetch_start(fetch_start),.read_v(read_v[{h}]),.read_row(read_row),.read_sector(read_sector),.raw_v(raw_v[{h}]),.raw_row(raw_row[{h}]),.raw_sector(raw_sector[{h}]),.raw_data(raw_data[{h}]),.done(done[{h}]),.fault(fault[{h}]),
.row_v(row_v[{h}]),.row_op(row_op[{h}]),.row_bank(row_bank[{h}]),.row_row(row_row[{h}]),.col_v(col_v[{h}]),.col_we(col_we[{h}]),.col_bank(col_bank[{h}]),.col_col(col_col[{h}]),.col_data(col_data[{h}]),.col_strb(col_strb[{h}]),.dram_rvalid(dram_rvalid[{h}]),.dram_rdata(dram_rdata[{h}]));
'''
    t+='''integer core_edge=0,hbm_edge=0,checks=0,reads=0,refreshes=0,descriptors=0;
reg[255:0]external_words[0:431];integer owner[0:23],base_sector[0:23];reg[36:0]expected_address[0:23];
reg opened[0:7][0:31][0:31];integer physical_row[0:7][0:31][0:31],act_at[0:7][0:31][0:31],pre_at[0:7][0:31][0:31],ref_until[0:7][0:31][0:31];
reg[5:0]due_read[0:7][0:31];reg[255:0]due_data[0:7][0:31];
reg[130000:0]raw_due=0;integer due_home[0:130000],due_word[0:130000];
function[29:0]inverse(input integer pc,input integer bank,input integer row,input integer col);
 reg[29:0]s;begin s=(row<<15)|((((bank>>2)^(row>>2))&7)<<12)|(col<<7)|((bank^row)&3);s=s|((pc^((s>>7)&31)^((s>>12)&31))<<2);inverse=s;end
endfunction
always @(posedge hbm_clk)begin:external_dram
 integer h,p,b,op,rr,s,j,hit,off;
 hbm_edge=hbm_edge+1;
 for(h=0;h<8;h=h+1)begin
  dram_rvalid[h]<=0;
  if(rst_n)for(p=0;p<32;p=p+1)begin
   if(row_v[h][p])begin
    b=row_bank[h][p*5+:5];op=row_op[h][p*3+:3];rr=row_row[h][p*19+:19];
    if(op==1)begin
     if(opened[h][p][b] || hbm_edge-pre_at[h][p][b]<16 || hbm_edge<ref_until[h][p][b])$fatal(1,"externalACTtiming h%0d p%0d b%0d",h,p,b);
     opened[h][p][b]=1;physical_row[h][p][b]=rr;act_at[h][p][b]=hbm_edge;
    end else if(op==0)begin
     if(opened[h][p][b] && hbm_edge-act_at[h][p][b]<28)$fatal(1,"externalearlyPRE");
     opened[h][p][b]=0;pre_at[h][p][b]=hbm_edge;
    end else if(op==6)begin
     if(opened[h][p][b] || hbm_edge-pre_at[h][p][b]<16 || hbm_edge<ref_until[h][p][b])$fatal(1,"externalREFtiming");
     ref_until[h][p][b]=hbm_edge+196;refreshes=refreshes+1;
    end else if(op!=5)$fatal(1,"unexpectedrowcommand");
   end
   if(col_v[h][p])begin
    b=col_bank[h][p*5+:5];
    if(col_we[h][p] || !opened[h][p][b] || hbm_edge-act_at[h][p][b]<19 || hbm_edge<ref_until[h][p][b])$fatal(1,"externalillegalRD");
    s=inverse(p,b,physical_row[h][p][b],col_col[h][p*5+:5]);hit=-1;off=0;
    for(j=0;j<24;j=j+1)if(owner[j]==h && s>=base_sector[j] && s<base_sector[j]+9)begin hit=j;off=s-base_sector[j];end
    if(hit<0)$fatal(1,"actualphysicalrequestoutsidereleasedhome h%0d pc%0d sector%0d",h,p,s);
    if(due_read[h][p]!=0)$fatal(1,"externalreadresponseoverlap");
    due_read[h][p]<=1;due_data[h][p]<=external_words[LAYER*216+hit*9+off];reads=reads+1;
   end
   if(due_read[h][p]!=0)begin
    due_read[h][p]<=due_read[h][p]<<1;
    if(due_read[h][p][5])begin dram_rvalid[h][p]<=1;dram_rdata[h][p*256+:256]<=due_data[h][p];end
   end
  end
 end
end
always @(posedge core_clk)begin:scoreboard
 integer idx,h;
 core_edge=core_edge+1;#2;
 if(rst_n)begin
  if(hash_fault || fault!=0)$fatal(1,"actualnativehomefault core%0d hash%b homes%h",core_edge,hash_fault,fault);
  if(request_valid[LAYER] && capture)begin
   idx=request_list_index[LAYER*5+:5];
   if(request_rank[LAYER*7+:7]!==7'(owner[idx]+LAYER*8) || request_address[LAYER*37+:37]!==expected_address[idx])$fatal(1,"actualhashdescriptoridentity");
   descriptors=descriptors+1;
  end
  for(h=0;h<8;h=h+1)begin
   if(raw_v[h] !== (raw_due[core_edge] && due_home[core_edge]==h))$fatal(1,"actualhomeSRAMreadcalendar core%0d home%0d v%b",core_edge,h,raw_v[h]);
   if(raw_v[h])begin
    idx=due_word[core_edge];
    if(raw_row[h]!==5'(idx/9) || raw_sector[h]!==4'(idx%9) || raw_data[h]!==external_words[LAYER*216+idx])$fatal(1,"actualhash/DMA/CDC/SRAMwordmismatch home%0d idx%0d",h,idx);
    checks=checks+1;
   end
  end
 end
end
task tick;begin @(posedge core_clk);#3;end endtask
integer j,s,cididx,fetch_edge;
initial begin
 $readmemh("external_hbm_sectors.hex",external_words);
 for(integer h=0;h<8;h=h+1)begin
  dram_rvalid[h]=0;dram_rdata[h]=0;
  for(integer p=0;p<32;p=p+1)begin
   due_read[h][p]=0;due_data[h][p]=0;
   for(integer b=0;b<32;b=b+1)begin opened[h][p][b]=0;physical_row[h][p][b]=0;act_at[h][p][b]=-1000;pre_at[h][p][b]=-1000;ref_until[h][p][b]=-1000;end
  end
 end
'''.replace('LAYER',str(li))
    for r in rows:
        j=r['list_index'];localbase=(r['address']&((1<<35)-1))//32
        t+=f'owner[{j}]={r["home"]};base_sector[{j}]={localbase};expected_address[{j}]=37\'d{r["address"]};\n'
    t+='repeat(4)tick;@(negedge core_clk);rst_n=1;epoch_begin=1;tick;@(negedge core_clk);epoch_begin=0;\n'
    for i,cid in enumerate(binding['compressed_history']):
        t+=f'@(negedge core_clk);in_valid=1;in_first={int(i==0)};in_cid={cid};capture={int(i==3)};tick;@(negedge core_clk);in_valid=0;repeat(39)tick;\n'
    t+='''if(descriptors!=24)$fatal(1,"full24hashdescriptorcount");
 @(negedge core_clk);fetch_start=1;tick;fetch_edge=core_edge;@(negedge core_clk);fetch_start=0;
 repeat(216*512+512-1)begin tick;if(done!=0)$fatal(1,"earlycompletion");end
 tick;if(done!==8'hff || core_edge-fetch_edge!=216*512+512)$fatal(1,"fixedfullfetchdone");
 repeat(4)tick;
 for(j=0;j<24;j=j+1)for(s=0;s<9;s=s+1)begin
  @(negedge core_clk);read_v=8'b1<<owner[j];read_row=j;read_sector=s;
  raw_due[core_edge+4]=1;due_home[core_edge+4]=owner[j];due_word[core_edge+4]=j*9+s;tick;
 end
 @(negedge core_clk);read_v=0;repeat(5)tick;
 if(checks!=216 || reads!=216 || refreshes<256)$fatal(1,"fullnativehomecounts reads%0d checks%0d",reads,checks);
 $display("PASS actualhash8homes nativeRWcontrollers CDCtwo-clocks SRAM216sectors descriptors24 checks%0d physicalRD%0d REFpb%0d fixedfetch111104coreedges",checks,reads,refreshes);$finish;
end
endmodule
'''
    return t

def run(out,inputs,li,compact=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);inputs=Path(inputs)
    binding=json.loads((inputs/'receipt.json').read_text());raw=(inputs/'external_hbm_sectors.hex').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==binding['data_sha256']['external_hbm_sectors.hex']
    (out/'external_hbm_sectors.hex').write_bytes(raw);tb=out/'tb.sv';testbench=bench(binding,li)
    if compact:
        from hbm_engram_hash_home_bound import prove
        bound=prove();(out/'released_home_bound.json').write_text(json.dumps(bound,indent=2)+'\n')
        testbench=testbench.replace('ot_hbm_engram_home_fetch #','ot_hbm_engram_home_fetch_compact #').replace('216*512+512','36*512+512').replace('fixedfetch111104coreedges','fixedfetch18944coreedges')
    tb.write_text(testbench)
    paths=['physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
        'rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv','rtl/hdc/v41/ot_hdc_engram_hash_shipped.sv','rtl/hdc/v41/ot_hdc_engram_gather.sv',
        'rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv','rtl/hbm_accel/service/native_sector_20261015/ot_hbm_native_sector_stack.sv',
        'rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv','rtl/hbm_accel/ingest/ot_hbm_loader_kport_address.sv',
        'rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_home_dispatch.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_hash_home_native.sv',
        'rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_row_store_decode.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_home_fetch.sv']
    if compact:paths[-1]=paths[-1].replace('home_fetch.sv','home_fetch_compact.sv')
    start=time.monotonic();cp=subprocess.run(['iverilog','-g2012','-s','tb','-o',str((out/'sim').resolve()),*[str(ROOT/p) for p in paths],str(tb)],capture_output=True,text=True)
    (out/'build.log').write_text(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stdout+cp.stderr
    print('BUILD_PASS seconds',round(time.monotonic()-start,2),flush=True)
    rp=subprocess.run(['vvp',str((out/'sim').resolve())],cwd=out,capture_output=True,text=True)
    (out/'run.log').write_text(rp.stdout+rp.stderr);assert rp.returncode==0,rp.stdout+rp.stderr
    receipt=dict(schema='opentallas.hbm.engram.native_home_fetch.v1',status='pass',layer=[1,14][li],homes=list(range(li*8,li*8+8)),
        rows=24,sectors=216,core_clock_ps=833.334,hbm_clock_ps=1024,external_HBM='physical DRAM row/column command/data only; original releasedtable bytes',
        fixed_fetch_core_edges=18944 if compact else 111104,compact_home_calendar=compact,output=rp.stdout.strip(),wall_seconds=time.monotonic()-start,
        source_binding=binding['data_sha256'],collective_decode_join=False,full_layer_qualified=False,physical_qualified=False,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths})
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--inputs',required=True);ap.add_argument('--layer-index',type=int,choices=[0,1],required=True);ap.add_argument('--compact',action='store_true');a=ap.parse_args();print(json.dumps(run(a.out,a.inputs,a.layer_index,a.compact),indent=2))
