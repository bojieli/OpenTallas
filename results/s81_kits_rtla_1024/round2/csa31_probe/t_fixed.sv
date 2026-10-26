module t(input wire [30:0] a, input wire [30:0] b, output wire [30:0] y);
    function automatic [30:0] csa31(input [30:0] a, input [30:0] b);
        reg [31:0] ax, bx, r; reg [8:0] z, o; reg c; integer k;
        begin
            ax = {1'b0, a}; bx = {1'b0, b}; r = 32'd0; c = 1'b0;
            for (k = 0; k < 4; k = k + 1) begin
                z = {1'b0, ax[8*k +: 8]} + {1'b0, bx[8*k +: 8]};
                o = {1'b0, ax[8*k +: 8]} + {1'b0, bx[8*k +: 8]} + 9'd1;
                r[8*k +: 8] = c ? o[7:0] : z[7:0];
                c = c ? o[8] : z[8];
            end
            csa31 = r[30:0];
        end
    endfunction
    assign y = csa31(a, b);
endmodule
