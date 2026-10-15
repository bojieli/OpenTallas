module ot_qfd_band_upper_faces #(parameter integer MUT=0) (
    input wire clk,reset_q,input wire [5:0] lnk,
    input wire [15:0] lpv,lf,
    output reg [3:0] quarter_pv,quarter_fault
);
    genvar u;
    generate for(u=0;u<4;u=u+1) begin:g_upper_face
        always @(posedge clk) begin
            quarter_pv[u] <= reset_q & lpv[4*u];
            if(!reset_q) quarter_fault[u] <= 1'b0;
            else quarter_fault[u] <= (&lnk) |
                ((MUT==1 && u==3) ? 1'b0 : (|lf[4*u +: 4])) |
                (|(lpv ^ {16{lpv[0]}}));
        end
    end endgenerate
endmodule
