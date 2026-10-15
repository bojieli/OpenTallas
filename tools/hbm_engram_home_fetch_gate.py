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
reg[5:0]due_read[0:7][0:31];reg[255:0]due_data[0:7][0:31][0:RETURN_LAST];
reg[130000:0]raw_due=0;reg[7:0]raw_due_mask[0:130000];integer due_home[0:130000],due_word[0:7][0:130000];
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
   due_read[h][p]<=due_read[h][p]<<1;
   for(integer d=1;d<=RETURN_LAST;d=d+1)due_data[h][p][d]<=due_data[h][p][d-1];
   if(col_v[h][p])begin
    b=col_bank[h][p*5+:5];
    if(col_we[h][p] || !opened[h][p][b] || hbm_edge-act_at[h][p][b]<19 || hbm_edge<ref_until[h][p][b])$fatal(1,"externalillegalRD");
    s=inverse(p,b,physical_row[h][p][b],col_col[h][p*5+:5]);hit=-1;off=0;
    for(j=0;j<24;j=j+1)if(owner[j]==h && s>=base_sector[j] && s<base_sector[j]+9)begin hit=j;off=s-base_sector[j];end
    if(hit<0)$fatal(1,"actualphysicalrequestoutsidereleasedhome h%0d pc%0d sector%0d",h,p,s);
    due_read[h][p][0]<=1;due_data[h][p][0]<=external_words[LAYER*216+hit*9+off];reads=reads+1;
   end
   if(due_read[h][p]!=0)begin
    if(due_read[h][p][5])begin dram_rvalid[h][p]<=1;dram_rdata[h][p*256+:256]<=due_data[h][p][RETURN_LAST];end
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
   if(raw_v[h] !== raw_due_mask[core_edge][h])$fatal(1,"actualhomeSRAMreadcalendar core%0d home%0d v%b",core_edge,h,raw_v[h]);
   if(raw_v[h])begin
    idx=due_word[h][core_edge];
    if(raw_row[h]!==5'(idx/9) || raw_sector[h]!==4'(idx%9) || raw_data[h]!==external_words[LAYER*216+idx])$fatal(1,"actualhash/DMA/CDC/SRAMwordmismatch home%0d idx%0d",h,idx);
    checks=checks+1;
   end
  end
 end
end
task tick;begin @(posedge core_clk);#3;end endtask
integer j,s,cididx,fetch_edge;
initial begin
 for(integer z=0;z<=130000;z=z+1)raw_due_mask[z]=0;
 $readmemh("external_hbm_sectors.hex",external_words);
 for(integer h=0;h<8;h=h+1)begin
  dram_rvalid[h]=0;dram_rdata[h]=0;
  for(integer p=0;p<32;p=p+1)begin
   due_read[h][p]=0;for(integer d=0;d<=RETURN_LAST;d=d+1)due_data[h][p][d]=0;
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
  raw_due_mask[core_edge+4]=8'b1<<owner[j];due_home[core_edge+4]=owner[j];due_word[owner[j]][core_edge+4]=j*9+s;tick;
 end
 @(negedge core_clk);read_v=0;repeat(5)tick;
 if(checks!=216 || reads!=216 || refreshes<256)$fatal(1,"fullnativehomecounts reads%0d checks%0d",reads,checks);
 $display("PASS actualhash8homes nativeRWcontrollers CDCtwo-clocks SRAM216sectors descriptors24 checks%0d physicalRD%0d REFpb%0d fixedfetch111104coreedges",checks,reads,refreshes);$finish;
end
endmodule
'''
    return t

def run(out,inputs,li,compact=False,return_edges=6,local_reads=False,mutant_return_row=False,programme=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);inputs=Path(inputs)
    binding=json.loads((inputs/'receipt.json').read_text());raw=(inputs/'external_hbm_sectors.hex').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==binding['data_sha256']['external_hbm_sectors.hex']
    (out/'external_hbm_sectors.hex').write_bytes(raw);tb=out/'tb.sv';testbench=bench(binding,li)
    if compact:
        from hbm_engram_hash_home_bound import prove
        bound=prove();(out/'released_home_bound.json').write_text(json.dumps(bound,indent=2)+'\n')
        testbench=testbench.replace('ot_hbm_engram_home_fetch #','ot_hbm_engram_home_fetch_compact #').replace('216*512+512','36*512+512').replace('fixedfetch111104coreedges','fixedfetch18944coreedges')
    if return_edges!=6:
        testbench=testbench.replace('reg[5:0]due_read',f'reg[{return_edges-1}:0]due_read').replace('due_read[h][p][5]',f'due_read[h][p][{return_edges-1}]')
    testbench=testbench.replace('RETURN_LAST',str(return_edges-1))
    if local_reads:
        testbench=testbench.replace('36*512+512','36*16+2048').replace('fixedfetch18944coreedges','fixedfetch2624coreedges')
    if compact and local_reads:
        checks=[]
        for h in range(8):
            owned=[r['list_index'] for r in binding['rows'] if r['layer']==[1,14][li] and r['home']==h]
            checks.append(f"if(home{h}.owned_slot_valid!==4'd{(1<<len(owned))-1} || home{h}.owned_row_count!==3'd{len(owned)})$fatal(1,\"compact owned count\");")
            for k,j in enumerate(owned):checks.append(f"if(home{h}.owned_slot_global_row[{k*5}+:5]!==5'd{j})$fatal(1,\"actual compact row identity\");")
        testbench=testbench.replace('if(descriptors!=24)', '\n'.join(checks)+'\nif(descriptors!=24)')
    if local_reads:
        assert compact
        # All4 slots/home are reserved: three actual rows and one explicit idle
        # for this input sequence. Metadata at +3 remains meaningful on idles.
        testbench=testbench.replace('ot_hbm_engram_home_fetch_compact #','ot_hbm_engram_home_fetch_compact_slots #').replace('.HOME_RANK(','.LOCAL_READ(1),.HOME_RANK(')
        testbench=testbench.replace('reg[7:0]read_v=0;', 'reg local_read_v=0;reg[1:0]local_read_slot=0;reg[3:0]local_read_sector=0;\nreg[7:0]read_v=0;')
        for h in range(8):
            testbench=testbench.replace(f'.fetch_start(fetch_start),.read_v(read_v[{h}])',f'.local_read_v(local_read_v),.local_read_slot(local_read_slot),.local_read_sector(local_read_sector),.fetch_start(fetch_start),.read_v(read_v[{h}])')
        begin=testbench.index(' for(j=0;j<24;j=j+1)for(s=0;s<9;s=s+1)begin',testbench.index('fixedfullfetchdone'))
        end=testbench.index(' if(checks!=216',begin)
        body=[]
        meta=[]
        initial=[]
        for h in range(8):
            owned=[r['list_index'] for r in binding['rows'] if r['layer']==[1,14][li] and r['home']==h]
            for k in range(4):initial.append(f"compact_row[{h}][{k}]={owned[k] if k<len(owned) else -1};")
            meta.append(f'''always @(posedge core_clk)begin
 #2;if(rst_n)begin
 if(home{h}.slot_response_v!==raw_due[core_edge])$fatal(1,"slot metadata calendar h{h}");
 if(raw_due[core_edge])begin
  if(home{h}.slot_response_present!==(compact_row[{h}][due_slot[core_edge]]>=0) || home{h}.slot_response_sector!==4'(due_sector[core_edge]) || home{h}.slot_response_row!==5'(compact_row[{h}][due_slot[core_edge]]>=0?compact_row[{h}][due_slot[core_edge]]:0))$fatal(1,"slot metadata identity h{h}");
  meta_checks=meta_checks+1;
 end
 end
end
''')
        testbench=testbench.replace('integer core_edge=0,', 'integer compact_row[0:7][0:3],due_slot[0:130000],due_sector[0:130000],meta_checks=0;\ninteger core_edge=0,')
        body.append(''' for(j=0;j<4;j=j+1)for(s=0;s<9;s=s+1)begin
  @(negedge core_clk);local_read_v=1;local_read_slot=j;local_read_sector=s;
  raw_due[core_edge+4]=1;due_slot[core_edge+4]=j;due_sector[core_edge+4]=s;
  for(integer h=0;h<8;h=h+1)if(compact_row[h][j]>=0)begin raw_due_mask[core_edge+4][h]=1;due_word[h][core_edge+4]=compact_row[h][j]*9+s;end
  tick;
 end
 @(negedge core_clk);local_read_v=0;repeat(5)tick;
 if(meta_checks!=288)$fatal(1,"all160slot-source metadata controls");
''')
        # Insert the new readbody before changing declarations, because indices
        # above referred to the original concrete string.
        begin=testbench.index(' for(j=0;j<24;j=j+1)for(s=0;s<9;s=s+1)begin',testbench.index('fixedfullfetchdone'))
        end=testbench.index(' if(checks!=216',begin)
        testbench=testbench[:begin]+''.join(body)+testbench[end:]
        testbench=testbench.replace('repeat(4)tick;@(negedge core_clk);rst_n=1;', '\n'.join(initial)+'\nrepeat(4)tick;@(negedge core_clk);rst_n=1;')
        testbench=testbench.replace('task tick;', ''.join(meta)+'\ntask tick;')
    if programme:
        assert local_reads
        image=json.loads((ROOT/'results/arch/hbm_engram_partition_1015/fetch_program_image.json').read_text())
        declaration="""reg prog_cfg_v=0,prog_desc_v=0,prog_launch_v=0,prog_token_v=0;
reg[11:0]prog_cfg_addr=0;reg[255:0]prog_cfg_data=0;
wire prog_epoch,prog_hash_v,prog_hash_first,prog_fetch,prog_done,prog_fault;
wire[16:0]prog_hash_cid;
ot_hbm_engram_fetch_program #(.FETCH_EDGES(2624)) fetch_program(
.clk_control(core_clk),.clk_mem(core_clk),.rst_n(rst_n),.cfg_v(prog_cfg_v),.cfg_target(8'd124),.cfg_addr(prog_cfg_addr),.cfg_data(prog_cfg_data),
.desc_v(prog_desc_v),.desc_base(10'd0),.desc_limit(10'd42),.desc_loops(16'd1),.launch_v(prog_launch_v),
.token_v(prog_token_v),.token_cid(17'd99091),.token_first(1'b0),.home_done(done),.home_fault(fault),
.configured(),.init_busy(),.busy(),.done(prog_done),.fault(prog_fault),.epoch_begin(prog_epoch),.hash_v(prog_hash_v),.hash_first(prog_hash_first),.fetch_start(prog_fetch),.hash_cid(prog_hash_cid),.instruction_v(),.instruction(),.instruction_pc());
"""
        testbench=testbench.replace('ot_hbm_engram_hash_home_native hash(',declaration+'ot_hbm_engram_hash_home_native hash(')
        testbench=testbench.replace('.in_valid(in_valid),.in_first(in_first),.in_cid(in_cid)', '.in_valid(in_valid|prog_hash_v),.in_first(prog_hash_v?prog_hash_first:in_first),.in_cid(prog_hash_v?prog_hash_cid:in_cid)')
        testbench=testbench.replace('.epoch_begin(epoch_begin)', '.epoch_begin(epoch_begin|prog_epoch)').replace('.fetch_start(fetch_start)', '.fetch_start(prog_fetch)')
        testbench=testbench.replace('if(hash_fault || fault!=0)', 'if(prog_fault || hash_fault || fault!=0)')
        old=f'@(negedge core_clk);in_valid=1;in_first=0;in_cid={binding["compressed_history"][3]};capture=1;tick;@(negedge core_clk);in_valid=0;repeat(39)tick;'
        seq=[]
        for w in image['programme']['configuration_writes']:
            seq.append(f"@(negedge core_clk);prog_cfg_v=1;prog_cfg_addr=12'd{w['addr']};prog_cfg_data=256'h{w['data']};tick;@(negedge core_clk);prog_cfg_v=0;repeat(2)tick;")
        seq.append('@(negedge core_clk);prog_desc_v=1;tick;@(negedge core_clk);prog_desc_v=0;repeat(130)tick;')
        seq.append('@(negedge core_clk);capture=1;prog_launch_v=1;prog_token_v=1;tick;@(negedge core_clk);prog_launch_v=0;prog_token_v=0;wait(hash_done);tick;')
        assert old in testbench
        testbench=testbench.replace(old,'\n'.join(seq))
        old='@(negedge core_clk);fetch_start=1;tick;fetch_edge=core_edge;@(negedge core_clk);fetch_start=0;'
        assert old in testbench
        testbench=testbench.replace(old,'wait(prog_fetch);tick;fetch_edge=core_edge;')
        testbench=testbench.replace('repeat(4)tick;\n for(j=', 'repeat(4)tick;\n if(!prog_done && fetch_program.busy)$fatal(1,"actual programme kernel completion");\n for(j=')
    tb.write_text(testbench)
    paths=['physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
        'rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv','rtl/hdc/v41/ot_hdc_engram_hash_shipped.sv','rtl/hdc/v41/ot_hdc_engram_gather.sv',
        'rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv','rtl/hbm_accel/service/native_sector_20261015/ot_hbm_native_sector_stack.sv',
        'rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv','rtl/hbm_accel/ingest/ot_hbm_loader_kport_address.sv',
        'rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_home_dispatch.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_hash_home_native.sv',
        'rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_row_store_decode.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_home_fetch.sv']
    if compact:paths[-1]=paths[-1].replace('home_fetch.sv','home_fetch_compact_slots.sv' if local_reads else 'home_fetch_compact.sv')
    if local_reads:paths[5]='rtl/hbm_accel/loader/service_native/ot_hbm_svc_native_sector_pipeline_stack.sv'
    if programme:paths.insert(-1,'rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_fetch_program.sv')
    compiled_paths=[str(ROOT/p) for p in paths]
    mutation=None
    if mutant_return_row:
        original=Path(compiled_paths[-1]).read_text();old='.write_row(response_core[264:260])';new=".write_row(response_core[264:260] ^ 5'd16)"
        assert original.count(old)==1
        variant=(out/'return_row_mutant.sv').resolve();variant.write_text(original.replace(old,new));compiled_paths[-1]=str(variant)
        mutation=dict(name='actual_DUT_return_row_bit4',source_sha256=hashlib.sha256(variant.read_bytes()).hexdigest())
    start=time.monotonic();cp=subprocess.run(['iverilog' ,'-g2012','-s','tb','-o',str((out/'sim').resolve()),*compiled_paths,str(tb)],capture_output=True,text=True)
    (out/'build.log').write_text(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stdout+cp.stderr
    print('BUILD_PASS seconds',round(time.monotonic()-start,2),flush=True)
    rp=subprocess.run(['vvp',str((out/'sim').resolve())],cwd=out,capture_output=True,text=True)
    (out/'run.log').write_text(rp.stdout+rp.stderr);assert (rp.returncode==0)==(not mutant_return_row),rp.stdout+rp.stderr
    receipt=dict(schema='opentallas.hbm.engram.native_home_fetch.v1',status='detected_mutant' if mutant_return_row else 'pass',mutation=mutation,layer=[1,14][li],homes=list(range(li*8,li*8+8)),
        rows=24,sectors=216,core_clock_ps=833.334,hbm_clock_ps=1024,external_HBM='physical DRAM row/column command/data only; original releasedtable bytes',
        fixed_fetch_core_edges=(2624 if local_reads else 18944) if compact else 111104,compact_home_calendar=compact,output=rp.stdout.strip(),wall_seconds=time.monotonic()-start,
        external_return_latency_edges=return_edges,local_slot_read_metadata=local_reads,source_binding=binding['data_sha256'],actual_programme_join=programme,collective_decode_join=False,full_layer_qualified=False,physical_qualified=False,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths})
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--inputs',required=True);ap.add_argument('--layer-index',type=int,choices=[0,1],required=True);ap.add_argument('--compact',action='store_true');ap.add_argument('--return-edges',type=int,default=6);ap.add_argument('--local-reads',action='store_true');ap.add_argument('--mutant-return-row',action='store_true');ap.add_argument('--programme',action='store_true');a=ap.parse_args();print(json.dumps(run(a.out,a.inputs,a.layer_index,a.compact,a.return_edges,a.local_reads,a.mutant_return_row,a.programme),indent=2))
