`timescale 1ns/1ps
module mock_sys_c;reg[0:0]w_dcal_fault=0;endmodule
module mock_dut;mock_sys_c sys_c();endmodule
module mock_far;task report;endtask endmodule
module tb_finalcal;
reg ck_core=0;always #1 ck_core=~ck_core;integer cyc_core=0;always @(posedge ck_core)cyc_core<=cyc_core+1;
integer post=0,late=0,po_n=0,ftx_n=0;reg far_en=0;mock_dut dut();mock_far u_far();
initial begin
void'($value$plusargs("POST=%d",post));void'($value$plusargs("LATE=%d",late));
$display("KVSLICE_BOOT PASS dcal_fault 0 cyc 0");
if(late!=0)fork begin repeat(3)@(negedge ck_core);dut.sys_c.w_dcal_fault=1;end join_none
        if (post > 0) begin
            repeat (post) @(posedge ck_core);
            $display("KVSLICE_POST cyc %0d events %0d fdi_tx_words %0d", cyc_core, po_n, ftx_n);
            if (far_en) u_far.report();
        end
        $display("KVSLICE_FINALCAL dcal_fault %b cyc %0d", dut.sys_c.w_dcal_fault[0], cyc_core);
        if (dut.sys_c.w_dcal_fault[0]) $fatal(1, "KVSLICE_FINALCAL FAIL: calendar fault after POST");
        $finish;
end
endmodule
