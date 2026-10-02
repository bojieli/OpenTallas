module qwen_loaded_capture #(
 parameter integer W=16,AW=24,TG=4,CODE_BANKS=5,MEM_EXTRA=1,ROM_HOLD_DIRECT_CAPTURE=1
)(input wire clk,rst_n,wrom_re,input wire [AW-1:0] wrom_addr,

 output wire [2*W*8*TG/2-1:0] wrom_q,
 output wire [CODE_BANKS-1:0] rom_ce,output wire [11:0] rom_addr,output reg [511:0] consumer_q);
 wire [2*CODE_BANKS*266-1:0] rom_rd;
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
    generate if (ROM_HOLD_DIRECT_CAPTURE != 0 &&
        (W != 16 || TG != 4 || CODE_BANKS != 5 || MEM_EXTRA != 1)) begin : g_unpriced_shape
        initial $error("ROM_HOLD_DIRECT_CAPTURE requires Maxwell-priced W16/TG4/CB5/MEM_EXTRA1");
    end endgenerate
    localparam integer PWB = 2 * W * 8;      // a group pair's slice of the code word (256 of the macro's 266 bits)
    generate
        for (p = 0; p < TG / 2; p = p + 1) begin : g_pair
            wire [PWB-1:0] or_q [0:CODE_BANKS];
            assign or_q[0] = {PWB{1'b0}};
            for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_bank
                wire [PWB-1:0] rd = rom_rd[(p*CODE_BANKS + b)*266 +: PWB];
                if (MEM_EXTRA != 0) begin : g_cap
                    if (ROM_HOLD_DIRECT_CAPTURE != 0) begin : g_direct
                        // CE-idle holds rd in the source ROM. Observability is
                        // still qualified by identical delayed bank metadata.
                        reg [PWB-1:0] cap;
                        always @(posedge clk) cap <= rd;
                        genvar chunk;
                        for (chunk = 0; chunk < PWB / 32; chunk = chunk + 1) begin : g_mask
                            // Eight32-bit chunks per column,16 per bank:
                            // exactly80 reset/hold selectorFFs. Keep replicas
                            // for physical locality; mapped preservation gates.
                            (* keep = 1, dont_touch = 1 *) reg local_sel;
                            always @(posedge clk or negedge rst_n) begin
                                if (!rst_n) local_sel <= 1'b0;
                                else if (code_rd_q) local_sel <= code_sel_q[b];
                            end
                            assign or_q[b+1][32*chunk +: 32] = or_q[b][32*chunk +: 32] |
                                (cap[32*chunk +: 32] & {32{local_sel}});
                        end
                    end else begin : g_original
                        // Original source behavior, defaultoff.
                        reg [PWB-1:0] cap;
                        always @(posedge clk) if (code_sel_q[b] && code_rd_q) cap <= rd;
                        assign or_q[b+1] = or_q[b] | (cap & {PWB{code_sel_q2[b]}});
                    end
                end else begin : g_nocap
                    assign or_q[b+1] = or_q[b] | (rd & {PWB{code_sel_q[b]}});
                end
            end
            assign wrom_q[PWB*p +: PWB] = or_q[CODE_BANKS];
        end
    endgenerate

    generate
        for (p = 0; p < 2; p = p + 1) begin : g_col
            for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_bank
                ot_rom_4096x266_m8 u_rom (.clk(clk), .ce_in(rom_ce[b]), .addr_in(rom_addr),
                                          .rd_out(rom_rd[(p*CODE_BANKS + b)*266 +: 266]));
            end
        end
    endgenerate
always @(posedge clk) consumer_q <= wrom_q;
endmodule
