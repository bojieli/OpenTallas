`timescale 1ps/1fs
module tb_col_rst_local;
 reg clk=0,pck=0,run_pck=0,rst=1,lock=0;
 reg [511:0] tx=512'h6ac3d52f;
 always #416.5 clk=~clk;
 always #416.62495 if(run_pck)pck=~pck;else pck=0;
 always @(negedge clk) tx <= {tx[510:0],tx[511]^tx[509]^tx[506]^tx[503]};
 wire [511:0] rg,rd,rm;wire [1:0] sg,sd,sm;wire [543:0] pg,pd,pm;wire cg,cd,cm;
 ot_pdie_serdes_col_gold #(.LOCKSAFE(1),.HOLD_EDGES(64),.TXL(7)) gold
  (.clk(clk),.rst(rst),.pma_lock(lock),.tx(tx),.rx(rg),.st(sg),.pma_tx(pg),.pma_tck(cg),.pma_rx(pg),.pma_rck(pck));
 ot_pdie_serdes_col #(.LOCKSAFE(1),.HOLD_EDGES(64),.TXL(7)) dut
  (.clk(clk),.rst(rst),.pma_lock(lock),.tx(tx),.rx(rd),.st(sd),.pma_tx(pd),.pma_tck(cd),.pma_rx(pg),.pma_rck(pck));
 ot_pdie_serdes_col_mut #(.LOCKSAFE(1),.HOLD_EDGES(64),.TXL(7)) mutant
  (.clk(clk),.rst(rst),.pma_lock(lock),.tx(tx),.rx(rm),.st(sm),.pma_tx(pm),.pma_tck(cm),.pma_rx(pg),.pma_rck(pck));
 integer checks=0,errors=0,mut_phase_errors=0,mut_io_errors=0,tx_changes=0,epochs=0;
 reg [543:0] prev_pg=0; reg armed=0;
 always @(posedge clk or posedge pck or negedge rst or negedge lock) begin
  #1;
  if(armed)begin
   checks=checks+1;
   if({rg,sg,pg,cg,gold.rs_t,gold.rs_r,gold.rst_g} !== {rd,sd,pd,cd,dut.rs_t,dut.rs_r,dut.rst_g}
     || {dut.rn_t_enc,dut.rn_t_rm,dut.rn_t_status} !== {3{gold.rn_t}})begin
    errors=errors+1;if(errors<4)$display("COL_RST_ERR time=%0t epoch=%0d",$time,epochs);
   end
   if({mutant.rn_t_enc,mutant.rn_t_rm,mutant.rn_t_status} !== {3{gold.rn_t}})mut_phase_errors=mut_phase_errors+1;
   if({rm,sm,pm,cm} !== {rg,sg,pg,cg})mut_io_errors=mut_io_errors+1;
   if(pg!==prev_pg)tx_changes=tx_changes+1;prev_pg=pg;
  end
 end
 initial begin
  #2;rst=0;armed=1;#5;rst=1;repeat(5)@(posedge clk);lock=1;run_pck=1;
  repeat(700)@(posedge pck);
  epochs=1;@(negedge pck);#13;rst=0;run_pck=0;#104;rst=1;repeat(8)@(posedge clk);run_pck=1;
  repeat(700)@(posedge pck);
  epochs=2;@(negedge pck);#17;lock=0;repeat(4)@(posedge pck);#11;lock=1;
  repeat(700)@(posedge pck);#10;
  $display("COL_RST_LOCAL_RESULT checks=%0d errors=%0d mutant_phase_errors=%0d mutant_io_errors=%0d tx_changes=%0d epochs=3 mission_added=0 reset_edges_added=0",checks,errors,mut_phase_errors,mut_io_errors,tx_changes);
  if(errors || !mut_phase_errors || tx_changes<100)$fatal(1,"actual COL reset-copy lockstep/mutant failed");
  $finish;
 end
 initial begin #4000000;$fatal(1,"timeout");end
endmodule
