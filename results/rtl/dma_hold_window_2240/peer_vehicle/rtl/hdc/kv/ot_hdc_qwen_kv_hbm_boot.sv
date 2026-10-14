`timescale 1ns/1ps
// Initial resident K-tail fill. A 32-byte HBM sector contains two adjacent
// 16-byte FP8 K words. Read the preceding and current position tiles for
// every layer/KV head, then write both words through the tail bank boot port.
// The caller holds token issue until done; no speculative requests are made.
module ot_hdc_qwen_kv_hbm_boot #(
    parameter integer AW=24,NW=16,W=16,LOG_HD=7,LOG_TW=2,LLG=3
) (
    input wire clk,rst_n,start,
    input wire [NW-1:0] pos,
    output wire busy,done,
    output wire req_v,input wire req_ready,output wire [AW-1:0] req_sector,
    input wire rsp_v,input wire [255:0] rsp_data,
    output wire wr_v,output wire [AW-1:0] wr_word,
    output wire [127:0] wr_data,
    output reg fault
);
    localparam integer LW=$clog2(W), LPAIR=LOG_HD-1;
    localparam integer TOTAL=1 << (LLG+LOG_HD);
    localparam integer LC=$clog2(TOTAL+1);
    localparam [2:0] IDLE=0,REQ=1,WAIT=2,WRITE_LO=3,WRITE_HI=4,DONE=5;
    reg [2:0] state;
    reg [LC-1:0] count;
    reg [LOG_TW-1:0] previous_tile,current_tile;
    reg [255:0] sector_data;
    wire phase=count[LLG+LPAIR];
    wire [LLG-1:0] layer_head=count[LPAIR +: LLG];
    wire [LPAIR-1:0] pair_idx=count[LPAIR-1:0];
    wire [LOG_TW-1:0] tile=phase ? current_tile : previous_tile;
    wire [AW-1:0] low_word=(AW'(layer_head) << (LOG_TW+LOG_HD)) |
                            (AW'(tile) << LOG_HD) | (AW'(pair_idx) << 1);
    assign req_v=state==REQ;
    assign req_sector=low_word >> 1;
    assign wr_v=state==WRITE_LO || state==WRITE_HI;
    assign wr_word=low_word + AW'(state==WRITE_HI);
    assign wr_data=state==WRITE_HI ? sector_data[255:128] : sector_data[127:0];
    assign busy=state!=IDLE && state!=DONE;
    assign done=state==DONE;
    initial if (LOG_HD<2) $error("Qwen HBM boot requires at least four K words per head");
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state<=IDLE; count<=0; previous_tile<=0; current_tile<=0;
            sector_data<=0; fault<=0;
        end else begin
            if (start && state!=IDLE && state!=DONE) fault<=1;
            case (state)
                IDLE,DONE: if (start) begin
                    count<=0;
                    current_tile<=(pos >> LW);
                    previous_tile<=(pos >> LW)-1'b1;
                    state<=REQ;
                end
                REQ: if (req_ready) state<=WAIT;
                WAIT: if (rsp_v) begin sector_data<=rsp_data; state<=WRITE_LO; end
                WRITE_LO: state<=WRITE_HI;
                WRITE_HI: if (count==TOTAL-1) state<=DONE;
                          else begin count<=count+1'b1; state<=REQ; end
                default: state<=IDLE;
            endcase
        end
    end
endmodule
