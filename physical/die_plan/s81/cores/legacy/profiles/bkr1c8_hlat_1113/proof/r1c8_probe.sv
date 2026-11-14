module ot_s81ph_hlk #(parameter integer W = 1, parameter integer EN = 0) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate if (EN != 0) begin : g_lat
        reg [W-1:0] l;
`ifdef OT_S81PH_HLK_MUT
        always_latch if (clk) l <= d;     // bench mutant: positive-level latch (the hop passes in the high phase)
`else
        always_latch if (!clk) l <= d;
`endif
        assign q = l;
`ifdef OT_S81PH_HLK_COV
        // bench coverage only: count q changes (each latch must toggle under the layer traffic)
        integer ntog = 0; reg [W-1:0] lq;
        always @(negedge clk) begin #0.001 if (l !== lq) ntog = ntog + 1; lq = l; end
        final $display("HLK_COV %m W %0d toggles %0d", W, ntog);
`endif
    end else begin : g_wire
        assign q = d;
    end endgenerate
endmodule
module ref_mux #(parameter MUT=0, HLAT=1, MW=592, NG=22, GB=(MW+NG-1)/NG)(input clk,rst_n,rpd,mbd,input [MW-1:0] i0_lane,mem_rdata,output [MW-1:0] r1_d,output [NG-1:0] rpb_out,memb_out);
 genvar gg;
    wire [NG-1:0] rpb_v, memb_v;
    generate for (gg = 0; gg < NG; gg = gg + 1) begin : g_r1
        localparam integer LO = gg * GB;
        localparam integer SW = (MW - LO < GB) ? (MW - LO) : GB;
        (* keep = "true" *) reg rpb, memb;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin rpb <= 1'b0; memb <= 1'b1; end
            else begin rpb <= rpd; memb <= (MUT == 1 && gg == 7) ? 1'b0 : mbd; end
        assign rpb_v[gg] = rpb; assign memb_v[gg] = memb;
        reg [SW-1:0] q;
        wire rpb_l, memb_l;   // HLAT: rpb / memb -> q through one lockup latch
        ot_s81ph_hlk #(.W(2), .EN(HLAT)) u_fl_r1s (.clk(clk), .d({rpb, memb}), .q({rpb_l, memb_l}));
        always @(posedge clk) q <= (i0_lane[LO +: SW] & {SW{rpb_l}}) | (mem_rdata[LO +: SW] & {SW{memb_l}});
        assign r1_d[LO +: SW] = q;
    end endgenerate

assign rpb_out=rpb_v; assign memb_out=memb_v; endmodule

`define OT_BKQ_R1C8
module new_mux #(parameter MUT=0, HLAT=1, MW=592, NG=22, GB=(MW+NG-1)/NG)(input clk,rst_n,rpd,mbd,input [MW-1:0] i0_lane,mem_rdata,output [MW-1:0] r1_d,output [NG-1:0] rpb_out,memb_out);
 genvar gg;
    wire [NG-1:0] rpb_v, memb_v;
    generate for (gg = 0; gg < NG; gg = gg + 1) begin : g_r1
        localparam integer LO = gg * GB;
        localparam integer SW = (MW - LO < GB) ? (MW - LO) : GB;
        (* keep = "true" *) reg rpb, memb;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin rpb <= 1'b0; memb <= 1'b1; end
            else begin rpb <= rpd; memb <= (MUT == 1 && gg == 7) ? 1'b0 : mbd; end
        assign rpb_v[gg] = rpb; assign memb_v[gg] = memb;
        reg [SW-1:0] q;
        wire rpb_l, memb_l;   // HLAT: rpb / memb -> q through one lockup latch
        ot_s81ph_hlk #(.W(2), .EN(HLAT)) u_fl_r1s (.clk(clk), .d({rpb, memb}), .q({rpb_l, memb_l}));
`ifdef OT_BKQ_R1C8
        // Same-cycle H2 control copies: each kept pair owns at most eight payload bits.
        // The original rpb/memb pair still owns the sign sideband (rpb_v/memb_v).
        // Every copy samples the identical rpd/mbd edge and retains the launch-side HLAT.
        for (genvar rs = 0; rs < (SW+7)/8; rs = rs + 1) begin : g_cp8
            localparam integer RL = rs*8;
            localparam integer RW = (SW-RL < 8) ? SW-RL : 8;
            (* keep = "true" *) reg rp8, mb8;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin rp8 <= 1'b0; mb8 <= 1'b1; end
                else begin
`ifdef OT_BKQ_R1C8_MUT
                    rp8 <= (gg == 5 && rs == 2) ? !rpd : rpd;
`else
                    rp8 <= rpd;
`endif
                    mb8 <= (MUT == 1 && gg == 7) ? 1'b0 : mbd;
                end
            wire rp8_l, mb8_l;
            ot_s81ph_hlk #(.W(2), .EN(HLAT)) u_fl_r1s (.clk(clk), .d({rp8, mb8}), .q({rp8_l, mb8_l}));
            always @(posedge clk) q[RL +: RW] <= (i0_lane[LO+RL +: RW] & {RW{rp8_l}}) | (mem_rdata[LO+RL +: RW] & {RW{mb8_l}});
        end
`else
        always @(posedge clk) q <= (i0_lane[LO +: SW] & {SW{rpb_l}}) | (mem_rdata[LO +: SW] & {SW{memb_l}});
`endif
        assign r1_d[LO +: SW] = q;
    end endgenerate

assign rpb_out=rpb_v; assign memb_out=memb_v; endmodule

module tb;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,rpd=0,mbd=1;
reg [591:0] lane=0,mem=0;
wire [591:0] a,b;wire [21:0] ar,am,br,bm;
ref_mux ref0(clk,rst_n,rpd,mbd,lane,mem,a,ar,am);
new_mux new0(clk,rst_n,rpd,mbd,lane,mem,b,br,bm);
integer i,j,mismatch=0;
initial begin
  for(i=0;i<2048;i=i+1) begin
    @(negedge clk);#1;
    rst_n=(i%127!=0 && i>1);rpd=$random;mbd=$random;
    for(j=0;j<592;j=j+1) begin lane[j]=$random;mem[j]=$random;end
    @(posedge clk);#1;
    if(i>3 && ({a,ar,am} !== {b,br,bm})) begin mismatch=mismatch+1;end
  end
`ifdef OT_BKQ_R1C8_MUT
 if(mismatch==0) $fatal(1,"mutant survived");
 $display("MUTANT_KILLED mismatches=%0d",mismatch);
`else
 if(mismatch!=0) $fatal(1,"exact mismatch count=%0d",mismatch);
 $display("EXACT_PASS cycles=2048 payload_bits=592 sideband_control_pairs=22 cycle_delta=0");
`endif
 $finish;
end
endmodule
