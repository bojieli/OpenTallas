`timescale 1ns/1ps
`default_nettype none
// Actual stage cmd85 -> die PQ f_iss92 producer. The descriptor image stores
// {native_tag2, command-sample-to-observed-retire edges24, native fields90}; GO is a registered
// command event. Neither readiness nor observed END changes the fixed edge.
// PW36: {v,address7,page3,reserved1,payload24}; pages0..4 fill116bits.
// Page7 address0: {seal1,reserved16,length8}. BEGIN revokes the old image;
// SEAL scans every row in NDesc fixed edges, independent of row contents.
module ot_s81_pq_command_endpoint #(
 parameter integer NDESC=64,MUT=0,PHW=9,PINREG=0,
 parameter integer NATIVE_BITS=81+PHW,DESC_BITS=NATIVE_BITS+26
)(input wire ck,rst_n,input wire[84:0]c_cmd,
 input wire[35:0]f_desc_pw,input wire[38:0]t_iss,
 output wire[NATIVE_BITS+1:0]f_iss,output reg[8:0]c_done,output wire[1:0]c_st,
 output wire image_sealed);
 wire[84:0]c_cmd_pin;wire[35:0]f_desc_pw_pin;wire[38:0]t_iss_pin;
 generate if(PINREG!=0)begin:g_input_capture
  reg[84:0]cmd_q;reg[35:0]pw_q;reg[38:0]status_q;
  always @(posedge ck or negedge rst_n)
   if(!rst_n)begin cmd_q[84]<=0;pw_q[35]<=0;end
   else begin cmd_q[84]<=c_cmd[84];pw_q[35]<=f_desc_pw[35];end
  always @(posedge ck)begin
   cmd_q[83:0]<=c_cmd[83:0];pw_q[34:0]<=f_desc_pw[34:0];status_q<=t_iss;
  end
  assign c_cmd_pin=cmd_q;assign f_desc_pw_pin=pw_q;assign t_iss_pin=status_q;
 end else begin:g_legacy_boundary
  assign c_cmd_pin=c_cmd;assign f_desc_pw_pin=f_desc_pw;assign t_iss_pin=t_iss;
 end endgenerate

 reg[DESC_BITS-1:0]mem[0:NDESC-1];reg[4:0]loaded[0:NDESC-1];
 reg[7:0]length_q,scan;reg begun,sealed,scanning,scan_bad;
 reg fault,go_q;reg[3:0]active;reg[7:0]command_tag[0:3];
 reg[NATIVE_BITS-1:0]native_fields;reg[23:0]age[0:3],duration[0:3];
 wire pw_v=f_desc_pw_pin[35];wire[6:0]addr=f_desc_pw_pin[34:28];
 wire[2:0]page=f_desc_pw_pin[27:25];wire[23:0]payload=f_desc_pw_pin[23:0];
 wire valid_command=c_cmd_pin[84];wire[23:0]arg=c_cmd_pin[30:7];
 assign f_iss={fault,native_fields,go_q};
 assign c_st={sealed&&!fault,fault};assign image_sealed=sealed;
 integer i,s;reg bad;reg seen_done;reg[1:0]selected_tag;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin
   length_q<=0;scan<=0;begun<=0;sealed<=0;scanning<=0;scan_bad<=0;
   fault<=0;active<=0;go_q<=0;
   for(i=0;i<4;i=i+1)begin command_tag[i]<=0;age[i]<=0;duration[i]<=0;end
   native_fields<=0;c_done<=0;
   for(i=0;i<NDESC;i=i+1)loaded[i]<=0;
  end else begin
   go_q<=0;c_done<=0;seen_done=0;
   if(t_iss_pin[2])fault<=1;
   if(pw_v)begin
    if((|active)||scanning)fault<=1;
    else if(page==7)begin
     if(addr!=0||f_desc_pw_pin[23:8]!=0||payload[7:0]==0||payload[7:0]>NDESC)begin fault<=1;sealed<=0;end
     else if(!f_desc_pw_pin[24])begin
      begun<=1;sealed<=0;length_q<=payload[7:0];
      for(i=0;i<NDESC;i=i+1)loaded[i]<=0;
     end else begin
      scanning<=1;sealed<=0;scan<=0;scan_bad<=!begun||length_q!=payload[7:0];
     end
    end else if(!begun||addr>=length_q||page>=5||f_desc_pw_pin[24]||(page==4&&(payload >> (DESC_BITS-96))!=0))begin fault<=1;sealed<=0;end
    else begin
     sealed<=0;
     case(page)
      0:mem[addr][23:0]<=payload;
      1:mem[addr][47:24]<=payload;
      2:mem[addr][71:48]<=payload;
      3:mem[addr][95:72]<=payload;
      4:mem[addr][DESC_BITS-1:96]<=payload[DESC_BITS-97:0];
     endcase
     loaded[addr][page]<=1;
    end
   end
   if(scanning)begin
    bad=scan_bad;
    if(scan<length_q&&(loaded[scan]!=5'b11111||mem[scan][NATIVE_BITS+23:NATIVE_BITS]<3))bad=1;
    scan_bad<=bad;
    if(scan==NDESC-1)begin scanning<=0;sealed<=!bad&&!fault;if(bad)fault<=1;end
    else scan<=scan+1'b1;
   end
   if(valid_command)begin
    selected_tag=arg<length_q?mem[arg][NATIVE_BITS+25:NATIVE_BITS+24]:2'd0;
    // Compiler selects the real native tag. No search for a free slot.
    if(!sealed||pw_v||arg>=length_q||active[selected_tag])fault<=1;
    else begin
     active[selected_tag]<=1;go_q<=1;age[selected_tag]<=0;
     native_fields<=mem[arg][NATIVE_BITS-1:0];duration[selected_tag]<=mem[arg][NATIVE_BITS+23:NATIVE_BITS];
     command_tag[selected_tag]<={c_cmd_pin[83],c_cmd_pin[6:0]};
     if(!t_iss_pin[0])fault<=1;
    end
   end
   // Static successor's END is the explicit retire-tag pulse. Global idle
   // may stay low while other native tags are live and never gates commands.
   if(t_iss_pin[36]&&(!active[t_iss_pin[38:37]]||age[t_iss_pin[38:37]]!=duration[t_iss_pin[38:37]]-1'b1))fault<=1;
   for(s=0;s<4;s=s+1)if(active[s])begin
    age[s]<=age[s]+1'b1;
    if(age[s]==duration[s]-1'b1+((MUT==1)?24'd1:24'd0))begin
     c_done<={1'b1,command_tag[s]};active[s]<=0;
     if(seen_done||!t_iss_pin[36]||t_iss_pin[38:37]!=s)fault<=1;
     seen_done=1;
    end
   end
  end
 end
endmodule
`default_nettype wire
