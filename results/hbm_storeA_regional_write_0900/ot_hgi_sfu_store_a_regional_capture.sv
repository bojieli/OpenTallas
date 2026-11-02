// Disabled source-event proposal. Four copies of EXISTING capture stages;
// this does not insert a pipeline edge or replace a production caller.
module ot_hgi_sfu_store_a_regional_capture(
 input wire clk,
 input wire ctl_reset_n, // exact selected CTL n6/m55 region2
 input wire meta_reset_n, // exact selected VM delivered rst_lg_n/t22
 input wire[2047:0] payload_D,
 input wire[151:0] meta87_D,
 output wire[8191:0] region_data,
 output wire[479:0] region_addr,
 output wire[63:0] region_group,
 output wire[31:0] region_stage_v
);
 for(genvar region=0;region<4;region=region+1)begin:g_region
  (* keep = "true", dont_touch = "true" *) reg[2047:0] data_q;
  (* keep = "true", dont_touch = "true" *) reg[151:0] meta_q;
  (* keep = "true", dont_touch = "true" *) always @(posedge clk or negedge ctl_reset_n)
   if(!ctl_reset_n)data_q<=0;
   else data_q<=payload_D;
  (* keep = "true", dont_touch = "true" *) always @(posedge clk or negedge meta_reset_n)
   if(!meta_reset_n)meta_q<=0;
   else meta_q<=meta87_D;
  assign region_data[2048*region+:2048]=data_q;
  for(genvar g=0;g<4;g=g+1)begin:g_meta
   assign region_addr[120*region+30*g+:30]=meta_q[38*g+2+:30];
   assign region_group[16*region+4*g+:4]=meta_q[38*g+32+:4];
   assign region_stage_v[8*region+2*g+:2]=meta_q[38*g+36+:2]&~meta_q[38*g+:2];
  end
 end
endmodule
