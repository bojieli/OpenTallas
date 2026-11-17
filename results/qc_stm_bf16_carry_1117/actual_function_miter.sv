module gold(input[31:0] b,output[15:0] y);localparam MUT=0;
    function automatic [15:0] bf16(input [31:0] b);
        reg [32:0] r;
        begin
            r = {1'b0, b} + 33'h7FFF + {32'd0, b[16]};
            bf16 = (MUT == 2) ? b[31:16] : r[31:16];
        end
    endfunction
assign y=bf16(b);endmodule
module candidate(input[31:0] b,output[15:0] y);localparam MUT=0;
    function automatic [15:0] bf16(input [31:0] b);
`ifdef OT_QFD_BF16_CARRY
        reg round_up;
        reg [15:0] inc;
        begin
            round_up = b[15] && (b[16] || (|b[14:0]));
            inc[0] = round_up;
            inc[1] = round_up && (&b[16:16]);
            inc[2] = round_up && (&b[17:16]);
            inc[3] = round_up && (&b[18:16]);
            inc[4] = round_up && (&b[19:16]);
            inc[5] = round_up && (&b[20:16]);
            inc[6] = round_up && (&b[21:16]);
            inc[7] = round_up && (&b[22:16]);
            inc[8] = round_up && (&b[23:16]);
            inc[9] = round_up && (&b[24:16]);
            inc[10] = round_up && (&b[25:16]);
            inc[11] = round_up && (&b[26:16]);
            inc[12] = round_up && (&b[27:16]);
            inc[13] = round_up && (&b[28:16]);
            inc[14] = round_up && (&b[29:16]);
            inc[15] = round_up && (&b[30:16]);
            bf16 = (MUT == 2) ? b[31:16] : (b[31:16] ^ inc);
        end
`else
        reg [32:0] r;
        begin
            r = {1'b0, b} + 33'h7FFF + {32'd0, b[16]};
            bf16 = (MUT == 2) ? b[31:16] : r[31:16];
        end
`endif
    endfunction
assign y=bf16(b);endmodule
module mutant(input[31:0] b,output[15:0] y);localparam MUT=0;
    function automatic [15:0] bf16(input [31:0] b);
`ifdef OT_QFD_BF16_CARRY
        reg round_up;
        reg [15:0] inc;
        begin
            round_up = b[15];
            inc[0] = round_up;
            inc[1] = round_up && (&b[16:16]);
            inc[2] = round_up && (&b[17:16]);
            inc[3] = round_up && (&b[18:16]);
            inc[4] = round_up && (&b[19:16]);
            inc[5] = round_up && (&b[20:16]);
            inc[6] = round_up && (&b[21:16]);
            inc[7] = round_up && (&b[22:16]);
            inc[8] = round_up && (&b[23:16]);
            inc[9] = round_up && (&b[24:16]);
            inc[10] = round_up && (&b[25:16]);
            inc[11] = round_up && (&b[26:16]);
            inc[12] = round_up && (&b[27:16]);
            inc[13] = round_up && (&b[28:16]);
            inc[14] = round_up && (&b[29:16]);
            inc[15] = round_up && (&b[30:16]);
            bf16 = (MUT == 2) ? b[31:16] : (b[31:16] ^ inc);
        end
`else
        reg [32:0] r;
        begin
            r = {1'b0, b} + 33'h7FFF + {32'd0, b[16]};
            bf16 = (MUT == 2) ? b[31:16] : r[31:16];
        end
`endif
    endfunction
assign y=bf16(b);endmodule
module actual_miter(input[31:0] b,output ok,output mutant_ok);wire[15:0] g,c,m;gold a(b,g);candidate d(b,c);mutant e(b,m);assign ok=(g==c);assign mutant_ok=(g==m);endmodule
