`timescale 1ns/1ps
// Canonical opaque548 kinds12/13/14. TX and RX each add exactly one register
// edge. Slots come from the assigned calendar; missing source/arrival faults,
// never waits. Static SRAM/CRC link TX3/RX1 and physical relay latency are
// separate resources. RuntimeHOSTepoch and installed-image epoch are distinct.
module qkd_host_native_context_tx(
 input wire ck,rst_n,send_slot,
 input wire request_v,input wire[58:0]request_tag,input wire[1:0]request_gen,
 input wire[17:0]request_token,request_position,
 input wire token_epoch_valid,input wire[15:0]token_epoch,
 input wire program_ready,installed_fusedcap,input wire[15:0]program_epoch,input wire[63:0]program_digest,
 output reg tx_v,tx_observed_v,output reg[547:0]tx_record,output reg fault
);
 reg held,epoch_valid_q;reg[15:0]epoch_q;reg[58:0]tag;reg[1:0]gen;
 wire source_ok=!fault&&held&&epoch_valid_q&&tag[58:43]==epoch_q&&program_ready;
 wire[511:0]data={370'd0,program_digest,program_epoch,installed_fusedcap,gen,tag};
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin held<=0;epoch_valid_q<=0;epoch_q<=0;tag<=0;gen<=0;tx_v<=0;tx_observed_v<=0;tx_record<=0;fault<=0;end
  else begin
   tx_v<=send_slot;tx_observed_v<=send_slot&&source_ok;
   if(token_epoch_valid)begin epoch_valid_q<=1;epoch_q<=token_epoch;end
   if(request_v)begin
    if(!epoch_valid_q||request_tag[58:43]!=epoch_q||request_tag[42:37]!=0||request_tag[5:0]!=0||request_token>=151936||request_position>=8192||request_tag[36:19]!=request_token||request_tag[18:6]!=request_position[12:0])fault<=1;
    held<=1;tag<=request_tag;gen<=request_gen;
   end
   if(send_slot)begin
    tx_record<={5'd0,4'd12,6'd63,tag[58:43],5'd0,data};
    if(source_ok!==1'b1)fault<=1;
   end
  end
 end
endmodule

module qfd_host_native_context_rx(
 input wire ck,rst_n,receive_slot,rx_v,input wire[547:0]rx_record,
 input wire program_begin_v,program_ready,installed_fusedcap,
 input wire[15:0]program_epoch,input wire[63:0]program_digest,
 input wire head_context_v,input wire[5:0]head_stage,
 input wire[17:0]head_token,head_position,input wire native_active,
 output reg host_epoch_valid,output wire[15:0]host_epoch,
 output reg[58:0]host_tag,output reg[1:0]host_gen,
 output reg host_fusedcap,output reg[15:0]host_image_epoch,output reg[63:0]host_image_digest,
 output reg fault
);
 wire[58:0]tag=rx_record[58:0];
 wire structure_ok=rx_record[547:543]==0&&rx_record[542:539]==12&&rx_record[538:533]==63&&rx_record[516:512]==0&&rx_record[511:142]==0&&tag[42:37]==0&&tag[5:0]==0&&tag[36:19]<151936&&rx_record[532:517]==tag[58:43];
 wire image_ok=program_ready&&rx_record[77:62]==program_epoch&&rx_record[141:78]==program_digest&&rx_record[61]==installed_fusedcap;
 assign host_epoch=host_tag[58:43];
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin host_epoch_valid<=0;host_tag<=0;host_gen<=0;host_fusedcap<=0;host_image_epoch<=0;host_image_digest<=0;fault<=0;end
  else begin
   if(program_begin_v)begin host_epoch_valid<=0;if(native_active)fault<=1;end
   if(rx_v!==receive_slot)begin fault<=1;host_epoch_valid<=0;end
   if(receive_slot)begin
    if(rx_v!==1'b1||structure_ok!==1'b1||image_ok!==1'b1||native_active!==1'b0||program_begin_v!==1'b0||fault)begin fault<=1;host_epoch_valid<=0;end
    else begin host_epoch_valid<=1;host_tag<=tag;host_gen<=rx_record[60:59];host_fusedcap<=rx_record[61];host_image_epoch<=rx_record[77:62];host_image_digest<=rx_record[141:78];end
   end
   if(host_epoch_valid&&(!program_ready||program_epoch!=host_image_epoch||program_digest!=host_image_digest||installed_fusedcap!=host_fusedcap))begin host_epoch_valid<=0;if(native_active)fault<=1;end
   if(head_context_v&&head_stage>=1&&head_stage<=36)
    if(!host_epoch_valid||!host_fusedcap||head_token!=host_tag[36:19]||head_position>=8192||head_position[12:0]!=host_tag[18:6])fault<=1;
  end
 end
endmodule

module qkd_program_auth_tx(
 input wire ck,rst_n,send_slot,input wire[1:0]send_type,
 input wire begin_v,input wire[15:0]begin_epoch,input wire[10:0]expected_pw,input wire[3:0]expected_dw,
 input wire auth_v,input wire[15:0]auth_epoch,input wire[63:0]auth_digest,
 output reg tx_v,tx_observed_v,output reg[547:0]tx_record,output reg fault
);
 reg bp,ap,begin_sent;reg[15:0]be,ae;reg[10:0]np;reg[3:0]nd;reg[63:0]digest;
 wire choose_begin=send_type==1;
 wire source_ok=!fault&&(choose_begin?bp:(send_type==2&&ap&&begin_sent&&ae==be));
 wire[511:0]data=choose_begin?{495'd0,nd,np,2'd1}:{446'd0,digest,2'd2};
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin bp<=0;ap<=0;begin_sent<=0;be<=0;ae<=0;np<=0;nd<=0;digest<=0;tx_v<=0;tx_observed_v<=0;tx_record<=0;fault<=0;end
  else begin
   tx_v<=send_slot;tx_observed_v<=send_slot&&source_ok;
   if(begin_v)begin
    if(bp||ap||expected_pw!=1024||expected_dw!=8)fault<=1;
    bp<=1;begin_sent<=0;be<=begin_epoch;np<=expected_pw;nd<=expected_dw;
   end
   if(auth_v)begin if(ap)fault<=1;ap<=1;ae<=auth_epoch;digest<=auth_digest;end
   if(send_slot)begin
    tx_record<={5'd0,4'd13,6'd63,(choose_begin?be:ae),5'd0,data};
    if(source_ok!==1'b1)fault<=1;
    if(choose_begin)begin bp<=0;begin_sent<=1;end else ap<=0;
   end
  end
 end
endmodule

module qfd_program_auth_rx(
 input wire ck,rst_n,receive_slot,rx_v,input wire[547:0]rx_record,
 output reg begin_v,output reg[15:0]begin_epoch,output reg[10:0]expected_pw,output reg[3:0]expected_dw,
 output reg auth_v,output reg[15:0]auth_epoch,output reg[63:0]auth_digest,output reg fault
);
 wire common_ok=rx_record[547:543]==0&&rx_record[542:539]==13&&rx_record[538:533]==63&&rx_record[516:512]==0;
 wire begin_ok=rx_record[1:0]==1&&rx_record[511:17]==0&&rx_record[12:2]==1024&&rx_record[16:13]==8;
 wire auth_ok=rx_record[1:0]==2&&rx_record[511:66]==0;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin begin_v<=0;begin_epoch<=0;expected_pw<=0;expected_dw<=0;auth_v<=0;auth_epoch<=0;auth_digest<=0;fault<=0;end
  else begin
   begin_v<=0;auth_v<=0;
   if(rx_v!==receive_slot)fault<=1;
   if(receive_slot)begin
    if(rx_v!==1'b1||common_ok!==1'b1||(begin_ok!==1'b1&&auth_ok!==1'b1))fault<=1;
    else if(begin_ok)begin begin_v<=1;begin_epoch<=rx_record[532:517];expected_pw<=rx_record[12:2];expected_dw<=rx_record[16:13];end
    else begin auth_v<=1;auth_epoch<=rx_record[532:517];auth_digest<=rx_record[65:2];end
   end
  end
 end
endmodule

module qfd_program_witness_tx(
 input wire ck,rst_n,send_slot,commit_v,program_ready,installed_fusedcap,program_fault,
 input wire[15:0]program_epoch,input wire[63:0]program_digest,
 output reg tx_v,tx_observed_v,output reg[547:0]tx_record,output reg fault
);
 reg held,cap;reg[15:0]epoch;reg[63:0]digest;
 wire source_ok=!program_ready||(!fault&&held&&!program_fault&&epoch==program_epoch&&digest==program_digest&&cap==installed_fusedcap);
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin held<=0;cap<=0;epoch<=0;digest<=0;tx_v<=0;tx_observed_v<=0;tx_record<=0;fault<=0;end
  else begin
   tx_v<=send_slot;tx_observed_v<=send_slot&&source_ok;
   if(commit_v)begin if(!program_ready||program_fault)fault<=1;held<=1;cap<=installed_fusedcap;epoch<=program_epoch;digest<=program_digest;end
   if(send_slot)begin
    tx_record<={5'd0,4'd14,6'd63,(program_ready?epoch:program_epoch),5'd0,445'd0,program_fault,program_ready,(program_ready?cap:1'b0),(program_ready?digest:program_digest)};
    if(source_ok!==1'b1)fault<=1;
   end
  end
 end
endmodule

module qkd_program_witness_rx(
 input wire ck,rst_n,program_begin_v,receive_slot,rx_v,input wire[547:0]rx_record,
 input wire[15:0]expected_epoch,input wire[63:0]expected_digest,
 input wire authorized_footer_valid,input wire[63:0]authorized_footer,
 output reg program_commit_v,output reg[15:0]program_commit_epoch,output reg[63:0]program_commit_digest,
 output reg program_installed_valid,output reg installed_fusedcap,output reg fault
);
 wire footer_ok=authorized_footer_valid&&authorized_footer[63:32]==32'h58504631&&authorized_footer[31:13]==0&&authorized_footer[1:0]==2&&authorized_footer[5:2]>=1&&authorized_footer[5:2]<=4;
 wire structural_ok=rx_record[547:543]==0&&rx_record[542:539]==14&&rx_record[538:533]==63&&rx_record[516:512]==0&&rx_record[511:67]==0;
 wire record_ok=structural_ok&&rx_record[65]&&!rx_record[66]&&rx_record[532:517]==expected_epoch&&rx_record[63:0]==expected_digest&&footer_ok&&rx_record[64]==authorized_footer[12];
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin program_commit_v<=0;program_commit_epoch<=0;program_commit_digest<=0;program_installed_valid<=0;installed_fusedcap<=0;fault<=0;end
  else begin
   program_commit_v<=0;
   if(program_begin_v)begin program_installed_valid<=0;installed_fusedcap<=0;end
   if(rx_v!==receive_slot)begin fault<=1;program_installed_valid<=0;installed_fusedcap<=0;end
   if(receive_slot)begin
    if(rx_v!==1'b1||structural_ok!==1'b1||program_begin_v)begin fault<=1;program_installed_valid<=0;installed_fusedcap<=0;end
    else if(rx_record[65]===1'b0)begin
     program_installed_valid<=0;installed_fusedcap<=0;if(rx_record[64]!==1'b0||rx_record[66])fault<=1;
    end else if(record_ok!==1'b1)begin fault<=1;program_installed_valid<=0;installed_fusedcap<=0;end
    else begin program_installed_valid<=1;program_commit_v<=1;program_commit_epoch<=rx_record[532:517];program_commit_digest<=rx_record[63:0];installed_fusedcap<=rx_record[64];end
   end
  end
 end
endmodule
