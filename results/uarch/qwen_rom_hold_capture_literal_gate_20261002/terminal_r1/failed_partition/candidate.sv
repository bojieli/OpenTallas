module qwen_optin_capture_logic #(
 parameter integer W=16,AW=24,TG=4,CODE_BANKS=5,MEM_EXTRA=1,ROM_HOLD_DIRECT_CAPTURE=0
)(input wire clk,rst_n,wrom_re,input wire [AW-1:0] wrom_addr,
 input wire [2*CODE_BANKS*266-1:0] rom_rd,
 output wire [2*W*8*TG/2-1:0] wrom_q,
 output wire [CODE_BANKS-1:0] rom_ce,output wire [11:0] rom_addr,
 output wire [4:0] f_q,f_q2,output wire f_s,
 output wire [79:0] f_mask,output wire [2559:0] f_cap);
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

assign f_q=code_sel_q; assign f_q2=code_sel_q2; assign f_s=code_rd_q;
generate if (ROM_HOLD_DIRECT_CAPTURE != 0) begin
assign f_cap[0 +: 256]=g_pair[0].g_bank[0].g_cap.g_direct.cap;
assign f_mask[0]=g_pair[0].g_bank[0].g_cap.g_direct.g_mask[0].local_sel;
assign f_mask[1]=g_pair[0].g_bank[0].g_cap.g_direct.g_mask[1].local_sel;
assign f_mask[2]=g_pair[0].g_bank[0].g_cap.g_direct.g_mask[2].local_sel;
assign f_mask[3]=g_pair[0].g_bank[0].g_cap.g_direct.g_mask[3].local_sel;
assign f_mask[4]=g_pair[0].g_bank[0].g_cap.g_direct.g_mask[4].local_sel;
assign f_mask[5]=g_pair[0].g_bank[0].g_cap.g_direct.g_mask[5].local_sel;
assign f_mask[6]=g_pair[0].g_bank[0].g_cap.g_direct.g_mask[6].local_sel;
assign f_mask[7]=g_pair[0].g_bank[0].g_cap.g_direct.g_mask[7].local_sel;
end else begin
assign f_cap[0 +: 256]=g_pair[0].g_bank[0].g_cap.g_original.cap;
assign f_mask[0]=code_sel_q2[0];
assign f_mask[1]=code_sel_q2[0];
assign f_mask[2]=code_sel_q2[0];
assign f_mask[3]=code_sel_q2[0];
assign f_mask[4]=code_sel_q2[0];
assign f_mask[5]=code_sel_q2[0];
assign f_mask[6]=code_sel_q2[0];
assign f_mask[7]=code_sel_q2[0];
end endgenerate
generate if (ROM_HOLD_DIRECT_CAPTURE != 0) begin
assign f_cap[256 +: 256]=g_pair[0].g_bank[1].g_cap.g_direct.cap;
assign f_mask[8]=g_pair[0].g_bank[1].g_cap.g_direct.g_mask[0].local_sel;
assign f_mask[9]=g_pair[0].g_bank[1].g_cap.g_direct.g_mask[1].local_sel;
assign f_mask[10]=g_pair[0].g_bank[1].g_cap.g_direct.g_mask[2].local_sel;
assign f_mask[11]=g_pair[0].g_bank[1].g_cap.g_direct.g_mask[3].local_sel;
assign f_mask[12]=g_pair[0].g_bank[1].g_cap.g_direct.g_mask[4].local_sel;
assign f_mask[13]=g_pair[0].g_bank[1].g_cap.g_direct.g_mask[5].local_sel;
assign f_mask[14]=g_pair[0].g_bank[1].g_cap.g_direct.g_mask[6].local_sel;
assign f_mask[15]=g_pair[0].g_bank[1].g_cap.g_direct.g_mask[7].local_sel;
end else begin
assign f_cap[256 +: 256]=g_pair[0].g_bank[1].g_cap.g_original.cap;
assign f_mask[8]=code_sel_q2[1];
assign f_mask[9]=code_sel_q2[1];
assign f_mask[10]=code_sel_q2[1];
assign f_mask[11]=code_sel_q2[1];
assign f_mask[12]=code_sel_q2[1];
assign f_mask[13]=code_sel_q2[1];
assign f_mask[14]=code_sel_q2[1];
assign f_mask[15]=code_sel_q2[1];
end endgenerate
generate if (ROM_HOLD_DIRECT_CAPTURE != 0) begin
assign f_cap[512 +: 256]=g_pair[0].g_bank[2].g_cap.g_direct.cap;
assign f_mask[16]=g_pair[0].g_bank[2].g_cap.g_direct.g_mask[0].local_sel;
assign f_mask[17]=g_pair[0].g_bank[2].g_cap.g_direct.g_mask[1].local_sel;
assign f_mask[18]=g_pair[0].g_bank[2].g_cap.g_direct.g_mask[2].local_sel;
assign f_mask[19]=g_pair[0].g_bank[2].g_cap.g_direct.g_mask[3].local_sel;
assign f_mask[20]=g_pair[0].g_bank[2].g_cap.g_direct.g_mask[4].local_sel;
assign f_mask[21]=g_pair[0].g_bank[2].g_cap.g_direct.g_mask[5].local_sel;
assign f_mask[22]=g_pair[0].g_bank[2].g_cap.g_direct.g_mask[6].local_sel;
assign f_mask[23]=g_pair[0].g_bank[2].g_cap.g_direct.g_mask[7].local_sel;
end else begin
assign f_cap[512 +: 256]=g_pair[0].g_bank[2].g_cap.g_original.cap;
assign f_mask[16]=code_sel_q2[2];
assign f_mask[17]=code_sel_q2[2];
assign f_mask[18]=code_sel_q2[2];
assign f_mask[19]=code_sel_q2[2];
assign f_mask[20]=code_sel_q2[2];
assign f_mask[21]=code_sel_q2[2];
assign f_mask[22]=code_sel_q2[2];
assign f_mask[23]=code_sel_q2[2];
end endgenerate
generate if (ROM_HOLD_DIRECT_CAPTURE != 0) begin
assign f_cap[768 +: 256]=g_pair[0].g_bank[3].g_cap.g_direct.cap;
assign f_mask[24]=g_pair[0].g_bank[3].g_cap.g_direct.g_mask[0].local_sel;
assign f_mask[25]=g_pair[0].g_bank[3].g_cap.g_direct.g_mask[1].local_sel;
assign f_mask[26]=g_pair[0].g_bank[3].g_cap.g_direct.g_mask[2].local_sel;
assign f_mask[27]=g_pair[0].g_bank[3].g_cap.g_direct.g_mask[3].local_sel;
assign f_mask[28]=g_pair[0].g_bank[3].g_cap.g_direct.g_mask[4].local_sel;
assign f_mask[29]=g_pair[0].g_bank[3].g_cap.g_direct.g_mask[5].local_sel;
assign f_mask[30]=g_pair[0].g_bank[3].g_cap.g_direct.g_mask[6].local_sel;
assign f_mask[31]=g_pair[0].g_bank[3].g_cap.g_direct.g_mask[7].local_sel;
end else begin
assign f_cap[768 +: 256]=g_pair[0].g_bank[3].g_cap.g_original.cap;
assign f_mask[24]=code_sel_q2[3];
assign f_mask[25]=code_sel_q2[3];
assign f_mask[26]=code_sel_q2[3];
assign f_mask[27]=code_sel_q2[3];
assign f_mask[28]=code_sel_q2[3];
assign f_mask[29]=code_sel_q2[3];
assign f_mask[30]=code_sel_q2[3];
assign f_mask[31]=code_sel_q2[3];
end endgenerate
generate if (ROM_HOLD_DIRECT_CAPTURE != 0) begin
assign f_cap[1024 +: 256]=g_pair[0].g_bank[4].g_cap.g_direct.cap;
assign f_mask[32]=g_pair[0].g_bank[4].g_cap.g_direct.g_mask[0].local_sel;
assign f_mask[33]=g_pair[0].g_bank[4].g_cap.g_direct.g_mask[1].local_sel;
assign f_mask[34]=g_pair[0].g_bank[4].g_cap.g_direct.g_mask[2].local_sel;
assign f_mask[35]=g_pair[0].g_bank[4].g_cap.g_direct.g_mask[3].local_sel;
assign f_mask[36]=g_pair[0].g_bank[4].g_cap.g_direct.g_mask[4].local_sel;
assign f_mask[37]=g_pair[0].g_bank[4].g_cap.g_direct.g_mask[5].local_sel;
assign f_mask[38]=g_pair[0].g_bank[4].g_cap.g_direct.g_mask[6].local_sel;
assign f_mask[39]=g_pair[0].g_bank[4].g_cap.g_direct.g_mask[7].local_sel;
end else begin
assign f_cap[1024 +: 256]=g_pair[0].g_bank[4].g_cap.g_original.cap;
assign f_mask[32]=code_sel_q2[4];
assign f_mask[33]=code_sel_q2[4];
assign f_mask[34]=code_sel_q2[4];
assign f_mask[35]=code_sel_q2[4];
assign f_mask[36]=code_sel_q2[4];
assign f_mask[37]=code_sel_q2[4];
assign f_mask[38]=code_sel_q2[4];
assign f_mask[39]=code_sel_q2[4];
end endgenerate
generate if (ROM_HOLD_DIRECT_CAPTURE != 0) begin
assign f_cap[1280 +: 256]=g_pair[1].g_bank[0].g_cap.g_direct.cap;
assign f_mask[40]=g_pair[1].g_bank[0].g_cap.g_direct.g_mask[0].local_sel;
assign f_mask[41]=g_pair[1].g_bank[0].g_cap.g_direct.g_mask[1].local_sel;
assign f_mask[42]=g_pair[1].g_bank[0].g_cap.g_direct.g_mask[2].local_sel;
assign f_mask[43]=g_pair[1].g_bank[0].g_cap.g_direct.g_mask[3].local_sel;
assign f_mask[44]=g_pair[1].g_bank[0].g_cap.g_direct.g_mask[4].local_sel;
assign f_mask[45]=g_pair[1].g_bank[0].g_cap.g_direct.g_mask[5].local_sel;
assign f_mask[46]=g_pair[1].g_bank[0].g_cap.g_direct.g_mask[6].local_sel;
assign f_mask[47]=g_pair[1].g_bank[0].g_cap.g_direct.g_mask[7].local_sel;
end else begin
assign f_cap[1280 +: 256]=g_pair[1].g_bank[0].g_cap.g_original.cap;
assign f_mask[40]=code_sel_q2[0];
assign f_mask[41]=code_sel_q2[0];
assign f_mask[42]=code_sel_q2[0];
assign f_mask[43]=code_sel_q2[0];
assign f_mask[44]=code_sel_q2[0];
assign f_mask[45]=code_sel_q2[0];
assign f_mask[46]=code_sel_q2[0];
assign f_mask[47]=code_sel_q2[0];
end endgenerate
generate if (ROM_HOLD_DIRECT_CAPTURE != 0) begin
assign f_cap[1536 +: 256]=g_pair[1].g_bank[1].g_cap.g_direct.cap;
assign f_mask[48]=g_pair[1].g_bank[1].g_cap.g_direct.g_mask[0].local_sel;
assign f_mask[49]=g_pair[1].g_bank[1].g_cap.g_direct.g_mask[1].local_sel;
assign f_mask[50]=g_pair[1].g_bank[1].g_cap.g_direct.g_mask[2].local_sel;
assign f_mask[51]=g_pair[1].g_bank[1].g_cap.g_direct.g_mask[3].local_sel;
assign f_mask[52]=g_pair[1].g_bank[1].g_cap.g_direct.g_mask[4].local_sel;
assign f_mask[53]=g_pair[1].g_bank[1].g_cap.g_direct.g_mask[5].local_sel;
assign f_mask[54]=g_pair[1].g_bank[1].g_cap.g_direct.g_mask[6].local_sel;
assign f_mask[55]=g_pair[1].g_bank[1].g_cap.g_direct.g_mask[7].local_sel;
end else begin
assign f_cap[1536 +: 256]=g_pair[1].g_bank[1].g_cap.g_original.cap;
assign f_mask[48]=code_sel_q2[1];
assign f_mask[49]=code_sel_q2[1];
assign f_mask[50]=code_sel_q2[1];
assign f_mask[51]=code_sel_q2[1];
assign f_mask[52]=code_sel_q2[1];
assign f_mask[53]=code_sel_q2[1];
assign f_mask[54]=code_sel_q2[1];
assign f_mask[55]=code_sel_q2[1];
end endgenerate
generate if (ROM_HOLD_DIRECT_CAPTURE != 0) begin
assign f_cap[1792 +: 256]=g_pair[1].g_bank[2].g_cap.g_direct.cap;
assign f_mask[56]=g_pair[1].g_bank[2].g_cap.g_direct.g_mask[0].local_sel;
assign f_mask[57]=g_pair[1].g_bank[2].g_cap.g_direct.g_mask[1].local_sel;
assign f_mask[58]=g_pair[1].g_bank[2].g_cap.g_direct.g_mask[2].local_sel;
assign f_mask[59]=g_pair[1].g_bank[2].g_cap.g_direct.g_mask[3].local_sel;
assign f_mask[60]=g_pair[1].g_bank[2].g_cap.g_direct.g_mask[4].local_sel;
assign f_mask[61]=g_pair[1].g_bank[2].g_cap.g_direct.g_mask[5].local_sel;
assign f_mask[62]=g_pair[1].g_bank[2].g_cap.g_direct.g_mask[6].local_sel;
assign f_mask[63]=g_pair[1].g_bank[2].g_cap.g_direct.g_mask[7].local_sel;
end else begin
assign f_cap[1792 +: 256]=g_pair[1].g_bank[2].g_cap.g_original.cap;
assign f_mask[56]=code_sel_q2[2];
assign f_mask[57]=code_sel_q2[2];
assign f_mask[58]=code_sel_q2[2];
assign f_mask[59]=code_sel_q2[2];
assign f_mask[60]=code_sel_q2[2];
assign f_mask[61]=code_sel_q2[2];
assign f_mask[62]=code_sel_q2[2];
assign f_mask[63]=code_sel_q2[2];
end endgenerate
generate if (ROM_HOLD_DIRECT_CAPTURE != 0) begin
assign f_cap[2048 +: 256]=g_pair[1].g_bank[3].g_cap.g_direct.cap;
assign f_mask[64]=g_pair[1].g_bank[3].g_cap.g_direct.g_mask[0].local_sel;
assign f_mask[65]=g_pair[1].g_bank[3].g_cap.g_direct.g_mask[1].local_sel;
assign f_mask[66]=g_pair[1].g_bank[3].g_cap.g_direct.g_mask[2].local_sel;
assign f_mask[67]=g_pair[1].g_bank[3].g_cap.g_direct.g_mask[3].local_sel;
assign f_mask[68]=g_pair[1].g_bank[3].g_cap.g_direct.g_mask[4].local_sel;
assign f_mask[69]=g_pair[1].g_bank[3].g_cap.g_direct.g_mask[5].local_sel;
assign f_mask[70]=g_pair[1].g_bank[3].g_cap.g_direct.g_mask[6].local_sel;
assign f_mask[71]=g_pair[1].g_bank[3].g_cap.g_direct.g_mask[7].local_sel;
end else begin
assign f_cap[2048 +: 256]=g_pair[1].g_bank[3].g_cap.g_original.cap;
assign f_mask[64]=code_sel_q2[3];
assign f_mask[65]=code_sel_q2[3];
assign f_mask[66]=code_sel_q2[3];
assign f_mask[67]=code_sel_q2[3];
assign f_mask[68]=code_sel_q2[3];
assign f_mask[69]=code_sel_q2[3];
assign f_mask[70]=code_sel_q2[3];
assign f_mask[71]=code_sel_q2[3];
end endgenerate
generate if (ROM_HOLD_DIRECT_CAPTURE != 0) begin
assign f_cap[2304 +: 256]=g_pair[1].g_bank[4].g_cap.g_direct.cap;
assign f_mask[72]=g_pair[1].g_bank[4].g_cap.g_direct.g_mask[0].local_sel;
assign f_mask[73]=g_pair[1].g_bank[4].g_cap.g_direct.g_mask[1].local_sel;
assign f_mask[74]=g_pair[1].g_bank[4].g_cap.g_direct.g_mask[2].local_sel;
assign f_mask[75]=g_pair[1].g_bank[4].g_cap.g_direct.g_mask[3].local_sel;
assign f_mask[76]=g_pair[1].g_bank[4].g_cap.g_direct.g_mask[4].local_sel;
assign f_mask[77]=g_pair[1].g_bank[4].g_cap.g_direct.g_mask[5].local_sel;
assign f_mask[78]=g_pair[1].g_bank[4].g_cap.g_direct.g_mask[6].local_sel;
assign f_mask[79]=g_pair[1].g_bank[4].g_cap.g_direct.g_mask[7].local_sel;
end else begin
assign f_cap[2304 +: 256]=g_pair[1].g_bank[4].g_cap.g_original.cap;
assign f_mask[72]=code_sel_q2[4];
assign f_mask[73]=code_sel_q2[4];
assign f_mask[74]=code_sel_q2[4];
assign f_mask[75]=code_sel_q2[4];
assign f_mask[76]=code_sel_q2[4];
assign f_mask[77]=code_sel_q2[4];
assign f_mask[78]=code_sel_q2[4];
assign f_mask[79]=code_sel_q2[4];
end endgenerate
endmodule
