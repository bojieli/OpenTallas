// Always-on local half of a coordinated cold-link session. No operation-arm input.
module ot_hbm_link_session_agent #(parameter integer ENABLE=0)(
 input wire clk_control,clk_stream,clk_link,por,
 input wire command_valid,output wire command_ready,input wire[71:0] command_word,
 output wire ack_valid,input wire ack_ready,output wire[71:0] ack_word,
 input wire quiet_core,quiet_phy,reserved_debt_zero,data_flight_empty,credit_control_empty,
 input wire phy_quiesced,phy_reset_ack,initial_credit_ack_seen,
 output wire phy_quiesce_req,phy_reset_req,admit_enable,launch_enable,
 output wire rst_n,prst_n,stream_cold_start,link_cold_start,
 output wire[23:0] stream_epoch,link_epoch,
 output wire fault
);
 import ot_hbm_credit_secded_pkg::*;
 reg[71:0] state_q,message_q;reg[1:0] healthy_q;
 wire[65:0] s=decode64(state_q),m=decode64(message_q),cmd=decode64(command_word);
 wire[23:0] epoch=s[63:40],seq=s[39:16];wire[7:0] phase=s[15:8];
 wire pending=s[0],busy=s[1],seen_command=s[2],run_release=s[3];
 wire clean=s[65:64]==0&&m[65:64]==0;
 wire start_seen_stream,start_seen_link,start_fault_stream,start_fault_link;
 assign fault=healthy_q!=2'b01;
 wire live=ENABLE!=0&&!fault&&clean;
 assign command_ready=live&&!pending&&!busy;
 assign ack_valid=live&&busy;assign ack_word=message_q;
 wire reset_hold=ENABLE==0||fault||s[65]||phase==0||phase==2||(phase==1&&epoch==0);
 // Do not drive reset from correctable state errors: scrub stalls permissions.
 ot_hbm_collective_reset_entry #(.ENABLE(1)) resets(clk_stream,clk_link,por||reset_hold,por||reset_hold,rst_n,prst_n);
 wire[71:0] epoch_word=encode64({40'b0,epoch});
 wire start_request=live&&(phase==4||phase==5);
 ot_hbm_link_start_adapter sa(clk_stream,rst_n,start_request,epoch_word,stream_cold_start,stream_epoch,start_seen_stream,start_fault_stream);
 ot_hbm_link_start_adapter la(clk_link,prst_n,start_request,epoch_word,link_cold_start,link_epoch,start_seen_link,start_fault_link);
 // Dual-rail synchronizer observations. Incoherent or faulty rails cannot satisfy a fence.
 wire[13:0] observation={start_fault_link,start_fault_stream,start_seen_link,start_seen_stream,prst_n,rst_n,
  initial_credit_ack_seen,phy_reset_ack,phy_quiesced,credit_control_empty,data_flight_empty,reserved_debt_zero,quiet_phy,quiet_core};
 (* ASYNC_REG="TRUE" *) reg[27:0] obs1,obs2;
 wire[13:0] yes,no;genvar x;
 generate for(x=0;x<14;x=x+1)begin:g_obs
  assign yes[x]=obs2[2*x+:2]==2'b10;assign no[x]=obs2[2*x+:2]==2'b01;
  always @(posedge clk_control or posedge por)begin
   if(por)begin obs1[2*x+:2]<=1;obs2[2*x+:2]<=1;end
   else begin obs1[2*x+:2]<={observation[x],!observation[x]};obs2[2*x+:2]<=obs1[2*x+:2];end
  end
 end endgenerate
 wire drained=&yes[4:0];
 assign phy_quiesce_req=ENABLE!=0&&(fault||phase!=5||!run_release);
 assign phy_reset_req=ENABLE!=0&&(fault||phase==2);
 assign admit_enable=live&&phase==5&&!pending;
 assign launch_enable=admit_enable||(live&&phase==1&&pending&&epoch!=0);
 reg[63:0] n,mn;reg bad,complete;reg[7:0] expected_phase;
 always @*begin
  n=s[63:0];mn=m[63:0];bad=0;complete=0;
  expected_phase=phase==5?8'd1:phase+8'd1;
  if(ack_valid&&ack_ready)n[1]=0;
  if(command_valid&&command_ready)begin
   if(cmd[65]||cmd[7:0]!=8'hc3||cmd[63:56]!=expected_phase||
    (!seen_command&&cmd[31:8]!=0)||(seen_command&&(seq==24'hffffff||cmd[31:8]!=seq+24'd1))||
    (expected_phase==3?(epoch==24'hffffff||cmd[55:32]!=epoch+24'd1):(cmd[55:32]!=epoch)))bad=1;
   else begin n={cmd[55:32],cmd[31:8],cmd[63:56],8'h05};end
  end
  if(pending)case(phase)
   1:complete=drained&&yes[5]&&no[6]; // quiesced; no stale reset ACK
   2:complete=drained&&yes[5]&&yes[6]&&no[8]&&no[9];
   3:complete=no[6]&&no[7]&&yes[5]&&yes[8]&&yes[9]&&no[10]&&no[11];
   4:complete=yes[10]&&yes[11]&&yes[5];
   5:begin
    if(yes[7])n[3]=1;
    complete=run_release&&no[5]&&yes[7];
   end
   default:bad=1;
  endcase
  if(complete)begin n[0]=0;n[1]=1;mn={phase|8'h80,epoch,seq,8'hac};end
  if(s[7:4]!=0||phase>5||yes[12]||yes[13])bad=1;
 end
 always @(posedge clk_control or posedge por)begin
  if(por)begin state_q<=encode64(0);message_q<=encode64(0);healthy_q<=1;end
  else if(ENABLE!=0&&!fault)begin
   if(s[65]||m[65])healthy_q<=2;
   else if(!clean)begin state_q<=encode64(s[63:0]);message_q<=encode64(m[63:0]);end
   else if(bad)healthy_q<=2;
   else begin state_q<=encode64(n);message_q<=encode64(mn);end
  end
 end
endmodule
