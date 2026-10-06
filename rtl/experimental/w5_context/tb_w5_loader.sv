`timescale 1ns/1ps
module tb_w5_loader;
 reg clk=0;always #0.5 clk=~clk;
 reg por_n=0,cfg=0,go=0;reg [5:0] ph=0;reg [2:0] np=2;
 wire [10:0] mp,mr;wire [47:0] cm=48'h1235fedcabcd ^ mp;
 wire cp,cr,gp,gr,bp,br,fp,fr;wire [4:0] ap,ar;wire [47:0] dp,dr;
 ot_w5_loader_checked #(.ENABLE(1)) dut(.clk(clk),.por_n(por_n),.cfg_go(cfg),.cfg_ph(ph),.cfg_np(np),
 .go(go),.cm_q(cm),.cm_a(mp),.c_v(cp),.c_a(ap),.c_d(dp),.go_e(gp),.ld_busy(bp),.fault(fp));
 ot_v41_pair_pq_ld #(.PQ(0),.PHW(6)) ref_dut(.clk(clk),.rst_n(por_n),.cfg_go(cfg),.cfg_ph(ph),.cfg_np(np),
 .go(go),.cm_q(cm),.cm_a(mr),.c_v(cr),.c_a(ar),.c_d(dr),.go_e(gr),.ld_busy(br),.fault(fr),
 .e_sh_free(1'b1),.e_bank_free(1'b1));
 integer receipts=0;reg compare=1;reg [85:0] held;
 always @(negedge clk)if(por_n&&compare)begin
 if({cp,gp,bp,fp}!=={cr,gr,br,fr})$fatal(1,"loader control differs");
 if(cp)begin
  if({ap,dp,mp}!=={ar,dr,mr})$fatal(1,"loader tuple differs");
  receipts=receipts+1;
 end
 end
 initial begin
 repeat(4)@(negedge clk);por_n=1;
 @(negedge clk);cfg=1;
 @(negedge clk);cfg=0;
 repeat(32)@(negedge clk);
 if(receipts!=25||fp)$fatal(1,"missing healthy full25 loader receipts");
 compare=0;cfg=1;ph=6'd63;
 @(negedge clk);cfg=0;
 repeat(4)@(negedge clk);
 dut.u_p.ld_a[3]=~dut.u_p.ld_a[3];
 #0.01;if(!fp||cp||gp||!bp)$fatal(1,"loader fault did not exclude tuple/GO");
 held=dut.u_p.snapshot;
 cfg=1;go=1;
 repeat(12)@(negedge clk);
 if(dut.u_p.snapshot!==held||!fp||cp||gp)$fatal(1,"loader quarantine erased accepted source");
 $display("PASS loader full25 source tuples exactly equal; address fault froze accepted phase/no cfg/GO");$finish;
 end
endmodule
