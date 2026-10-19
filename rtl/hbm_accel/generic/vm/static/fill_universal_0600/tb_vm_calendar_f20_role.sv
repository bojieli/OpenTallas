`timescale 1ns/1ps
`default_nettype none
// LH-UNREAD 10-19: hfd_hgi_vm_calendar_f20_role #(W) vs the universal hfd_hgi_vm_calendar_f20 (die master of record).
// Phase A (legal rows: payload random in [W-1:0], universal tail [186:W] zero): EVERY edge equal -- role payload ==
//   universal calendar[W-1:0], universal tail outputs == 0, calendar_v/active/done/fault/ordinal/tgt_configured/tgt_fault.
// Phase B (one row with ONE random tail bit in [186:W] set): the universal master EXPORTS the tail and does not fault;
//   the role master must raise its existing sticky fault and emit payload 0 for that row.
// MUT=1: device behaves as the universal (tail accepted) -> must FAIL. MUT=2: device payload bit0 flipped -> must FAIL.
module tb_vm_calendar_f20_role;
    parameter integer W=19, MUT=0, SEED=11;
    localparam [7:0] T=8'd132;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, cfg_v=0, desc_v=0, launch_v=0;
    reg [7:0] cfg_target=0; reg [11:0] cfg_addr=0, desc_base=0; reg [255:0] cfg_data=0; reg [12:0] desc_limit=0; reg [15:0] desc_loops=0;
    wire [186:0] rf; wire r_v,r_act,r_done,r_fault,r_conf,r_tf; wire [31:0] r_ord;
    hfd_hgi_vm_calendar_f20 uni(.clk(clk),.clk_cap(clk),.clk_mem(clk),.clk_tgt(clk),.rst_n(rst_n),.tgt(T),.cfg_v(cfg_v),
        .cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),
        .desc_loops(desc_loops),.launch_v(launch_v),.tgt_configured(r_conf),.tgt_fault(r_tf),.calendar_v(r_v),.active(r_act),.done(r_done),
        .fault(r_fault),.ordinal(r_ord),.client_seq(rf[0+:10]),.response_enable(rf[10+:5]),.response_seq(rf[15+:10]),.bank_enable(rf[25+:8]),
        .bank_client(rf[33+:24]),.hub_ring_enable(rf[57+:2]),.hub_ring_client(rf[59+:6]),.rslot_v(rf[65+:8]),.wslot_v(rf[73+:8]),
        .rslot(rf[81+:24]),.wslot(rf[105+:24]),.ring_tx_enable(rf[129+:2]),.ring_tx_source(rf[131+:6]),.replay_enable(rf[137]),
        .replay_source(rf[138]),.lg_local_read(rf[139+:24]),.lg_local_write(rf[163+:24]));
    wire [W-1:0] dp; wire d_v,d_act,d_done,d_fault,d_conf,d_tf; wire [31:0] d_ord;
    hfd_hgi_vm_calendar_f20_role #(.W(W)) dut(.clk(clk),.clk_cap(clk),.clk_mem(clk),.clk_tgt(clk),.rst_n(rst_n),.tgt(T),.cfg_v(cfg_v),
        .cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),
        .desc_loops(desc_loops),.launch_v(launch_v),.tgt_configured(d_conf),.tgt_fault(d_tf),.calendar_v(d_v),.active(d_act),.done(d_done),
        .fault(d_fault),.ordinal(d_ord),.payload(dp));
    // bench mutants act on the observed device outputs
    wire [W-1:0] dpay = MUT==1 ? rf[W-1:0] : MUT==2 ? (dp ^ {{(W-1){1'b0}}, d_v}) : dp;
    wire dfault = MUT==1 ? r_fault : d_fault;
    reg [186:0] pay;
    integer errors=0, checked=0, active_edges=0, i, l, seed, n, j, b, phase=0, tail_seen=0, bad_row_zero=0;
    always @(negedge clk) if (rst_n) begin
        checked=checked+1;
        if (phase==0) begin
            if ({dpay,d_v,d_act,d_done,dfault,d_conf,d_tf,d_ord} !== {rf[W-1:0],r_v,r_act,r_done,r_fault,r_conf,r_tf,r_ord} ||
                rf[186:W] !== 0) begin
                errors=errors+1; if (errors<5) $display("MISMATCH t=%0t pay %h/%h v %b/%b f %b/%b", $time,dpay,rf[W-1:0],d_v,r_v,dfault,r_fault);
            end
            if (r_v && rf!=0) active_edges=active_edges+1;
        end else begin
            if (r_v && rf[186:W]!=0) begin tail_seen=tail_seen+1; if (dpay==0) bad_row_zero=1; end
        end
    end
    task automatic tick; begin @(posedge clk); #1; end endtask
    task automatic cfg(input [7:0] t, input [11:0] a, input [255:0] d); begin cfg_v=1; cfg_target=t; cfg_addr=a; cfg_data=d; tick; cfg_v=0; tick; end endtask
    task automatic run(input integer rows); begin
        desc_v=1; cfg_target=T; desc_base=0; desc_limit=rows[12:0]; desc_loops=1+($random(seed)&1); tick; desc_v=0;
        repeat(rows+8) tick; launch_v=1; tick; launch_v=0; repeat(rows*3+20) tick; end endtask
    initial begin
        seed=SEED; repeat(3) tick; rst_n=1; repeat(4) tick;
        for (l=0; l<5; l=l+1) begin
            n = 8 + ($random(seed) & 31);
            for (i=0; i<n; i=i+1) begin
                pay = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
                pay = pay & ((187'd1 << W) - 1);
                cfg(T, i[11:0], {16'hc7a1, 6'd0, i[9:0], 37'd0, pay});
                if (($random(seed) & 3)==0) cfg(T+8'd1, i[11:0], {8{$random(seed)}});
            end
            run(n);
        end
        if (errors!=0 || active_edges==0 || dfault || r_fault) begin
            $display("CAL_F20_ROLE FAIL W=%0d phaseA errors=%0d checks=%0d active_edges=%0d", W, errors, checked, active_edges); $fatal(1,"A");
        end
        // phase B: one nonzero tail bit
        phase=1; n=12; j=$unsigned($random(seed))%n; b=W+($unsigned($random(seed))%(187-W));
        for (i=0; i<n; i=i+1) begin
            pay = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
            pay = (pay & ((187'd1 << W) - 1)) | 187'd1;              // nonzero legal payload on every row
            if (i==j) pay[b]=1'b1;
            cfg(T, i[11:0], {16'hc7a1, 6'd0, i[9:0], 37'd0, pay});
        end
        run(n);
        if (tail_seen>0 && !r_fault && dfault && bad_row_zero)
            $display("CAL_F20_ROLE PASS W=%0d checks=%0d active_edges=%0d tail_row=%0d tail_bit=%0d universal_exported_tail=%0d role_fault=1", W, checked, active_edges, j, b, tail_seen);
        else begin
            $display("CAL_F20_ROLE FAIL W=%0d phaseB tail_seen=%0d uni_fault=%b role_fault=%b row_zero=%0d", W, tail_seen, r_fault, dfault, bad_row_zero); $fatal(1,"B");
        end
        $finish;
    end
endmodule
`default_nettype wire
