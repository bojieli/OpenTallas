`default_nettype none
// Static compiler slots; original exact arithmetic, no queues, credits or backpressure.
module ot_hbm_idx_engine_static #(parameter integer MUT=0)(
    input wire clk, input wire clk_tail, input wire [3:0] clk_chunk, input wire [127:0] clk_hslice,
    input  wire                 rst_n,
    input  wire                 ql_v,
    input  wire [7:0]           ql_head,
    input  wire [NB*128-1:0]    ql_codes,
    input  wire [NB*8-1:0]      ql_sc,
    input  wire [15:0]          ql_w,
    input  wire                 k_valid,
    
    input  wire [NK-1:0]        k_kv,
    input  wire [NK-1:0]        k_keep,
    input  wire [NK*NB*136-1:0] k_key,
    output wire                  o_valid,
    
    output wire  [NK-1:0]        o_kv,
    output wire  [NK*16-1:0]     o_score,
    output wire  [NK-1:0]        o_fault,
    // activation counters (since reset; for the benches): keys scored (score
    // slots delivered), head terms fused (ReLU x weight terms summed inside the
    // engine: IH per scored key), keys whose score faulted
    output reg   [47:0]          cnt_keys_scored,
    output reg   [47:0]          cnt_headsums_fused,
    output reg   [47:0]          cnt_faults
, output wire online, output wire protocol_fault
);
 localparam integer NK=4,IH=32,NB=4,NCH=4,FPL=7,FML=5,QL=5;
 wire take;wire[3:0]keep_d,chunks_online;
    // chunks
    wire [NCH-1:0]        cv;
    wire [NK-1:0]         ckv [0:NCH-1];
    wire [NK*32-1:0]      csum [0:NCH-1];
    wire [NK-1:0]         cfl [0:NCH-1];
    genvar c, g;
    generate
        for (c = 0; c < NCH; c = c + 1) begin : g_ch
            ot_hbm_idx_chunk_owned_native u_c (
                .clk(clk_chunk[c]), .clk_hslice(clk_hslice[32*c+:32]), .rst_n(rst_n), .hb(8'(8 * ((MUT == 1) ? (c ^ 1) : ((MUT == 2 && c == 0) ? 1 : c)))), .ql_v(ql_v), .ql_head(ql_head), .ql_codes(ql_codes), .ql_sc(ql_sc),
                .ql_w(ql_w), .k_v(take), .k_kv(k_kv), .k_key(k_key),
                .online(chunks_online[c]), .c_v(cv[c]), .c_kv(ckv[c]), .c_sum(csum[c]), .c_fault(cfl[c]));
        end
    endgenerate
    wire [NK*NCH*32-1:0] tsum;
    wire [NK*NCH-1:0] tfl;
    for(genvar gi=0;gi<NK;gi=gi+1)begin:g_transpose
      for(genvar ci=0;ci<NCH;ci=ci+1)begin:g_chunk
        assign tsum[(gi*NCH+ci)*32+:32]=csum[ci][32*gi+:32];
        assign tfl[gi*NCH+ci]=cfl[ci][gi];
      end
    end
    wire              tv;
    wire [NK-1:0]     tkv, tf;
    wire [NK*16-1:0]  ts;
    ot_hbm_idx_tail_native u_t (.clk(clk_tail), .rst_n(rst_n), .i_v(cv[0]), .i_kv(ckv[0]),
        .i_keep(keep_d), .i_sum(tsum), .i_fault(tfl), .o_v(tv), .o_kv(tkv), .o_score(ts), .o_fault(tf));

    // Measured retained arithmetic chunk latency; metadata has the same fixed path.
    ot_hdc_delay #(.W(4),.D(106)) keep_pipe(.clk(clk),.rst_n(rst_n),.d(k_keep),.q(keep_d));
    assign take=k_valid;
    reg [3:0] ready1,ready2;
    reg online_q;
    assign online=online_q;
    reg fault_q; reg [1:0] settle;
    
    always @(posedge clk or negedge rst_n)begin
      if(!rst_n)begin ready1<=0;ready2<=0;online_q<=0;fault_q<=0;settle<=0;end
      else begin
        if(ql_v)settle<=3;else if(settle!=0)settle<=settle-1;
        ready1<=chunks_online;ready2<=ready1;online_q<=&ready2;
        if(k_valid && (!online_q||ql_v||settle!=0))fault_q<=1;
      end
    end
    reg ov;reg[3:0]ok,ofl;reg[63:0]os;
    assign o_valid=ov;assign o_kv=ok;assign o_score=os;assign o_fault=ofl;
    assign protocol_fault=fault_q;
    always @(posedge clk or negedge rst_n)begin
      if(!rst_n)begin ov<=0;cnt_keys_scored<=0;cnt_headsums_fused<=0;cnt_faults<=0;end
      else begin
        ov<=tv;ok<=tkv;os<=ts;ofl<=tf;
        if(tv)begin
          cnt_keys_scored<=cnt_keys_scored+48'($countones(tkv));
          cnt_headsums_fused<=cnt_headsums_fused+48'($countones(tkv)*32);
          cnt_faults<=cnt_faults+48'($countones(tkv&tf));
        end
      end
    end
endmodule
`default_nettype wire
