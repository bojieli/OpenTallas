`timescale 1ns/1ps
`default_nettype none
// H-NETLIST 0600: folded calendar+target master hfd_hgi_vm_calendar_f20 (strap tgt) == the die's former two-tile
// composition ot_static_program_target #(TARGET=T) -> hfd_hgi_vm_calendar on EVERY edge (all outputs incl.
// configured/fault), under F20 traffic to this and to a neighbouring target id. MUT=1: strap off by one (must differ).
module tb_vm_calendar_f20_eq;
    parameter integer MUT=0, SEED=7;
    localparam [7:0] T=8'd57;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, cfg_v=0, desc_v=0, launch_v=0;
    reg [7:0] cfg_target=0; reg [11:0] cfg_addr=0, desc_base=0; reg [255:0] cfg_data=0; reg [12:0] desc_limit=0; reg [15:0] desc_loops=0;
    // reference two-tile composition
    wire r_we,r_sv; wire [9:0] r_wa,r_sb; wire [255:0] r_wd; wire [10:0] r_sl; wire [15:0] r_lp; wire r_conf,r_tf;
    wire [186:0] rf; wire r_v,r_act,r_done,r_fault; wire [31:0] r_ord;
    ot_static_program_target #(.TARGET(T),.PCW(10)) ref_t(.clk(clk),.rst_n(rst_n),.tgt(8'd0),.cfg_v(cfg_v),.cfg_target(cfg_target),
        .cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),
        .launch_v(launch_v),.program_active(r_act),.program_cfg_we(r_we),.program_cfg_addr(r_wa),.program_cfg_data(r_wd),
        .program_start_v(r_sv),.program_start_base(r_sb),.program_start_limit(r_sl),.program_start_loops(r_lp),.configured(r_conf),.fault(r_tf));
    hfd_hgi_vm_calendar ref_c(.clk(clk),.clk_cap(clk),.clk_mem(clk),.rst_n(rst_n),.cfg_we(r_we),.cfg_addr(r_wa),.cfg_data(r_wd),
        .start_v(r_sv),.start_base(r_sb),.start_limit(r_sl),.start_loops(r_lp),.calendar_v(r_v),.active(r_act),.done(r_done),.fault(r_fault),
        .ordinal(r_ord),.client_seq(rf[0+:10]),.response_enable(rf[10+:5]),.response_seq(rf[15+:10]),.bank_enable(rf[25+:8]),
        .bank_client(rf[33+:24]),.hub_ring_enable(rf[57+:2]),.hub_ring_client(rf[59+:6]),.rslot_v(rf[65+:8]),.wslot_v(rf[73+:8]),
        .rslot(rf[81+:24]),.wslot(rf[105+:24]),.ring_tx_enable(rf[129+:2]),.ring_tx_source(rf[131+:6]),.replay_enable(rf[137]),
        .replay_source(rf[138]),.lg_local_read(rf[139+:24]),.lg_local_write(rf[163+:24]));
    // device under test
    wire [186:0] df; wire d_v,d_act,d_done,d_fault,d_conf,d_tf; wire [31:0] d_ord;
    hfd_hgi_vm_calendar_f20 dut(.clk(clk),.clk_cap(clk),.clk_mem(clk),.clk_tgt(clk),.rst_n(rst_n),.tgt(MUT==1?T+8'd1:T),.cfg_v(cfg_v),
        .cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),
        .desc_loops(desc_loops),.launch_v(launch_v),.tgt_configured(d_conf),.tgt_fault(d_tf),.calendar_v(d_v),.active(d_act),.done(d_done),
        .fault(d_fault),.ordinal(d_ord),.client_seq(df[0+:10]),.response_enable(df[10+:5]),.response_seq(df[15+:10]),.bank_enable(df[25+:8]),
        .bank_client(df[33+:24]),.hub_ring_enable(df[57+:2]),.hub_ring_client(df[59+:6]),.rslot_v(df[65+:8]),.wslot_v(df[73+:8]),
        .rslot(df[81+:24]),.wslot(df[105+:24]),.ring_tx_enable(df[129+:2]),.ring_tx_source(df[131+:6]),.replay_enable(df[137]),
        .replay_source(df[138]),.lg_local_read(df[139+:24]),.lg_local_write(df[163+:24]));
    reg [186:0] pay;
    integer errors=0, checked=0, active_edges=0, i, l, seed, n;
    always @(negedge clk) if (rst_n) begin
        checked=checked+1;
        if ({df,d_v,d_act,d_done,d_fault,d_conf,d_tf,d_ord} !== {rf,r_v,r_act,r_done,r_fault,r_conf,r_tf,r_ord}) begin
            errors=errors+1; if (errors<5) $display("MISMATCH t=%0t v %b/%b act %b/%b conf %b/%b tf %b/%b", $time,d_v,r_v,d_act,r_act,d_conf,r_conf,d_tf,r_tf);
        end
        if (r_v && rf!=0) active_edges=active_edges+1;
    end
    task automatic tick; begin @(posedge clk); #1; end endtask
    task automatic cfg(input [7:0] t, input [11:0] a, input [255:0] d); begin cfg_v=1; cfg_target=t; cfg_addr=a; cfg_data=d; tick; cfg_v=0; tick; end endtask
    initial begin
        seed=SEED; repeat(3) tick; rst_n=1; repeat(4) tick;
        for (l=0; l<6; l=l+1) begin
            n = 8 + ($random(seed) & 31);
            for (i=0; i<n; i=i+1) begin
                pay = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
                cfg(T, i[11:0], {16'hc7a1, 6'd0, i[9:0], 37'd0, pay});
                if (($random(seed) & 3)==0) cfg(T+8'd1, i[11:0], {8{$random(seed)}});   // neighbour id traffic
            end
            desc_v=1; cfg_target=T; desc_base=0; desc_limit=n[12:0]; desc_loops=1+($random(seed)&1); tick; desc_v=0;
            repeat(n+8) tick;                       // installed-row scan before configured
            launch_v=1; tick; launch_v=0;
            repeat(n*3+20) tick;
        end
        if (errors==0 && active_edges>0) $display("CAL_F20_EQ PASS checks=%0d active_edges=%0d", checked, active_edges);
        else begin $display("CAL_F20_EQ FAIL errors=%0d checks=%0d active_edges=%0d", errors, checked, active_edges); $fatal(1,"eq"); end
        $finish;
    end
endmodule
`default_nettype wire
