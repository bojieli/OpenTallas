module source_boundary(input clk,rst_n,go,ready,input[127:0]xl,
input wire [17:0] i_nout,
input wire [17:0] i_tiles,
input wire [17:0] i_k,
input wire [0:0] i_wsrc,
input wire [23:0] i_wbase,
input wire [23:0] i_ts,
input wire [23:0] i_ks,
input wire [23:0] i_js,
input wire [23:0] i_xbase,
input wire [23:0] i_xks,
input wire [23:0] i_xjs,
input wire [23:0] i_xcs,
input wire [2:0] i_jsh,
input wire [3:0] i_split,
input wire [23:0] i_wcs,
input wire [0:0] i_round,
input wire [23:0] i_obase,
input wire [23:0] i_ots,
input wire [23:0] i_ojs,
input wire [0:0] i_mmode,
input wire [0:0] i_oen,
input wire [0:0] i_amax,
input wire [0:0] i_rmax,
input wire [23:0] i_mbase,output reg go_q,output reg[378:0]ib_q,output reg[127:0]xl_q);
localparam NW=18,AW=24,IBW=379,BD=1,IREG=1;
wire[378:0]tb;wire tgo;
    wire [IBW-1:0] ib = {i_nout, i_tiles, i_k, i_wsrc, i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs, i_xcs,
                         i_jsh, i_split, i_wcs, i_round, i_obase, i_ots, i_ojs, i_mmode, i_oen, i_amax, i_rmax,
                         i_mbase};
    ot_hdc_delay #(.W(IBW), .D(BD - IREG)) u_ib (.clk(clk), .rst_n(rst_n), .d(ib), .q(tb));
    ot_hdc_delay #(.W(1), .D(BD - IREG), .RESET(1)) u_go (.clk(clk), .rst_n(rst_n), .d(go && ready), .q(tgo));

wire ib_go=tgo;
wire[378:0]tile_ib=tb;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) go_q <= 1'b1;
        else go_q <= ib_go;
    end
    always @(posedge clk) begin ib_q <= tile_ib; xl_q <= xl; end

endmodule
module proof(input clk,rst_n,go,ready,input[378:0]ib,input[127:0]xl);
wire go_q;wire[378:0]ib_q;wire[127:0]xl_q;
source_boundary dut(.clk(clk),.rst_n(rst_n),.go(go),.ready(ready),.xl(xl),.i_nout(ib[378 -: 18]),.i_tiles(ib[360 -: 18]),.i_k(ib[342 -: 18]),.i_wsrc(ib[324 -: 1]),.i_wbase(ib[323 -: 24]),.i_ts(ib[299 -: 24]),.i_ks(ib[275 -: 24]),.i_js(ib[251 -: 24]),.i_xbase(ib[227 -: 24]),.i_xks(ib[203 -: 24]),.i_xjs(ib[179 -: 24]),.i_xcs(ib[155 -: 24]),.i_jsh(ib[131 -: 3]),.i_split(ib[128 -: 4]),.i_wcs(ib[124 -: 24]),.i_round(ib[100 -: 1]),.i_obase(ib[99 -: 24]),.i_ots(ib[75 -: 24]),.i_ojs(ib[51 -: 24]),.i_mmode(ib[27 -: 1]),.i_oen(ib[26 -: 1]),.i_amax(ib[25 -: 1]),.i_rmax(ib[24 -: 1]),.i_mbase(ib[23 -: 24]),.go_q(go_q),.ib_q(ib_q),.xl_q(xl_q));
reg seen_reset=0,ref_go;reg[378:0]ref_ib;reg[127:0]ref_x;
always @(posedge clk) begin
 if(!rst_n)seen_reset<=1;
 ref_go<=rst_n && go && ready;
 ref_ib<=ib;ref_x<=xl;
end
always @* if(!rst_n)assert(!go_q);
always @* if(seen_reset)begin
 assert(go_q==ref_go);
 if(go_q)begin assert(ib_q==ref_ib);assert(xl_q==ref_x);end
end
endmodule
