`timescale 1ns/1fs
module tb;
localparam real TICK=0.0520833333333333;
localparam integer PREFIX=15300,FPREFIX=0;
reg core_clk=0,fec_clk=0,hbm_clk=0;
always #(8*TICK)core_clk=~core_clk;initial begin wait(link_core_on);forever #(8.5*TICK)fec_clk=~fec_clk;end
initial begin #0.017;forever #0.512 hbm_clk=~hbm_clk;end
integer fc=0,cc=0;realtime link_origin;reg phase_checked=0;always @(posedge link_core_on)link_origin=$realtime;always @(posedge fec_clk)if(!phase_checked)begin phase_checked=1;if($realtime-link_origin<0.4427075 || $realtime-link_origin>0.4427085)$fatal(1,"FEC_ORIGIN_PHASE");end
reg rst_n=0,epoch_begin=0,fetch_start=0,capture=0,in_valid=0,in_first=0;reg[16:0]in_cid=0;
wire[1:0]request_valid;wire[13:0]request_rank;wire[73:0]request_address;
wire[51:0]request_local_row;wire[9:0]request_staging_slot,request_list_index;
wire[39:0]gather_slot_id;wire hash_done,hash_fault;
ot_hbm_engram_hash_home_native hash(.clk(core_clk),.rst_n(rst_n),.in_valid(in_valid),.in_first(in_first),.in_cid(in_cid),
.request_valid(request_valid),.request_rank(request_rank),.request_address(request_address),.request_local_row(request_local_row),
.request_staging_slot(request_staging_slot),.gather_slot_id(gather_slot_id),.request_list_index(request_list_index),.done(hash_done),.fault(hash_fault));
wire[7:0]local_read_v;wire[1:0]local_read_slot[0:7];wire[3:0]local_read_sector[0:7];
wire[3:0]owned_valid[0:7];wire[19:0]owned_rows[0:7];wire[2:0]owned_count[0:7];wire[7:0]response_v,response_present;wire[4:0]response_row[0:7];wire[3:0]response_sector[0:7];
reg[7:0]read_v=0;reg[4:0]read_row=0;reg[3:0]read_sector=0;
wire[7:0]raw_v,done,fault;wire[4:0]raw_row[0:7];wire[3:0]raw_sector[0:7];wire[255:0]raw_data[0:7];
wire[31:0]row_v[0:7],col_v[0:7],col_we[0:7];wire[95:0]row_op[0:7];wire[159:0]row_bank[0:7],col_bank[0:7],col_col[0:7];wire[607:0]row_row[0:7];
wire[8191:0]col_data[0:7];wire[1023:0]col_strb[0:7];reg[31:0]dram_rvalid[0:7];reg[8191:0]dram_rdata[0:7];
ot_hbm_engram_home_fetch_grouped_guarded #(.LOCAL_READ(1),.HOME_RANK(0)) home0(.core_clk(core_clk),.hbm_clk(hbm_clk),.rst_n(rst_n),.epoch_begin(epoch_begin),
.descriptor_v(request_valid[0] && capture),.descriptor_rank(request_rank[0+:7]),.descriptor_index(request_list_index[0+:5]),.descriptor_address(request_address[0+:37]),
.local_read_v(local_read_v[0]),.local_read_slot(local_read_slot[0]),.local_read_sector(local_read_sector[0]),.fetch_start(fetch_start),.read_v(1'b0),.read_row(5'b0),.read_sector(4'b0),.owned_slot_valid(owned_valid[0]),.owned_slot_global_row(owned_rows[0]),.owned_row_count(owned_count[0]),.slot_response_v(response_v[0]),.slot_response_present(response_present[0]),.slot_response_row(response_row[0]),.slot_response_sector(response_sector[0]),.raw_v(raw_v[0]),.raw_row(raw_row[0]),.raw_sector(raw_sector[0]),.raw_data(raw_data[0]),.done(done[0]),.fault(fault[0]),
.row_v(row_v[0]),.row_op(row_op[0]),.row_bank(row_bank[0]),.row_row(row_row[0]),.col_v(col_v[0]),.col_we(col_we[0]),.col_bank(col_bank[0]),.col_col(col_col[0]),.col_data(col_data[0]),.col_strb(col_strb[0]),.dram_rvalid(dram_rvalid[0]),.dram_rdata(dram_rdata[0]));
ot_hbm_engram_home_fetch_grouped_guarded #(.LOCAL_READ(1),.HOME_RANK(1)) home1(.core_clk(core_clk),.hbm_clk(hbm_clk),.rst_n(rst_n),.epoch_begin(epoch_begin),
.descriptor_v(request_valid[0] && capture),.descriptor_rank(request_rank[0+:7]),.descriptor_index(request_list_index[0+:5]),.descriptor_address(request_address[0+:37]),
.local_read_v(local_read_v[1]),.local_read_slot(local_read_slot[1]),.local_read_sector(local_read_sector[1]),.fetch_start(fetch_start),.read_v(1'b0),.read_row(5'b0),.read_sector(4'b0),.owned_slot_valid(owned_valid[1]),.owned_slot_global_row(owned_rows[1]),.owned_row_count(owned_count[1]),.slot_response_v(response_v[1]),.slot_response_present(response_present[1]),.slot_response_row(response_row[1]),.slot_response_sector(response_sector[1]),.raw_v(raw_v[1]),.raw_row(raw_row[1]),.raw_sector(raw_sector[1]),.raw_data(raw_data[1]),.done(done[1]),.fault(fault[1]),
.row_v(row_v[1]),.row_op(row_op[1]),.row_bank(row_bank[1]),.row_row(row_row[1]),.col_v(col_v[1]),.col_we(col_we[1]),.col_bank(col_bank[1]),.col_col(col_col[1]),.col_data(col_data[1]),.col_strb(col_strb[1]),.dram_rvalid(dram_rvalid[1]),.dram_rdata(dram_rdata[1]));
ot_hbm_engram_home_fetch_grouped_guarded #(.LOCAL_READ(1),.HOME_RANK(2)) home2(.core_clk(core_clk),.hbm_clk(hbm_clk),.rst_n(rst_n),.epoch_begin(epoch_begin),
.descriptor_v(request_valid[0] && capture),.descriptor_rank(request_rank[0+:7]),.descriptor_index(request_list_index[0+:5]),.descriptor_address(request_address[0+:37]),
.local_read_v(local_read_v[2]),.local_read_slot(local_read_slot[2]),.local_read_sector(local_read_sector[2]),.fetch_start(fetch_start),.read_v(1'b0),.read_row(5'b0),.read_sector(4'b0),.owned_slot_valid(owned_valid[2]),.owned_slot_global_row(owned_rows[2]),.owned_row_count(owned_count[2]),.slot_response_v(response_v[2]),.slot_response_present(response_present[2]),.slot_response_row(response_row[2]),.slot_response_sector(response_sector[2]),.raw_v(raw_v[2]),.raw_row(raw_row[2]),.raw_sector(raw_sector[2]),.raw_data(raw_data[2]),.done(done[2]),.fault(fault[2]),
.row_v(row_v[2]),.row_op(row_op[2]),.row_bank(row_bank[2]),.row_row(row_row[2]),.col_v(col_v[2]),.col_we(col_we[2]),.col_bank(col_bank[2]),.col_col(col_col[2]),.col_data(col_data[2]),.col_strb(col_strb[2]),.dram_rvalid(dram_rvalid[2]),.dram_rdata(dram_rdata[2]));
ot_hbm_engram_home_fetch_grouped_guarded #(.LOCAL_READ(1),.HOME_RANK(3)) home3(.core_clk(core_clk),.hbm_clk(hbm_clk),.rst_n(rst_n),.epoch_begin(epoch_begin),
.descriptor_v(request_valid[0] && capture),.descriptor_rank(request_rank[0+:7]),.descriptor_index(request_list_index[0+:5]),.descriptor_address(request_address[0+:37]),
.local_read_v(local_read_v[3]),.local_read_slot(local_read_slot[3]),.local_read_sector(local_read_sector[3]),.fetch_start(fetch_start),.read_v(1'b0),.read_row(5'b0),.read_sector(4'b0),.owned_slot_valid(owned_valid[3]),.owned_slot_global_row(owned_rows[3]),.owned_row_count(owned_count[3]),.slot_response_v(response_v[3]),.slot_response_present(response_present[3]),.slot_response_row(response_row[3]),.slot_response_sector(response_sector[3]),.raw_v(raw_v[3]),.raw_row(raw_row[3]),.raw_sector(raw_sector[3]),.raw_data(raw_data[3]),.done(done[3]),.fault(fault[3]),
.row_v(row_v[3]),.row_op(row_op[3]),.row_bank(row_bank[3]),.row_row(row_row[3]),.col_v(col_v[3]),.col_we(col_we[3]),.col_bank(col_bank[3]),.col_col(col_col[3]),.col_data(col_data[3]),.col_strb(col_strb[3]),.dram_rvalid(dram_rvalid[3]),.dram_rdata(dram_rdata[3]));
ot_hbm_engram_home_fetch_grouped_guarded #(.LOCAL_READ(1),.HOME_RANK(4)) home4(.core_clk(core_clk),.hbm_clk(hbm_clk),.rst_n(rst_n),.epoch_begin(epoch_begin),
.descriptor_v(request_valid[0] && capture),.descriptor_rank(request_rank[0+:7]),.descriptor_index(request_list_index[0+:5]),.descriptor_address(request_address[0+:37]),
.local_read_v(local_read_v[4]),.local_read_slot(local_read_slot[4]),.local_read_sector(local_read_sector[4]),.fetch_start(fetch_start),.read_v(1'b0),.read_row(5'b0),.read_sector(4'b0),.owned_slot_valid(owned_valid[4]),.owned_slot_global_row(owned_rows[4]),.owned_row_count(owned_count[4]),.slot_response_v(response_v[4]),.slot_response_present(response_present[4]),.slot_response_row(response_row[4]),.slot_response_sector(response_sector[4]),.raw_v(raw_v[4]),.raw_row(raw_row[4]),.raw_sector(raw_sector[4]),.raw_data(raw_data[4]),.done(done[4]),.fault(fault[4]),
.row_v(row_v[4]),.row_op(row_op[4]),.row_bank(row_bank[4]),.row_row(row_row[4]),.col_v(col_v[4]),.col_we(col_we[4]),.col_bank(col_bank[4]),.col_col(col_col[4]),.col_data(col_data[4]),.col_strb(col_strb[4]),.dram_rvalid(dram_rvalid[4]),.dram_rdata(dram_rdata[4]));
ot_hbm_engram_home_fetch_grouped_guarded #(.LOCAL_READ(1),.HOME_RANK(5)) home5(.core_clk(core_clk),.hbm_clk(hbm_clk),.rst_n(rst_n),.epoch_begin(epoch_begin),
.descriptor_v(request_valid[0] && capture),.descriptor_rank(request_rank[0+:7]),.descriptor_index(request_list_index[0+:5]),.descriptor_address(request_address[0+:37]),
.local_read_v(local_read_v[5]),.local_read_slot(local_read_slot[5]),.local_read_sector(local_read_sector[5]),.fetch_start(fetch_start),.read_v(1'b0),.read_row(5'b0),.read_sector(4'b0),.owned_slot_valid(owned_valid[5]),.owned_slot_global_row(owned_rows[5]),.owned_row_count(owned_count[5]),.slot_response_v(response_v[5]),.slot_response_present(response_present[5]),.slot_response_row(response_row[5]),.slot_response_sector(response_sector[5]),.raw_v(raw_v[5]),.raw_row(raw_row[5]),.raw_sector(raw_sector[5]),.raw_data(raw_data[5]),.done(done[5]),.fault(fault[5]),
.row_v(row_v[5]),.row_op(row_op[5]),.row_bank(row_bank[5]),.row_row(row_row[5]),.col_v(col_v[5]),.col_we(col_we[5]),.col_bank(col_bank[5]),.col_col(col_col[5]),.col_data(col_data[5]),.col_strb(col_strb[5]),.dram_rvalid(dram_rvalid[5]),.dram_rdata(dram_rdata[5]));
ot_hbm_engram_home_fetch_grouped_guarded #(.LOCAL_READ(1),.HOME_RANK(6)) home6(.core_clk(core_clk),.hbm_clk(hbm_clk),.rst_n(rst_n),.epoch_begin(epoch_begin),
.descriptor_v(request_valid[0] && capture),.descriptor_rank(request_rank[0+:7]),.descriptor_index(request_list_index[0+:5]),.descriptor_address(request_address[0+:37]),
.local_read_v(local_read_v[6]),.local_read_slot(local_read_slot[6]),.local_read_sector(local_read_sector[6]),.fetch_start(fetch_start),.read_v(1'b0),.read_row(5'b0),.read_sector(4'b0),.owned_slot_valid(owned_valid[6]),.owned_slot_global_row(owned_rows[6]),.owned_row_count(owned_count[6]),.slot_response_v(response_v[6]),.slot_response_present(response_present[6]),.slot_response_row(response_row[6]),.slot_response_sector(response_sector[6]),.raw_v(raw_v[6]),.raw_row(raw_row[6]),.raw_sector(raw_sector[6]),.raw_data(raw_data[6]),.done(done[6]),.fault(fault[6]),
.row_v(row_v[6]),.row_op(row_op[6]),.row_bank(row_bank[6]),.row_row(row_row[6]),.col_v(col_v[6]),.col_we(col_we[6]),.col_bank(col_bank[6]),.col_col(col_col[6]),.col_data(col_data[6]),.col_strb(col_strb[6]),.dram_rvalid(dram_rvalid[6]),.dram_rdata(dram_rdata[6]));
ot_hbm_engram_home_fetch_grouped_guarded #(.LOCAL_READ(1),.HOME_RANK(7)) home7(.core_clk(core_clk),.hbm_clk(hbm_clk),.rst_n(rst_n),.epoch_begin(epoch_begin),
.descriptor_v(request_valid[0] && capture),.descriptor_rank(request_rank[0+:7]),.descriptor_index(request_list_index[0+:5]),.descriptor_address(request_address[0+:37]),
.local_read_v(local_read_v[7]),.local_read_slot(local_read_slot[7]),.local_read_sector(local_read_sector[7]),.fetch_start(fetch_start),.read_v(1'b0),.read_row(5'b0),.read_sector(4'b0),.owned_slot_valid(owned_valid[7]),.owned_slot_global_row(owned_rows[7]),.owned_row_count(owned_count[7]),.slot_response_v(response_v[7]),.slot_response_present(response_present[7]),.slot_response_row(response_row[7]),.slot_response_sector(response_sector[7]),.raw_v(raw_v[7]),.raw_row(raw_row[7]),.raw_sector(raw_sector[7]),.raw_data(raw_data[7]),.done(done[7]),.fault(fault[7]),
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
    due_read[h][p][0]<=1;due_data[h][p][0]<=external_words[0*216+hit*9+off]^((MUT==2&&hit==0&&off==0)?256'd1:256'd0);reads=reads+1;
   end
   if(due_read[h][p]!=0)begin
    if(due_read[h][p][22])begin dram_rvalid[h][p]<=1;dram_rdata[h][p*256+:256]<=due_data[h][p][22];end
   end
  end
 end
end

always @(posedge core_clk)begin:scoreboard
 integer idx;
 core_edge=core_edge+1;cc=core_edge-PREFIX;#0.000001;
 if(core_edge%2048==0)begin $display("SLOT_CHAIN_PROGRESS globalC%0d phaseC%0d",core_edge,cc);$fflush;end
 if(rst_n)begin
  if(request_valid[0] && capture)descriptors=descriptors+1;
  if(hash_fault || fault!=0)$fatal(1,"nativeproducerfault C%0d hash%b home%h",cc,hash_fault,fault);
  if(|nodedone)begin node_done_edges=node_done_edges+1;if(cc!=404+program_limit || nodedone!==9'h1ff)$fatal(1,"NATIVE_DONE_EDGE C%0d",cc);end
  if(MUT==0 && ((|nodefault)||consumer_fault||(|linkfault)||(|fecfault)||(|pmafault)||(|padfault)))
   $fatal(1,"CHAIN_FAULT C%0d node%h link%h fec%h pma%h pad%h consumer%b",cc,nodefault,linkfault,fecfault,pmafault,padfault,consumer_fault);
  if(craw_v)begin
   if(craw_data!==external_words[0*216+craw_row*9+craw_sector])begin mismatches=mismatches+1;if(MUT==0)$fatal(1,"CHAIN_RAW_MISMATCH C%0d row%0d sector%0d",cc,craw_row,craw_sector);end
   raw_checks=raw_checks+1;
  end
  if(decoded_v)begin
   if(decoded_data!==golden[0*192+decoded_row*8+decoded_block])begin mismatches=mismatches+1;if(MUT==0)$fatal(1,"CHAIN_DECODE_MISMATCH C%0d row%0d block%0d",cc,decoded_row,decoded_block);end
   decode_checks=decode_checks+1;
  end
  if(cwrite_v)write_checks=write_checks+1;
  if(cc==3050)begin
   if(MUT==0)begin
    if(node_done_edges!=1 || nodebusy!=0)$fatal(1,"NATIVE_RETIREMENT_COUNT");
    if(!all_complete[8])$fatal(1,"SLOT_CHAIN_INCOMPLETE");
    if(raw_checks!=216 || decode_checks!=192 || write_checks!=216 || mismatches)$fatal(1,"WHOLE_CHAIN_COUNTS raw%0d decoded%0d writes%0d mismatch%0d",raw_checks,decode_checks,write_checks,mismatches);
    $display("ENGRAM_WHOLE_CHAIN_PASS actual8homehash guarded23 sectors216 rows24 packets160 NOP40 hops720 nodes9 programme189SRAM links8 TX6RX2 FEC151 age16:17 decoded192 BF166144");
   end else begin
    if(MUT==1 && !nodefault[0])$fatal(1,"PROGRAM_MUTANT_ESCAPED");
    if(MUT==3 && !nodefault[0])$fatal(1,"SLOT_MUTANT_ESCAPED");
    if(MUT==2 && mismatches==0)$fatal(1,"PAYLOAD_MUTANT_ESCAPED");
    $display("ENGRAM_WHOLE_CHAIN_MUTANT_PASS m%0d mismatch%0d nodefault%h",MUT,mismatches,nodefault);
   end
   $finish;
  end
 end
end
task tick;begin @(posedge core_clk);#0.003;end endtask
integer j,s,cididx,fetch_edge;
integer node_done_edges=0;integer program_limit=2091;initial if($value$plusargs("limit=%d",program_limit))begin end

reg cfg_v=0,desc_v=0;reg[11:0]cfg_addr=0;reg[255:0]cfg_data[0:8];reg[255:0]images[0:24191];
wire[8:0]configured,init_busy,nodebusy,nodedone,nodefault,all_complete;
wire[8:0]txv,rxv,cwv,crv;wire[611:0]txf[0:8],rxf[0:8];
wire[4:0]cwrow[0:8],crrow[0:8];wire[3:0]cwsec[0:8],crsec[0:8];wire[255:0]cwdata[0:8];
reg launch=0,linkepoch=0;always @(negedge core_clk)begin launch=cc+1==399;linkepoch=cc+1==450;end
wire[31:0]linkfault,pmafault;wire[15:0]fecfault;wire[7:0]padfault;
wire[511:0]pma[0:7];wire[1:0]status[0:7];
reg link_core_on=0,link_fec_on=0,link_rst_n=0;
 wire link_core_clk=core_clk&&link_core_on,link_fec_clk=fec_clk&&link_fec_on;
 always @(negedge core_clk)if(core_edge==PREFIX)begin link_core_on=1;link_fec_on=1;end
 always @(negedge fec_clk)begin if(fc==8)link_rst_n=1;end
 reg txstart=0,rxstart=0,txstep=0,rxstep=0,slot=0;
reg ctxs=0,ctxt=0,ctxl=0,ftxs=0,ftxt=0,ftxl=0,frxs=0,frxt=0,frxl=0,crxs=0,crxt=0,crxl=0;
reg sers=0,serr=0,dess=0,desr=0,cap_s=0,cap_t=0,cap_l=0,read_s=0,read_t=0,read_l=0;
function automatic integer C(input integer base,k);C=base+17*k/16;endfunction
function automatic integer A(input integer j);A=C(511,613*j/487);endfunction
always @(negedge core_clk)begin
 txstart=cc+1==510;rxstart=cc+1==697;ctxs=cc+1==511;crxs=cc+1==696;
 ctxt=0;ctxl=0;crxt=0;crxl=0;txstep=0;rxstep=0;slot=0;
 serr=cc+1==40;dess=cc+1==41;
 for(integer k=0;k<2048;k=k+1)begin
  if(cc+1==C(511,k))txstep=1;
  if(cc+1==C(512,k))begin ctxt=1;ctxl=k==2047;end
  if(cc+1==C(697,k))begin crxt=1;crxl=k==2047;end
  if(cc+1==C(698,k))rxstep=1;
 end
 for(integer j=0;j<1628;j=j+1)if(cc+1==A(j))slot=1;
end
integer global_fc=0;
always @(posedge fec_clk)begin global_fc=global_fc+1;fc=global_fc-FPREFIX;end
always @(negedge fec_clk)begin
 ftxs=fc+1==487;ftxt=fc+1>=488&&fc+1<=2535;ftxl=fc+1==2535;
 frxs=fc+1==648;frxt=fc+1>=649&&fc+1<=2696;frxl=fc+1==2696;
 sers=fc+1==16;desr=fc+1==64;
 cap_s=fc+1==639;cap_t=fc+1>=640&&fc+1<=2687;cap_l=fc+1==2687;
 read_s=fc+1==647;read_t=fc+1>=648&&fc+1<=2695;read_l=fc+1==2695;
end
assign rxv[0]=0;assign rxf[0]=0;
for(genvar n=0;n<9;n=n+1)begin:g_node
 wire source_v;wire[4:0]source_row;wire[3:0]source_sector;
 if(n<8)begin assign local_read_v[n]=source_v;assign local_read_slot[n]=source_row[1:0];assign local_read_sector[n]=source_sector;end
 ot_hcoll_engram_chain_slot_node #(.NODE(n),.HOME_BASE(0)) node(
 .rst_n(rst_n),.clk_control(core_clk),.clk_mem({21{core_clk}}),.clk_program_capture({21{core_clk}}),
 .clk_qcapture(core_clk),.clk_qoutput(core_clk),.clk_bridge({8{core_clk}}),.clk_rxface({3{core_clk}}),.clk_endpoint_tx({5{core_clk}}),.clk_endpoint_rx({5{core_clk}}),
 .cfg_v(cfg_v),.cfg_target(8'd120),.cfg_addr(cfg_addr),.cfg_data(cfg_data[n]),.desc_v(desc_v),.desc_base(12'd0),.desc_limit(program_limit),.desc_loops(16'd1),
 .launch_v(launch),.program_active(1'b0),.epoch_begin(linkepoch),.epoch(8'h72),.phy_up(1'b1),
 .source_read_v(source_v),.source_read_row(source_row),.source_read_sector(source_sector),
 .owned_slot_valid(n<8?owned_valid[n]:4'b0),.owned_slot_global_row(n<8?owned_rows[n]:20'b0),
 .source_response_v(n<8?response_v[n]:1'b0),.source_response_present(n<8?response_present[n]:1'b0),.source_response_row(n<8?response_row[n]:5'b0),.source_response_sector(n<8?response_sector[n]:4'b0),
 .source_raw_v(n<8?raw_v[n]:1'b0),.source_raw_row(n<8?raw_row[n]:5'b0),.source_raw_sector(n<8?raw_sector[n]:4'b0),.source_raw_data(n<8?raw_data[n]:256'b0),
 .consumer_write_v(cwv[n]),.consumer_write_row(cwrow[n]),.consumer_write_sector(cwsec[n]),.consumer_write_data(cwdata[n]),
 .consumer_read_v(crv[n]),.consumer_read_row(crrow[n]),.consumer_read_sector(crsec[n]),
 .tx_pin_v(txv[n]),.tx_pin_frame(txf[n]),.rx_pin_v(rxv[n]),.rx_pin_frame(rxf[n]),
 .consumer_complete(all_complete[n]),.configured(configured[n]),.init_busy(init_busy[n]),.busy(nodebusy[n]),.done(nodedone[n]),.fault(nodefault[n]),.issued_v(),.issued_control());
end
for(genvar l=0;l<8;l=l+1)begin:g_link
 ot_hbm_core_fec_frame_link link(.core_clk(link_core_clk),.rst_n(link_rst_n),.fec_clks({16{link_fec_clk}}),.phy_clks({6{link_core_clk}}),
 .tx_start(txstart),.rx_start(rxstart),.tx_word_step(txstep),.rx_word_step(rxstep),.tx_slot_v(slot),.endpoint_tx_v(txv[l]),.endpoint_tx_frame(txf[l]),
 .expected_tx_slot(),.endpoint_rx_v(rxv[l+1]),.endpoint_rx_frame(rxf[l+1]),
 .ctx_start(ctxs),.ctx_take(ctxt),.ctx_last(ctxl),.ftx_start(ftxs),.ftx_take(ftxt),.ftx_last(ftxl),
 .frx_start(frxs),.frx_take(frxt),.frx_last(frxl),.crx_start(crxs),.crx_take(crxt),.crx_last(crxl),
 .capture_start(cap_s),.capture_take(cap_t),.capture_last(cap_l),.read_start(read_s),.read_take(read_t),.read_last(read_l),
 .ser_write_start(sers),.ser_read_start(serr),.des_write_start(dess),.des_read_start(desr),
 .pma_tx(pma[l]),.pma_rx(pma[l]),.fault_core(linkfault[l*4+:4]),.crossing_fault_fec(fecfault[l*2+:2]),.pma_fault(pmafault[l*4+:4]),.status(status[l]),.padding_fault(padfault[l]));
end
wire cwrite_v=cwv[8],decoded_v,craw_v,consumer_fault;wire[4:0]decoded_row,craw_row;wire[2:0]decoded_block;wire[3:0]craw_sector;wire[511:0]decoded_data;wire[255:0]craw_data;
reg[511:0]golden[0:383];integer raw_checks=0,decode_checks=0,write_checks=0,mismatches=0,MUT=0;
ot_hbm_engram_row_store_decode consumer(.clk(core_clk),.rst_n(rst_n),.epoch_begin(linkepoch),
 .write_v(cwv[8]),.write_row(cwrow[8]),.write_sector(cwsec[8]),.write_data(cwdata[8]),.read_v(crv[8]),.read_row(crrow[8]),.read_sector(crsec[8]),
 .out_v(decoded_v),.out_row(decoded_row),.out_block(decoded_block),.out_data(decoded_data),.raw_v(craw_v),.raw_row(craw_row),.raw_sector(craw_sector),.raw_data(craw_data),.fault(consumer_fault));
initial begin #40000;$fatal(1,"WHOLE_CHAIN_TIMEOUT");end

for(genvar d=0;d<9;d=d+1)begin:g_diagnostic
 always @(negedge core_clk)if((cc+1>=508 && cc+1<=513)||(cc+1>=699 && cc+1<=707))begin $display("FRAME_INPUT C%0d n%0d tx%b rx%b expect%b seq%0d",cc+1,d,txv[d],rxv[d],g_node[d].node.ctl[124],g_node[d].node.ctl[125+:16]);$fflush;end
 always @(posedge core_clk)begin #0.0000005;if((cc>=508 && cc<=513)||(cc>=699 && cc<=707))begin $display("FRAME_EDGE C%0d n%0d tx%b rx%b expect%b seq%0d",cc,d,txv[d],rxv[d],g_node[d].node.ctl[124],g_node[d].node.ctl[125+:16]);$fflush;end if(cc>450 && (g_node[d].node.packet_fault || g_node[d].node.qfault || (|g_node[d].node.bf) || (|g_node[d].node.rf) || g_node[d].node.tx_abort || g_node[d].node.rx_abort))begin
 $display("NODE_DETAIL C%0d n%0d program%b packet%b q%b kind%h bridge%h face%h tx%h rx%h ctl%h",cc,d,g_node[d].node.program_fault,g_node[d].node.packet_fault,g_node[d].node.qfault,g_node[d].node.qkind,g_node[d].node.bf,g_node[d].node.rf,g_node[d].node.tx_cause,g_node[d].node.rx_cause,g_node[d].node.ctl);$fflush;end end
end

initial begin
 for(integer z=0;z<=130000;z=z+1)raw_due_mask[z]=0;
 $readmemh("external_hbm_sectors.hex",external_words);
 $readmemh("expected_bf16.hex",golden);
 $readmemh("n0.hex",images,0,2687);cfg_data[0]=0;
$readmemh("n1.hex",images,2688,5375);cfg_data[1]=0;
$readmemh("n2.hex",images,5376,8063);cfg_data[2]=0;
$readmemh("n3.hex",images,8064,10751);cfg_data[3]=0;
$readmemh("n4.hex",images,10752,13439);cfg_data[4]=0;
$readmemh("n5.hex",images,13440,16127);cfg_data[5]=0;
$readmemh("n6.hex",images,16128,18815);cfg_data[6]=0;
$readmemh("n7.hex",images,18816,21503);cfg_data[7]=0;
$readmemh("n8.hex",images,21504,24191);cfg_data[8]=0;
 if($value$plusargs("mut=%d",MUT))begin end
 if(MUT==1)images[0]=images[0]^(256'd1<<238);
 if(MUT==3)begin
  for(integer i=0;i<2688;i=i+1)if(images[i][107])begin images[i]=images[i]^(256'd1<<108);break;end
 end

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
 if(reads!=216 || descriptors!=24)$fatal(1,"nativefetchcounts");
 for(integer w=0;w<1344;w=w+1)begin
  @(negedge core_clk);cfg_v=1;cfg_addr=12'(w*2);
  for(integer n=0;n<9;n=n+1)cfg_data[n]=images[n*2688+w*2];tick;
  @(negedge core_clk);cfg_addr=12'(w*2+1);
  for(integer n=0;n<9;n=n+1)cfg_data[n]=images[n*2688+w*2+1];tick;
  @(negedge core_clk);cfg_v=0;repeat(2)tick;
 end
 @(negedge core_clk);desc_v=1;tick;@(negedge core_clk);desc_v=0;
 repeat(1346)tick;
 if(MUT==1)begin if(!nodefault[0])$fatal(1,"reservedprogramme_mutant_escaped");$display("ENGRAM_SLOT_PROGRAM_MUTANT_PASS");$finish;end else begin
 if(configured!==9'h1ff || init_busy!=0)$fatal(1,"nativecatalogue_notconfigured");
 $display("SLOT_CHAIN_PREFLIGHT actual24rows216DRAMreads 9x21nativeprogrammeSRAMs ready C%0d",core_edge);$fflush;
 end
end
endmodule
