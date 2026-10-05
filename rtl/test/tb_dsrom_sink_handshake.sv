`timescale 1ns/1ps
// Actual XU + actual Sinkhorn arithmetic. Six immediate SINK operations versus
// the unchanged legacy request protocol with enough drain between operations.
module tb_dsrom_sink_handshake;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;
    integer cyc=0,sent[0:1],received[0:1],accepts=0,pending_old_busy=0;
    wire [1:0] ready,go,w_we,fault,xr_re,sk_busy;
    wire [23:0] xr_addr[0:1],w_addr[0:1];
    wire [31:0] w_mask[0:1];
    wire [1023:0] w_data[0:1];
    reg [1023:0] xr_q[0:1];
    reg [511:0] captured[0:1][0:5];
    function automatic [511:0] input_matrix(input integer position);
        for(integer k=0;k<16;k=k+1)
            case((k+position)%4)
                0:input_matrix[k*32+:32]=32'h3f800000;
                1:input_matrix[k*32+:32]=32'h40000000;
                2:input_matrix[k*32+:32]=32'h40800000;
                3:input_matrix[k*32+:32]=32'h41000000;
            endcase
    endfunction
    genvar b;
    generate for(b=0;b<2;b=b+1) begin:g
        // Fixed XU launches as soon as ready, including the prior ov window.
        // Legacy reference waits for the original unit's complete drain.
        assign go[b]=rst_n && sent[b]<6 && ready[b] && (b==1 || !sk_busy[b]);
        ot_hdc_v41_xu #(.SK_ACCEPT_HANDSHAKE(b),.SK_STEP(7)) dut(
            .clk(clk),.rst_n(rst_n),.go(go[b]),.ready(ready[b]),.idle(),
            .i_op(2'd1),.i_src(24'(sent[b]*32)),.i_dst(24'(sent[b]*32)),.i_n(16'd16),.i_k(5'd0),.i_layer(1'b0),
            .token(16'd0),.first(1'b0),.i_hslot(3'd0),.rst_v(1'b0),.rst_slot(3'd0),
            .sel_first(),.prime_v(1'b0),.prime_first(1'b0),.prime_cid(12'd0),
            .vr_re(),.vr_addr(),.vr_q(32'd0),.xr_re(xr_re[b]),.xr_addr(xr_addr[b]),.xr_q(xr_q[b]),
            .vw_we(),.vw_addr(),.vw_data(),.w_we(w_we[b]),.w_addr(w_addr[b]),.w_mask(w_mask[b]),.w_data(w_data[b]),
            .cr_re(),.cr_addr(),.cr_q(64'd0),.er_re(),.er_addr(),.er_q(264'd0),.fault(fault[b]));
        assign sk_busy[b]=dut.sk_busy;
        always @(posedge clk) if(rst_n) begin
            if(go[b]) sent[b]<=sent[b]+1;
            if(xr_re[b]) xr_q[b]<={512'd0,input_matrix(32'(xr_addr[b])/32)};
            if(w_we[b]) begin
                if(received[b]>=6 || w_addr[b]!=24'(received[b]*32) || w_mask[b]!=32'hffff)
                    $fatal(1,"write identity/mask");
                captured[b][received[b]]=w_data[b][511:0];
                received[b]=received[b]+1;
            end
            if(fault[b]) $fatal(1,"fault");
        end
    end endgenerate
    reg [1023:0] held_input;
    reg holding=0;
    always @(posedge clk) if(rst_n) begin
        cyc<=cyc+1;
        if(g[1].dut.sk_accepted) accepts<=accepts+1;
        if(g[1].dut.sk_in && g[1].dut.sk_busy && !g[1].dut.sk_started) pending_old_busy<=pending_old_busy+1;
        if(holding && g[1].dut.sk_in && xr_q[1]!==held_input) $fatal(1,"pending input changed");
        holding<=g[1].dut.sk_in && !g[1].dut.sk_accepted;
        held_input<=xr_q[1];
        if(received[0]==6 && received[1]==6) begin
            for(integer k=0;k<6;k=k+1) if(captured[0][k]!==captured[1][k]) $fatal(1,"data mismatch op=%0d",k);
            if(accepts!=6 || pending_old_busy==0) $fatal(1,"accept/overlap coverage");
            $display("SINK_HANDSHAKE PASS operations=6 accepted=%0d old_busy_pending_cycles=%0d exact_words=96 cycles=%0d",accepts,pending_old_busy,cyc);
            $finish;
        end
    end
    initial begin
        for(integer k=0;k<2;k=k+1) begin sent[k]=0;received[k]=0;xr_q[k]=0;end
        repeat(5) @(negedge clk);rst_n=1;
    end
endmodule
