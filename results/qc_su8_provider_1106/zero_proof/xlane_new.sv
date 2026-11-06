(* keep_hierarchy = "yes" *) module xlane_new #(parameter integer K = 0) (
    input wire ck, input wire [15:0] sel, input wire [95:0] xin, output wire [95:0] q);
    wire [95:0] m;
    genvar f;
    generate for (f = 0; f < 4; f = f + 1) begin : g_f
        qfd_dv_su8_stride #(.K(K)) u_off (.x(xin[24*f +: 24]), .y(m[24*f +: 24]));
    end endgenerate
    // Multiplication by constant K has exactzero trailingbits; only payloadbits require storage.
    genvar b;
    generate for (b = 0; b < 96; b = b + 1) begin : g_payload
        if ((K % (1 << ((b % 24) + 1))) == 0) begin : g_zero
            assign q[b] = 1'b0;
        end else begin : g_live
            reg payload;
            always @(posedge ck) if (sel[b / 6]) payload <= m[b];
            assign q[b] = payload;
        end
    end endgenerate
endmodule
