`timescale 1ns/1ps
module tb_port;
 reg clk=0;always #0.416666667 clk=~clk;
 reg rst_n=0,qp=0,rx=0;reg[544:0] din={17'h1aaaa,{16{32'h34561234}},16'h7777};
 wire txv,rbv,fault,ce,stall;wire[544:0] txd,rbd;wire[1:0] drops;
 ot_hcoll_port #(.PAYLOAD_ECC(1), .FACE_CK(`ifdef FACECK 1 `else 0 `endif)) dut(.clk(clk),.ckf(clk),.rst_n(rst_n),.qp_push(qp),.qp_din(din),.qr_push(1'b0),.qr_din('0),.sw_cr_ret(1'b0),.ph_tx_v(txv),.ph_tx_flit(txd),.ph_rx_v(rx),.ph_rx_flit(din),.rb_v(rbv),.rb_d(rbd),.rb_cr(1'b0),.stall(stall),.fault(fault),.ecc_ce(ce),.rx_ecc_drop(drops));
 integer txs,rbs,ces,ds,checks=0;reg track=0;
 always @(negedge clk)if(track)begin
 txs=txs+txv;rbs=rbs+rbv;ces=ces+ce;ds=ds+integer'(drops);
 if(txv&&txd!==din)$fatal(1,"corrupt TX publication");if(rbv&&rbd!==din)$fatal(1,"corrupt RX publication");
 end
 task trial(input integer where,input integer doublebit);
 integer a,n;reg wc;
 begin
 @(negedge clk);track=0;rst_n=0;qp=0;rx=0;repeat(2)@(negedge clk);rst_n=1;
 txs=0;rbs=0;ces=0;ds=0;track=1;
 if(where<2)qp=1;else rx=1;
 @(negedge clk);qp=0;rx=0;
 n=0;wc=0;
 while(!wc && n<80)begin
 case(where)
 0:begin wc=dut.u_qp.g_bk[0].u_m.w_ce;a=dut.u_qp.g_bk[0].u_m.w_addr;end
 1:begin wc=dut.u_wtx.u_m.w_ce;a=dut.u_wtx.u_m.w_addr;end
 2:begin wc=dut.u_wrx.u_m.w_ce;a=dut.u_wrx.u_m.w_addr;end
 3:begin wc=dut.u_rb.g_bk[0].u_m.w_ce;a=dut.u_rb.g_bk[0].u_m.w_addr;end
 endcase
 if(!wc)@(negedge clk);n=n+1;
 end
 if(!wc)$fatal(1,"no actual macro write %0d",where);
 @(negedge clk);
 case(where)
 0:begin dut.u_qp.g_bk[0].u_m.g_m[0].u_sram.arr[a][2]=~dut.u_qp.g_bk[0].u_m.g_m[0].u_sram.arr[a][2];if(doublebit)dut.u_qp.g_bk[0].u_m.g_m[0].u_sram.arr[a][0]=~dut.u_qp.g_bk[0].u_m.g_m[0].u_sram.arr[a][0];end
 1:begin dut.u_wtx.u_m.g_m[0].u_sram.arr[a][2]=~dut.u_wtx.u_m.g_m[0].u_sram.arr[a][2];if(doublebit)dut.u_wtx.u_m.g_m[0].u_sram.arr[a][0]=~dut.u_wtx.u_m.g_m[0].u_sram.arr[a][0];end
 2:begin dut.u_wrx.u_m.g_m[0].u_sram.arr[a][2]=~dut.u_wrx.u_m.g_m[0].u_sram.arr[a][2];if(doublebit)dut.u_wrx.u_m.g_m[0].u_sram.arr[a][0]=~dut.u_wrx.u_m.g_m[0].u_sram.arr[a][0];end
 3:begin dut.u_rb.g_bk[0].u_m.g_m[0].u_sram.arr[a][2]=~dut.u_rb.g_bk[0].u_m.g_m[0].u_sram.arr[a][2];if(doublebit)dut.u_rb.g_bk[0].u_m.g_m[0].u_sram.arr[a][0]=~dut.u_rb.g_bk[0].u_m.g_m[0].u_sram.arr[a][0];end
 endcase
 repeat(80)@(negedge clk);track=0;
 if(doublebit)begin
 if(!fault||txs||rbs)$fatal(1,"UE not refused/faulted where=%0d",where);
 if(where>=2&&ds!=1)$fatal(1,"RX UE credit lost ds=%0d",ds);
 if(where==1&&dut.credit!=256)$fatal(1,"TX reserved credit lost");
 end else if(fault||ces!=1||((where<2)&&(txs!=1))||((where>=2)&&(rbs!=1)))$fatal(1,"CE port mismatch where=%0d ce=%0d tx=%0d rb=%0d",where,ces,txs,rbs);
 checks=checks+1;
 end endtask
 initial begin
 for(integer w=0;w<4;w=w+1)begin trial(w,0);trial(w,1);end
 $display("PAYLOAD_PORT PASS actual_stores=4 CE_UE_trials=%0d",checks);$finish;
 end
endmodule
