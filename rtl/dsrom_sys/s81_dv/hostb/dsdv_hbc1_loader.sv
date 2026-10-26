`timescale 1ns/1ps
`default_nettype none
// SOURCE-ONLY minimal HBC1 local authority loader. No runtime qualification.
// Compile-time slots/clock/reset identity are required; defaults refuse writes.
// This is the addressed local consumer, not a nonlocal bootstrap router.
module dsdv_hbc1_loader #(
 parameter integer ENABLE=0, LOCAL_STAGE=255, LOCAL_RANK=4, PHASE_BOUND=0, VARIABLE_WORDS=0, ALLOW_RELOAD=0,
 parameter [63:0] CLOCK_RESET_ID=64'd0,
 parameter [47:0] BOOT_HEADER_EDGE=48'hffffffffffff,
 parameter [47:0] BOOT_COMMIT_EDGE=48'hffffffffffff
)(input wire ck,rst_n,input wire[1103:0] ring_i,input wire job_active,
 output wire[1103:0] local_ring,output wire[511:0] active_fields,
 output wire context_valid,output wire[47:0] receiver_edge,boot_edge,
 output wire[7:0] fault,
 // COLLB-HOST 10-21 native census (max 32 loads): kept same-edge copies for the affine book
 output wire context_valid_bk,output wire[47:0] receiver_edge_bk);
 generate if(ENABLE==0)begin:g_original
  assign local_ring=ring_i;assign active_fields=0;assign context_valid=0;
  assign receiver_edge=0;assign boot_edge=0;assign fault=0;
  assign context_valid_bk=0;assign receiver_edge_bk=0;
 end else begin:g_hbc
  localparam[47:0] BODY_EDGE=BOOT_HEADER_EDGE+48'd4;
  localparam[47:0] COMMIT_DELTA=BOOT_COMMIT_EDGE-BODY_EDGE;
  localparam VALID_PROFILE=PHASE_BOUND!=0&&LOCAL_STAGE<241&&LOCAL_STAGE>=0&&LOCAL_RANK<4&&LOCAL_RANK>=0&&
   CLOCK_RESET_ID!=0&&BOOT_HEADER_EDGE!=48'hffffffffffff&&BOOT_COMMIT_EDGE!=48'hffffffffffff&&BOOT_COMMIT_EDGE>BODY_EDGE+2;
  wire[3:0] pending,ready,shadow_date,active_date;wire[511:0] shadow;
  wire rn;(* keep_hierarchy="yes" *)ot_reset_sync #(.ASYNC_STAGES(2)) u_reset(.clk(ck),.async_rst_n(rst_n),.sync_rst_n(rn));
  reg valid;reg[7:0] f;reg body_seen;reg valid_n;reg[7:0] f_n;
  assign fault=f;
  // context_valid = valid&&f==0 had 35 loads (book slot compares + RX configured + port): it is now two kept
  // flop copies of the SAME function registered from the next state (valid_n, f_n) -> identical value on the
  // same edge, one copy for RX/port, one for the book.
  wire ctx_n=valid_n&&f_n==0;
  (* keep_hierarchy="yes" *)dsdv_hbc_ctx_copy #(.ID(0)) u_ctx_a(.ck(ck),.rst_n(rst_n),.d(ctx_n),.q(context_valid));
  (* keep_hierarchy="yes" *)dsdv_hbc_ctx_copy #(.ID(1)) u_ctx_b(.ck(ck),.rst_n(rst_n),.d(ctx_n),.q(context_valid_bk));
  wire hv=ring_i[0]&&ring_i[3:1]==6;
  wire[511:0] p=ring_i[532:21];
  wire command=hv&&p[31:0]==32'h31434248&&!(|pending); // Never inspect raw-body magic.
  wire addressed=p[47:40]==LOCAL_STAGE&&p[49:48]==LOCAL_RANK;
  wire claimed=command&&addressed || hv&&(|pending);
  assign local_ring={ring_i[1103:1],ring_i[0]&&!claimed};
  wire header_shape=p[35:32]==1&&p[177:114]==CLOCK_RESET_ID&&!(|p[511:290]);
  wire load_header=command&&addressed&&p[39:36]==0;
  wire commit_header=command&&addressed&&p[39:36]==1;
  reg ever_committed,slot_armed;
  reg[47:0] local_body_slot,local_commit_slot;
  wire[48:0] retire_wide={1'b0,active_fields[393:346]}+49'd3;
  wire retire_ready=ALLOW_RELOAD!=0&&valid&&!job_active&&!(|pending)&&!(|ready)&&
    !retire_wide[48]&&receiver_edge>=retire_wide[47:0];
  wire[48:0] next_body_wide={1'b0,boot_edge}+49'd4;
  wire[47:0] body_date=ALLOW_RELOAD!=0?local_body_slot:BODY_EDGE;
  wire[47:0] commit_date=ALLOW_RELOAD!=0?local_commit_slot:BOOT_COMMIT_EDGE;
  wire dated=ALLOW_RELOAD==0||slot_armed;
  wire load_format=header_shape&&p[65:50]==0&&p[81:66]==512&&p[289:242]==((ALLOW_RELOAD!=0&&ever_committed)?next_body_wide[47:0]:BODY_EDGE)&&!next_body_wide[48];
  wire load_slot=(!ever_committed&&boot_edge==BOOT_HEADER_EDGE)||retire_ready;
  wire load_permit=(!valid&&!ever_committed||retire_ready)&&!job_active&&f==0&&VALID_PROFILE;
  wire load_good=load_header&&load_format&&load_slot&&load_permit;
  wire[95:0] expected;wire[31:0] expected_crc=expected[31:0];wire[63:0] expected_programme=expected[95:32];
  wire[31:0] actual_crc;dsdv_hostb_crc512 u_crc(.d(shadow),.q(actual_crc));
  // Body schema from bootstrap_actual417_demand.json, all constant slices.
  wire[47:0] seed=shadow[211:164],first_header=shadow[259:212];
  wire[11:0] stride=shadow[271:260];wire[9:0] words=shadow[281:272];
  wire[7:0] target_gap=shadow[289:282],transit_gap=shadow[297:290];
  wire[47:0] ks_capture=shadow[345:298],prev_input=shadow[393:346];
  wire[47:0] status_sample=shadow[441:394],return_send=shadow[489:442];
  wire[7:0] data_stage=shadow[497:490];wire[1:0] data_rank=shadow[499:498];
  wire[48:0] commit_epoch_wide={1'b0,seed}+{1'b0,COMMIT_DELTA}+49'd1;
  wire[13:0] header_span={words-10'd1,4'b0};
  wire[48:0] end_header_wide={1'b0,first_header}+{35'd0,header_span}+49'd4;
  wire body_shape=!commit_epoch_wide[48]&&!end_header_wide[48]&&(VARIABLE_WORDS!=0 ? words!=0 : words==417)&&stride==16&&target_gap==4&&transit_gap==4&&data_stage<241&&data_rank<4&&
   shadow[511:500]==0&&shadow[163:100]==expected_programme&&
   first_header>seed+COMMIT_DELTA+4&&ks_capture>end_header_wide[47:0]&&
   prev_input>ks_capture&&status_sample<return_send&&return_send<prev_input;
  wire body_check=dated&&boot_edge==body_date+1&&body_seen;
  wire body_good=body_check&&actual_crc==expected_crc&&body_shape&&f==0;
  wire commit_permit=header_shape&&p[65:50]==1&&p[81:66]==0&&
   dated&&p[289:242]==commit_date&&boot_edge==commit_date&&p[113:82]==expected_crc&&
   p[241:178]==expected_programme&&(&ready)&&!valid&&!job_active&&f==0&&VALID_PROFILE;
  wire commit_good=commit_header&&commit_permit;
  always @* begin
   valid_n=valid;f_n=f;
   begin
    if(load_header&&!load_good)f_n[0]=1;
    if(VALID_PROFILE&&boot_edge==BOOT_HEADER_EDGE&&!load_good)f_n[0]=1;
    if(command&&addressed&&p[39:36]>1)f_n[1]=1;
    if(dated&&boot_edge==body_date&&(|pending)&&!hv)f_n[2]=1;
    if(hv&&(|pending)&&boot_edge!=body_date)f_n[2]=1;
    if(body_check&&!body_good)f_n[3]=1;
    if(commit_header&&!commit_good)f_n[4]=1;
    if(dated&&boot_edge==commit_date&&!commit_good)f_n[5]=1;
    if(command&&addressed&&((valid&&!load_good)||job_active))f_n[6]=1;
    if(job_active&&((|pending)||(|ready)))f_n[6]=1;
    if(command&&addressed&&!VALID_PROFILE)f_n[7]=1;
    if(ALLOW_RELOAD!=0&&load_good)valid_n=0;
    if(commit_good)valid_n=1;
   end
  end
  always @(posedge ck or negedge rn)begin
   if(!rn)begin valid<=0;f<=0;body_seen<=0;ever_committed<=0;slot_armed<=0;end
   else begin
    valid<=valid_n;f<=f_n;
    if(load_good)begin
     body_seen<=0;slot_armed<=1;
     local_body_slot<=p[289:242];local_commit_slot<=p[289:242]+COMMIT_DELTA;
    end else if(dated&&boot_edge==body_date&&(|pending))body_seen<=hv;
    if(commit_good)ever_committed<=1;
   end
  end
  genvar k;
  for(k=0;k<4;k=k+1)begin:g_clock
   wire carry_boot,carry_epoch;
   if(k==0)begin:g_first assign carry_boot=1'b1;assign carry_epoch=1'b1;end
   else begin:g_carry assign carry_boot=&boot_edge[k*12-1:0];assign carry_epoch=&receiver_edge[k*12-1:0];end
   (* keep_hierarchy="yes" *)dsdv_hbc_boot12 #(.ID(k)) u_boot(.ck(ck),.rst_n(rst_n),.carry(carry_boot),.q(boot_edge[12*k+:12]));
   wire[47:0] epoch_at_next=seed+COMMIT_DELTA+1;
   (* keep_hierarchy="yes" *)dsdv_hbc_epoch12 #(.ID(k)) u_epoch(.ck(ck),.commit_request(commit_header),.commit_permit(commit_permit),.valid(valid),.fault_clear(f==0),.carry(carry_epoch),
    .d(epoch_at_next[12*k+:12]),.q(receiver_edge[12*k+:12]));
   // receiver_edge bits had 33-38 loads: the book reads its own kept same-edge copy of the epoch counter
   // (same load/run enables, same commit date, carry from its own bits).
   wire carry_epoch_bk;
   if(k==0)begin:g_first_bk assign carry_epoch_bk=1'b1;end
   else begin:g_carry_bk assign carry_epoch_bk=&receiver_edge_bk[k*12-1:0];end
   (* keep_hierarchy="yes" *)dsdv_hbc_epoch12 #(.ID(k+4)) u_epoch_bk(.ck(ck),.commit_request(commit_header),.commit_permit(commit_permit),.valid(valid),.fault_clear(f==0),.carry(carry_epoch_bk),
    .d(epoch_at_next[12*k+:12]),.q(receiver_edge_bk[12*k+:12]));
   (* keep_hierarchy="yes" *)dsdv_hbc_owner #(.ID(k),.BODY_EDGE(BODY_EDGE),.COMMIT_EDGE(BOOT_COMMIT_EDGE),.DYNAMIC(ALLOW_RELOAD)) u_owner(
    .ck(ck),.rst_n(rst_n),.load_header(load_good),.body_good(body_good),.body_due(dated&&boot_edge==body_date),.commit_due(dated&&boot_edge==commit_date),.edge_now(boot_edge),.pending(pending[k]),.ready(ready[k]));
  end
  for(k=0;k<4;k=k+1)begin:g_dates
   (* keep_hierarchy="yes" *)dsdv_hbc_fixed_date #(.ID(k),.DATE(BODY_EDGE),.DYNAMIC(ALLOW_RELOAD)) u_shadow_date(.edge_now(boot_edge),.local_date(local_body_slot),.match(shadow_date[k]));
   (* keep_hierarchy="yes" *)dsdv_hbc_fixed_date #(.ID(k+4),.DATE(BOOT_COMMIT_EDGE),.DYNAMIC(ALLOW_RELOAD)) u_active_date(.edge_now(boot_edge),.local_date(local_commit_slot),.match(active_date[k]));
  end
  for(k=0;k<8;k=k+1)begin:g_header
   wire[95:0] d={p[241:178],p[113:82]};
   wire header_en;
   (* keep_hierarchy="yes" *)dsdv_hbc_header_enable #(.ID(k)) u_en(.request(load_header),.format_ok(load_format),.slot(load_slot),.permit(load_permit),.en(header_en));
   (* keep_hierarchy="yes" *)dsdv_hostb_hold_bits #(.ID(k),.W(12)) u_bank(.ck(ck),.en(header_en),.d(d[12*k+:12]),.q(expected[12*k+:12]));
  end
  for(k=0;k<43;k=k+1)begin:g_field
   localparam integer LO=12*k,W=(512-LO<12)?512-LO:12;
   (* keep_hierarchy="yes" *)dsdv_hbc_field #(.ID(k),.W(W)) u_shadow(
    .ck(ck),.owner(pending[k/11]),.date_match(shadow_date[k/11]),.d(p[LO+:W]),.q(shadow[LO+:W]));
   (* keep_hierarchy="yes" *)dsdv_hbc_field #(.ID(k+43),.W(W)) u_active(
    .ck(ck),.owner(ready[k/11]),.date_match(active_date[k/11]),.d(shadow[LO+:W]),.q(active_fields[LO+:W]));
  end
 end endgenerate
endmodule
module dsdv_hbc_ctx_copy #(parameter integer ID=0)(input wire ck,rst_n,d,output reg q);
 wire rn;(* keep_hierarchy="yes" *)ot_reset_sync #(.ASYNC_STAGES(2)) u_reset(.clk(ck),.async_rst_n(rst_n),.sync_rst_n(rn));
 always @(posedge ck or negedge rn)if(!rn)q<=0;else q<=d;
endmodule
module dsdv_hbc_boot12 #(parameter integer ID=0)(input wire ck,rst_n,carry,output reg[11:0]q);
 wire rn;(* keep_hierarchy="yes" *)ot_reset_sync #(.ASYNC_STAGES(2)) u_reset(.clk(ck),.async_rst_n(rst_n),.sync_rst_n(rn));
 always @(posedge ck or negedge rn)if(!rn)q<=0;else q<=q+carry;
endmodule
module dsdv_hbc_epoch12 #(parameter integer ID=0)(input wire ck,commit_request,commit_permit,valid,fault_clear,carry,input wire[11:0]d,output reg[11:0]q);
 wire load,run;
 (* keep_hierarchy="yes" *)dsdv_hbc_epoch_enable #(.ID(ID)) u_en(.request(commit_request),.permit(commit_permit),.valid(valid),.fault_clear(fault_clear),.load(load),.run(run));
 always @(posedge ck)if(load)q<=d;else if(run)q<=q+carry;
endmodule
module dsdv_hbc_epoch_enable #(parameter integer ID=0)(input wire request,permit,valid,fault_clear,output wire load,run);
 assign load=request&&permit;assign run=valid&&fault_clear;
endmodule
module dsdv_hbc_header_enable #(parameter integer ID=0)(input wire request,format_ok,slot,permit,output wire en);
 assign en=request&&format_ok&&slot&&permit;
endmodule
module dsdv_hbc_owner #(parameter integer ID=0,parameter[47:0]BODY_EDGE=0,COMMIT_EDGE=0,parameter integer DYNAMIC=0)(
 input wire ck,rst_n,load_header,body_good,body_due,commit_due,input wire[47:0]edge_now,output reg pending,ready);
 wire rn;(* keep_hierarchy="yes" *)ot_reset_sync #(.ASYNC_STAGES(2)) u_reset(.clk(ck),.async_rst_n(rst_n),.sync_rst_n(rn));
 always @(posedge ck or negedge rn)if(!rn)begin pending<=0;ready<=0;end
 else begin
  if(load_header)pending<=1;else if(DYNAMIC!=0?body_due:edge_now>=BODY_EDGE)pending<=0;
  if(load_header)ready<=0;else if(body_good)ready<=1;else if(DYNAMIC!=0?commit_due:edge_now>=COMMIT_EDGE)ready<=0;
 end
endmodule
module dsdv_hbc_field #(parameter integer ID=0,W=12)(
 input wire ck,owner,date_match,input wire[W-1:0]d,output wire[W-1:0]q);
 wire en;
 (* keep_hierarchy="yes" *)dsdv_hbc_fixed_enable #(.ID(ID)) u_enable(.owner(owner),.date_match(date_match),.en(en));
 (* keep_hierarchy="yes" *)dsdv_hostb_hold_bits #(.ID(ID),.W(W)) u_bits(.ck(ck),.en(en),.d(d),.q(q));
endmodule
module dsdv_hbc_fixed_enable #(parameter integer ID=0)(input wire owner,date_match,output wire en);
 assign en=owner&&date_match;
endmodule
module dsdv_hbc_fixed_date #(parameter integer ID=0,parameter[47:0]DATE=0,parameter integer DYNAMIC=0)(input wire[47:0]edge_now,local_date,output wire match);
 assign match=edge_now==(DYNAMIC!=0?local_date:DATE);
endmodule
`default_nettype wire
