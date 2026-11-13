module tb_wcc_group;
    parameter bit WNEG = 0;
    integer phase = 0;
    parameter int TC_INIT = 5;
    logic fclk=0, clk=0, rst_n=0;
    logic [1104:0] d=0;
    wire [1104:0] q, q_ref;
    wire ready, ready_ref, fault, fault_ref;
    integer errors=0, checks=0, epoch=0;
    ot_dp_clk_landing #(.W(1105),.WNEG(WNEG),.LOCAL(1),.DSREP(8)) dut
      (.fclk(fclk),.clk(clk),.rst_n(rst_n),.d(d),.q(q),.ready(ready),.fault(fault));
    ot_ref_dp_clk_landing #(.W(1105),.WNEG(WNEG),.LOCAL(1),.DSREP(8)) ref_dut
      (.fclk(fclk),.clk(clk),.rst_n(rst_n),.d(d),.q(q_ref),.ready(ready_ref),.fault(fault_ref));
    initial begin
        dut.u_ring.tc=TC_INIT; ref_dut.u_ring.tc=TC_INIT;
`ifdef OT_MESO_WCC_GROUP
        dut.u_ring.g_wcc.g_grouped.group[0].u_group.tc_group=0;
        dut.u_ring.g_wcc.g_grouped.group[1].u_group.tc_group=3;
        dut.u_ring.g_wcc.g_grouped.group[2].u_group.tc_group=2;
        dut.u_ring.g_wcc.g_grouped.group[3].u_group.tc_group=1;
        dut.u_ring.g_wcc.g_grouped.group[4].u_group.tc_group=2;
`endif
        # (833*8) rst_n=1;
        repeat(4) begin
            # (833*200) rst_n=0;
            # (833*9) rst_n=1;
        end
        # (833*200);
        $display("WCC_GROUP WNEG=%0d PHASE=%0d TC_INIT=%0d checks=%0d errors=%0d",WNEG,phase,TC_INIT,checks,errors);
        if (checks<700 || errors) $fatal(1,"WCC_GROUP_LOCKSTEP_FAIL");
        $finish;
    end
    initial forever begin #416 fclk=1; #417 fclk=0; end
    initial begin
        if (!$value$plusargs("PHASE=%d", phase)) phase=0;
        #(phase);
        forever begin #416 clk=1; #417 clk=0; end
    end
    always @(negedge fclk) begin
        epoch=epoch+1;
        for(integer i=0;i<1105;i=i+1) d[i]=((epoch*37+i*13) ^ (epoch>>(i%11))) & 1;
    end
    always @(posedge clk) begin
        #1;
        if(epoch>8) begin
            if(ready!==ready_ref || fault!==fault_ref) begin
                errors=errors+1;
                if(errors<4) $display("STATUS epoch=%0d ready=%b/%b fault=%b/%b",epoch,ready,ready_ref,fault,fault_ref);
            end
            if(ready_ref) begin
                checks=checks+1;
                if(q!==q_ref) begin
                    errors=errors+1;
                    if(errors<4) $display("DATA epoch=%0d q=%h ref=%h",epoch,q[63:0],q_ref[63:0]);
                end
            end
        end
    end
endmodule
