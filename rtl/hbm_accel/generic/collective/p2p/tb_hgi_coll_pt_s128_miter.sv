`timescale 1ns/1ps
`default_nettype none
// HBM-COLLFJ2 (10-19): random miter ot_hgi_coll_static_program_target_s128 (SAFE fj body: flow SRAM + registered decode)
// == ot_hgi_coll_static_program_target #(ROWS 128) (closed form), every output every cycle, under random episodes that
// go beyond the host contract the scripted parent programme keeps: frames / descriptors / launches at random gaps
// (0..70 edges, so frames land on the edge a drain completes, rows are rewritten right after their drain, descriptors
// overlap scans), random targets / segments / spare bits, valid and invalid programmes, random issuer feedback and
// random resets.  Prints PT_S128_MITER PASS|FAIL and the coverage counters (accept / fault / configured / start / fwd).
module tb_hgi_coll_pt_s128_miter;
    reg clk=0, rst_n=0;
    always #1 clk=~clk;
    reg cfg_v=0, desc_v=0, launch_v=0, program_active=0, issuer_busy=0, issuer_fault=0, issuer_uop_v=0;
    reg [7:0] cfg_target=0; reg [11:0] cfg_addr=0; reg [255:0] cfg_data=0;
    reg [11:0] desc_base=0; reg [12:0] desc_limit=0; reg [15:0] desc_loops=0; reg [6:0] issuer_uop_pc=0;
    wire [36:0] r_cfg, d_cfg; wire r_st, d_st; wire [6:0] r_spc, d_spc; wire r_conf, d_conf, r_ib, d_ib, r_f, d_f;
    ot_hgi_coll_static_program_target #(.TARGET(8'd52),.ROWS(128)) u_ref(.clk(clk),.rst_n(rst_n),.cfg_v(cfg_v),
        .cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),
        .desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),.program_active(program_active),
        .issuer_busy(issuer_busy),.issuer_fault(issuer_fault),.issuer_uop_v(issuer_uop_v),.issuer_uop_pc(issuer_uop_pc),
        .issuer_cfg(r_cfg),.issuer_start(r_st),.issuer_start_pc(r_spc),.configured(r_conf),.init_busy(r_ib),.fault(r_f));
    ot_hgi_coll_static_program_target_s128 #(.TARGET(8'd52)) u_dut(.clk(clk),.rst_n(rst_n),.cfg_v(cfg_v),
        .cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),
        .desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),.program_active(program_active),
        .issuer_busy(issuer_busy),.issuer_fault(issuer_fault),.issuer_uop_v(issuer_uop_v),.issuer_uop_pc(issuer_uop_pc),
        .issuer_cfg(d_cfg),.issuer_start(d_st),.issuer_start_pc(d_spc),.configured(d_conf),.init_busy(d_ib),.fault(d_f));
    integer cyc=0, mism=0, n_fault=0, n_conf=0, n_start=0, n_fwd=0, n_ep=0;
    always @(posedge clk) begin
        cyc<=cyc+1;
        if ({r_cfg,r_st,r_spc,r_conf,r_ib,r_f} !== {d_cfg,d_st,d_spc,d_conf,d_ib,d_f}) begin
            if (mism<8) $display("PT_S128_MISMATCH cyc %0d ref cfg %h st %b spc %0d conf %b ib %b f %b | dut cfg %h st %b spc %0d conf %b ib %b f %b",
                cyc, r_cfg, r_st, r_spc, r_conf, r_ib, r_f, d_cfg, d_st, d_spc, d_conf, d_ib, d_f);
            mism<=mism+1;
        end
        if (r_st) n_start<=n_start+1;
    end
    // forward coverage: a frame decided on the edge after the drain of its own row completed
    reg pend_fwd=0;
    always @(posedge clk) begin
        pend_fwd <= rst_n && u_dut.drain_done && cfg_v && cfg_target==8'd52 && cfg_addr[9:3]==u_dut.row;
        if (pend_fwd) n_fwd<=n_fwd+1;
    end
    reg r_f_d=0, r_conf_d=0;
    always @(posedge clk) begin r_f_d<=r_f; r_conf_d<=r_conf; if (r_f && !r_f_d) n_fault<=n_fault+1; if (r_conf && !r_conf_d) n_conf<=n_conf+1; end
    // ---- stimulus --------------------------------------------------------------------------------------------------
    integer seed;
    function automatic integer rnd(input integer n); rnd = $urandom % n; endfunction
    task idle(input integer n); integer i; begin for (i=0;i<n;i=i+1) begin @(negedge clk); cfg_v=0; desc_v=0; launch_v=0;
        program_active = (rnd(16)==0); issuer_busy = (rnd(16)==0); issuer_fault = (rnd(400)==0);
        issuer_uop_v = (rnd(24)==0); issuer_uop_pc = rnd(128); end end endtask
    task quiet; begin program_active=0; issuer_busy=0; issuer_fault=0; issuer_uop_v=0; end endtask
    task frame(input integer row, input integer seg, input [255:0] d, input integer bad);
        begin @(negedge clk); quiet; cfg_v=1; desc_v=0; launch_v=0;
            cfg_target = (bad==1) ? 8'd53 : 8'd52;
            cfg_addr = {2'b00, row[6:0], seg[2:0]}; if (bad==2) cfg_addr[11:10]=2'(1+rnd(3));
            cfg_data = d; if (bad==3) cfg_data[64+rnd(192)]=1'b1; if (bad==4) cfg_data[54+rnd(10)]=1'b1;
            @(negedge clk); cfg_v=0; end endtask
    function automatic [63:0] meta(input integer r, input integer lo, input integer hi, input integer last);
        reg [63:0] m; integer nx, tg;
        begin m = {$urandom,$urandom}; m[63:51]=0; m[44]=(last!=0); m[43:12]=0;
            nx = (r+1<hi) ? r+1 : r; tg = lo + rnd(hi-lo);
            if (rnd(3)==0) begin m[12+rnd(32)]=1'b1; end            // has_repeat
            if (rnd(20)==0) nx = rnd(128);                          // occasionally out of range
            m[5:0]=nx[5:0]; m[51]=nx[6]; m[11:6]=tg[5:0]; m[52]=tg[6]; meta=m; end endfunction
    task load_row(input integer r, input integer lo, input integer hi, input integer last, input integer badp);
        integer s, k, order[0:6], t, tmp; reg [255:0] d;
        begin for (k=0;k<7;k=k+1) order[k]=k;
            for (k=6;k>0;k=k-1) begin t=rnd(k+1); tmp=order[k]; order[k]=order[t]; order[t]=tmp; end
            for (k=0;k<7;k=k+1) begin s=order[k];
                if (s==6) d={192'b0, meta(r,lo,hi,last)}; else d={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
                frame(r, s, d, (rnd(badp)==0) ? 1+rnd(4) : 0);
                if (rnd(3)==0) idle(rnd(3));
            end end endtask
    integer ep, nrows, b, lim, r, g, v;
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1019;
        v = $urandom(seed);
        for (ep=0; ep<`PT_EPISODES; ep=ep+1) begin
            n_ep = ep;
            @(negedge clk); rst_n=0; cfg_v=0; desc_v=0; launch_v=0; quiet; idle(1+rnd(3)); @(negedge clk); rst_n=1;
            idle(rnd(4));
            nrows = 1 + rnd(4); b = rnd(128-nrows+1); lim = b + nrows;
            for (r=b; r<lim; r=r+1) begin
                load_row(r, b, lim, r==lim-1, (rnd(4)==0) ? 30 : 100000);
                g = (rnd(3)==0) ? rnd(58) : 54 + rnd(6);              // drain is 54 edges: hit the completion edge
                if (rnd(5)==0) begin idle(g); frame(r, rnd(7), {192'b0, meta(r,b,lim,1)}, 0); end   // rewrite a loaded row
                else idle(g);
            end
            if (rnd(8)==0) idle(rnd(4)); else idle(rnd(2));
            // descriptor (sometimes wrong range / loops / target), then launch at a random distance from the scan end
            @(negedge clk); quiet; desc_v=1; cfg_target = (rnd(30)==0) ? 8'd51 : 8'd52;
            desc_base = (rnd(10)==0) ? rnd(140) : b; desc_limit = (rnd(10)==0) ? rnd(140) : lim;
            desc_loops = (rnd(20)==0) ? 2 : 1;
            if (rnd(15)==0) cfg_v=1;
            @(negedge clk); desc_v=0; cfg_v=0;
            if (rnd(6)==0) begin idle(rnd(130)); frame(rnd(128), rnd(7), 0, 0); end
            idle((rnd(4)==0) ? rnd(140) : 128 + rnd(8));
            @(negedge clk); quiet; launch_v=1; cfg_target=8'd52; @(negedge clk); launch_v=0;
            idle(5 + rnd(30));
            if (rnd(3)==0) begin @(negedge clk); quiet; launch_v=1; @(negedge clk); launch_v=0; idle(rnd(10)); end
        end
        idle(4);
        $display("PT_S128_COVER episodes %0d cycles %0d faults %0d configured %0d starts %0d fwd_frames %0d", `PT_EPISODES, cyc, n_fault, n_conf, n_start, n_fwd);
        if (mism==0 && n_conf>0 && n_start>0 && n_fault>0) $display("PT_S128_MITER PASS checks %0d", cyc);
        else $display("PT_S128_MITER FAIL mismatches %0d", mism);
        $finish;
    end
endmodule
`default_nettype wire
