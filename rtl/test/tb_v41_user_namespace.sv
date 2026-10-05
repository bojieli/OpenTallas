`timescale 1ns/1ps
module tb_v41_user_namespace;
`ifdef FULL_NW21
    localparam integer NW=21;
`else
    localparam integer NW=16;
`endif
    localparam integer FLIT=512, MAXU=866, USER_W=10, VWA=20, AW=30;
    localparam integer HDR_IDX=40+NW, HDR_VAL=HDR_IDX+NW,
        HDR_TOK=HDR_VAL+32, HDR_ADDR=HDR_TOK+NW, HDR_USER_HI=HDR_ADDR+16;
    reg clk=0, rst_n=0;
    always #5 clk=~clk;
    reg in_valid=0, in_last=0;
    reg [FLIT-1:0] in_data=0;
    wire in_ready, out_valid, out_last, core_start, core_busy, vm_we, vm_re;
    wire [FLIT-1:0] out_data, vm_wdata;
    wire [VWA-1:0] vm_waddr, vm_raddr;
    wire [AW-1:0] kv_base;
    wire [USER_W-1:0] core_user, tok_user;
    wire [NW-1:0] core_token, core_pos, tok_pos, tok_id;
    wire [9:0] users_done;
    wire proto_fault;
    ot_rom_pkg_ctrl_x #(.MAXU(MAXU), .USER_W(USER_W), .NW(NW), .AW(AW), .VWA(VWA),
        .KVW(1024), .XWORDS(1), .RXWORDS(1), .SOURCE(0), .FWD_TOKEN(1),
        .SIDE_IN(1), .SIDE_USH(10), .SIDE_RXB(7), .SEND_HIDDEN(1)) dut (
        .clk(clk), .rst_n(rst_n), .cfg_users(10'd0), .cfg_prompt_len(NW'(1)), .cfg_gen_len(NW'(1)),
        .in_valid(in_valid), .in_ready(in_ready), .in_data(in_data), .in_last(in_last),
        .out_valid(out_valid), .out_ready(1'b1), .out_data(out_data), .out_last(out_last),
        .core_start(core_start), .core_token(core_token), .core_pos(core_pos),
        .core_user(core_user), .core_done(core_busy), .core_next_token(NW'(2)),
        .core_next_val(32'h3f800000), .kv_base(kv_base),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .vm_re(vm_re), .vm_raddr(vm_raddr), .vm_rq(512'd0),
        .pr_re(), .pr_user(), .pr_pos(), .pr_q(NW'(0)),
        .core_busy(core_busy), .tok_valid(), .tok_user(tok_user),
        .tok_pos(tok_pos), .tok_id(tok_id), .users_done(users_done), .proto_fault(proto_fault));

    wire src_start, src_busy, src_fault, src_pr_re;
    reg src_in_valid=0, src_in_last=0;
    reg [FLIT-1:0] src_in_data=0;
    wire src_in_ready;
    wire [USER_W-1:0] src_user, src_pr_user;
    wire [AW-1:0] src_kv_base;
    wire [9:0] src_users_done;
    ot_rom_pkg_ctrl_x #(.MAXU(MAXU), .USER_W(USER_W), .NW(NW), .AW(AW), .VWA(VWA),
        .KVW(1024), .XWORDS(1), .SOURCE(1), .SEND_HIDDEN(0), .SEND_RESULT(0)) source (
        .clk(clk), .rst_n(rst_n), .cfg_users(10'd866), .cfg_prompt_len(NW'(1)), .cfg_gen_len(NW'(0)),
        .in_valid(src_in_valid), .in_ready(src_in_ready), .in_data(src_in_data), .in_last(src_in_last),
        .out_valid(), .out_ready(1'b1), .out_data(), .out_last(),
        .core_start(src_start), .core_token(), .core_pos(), .core_user(src_user),
        .core_done(src_busy), .core_next_token(NW'(0)), .core_next_val(32'd0), .kv_base(src_kv_base),
        .vm_we(), .vm_waddr(), .vm_wdata(), .vm_re(), .vm_raddr(), .vm_rq(512'd0),
        .pr_re(src_pr_re), .pr_user(src_pr_user), .pr_pos(), .pr_q(NW'(11)),
        .core_busy(src_busy), .tok_valid(), .tok_user(), .tok_pos(), .tok_id(),
        .users_done(src_users_done), .proto_fault(src_fault));

    function automatic [FLIT-1:0] hdr(input [3:0] typ, input [USER_W-1:0] user);
        begin
            hdr=0;
            hdr[16 +: 4]=typ;
            hdr[24 +: 8]=1;
            hdr[32 +: 8]=user[7:0];
            hdr[HDR_USER_HI +: 2]=user[9:8];
            hdr[HDR_TOK +: NW]=NW'(16'h1234);
            hdr[HDR_ADDR +: 16]=7;
        end
    endfunction
    task automatic send(input [FLIT-1:0] data, input bit last);
        begin
            @(negedge clk); in_valid=1; in_data=data; in_last=last;
            @(posedge clk);
            if (!in_ready) $fatal(1,"unexpected inbound stall");
            @(negedge clk); in_valid=0; in_last=0;
        end
    endtask
    task automatic send_src(input [FLIT-1:0] data);
        begin
            @(negedge clk); src_in_valid=1; src_in_data=data; src_in_last=1;
            @(posedge clk);
            if (!src_in_ready) $fatal(1,"unexpected SOURCE inbound stall");
            @(negedge clk); src_in_valid=0; src_in_last=0;
        end
    endtask
    integer starts=0, side_writes=0, outbound=0, src_starts=0;
    reg [USER_W-1:0] expect_user [0:2];
    initial begin expect_user[0]=1; expect_user[1]=257; expect_user[2]=865; end
    always @(posedge clk) if (rst_n) begin
        if (src_start) begin
            if (src_starts >= 866 || source.st_user !== src_starts)
                $fatal(1,"SOURCE user scheduler alias at %0d got %0d",src_starts,source.st_user);
            src_starts=src_starts+1;
        end
        if (core_start) begin
            if (starts >= 3 || dut.st_user !== expect_user[starts] || core_token !== 16'h1234)
                $fatal(1,"core start user/token mismatch at %0d",starts);
            starts=starts+1;
        end
        if (vm_we && dut.rx_st == 2'd2) begin
            if (side_writes >= 3 || vm_waddr !== (expect_user[side_writes]*1024+7))
                $fatal(1,"SIDE alias: word %0d got %0d",side_writes,vm_waddr);
            side_writes=side_writes+1;
        end
        if (out_valid && out_data[16 +: 4] == 1) begin
            if (outbound >= 3 || {out_data[HDR_USER_HI +: 2],out_data[32 +: 8]} !== expect_user[outbound])
                $fatal(1,"outbound header user alias at %0d",outbound);
            outbound=outbound+1;
        end
    end
    integer j;
    initial begin
        repeat (3) @(negedge clk); rst_n=1;
        for (j=0;j<3;j=j+1) begin
            send(hdr(3,expect_user[j]),0);
            send(512'hdeadcafe,1);
            send(hdr(1,expect_user[j]),0);
            send(512'h55,1);
            repeat (8) @(negedge clk);
            if (core_user !== expect_user[j] || kv_base !== expect_user[j]*1024)
                $fatal(1,"running user/KV base mismatch user=%0d got=%0d base=%0d",expect_user[j],core_user,kv_base);
        end
        wait(src_starts==866);
        for (j=0;j<866;j=j+1) send_src(hdr(2,USER_W'(j)));
        repeat (8) @(negedge clk);
        if (starts!=3 || side_writes!=3 || outbound!=3 || proto_fault || src_fault ||
            src_pr_user !== 10'd865 || src_users_done !== 10'd866)
            $fatal(1,"namespace verdict starts=%0d side=%0d outbound=%0d source=%0d faults=%0b/%0b",starts,side_writes,outbound,src_starts,proto_fault,src_fault);
        send(hdr(3,10'd866),0);
        send(512'hbad,1);
        repeat (2) @(negedge clk);
        if (!proto_fault || side_writes!=3 || starts!=3)
            $fatal(1,"invalid user 866 aliased a valid context");
        $display("PASS v41 user namespace ids 1/257/865, SOURCE 866 contexts, invalid 866 rejected");
        $finish;
    end
    initial begin #200000; $fatal(1,"timeout"); end
endmodule
