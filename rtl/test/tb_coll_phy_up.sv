`timescale 1ns/1ps
module tb_coll_phy_up;
    reg clk=0;
    always #0.416666 clk=~clk;
    reg rst_n=0,epoch=0,wr=0,rd=0,up=1;
    wire[1:0]txv,abort;
    wire[7:0]cause[0:1];
    integer cyc=0,txedge=-1,old_fault=-1,safe_fault=-1,errors=0;
    for(genvar k=0;k<2;k=k+1)begin:g_ctl
        ot_qwen_static_slot_ctl #(.FW(32),.CW(16),.SAFE(k))u_ctl(
            .clk(clk),.rst_n(rst_n),.epoch_begin(epoch),.epoch(8'h01),
            .wr_v(wr),.wr_observed_v(1'b1),.wr_slot(6'd0),.q_data(32'h12345678),
            .rd_v(rd),.rd_slot(6'd0),.rx_expect_v(1'b0),.rx_expect_slot(6'd0),
            .p_tx_up(up),.p_tx_v(txv[k]),.p_tx_flit(),.p_rx_v(1'b0),.p_rx_flit(67'd0),
            .rx_v(),.rx_flit(),.epoch_abort(abort[k]),.fault_cause(cause[k]));
    end
    always @(negedge clk)begin
        rst_n<=cyc>=4;
        epoch<=cyc==10 || cyc==40;
        wr<=cyc==20;
        rd<=cyc==24;
        // The read at edge25 launches the TX3 boundary at edge28.
        up<=cyc!=27;
    end
    always @(posedge clk)begin
        cyc=cyc+1;
        #0.001;
        if(txv[0] && txedge<0)txedge=cyc;
        if(abort[0] && old_fault<0)old_fault=cyc;
        if(abort[1] && safe_fault<0)safe_fault=cyc;
        if(cyc<28 && txv[0]!==txv[1])errors=errors+1;
        if(cyc==48)begin
            if(txedge!=28 || old_fault!=28 || safe_fault!=29 || cause[0]!=0 || cause[1]!=0 || |abort)errors=errors+1;
            $display("COLL_PHY_UP %s tx %0d original_fault %0d captured_fault %0d diagnostic_added_edges1 errors%0d",
                     errors==0?"PASS":"FAIL",txedge,old_fault,safe_fault,errors);
            $finish;
        end
    end
endmodule
