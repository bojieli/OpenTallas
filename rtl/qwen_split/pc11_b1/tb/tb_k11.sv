`timescale 1ns/1ps
module tb_k11;
    localparam [58:0] TAG={16'd8,6'd1,18'd24,13'd8191,6'd0};
    localparam [1:0] GEN=2'd2;
    localparam [19:0] BASE=20'h2000;
    localparam [28:0] ADDR=29'h100ff;
    localparam TXDP=162;
    logic ck=0; always #5 ck=~ck;
    logic rst_n=0, begin_slot=0, request_slot=0, q_slot=0, result_slot=0, result_v=0;
    logic vm_commit_v=0, kernel_done=0, complete_slot=0;
    logic [4:0] beat=0; logic [511:0] result_data=0;
    int arm=0;
    wire en = arm!=8;
    // K side
    logic open=0, pcc_commit=0, k_slot=0, k_cap=0, mctx_k=0; logic [60:0] pcc_id={TAG,GEN}; logic [28:0] pcc_addr=ADDR;
    logic h_v=0; logic [547:0] h_rec=0;
    wire tx_v, tx_cap, k_fault; wire [547:0] tx_rec;
    qkd_pc11_b1_kind11_tx #(.TXDP(TXDP)) ktx(.ck,.rst_n,.enabled(en),.authorized(1'b1),.mctx(mctx_k),
        .parent_open(open),.parent_identity({TAG,GEN}),.parent_address(ADDR),.parent_user(2'd0),
        .pcc_commit,.pcc_identity(pcc_id),.pcc_address(pcc_addr),.port1_slot(k_slot),.slot_kind(4'd11),.slot_beat(5'd0),
        .slot_user(2'd0),.port1_capture(k_cap),.host_valid(h_v),.host_record(h_rec),.tx_valid(tx_v),.tx_record(tx_rec),
        .commit_capture(tx_cap),.fault(k_fault));
    // link: 20-cycle delay
    logic [20:0] vd=0; logic [547:0] rd [0:20];
    always @(posedge ck) begin vd<={vd[19:0],tx_v}; rd[0]<=tx_rec; for(int i=1;i<=20;i++) rd[i]<=rd[i-1]; end
    logic inj=0; logic [547:0] inj_rec=0; logic [3:0] inj_kind=4'd11; logic inj_port1=1;
    wire r_ev = vd[20] | inj;
    wire [547:0] r_rec0 = inj ? inj_rec : rd[20];
    wire [547:0] r_rec = r_rec0 ^ ((arm==2 && vd[20]) ? 548'd1 : 548'd0) ^ ((arm==6 && vd[20]) ? (548'd1<<61) : 548'd0)
                         ^ ((arm==5 && vd[20]) ? (548'd1<<(543-4+0)) : 548'd0);
    wire [3:0] c_kind = inj ? inj_kind : 4'd11;
    wire p1 = inj ? inj_port1 : 1'b1;
    logic mctx_c=0; logic aw=0;
    wire host_event, b1_ready, c_fault; wire [60:0] b1_id; wire [28:0] b1_addr;
    qfd_pc11_b1_kind11_rx crx(.ck,.rst_n,.enabled(en),.authorized(1'b1),.mctx(mctx_c),
        .awaited_parent_v(aw),.awaited_identity({TAG,GEN}),.awaited_address(ADDR),.awaited_user(2'd0),
        .port1_slot(r_ev&&p1),.port1_event(r_ev&&p1),.any_event(r_ev),.any_event_kind(c_kind),
        .slot_kind(r_ev?c_kind:4'd0),.slot_beat(5'd0),.slot_user(2'd0),.rx_record(r_rec),
        .host_event,.b1_ready,.b1_identity(b1_id),.b1_address(b1_addr),.fault(c_fault));
    wire [2:0] vm_write_v, completed, fault, acc, kreq;
    wire [2:0][19:0] vm_write_word; wire [2:0][511:0] vm_write_data; wire [2:0][24:0] vm_write_pub;
    for(genvar i=0;i<3;i++)begin:g_service
        qfd_native59_static_service_obs1 #(.LOCAL32(i==1),.PCC_B1(i!=2)) dut(
            .ck,.rst_n,.source_fault((i!=2) && c_fault),.begin_slot,.begin_tag(TAG),
            .request_slot,.request_tag(TAG),.result_base_word(BASE),.qr_committed(1'b1),.qr_tag(TAG),
            .request_generation(GEN),.pcc_b1_ready(b1_ready),.pcc_b1_identity(b1_id),.pcc_b1_result_accepted(acc[i]),
            .kernel_request_v(kreq[i]),.kernel_request_tag(),
            .q_slot,.q_slot_pub({76{q_slot}}),.q_slot_beat(beat),
            .q_v(q_slot),.q_beat(beat),.q_tag(TAG),.q_data(512'd0),
            .kernel_q_v(),.kernel_q_beat(),.kernel_q_tag(),.kernel_q_data(),
            .result_slot,.result_slot_pub({76{result_slot}}),.result_slot_beat(beat),
            .result_v,.result_beat(beat),.result_tag(TAG),.result_data,
            .kernel_request_pub(),.vm_write_pub(vm_write_pub[i]),.vm_write_v(vm_write_v[i]),
            .vm_write_word(vm_write_word[i]),.vm_write_beat(),.vm_write_tag(),.vm_write_data(vm_write_data[i]),
            .vm_commit_v,.vm_commit_beat(beat),.vm_commit_tag(TAG),
            .kernel_done,.kernel_done_tag(TAG),.completing(),.completed_tag(),.complete_slot,
            .completed(completed[i]),.active(),.fault(fault[i]),.native_ret(),
            .begin_pub({13{begin_slot}}),.request_pub({7{request_slot}}),.q_slot_beat_pub(beat),
            .result_slot_beat_pub(beat),.vm_commit_beat_pub(beat),.q_slot_beat_pub2(beat),
            .result_slot_beat_pub2(beat),.vm_commit_beat_pub2(beat),.q_slot_beat_pub3(beat),
            .result_slot_beat_pub3(beat),.vm_commit_beat_pub3(beat),.vm_commit_beat_pub4(beat));
    end
    int host_ev_n=0;
    always @(posedge ck) if (host_event) host_ev_n++;
    task step; @(posedge ck); #1; endtask
    // K/C link driver: parent open, PCC commit, slot, capture
    task link_run(input bit do_commit, input bit dup);
        @(negedge ck); open=1; aw=1; step(); @(negedge ck); open=0; aw=0;
        repeat(3) step();
        if (do_commit) begin @(negedge ck); pcc_commit=1; step(); @(negedge ck); pcc_commit=0; end
        @(negedge ck); k_slot=1; step(); @(negedge ck); k_slot=0;
        repeat(TXDP-2) step();
        @(negedge ck); k_cap=1; repeat(3) step(); @(negedge ck); k_cap=0;
        repeat(30) step();
        if (dup) begin
            @(negedge ck); inj=1; inj_rec=rd[20]; step(); @(negedge ck); inj=0; // placeholder replaced below
        end
    endtask
    logic [547:0] good_rec;
    initial begin
        if ($value$plusargs("ARM=%d",arm)) begin end
        repeat(3)@(negedge ck); rst_n=1;
        if (arm==7) begin mctx_c=1; end
        begin_slot=1; step(); @(negedge ck); begin_slot=0;
        request_slot=1; step(); @(negedge ck); request_slot=0;
        for(int i=0;i<32;i++)begin q_slot=1;beat=5'(i);step();@(negedge ck); end
        q_slot=0;
        if (arm!=3) begin
            if (arm==1) link_run(0,0); else link_run(1,0);
            if (arm==4) begin // duplicate: replay the exact accepted record once more as a second kind11 event
                good_rec = ktx.rec; @(negedge ck); inj=1; inj_rec=good_rec; step(); @(negedge ck); inj=0; repeat(3) step();
            end
            if (arm==9) begin // stray kind11 on another port
                @(negedge ck); inj=1; inj_port1=0; inj_rec=0; step(); @(negedge ck); inj=0; inj_port1=1; repeat(3) step();
            end
        end
        for(int i=0;i<32;i++)begin
            result_slot=1;result_v=1;beat=5'(i);result_data=512'(i+64);
            step();
            if (arm==0 || arm==8) begin
                if (arm==0 && (vm_write_v!==3'b111 || vm_write_pub[1]!==25'h1ffffff || fault)) $fatal(1,"valid kind11 result write blocked");
                if (arm==8 && (vm_write_v[1:0]!==2'b00 || vm_write_v[2]!==1'b1)) $fatal(1,"default-off must withhold B1 (no receipt) and leave plain copy");
            end else if (vm_write_v[1:0]!==2'b00 && arm!=4 && arm!=9) $fatal(1,"bad kind11 allowed protected write arm %0d beat %0d",arm,i);
            @(negedge ck); result_slot=0;result_v=0;vm_commit_v=1; step();@(negedge ck); vm_commit_v=0;
        end
        if (arm==3) begin link_run(1,0); end // late: receipt after all result beats
        kernel_done=1; step();@(negedge ck);kernel_done=0;
        complete_slot=1; step();
        if (arm==0 && (completed!=3'b111 || fault || host_ev_n!=0 || b1_addr!==ADDR || b1_id!=={TAG,GEN})) $fatal(1,"nominal failed completed=%b fault=%b",completed,fault);
        if ((arm==4||arm==9) && (!c_fault || (completed[1:0]!=0 && fault[1:0]==0))) $fatal(1,"duplicate/stray escaped arm %0d",arm);
        if ((arm==1||arm==2||arm==3||arm==5||arm==6||arm==7||arm==8) && completed[1:0]!=2'b00) $fatal(1,"bad kind11 arm %0d completed protected %b",arm,completed);
        if (arm!=0 && arm!=8 && !(c_fault || k_fault || arm==1 || arm==3)) $fatal(1,"arm %0d no fault flagged",arm);
        if (completed[2]!==1'b1 || fault[2]!==1'b0) $fatal(1,"plain copy must complete without fault arm %0d completed=%b fault=%b",arm,completed,fault);
        if (arm==3 && (completed[1:0]!==2'b00 || fault[1:0]!==2'b11)) $fatal(1,"late receipt: protected copies must fault and never complete (completed=%b fault=%b)",completed,fault);
        $display("K11_RESULT arm=%0d completed=%b fault=%b cfault=%b kfault=%b ready=%b host_ev=%0d",arm,completed,fault,c_fault,k_fault,b1_ready,host_ev_n);
        $finish;
    end
endmodule
