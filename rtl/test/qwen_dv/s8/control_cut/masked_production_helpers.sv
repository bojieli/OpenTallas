`timescale 1ns/1ps
module qfd_dv_s8_lp_flags_mask_local_w #(
    parameter integer W = 24, D = 4, FW=2, FLO=16,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D),
    parameter integer GB = 12                                  // data bits per kept selector copy (~2 GB + 2 loads)
) (
    input wire ck, rsi,
    input wire [W-1:0] i,
    input wire [D*FW-1:0] masked,
    output wire [D-1:0] flags_oh,
    output wire [D*W-1:0] bank,
    output wire [D*(AW+1)-1:0] epo,
    output wire [D-1:0] vld
);
    localparam integer NC = (W + GB - 1) / GB;
    reg rq;
    reg [D-1:0] valid;
    wire [NC*D-1:0] oh;                                        // copy g = oh[g*D +: D]
    always @(posedge ck) rq <= rsi;
    genvar s, g;
    generate for (g = 0; g < NC; g = g + 1) begin : g_oh
        ot_pl_land_n32_oh #(.D(D), .ID(g)) u_oh (.ck(ck), .rq(rq), .oh(oh[g*D +: D]));
    end endgenerate
    assign flags_oh=oh[(FLO/GB)*D+:D];
    always @(posedge ck)
        if (!rq) valid <= 0;
        else     valid <= valid | oh[D-1:0];
    generate for (s=0;s<D;s=s+1) begin:g_slot
        for (g = 0; g < NC; g = g + 1) begin : g_grp
            localparam integer LO = g * GB;
            localparam integer GW = (W - LO < GB) ? W - LO : GB;
            reg [GW-1:0] dq;
            wire [GW-1:0] slot_i;
            for(genvar h=0;h<GW;h=h+1)begin:g_input
                if(LO+h>=FLO && LO+h<FLO+FW)begin:g_masked
                    assign slot_i[h]=masked[s*FW+LO+h-FLO];
                end else begin:g_original
                    assign slot_i[h]=i[LO+h];
                end
            end
            always @(posedge ck) if (oh[g*D + s]) dq <= slot_i;
            assign bank[s*W + LO +: GW] = dq;
        end
    end endgenerate
    assign vld = valid;
`ifndef SYNTHESIS
    reg [AW:0] wc;
    reg [AW:0] epoch [0:D-1];
    always @(posedge ck) if (!rq) wc <= 0; else wc <= wc + 1'b1;
    generate for (s=0;s<D;s=s+1) begin:g_ep
        always @(posedge ck) if (rq && oh[s]) epoch[s] <= wc;
        assign epo[s*(AW+1)+:AW+1] = epoch[s];
    end endgenerate
`else
    assign epo = {(D*(AW+1)){1'b0}};
`endif
endmodule

module qfd_dv_s8_lp_flags_mask_gate #(parameter integer FW=2,ID=0)(
 input wire [FW-1:0] i,input wire a,b,c,output wire [FW-1:0] y);
 wire any_en=a|b|c;
 assign y=any_en ? i : {FW{1'b0}};
endmodule
