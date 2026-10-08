module source_cut(input wire clk,rst_n,go,ready,
      input wire[378:0] word, input wire[127:0] xl,
      output wire tgo, output wire[378:0] tb, output wire[127:0] xl_d);
      localparam NW=18, AW=24, IBW=379, TG=4, NXL=1, BD=3, XVM=0, IREG=1;
        wire [NW-1:0] i_nout, i_tiles, i_k;
    wire          i_wsrc, i_round, i_mmode, i_oen, i_amax, i_rmax;
    wire [AW-1:0] i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs, i_xcs, i_wcs, i_obase, i_ots, i_ojs, i_mbase;
    wire [2:0]    i_jsh;
    wire [3:0]    i_split;

assign {i_nout,i_tiles,i_k,i_wsrc,i_wbase,i_ts,i_ks,i_js,i_xbase,i_xks,i_xjs,i_xcs,i_jsh,i_split,i_wcs,i_round,i_obase,i_ots,i_ojs,i_mmode,i_oen,i_amax,i_rmax,i_mbase} = word;
    wire [IBW-1:0] ib = {i_nout, i_tiles, i_k, i_wsrc, i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs, i_xcs,
                         i_jsh, i_split, i_wcs, i_round, i_obase, i_ots, i_ojs, i_mmode, i_oen, i_amax, i_rmax,
                         i_mbase};
    ot_hdc_delay #(.W(IBW), .D(BD - IREG)) u_ib (.clk(clk), .rst_n(rst_n), .d(ib), .q(tb));
    ot_hdc_delay #(.W(1), .D(BD - IREG), .RESET(1)) u_go (.clk(clk), .rst_n(rst_n), .d(go && ready), .q(tgo));
    ot_hdc_delay #(.W(NXL*TG*32), .D(BD - XVM - IREG)) u_xnet (.clk(clk), .rst_n(rst_n), .d(xl), .q(xl_d));
endmodule
module sink_cut(input wire clk,rst_n,ib_go,
      input wire[378:0] ib, input wire[127:0] xl, output wire[507:0] observed);
      localparam NW=18,AW=24,TG=4,IREG=1,MEM_EXTRA=0;
        localparam integer IBW = 3 * NW + 13 * AW + 13;
    reg              go_q;
    reg  [IBW-1:0]   ib_q;
    reg  [TG*32-1:0] xl_q;
    wire             go_i  = IREG ? go_q : ib_go;
    wire [IBW-1:0]   ib_i  = IREG ? ib_q : ib;
    wire [TG*32-1:0] xl_r  = IREG ? xl_q : xl;
    wire [TG*32-1:0] xl_i;
    ot_hdc_delay #(.W(TG*32), .D(MEM_EXTRA)) u_xm (.clk(clk), .rst_n(rst_n), .d(xl_r), .q(xl_i));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) go_q <= 1'b0;
        else go_q <= ib_go;
    end
    always @(posedge clk) begin ib_q <= ib; xl_q <= xl; end

    wire [NW-1:0] b_nout, b_tiles, b_k;
    wire          b_wsrc, b_round, b_mmode, b_oen, b_amax, b_rmax;
    wire [AW-1:0] b_wbase, b_ts, b_ks, b_js, b_xbase, b_xks, b_xjs, b_xcs, b_wcs, b_obase, b_ots, b_ojs, b_mbase;
    wire [2:0]    b_jsh;
    wire [3:0]    b_split;
    assign {b_nout, b_tiles, b_k, b_wsrc, b_wbase, b_ts, b_ks, b_js, b_xbase, b_xks, b_xjs, b_xcs,
            b_jsh, b_split, b_wcs, b_round, b_obase, b_ots, b_ojs, b_mmode, b_oen, b_amax, b_rmax, b_mbase} = ib_i;


assign observed={xl_i,go_i,{b_nout, b_tiles, b_k, b_wsrc, b_wbase, b_ts, b_ks, b_js, b_xbase, b_xks, b_xjs, b_xcs, b_jsh, b_split, b_wcs, b_round, b_obase, b_ots, b_ojs, b_mmode, b_oen, b_amax, b_rmax, b_mbase}};
endmodule
