module ot_hep_tx_gbx #(parameter integer IDLE_K = 204, parameter integer MUT = 0) (
    input  wire         clk,
    input  wire         rst_n,           
    input  wire         tx_v,            
    input  wire [611:0] tx_frame,
    output reg  [511:0] beat,            
    output reg          cal_fault
);
     
     
     
     
    localparam integer GB = 13, SL = 64, NSL = (613 + SL - 1) / SL;
    reg [2:0]  ph;
    reg [GB-1:0] gc;                     
    wire idle_n_now = (gc == IDLE_K[GB-1:0]);
     
    wire [2:0]  ph_n = idle_n_now ? ph : (ph == 3'd4 ? 3'd0 : ph + 3'd1);
    wire [GB-1:0] gc_n = idle_n_now ? {GB{1'b0}} : (ph == 3'd4 ? gc + 1'b1 : gc);
    wire idle_n = (gc_n == IDLE_K[GB-1:0]);
    (* keep *) reg [NSL*5-1:0] oh;       
    (* keep *) reg [NSL-1:0]   tk;       
    (* keep *) reg [7:0] idr;            
    reg [612:0] prv;
    reg [612:0] cur;
    reg [509:0] g;
    integer s, j, k;
    wire [511:0] bnext = {g, 1'b0, oh[0]};
    always @(*) begin
        for (s = 0; s < NSL; s = s + 1)
            for (j = s * SL; j < (s + 1) * SL && j < 613; j = j + 1)
                cur[j] = tk[s] & (j == 0 ? tx_v : tx_frame[j - 1]);
        for (j = 0; j < 510; j = j + 1) begin
             
            s = j / SL;
            g[j] = (oh[s*5+0] & cur[j])
                 | (oh[s*5+1] & (j < 103 ? prv[510 + j] : cur[j - 103]))
                 | (oh[s*5+2] & (j < 206 ? ((MUT == 1) ? prv[406 + j] : prv[407 + j]) : cur[j - 206]))
                 | (oh[s*5+3] & (j < 309 ? prv[304 + j] : cur[j - 309]))
                 | (oh[s*5+4] & (j < 412 ? prv[201 + j] : 1'b0));
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            ph <= 3'd0; gc <= {GB{1'b0}}; beat <= 512'd2; cal_fault <= 1'b0;
            oh <= {NSL{5'b00001}}; tk <= {NSL{1'b1}}; idr <= 8'd0;
        end else begin
            ph <= ph_n; gc <= gc_n;
            oh <= {NSL{(idle_n ? 5'b00000 : 5'b00001 << ph_n)}};
            tk <= {NSL{!idle_n && ph_n != 3'd4}};
            idr <= {8{idle_n}};
            for (k = 0; k < 512; k = k + 1) beat[k] <= idr[k / 64] ? (k == 1) : bnext[k];
            if (tx_v && !tk[0]) cal_fault <= 1'b1;
        end
    always @(posedge clk) prv <= cur;
endmodule
