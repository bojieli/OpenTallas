`timescale 1ns/1ps
// W19 accepted256B baseline rank0/SM0 sequential dispatch: HBM -> fetch -> bench tag join
// adapter -> unchanged SM bulk-copy/SRAM/arithmetic. All exponent bytes traverse
// DRAM. Uses the existing full-K real-operand packing and golden result format.
module tb_w19_rank_dispatch;
    parameter integer SUB = 4, LBS = 2, LSB = 16, NC = 2, XDEPTH = 128, RMAX = 256, LEV = 4;
    localparam integer RW = $clog2(RMAX);
    localparam integer FRAGW = NC * (SUB * LBS * 266 + SUB * LSB * 16);
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg start = 0;
    reg [RW:0] op_rows; reg [15:0] op_c; reg [7:0] op_g; reg op_scale; reg op_gs; reg [1:0] op_fmt;
    wire busy;
    reg d_valid = 0; wire d_ready; reg [31:0] d_base = 0; reg [23:0] d_lines;
    wire req_v; wire [31:0] req_addr; wire [9:0] req_tag;
    reg rsp_v=0; reg [9:0] rsp_tag; reg [1087:0] rsp_data;
    reg xw_en = 0; reg [$clog2(XDEPTH)-1:0] xw_addr; reg [6:0] xw_grp; reg [8*256-1:0] xw_data; integer gg;
    wire rv; wire [RW-1:0] rrow; wire [NC*32-1:0] rdata; wire fault; wire arrive; wire released;
    reg release_in = 0;
    ot_gpu_sm_v #(.SUB(SUB), .LBS(LBS), .LSB(LSB), .NC(NC), .RMAX(RMAX), .LEV(LEV), .XD(XDEPTH), .MAX_OUT(512)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .op_rows(op_rows), .op_c(op_c), .op_g(op_g), .op_gs(op_gs),
        .op_fmt(op_fmt), .busy(busy), .d_valid(d_valid), .d_ready(d_ready), .d_base(d_base),
        .d_lines(d_lines), .req_v(req_v), .req_ready(tag_room && allow_req), .req_addr(req_addr), .req_tag(req_tag),
        .rsp_v(rsp_v), .rsp_tag(rsp_tag), .rsp_data(rsp_data), .xw_en(xw_en), .xw_addr(xw_addr), .xw_grp(xw_grp),
        .xw_data(xw_data), .rv(rv), .rrow(rrow), .rdata(rdata), .fault(fault), .arrive(arrive),
        .release_in(release_in), .released(released));
    reg [1087:0] lines [0:65535];
    reg [FRAGW+2047:0] xwords [0:XDEPTH-1];
    reg [31:0] cfg [0:7];
    // Compact transport: consecutive 136-B payloads, final HBM line padding only.
    // No weights or exponents reach rsp_data except through the HBM model.
    // The tag FIFO joins independent SM read requests to the ordered fetch
    // stream; all ready/valid transfers are counted at the sampling edge.
    localparam integer AW = 24, NPC = 32, MEMW = 2097152;
    wire fqv, fqr, evr, fidle, fsv;
    wire [AW-1:0] fa;
    wire [5:0] fn;
    wire [15:0] ft;
    wire [NPC-1:0] hv, hr;
    wire [NPC*16-1:0] ht;
    wire [NPC*5-1:0] hb;
    wire [NPC*256-1:0] hd;
    wire [1023:0] fsd;
    reg ev = 0;
    reg [8:0] expert_id;
    wire [15:0] transport_lines = nlines * 2;
    reg [21:0] cfg_base; reg [15:0] cfg_stride,cfg_offset,dispatch_epoch;
    reg [31:0] plan [0:107];
    integer descriptor, expected_first, expected_end;
    reg [1023:0] rootdir;
    wire stall_mode = cfg[7][0];
    wire allow_req = !stall_mode || (cyc % 17 >= 7);
    wire allow_line = !stall_mode || (cyc % 13 >= 5);
    // Existing accepted two-line bench join; no compact adapter instance.
    integer tq_w=0,tq_r=0,half=0;
    reg [9:0] tags[0:511];reg [1023:0] weight_line;
    wire tag_room=tq_w-tq_r<512;
    wire fsready=tq_w!=tq_r && allow_line;
    wire adapter_idle=tq_w==tq_r && half==0;
    wire adapter_fault=1'b0;
    ot_gpu_expert_fetch #(.NSM(1), .NPC(NPC), .DEPTH(64), .MAX_OUT(32), .DQ(4)) fetch (
        .clk(clk), .rst_n(rst_n), .cfg_base(cfg_base), .cfg_exp_lines(cfg_stride),
        .cfg_off(cfg_offset), .cfg_lines(transport_lines), .e_valid(ev), .e_ready(evr), .e_id(expert_id),
        .req_v(fqv), .req_rdy(fqr), .req_addr(fa), .req_len(fn), .req_tag(ft),
        .rsp_v(hv), .rsp_rdy(hr), .rsp_tag(ht), .rsp_beat(hb), .rsp_data(hd),
        .s_valid(fsv), .s_ready(fsready), .s_data(fsd), .idle(fidle));
    ot_hdc_hbm_model #(.NPC(NPC), .AW(AW), .MEM_WORDS(MEMW), .TAGW(16), .LENW(6), .BEATW(5),
        .CLK_PS(833), .REQ_PS(15000), .RSP_PS(15000), .PC_RDY(1), .QD(64), .RQD(32)) hbm (
        .clk(clk), .rst_n(rst_n), .req_v(fqv), .req_rdy(fqr), .pc_room(), .req_we(1'b0),
        .req_addr(fa), .req_len(fn), .req_tag(ft), .req_wdata(256'd0),
        .rsp_v(hv), .rsp_rdy(hr), .rsp_tag(ht), .rsp_beat(hb), .rsp_data(hd));
    integer nlines, i, ii, kk, fo, seed, pick, cyc, t0, t_first, t_last, nres, t_lastline, consumed;
    integer fetched = 0, returned = 0, first_req = -1, first_sector = -1, first_payload = -1, stalls = 0;
    reg [1023:0] dir;
    always @(posedge clk) begin
        rsp_v <= 1'b0;
        if (rst_n) begin
            if (ev && evr) ev <= 0;
            if (start) ev <= 1;
            if (fqv && fqr && first_req < 0) first_req = cyc;
            if (|(hv & hr)) if (first_sector < 0) first_sector = cyc;
            if (fsv && !fsready) stalls = stalls + 1;
            if (fqv && fqr && (fa < expected_first || fa+fn > expected_end))
                $fatal(1,"descriptor address escaped actual SM operation segment");
            if (req_v && tag_room && allow_req) begin
                if (req_addr !== tq_w) $fatal(1, "SM request order");
                tags[tq_w % 512] = req_tag;
                tq_w = tq_w + 1;
            end
            if (fsv && fsready) begin
                fetched = fetched + 1;
                if (half == 0) begin weight_line <= fsd; half = 1; end
                else begin
                    if (fsd[1023:64] !== 960'd0) $fatal(1, "transport padding");
                    rsp_v <= 1; rsp_tag <= tags[tq_r % 512];
                    rsp_data <= {fsd[63:0], weight_line};
                    tq_r = tq_r + 1; half = 0; returned = returned + 1;
                    if (first_payload < 0) first_payload = cyc;
                end
            end
        end
    end
    always @(posedge clk) cyc <= cyc + 1;
    always @(posedge clk) if (dut.w_valid && dut.w_ready) begin consumed = consumed + 1; t_lastline = $time; end
    reg [RMAX-1:0] seen_rows = 0;
    always @(posedge clk) if (rv) begin
        if (rrow >= op_rows || seen_rows[rrow]) $fatal(1, "duplicate or out-of-range SM result");
        seen_rows[rrow] = 1;
        if (nres == 0) t_first = $time;
        t_last = $time;
        $fwrite(fo, "%0d %h\n", rrow, rdata);
        nres = nres + 1;
    end
    always @(posedge clk) release_in <= arrive;
    initial begin
        if (!$value$plusargs("DIR=%s",rootdir)) $fatal(1,"missing dispatch directory");
        cyc=0;nres=0;consumed=0;expected_first=0;expected_end=0;
        $readmemh({rootdir,"/dispatch.hex"},plan);
        // One combined host-loaded stack image, preserved across all descriptors.
        $readmemh({rootdir,"/stack0.hex"},hbm.mem);
        repeat(4) @(negedge clk);rst_n=1;
        for(descriptor=0;descriptor<18;descriptor=descriptor+1) begin
            @(negedge clk);
            if(descriptor>0 && (!adapter_idle || !fidle || busy || ev)) $fatal(1,"producer dispatch before drain");
            $sformat(dir,"%0s/case%0d",rootdir,descriptor);
            $readmemh({dir,"/cfg.hex"},cfg);$readmemh({dir,"/x.hex"},xwords);
            op_rows=cfg[0];op_c=cfg[1];op_g=cfg[2];op_fmt=cfg[3];nlines=cfg[4];op_gs=cfg[5];expert_id=cfg[6];
            if(cfg[7][2:1]!=0) $fatal(1,"unexpected fault-injection fixture");
            cfg_base=plan[descriptor*6];cfg_stride=plan[descriptor*6+1];cfg_offset=plan[descriptor*6+2];
            dispatch_epoch=plan[descriptor*6+3];expected_first=plan[descriptor*6+4];expected_end=plan[descriptor*6+5];
            // Allow derived cfg_lines to settle before checking a format transition.
            #0.01;
            if(expected_first!=(cfg_base+expert_id*cfg_stride+cfg_offset)*4 || expected_end-expected_first!=transport_lines*4)
                $fatal(1,"dispatch/loader/fetch descriptor mismatch");
            nres=0;consumed=0;fetched=0;returned=0;seen_rows=0;tq_w=0;tq_r=0;half=0;first_req=-1;first_sector=-1;first_payload=-1;stalls=0;
            fo=$fopen({dir,"/out.txt"},"w");
            for(ii=0;ii<XDEPTH;ii=ii+1)
                for(gg=0;gg<(FRAGW+2047)/2048;gg=gg+1) begin
                    @(negedge clk);xw_en=1;xw_addr=ii;xw_grp=gg;xw_data=xwords[ii][gg*2048 +:2048];
                end
            @(negedge clk);xw_en=0;d_valid=1;d_lines=nlines;
            @(posedge clk);if(!d_ready)$fatal(1,"SM descriptor not ready");
            @(negedge clk);d_valid=0;start=1;t0=$time;
            @(negedge clk);start=0;
            wait(busy);wait(!busy);repeat(4)@(negedge clk);
            if(nres!=op_rows || consumed!=nlines || fault || adapter_fault) $fatal(1,"SM output/count/fault");
            if(fetched!=transport_lines || returned!=nlines || !adapter_idle || !fidle) $fatal(1,"descriptor incomplete");
            $fwrite(fo,"# dispatch %0d expert %0d epoch %0d first_sector %0d fetched %0d returned %0d cycles %0d stalls %0d\n",
                descriptor,expert_id,dispatch_epoch,expected_first,fetched,returned,$time-t0,stalls);
            $fclose(fo);
            $display("DISPATCH %0d PASS",descriptor);
        end
        $display("RANK_DISPATCH PASS descriptors=18 resets=1 physical_SM_instances=1");$finish;
    end
    initial begin #200000; $fatal(1,"rank descriptor timeout");end
endmodule
