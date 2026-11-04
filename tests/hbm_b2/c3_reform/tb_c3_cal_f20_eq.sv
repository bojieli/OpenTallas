`timescale 1ns/1ps
`default_nettype none
// DIE-HBM-61 RE-FORM C3 11-03: hfd_hgi_vm_calendar_f20 (FREE_PAYLOAD=1) == origin/main hfd_hgi_vm_calendar_f20 (renamed
// *_old) on EVERY edge, all outputs, shift 0. Random F20 traffic: legal rows, bad magic/address, out-of-range rows,
// neighbour ids, descriptors (valid/invalid/reuse), early/late launches, writes during scan/active, random resets.
module tb_c3_cal_f20_eq;
    parameter integer SEED=7, NCYC=60000;
    localparam [7:0] T=8'd57;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, cfg_v=0, desc_v=0, launch_v=0;
    reg [7:0] cfg_target=0; reg [11:0] cfg_addr=0, desc_base=0; reg [255:0] cfg_data=0; reg [12:0] desc_limit=0; reg [15:0] desc_loops=0;
    wire [186:0] rf, df; wire [31:0] r_ord, d_ord;
    wire r_v,r_act,r_done,r_fault,r_conf,r_tf, d_v,d_act,d_done,d_fault,d_conf,d_tf;
`define C3_F20(M,N,F,V,A,D,FL,C,TF,O) M N(.clk(clk),.clk_cap(clk),.clk_mem(clk),.clk_tgt(clk),.rst_n(rst_n),.tgt(T),.cfg_v(cfg_v), \
        .cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit), \
        .desc_loops(desc_loops),.launch_v(launch_v),.tgt_configured(C),.tgt_fault(TF),.calendar_v(V),.active(A),.done(D), \
        .fault(FL),.ordinal(O),.client_seq(F[0+:10]),.response_enable(F[10+:5]),.response_seq(F[15+:10]),.bank_enable(F[25+:8]), \
        .bank_client(F[33+:24]),.hub_ring_enable(F[57+:2]),.hub_ring_client(F[59+:6]),.rslot_v(F[65+:8]),.wslot_v(F[73+:8]), \
        .rslot(F[81+:24]),.wslot(F[105+:24]),.ring_tx_enable(F[129+:2]),.ring_tx_source(F[131+:6]),.replay_enable(F[137]), \
        .replay_source(F[138]),.lg_local_read(F[139+:24]),.lg_local_write(F[163+:24]));
    `C3_F20(hfd_hgi_vm_calendar_f20_old, ref_f20, rf, r_v, r_act, r_done, r_fault, r_conf, r_tf, r_ord)
    `C3_F20(hfd_hgi_vm_calendar_f20, dut, df, d_v, d_act, d_done, d_fault, d_conf, d_tf, d_ord)
    integer off=0, errors=0, checked=0, active_edges=0, launches=0, tfaults=0, resets=0, seed, cyc=0, n, i, k;
    always @(negedge clk) if (rst_n) begin
        checked=checked+1;
        if ({df,d_v,d_act,d_done,d_fault,d_conf,d_tf,d_ord} !== {rf,r_v,r_act,r_done,r_fault,r_conf,r_tf,r_ord}) begin
            errors=errors+1; if (errors<5) $display("MISMATCH t=%0t v %b/%b act %b/%b conf %b/%b tf %b/%b f %b/%b", $time,
                d_v,r_v,d_act,r_act,d_conf,r_conf,d_tf,r_tf,d_fault,r_fault);
        end
        if (r_v && rf!=0) active_edges=active_edges+1;
        if (ref_f20.p_sv) launches=launches+1;
        if (r_tf) tfaults=tfaults+1;
    end
    task automatic tick; begin @(posedge clk); #1; cyc=cyc+1; cfg_v=0; desc_v=0; launch_v=0; end endtask
    task automatic row(input [11:0] a, input integer bad); reg [255:0] d; begin
        d={$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
        d[255:240]=16'hc7a1; d[239:224]={4'b0,a}; if (($random(seed)&63)!=0) d[223:187]=0;
        if (bad==1) d[255:240]=16'hc7a0; if (bad==2) d[239:224]=d[239:224]^16'h1;
        cfg_v=1; cfg_target=(($random(seed)&7)==0)?T+8'd1:T; cfg_addr=a; cfg_data=d; tick;
    end endtask
    initial begin
        seed=SEED; repeat(3) tick; rst_n=1; repeat(4) tick;
        while (cyc<NCYC) begin
            k=$random(seed)&63;
            if (k==0 || r_tf || r_fault) begin rst_n=0; resets=resets+1; repeat(2) tick; rst_n=1; repeat(3) tick; end
            n = 1 + ($random(seed) & 31); off = {$random(seed)} % (1024 - n);   // rows anywhere in the 1024-row bitmap
            for (i=0; i<n; i=i+1) begin
                row(12'(off+i), (($random(seed)&31)==0) ? 1+($random(seed)&1) : 0);
                if (($random(seed)&3)==0) tick;
                if (($random(seed)&63)==0) row(12'd1024+($random(seed)&15), 0);   // out-of-range row
            end
            desc_v=1; cfg_target=(($random(seed)&15)==0)?T+8'd1:T; desc_base=12'(off+((($random(seed)&7)==0)?($random(seed)&7):0));
            desc_limit=13'(off+((($random(seed)&15)==0)?n+1:n)); desc_loops=(($random(seed)&31)==0)?0:1+($random(seed)&1); tick;
            if (($random(seed)&7)==0) row(12'(off+($random(seed)&31)), 0);         // write during scan
            repeat((($random(seed)&7)==0) ? ($random(seed)&7) : n+8) tick;          // early launch sometimes
            launch_v=1; cfg_target=T; tick;
            if (($random(seed)&7)==0) begin repeat($random(seed)&15) tick; row(12'(off+($random(seed)&31)), 0); end  // write while active
            if (($random(seed)&3)==0) begin   // descriptor-only rearm (reuse)
                repeat(n*3+10) tick; desc_v=1; cfg_target=T; tick; repeat(n+8) tick; launch_v=1; tick;
            end
            repeat(n*3+20) tick;
        end
        $display("C3_CAL_EQ %s errors=%0d checks=%0d active_edges=%0d launches=%0d tfault_edges=%0d resets=%0d",
            (errors==0 && active_edges>0 && launches>0) ? "PASS" : "FAIL", errors, checked, active_edges, launches, tfaults, resets);
        $finish;
    end
endmodule
`default_nettype wire
