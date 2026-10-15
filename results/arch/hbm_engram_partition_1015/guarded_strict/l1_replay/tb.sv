`timescale 1ps/1fs
module tb;
reg core_clk=0,hbm_clk=0;always #416.667 core_clk=~core_clk;initial begin #17;forever #512 hbm_clk=~hbm_clk;end
reg rst_n=0,epoch_begin=0,fetch_start=0,capture=0,in_valid=0,in_first=0;reg[16:0]in_cid=0;
wire[1:0]request_valid;wire[13:0]request_rank;wire[73:0]request_address;
wire[51:0]request_local_row;wire[9:0]request_staging_slot,request_list_index;
wire[39:0]gather_slot_id;wire hash_done,hash_fault;
ot_hbm_engram_hash_home_native hash(.clk(core_clk),.rst_n(rst_n),.in_valid(in_valid),.in_first(in_first),.in_cid(in_cid),
.request_valid(request_valid),.request_rank(request_rank),.request_address(request_address),.request_local_row(request_local_row),
.request_staging_slot(request_staging_slot),.gather_slot_id(gather_slot_id),.request_list_index(request_list_index),.done(hash_done),.fault(hash_fault));
reg local_read_v=0;reg[1:0]local_read_slot=0;reg[3:0]local_read_sector=0;
reg[7:0]read_v=0;reg[4:0]read_row=0;reg[3:0]read_sector=0;
wire[7:0]raw_v,done,fault;wire[4:0]raw_row[0:7];wire[3:0]raw_sector[0:7];wire[255:0]raw_data[0:7];
wire[31:0]row_v[0:7],col_v[0:7],col_we[0:7];wire[95:0]row_op[0:7];wire[159:0]row_bank[0:7],col_bank[0:7],col_col[0:7];wire[607:0]row_row[0:7];
wire[8191:0]col_data[0:7];wire[1023:0]col_strb[0:7];reg[31:0]dram_rvalid[0:7];reg[8191:0]dram_rdata[0:7];
ot_hbm_engram_home_fetch_grouped_guarded #(.LOCAL_READ(1),.HOME_RANK(0)) home0(.core_clk(core_clk),.hbm_clk(hbm_clk),.rst_n(rst_n),.epoch_begin(epoch_begin),
.descriptor_v(request_valid[0] && capture),.descriptor_rank(request_rank[0+:7]),.descriptor_index(request_list_index[0+:5]),.descriptor_address(request_address[0+:37]),
.local_read_v(local_read_v),.local_read_slot(local_read_slot),.local_read_sector(local_read_sector),.fetch_start(fetch_start),.read_v(read_v[0]),.read_row(read_row),.read_sector(read_sector),.raw_v(raw_v[0]),.raw_row(raw_row[0]),.raw_sector(raw_sector[0]),.raw_data(raw_data[0]),.done(done[0]),.fault(fault[0]),
.row_v(row_v[0]),.row_op(row_op[0]),.row_bank(row_bank[0]),.row_row(row_row[0]),.col_v(col_v[0]),.col_we(col_we[0]),.col_bank(col_bank[0]),.col_col(col_col[0]),.col_data(col_data[0]),.col_strb(col_strb[0]),.dram_rvalid(dram_rvalid[0]),.dram_rdata(dram_rdata[0]));
ot_hbm_engram_home_fetch_grouped_guarded #(.LOCAL_READ(1),.HOME_RANK(1)) home1(.core_clk(core_clk),.hbm_clk(hbm_clk),.rst_n(rst_n),.epoch_begin(epoch_begin),
.descriptor_v(request_valid[0] && capture),.descriptor_rank(request_rank[0+:7]),.descriptor_index(request_list_index[0+:5]),.descriptor_address(request_address[0+:37]),
.local_read_v(local_read_v),.local_read_slot(local_read_slot),.local_read_sector(local_read_sector),.fetch_start(fetch_start),.read_v(read_v[1]),.read_row(read_row),.read_sector(read_sector),.raw_v(raw_v[1]),.raw_row(raw_row[1]),.raw_sector(raw_sector[1]),.raw_data(raw_data[1]),.done(done[1]),.fault(fault[1]),
.row_v(row_v[1]),.row_op(row_op[1]),.row_bank(row_bank[1]),.row_row(row_row[1]),.col_v(col_v[1]),.col_we(col_we[1]),.col_bank(col_bank[1]),.col_col(col_col[1]),.col_data(col_data[1]),.col_strb(col_strb[1]),.dram_rvalid(dram_rvalid[1]),.dram_rdata(dram_rdata[1]));
ot_hbm_engram_home_fetch_grouped_guarded #(.LOCAL_READ(1),.HOME_RANK(2)) home2(.core_clk(core_clk),.hbm_clk(hbm_clk),.rst_n(rst_n),.epoch_begin(epoch_begin),
.descriptor_v(request_valid[0] && capture),.descriptor_rank(request_rank[0+:7]),.descriptor_index(request_list_index[0+:5]),.descriptor_address(request_address[0+:37]),
.local_read_v(local_read_v),.local_read_slot(local_read_slot),.local_read_sector(local_read_sector),.fetch_start(fetch_start),.read_v(read_v[2]),.read_row(read_row),.read_sector(read_sector),.raw_v(raw_v[2]),.raw_row(raw_row[2]),.raw_sector(raw_sector[2]),.raw_data(raw_data[2]),.done(done[2]),.fault(fault[2]),
.row_v(row_v[2]),.row_op(row_op[2]),.row_bank(row_bank[2]),.row_row(row_row[2]),.col_v(col_v[2]),.col_we(col_we[2]),.col_bank(col_bank[2]),.col_col(col_col[2]),.col_data(col_data[2]),.col_strb(col_strb[2]),.dram_rvalid(dram_rvalid[2]),.dram_rdata(dram_rdata[2]));
ot_hbm_engram_home_fetch_grouped_guarded #(.LOCAL_READ(1),.HOME_RANK(3)) home3(.core_clk(core_clk),.hbm_clk(hbm_clk),.rst_n(rst_n),.epoch_begin(epoch_begin),
.descriptor_v(request_valid[0] && capture),.descriptor_rank(request_rank[0+:7]),.descriptor_index(request_list_index[0+:5]),.descriptor_address(request_address[0+:37]),
.local_read_v(local_read_v),.local_read_slot(local_read_slot),.local_read_sector(local_read_sector),.fetch_start(fetch_start),.read_v(read_v[3]),.read_row(read_row),.read_sector(read_sector),.raw_v(raw_v[3]),.raw_row(raw_row[3]),.raw_sector(raw_sector[3]),.raw_data(raw_data[3]),.done(done[3]),.fault(fault[3]),
.row_v(row_v[3]),.row_op(row_op[3]),.row_bank(row_bank[3]),.row_row(row_row[3]),.col_v(col_v[3]),.col_we(col_we[3]),.col_bank(col_bank[3]),.col_col(col_col[3]),.col_data(col_data[3]),.col_strb(col_strb[3]),.dram_rvalid(dram_rvalid[3]),.dram_rdata(dram_rdata[3]));
ot_hbm_engram_home_fetch_grouped_guarded #(.LOCAL_READ(1),.HOME_RANK(4)) home4(.core_clk(core_clk),.hbm_clk(hbm_clk),.rst_n(rst_n),.epoch_begin(epoch_begin),
.descriptor_v(request_valid[0] && capture),.descriptor_rank(request_rank[0+:7]),.descriptor_index(request_list_index[0+:5]),.descriptor_address(request_address[0+:37]),
.local_read_v(local_read_v),.local_read_slot(local_read_slot),.local_read_sector(local_read_sector),.fetch_start(fetch_start),.read_v(read_v[4]),.read_row(read_row),.read_sector(read_sector),.raw_v(raw_v[4]),.raw_row(raw_row[4]),.raw_sector(raw_sector[4]),.raw_data(raw_data[4]),.done(done[4]),.fault(fault[4]),
.row_v(row_v[4]),.row_op(row_op[4]),.row_bank(row_bank[4]),.row_row(row_row[4]),.col_v(col_v[4]),.col_we(col_we[4]),.col_bank(col_bank[4]),.col_col(col_col[4]),.col_data(col_data[4]),.col_strb(col_strb[4]),.dram_rvalid(dram_rvalid[4]),.dram_rdata(dram_rdata[4]));
ot_hbm_engram_home_fetch_grouped_guarded #(.LOCAL_READ(1),.HOME_RANK(5)) home5(.core_clk(core_clk),.hbm_clk(hbm_clk),.rst_n(rst_n),.epoch_begin(epoch_begin),
.descriptor_v(request_valid[0] && capture),.descriptor_rank(request_rank[0+:7]),.descriptor_index(request_list_index[0+:5]),.descriptor_address(request_address[0+:37]),
.local_read_v(local_read_v),.local_read_slot(local_read_slot),.local_read_sector(local_read_sector),.fetch_start(fetch_start),.read_v(read_v[5]),.read_row(read_row),.read_sector(read_sector),.raw_v(raw_v[5]),.raw_row(raw_row[5]),.raw_sector(raw_sector[5]),.raw_data(raw_data[5]),.done(done[5]),.fault(fault[5]),
.row_v(row_v[5]),.row_op(row_op[5]),.row_bank(row_bank[5]),.row_row(row_row[5]),.col_v(col_v[5]),.col_we(col_we[5]),.col_bank(col_bank[5]),.col_col(col_col[5]),.col_data(col_data[5]),.col_strb(col_strb[5]),.dram_rvalid(dram_rvalid[5]),.dram_rdata(dram_rdata[5]));
ot_hbm_engram_home_fetch_grouped_guarded #(.LOCAL_READ(1),.HOME_RANK(6)) home6(.core_clk(core_clk),.hbm_clk(hbm_clk),.rst_n(rst_n),.epoch_begin(epoch_begin),
.descriptor_v(request_valid[0] && capture),.descriptor_rank(request_rank[0+:7]),.descriptor_index(request_list_index[0+:5]),.descriptor_address(request_address[0+:37]),
.local_read_v(local_read_v),.local_read_slot(local_read_slot),.local_read_sector(local_read_sector),.fetch_start(fetch_start),.read_v(read_v[6]),.read_row(read_row),.read_sector(read_sector),.raw_v(raw_v[6]),.raw_row(raw_row[6]),.raw_sector(raw_sector[6]),.raw_data(raw_data[6]),.done(done[6]),.fault(fault[6]),
.row_v(row_v[6]),.row_op(row_op[6]),.row_bank(row_bank[6]),.row_row(row_row[6]),.col_v(col_v[6]),.col_we(col_we[6]),.col_bank(col_bank[6]),.col_col(col_col[6]),.col_data(col_data[6]),.col_strb(col_strb[6]),.dram_rvalid(dram_rvalid[6]),.dram_rdata(dram_rdata[6]));
ot_hbm_engram_home_fetch_grouped_guarded #(.LOCAL_READ(1),.HOME_RANK(7)) home7(.core_clk(core_clk),.hbm_clk(hbm_clk),.rst_n(rst_n),.epoch_begin(epoch_begin),
.descriptor_v(request_valid[0] && capture),.descriptor_rank(request_rank[0+:7]),.descriptor_index(request_list_index[0+:5]),.descriptor_address(request_address[0+:37]),
.local_read_v(local_read_v),.local_read_slot(local_read_slot),.local_read_sector(local_read_sector),.fetch_start(fetch_start),.read_v(read_v[7]),.read_row(read_row),.read_sector(read_sector),.raw_v(raw_v[7]),.raw_row(raw_row[7]),.raw_sector(raw_sector[7]),.raw_data(raw_data[7]),.done(done[7]),.fault(fault[7]),
.row_v(row_v[7]),.row_op(row_op[7]),.row_bank(row_bank[7]),.row_row(row_row[7]),.col_v(col_v[7]),.col_we(col_we[7]),.col_bank(col_bank[7]),.col_col(col_col[7]),.col_data(col_data[7]),.col_strb(col_strb[7]),.dram_rvalid(dram_rvalid[7]),.dram_rdata(dram_rdata[7]));
integer compact_row[0:7][0:3],due_slot[0:130000],due_sector[0:130000],meta_checks=0;
integer core_edge=0,hbm_edge=0,checks=0,reads=0,refreshes=0,descriptors=0;
reg[255:0]external_words[0:431];integer owner[0:23],base_sector[0:23];reg[36:0]expected_address[0:23];
reg opened[0:7][0:31][0:31];integer physical_row[0:7][0:31][0:31],act_at[0:7][0:31][0:31],pre_at[0:7][0:31][0:31],ref_until[0:7][0:31][0:31];
reg[22:0]due_read[0:7][0:31];reg[255:0]due_data[0:7][0:31][0:22];
reg[130000:0]raw_due=0;reg[7:0]raw_due_mask[0:130000];integer due_home[0:130000],due_word[0:7][0:130000];
integer read_at[0:7][0:31][0:31],last_act[0:7][0:31],ref_at[0:7][0:31];
integer last_act_bg[0:7][0:31][0:3],last_col_bg[0:7][0:31][0:3],faw[0:7][0:31][0:3];
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
     if(opened[h][p][b] || hbm_edge-pre_at[h][p][b]<16 || hbm_edge<ref_until[h][p][b] || hbm_edge-last_act[h][p]<3 || hbm_edge-last_act_bg[h][p][b&3]<4 || hbm_edge-faw[h][p][0]<15 || hbm_edge-ref_at[h][p]<8)$fatal(1,"externalACTtiming h%0d p%0d b%0d",h,p,b);
     opened[h][p][b]=1;physical_row[h][p][b]=rr;act_at[h][p][b]=hbm_edge;last_act[h][p]=hbm_edge;last_act_bg[h][p][b&3]=hbm_edge;for(integer f=0;f<3;f=f+1)faw[h][p][f]=faw[h][p][f+1];faw[h][p][3]=hbm_edge;
    end else if(op==0)begin
     if(opened[h][p][b] && (hbm_edge-act_at[h][p][b]<28 || hbm_edge-read_at[h][p][b]<6))$fatal(1,"externalearlyPRE");
     opened[h][p][b]=0;pre_at[h][p][b]=hbm_edge;
    end else if(op==6)begin
     if(opened[h][p][b] || hbm_edge-pre_at[h][p][b]<16 || hbm_edge<ref_until[h][p][b] || hbm_edge-last_act[h][p]<8 || hbm_edge-ref_at[h][p]<8)$fatal(1,"externalREFtiming");
     ref_until[h][p][b]=hbm_edge+196;refreshes=refreshes+1;ref_at[h][p]=hbm_edge;
    end else if(op==5)begin for(integer bb=0;bb<32;bb=bb+1)begin if(opened[h][p][bb] && (hbm_edge-act_at[h][p][bb]<28 || hbm_edge-read_at[h][p][bb]<6))$fatal(1,"externalPREALLtiming");opened[h][p][bb]=0;pre_at[h][p][bb]=hbm_edge;end end else $fatal(1,"unexpectedrowcommand");
   end
   due_read[h][p]<=due_read[h][p]<<1;
   for(integer d=1;d<=22;d=d+1)due_data[h][p][d]<=due_data[h][p][d-1];
   if(col_v[h][p])begin
    b=col_bank[h][p*5+:5];
    if(col_we[h][p] || !opened[h][p][b] || hbm_edge-act_at[h][p][b]<19 || hbm_edge<ref_until[h][p][b] || hbm_edge-last_col_bg[h][p][b&3]<3)$fatal(1,"externalillegalRD");
    read_at[h][p][b]=hbm_edge;last_col_bg[h][p][b&3]=hbm_edge;
    s=inverse(p,b,physical_row[h][p][b],col_col[h][p*5+:5]);hit=-1;off=0;
    for(j=0;j<24;j=j+1)if(owner[j]==h && s>=base_sector[j] && s<base_sector[j]+9)begin hit=j;off=s-base_sector[j];end
    if(hit<0)$fatal(1,"actualphysicalrequestoutsidereleasedhome h%0d pc%0d sector%0d",h,p,s);
    due_read[h][p][0]<=1;due_data[h][p][0]<=external_words[0*216+hit*9+off];reads=reads+1;
   end
   if(due_read[h][p]!=0)begin
    if(due_read[h][p][22])begin dram_rvalid[h][p]<=1;dram_rdata[h][p*256+:256]<=due_data[h][p][22];end
   end
  end
 end
end
always @(posedge core_clk)begin:scoreboard
 integer idx,h;
 core_edge=core_edge+1;#2;
 if(rst_n)begin
  if(hash_fault || fault!=0)$fatal(1,"actualnativehomefault core%0d hash%b homes%h",core_edge,hash_fault,fault);
  if(request_valid[0] && capture)begin
   idx=request_list_index[0*5+:5];
   if(request_rank[0*7+:7]!==7'(owner[idx]+0*8) || request_address[0*37+:37]!==expected_address[idx])$fatal(1,"actualhashdescriptoridentity");
   descriptors=descriptors+1;
  end
  for(h=0;h<8;h=h+1)begin
   if(raw_v[h] !== raw_due_mask[core_edge][h])$fatal(1,"actualhomeSRAMreadcalendar core%0d home%0d v%b",core_edge,h,raw_v[h]);
   if(raw_v[h])begin
    idx=due_word[h][core_edge];
    if(raw_row[h]!==5'(idx/9) || raw_sector[h]!==4'(idx%9) || raw_data[h]!==external_words[0*216+idx])$fatal(1,"actualhash/DMA/CDC/SRAMwordmismatch home%0d idx%0d",h,idx);
    checks=checks+1;
   end
  end
 end
end
always @(posedge core_clk)begin
 #2;if(rst_n)begin
 if(home0.slot_response_v!==raw_due[core_edge])$fatal(1,"slot metadata calendar h0");
 if(raw_due[core_edge])begin
  if(home0.slot_response_present!==(compact_row[0][due_slot[core_edge]]>=0) || home0.slot_response_sector!==4'(due_sector[core_edge]) || home0.slot_response_row!==5'(compact_row[0][due_slot[core_edge]]>=0?compact_row[0][due_slot[core_edge]]:0))$fatal(1,"slot metadata identity h0");
  meta_checks=meta_checks+1;
 end
 end
end
always @(posedge core_clk)begin
 #2;if(rst_n)begin
 if(home1.slot_response_v!==raw_due[core_edge])$fatal(1,"slot metadata calendar h1");
 if(raw_due[core_edge])begin
  if(home1.slot_response_present!==(compact_row[1][due_slot[core_edge]]>=0) || home1.slot_response_sector!==4'(due_sector[core_edge]) || home1.slot_response_row!==5'(compact_row[1][due_slot[core_edge]]>=0?compact_row[1][due_slot[core_edge]]:0))$fatal(1,"slot metadata identity h1");
  meta_checks=meta_checks+1;
 end
 end
end
always @(posedge core_clk)begin
 #2;if(rst_n)begin
 if(home2.slot_response_v!==raw_due[core_edge])$fatal(1,"slot metadata calendar h2");
 if(raw_due[core_edge])begin
  if(home2.slot_response_present!==(compact_row[2][due_slot[core_edge]]>=0) || home2.slot_response_sector!==4'(due_sector[core_edge]) || home2.slot_response_row!==5'(compact_row[2][due_slot[core_edge]]>=0?compact_row[2][due_slot[core_edge]]:0))$fatal(1,"slot metadata identity h2");
  meta_checks=meta_checks+1;
 end
 end
end
always @(posedge core_clk)begin
 #2;if(rst_n)begin
 if(home3.slot_response_v!==raw_due[core_edge])$fatal(1,"slot metadata calendar h3");
 if(raw_due[core_edge])begin
  if(home3.slot_response_present!==(compact_row[3][due_slot[core_edge]]>=0) || home3.slot_response_sector!==4'(due_sector[core_edge]) || home3.slot_response_row!==5'(compact_row[3][due_slot[core_edge]]>=0?compact_row[3][due_slot[core_edge]]:0))$fatal(1,"slot metadata identity h3");
  meta_checks=meta_checks+1;
 end
 end
end
always @(posedge core_clk)begin
 #2;if(rst_n)begin
 if(home4.slot_response_v!==raw_due[core_edge])$fatal(1,"slot metadata calendar h4");
 if(raw_due[core_edge])begin
  if(home4.slot_response_present!==(compact_row[4][due_slot[core_edge]]>=0) || home4.slot_response_sector!==4'(due_sector[core_edge]) || home4.slot_response_row!==5'(compact_row[4][due_slot[core_edge]]>=0?compact_row[4][due_slot[core_edge]]:0))$fatal(1,"slot metadata identity h4");
  meta_checks=meta_checks+1;
 end
 end
end
always @(posedge core_clk)begin
 #2;if(rst_n)begin
 if(home5.slot_response_v!==raw_due[core_edge])$fatal(1,"slot metadata calendar h5");
 if(raw_due[core_edge])begin
  if(home5.slot_response_present!==(compact_row[5][due_slot[core_edge]]>=0) || home5.slot_response_sector!==4'(due_sector[core_edge]) || home5.slot_response_row!==5'(compact_row[5][due_slot[core_edge]]>=0?compact_row[5][due_slot[core_edge]]:0))$fatal(1,"slot metadata identity h5");
  meta_checks=meta_checks+1;
 end
 end
end
always @(posedge core_clk)begin
 #2;if(rst_n)begin
 if(home6.slot_response_v!==raw_due[core_edge])$fatal(1,"slot metadata calendar h6");
 if(raw_due[core_edge])begin
  if(home6.slot_response_present!==(compact_row[6][due_slot[core_edge]]>=0) || home6.slot_response_sector!==4'(due_sector[core_edge]) || home6.slot_response_row!==5'(compact_row[6][due_slot[core_edge]]>=0?compact_row[6][due_slot[core_edge]]:0))$fatal(1,"slot metadata identity h6");
  meta_checks=meta_checks+1;
 end
 end
end
always @(posedge core_clk)begin
 #2;if(rst_n)begin
 if(home7.slot_response_v!==raw_due[core_edge])$fatal(1,"slot metadata calendar h7");
 if(raw_due[core_edge])begin
  if(home7.slot_response_present!==(compact_row[7][due_slot[core_edge]]>=0) || home7.slot_response_sector!==4'(due_sector[core_edge]) || home7.slot_response_row!==5'(compact_row[7][due_slot[core_edge]]>=0?compact_row[7][due_slot[core_edge]]:0))$fatal(1,"slot metadata identity h7");
  meta_checks=meta_checks+1;
 end
 end
end

always @(posedge hbm_clk)begin
 if(rst_n && home0.collected)begin
  for(integer p=0;p<32;p=p+1)begin
   for(integer q=0;q<36;q=q+1)begin
    if(home0.request_present[q] && home0.request_pc[q]==p &&
       (!home0.row_locked[p] || home0.request_address[q][29:15]==home0.selected_row[p]) && !home0.kv[p])
      $fatal(1,"independentPCserviceblocked h0 p%0d",p);
   end
  end
 end
end
always @(posedge hbm_clk)begin
 if(rst_n && home1.collected)begin
  for(integer p=0;p<32;p=p+1)begin
   for(integer q=0;q<36;q=q+1)begin
    if(home1.request_present[q] && home1.request_pc[q]==p &&
       (!home1.row_locked[p] || home1.request_address[q][29:15]==home1.selected_row[p]) && !home1.kv[p])
      $fatal(1,"independentPCserviceblocked h1 p%0d",p);
   end
  end
 end
end
always @(posedge hbm_clk)begin
 if(rst_n && home2.collected)begin
  for(integer p=0;p<32;p=p+1)begin
   for(integer q=0;q<36;q=q+1)begin
    if(home2.request_present[q] && home2.request_pc[q]==p &&
       (!home2.row_locked[p] || home2.request_address[q][29:15]==home2.selected_row[p]) && !home2.kv[p])
      $fatal(1,"independentPCserviceblocked h2 p%0d",p);
   end
  end
 end
end
always @(posedge hbm_clk)begin
 if(rst_n && home3.collected)begin
  for(integer p=0;p<32;p=p+1)begin
   for(integer q=0;q<36;q=q+1)begin
    if(home3.request_present[q] && home3.request_pc[q]==p &&
       (!home3.row_locked[p] || home3.request_address[q][29:15]==home3.selected_row[p]) && !home3.kv[p])
      $fatal(1,"independentPCserviceblocked h3 p%0d",p);
   end
  end
 end
end
always @(posedge hbm_clk)begin
 if(rst_n && home4.collected)begin
  for(integer p=0;p<32;p=p+1)begin
   for(integer q=0;q<36;q=q+1)begin
    if(home4.request_present[q] && home4.request_pc[q]==p &&
       (!home4.row_locked[p] || home4.request_address[q][29:15]==home4.selected_row[p]) && !home4.kv[p])
      $fatal(1,"independentPCserviceblocked h4 p%0d",p);
   end
  end
 end
end
always @(posedge hbm_clk)begin
 if(rst_n && home5.collected)begin
  for(integer p=0;p<32;p=p+1)begin
   for(integer q=0;q<36;q=q+1)begin
    if(home5.request_present[q] && home5.request_pc[q]==p &&
       (!home5.row_locked[p] || home5.request_address[q][29:15]==home5.selected_row[p]) && !home5.kv[p])
      $fatal(1,"independentPCserviceblocked h5 p%0d",p);
   end
  end
 end
end
always @(posedge hbm_clk)begin
 if(rst_n && home6.collected)begin
  for(integer p=0;p<32;p=p+1)begin
   for(integer q=0;q<36;q=q+1)begin
    if(home6.request_present[q] && home6.request_pc[q]==p &&
       (!home6.row_locked[p] || home6.request_address[q][29:15]==home6.selected_row[p]) && !home6.kv[p])
      $fatal(1,"independentPCserviceblocked h6 p%0d",p);
   end
  end
 end
end
always @(posedge hbm_clk)begin
 if(rst_n && home7.collected)begin
  for(integer p=0;p<32;p=p+1)begin
   for(integer q=0;q<36;q=q+1)begin
    if(home7.request_present[q] && home7.request_pc[q]==p &&
       (!home7.row_locked[p] || home7.request_address[q][29:15]==home7.selected_row[p]) && !home7.kv[p])
      $fatal(1,"independentPCserviceblocked h7 p%0d",p);
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
   last_act[h][p]=-1000;ref_at[h][p]=-1000;for(integer g=0;g<4;g=g+1)begin last_act_bg[h][p][g]=-1000;last_col_bg[h][p][g]=-1000;faw[h][p][g]=-1000;end
   due_read[h][p]=0;for(integer d=0;d<=22;d=d+1)due_data[h][p][d]=0;
   for(integer b=0;b<32;b=b+1)begin read_at[h][p][b]=-1000;opened[h][p][b]=0;physical_row[h][p][b]=0;act_at[h][p][b]=-1000;pre_at[h][p][b]=-1000;ref_until[h][p][b]=-1000;end
  end
 end
owner[0]=0;base_sector[0]=65362329;expected_address[0]=37'd105170809632;
owner[1]=0;base_sector[1]=220857147;expected_address[1]=37'd110146643808;
owner[2]=0;base_sector[2]=417973230;expected_address[2]=37'd116454358464;
owner[3]=1;base_sector[3]=55671912;expected_address[3]=37'd104860716288;
owner[4]=1;base_sector[4]=200178234;expected_address[4]=37'd109484918592;
owner[5]=1;base_sector[5]=316600056;expected_address[5]=37'd113210416896;
owner[6]=2;base_sector[6]=99602649;expected_address[6]=37'd106266499872;
owner[7]=2;base_sector[7]=195046668;expected_address[7]=37'd109320708480;
owner[8]=2;base_sector[8]=311483223;expected_address[8]=37'd113046678240;
owner[9]=3;base_sector[9]=45337617;expected_address[9]=37'd104530018848;
owner[10]=3;base_sector[10]=217660968;expected_address[10]=37'd110044366080;
owner[11]=3;base_sector[11]=310161717;expected_address[11]=37'd113004390048;
owner[12]=4;base_sector[12]=44781921;expected_address[12]=37'd104512236576;
owner[13]=4;base_sector[13]=171279162;expected_address[13]=37'd108560148288;
owner[14]=4;base_sector[14]=289001862;expected_address[14]=37'd112327274688;
owner[15]=5;base_sector[15]=20006622;expected_address[15]=37'd103719427008;
owner[16]=5;base_sector[16]=246938310;expected_address[16]=37'd110981241024;
owner[17]=5;base_sector[17]=327823794;expected_address[17]=37'd113569576512;
owner[18]=6;base_sector[18]=30011022;expected_address[18]=37'd104039567808;
owner[19]=6;base_sector[19]=197909802;expected_address[19]=37'd109412328768;
owner[20]=6;base_sector[20]=368510175;expected_address[20]=37'd114871540704;
owner[21]=7;base_sector[21]=136401966;expected_address[21]=37'd107444078016;
owner[22]=7;base_sector[22]=216248544;expected_address[22]=37'd109999168512;
owner[23]=7;base_sector[23]=351420147;expected_address[23]=37'd114324659808;
compact_row[0][0]=0;
compact_row[0][1]=1;
compact_row[0][2]=2;
compact_row[0][3]=-1;
compact_row[1][0]=3;
compact_row[1][1]=4;
compact_row[1][2]=5;
compact_row[1][3]=-1;
compact_row[2][0]=6;
compact_row[2][1]=7;
compact_row[2][2]=8;
compact_row[2][3]=-1;
compact_row[3][0]=9;
compact_row[3][1]=10;
compact_row[3][2]=11;
compact_row[3][3]=-1;
compact_row[4][0]=12;
compact_row[4][1]=13;
compact_row[4][2]=14;
compact_row[4][3]=-1;
compact_row[5][0]=15;
compact_row[5][1]=16;
compact_row[5][2]=17;
compact_row[5][3]=-1;
compact_row[6][0]=18;
compact_row[6][1]=19;
compact_row[6][2]=20;
compact_row[6][3]=-1;
compact_row[7][0]=21;
compact_row[7][1]=22;
compact_row[7][2]=23;
compact_row[7][3]=-1;
repeat(4)tick;@(negedge core_clk);rst_n=1;epoch_begin=1;tick;@(negedge core_clk);epoch_begin=0;
@(negedge core_clk);in_valid=1;in_first=1;in_cid=17;capture=0;tick;@(negedge core_clk);in_valid=0;repeat(39)tick;
@(negedge core_clk);in_valid=1;in_first=0;in_cid=999;capture=0;tick;@(negedge core_clk);in_valid=0;repeat(39)tick;
@(negedge core_clk);in_valid=1;in_first=0;in_cid=5543;capture=0;tick;@(negedge core_clk);in_valid=0;repeat(39)tick;
@(negedge core_clk);in_valid=1;in_first=0;in_cid=99091;capture=1;tick;@(negedge core_clk);in_valid=0;repeat(39)tick;
if(home0.owned_slot_valid!==4'd7 || home0.owned_row_count!==3'd3)$fatal(1,"compact owned count");
if(home0.owned_slot_global_row[0+:5]!==5'd0)$fatal(1,"actual compact row identity");
if(home0.owned_slot_global_row[5+:5]!==5'd1)$fatal(1,"actual compact row identity");
if(home0.owned_slot_global_row[10+:5]!==5'd2)$fatal(1,"actual compact row identity");
if(home1.owned_slot_valid!==4'd7 || home1.owned_row_count!==3'd3)$fatal(1,"compact owned count");
if(home1.owned_slot_global_row[0+:5]!==5'd3)$fatal(1,"actual compact row identity");
if(home1.owned_slot_global_row[5+:5]!==5'd4)$fatal(1,"actual compact row identity");
if(home1.owned_slot_global_row[10+:5]!==5'd5)$fatal(1,"actual compact row identity");
if(home2.owned_slot_valid!==4'd7 || home2.owned_row_count!==3'd3)$fatal(1,"compact owned count");
if(home2.owned_slot_global_row[0+:5]!==5'd6)$fatal(1,"actual compact row identity");
if(home2.owned_slot_global_row[5+:5]!==5'd7)$fatal(1,"actual compact row identity");
if(home2.owned_slot_global_row[10+:5]!==5'd8)$fatal(1,"actual compact row identity");
if(home3.owned_slot_valid!==4'd7 || home3.owned_row_count!==3'd3)$fatal(1,"compact owned count");
if(home3.owned_slot_global_row[0+:5]!==5'd9)$fatal(1,"actual compact row identity");
if(home3.owned_slot_global_row[5+:5]!==5'd10)$fatal(1,"actual compact row identity");
if(home3.owned_slot_global_row[10+:5]!==5'd11)$fatal(1,"actual compact row identity");
if(home4.owned_slot_valid!==4'd7 || home4.owned_row_count!==3'd3)$fatal(1,"compact owned count");
if(home4.owned_slot_global_row[0+:5]!==5'd12)$fatal(1,"actual compact row identity");
if(home4.owned_slot_global_row[5+:5]!==5'd13)$fatal(1,"actual compact row identity");
if(home4.owned_slot_global_row[10+:5]!==5'd14)$fatal(1,"actual compact row identity");
if(home5.owned_slot_valid!==4'd7 || home5.owned_row_count!==3'd3)$fatal(1,"compact owned count");
if(home5.owned_slot_global_row[0+:5]!==5'd15)$fatal(1,"actual compact row identity");
if(home5.owned_slot_global_row[5+:5]!==5'd16)$fatal(1,"actual compact row identity");
if(home5.owned_slot_global_row[10+:5]!==5'd17)$fatal(1,"actual compact row identity");
if(home6.owned_slot_valid!==4'd7 || home6.owned_row_count!==3'd3)$fatal(1,"compact owned count");
if(home6.owned_slot_global_row[0+:5]!==5'd18)$fatal(1,"actual compact row identity");
if(home6.owned_slot_global_row[5+:5]!==5'd19)$fatal(1,"actual compact row identity");
if(home6.owned_slot_global_row[10+:5]!==5'd20)$fatal(1,"actual compact row identity");
if(home7.owned_slot_valid!==4'd7 || home7.owned_row_count!==3'd3)$fatal(1,"compact owned count");
if(home7.owned_slot_global_row[0+:5]!==5'd21)$fatal(1,"actual compact row identity");
if(home7.owned_slot_global_row[5+:5]!==5'd22)$fatal(1,"actual compact row identity");
if(home7.owned_slot_global_row[10+:5]!==5'd23)$fatal(1,"actual compact row identity");
if(descriptors!=24)$fatal(1,"full24hashdescriptorcount");
 @(negedge core_clk);fetch_start=1;tick;fetch_edge=core_edge;@(negedge core_clk);fetch_start=0;
 repeat(36+8192-1)begin tick;if(done!=0)$fatal(1,"earlycompletion");end
 tick;if(done!==8'hff || core_edge-fetch_edge!=36+8192)$fatal(1,"fixedfullfetchdone");
 repeat(4)tick;
 for(j=0;j<4;j=j+1)for(s=0;s<9;s=s+1)begin
  @(negedge core_clk);local_read_v=1;local_read_slot=j;local_read_sector=s;
  raw_due[core_edge+4]=1;due_slot[core_edge+4]=j;due_sector[core_edge+4]=s;
  for(integer h=0;h<8;h=h+1)if(compact_row[h][j]>=0)begin raw_due_mask[core_edge+4][h]=1;due_word[h][core_edge+4]=compact_row[h][j]*9+s;end
  tick;
 end
 @(negedge core_clk);local_read_v=0;repeat(5)tick;
 if(meta_checks!=288)$fatal(1,"all160slot-source metadata controls");
 if(checks!=216 || reads!=216 || refreshes<256)$fatal(1,"fullnativehomecounts reads%0d checks%0d",reads,checks);
 $display("PASS actualhash8homes nativeRWcontrollers CDCtwo-clocks SRAM216sectors descriptors24 checks%0d physicalRD%0d REFpb%0d fixedfetch8228coreedges",checks,reads,refreshes);$finish;
end
endmodule
