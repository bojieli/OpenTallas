`timescale 1ns/1ps
// Complete finite emitted L19 plan, not a fragment END completion shortcut.
// Four source-owned command lanes; each rank follows its literal program book.
module ot_dsrom_wfc_whole_stage #(
 parameter integer ENABLE=0, BOOK_WORDS=167, GROUPS=48,
 parameter string BOOK0="",BOOK1="",BOOK2="",BOOK3=""
)(
 input wire clk,rst_n,
 input wire request_v, output wire request_ready,
 input wire [46:0] request_identity,input wire [20:0] request_token,input wire [13:0] request_entry,
 input wire [15:0] configured_epoch,
 // Native command takes, before the same source edge; these are not host pulses.
 input wire [3:0] command_v,output wire [3:0] command_ready,
 input wire [187:0] command_identity,input wire [83:0] command_token,input wire [27:0] command_home,
 input wire [55:0] command_entry,command_pc,input wire [15:0] command_unit,
 // Real C8 retirement + same-owner restore/publication/drain receipts.
 input wire [3:0] retire_v,input wire [187:0] retire_identity,
 input wire [27:0] retire_home,input wire [55:0] retire_entry,
 input wire [23:0] retire_visibility, // restored + continuation/KV/index/remote/all-copy
 input wire [3:0] retire_quiet,retire_capture_drained,retire_fault,
 // Real final source fence, independently of the last native END.
 input wire [3:0] fence_v,input wire [187:0] fence_identity,input wire [19:0] fence_visibility,
 // Actual native terminal result after END. L19 is typed STAGE_HANDOFF.
 input wire result_v,input wire [46:0] result_identity,input wire [20:0] result_token,
 input wire [31:0] result_value,
 input wire whole_stage_accepted,
 output wire whole_stage_v,output wire [46:0] whole_stage_identity,
 output wire [20:0] whole_stage_next_token,output wire [31:0] whole_stage_value,
 output wire token_result_valid,stage_handoff,pending,fault
);
 initial if(BOOK_WORDS!=167||GROUPS!=48)$fatal(1,"literal emitted L19 book/model changed");
 generate if(ENABLE)begin:g_live
  reg active=0,active_check=1,poison=0,armed=0,have_result=0;
  reg [46:0] identity=0,identity_check={47{1'b1}};
  reg [20:0] token=0,token_check={21{1'b1}},request_token_q=0,request_token_check={21{1'b1}};reg [31:0] value=0,value_check={32{1'b1}};reg have_result_check=1;
  reg [11:0] ptr[0:3],ptr_check[0:3];
  reg [3:0] await_retire=0,finished=0,fenced=0,fenced_check=4'hf;
  reg [6:0] held_home[0:3];reg [13:0] held_entry[0:3];
  reg [7:0] retired_groups[0:3],retired_check[0:3];
  reg [3:0] rank_fault=0;
  wire state_bad=active!=~active_check||identity!=~identity_check||token!=~token_check||value!=~value_check||request_token_q!=~request_token_check||have_result!=~have_result_check;
  assign fault=poison||state_bad||(|rank_fault);assign pending=active;
  assign request_ready=rst_n&&!fault&&!active;
  wire take=request_v&&request_ready;
  wire all_finished=&finished;
  assign whole_stage_v=rst_n&&active&&!fault&&all_finished&&(&fenced)&&have_result;
  assign whole_stage_identity=identity;
  assign whole_stage_next_token=token;assign whole_stage_value=value;
  assign stage_handoff=whole_stage_v;assign token_result_valid=1'b0;
  for(genvar rank=0;rank<4;rank=rank+1)begin:g_rank
   wire [71:0] q;
   wire ptr_bad=ptr[rank]!=~ptr_check[rank]||retired_groups[rank]!=~retired_check[rank]||fenced[rank]!=~fenced_check[rank];
   assign command_ready[rank]=rst_n&&active&&armed&&!fault&&!ptr_bad&&!await_retire[rank]&&!finished[rank];
   wire cmd_take=command_v[rank]&&command_ready[rank];
   wire [11:0] next_address=take?12'd0:ptr[rank]+12'd1;
   (* keep=1,dont_touch=1 *) ot_rom_4096x72_m8
`ifndef SYNTHESIS
    #(.VIAMAP(rank==0?BOOK0:rank==1?BOOK1:rank==2?BOOK2:BOOK3))
`endif
    u_book(.clk(clk),.ce_in(take||(cmd_take&&!q[40])),.addr_in(next_address),.rd_out(q));
   initial begin ptr[rank]=0;ptr_check[rank]=12'hfff;retired_groups[rank]=0;retired_check[rank]=8'hff;end
   always @(posedge clk)begin
    if(rst_n)begin
     if(ptr_bad)rank_fault[rank]<=1;
     if(take)begin await_retire[rank]<=0;finished[rank]<=0;fenced[rank]<=0;fenced_check[rank]<=1;ptr[rank]<=0;ptr_check[rank]<=12'hfff;retired_groups[rank]<=0;retired_check[rank]<=8'hff;end
     if(command_v[rank])begin
      if(!command_ready[rank]||command_identity[47*rank+:47]!=identity||command_token[21*rank+:21]!=request_token_q||command_home[7*rank+:7]!=q[6:0]||command_entry[14*rank+:14]!=q[20:7]||command_pc[14*rank+:14]!=q[34:21]||command_unit[4*rank+:4]!=q[38:35]||ptr[rank]>=BOOK_WORDS)rank_fault[rank]<=1;
      else begin
       ptr[rank]<=ptr[rank]+1;ptr_check[rank]<=~(ptr[rank]+12'd1);
       if(q[39])begin await_retire[rank]<=1;held_home[rank]<=q[6:0];held_entry[rank]<=q[20:7];end
      end
     end
     if(retire_v[rank])begin
      if(!active||!await_retire[rank]||retire_identity[47*rank+:47]!=identity||retire_home[7*rank+:7]!=held_home[rank]||retire_entry[14*rank+:14]!=held_entry[rank]||retire_visibility[6*rank+:6]!=6'b111111||!retire_quiet[rank]||!retire_capture_drained[rank]||retire_fault[rank])rank_fault[rank]<=1;
      else begin
       await_retire[rank]<=0;retired_groups[rank]<=retired_groups[rank]+1;retired_check[rank]<=~(retired_groups[rank]+8'd1);
       if(ptr[rank]==BOOK_WORDS&&retired_groups[rank]==GROUPS-1)finished[rank]<=1;
      end
     end
     if(fence_v[rank])begin
      if(!active||!finished[rank]||fence_identity[47*rank+:47]!=identity||fence_visibility[5*rank+:5]!=5'b11111||fenced[rank])rank_fault[rank]<=1;
      else begin fenced[rank]<=1;fenced_check[rank]<=0;end
     end
     if(whole_stage_accepted&&whole_stage_v)begin await_retire[rank]<=0;finished[rank]<=0;fenced[rank]<=0;fenced_check[rank]<=1;end
    end
   end
  end
  always @(posedge clk)begin
   if(!rst_n)begin if(active)poison<=1;end
   else begin
    if(state_bad)poison<=1;
    if(take)begin
     if(request_identity[46:31]!=configured_epoch||request_entry!=14'd12)poison<=1;
     else begin active<=1;active_check<=0;identity<=request_identity;identity_check<=~request_identity;request_token_q<=request_token;request_token_check<=~request_token;armed<=0;have_result<=0;have_result_check<=1;end
    end else if(active)armed<=1;
    if(result_v)begin
     if(!active||!all_finished||result_identity!=identity||have_result)poison<=1;
     else begin token<=result_token;token_check<=~result_token;value<=result_value;value_check<=~result_value;have_result<=1;have_result_check<=0;end
    end
    if(whole_stage_accepted)begin
     if(!whole_stage_v)poison<=1;
     else begin active<=0;active_check<=1;armed<=0;have_result<=0;have_result_check<=1;end
    end
   end
  end
 end else begin:g_off
  assign request_ready=0;assign command_ready=0;assign whole_stage_v=0;assign whole_stage_identity=0;
  assign whole_stage_next_token=0;assign whole_stage_value=0;assign token_result_valid=0;assign stage_handoff=0;assign pending=0;assign fault=0;
 end endgenerate
endmodule
