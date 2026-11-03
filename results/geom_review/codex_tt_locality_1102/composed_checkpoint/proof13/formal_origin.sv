module formal_origin(input clk,rn,p,fall,pad,output ok);
 wire old,oldd;wire[3:0] rr,dd,offr,offd,raw_r;wire raw;
 // The actual existing parent leaf and new regional copies sample exactly rst_rl_85 on the same clock.
 ot_dp_rrelay parent(clk,rn,raw);
 for(genvar r=0;r<4;r=r+1) begin:g_raw
   ot_dp_rrelay copy(clk,rn,raw_r[r]);
 end
 ot_dp_landing_origin_s #(.PADW(1),.FWD_COPY(0)) gold(clk,raw,p,fall,pad,old,oldd);
 ot_dp_landing_origin_s_regional #(.ENABLE(1)) gate(clk,raw,p,fall,pad,raw_r,rr,dd);
 ot_dp_landing_origin_s_regional #(.ENABLE(0)) off(clk,raw,p,fall,pad,raw_r,offr,offd);
 assign ok=(raw_r=={4{raw}})&&({4{old}}==rr)&&({4{oldd}}==dd)&&({4{old}}==offr)&&({4{oldd}}==offd);
endmodule
(* keep_hierarchy, keep *) module ot_dp_rrelay(input clk,input d,output reg q);
 always @(posedge clk) q<=d;
endmodule
