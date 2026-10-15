`timescale 1ns/1ps
// Actual return-ring drain exports. No parent or physical timing claim.
module tb_static_return_idle;
 parameter integer PHASE_PS=137;
 reg hc=0,ck=0,rst=0,put=0,expected=0;
 reg [293:0] co=0;
 always #0.512 hc=~hc;
 initial begin #(PHASE_PS*0.001);forever #0.416667 ck=~ck;end
 wire ih,ic,av,hf,cf;wire[255:0]data;
 qkd_static_kv_return_slots dut(.pll_hbm(hc),.hrst(rst),.ck(ck),.rsi(rst),
 .controller_co(co),.controller_epoch(16'd7),.compiled_hbm_put(put),
 .expected_put(expected),.expected_sector(10'd0),.expected_epoch(16'd7),.expected_layer(6'd0),
 .actual_valid(av),.actual_sector(),.actual_epoch(),.actual_layer(),.actual_data(data),
 .fault_hbm(hf),.fault_core(cf),.idle_hbm(ih),.idle_core(ic));
 task wait_quiet;
 begin repeat(8)@(negedge hc);repeat(8)@(negedge ck);#0.01;end
 endtask
 task landing;
 begin @(negedge hc);put=1;co[0]=1;co[281:26]=256'h12345678;
 @(negedge hc);put=0;co=0;end
 endtask
 initial begin
 repeat(4)@(negedge hc);rst=1;wait_quiet();
 if(ih!==1||ic!==1)$fatal(1,"IDLE empty reset ring");
 landing();wait_quiet();
 if(ih!==0||ic!==0)$fatal(1,"IDLE outstanding publication lost");
 @(negedge ck);expected=1;
 // Current input slot must suppress idle on its capture edge.
 @(negedge ck);if(ic!==0)$fatal(1,"IDLE core pending slot ignored");expected=0;
 wait_quiet();
 if(ih!==1||ic!==1||hf||cf)$fatal(1,"IDLE consumed ring failed to drain");
 landing();wait_quiet();
 if(ih!==0||ic!==0)$fatal(1,"IDLE reused entry falsely drained");
 @(negedge hc);rst=0;repeat(4)@(negedge hc);
 if(ih!==0||ic!==0)$fatal(1,"IDLE reset must not advertise drained");
 rst=1;wait_quiet();
 if(ih!==1||ic!==1)$fatal(1,"IDLE reset ring failed to drain");
 $display("PASS actual return-ring idle phase%0d outstanding/consume/reuse/reset",PHASE_PS);$finish;
 end
 initial begin #2000;$fatal(1,"IDLE timeout");end
endmodule
