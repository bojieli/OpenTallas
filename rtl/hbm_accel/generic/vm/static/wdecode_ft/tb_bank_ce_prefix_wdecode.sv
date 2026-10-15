`timescale 1ns/1ps
module tb_bank_ce_prefix_wdecode;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;
    ot_vms_bank_static_wdecode_ft #(.RG(7),.WG(3)) bank(
        .clk(clk),.rst_n(rst_n),.bid(3'd0),.sid(2'd0),.rslot_v(1'b0),.rslot(3'd0),
        .wslot_v(1'b0),.wslot(3'd0),.rq(119'd0),.rr(),.wq(843'd0),.wq_done(),
        .dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),
        .xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status());
    integer exact;
    reg [15:0] actual;
    initial begin
        // Exhaust allcounterstates and every4bitincrement, including all
        // physically possible0..8 corrections and every saturation boundary.
        for(integer count=0;count<65536;count=count+1)begin
            for(integer step=0;step<16;step=step+1)begin
                exact=count+step;if(exact>65535)exact=65535;
                actual=bank.sat_ce_add(16'(count),4'(step));
                if(actual!==16'(exact))$fatal(1,"CE prefix mismatch count=%0d step=%0d",count,step);
            end
        end
        $display("BANK_CE_PREFIX PASS states=65536 increments=16 cases=1048576 exact_saturation=1 unchanged_edge=1");$finish;
    end
endmodule
