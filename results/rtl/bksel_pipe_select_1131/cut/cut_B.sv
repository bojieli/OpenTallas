`timescale 1ps/1fs
module cut_ref #(parameter integer QW=11)(input wire clk,input wire [335:0] u,input wire [QW-1:0] q,input wire [20:0] acc,input wire [3:0] tag,output wire [3:0] sel,output wire [20:0] above,output wire [QW-1:0] quota,output wire [3:0] date,output wire valid);
localparam integer XW=21;
integer i,ia,ib;
wire [335:0] u3_r=u;wire [QW-1:0] q_b3=q;wire [20:0] acc_b3=acc;wire [3:0] g_b3=tag;reg [7:0] res_b;reg [20:0] res_above;reg res_ok;
    reg [15:0]      geb;
    reg [16*XW-1:0] u4_r;
    reg [XW-1:0]    acc_b4;
    reg [3:0]       g_b4;
    always @(posedge clk) begin
        for (ib = 0; ib < 16; ib = ib + 1) geb[ib] <= (u3_r[XW*ib +: XW] >= {{(XW-QW){1'b0}}, q_b3});
        u4_r <= u3_r; acc_b4 <= acc_b3; g_b4 <= g_b3;
    end
    reg [3:0]    bb;
    reg          okb;
    reg [XW-1:0] aboveb;
    always @(*) begin
        bb = 4'd0; okb = 1'b0;
        for (i = 0; i < 16; i = i + 1)
            if (geb[i]) begin bb = i[3:0]; okb = 1'b1; end
        aboveb = (bb == 4'd15) ? acc_b4 : u4_r[XW*(bb + 4'd1) +: XW];
    end
    always @(posedge clk) begin
        res_b <= {g_b4, bb}; res_ok <= okb; res_above <= aboveb;
    end

assign sel=res_b[3:0];assign above=res_above;assign quota=0;assign date=res_b[7:4];assign valid=res_ok;
endmodule
module cut_r1 #(parameter integer QW=11)(input wire clk,input wire [335:0] u,input wire [QW-1:0] q,input wire [20:0] acc,input wire [3:0] tag,output wire [3:0] sel,output wire [20:0] above,output wire [QW-1:0] quota,output wire [3:0] date,output wire valid);
localparam integer XW=21;
integer i,ia,ib;
wire [335:0] u3_r=u;wire [QW-1:0] q_b3=q;wire [20:0] acc_b3=acc;wire [3:0] g_b3=tag;reg [7:0] res_b;reg [20:0] res_above;reg res_ok;
    reg [15:0]      geb;
    reg [16*XW-1:0] u4_r;
    reg [XW-1:0]    acc_b4;
    reg [3:0]       g_b4;
    always @(posedge clk) begin
        for (ib = 0; ib < 16; ib = ib + 1) geb[ib] <= (u3_r[XW*ib +: XW] >= {{(XW-QW){1'b0}}, q_b3});
        u4_r <= u3_r; acc_b4 <= acc_b3; g_b4 <= g_b3;
    end
    reg [3:0]    bb;
    reg          okb;
    wire [XW-1:0] aboveb;
    always @(*) begin
        bb = 4'd0; okb = 1'b0;
        for (i = 0; i < 16; i = i + 1)
            if (geb[i]) begin bb = i[3:0]; okb = 1'b1; end
    end
    // Opt-in R1: constant-index highest-one mask, balanced returning-count select.
    wire [15:0] gh;
    wire gz = ~|geb[15:1];
    generate for (genvar bk = 0; bk < 16; bk = bk + 1) begin : g_select_highest
        if (bk == 15) begin : g_top
            assign gh[bk] = geb[bk];
        end else begin : g_other
            assign gh[bk] = geb[bk] & ~|geb[15:bk+1];
        end
    end endgenerate
    wire [XW-1:0] ab_t [0:15];
    generate for (genvar bk = 0; bk < 16; bk = bk + 1) begin : g_select_above
        if (bk == 15) begin : g_top
            assign ab_t[bk] = {XW{gh[bk]}} & acc_b4;
        end else if (bk == 0) begin : g_zero
            assign ab_t[bk] = {XW{gz}} & u4_r[XW +: XW];
        end else begin : g_other
            assign ab_t[bk] = {XW{gh[bk]}} & u4_r[XW*(bk+1) +: XW];
        end
    end endgenerate
    assign aboveb = ((ab_t[0] | ab_t[1]) | (ab_t[2] | ab_t[3]))
                  | ((ab_t[4] | ab_t[5]) | (ab_t[6] | ab_t[7]))
                  | ((ab_t[8] | ab_t[9]) | (ab_t[10] | ab_t[11]))
                  | ((ab_t[12] | ab_t[13]) | (ab_t[14] | ab_t[15]));
    always @(posedge clk) begin
        res_b <= {g_b4, bb}; res_ok <= okb; res_above <= aboveb;
    end

assign sel=res_b[3:0];assign above=res_above;assign quota=0;assign date=res_b[7:4];assign valid=res_ok;
endmodule
module cut_r2 #(parameter integer QW=11)(input wire clk,input wire [335:0] u,input wire [QW-1:0] q,input wire [20:0] acc,input wire [3:0] tag,output wire [3:0] sel,output wire [20:0] above,output wire [QW-1:0] quota,output wire [3:0] date,output wire valid);
localparam integer XW=21;
integer i,ia,ib;
wire [335:0] u3_r=u;wire [QW-1:0] q_b3=q;wire [20:0] acc_b3=acc;wire [3:0] g_b3=tag;reg [7:0] res_b;reg [20:0] res_above;reg res_ok;
    reg [15:0]      geb;
    reg [16*XW-1:0] u4_r;
    reg [XW-1:0]    acc_b4;
    reg [3:0]       g_b4;
    always @(posedge clk) begin
        for (ib = 0; ib < 16; ib = ib + 1) geb[ib] <= (u3_r[XW*ib +: XW] >= {{(XW-QW){1'b0}}, q_b3});
        u4_r <= u3_r; acc_b4 <= acc_b3; g_b4 <= g_b3;
    end
    reg [3:0]    bb;
    reg          okb;
    wire [XW-1:0] aboveb;
    always @(*) begin
        bb = 4'd0; okb = 1'b0;
        for (i = 0; i < 16; i = i + 1)
            if (geb[i]) begin bb = i[3:0]; okb = 1'b1; end
    end
    // Opt-in R2: register the NEXT compare mask on the same edge as geb.
    wire [15:0] geb_nx;
    generate for (genvar bk = 0; bk < 16; bk = bk + 1) begin : g_select_compare_next
        assign geb_nx[bk] = u3_r[XW*bk +: XW] >= {{(XW-QW){1'b0}}, q_b3};
    end endgenerate
    reg [15:0] gh;
    reg gz;
    // BEGIN registered selector -- mutant changes only this block to stale geb
    generate for (genvar bk = 0; bk < 16; bk = bk + 1) begin : g_select_highest
        if (bk == 15) begin : g_top
            always @(posedge clk) gh[bk] <= geb_nx[bk];
        end else begin : g_other
            always @(posedge clk) gh[bk] <= geb_nx[bk] & ~|geb_nx[15:bk+1];
        end
    end endgenerate
    always @(posedge clk) gz <= ~|geb_nx[15:1];
    // END registered selector
    wire [XW-1:0] ab_t [0:15];
    generate for (genvar bk = 0; bk < 16; bk = bk + 1) begin : g_select_above
        if (bk == 15) begin : g_top
            assign ab_t[bk] = {XW{gh[bk]}} & acc_b4;
        end else if (bk == 0) begin : g_zero
            assign ab_t[bk] = {XW{gz}} & u4_r[XW +: XW];
        end else begin : g_other
            assign ab_t[bk] = {XW{gh[bk]}} & u4_r[XW*(bk+1) +: XW];
        end
    end endgenerate
    assign aboveb = ((ab_t[0] | ab_t[1]) | (ab_t[2] | ab_t[3]))
                  | ((ab_t[4] | ab_t[5]) | (ab_t[6] | ab_t[7]))
                  | ((ab_t[8] | ab_t[9]) | (ab_t[10] | ab_t[11]))
                  | ((ab_t[12] | ab_t[13]) | (ab_t[14] | ab_t[15]));
    always @(posedge clk) begin
        res_b <= {g_b4, bb}; res_ok <= okb; res_above <= aboveb;
    end

assign sel=res_b[3:0];assign above=res_above;assign quota=0;assign date=res_b[7:4];assign valid=res_ok;
endmodule
module cut_mut #(parameter integer QW=11)(input wire clk,input wire [335:0] u,input wire [QW-1:0] q,input wire [20:0] acc,input wire [3:0] tag,output wire [3:0] sel,output wire [20:0] above,output wire [QW-1:0] quota,output wire [3:0] date,output wire valid);
localparam integer XW=21;
integer i,ia,ib;
wire [335:0] u3_r=u;wire [QW-1:0] q_b3=q;wire [20:0] acc_b3=acc;wire [3:0] g_b3=tag;reg [7:0] res_b;reg [20:0] res_above;reg res_ok;
    reg [15:0]      geb;
    reg [16*XW-1:0] u4_r;
    reg [XW-1:0]    acc_b4;
    reg [3:0]       g_b4;
    always @(posedge clk) begin
        for (ib = 0; ib < 16; ib = ib + 1) geb[ib] <= (u3_r[XW*ib +: XW] >= {{(XW-QW){1'b0}}, q_b3});
        u4_r <= u3_r; acc_b4 <= acc_b3; g_b4 <= g_b3;
    end
    reg [3:0]    bb;
    reg          okb;
    wire [XW-1:0] aboveb;
    always @(*) begin
        bb = 4'd0; okb = 1'b0;
        for (i = 0; i < 16; i = i + 1)
            if (geb[i]) begin bb = i[3:0]; okb = 1'b1; end
    end
    // Opt-in R2: register the NEXT compare mask on the same edge as geb.
    wire [15:0] geb_nx;
    generate for (genvar bk = 0; bk < 16; bk = bk + 1) begin : g_select_compare_next
        assign geb_nx[bk] = u3_r[XW*bk +: XW] >= {{(XW-QW){1'b0}}, q_b3};
    end endgenerate
    reg [15:0] gh;
    reg gz;
    // BEGIN registered selector -- mutant changes only this block to stale geb
    generate for (genvar bk = 0; bk < 16; bk = bk + 1) begin : g_select_highest
        if (bk == 15) begin : g_top
            always @(posedge clk) gh[bk] <= geb[bk];
        end else begin : g_other
            always @(posedge clk) gh[bk] <= geb[bk] & ~|geb[15:bk+1];
        end
    end endgenerate
    always @(posedge clk) gz <= ~|geb[15:1];
    // END registered selector
    wire [XW-1:0] ab_t [0:15];
    generate for (genvar bk = 0; bk < 16; bk = bk + 1) begin : g_select_above
        if (bk == 15) begin : g_top
            assign ab_t[bk] = {XW{gh[bk]}} & acc_b4;
        end else if (bk == 0) begin : g_zero
            assign ab_t[bk] = {XW{gz}} & u4_r[XW +: XW];
        end else begin : g_other
            assign ab_t[bk] = {XW{gh[bk]}} & u4_r[XW*(bk+1) +: XW];
        end
    end endgenerate
    assign aboveb = ((ab_t[0] | ab_t[1]) | (ab_t[2] | ab_t[3]))
                  | ((ab_t[4] | ab_t[5]) | (ab_t[6] | ab_t[7]))
                  | ((ab_t[8] | ab_t[9]) | (ab_t[10] | ab_t[11]))
                  | ((ab_t[12] | ab_t[13]) | (ab_t[14] | ab_t[15]));
    always @(posedge clk) begin
        res_b <= {g_b4, bb}; res_ok <= okb; res_above <= aboveb;
    end

assign sel=res_b[3:0];assign above=res_above;assign quota=0;assign date=res_b[7:4];assign valid=res_ok;
endmodule
