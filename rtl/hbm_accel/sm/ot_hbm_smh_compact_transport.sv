`ifdef OT_SMH_COMPACT_HARD
`define OT_SMH_SLICE ot_hbm_smh_transport_hard
`else
`define OT_SMH_SLICE ot_hbm_smh_transport_slice
`endif
// Compact replacement for the physical pt_w/pt_e band. Each 128-bit slice
// has its own clock/reset pins; the die places the register slices among the
// retained compute children and carries transit wires on assigned M6/M7 tracks.
// RTL-only candidate: physical outline, clocks, cuts and slot fit are unqualified.
module ot_hbm_smh_transport_slice #(
    parameter integer W = 128,
    parameter [W-1:0] RESET_MASK = 0,
    parameter integer STAGES = 2
) (input wire clk, rst_a, input wire [W-1:0] d,
   output wire [W-1:0] first, output wire [W-1:0] last);
    wire rn;
`ifdef OT_SMH_RSTRELAY
    ot_rst_relay #(.REGIONS(1)) u_reset (.clk(clk), .rst_n_in(rst_a), .rst_n(rn));
`else
    assign rn = rst_a;
`endif
    genvar b;
    generate for (b=0; b<W; b=b+1) begin: g_bit
`ifdef OT_SMH_TRANSPORT_KEEP
        // Distinct N/S launch copies must survive synth. ot_keep_regs.tcl
        // moves this wire attribute onto the driving per-bit flop cells.
        (* keep = 1 *) reg q1;
        reg q2;
`else
        reg q1, q2;
`endif
        if (RESET_MASK[b]) begin: g_valid
            always @(posedge clk or negedge rn)
                if (!rn) begin q1<=0; q2<=0; end
                else begin q1<=d[b]; q2<=q1; end
        end else begin: g_data
            always @(posedge clk) begin q1<=d[b]; q2<=q1; end
        end
        assign first[b]=q1;
`ifdef OT_SMH_COMPACT_MUT_LAT
        assign last[b]=q1;
`else
        assign last[b]=(STAGES==1) ? q1 : q2;
`endif
    end endgenerate
endmodule

// A wires-only parent. Slice width and masks specialize to real distinct masters
// when kits are built; this wrapper is never a pin-only physical replacement.
module ot_hbm_smh_compact_pt_w #(parameter integer TAGW=16, NBEAT=13, CHUNK=128) (
 input wire clk,rst_a,
 input wire [2*(6+TAGW+788+1+7)-1:0] rin,
 input wire [7+NBEAT+2048:0] bin,
 output wire [2*(6+TAGW+788+1+7)-1:0] rpm,
 output wire [7+NBEAT+2048:0] bm,
 output wire [6+TAGW+788+1+7-1:0] rl1_n,rl1_s,
 output wire [7+NBEAT+2048:0] bk1_n,bk1_s,
 output wire [NBEAT-1:0] ohl1_n,ohl1_s);
 localparam integer R=6+TAGW+788+1+7, B=8+NBEAT+2048;
 localparam [R-1:0] RM=({{(R-2){1'b0}},2'b11} << (R-2)) | ({{(R-1){1'b0}},1'b1} << 7);
 localparam [B-1:0] BM=({{(B-1){1'b0}},1'b1} << (B-1));
`ifdef OT_SMH_GROUP_TRANSPORT
 ot_hbm_smh_group_pt_w #(.TAGW(TAGW),.NBEAT(NBEAT),.CHUNK(CHUNK)) u_groups(.*);
`else
 wire [2*R-1:0] first_r;
 wire [B-1:0] first_b;
 genvar row,k;
 generate for(row=0;row<2;row=row+1) begin: g_row
  for(k=0;k<(R+CHUNK-1)/CHUNK;k=k+1) begin: g_slice
   localparam integer OFF=k*CHUNK, W=(R-OFF<CHUNK)?R-OFF:CHUNK;
   `OT_SMH_SLICE #(.W(W),.RESET_MASK(RM[OFF+:W])) u_slice
    (.clk(clk),.rst_a(rst_a),.d(rin[row*R+OFF+:W]),.first(first_r[row*R+OFF+:W]),.last(rpm[row*R+OFF+:W]));
  end
 end
 for(k=0;k<(B+CHUNK-1)/CHUNK;k=k+1) begin: g_beat
  localparam integer OFF=k*CHUNK, W=(B-OFF<CHUNK)?B-OFF:CHUNK;
  wire [W-1:0] unused_n,unused_s;
  `OT_SMH_SLICE #(.W(W),.RESET_MASK(BM[OFF+:W])) u_transit
   (.clk(clk),.rst_a(rst_a),.d(bin[OFF+:W]),.first(first_b[OFF+:W]),.last(bm[OFF+:W]));
  `OT_SMH_SLICE #(.W(W),.STAGES(1),.RESET_MASK(BM[OFF+:W])) u_north
   (.clk(clk),.rst_a(rst_a),.d(bin[OFF+:W]),.first(bk1_n[OFF+:W]),.last(unused_n));
  `OT_SMH_SLICE #(.W(W),.STAGES(1),.RESET_MASK(BM[OFF+:W])) u_south
   (.clk(clk),.rst_a(rst_a),.d(bin[OFF+:W]),.first(bk1_s[OFF+:W]),.last(unused_s));
 end endgenerate
 assign rl1_n=first_r[0+:R]; assign rl1_s=first_r[R+:R];
 assign ohl1_n=bk1_n[2048+:NBEAT]; assign ohl1_s=bk1_s[2048+:NBEAT];
`endif
endmodule

module ot_hbm_smh_compact_pt_e #(parameter integer TAGW=16,NBEAT=13,CHUNK=128) (
 input wire clk,rst_a,
 input wire [2*(6+TAGW+788+1+7)-1:0] rpm,
 input wire [7+NBEAT+2048:0] bm,
 output wire [2*(6+TAGW+788+1+7)-1:0] rout,
 output wire [7+NBEAT+2048:0] bout);
 localparam integer R=6+TAGW+788+1+7, B=8+NBEAT+2048;
 localparam [R-1:0] RM=({{(R-2){1'b0}},2'b11} << (R-2)) | ({{(R-1){1'b0}},1'b1} << 7);
 localparam [B-1:0] BM=({{(B-1){1'b0}},1'b1} << (B-1));
`ifdef OT_SMH_GROUP_TRANSPORT
 ot_hbm_smh_group_pt_e #(.TAGW(TAGW),.NBEAT(NBEAT),.CHUNK(CHUNK)) u_groups(.*);
`else
 genvar row,k;
 generate for(row=0;row<2;row=row+1) begin: g_row
  for(k=0;k<(R+CHUNK-1)/CHUNK;k=k+1) begin: g_slice
   localparam integer OFF=k*CHUNK,W=(R-OFF<CHUNK)?R-OFF:CHUNK;
   wire [W-1:0] unused_first;
   `OT_SMH_SLICE #(.W(W),.RESET_MASK(RM[OFF+:W])) u_slice
    (.clk(clk),.rst_a(rst_a),.d(rpm[row*R+OFF+:W]),.first(unused_first),.last(rout[row*R+OFF+:W]));
  end
 end
 for(k=0;k<(B+CHUNK-1)/CHUNK;k=k+1) begin: g_beat
  localparam integer OFF=k*CHUNK,W=(B-OFF<CHUNK)?B-OFF:CHUNK;
  wire [W-1:0] unused_first;
  `OT_SMH_SLICE #(.W(W),.RESET_MASK(BM[OFF+:W])) u_slice
   (.clk(clk),.rst_a(rst_a),.d(bm[OFF+:W]),.first(unused_first),.last(bout[OFF+:W]));
 end endgenerate
`endif
endmodule

`undef OT_SMH_SLICE
