// X epoch storage/replay leaf. Data for an epoch arrives before its first read.
// DEPTH=2 is native streaming pingpong; larger DEPTH allows full-preload burst.
// Epoch tags distinguish stale data on wrap. Loader handles tile/line matching.
module ot_qwen_xepoch_cache #(
    parameter integer DEPTH=2,
    parameter integer MUT_STALE_BANK=0
) (
    input wire clk,input wire rst_n,input wire clear,
    input wire load_v,input wire [15:0] load_epoch,input wire [127:0] load_x,
    input wire read_v,input wire [15:0] read_epoch,
    output reg q_v,output reg [127:0] q_x,output reg fault
);
    localparam integer AB=(DEPTH<=2)?1:$clog2(DEPTH);
    reg [127:0] data[0:DEPTH-1];
    reg [15:0] tags[0:DEPTH-1];
    reg [DEPTH-1:0] valid;
    wire [AB-1:0] wi=load_epoch[AB-1:0];
    wire [AB-1:0] ri=MUT_STALE_BANK?0:read_epoch[AB-1:0];
    initial if(DEPTH<2 || (DEPTH&(DEPTH-1))!=0) $error("DEPTH must be power of two>=2");
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin valid<=0;q_v<=0;q_x<=0;fault<=0;end
        else begin
            q_v<=0;
            if(clear) valid<=0;
            if(load_v && !clear) begin data[wi]<=load_x;tags[wi]<=load_epoch;valid[wi]<=1;end
            if(read_v && !clear) begin
                if(valid[ri] && tags[ri]==read_epoch) begin q_v<=1;q_x<=data[ri];end
                else begin fault<=1;q_x<=0;end
                if(load_v && wi==ri) fault<=1; // source must not overwrite current epoch
            end
        end
    end
endmodule
