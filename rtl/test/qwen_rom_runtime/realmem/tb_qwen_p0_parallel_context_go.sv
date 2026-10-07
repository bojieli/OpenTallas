`timescale 1ps/1fs
// Early-go handshake gate for ot_qwen_p0_parallel_transport_context.
// MODE 0: descriptor and GO in the same cycle (rm_early_go); MODE 1: GO one cycle after
// the descriptor (regression); MODE 2: GO with no descriptor (negative control, must fault).
// MODE 3: no stimulus (idle control). MODE/EXPECT_FAULT may be overridden at run
// time with +MODE=<n> +EXPECT_FAULT=<n>, so one build per SCG covers every case.
// EXPECT_FAULT is the expected fault outcome; the bench fails if it differs.
// Faults are sampled only after POR release: before the first reset edge the
// complementary checked-state registers hold simulator init values (primary==inverse),
// which reads as a state upset. That pre-reset read was the earlier false FAIL.
module tb_qwen_p0_parallel_context_go #(parameter integer MODE=0, SCG=1, EXPECT_FAULT=0);
    reg clk=0,hclk=0,por=1,warm=1;
    integer mode=MODE, expect_fault=EXPECT_FAULT;
    initial begin #1 por=0; end // a real POR edge at time 1
    always begin #416.666 clk=1;#416.667 clk=0;end
    always #512 hclk=~hclk;
    reg d_v=0,go=0; reg [18:0] d_row=0; reg [10:0] d_n=16;
    wire d_rdy,fault,quiet;
    wire [127:0] l_v,w_room,wd_v,row_v,col_v,col_we,busy,h_cv;
    wire [128*17-1:0] l_sec; wire [128*8-1:0] l_row; wire [128*256-1:0] l_data;
    wire [128*9-1:0] wd_tag,h_ctag; wire [128*3-1:0] row_op,h_cred_ret;
    wire [128*5-1:0] row_bank,col_bank,col_col; wire [128*19-1:0] row_row;
    wire [3:0] h_desc_commit,h_go_commit; wire [11:0] h_desc_ordinal,h_go_ordinal;
    wire [128*24-1:0] h_csec; wire [128*256-1:0] h_cdata;
    ot_qwen_p0_parallel_transport_context #(.ENABLE(1),.CDC_CONSUMER_JOIN(1),.LANDING_RSEL(1),.LOCAL_WIRE_SPANS(0),.SAME_CYCLE_GO(SCG)) dut(
        .clk(clk),.hclk(hclk),.rst_n(por),.warm_rst_n(warm),.d_v(d_v),.go(go),.d_row(d_row),.d_n(d_n),
        .d_rdy(d_rdy),.fault(fault),.quiet(quiet),.l_v(l_v),.l_sec(l_sec),.l_row(l_row),.l_data(l_data),
        .l_pop(128'b0),.w_v(128'b0),.wd_accept(128'b0),.w_sec('0),.w_data('0),.w_tag('0),.w_room(w_room),.wd_v(wd_v),.wd_tag(wd_tag),
        .h_lv(128'b0),.h_av(128'b0),.h_lsec('0),.h_lrow('0),.h_ldata('0),.h_atag('0),.phy_fault(1'b0),
        .row_v(row_v),.col_v(col_v),.col_we(col_we),.busy(busy),.row_op(row_op),.row_bank(row_bank),.col_bank(col_bank),
        .col_col(col_col),.row_row(row_row),.h_cred_ret(h_cred_ret),.h_desc_commit(h_desc_commit),.h_go_commit(h_go_commit),
        .h_desc_ordinal(h_desc_ordinal),.h_go_ordinal(h_go_ordinal),.h_cv(h_cv),.h_csec(h_csec),.h_cdata(h_cdata),.h_ctag(h_ctag));
    reg [3:0] dseen=0,gseen=0; reg fseen=0;
    always @(posedge hclk) begin dseen<=dseen|h_desc_commit; gseen<=gseen|h_go_commit; end
    always @(posedge clk) if(por && fault) begin
        if(!fseen) $display("FAULT first at %t: ctl_cf=%b state_bad=%b state5=%b hf=%b pc_cf0=%h cb_bad0=%b state0=%b",$time,
            {dut.active.stack[3].ctl_cf,dut.active.stack[2].ctl_cf,dut.active.stack[1].ctl_cf,dut.active.stack[0].ctl_cf},
            {dut.active.stack[3].state_bad,dut.active.stack[2].state_bad,dut.active.stack[1].state_bad,dut.active.stack[0].state_bad},
            {dut.active.stack[3].state[5],dut.active.stack[2].state[5],dut.active.stack[1].state[5],dut.active.stack[0].state[5]},
            {dut.active.stack[3].hf_sync[1],dut.active.stack[2].hf_sync[1],dut.active.stack[1].hf_sync[1],dut.active.stack[0].hf_sync[1]},
            dut.active.stack[0].pc_cf, dut.active.stack[0].cb_bad, dut.active.stack[0].state);
        fseen<=1; end
    initial begin
        if($value$plusargs("MODE=%d",mode)) ; if($value$plusargs("EXPECT_FAULT=%d",expect_fault)) ;
        repeat(4)@(negedge clk); por=1; repeat(64)@(negedge clk);
        wait(d_rdy); @(negedge clk);
        if(mode==0) begin d_v=1;go=1; @(negedge clk); d_v=0;go=0; end
        else if(mode==1) begin d_v=1; @(negedge clk); d_v=0;go=1; @(negedge clk); go=0; end
        else if(mode==2) begin go=1; @(negedge clk); go=0; end
        repeat(400)@(negedge clk);
        $display("MODE=%0d SCG=%0d fault=%0d dseen=%x gseen=%x", mode, SCG, fseen, dseen, gseen);
        if(fseen!==expect_fault[0]) $fatal(1,"fault outcome %0d != expected %0d", fseen, expect_fault);
        if(!expect_fault && mode<2 && (dseen!=4'hf)) $fatal(1,"descriptor not consumed by all four stacks");
        if(!expect_fault && mode<2 && (gseen!=4'hf)) $fatal(1,"GO not consumed by all four stacks");
        $display("TB PASS"); $finish;
    end
endmodule
