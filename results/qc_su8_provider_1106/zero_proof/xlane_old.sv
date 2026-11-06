(* keep_hierarchy = "yes" *) module xlane_old #(parameter integer K = 0) (
    input wire ck, input wire [15:0] sel, input wire [95:0] xin, output reg [95:0] q);
    wire [95:0] m;
    genvar f;
    generate for (f = 0; f < 4; f = f + 1) begin : g_f
        qfd_dv_su8_stride #(.K(K)) u_off (.x(xin[24*f +: 24]), .y(m[24*f +: 24]));
    end endgenerate
    integer c;
    always @(posedge ck)
        for (c = 0; c < 16; c = c + 1) if (sel[c]) q[6*c +: 6] <= m[6*c +: 6];
endmodule
