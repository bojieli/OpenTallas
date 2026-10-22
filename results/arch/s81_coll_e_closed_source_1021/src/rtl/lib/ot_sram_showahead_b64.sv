// S81-COLL bank64 production helper (10-19): byte-for-byte logic of the qualified coupon ot_sram_showahead_bank64_coupon
// (19,994 checks PASS, forwarding mutants FAIL, unsafe-collision fatal), renamed for production binding; W/AW free.
`timescale 1ns/1ps
// Registered continuous SRAM read, NEW on a current logical same-address write.
// WREG=1 registers macro write pins; its previous logical write also forwards.
// Caller supplies ra = NEXT head and independent same-depth resets per16-bit slice.
// No reset/storage ECC is added to the SRAM. Two unconditional payload registers
// avoid a W-bit hit-enable cone; reset-distinct kept flags each select <=16 bits.
module ot_sram_showahead_b64 #(
 parameter integer W=553, AW=3, WREG=1, NS=(W+15)/16, MUT=0, LOCAL_HIT=1
)(input wire clk, input wire [NS-1:0] rst_n,
 input wire we, input wire [AW-1:0] wa, input wire [W-1:0] wd,
 input wire [AW-1:0] ra, output wire [W-1:0] q);
 localparam integer NB=(W+63)/64;
 reg wv; reg [AW-1:0] waddr; reg [W-1:0] wdata, prevdata;
 always @(posedge clk or negedge rst_n[0]) if(!rst_n[0]) wv<=1'b0; else wv<=we;
 always @(posedge clk) begin waddr<=wa; wdata<=wd; prevdata<=wdata; end
 wire current_hit=we && wa==ra;
 wire previous_hit=(WREG!=0) && wv && waddr==ra;
 localparam integer HG=(NS+15)/16;
 wire [HG-1:0] local_current_hit,local_previous_hit;
 genvar h;
 generate for(h=0;h<HG;h=h+1) begin:g_hit
  if(LOCAL_HIT) begin:g_local
   // Fixed width avoids paramod keep-name mismatch. Each output drives <=16
   // distinct slice flag D pins; no extra clock edge or shared35-load hit.
   (* keep=1 *) ot_sram_showahead_b64_hit5 u_current(.enable(we),.a(5'(wa)),.b(5'(ra)),.hit(local_current_hit[h]));
   (* keep=1 *) ot_sram_showahead_b64_hit5 u_previous(.enable((WREG!=0)&&wv),.a(5'(waddr)),.b(5'(ra)),.hit(local_previous_hit[h]));
  end else begin:g_legacy
   assign local_current_hit[h]=current_hit;
   assign local_previous_hit[h]=previous_hit;
  end
 end endgenerate
 wire mw=(WREG!=0) ? wv : we;
 wire [AW-1:0] mwa=(WREG!=0) ? waddr : wa;
 wire [W-1:0] mwd=(WREG!=0) ? wdata : wd;
 wire [NB*64-1:0] padded={{(NB*64-W){1'b0}},mwd}, raw;
 // Avoid the undefined same-address dual-clock macro case even with tied
 // clocks. A blocked read is answered only by registered previous-write data;
 // current logical write forwarding has higher priority. No extra edge.
 wire physical_collision=mw&&(mwa==ra);
 wire read_safe=(MUT==3)?1'b1:!physical_collision;
 genvar b,s;
 generate for(b=0;b<NB;b=b+1) begin:g_bank
  ot_sram_1r1w2c_32x64_m1 u_m(.wclk(clk),.rclk(clk),.r_ce_in(read_safe),.r_addr_in(5'(ra)),
   .rd_out(raw[b*64+:64]),.w_ce_in(mw),.w_addr_in(5'(mwa)),
   .wd_in(padded[b*64+:64]),.w_mask_in({64{1'b1}}));
 end
 for(s=0;s<NS;s=s+1) begin:g_slice
  localparam integer LO=s*16, SW=(W-LO<16)?W-LO:16;
  (* keep="true" *) reg cur_q, prev_q;
  always @(posedge clk or negedge rst_n[s])
   if(!rst_n[s]) begin cur_q<=1'b0; prev_q<=1'b0; end
   else begin cur_q<=(MUT==1)?1'b0:local_current_hit[s/16]; prev_q<=(MUT==2)?1'b0:local_previous_hit[s/16]; end
  assign q[LO+:SW]=cur_q ? wdata[LO+:SW] : prev_q ? prevdata[LO+:SW] : raw[LO+:SW];
 end endgenerate
`ifndef SYNTHESIS
 always @(posedge clk) if(rst_n[0] && read_safe && physical_collision)
   $fatal(1,"COLL_COLLISION_UNSAFE macro read/write same address");
 initial begin
  if(WREG!=1 || AW>5 || AW<1 || W<1 || NS!=(W+15)/16) $fatal(1,"ot_sram_showahead_b64 invalid shape");
 end
`endif
endmodule

// Unparameterized kept comparator: independent physical copies per <=16 slices.
(* keep_hierarchy=1 *) module ot_sram_showahead_b64_hit5(
 input wire enable,input wire [4:0] a,b,output wire hit);
 assign hit=enable&&(a==b);
endmodule
