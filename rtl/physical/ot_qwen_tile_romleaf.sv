`timescale 1ns/1ps
// Single actual 4096x266 ROM, capture and exact BF16 expansion pipeline.
// Request and output pins terminate in the original registers: zero added edges.
module ot_qwen_tile_romleaf
`ifndef SYNTHESIS
 #(parameter integer ROM_TILE=-1, ROM_BANK=-1, ROM_COL=-1)
`endif
(input wire clk,rst_n,ce_d,any_d,input wire [11:0] ad_d,output wire [511:0] r_q);
 wire [12:0] req_m;
 wire [265:0] rd;
 ot_qwen_romleaf_logic u_lg (.clk(clk),.rst_n(rst_n),.ce_d(ce_d),.any_d(any_d),.ad_d(ad_d),.req_m(req_m),.rd(rd[255:0]),.r_q(r_q));
 ot_rom_4096x266_m8
`ifndef SYNTHESIS
 #(.INSTANCE(ROM_TILE<0 ? "" : $sformatf("qtile_t%0d_b%0d_c%0d",ROM_TILE,ROM_BANK,ROM_COL)))
`endif
 u_rom (.clk(clk),.ce_in(req_m[12]),.addr_in(req_m[11:0]),.rd_out(rd));
`ifndef SYNTHESIS
 string image_dir,image_file;
 integer image_fd;
 initial begin
  if ($value$plusargs("OT_ROM_DIR=%s",image_dir)) begin
   if(ROM_TILE<0||ROM_TILE>=768||ROM_BANK<0||ROM_BANK>=5||ROM_COL<0||ROM_COL>=2) $fatal(1,"invalid ROMleaf binding");
   image_file=$sformatf("%s/qtile_t%0d_b%0d_c%0d.viamap.hex",image_dir,ROM_TILE,ROM_BANK,ROM_COL);
   image_fd=$fopen(image_file,"r"); if(image_fd==0) $fatal(1,"missing ROMleaf mask %s",image_file); $fclose(image_fd);
  end else if(ROM_TILE>=0) $fatal(1,"bound ROMleaf requires +OT_ROM_DIR");
 end
`endif
endmodule

module ot_qwen_romleaf_logic #(
    parameter integer PAIR_CLOCKS = 0,
    parameter integer PWB = 256,
    parameter integer ROM_CAP2 = 1,
    parameter integer ROM_CAPX = 2,
    parameter integer ROM_MUT = 0,
    parameter integer MUT3 = 0,
    parameter integer MUT5 = 0
) (
    input  wire               clk,
    
    input  wire               rst_n,
    input  wire               ce_d,
    input  wire               any_d,
    input  wire [11:0]        ad_d,
    output wire [12:0]        req_m,     // {column 1 {ce, addr}, column 0 {ce, addr}} to the macros
    input  wire [PWB-1:0]     rd,        // {column 1, column 0} macro words (low PWB bits)
    output wire [2*PWB-1:0]   r_q        // {pair 1, pair 0} relay word (BF16 expansion, 0 when the row is not selected)
);
    function automatic [15:0] int8_bf16(input [7:0] code);   // == ot_qwen_w12_matvec_part int8_bf16
        reg [7:0] mag, norm;
        reg [2:0] msb;
        integer bit_index;
        begin
            mag = code[7] ? (~code + 8'd1) : code;
            msb = 0;
            for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1)
                if (mag[bit_index]) msb = bit_index[2:0];
            norm = mag << (3'd7 - msb);
            int8_bf16 = (mag == 0) ? 16'd0 :
                        {code[7], (8'd127 + {5'd0, msb}), norm[6:0]};
        end
    endfunction
    function automatic [2:0] lead1(input [7:0] m);           // leading-one position (0 when m == 0)
        integer i;
        begin lead1 = 0; for (i = 0; i < 8; i = i + 1) if (m[i]) lead1 = i[2:0]; end
    endfunction
    ot_qwen_mpr_reg u_r0 (.clk(clk), .rst_n(rst_n), .d({ce_d, ad_d}), .q(req_m));
    //: the row's copy of its request enable and of "any row enabled" (== rom_ce[b], |rom_ce of the flat pipeline)
    (* keep *) reg ce_q, any_q;
    reg sel_1, sel_c, sel_c2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ce_q <= 1'b0; any_q <= 1'b0; sel_1 <= 1'b0; sel_c <= 1'b0; sel_c2 <= 1'b0; end
        else begin
            ce_q <= ce_d; any_q <= any_d;
            if (any_q) sel_1 <= ce_q;
            sel_c <= sel_1;
            sel_c2 <= sel_c;
        end
    end
    genvar p;
    generate for (p = 0; p < 1; p = p + 1) begin : g_pair
        wire pair_clk = clk;
        wire [2*PWB-1:0] cv;
        begin : g_bank
                //: the bank's output register at its pins, no enable
                (* keep *) reg [PWB-1:0] cap;
                always @(posedge pair_clk) cap <= rd[p*PWB +: PWB];
                wire [PWB-1:0] cx;                     // the word the expansion reads
                wire           sx, sx_early;           // its bank select (and the mutant's one-edge-early select)
                wire [2*PWB-1:0] cxw;                  // ROM_CAPX: the registered masked expansion
                if (ROM_CAP2 != 0 && ROM_CAPX == 2) begin : g_capx2
                    //: rung A (beside cap): sign, magnitude, leading-one position, masked nonzero, per byte
                    (* keep *) reg [PWB/8-1:0] xa_s, xa_nz;
                    (* keep *) reg [PWB-1:0]   xa_m;
                    (* keep *) reg [3*PWB/8-1:0] xa_p;
                    (* keep *) reg [2*PWB-1:0] cap2x;
                    (* keep *) reg [PWB/32-1:0] sel_r;          // the select, one kept copy per 4 bytes
                    genvar ex, er;
                    for (er = 0; er < PWB / 32; er = er + 1) begin : g_selr
                        always @(posedge pair_clk) sel_r[er] <= (ROM_MUT != 0) ? sel_1 : sel_c;
                    end
                    for (ex = 0; ex < PWB / 8; ex = ex + 1) begin : g_cvx
                        wire [7:0] cb = cap[8*ex +: 8];
                        wire [7:0] mg = cb[7] ? (~cb + 8'd1) : cb;
                        always @(posedge pair_clk) begin
                            xa_s[ex] <= cb[7];
                            xa_m[8*ex +: 8] <= mg;
                            xa_p[3*ex +: 3] <= lead1(mg);
                            xa_nz[ex] <= (mg != 8'd0);
                        end
                        //: rung B: normalising shift + exponent, masked by the select of the edge rung A holds
                        wire [7:0] nm = xa_m[8*ex +: 8] << (3'd7 - xa_p[3*ex +: 3]);
                        always @(posedge pair_clk)
                            cap2x[16*ex +: 16] <= (xa_nz[ex] && sel_r[ex / 4]) ?
                                {xa_s[ex], 8'd127 + {5'd0, xa_p[3*ex +: 3]}, nm[6:0]} : 16'd0;
                    end
                    assign cx = {PWB{1'b0}}; assign sx = 1'b0; assign sx_early = 1'b0; assign cxw = cap2x;
                end else if (ROM_CAP2 != 0 && ROM_CAPX != 0) begin : g_capx
                    //: cap2 = the masked BF16 expansion of cap (select of the edge cap holds the word: sel_c)
                    (* keep *) reg [2*PWB-1:0] cap2x;
                    genvar ex;
                    for (ex = 0; ex < PWB / 8; ex = ex + 1) begin : g_cvx
                        always @(posedge pair_clk) cap2x[16*ex +: 16] <= int8_bf16(cap[8*ex +: 8]) & {16{(ROM_MUT != 0) ? sel_1 : sel_c}};
                    end
                    assign cx = {PWB{1'b0}}; assign sx = 1'b0; assign sx_early = 1'b0; assign cxw = cap2x;
                end else if (ROM_CAP2 != 0) begin : g_cap2
                    (* keep *) reg [PWB-1:0] cap2;
                    always @(posedge pair_clk) cap2 <= cap;
                    assign cx = cap2; assign sx = sel_c2; assign sx_early = sel_c; assign cxw = {2*PWB{1'b0}};
                end else begin : g_cap1
                    assign cx = cap; assign sx = sel_c; assign sx_early = sel_1; assign cxw = {2*PWB{1'b0}};
                end
                if (ROM_CAP2 != 0 && ROM_CAPX != 0) begin : g_cvr
                    assign cv = cxw;
                end else begin : g_cvc
                    genvar e;
                    for (e = 0; e < PWB / 8; e = e + 1) begin : g_cv
                        assign cv[16*e +: 16] = int8_bf16(cx[8*e +: 8]) & {16{(ROM_MUT != 0) ? sx_early : sx}};
                    end
                end
        end
        reg [2*PWB-1:0] g, r, rx;
        always @(posedge pair_clk) begin g <= cv; r <= g; rx <= r; end
`ifdef OT_ROMLEAF_LATENCY_MUTANT
        assign r_q[2*PWB*p +: 2*PWB] = rx;
`else
        assign r_q[2*PWB*p +: 2*PWB] = (MUT5 != 0) ? rx : r;
`endif
    end endgenerate
endmodule
