`timescale 1ns/1ps
// C8 head interval measurement, existing reduced MTP images and exact engine.
// No replacement arithmetic, clock claim, or synthetic completion/ready signal.
module tb_dsrom_c8_head_interval(input wire clk);
    localparam integer MG=8, BAW=18, AW=24, NW=16, W=16, G=4;
    reg rst_n=0, go=0;
    reg [31:0] desc [0:6*16-1], vm [0:131071], bank [0:64*(1<<BAW)-1];
    reg [31:0] expect_logits [0:6*4040-1];
    reg [2047:0] rd[0:1];
    reg [127:0] xq;
    wire ready,idle,ov,fault,any;
    wire [7:0] bre;
    wire [8*BAW-1:0] ba;
    wire [3:0] xre,owe;
    wire [4*AW-1:0] xa,oa;
    wire [63:0] mask;
    wire [2047:0] data;
    wire [15:0] token;
    wire [31:0] value;
    integer active=0, launched=0, completed=0, cyc=0, errors=0, checked=0;
    integer start_cycle[0:5], done_cycle[0:5], row_count[0:5];
    integer i,q,l,r;
    reg running=0;
    reg [8*1024-1:0] dir;
    ot_hdc_v41x_me_adapt #(.MG(MG),.BAW(BAW),.MP(1),.KMAX(512),.RL(2)) dut (
        .clk(clk),.rst_n(rst_n),.go(go),.i_preloaded(1'b0),.ready(ready),.idle(idle),
        .i_nout(desc[active*16]),.i_tiles(desc[active*16+1]),.i_k(desc[active*16+2]),
        .i_wbase(desc[active*16+3]),.i_xbase(desc[active*16+4]),.i_xjs(desc[active*16+5]),
        .i_split(desc[active*16+6]),.i_round(desc[active*16+7]),
        .i_obase(desc[active*16+8]),.i_ots(desc[active*16+9]),.i_ojs(desc[active*16+10]),
        .i_oen(1'b0),.i_amax(1'b1),.i_m(3'd1),.i_xps(24'd0),.i_ops(24'd0),
        .cfg_xs(desc[active*16+11]),.wb_re(bre),.wb_addr(ba),.wb_q(rd[1]),
        .x_re(xre),.x_addr(xa),.x_q(xq),.shared_xr0('0),
        .ov(ov),.o_we(owe),.o_addr(oa),.o_mask(mask),.o_data(data),
        .am_idx(token),.am_val(value),.am_any(any),.fault(fault));
    initial begin
        if (!$value$plusargs("DIR=%s",dir)) $fatal(1,"missing cached head stimulus");
        $readmemh({dir,"/desc.hex"},desc);
        $readmemh({dir,"/vm.hex"},vm);
        $readmemh({dir,"/mbank.hex"},bank);
        $readmemh({dir,"/head_logits.hex"},expect_logits);
        for (i=0;i<6;i=i+1) row_count[i]=0;
    end
    always @(posedge clk) begin
        cyc<=cyc+1;
        // Same synchronous read/capture timing as the actual MTP core bench.
        for(q=0;q<64;q=q+1)
            rd[0][q*32+:32]<=bank[32'(ba[(q%8)*BAW+:BAW])*64+q];
        rd[1]<=rd[0];
        for(q=0;q<4;q=q+1) if(xre[q]) xq[q*32+:32]<=vm[xa[q*AW+:AW]];
        if(cyc==5) rst_n<=1;
        go<=0;
        if(rst_n && !running && launched<6 && ready) begin
            go<=1; running<=1;
        end
        if(go && ready) begin
            start_cycle[active]=cyc; launched=launched+1;
            $display("HEAD_START slot=%0d cycle=%0d",active,cyc);
        end
        if(running && ov) begin
            for(q=0;q<4;q=q+1) for(l=0;l<16;l=l+1) if(mask[q*16+l]) begin
                r=oa[q*AW+:AW]*16+l;
                if(r<4040) begin
                    checked=checked+1; row_count[active]=row_count[active]+1;
                    if(data[(q*16+l)*32+:32]!==expect_logits[active*4040+r]) errors=errors+1;
                end else errors=errors+1;
            end
        end
        // The real adapter has a single activation context; measure its
        // actual re-entry after drain, rather than assuming tile occupancy.
        if(running && !go && row_count[active]==4040 && ready && idle) begin
            done_cycle[active]=cyc;
            if(fault || !any || token!==desc[active*16+12]) errors=errors+1;
            $display("HEAD_DONE slot=%0d cycle=%0d latency=%0d token=%0d fault=%0d",active,cyc,
                     cyc-start_cycle[active],token,fault);
            completed=completed+1;
            if(completed==6) begin
                for(i=1;i<6;i=i+1)
                    $display("HEAD_II from=%0d to=%0d cycles=%0d",i-1,i,start_cycle[i]-start_cycle[i-1]);
                $display("C8_HEAD positions=%0d logits_checked=%0d errors=%0d",completed,checked,errors);
                if(errors==0 && checked==6*4040) $display("PASS"); else $display("FAIL");
                $finish;
            end
            active<=active+1; running<=0;
        end
    end
endmodule
