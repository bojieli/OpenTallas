module capture_miter #(parameter integer NPC=2,parameter integer MUT=0,parameter integer GW=(NPC==2?1:2))
(input wire clk,input wire[GW-1:0] group_in,input wire[NPC*256-1:0] data_in,output wire mismatch);
 wire[255:0] q;reg[255:0] selected,gold;integer g;
 ot_hbm_svc_vmdel_payload_capture #(.NPC(NPC),.MUT(MUT)) dut(.*);
 always @*begin selected=0;for(g=0;g<NPC;g=g+1) selected=selected|({256{group_in==GW'(g)}}&data_in[g*256+:256]);end
 always @(posedge clk)gold<=selected;
 reg past_valid=0;
 always @(posedge clk)past_valid<=1;
 assign mismatch=past_valid && (q!=gold);
endmodule
