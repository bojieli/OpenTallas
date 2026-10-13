`timescale 1ns/1ps
// New M5 leaf: 32 original FSW32 FIFO slices, two banks. Four leaves
// replace one 4096-bit regional FIFO. The original registered pop/push
// replicas and one-hot pointer epochs are preserved inside this boundary.
// DONT add another pin-register stage without matching every epoch/data path.
module ot_qfd_vm_xfifo32_t #(
    parameter integer NPP=12,
    parameter integer FSW=32,
    parameter integer MEREG=1,
    parameter integer MUT=0
)(
    input wire clk,
    input wire me_in,
    input wire [1:0] rtg,
    input wire [1:0] pgw,
    input wire [1:0] xg,
    input wire [1023:0] bx,
    output reg [1023:0] xo
);
    localparam integer NSL=1024/FSW;
    localparam integer SPB=512/FSW;
    genvar k,e;
    initial if(FSW!=32 || NPP<2 || 1024*NPP+1024+(2*NPP+3)*NSL>15000)
        $fatal(1,"invalid local FIFO clock root budget");
    generate for (k = 0; k < NSL; k = k + 1) begin : g_fs
        (* keep = "true", dont_touch = "true" *) reg mr_k;       // me_t replica
        (* keep = "true", dont_touch = "true" *) reg pp_k;       // pop pin-flop replica
        (* keep = "true", dont_touch = "true" *) reg xv_k;       // push replica
        (* keep = "true", dont_touch = "true" *) reg [NPP-1:0] wpo, rpo;
        wire me_k = (MEREG != 0) ? mr_k : me_in;
        wire pop_k = me_k && pp_k;
        always @(posedge clk) mr_k <= me_in;
        always @(posedge clk or negedge rtg[k / SPB])
            if (!rtg[k / SPB]) begin pp_k <= 1'b0; xv_k <= 1'b0; wpo <= {{(NPP-1){1'b0}}, 1'b1}; rpo <= {{(NPP-1){1'b0}}, 1'b1}; end
            else begin
                if (me_k) pp_k <= pgw[k / SPB];
                xv_k <= xg[k / SPB];
                if (xv_k) wpo <= (NPP > 1) ? {wpo[NPP-2:0], wpo[NPP-1]} : wpo;
                if (pop_k) rpo <= (NPP > 1) ? {rpo[NPP-2:0], rpo[NPP-1]} : rpo;
            end
        reg [FSW-1:0] fe [0:NPP-1];
        for (e = 0; e < NPP; e = e + 1) begin : g_fe
            always @(posedge clk) if (xv_k && wpo[e]) fe[e] <= bx[k*FSW +: FSW];
        end
        reg [FSW-1:0] rd;
        integer i;
        always @* begin
            rd = {FSW{1'b0}};
            for (i = 0; i < NPP; i = i + 1) rd = rd | (fe[(i + ((MUT != 0) ? 1 : 0)) % NPP] & {FSW{rpo[i]}});
        end
        always @(posedge clk) if (pop_k) xo[k*FSW +: FSW] <= rd;
    end endgenerate
endmodule
