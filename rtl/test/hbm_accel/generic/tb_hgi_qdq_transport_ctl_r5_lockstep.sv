`timescale 1ns/1ps
`default_nettype none
// HBM-HUB-RTL-1 11-11 (DIE-HBM-100 ruling (B)): bench of ot_hgi_qdq_transport_ctl_r5 (256-entry ring A, RLI 2..254).
// Both DUTs see a fixed-latency VM model: bank b answers rr_v[b] exactly L edges after its rq[b] valid (+L plusarg).
//   +MODE=0  lockstep: ctl_r4 (reference, signed design) and ctl_r5 on the same strap +RLI (<= 126), same commands;
//            every output compared cycle for cycle (reset-cleared outputs from reset release, data outputs after the
//            power-up flush); ring SRAMs and pointers start RANDOM in both.
//   +MODE=1  ctl_r5 alone at +RLI (any 2..254): no fault, every command decoded in order (dec_header op/block FIFO),
//            beat_done / record_done counts = commands / last commands.
// Both modes print FAULT_AT=<cycle or -1>; a fault must be sticky (never clears before reset).  The run script sweeps L
// to find the pass latency and runs the +0 / +2 controls.  MUT (parameter) = ring A read one entry late (r5 only).
module tb_hgi_qdq_transport_ctl_r5_lockstep #(parameter integer MUT=0);
    reg clk=0; always #1 clk=~clk;
    reg rst_n=0;
    integer MODE, RLI, L, NCMD, SEED, cyc=0;
    reg [7:0] rl8; reg [5:0] wc6;
    reg cmd_v=0, cmd_last=0; reg [5:0] cmd_op=0; reg [7:0] cmd_block=0; reg [15:0] cmd_src=0, cmd_dst=0;
    wire [8*17-1:0] rq4, rq5; wire [7:0] wqv4, wqv5; wire [8*16-1:0] wqa4, wqa5; wire [8*8-1:0] wqm4, wqm5;
    wire [2:0] rs4, rs5, ws4, ws5; wire bd4, bd5, rd4, rd5, f4, f5, dv4, dv5; wire [127:0] dh4, dh5;
    reg [7:0] rr4 [0:511]; reg [7:0] rr5 [0:511];   // VM model delay lines (index = edges since the request)
    reg [511:0] vo4_d, vo5_d;
    wire [7:0] rrv4 = rr4[L-1], rrv5 = rr5[L-1];
    wire vo4 = vo4_d[24], vo5 = vo5_d[24];          // decoder model: vo = dec_v DL (25) edges later, no qfault
    ot_hgi_qdq_transport_ctl_r4 #(.DL(25),.MUT(0)) u4(.clk(clk),.rst_n(rst_n),.rl_cfg(rl8[6:0]),.wc_cfg(wc6),
        .cmd_v(cmd_v),.cmd_op(cmd_op),.cmd_block(cmd_block),.cmd_src(cmd_src),.cmd_dst(cmd_dst),.cmd_last(cmd_last),
        .rq(rq4),.rr_v(rrv4),.wq_v(wqv4),.wq_addr(wqa4),.wq_mask(wqm4),.rsel(rs4),.wsel(ws4),.beat_done(bd4),
        .record_done(rd4),.fault(f4),.dec_v(dv4),.dec_header(dh4),.vo(vo4),.qfault(1'b0),.decode_fault(1'b0));
    ot_hgi_qdq_transport_ctl_r5 #(.DL(25),.MUT(MUT)) u5(.clk(clk),.rst_n(rst_n),.rl_cfg(rl8),.wc_cfg(wc6),
        .cmd_v(cmd_v),.cmd_op(cmd_op),.cmd_block(cmd_block),.cmd_src(cmd_src),.cmd_dst(cmd_dst),.cmd_last(cmd_last),
        .rq(rq5),.rr_v(rrv5),.wq_v(wqv5),.wq_addr(wqa5),.wq_mask(wqm5),.rsel(rs5),.wsel(ws5),.beat_done(bd5),
        .record_done(rd5),.fault(f5),.dec_v(dv5),.dec_header(dh5),.vo(vo5),.qfault(1'b0),.decode_fault(1'b0));
    function automatic [7:0] vbits(input [8*17-1:0] rq);
        for(integer b=0;b<8;b=b+1) vbits[b]=rq[b*17+16];
    endfunction
    always @(posedge clk) begin
        rr4[0]<=vbits(rq4); rr5[0]<=vbits(rq5);
        for(integer i=1;i<512;i=i+1) begin rr4[i]<=rr4[i-1]; rr5[i]<=rr5[i-1]; end
        vo4_d<={vo4_d[510:0],dv4}; vo5_d<={vo5_d[510:0],dv5};
    end
    // power-up: random ring contents, commit rings and write pointers (after the macro models' own zero init)
    initial begin
        #0.5;
        for(integer i=0;i<128;i=i+1) u4.u_ctl.ring.arr[i]={$random,$random};
        for(integer i=0;i<128;i=i+1) u5.u_ctl.ring.arr[i]={$random,$random,$random,$random};
        for(integer i=0;i<64;i=i+1) begin u4.u_ctl.commit.arr[i]=16'($random); u5.u_ctl.commit.arr[i]=16'($random); end
        u4.u_ctl.wp=7'($random); u5.u_ctl.wp=8'($random);
        for(integer i=0;i<512;i=i+1) begin rr4[i]=0; rr5[i]=0; end
        vo4_d=0; vo5_d=0;
    end
    // checks
    integer fault_at=-1, ncmd=0, nlast=0, nbd=0, nrd=0, ndec=0, wr=0, rp=0, compared=0;
    reg [13:0] hq [0:65535];
    task automatic fail(input string s); begin $display("FAIL CTL_R5 %s cycle%0d", s, cyc); $fatal(1, "CTL_R5_FAIL"); end endtask
    always @(negedge clk) if(rst_n) begin
        if(MODE==0) begin
            if(vbits(rq4)!==vbits(rq5) || wqv4!==wqv5 || bd4!==bd5 || rd4!==rd5 || f4!==f5 || dv4!==dv5)
                fail($sformatf("LOCKSTEP control outputs r4 %h %h %b%b%b%b r5 %h %h %b%b%b%b",vbits(rq4),wqv4,bd4,rd4,f4,dv4,
                     vbits(rq5),wqv5,bd5,rd5,f5,dv5));
            if(cyc>=320) begin
                if(rq4!==rq5 || wqa4!==wqa5 || wqm4!==wqm5 || rs4!==rs5 || ws4!==ws5 || dh4!==dh5)
                    fail("LOCKSTEP data outputs");
                compared=compared+1;
            end
        end
        if(f5 && fault_at<0) fault_at=cyc;
        if(fault_at>=0 && !f5) fail("fault not sticky");
        if(bd5) nbd=nbd+1;
        if(rd5) nrd=nrd+1;
        if(dv5 && fault_at<0) begin
            if(rp>=wr) fail("dec_v without a command");
            if({dh5[123:118],dh5[71:64]}!==hq[rp] || dh5[127:124]!==4'd4)
                fail($sformatf("dec_header %h expected op/block %h", {dh5[123:118],dh5[71:64]}, hq[rp]));
            rp=rp+1; ndec=ndec+1;
        end
    end
    // stimulus
    initial begin
        if(!$value$plusargs("MODE=%d",MODE)) MODE=0;
        if(!$value$plusargs("RLI=%d",RLI)) RLI=126;
        if(!$value$plusargs("L=%d",L)) L=100;
        if(!$value$plusargs("NCMD=%d",NCMD)) NCMD=3000;
        if(!$value$plusargs("SEED=%d",SEED)) SEED=1;
        if(L<1 || L>512) $fatal(1,"L 1..512");
        void'($urandom(SEED));
        rl8=8'(RLI); wc6=6'd18;
        repeat(20) @(posedge clk);
        @(negedge clk) rst_n=1;
        repeat(10) @(negedge clk);
        while(ncmd<NCMD) begin
            @(negedge clk);
            cmd_v=($urandom%3)!=0;
            case($urandom%3) 0: begin cmd_op=4; cmd_block=8'($urandom); end 1: begin cmd_op=5; cmd_block=8'($urandom); end
                default: begin cmd_op=6; cmd_block=16; end endcase
            cmd_src={13'($urandom),3'($urandom%5)}; cmd_dst={13'($urandom),3'($urandom%5)};
            cmd_last=($urandom%4)==0;
            if(cmd_v) begin hq[wr]={cmd_op,cmd_block}; wr=wr+1; ncmd=ncmd+1; if(cmd_last) nlast=nlast+1; end
        end
        @(negedge clk) cmd_v=0;
        repeat(RLI+L+120) @(negedge clk);
        $display("FAULT_AT=%0d MODE=%0d RLI=%0d L=%0d cmds=%0d last=%0d dec=%0d beat_done=%0d record_done=%0d compared=%0d",
            fault_at, MODE, RLI, L, ncmd, nlast, ndec, nbd, nrd, compared);
        if(fault_at<0) begin
            if(ndec!=ncmd || nbd!=ncmd || nrd!=nlast) fail("accounting");
            $display("PASS CTL_R5 MODE=%0d RLI=%0d L=%0d", MODE, RLI, L);
        end
        $finish;
    end
    always @(posedge clk) cyc<=cyc+1;
    initial begin repeat(200000) @(negedge clk); $fatal(1,"CTL_R5_FAIL watchdog"); end
endmodule
`default_nettype wire
