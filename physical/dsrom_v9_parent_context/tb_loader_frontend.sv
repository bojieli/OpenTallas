`timescale 1ns/1ps
module loader_compare #(parameter PQ=0)(input clk,rst_n,cfg_go,go,e_sh_free,e_bank_free,
 input [5:0] cfg_ph,input [2:0] cfg_np,input [47:0] cm_q);
 wire [10:0] ar,af,am; wire vr,vf,vm;wire [4:0] cr,cf,cm;wire [47:0] dr,df,dm;
 wire gr,gf,gm,br,bf,bm,fr,ff,fm;
 ot_v41_pair_pq_ld #(.PQ(PQ)) ref_r(.clk(clk),.rst_n(rst_n),.cfg_go(cfg_go),.cfg_ph(cfg_ph),.cfg_np(cfg_np),.go(go),.e_sh_free(e_sh_free),.e_bank_free(e_bank_free),.cm_a(ar),.cm_q(cm_q),.c_v(vr),.c_a(cr),.c_d(dr),.go_e(gr),.ld_busy(br),.fault(fr));
 ot_v41_pair_pq_ld_frontend #(.PQ(PQ)) fix_r(.clk(clk),.rst_n(rst_n),.cfg_go(cfg_go),.cfg_ph(cfg_ph),.cfg_np(cfg_np),.go(go),.e_sh_free(e_sh_free),.e_bank_free(e_bank_free),.cm_a(af),.cm_q(cm_q),.c_v(vf),.c_a(cf),.c_d(df),.go_e(gf),.ld_busy(bf),.fault(ff));
 generate if(PQ==0) begin:g0
 `ifdef BAD_FRONTEND
 pq0_bad_mapped mapped(.clk(clk),.rst_n(rst_n),.cfg_go(cfg_go),.cfg_ph(cfg_ph),.cfg_np(cfg_np),.go(go),.e_sh_free(e_sh_free),.e_bank_free(e_bank_free),.cm_a(am),.cm_q(cm_q),.c_v(vm),.c_a(cm),.c_d(dm),.go_e(gm),.ld_busy(bm),.fault(fm));
 `else
 pq0_fixed_mapped mapped(.clk(clk),.rst_n(rst_n),.cfg_go(cfg_go),.cfg_ph(cfg_ph),.cfg_np(cfg_np),.go(go),.e_sh_free(e_sh_free),.e_bank_free(e_bank_free),.cm_a(am),.cm_q(cm_q),.c_v(vm),.c_a(cm),.c_d(dm),.go_e(gm),.ld_busy(bm),.fault(fm));
 `endif
 end else begin:g1
 pq1_fixed_mapped mapped(.clk(clk),.rst_n(rst_n),.cfg_go(cfg_go),.cfg_ph(cfg_ph),.cfg_np(cfg_np),.go(go),.e_sh_free(e_sh_free),.e_bank_free(e_bank_free),.cm_a(am),.cm_q(cm_q),.c_v(vm),.c_a(cm),.c_d(dm),.go_e(gm),.ld_busy(bm),.fault(fm));
 end endgenerate
 integer checks=0,fault_cycles=0,words=0,admitted=0,reset_samples=0;
 always @(posedge clk) begin
 #1;
 if ({ar,vr,cr,dr,gr,br,fr} !== {af,vf,cf,df,gf,bf,ff}) $fatal(1,"RTL exact mismatch PQ=%0d check=%0d",PQ,checks);
 if ({ref_r.ld_run,ref_r.ld_k,ref_r.ld_a,ref_r.ld_np,ref_r.pend,ref_r.pend_ph,ref_r.pend_np,ref_r.act} !== {fix_r.ld_run,fix_r.ld_k,fix_r.ld_a,fix_r.ld_np,fix_r.pend,fix_r.pend_ph,fix_r.pend_np,fix_r.act}) $fatal(1,"state mismatch PQ=%0d check=%0d",PQ,checks);
 if ({vr,gr,br,fr} !== {vm,gm,bm,fm}) $fatal(1,"lowered control mismatch PQ=%0d check=%0d ref=%b mapped=%b",PQ,checks,{vr,gr,br,fr},{vm,gm,bm,fm});
 // Address exists during a real load; data/address equality retains every valid byte.
 if(ref_r.ld_run && ar!==am) $fatal(1,"lowered ROM address mismatch PQ=%0d",PQ);
 if(vr && {cr,dr}!=={cm,dm}) $fatal(1,"lowered payload mismatch PQ=%0d",PQ);
 if(fr) fault_cycles=fault_cycles+1;
 if(vr) words=words+1;
 if(gr) admitted=admitted+1;
 if(!rst_n) begin reset_samples=reset_samples+1;if(fr!==0 || fm!==0) $fatal(1,"reset fault differs PQ=%0d",PQ);end
 checks=checks+1;
 end
endmodule
module tb_loader_frontend;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=1,cfg_go=0,go=0,e_sh_free=1,e_bank_free=1;
 reg [5:0] cfg_ph=0;reg[2:0]cfg_np=1;reg[47:0]cm_q=48'h123456789ab1;
 reg[31:0]lfsr=32'h417932ab;integer n;
 loader_compare #(.PQ(0)) p0(.*);loader_compare #(.PQ(1)) p1(.*);
 initial begin
 #1 rst_n=0;
 for(n=0;n<4000;n=n+1) begin
 @(negedge clk);
 lfsr={lfsr[30:0],lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};
 rst_n=(n>=3 && n%311>2);
 cfg_go=(n==4 || n==7 || n%41==5);
 go=(n==11 || n%37==19 || n%13==9);
 e_sh_free=(n>=12 && lfsr[1:0]!=0);e_bank_free=(n>=12 && lfsr[3:2]!=0);
 cfg_ph=lfsr[9:4];cfg_np=1+lfsr[12:10]%7;cm_q={lfsr,lfsr[15:1],1'b1};
 end
 @(negedge clk);
 if(p0.fault_cycles!=0 || p1.fault_cycles==0 || p0.words<100 || p1.words<100 || p0.admitted==0 || p1.admitted==0 || p0.reset_samples<20 || p1.reset_samples<20) $fatal(1,"coverage insufficient");
 $display("PASS original/corrected RTL all outputs+internal states; lowered PQ0/PQ1 all control and valid ROM bytes; checks=%0d/%0d words=%0d/%0d admitted=%0d/%0d fault_cycles=%0d/%0d resets=%0d/%0d",p0.checks,p1.checks,p0.words,p1.words,p0.admitted,p1.admitted,p0.fault_cycles,p1.fault_cycles,p0.reset_samples,p1.reset_samples);
 $finish;
 end
endmodule
