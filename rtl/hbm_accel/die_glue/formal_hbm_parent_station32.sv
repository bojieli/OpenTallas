module formal_hbm_parent_station32 #(
    parameter integer W=328
) (input wire ck, input wire rst_n, input wire [W-1:0] i);
    localparam integer G=(W+23)/24;
    wire [W-1:0] o;
    wire [G-1:0] ready;
    wire ck_o;
    ot_hbm_parent_station32 #(.W(W)) dut(.*);
    reg [3:0] history;
    // No initialization: data/reset state and all inputs are arbitrary.
    // An independently tracked four-edge run of released reset establishes
    // the contractual one-hop state regardless of the arbitrary start.
    always @(posedge ck) begin
        history <= {history[2:0],rst_n};
        if (&history && rst_n) begin
            assert(o==$past(i));
            assert(ready=={G{1'b1}});
        end
    end
    always @* assert(ck_o==ck);
endmodule
