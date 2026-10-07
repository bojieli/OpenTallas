// Minimum opt-in protected serial SRAM row path. This is NOT the full-width
// score/PV replay path: that requires 128 parallel decode lanes at II=1.
// All ports here are stream-clock synchronous; no CDC is implied.
module ot_dsrom_softmax_serial_row(
    input wire clk,rst_n,
    input wire wr_valid,
    output wire wr_ready,
    input wire [1023:0] wr_data,
    input wire [2:0] wr_beat,
    input wire [6:0] wr_addr,
    input wire [15:0] wr_tag,
    output wire mem_w_valid,
    input wire mem_w_ready,
    output wire [6:0] mem_w_addr,
    output wire [9215:0] mem_w_code,
    input wire rd_valid,
    output wire rd_ready,
    input wire [6:0] rd_addr,
    input wire [15:0] rd_tag,
    output wire mem_r_en,
    output wire [6:0] mem_r_addr,
    output wire [15:0] mem_r_tag,
    input wire mem_return_valid,
    input wire [15:0] mem_return_tag,
    input wire [9215:0] mem_return_code,
    output wire out_valid,
    input wire out_ready,
    output wire [1023:0] out_data,
    output wire [2:0] out_beat,
    output wire [15:0] out_tag,
    output wire out_corrected,
    output wire fault
);
    reg [9215:0] write_row,read_row;
    (* keep="true",dont_touch="true" *) reg [3:0] wc,wc_n;
    (* keep="true",dont_touch="true" *) reg [15:0] wt,wt_n,rt,rt_n;
    (* keep="true",dont_touch="true" *) reg [6:0] wa,wa_n,ra,ra_n;
    (* keep="true",dont_touch="true" *) reg [2:0] pending,pending_n,ri,ri_n;
    (* keep="true",dont_touch="true" *) reg whole,whole_n;
    (* keep="true",dont_touch="true" *) reg [1:0] rs,rs_n,settle,settle_n;
    (* keep="true",dont_touch="true" *) reg failed,failed_n;
    localparam [1:0] IDLE=0,ISSUE=1,WAIT_MEM=2,SERIAL=3;
    wire integrity=(wc_n==~wc)&&(wt_n==~wt)&&(rt_n==~rt)&&(wa_n==~wa)&&(ra_n==~ra)
        &&(pending_n==~pending)&&(ri_n==~ri)&&(whole_n==~whole)&&(rs_n==~rs)
        &&(settle_n==~settle)&&(failed_n==~failed)&&(wc<=8)&&(rs<=SERIAL);
    wire [15:0] wcv,rv,corr,ue;
    wire [1151:0] encoded;
    wire w_valid_disagree=(wcv!=0 && wcv!=16'hffff);
    wire r_valid_disagree=(rv!=0 && rv!=16'hffff);
    wire active_ue=(rs==SERIAL && settle==0 && (&rv) && (|ue));
    assign fault=failed || !integrity || w_valid_disagree || r_valid_disagree || active_ue;
    assign wr_ready=!fault && wc<8;
    wire wfire=wr_valid&&wr_ready;
    wire bad_write=wfire && ((wr_beat!=wc[2:0]) || (wc!=0 && (wr_tag!=wt || wr_addr!=wa)));
    wire accept_write=wfire&&!bad_write;
    assign mem_w_valid=whole&&!fault;
    assign mem_w_addr=wa;
    assign mem_w_code=write_row;
    assign rd_ready=(rs==IDLE)&&!fault;
    wire rfire=rd_valid&&rd_ready;
    assign mem_r_en=(rs==ISSUE)&&!fault;
    assign mem_r_addr=ra;
    assign mem_r_tag=rt;
    wire bad_return=mem_return_valid && (rs!=WAIT_MEM || mem_return_tag!=rt);
`ifdef SOFTMAX_SERIAL_SWAP_BEATS
    wire [1151:0] selected=read_row[1152*(ri^3'd1) +: 1152];
`else
    wire [1151:0] selected=read_row[1152*ri +: 1152];
`endif
    genvar lane;
    generate for(lane=0;lane<16;lane=lane+1)begin:g_codec
        ot_dsrom_softmax_ecc_lane codec(
            .clk(clk),.rst_n(rst_n),.w_valid(accept_write),
            .w_data(wr_data[64*lane +:64]),.w_code_valid(wcv[lane]),
            .w_code(encoded[72*lane +:72]),.r_valid(rs==SERIAL&&!fault),
            .r_code(selected[72*lane +:72]),.r_data_valid(rv[lane]),
            .r_data(out_data[64*lane +:64]),.corrected(corr[lane]),.uncorrectable(ue[lane]));
    end endgenerate
    assign out_valid=(rs==SERIAL)&&(settle==0)&&(&rv)&&!fault;
    assign out_beat=ri;
    assign out_tag=rt;
    assign out_corrected=|corr;
    always @(posedge clk)begin
        if(!rst_n)begin
            wc<=0;wc_n<=~4'd0;wt<=0;wt_n<=~16'd0;rt<=0;rt_n<=~16'd0;
            wa<=0;wa_n<=~7'd0;ra<=0;ra_n<=~7'd0;pending<=0;pending_n<=~3'd0;
            ri<=0;ri_n<=~3'd0;whole<=0;whole_n<=1;rs<=IDLE;rs_n<=~IDLE;
            settle<=0;settle_n<=~2'd0;failed<=0;failed_n<=1;
        end else if(fault || bad_write || bad_return)begin failed<=1;failed_n<=0;end
        else begin
            if(accept_write)begin
                wc<=wc+4'd1;wc_n<=~(wc+4'd1);pending<=wr_beat;pending_n<=~wr_beat;
                if(wc==0)begin wt<=wr_tag;wt_n<=~wr_tag;wa<=wr_addr;wa_n<=~wr_addr;end
            end
            if(&wcv)begin
                write_row[1152*pending +:1152]<=encoded;
                if(pending==7)begin whole<=1;whole_n<=0;end
            end
            if(mem_w_valid&&mem_w_ready)begin wc<=0;wc_n<=~4'd0;whole<=0;whole_n<=1;end
            if(rfire)begin rs<=ISSUE;rs_n<=~ISSUE;rt<=rd_tag;rt_n<=~rd_tag;ra<=rd_addr;ra_n<=~rd_addr;end
            if(rs==ISSUE)begin rs<=WAIT_MEM;rs_n<=~WAIT_MEM;end
            if(mem_return_valid)begin
                read_row<=mem_return_code;rs<=SERIAL;rs_n<=~SERIAL;
                ri<=0;ri_n<=~3'd0;settle<=3;settle_n<=~2'd3;
            end
            if(rs==SERIAL && settle!=0)begin settle<=settle-2'd1;settle_n<=~(settle-2'd1);end
            if(out_valid&&out_ready)begin
                if(ri==7)begin rs<=IDLE;rs_n<=~IDLE;end
                else begin ri<=ri+3'd1;ri_n<=~(ri+3'd1);settle<=3;settle_n<=~2'd3;end
            end
        end
    end
endmodule
