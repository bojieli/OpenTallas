module qwen_current_capture_logic #(
 parameter integer W=16,AW=24,TG=4,CODE_BANKS=5,MEM_EXTRA=1
)(input wire clk,rst_n,wrom_re,input wire [AW-1:0] wrom_addr,
 input wire [2*CODE_BANKS*266-1:0] rom_rd,
 output wire [2*W*8*TG/2-1:0] wrom_q,
 output wire [CODE_BANKS-1:0] rom_ce,output wire [11:0] rom_addr);
    reg  [CODE_BANKS-1:0] code_sel_q;
    genvar b, p;
    generate
        for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_ce
            assign rom_ce[b] = wrom_re && (wrom_addr[AW-1:12] == b);
        end
    endgenerate
    assign rom_addr = wrom_addr[11:0];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) code_sel_q <= {CODE_BANKS{1'b0}};
        else if (wrom_re) code_sel_q <= rom_ce;
    end
    //: MEM_EXTRA: the read strobe and bank select one more cycle, for the captured banks' OR
    reg code_rd_q;
    reg [CODE_BANKS-1:0] code_sel_q2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin code_rd_q <= 1'b0; code_sel_q2 <= {CODE_BANKS{1'b0}}; end
        else begin
            code_rd_q <= wrom_re;
            if (code_rd_q) code_sel_q2 <= code_sel_q;
        end
    end
    localparam integer PWB = 2 * W * 8;      // a group pair's slice of the code word (256 of the macro's 266 bits)
    generate
        for (p = 0; p < TG / 2; p = p + 1) begin : g_pair
            wire [PWB-1:0] or_q [0:CODE_BANKS];
            assign or_q[0] = {PWB{1'b0}};
            for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_bank
                wire [PWB-1:0] rd = rom_rd[(p*CODE_BANKS + b)*266 +: PWB];
                if (MEM_EXTRA != 0) begin : g_cap
                    //: the bank's output register at its pins: captured only when the bank was read
                    reg [PWB-1:0] cap;
                    always @(posedge clk) if (code_sel_q[b] && code_rd_q) cap <= rd;
                    assign or_q[b+1] = or_q[b] | (cap & {PWB{code_sel_q2[b]}});
                end else begin : g_nocap
                    assign or_q[b+1] = or_q[b] | (rd & {PWB{code_sel_q[b]}});
                end
            end
            assign wrom_q[PWB*p +: PWB] = or_q[CODE_BANKS];
        end
    endgenerate

endmodule
