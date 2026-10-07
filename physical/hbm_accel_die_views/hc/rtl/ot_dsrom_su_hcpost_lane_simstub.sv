// SIM STUB of ot_dsrom_su_hcpost_lane (connectivity bench only): out[t] = in[(13t+5) % LI] ^ in[(7t+1) % LI], registered
module ot_dsrom_su_hcpost_lane #(parameter integer ML = 0, parameter integer AL = 0) (input wire clk, input wire rst_n, input wire [0:0] v, input wire [31:0] r0, input wire [31:0] r1, input wire [31:0] r2, input wire [31:0] r3, input wire [31:0] y, input wire [31:0] c0, input wire [31:0] c1, input wire [31:0] c2, input wire [31:0] c3, input wire [31:0] p, output wire [0:0] vo, output wire [31:0] o, output wire [0:0] fault);
    wire [320:0] lin = {p, c3, c2, c1, c0, y, r3, r2, r1, r0, v};
    reg [33:0] r;
    always @(posedge clk) begin
        r[0] <= lin[5] ^ lin[1];
        r[1] <= lin[18] ^ lin[8];
        r[2] <= lin[31] ^ lin[15];
        r[3] <= lin[44] ^ lin[22];
        r[4] <= lin[57] ^ lin[29];
        r[5] <= lin[70] ^ lin[36];
        r[6] <= lin[83] ^ lin[43];
        r[7] <= lin[96] ^ lin[50];
        r[8] <= lin[109] ^ lin[57];
        r[9] <= lin[122] ^ lin[64];
        r[10] <= lin[135] ^ lin[71];
        r[11] <= lin[148] ^ lin[78];
        r[12] <= lin[161] ^ lin[85];
        r[13] <= lin[174] ^ lin[92];
        r[14] <= lin[187] ^ lin[99];
        r[15] <= lin[200] ^ lin[106];
        r[16] <= lin[213] ^ lin[113];
        r[17] <= lin[226] ^ lin[120];
        r[18] <= lin[239] ^ lin[127];
        r[19] <= lin[252] ^ lin[134];
        r[20] <= lin[265] ^ lin[141];
        r[21] <= lin[278] ^ lin[148];
        r[22] <= lin[291] ^ lin[155];
        r[23] <= lin[304] ^ lin[162];
        r[24] <= lin[317] ^ lin[169];
        r[25] <= lin[9] ^ lin[176];
        r[26] <= lin[22] ^ lin[183];
        r[27] <= lin[35] ^ lin[190];
        r[28] <= lin[48] ^ lin[197];
        r[29] <= lin[61] ^ lin[204];
        r[30] <= lin[74] ^ lin[211];
        r[31] <= lin[87] ^ lin[218];
        r[32] <= lin[100] ^ lin[225];
        r[33] <= lin[113] ^ lin[232];
    end
    assign vo = r[0:0];
    assign o = r[32:1];
    assign fault = r[33:33];
endmodule
