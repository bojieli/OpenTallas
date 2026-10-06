`timescale 1ns/1ps
// One finite owned native-edge bundle. No new VM/codec/retirement authority.
// Router clocks run continuously; controller CE commits only protected events.
module ot_dsrom_wfc_vm_caller_adapter #(parameter ENABLE=0)(
 input wire fast_clk,cold_n,fast_rst_n,slow_rst_n,
 input wire xa_we,xa_re,input wire[14:0]xa_waddr,xa_raddr,
 input wire[511:0]xa_wdata,input wire[46:0]xa_owner,
 input wire xa_read_capture,xa_owner_conflict,input wire[46:0]xa_read_owner,
 output wire advance,memory_step,read_step,write_step,write_quiet,
 input wire xb_v,output wire xb_ready,input wire[46:0]xb_owner,
 input wire[3:0]xb_we4,input wire[59:0]xb_waddr4,input wire[2047:0]xb_wdata4,
 input wire xb_re,input wire[14:0]xb_raddr,
 output wire xb_reply_v,output wire[46:0]xb_reply_owner,
 output wire[511:0]xb_read_data,output wire[3:0]xb_row_visible,
 input wire xb_consume_v,input wire[46:0]xb_consume_owner,
 output wire xb_port_retired,
 output wire request_v,input wire request_ready,output wire[46:0]request_owner,
 output wire[1:0]read_enable,output wire[29:0]read_addr,
 output wire[4:0]write_enable,output wire[74:0]write_addr,
 output wire[2559:0]write_data,output wire[79:0]write_mask,
 input wire reply_v,input wire[46:0]reply_owner,input wire[1023:0]read_data,
 input wire[4:0]row_visible,input wire port_retired,pending,provider_fault,initializing,
 output wire consume_v,output wire[46:0]consume_owner,output wire allcopies_fenced,
 output wire fault,output wire[3:0]phase
);
 generate if(ENABLE)begin:g_live
  localparam IDLE=4'd0,WAIT_REPLY=4'd1,ISSUE=4'd2,CAPTURE=4'd3,DRAIN=4'd4,WAIT_RETIRE=4'd5,WRITE_REQUEST=4'd6;
  localparam PAIRED=8,RA=7,WA=6,B=5,ADONE=4,BDONE=3,SEEN=2,SENT=1,POISON=0;
  reg[3:0]state,state_check;reg[46:0]owner,owner_check,paired_owner,paired_owner_check;
  reg[8:0]flags,flags_check;reg[4:0]expected_we,expected_we_check;
  wire bad=state!=~state_check||owner!=~owner_check||paired_owner!=~paired_owner_check||flags!=~flags_check||expected_we!=~expected_we_check;
  assign phase=state;assign fault=bad||flags[POISON]||provider_fault;
  wire xa_intent=xa_we||xa_re;
  // An unaccepted different owner stays held outside; never relabel it as XA.
  wire split=state==IDLE&&xa_we&&xa_re&&xa_owner_conflict;
  wire second_write=state==WRITE_REQUEST;
  wire include_b=xb_v&&!split&&!second_write&&(!xa_intent||xb_owner==xa_owner);
  wire event_v=xa_intent||include_b;
  assign request_v=cold_n&&fast_rst_n&&slow_rst_n&&!fault&&
    ((state==IDLE&&event_v)||(second_write&&xa_we&&xa_owner==paired_owner));
  assign request_owner=second_write?paired_owner:split?xa_read_owner:xa_intent?xa_owner:xb_owner;
  assign read_enable=second_write?2'b00:{include_b&&xb_re,xa_re};
  assign read_addr={xb_raddr,xa_raddr};
  assign write_enable=second_write?5'b00001:{xb_we4&{4{include_b}},xa_we&&!split};
  assign write_addr={xb_waddr4,xa_waddr};assign write_data={xb_wdata4,xa_wdata};
  assign write_mask={{64{include_b}},16'hffff};
  assign xb_ready=request_v&&request_ready&&include_b;
  assign memory_step=cold_n&&fast_rst_n&&slow_rst_n&&!fault&&(state==IDLE||state==ISSUE||state==WRITE_REQUEST);
  assign read_step=state==WRITE_REQUEST?1'b0:state==ISSUE?flags[RA]:1'b1;
  assign write_step=state==ISSUE?flags[WA]:1'b1;
  assign advance=cold_n&&fast_rst_n&&slow_rst_n&&!fault&&!initializing&&
    ((state==IDLE&&!event_v&&!pending)||(state==ISSUE&&(flags[RA]||flags[WA]))||(state==CAPTURE&&flags[RA]));
  // Quiet is a real protected visible fact; transport debt still retires later.
  assign write_quiet=!pending||(reply_v&&reply_owner==owner&&row_visible==expected_we);
  assign xb_reply_v=reply_v&&!fault&&state!=IDLE&&flags[B]&&!flags[BDONE];
  assign xb_reply_owner=owner;assign xb_read_data=read_data[1023:512];
  assign xb_row_visible=xb_reply_v?row_visible[4:1]:4'd0;
  assign consume_owner=owner;
  assign allcopies_fenced=flags[ADONE]&&flags[BDONE]&&reply_v&&reply_owner==owner&&row_visible==expected_we;
  assign consume_v=!fault&&state==DRAIN&&allcopies_fenced&&!flags[SENT];
  assign xb_port_retired=port_retired&&!fault&&state==WAIT_RETIRE&&flags[B];
  wire invalid_consume=xb_consume_v&&(!xb_reply_v||xb_consume_owner!=owner);
  wire invalid_retired=port_retired&&state!=WAIT_RETIRE;
  wire invalid_pair_write=second_write&&(!xa_we||xa_owner!=paired_owner);
  task automatic poison;begin flags[POISON]<=1;flags_check[POISON]<=0;end endtask
  task automatic flag_set(input integer i,input value);begin flags[i]<=value;flags_check[i]<=!value;end endtask
  task automatic go(input[3:0]s);begin state<=s;state_check<=~s;end endtask
  always @(posedge fast_clk)begin
   if(!cold_n)begin state<=IDLE;state_check<=~IDLE;owner<=0;owner_check<=~47'd0;paired_owner<=0;paired_owner_check<=~47'd0;flags<=0;flags_check<=9'h1ff;expected_we<=0;expected_we_check<=5'h1f;end
   else if(!fast_rst_n||!slow_rst_n)begin if(state!=IDLE||pending)poison();end
   else if(bad||provider_fault||invalid_pair_write||invalid_consume||invalid_retired)poison();
   else if(!fault)begin
    if(xb_consume_v)begin
     if(!xb_reply_v||xb_consume_owner!=owner)poison();else flag_set(BDONE,1);
    end
    if(port_retired&&state!=WAIT_RETIRE)poison();
    case(state)
     IDLE:if(request_v&&request_ready)begin
      owner<=request_owner;owner_check<=~request_owner;
      expected_we<=write_enable;expected_we_check<=~write_enable;
      paired_owner<=xa_owner;paired_owner_check<=~xa_owner;
      flags<={split,xa_re,xa_we&&!split,include_b,!(xa_we||xa_re),!include_b,3'b000};
      flags_check<=~{split,xa_re,xa_we&&!split,include_b,!(xa_we||xa_re),!include_b,3'b000};
      go(WAIT_REPLY);
     end
     WAIT_REPLY:if(reply_v)begin
      if(reply_owner!=owner||row_visible!=expected_we)poison();
      else begin flag_set(SEEN,1);go(ISSUE);end
     end
     ISSUE:begin
      if(flags[RA])go(CAPTURE);
      else begin flag_set(ADONE,1);go(DRAIN);end
     end
     CAPTURE:begin
      if(!xa_read_capture)poison();
      else begin flag_set(ADONE,1);go(DRAIN);end
     end
     DRAIN:if(consume_v)begin flag_set(SENT,1);go(WAIT_RETIRE);end
     WAIT_RETIRE:if(port_retired)begin if(flags[PAIRED])go(WRITE_REQUEST);else go(IDLE);end
     WRITE_REQUEST:if(request_v&&request_ready)begin
      owner<=paired_owner;owner_check<=~paired_owner;
      expected_we<=5'b00001;expected_we_check<=~5'b00001;
      flags<=9'b001001000;flags_check<=~9'b001001000;
      go(WAIT_REPLY);
     end
     default:poison();
    endcase
   end
  end
 end else begin:g_off
  assign {advance,memory_step,read_step,write_step,write_quiet,xb_ready,xb_reply_v,xb_reply_owner,xb_read_data,xb_row_visible,
   xb_port_retired,request_v,request_owner,read_enable,read_addr,write_enable,write_addr,write_data,write_mask,
   consume_v,consume_owner,allcopies_fenced,fault,phase}=0;
 end endgenerate
endmodule
