`timescale 1ps/1fs
module cut_ref #(parameter integer QW=11)(input wire clk,input wire [335:0] u,input wire [QW-1:0] q,input wire [20:0] acc,input wire [3:0] tag,output wire [3:0] sel,output wire [20:0] above,output wire [QW-1:0] quota,output wire [3:0] date,output wire valid);
localparam integer XW=21;
integer i,ia,ib;
wire [335:0] s3_r=u; wire [QW-1:0] q3=q; reg [3:0] g_out;
    reg [15:0]      gea;
    reg [16*XW-1:0] s4_r;
    reg [QW-1:0]    q4;
    always @(posedge clk) begin
        for (ia = 0; ia < 16; ia = ia + 1) gea[ia] <= (s3_r[XW*ia +: XW] >= {{(XW-QW){1'b0}}, q3});
        s4_r <= s3_r; q4 <= q3;
    end
    reg [3:0]    ga;
    reg [XW-1:0] acca;
    always @(*) begin
        ga = 4'd0;
        for (i = 0; i < 16; i = i + 1)
            if (gea[i]) ga = i[3:0];
        acca = (ga == 4'd15) ? {XW{1'b0}} : s4_r[XW*(ga + 4'd1) +: XW];
    end
    reg [XW-1:0] acc_a;
    reg [QW-1:0] qa;
    always @(posedge clk) begin g_out <= ga; acc_a <= acca; qa <= q4; end
assign sel=g_out;assign above=acc_a;assign quota=qa;assign date=0;assign valid=0;
endmodule
module cut_r1 #(parameter integer QW=11)(input wire clk,input wire [335:0] u,input wire [QW-1:0] q,input wire [20:0] acc,input wire [3:0] tag,output wire [3:0] sel,output wire [20:0] above,output wire [QW-1:0] quota,output wire [3:0] date,output wire valid);
localparam integer XW=21;
integer i,ia,ib;
wire [335:0] s3_r=u; wire [QW-1:0] q3=q; reg [3:0] g_out;
    reg [15:0]      gea;
    reg [16*XW-1:0] s4_r;
    reg [QW-1:0]    q4;
    always @(posedge clk) begin
        for (ia = 0; ia < 16; ia = ia + 1) gea[ia] <= (s3_r[XW*ia +: XW] >= {{(XW-QW){1'b0}}, q3});
        s4_r <= s3_r; q4 <= q3;
    end
    reg [3:0] ga;
    wire [XW-1:0] acca;
    always @(*) begin
        ga = 4'd0;
        for (i = 0; i < 16; i = i + 1)
            if (gea[i]) ga = i[3:0];
    end
    // A-select R1: top bucket returns ZERO, unlike B's acc_b4 fallback.
    wire [15:0] ah;
    wire az = ~|gea[15:1];
    generate for (genvar ak = 0; ak < 16; ak = ak + 1) begin : g_a_select_highest
        if (ak == 15) begin : g_top
            assign ah[ak] = gea[ak];
        end else begin : g_other
            assign ah[ak] = gea[ak] & ~|gea[15:ak+1];
        end
    end endgenerate
    wire [XW-1:0] a_t [0:15];
    generate for (genvar ak = 0; ak < 16; ak = ak + 1) begin : g_a_select_count
        if (ak == 15) begin : g_top
            assign a_t[ak] = {XW{1'b0}};
        end else if (ak == 0) begin : g_zero
            assign a_t[ak] = {XW{az}} & s4_r[XW +: XW];
        end else begin : g_other
            assign a_t[ak] = {XW{ah[ak]}} & s4_r[XW*(ak+1) +: XW];
        end
    end endgenerate
    assign acca = ((a_t[0] | a_t[1]) | (a_t[2] | a_t[3]))
                | ((a_t[4] | a_t[5]) | (a_t[6] | a_t[7]))
                | ((a_t[8] | a_t[9]) | (a_t[10] | a_t[11]))
                | ((a_t[12] | a_t[13]) | (a_t[14] | a_t[15]));
    reg [XW-1:0] acc_a;
    reg [QW-1:0] qa;
    always @(posedge clk) begin g_out <= ga; acc_a <= acca; qa <= q4; end
assign sel=g_out;assign above=acc_a;assign quota=qa;assign date=0;assign valid=0;
endmodule
module cut_r2 #(parameter integer QW=11)(input wire clk,input wire [335:0] u,input wire [QW-1:0] q,input wire [20:0] acc,input wire [3:0] tag,output wire [3:0] sel,output wire [20:0] above,output wire [QW-1:0] quota,output wire [3:0] date,output wire valid);
localparam integer XW=21;
integer i,ia,ib;
wire [335:0] s3_r=u; wire [QW-1:0] q3=q; reg [3:0] g_out;
    reg [15:0]      gea;
    reg [16*XW-1:0] s4_r;
    reg [QW-1:0]    q4;
    always @(posedge clk) begin
        for (ia = 0; ia < 16; ia = ia + 1) gea[ia] <= (s3_r[XW*ia +: XW] >= {{(XW-QW){1'b0}}, q3});
        s4_r <= s3_r; q4 <= q3;
    end
    reg [3:0] ga;
    wire [XW-1:0] acca;
    always @(*) begin
        ga = 4'd0;
        for (i = 0; i < 16; i = i + 1)
            if (gea[i]) ga = i[3:0];
    end
    // A-select R2: mask and sum capture the SAME compare input edge; no added cycle.
    wire [15:0] gea_nx;
    generate for (genvar ak = 0; ak < 16; ak = ak + 1) begin : g_a_select_compare_next
        assign gea_nx[ak] = s3_r[XW*ak +: XW] >= {{(XW-QW){1'b0}}, q3};
    end endgenerate
    reg [15:0] ah;
    reg az;
    // BEGIN registered A selector -- mutant changes only this block to stale gea
    generate for (genvar ak = 0; ak < 16; ak = ak + 1) begin : g_a_select_highest
        if (ak == 15) begin : g_top
            always @(posedge clk) ah[ak] <= gea_nx[ak];
        end else begin : g_other
            always @(posedge clk) ah[ak] <= gea_nx[ak] & ~|gea_nx[15:ak+1];
        end
    end endgenerate
    always @(posedge clk) az <= ~|gea_nx[15:1];
    // END registered A selector
    wire [XW-1:0] a_t [0:15];
    generate for (genvar ak = 0; ak < 16; ak = ak + 1) begin : g_a_select_count
        if (ak == 15) begin : g_top
            assign a_t[ak] = {XW{1'b0}};
        end else if (ak == 0) begin : g_zero
            assign a_t[ak] = {XW{az}} & s4_r[XW +: XW];
        end else begin : g_other
            assign a_t[ak] = {XW{ah[ak]}} & s4_r[XW*(ak+1) +: XW];
        end
    end endgenerate
    assign acca = ((a_t[0] | a_t[1]) | (a_t[2] | a_t[3]))
                | ((a_t[4] | a_t[5]) | (a_t[6] | a_t[7]))
                | ((a_t[8] | a_t[9]) | (a_t[10] | a_t[11]))
                | ((a_t[12] | a_t[13]) | (a_t[14] | a_t[15]));
    reg [XW-1:0] acc_a;
    reg [QW-1:0] qa;
    always @(posedge clk) begin g_out <= ga; acc_a <= acca; qa <= q4; end
assign sel=g_out;assign above=acc_a;assign quota=qa;assign date=0;assign valid=0;
endmodule
module cut_mut #(parameter integer QW=11)(input wire clk,input wire [335:0] u,input wire [QW-1:0] q,input wire [20:0] acc,input wire [3:0] tag,output wire [3:0] sel,output wire [20:0] above,output wire [QW-1:0] quota,output wire [3:0] date,output wire valid);
localparam integer XW=21;
integer i,ia,ib;
wire [335:0] s3_r=u; wire [QW-1:0] q3=q; reg [3:0] g_out;
    reg [15:0]      gea;
    reg [16*XW-1:0] s4_r;
    reg [QW-1:0]    q4;
    always @(posedge clk) begin
        for (ia = 0; ia < 16; ia = ia + 1) gea[ia] <= (s3_r[XW*ia +: XW] >= {{(XW-QW){1'b0}}, q3});
        s4_r <= s3_r; q4 <= q3;
    end
    reg [3:0] ga;
    wire [XW-1:0] acca;
    always @(*) begin
        ga = 4'd0;
        for (i = 0; i < 16; i = i + 1)
            if (gea[i]) ga = i[3:0];
    end
    // A-select R2: mask and sum capture the SAME compare input edge; no added cycle.
    wire [15:0] gea_nx;
    generate for (genvar ak = 0; ak < 16; ak = ak + 1) begin : g_a_select_compare_next
        assign gea_nx[ak] = s3_r[XW*ak +: XW] >= {{(XW-QW){1'b0}}, q3};
    end endgenerate
    reg [15:0] ah;
    reg az;
    // BEGIN registered A selector -- mutant changes only this block to stale gea
    generate for (genvar ak = 0; ak < 16; ak = ak + 1) begin : g_a_select_highest
        if (ak == 15) begin : g_top
            always @(posedge clk) ah[ak] <= gea[ak];
        end else begin : g_other
            always @(posedge clk) ah[ak] <= gea[ak] & ~|gea[15:ak+1];
        end
    end endgenerate
    always @(posedge clk) az <= ~|gea[15:1];
    // END registered A selector
    wire [XW-1:0] a_t [0:15];
    generate for (genvar ak = 0; ak < 16; ak = ak + 1) begin : g_a_select_count
        if (ak == 15) begin : g_top
            assign a_t[ak] = {XW{1'b0}};
        end else if (ak == 0) begin : g_zero
            assign a_t[ak] = {XW{az}} & s4_r[XW +: XW];
        end else begin : g_other
            assign a_t[ak] = {XW{ah[ak]}} & s4_r[XW*(ak+1) +: XW];
        end
    end endgenerate
    assign acca = ((a_t[0] | a_t[1]) | (a_t[2] | a_t[3]))
                | ((a_t[4] | a_t[5]) | (a_t[6] | a_t[7]))
                | ((a_t[8] | a_t[9]) | (a_t[10] | a_t[11]))
                | ((a_t[12] | a_t[13]) | (a_t[14] | a_t[15]));
    reg [XW-1:0] acc_a;
    reg [QW-1:0] qa;
    always @(posedge clk) begin g_out <= ga; acc_a <= acca; qa <= q4; end
assign sel=g_out;assign above=acc_a;assign quota=qa;assign date=0;assign valid=0;
endmodule
