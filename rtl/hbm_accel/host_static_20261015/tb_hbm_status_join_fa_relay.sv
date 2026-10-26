`timescale 1ns/1ps
// Lockstep (HBM-TILES-A2 2026-10-17): the hardened status/fault-tree root ot_hbm_status_join_fa RRELAY=1 (die defaults
// NT67/NF105/NH6, NA 4, FCLR 125) against ot_hbm_status_join_fa RRELAY=0 reset by one ot_rst_relay with the same 2+1
// stages. Every output (incl. a_cause) compared every edge (4-state !==) under random cfg/desc/launch frames on the die
// target ids and the fault-clear target 125, ready/active/fault traffic, region-root fault pulses and levels, and 6
// resets whose release edges see input activity. MUT 1 participation ignored, 3 DUT without the relay (raw rst_n),
// 4 DUT FMUT 1 (cause not sticky): must FAIL.
module tb_hbm_status_join_fa_relay;
parameter integer MUT=0;
// NT/NF/NH/TGTS: r3 module defaults; STATFA4 10-17: run_status_join_fa_relay.sh OUT MUT d4f sets the d4f die instance's
// NT 69 / NF 107 / 552-bit TGTS (hdie_host_status_fa_r4).
parameter integer NT=67, NF=105, NH=6;
parameter [NT*8-1:0] TGTS=536'hd7d6d5d4d3d2d1d0c7c6c5c4c3c2c1c0a5a4a2a0878685846f6e6d6c6a68666463626160575655545352515047464544434241403b3a39387877767574703736353430;
reg clk=0,rst_n=0; always #1 clk=~clk;
reg cv=0,dv=0,lv=0; reg [7:0] ct=0; reg [NT-1:0] rdy=0,act=0; reg [NF-1:0] tf=0; reg [NH-1:0] hf=0;
reg [3:0] af=0; wire [3:0] d_ac, r_ac;
wire d_br,d_pa,d_pf,d_df,d_irq, r_br,r_pa,r_pf,r_df,r_irq;
ot_hbm_status_join_fa #(.NT(NT),.NF(NF),.NH(NH),.TGTS(TGTS),.MUT(MUT==1?1:0),.RRELAY(MUT==3?0:1),.FMUT(MUT==4?1:0)) dut(.clk(clk),.rst_n(rst_n),.cfg_v(cv),.desc_v(dv),.launch_v(lv),
 .cfg_target(ct),.t_ready(rdy),.t_active(act),.t_fault(tf),.h_fault(hf),.a_fault(af),
 .block_ready(d_br),.program_active(d_pa),.program_fault(d_pf),.die_fault(d_df),.irq(d_irq),.a_cause(d_ac));
wire [0:0] r_rst;
ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) r_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(r_rst));
ot_hbm_status_join_fa #(.NT(NT),.NF(NF),.NH(NH),.TGTS(TGTS)) ref0(.clk(clk),.rst_n(r_rst[0]),.cfg_v(cv),.desc_v(dv),.launch_v(lv),
 .cfg_target(ct),.t_ready(rdy),.t_active(act),.t_fault(tf),.h_fault(hf),.a_fault(af),
 .block_ready(r_br),.program_active(r_pa),.program_fault(r_pf),.die_fault(r_df),.irq(r_irq),.a_cause(r_ac));
integer edges=0,mism=0,nbr=0,nirq=0,npf=0,nac=0,nclr=0,started=0;
always @(posedge clk) if(started) begin
 edges=edges+1;
 if({d_br,d_pa,d_pf,d_df,d_irq,d_ac}!=={r_br,r_pa,r_pf,r_df,r_irq,r_ac}) begin
  mism=mism+1; if(mism<=5) $display("MISMATCH t=%0t br %b/%b pa %b/%b pf %b/%b df %b/%b irq %b/%b ac %h/%h",$time,d_br,r_br,d_pa,r_pa,d_pf,r_pf,d_df,r_df,d_irq,r_irq,d_ac,r_ac);
 end
 if(r_br) nbr=nbr+1; if(r_irq) nirq=nirq+1; if(r_pf) npf=npf+1; if(|r_ac) nac=nac+1; if(cv && ct==8'd125) nclr=nclr+1;
end
integer seed=5,i,r,k,cyc; reg af_lvl=0;
always @(negedge clk) if(started) begin
 r=$unsigned($random(seed))%1000;
 cv=0; dv=0; lv=0;
 k=$unsigned($random(seed))%NT; ct=TGTS[k*8+:8];
 if(r<30) cv=1; else if(r<60) dv=1; else if(r<66) lv=1;
 if(r>=100 && r<400) rdy[$unsigned($random(seed))%NT]=($unsigned($random(seed))%8)!=0;
 if(r>=400 && r<440) act[$unsigned($random(seed))%NT]=~act[$unsigned($random(seed))%NT];
 if(r>=440 && r<450) act=0;
 if(r>=450 && r<455) tf[$unsigned($random(seed))%NF]=~tf[$unsigned($random(seed))%NF];
 if(r>=455 && r<458) hf[$unsigned($random(seed))%NH]=~hf[$unsigned($random(seed))%NH];
 if(r>=458 && r<462) begin tf=0; hf=0; end
 if(r>=462 && r<470) rdy={NT{1'b1}};
 // region-root faults: rare pulses, rarer levels; fault-clear rows to target 125
 af=af & {4{af_lvl}};
 if(r>=470 && r<473) af[$unsigned($random(seed))%4]=1'b1;
 if(r==473) af_lvl=~af_lvl;
 if(r>=474 && r<479) begin cv=1; ct=8'd125; end
end
initial begin
 started=1; repeat(4) @(posedge clk); rst_n=1;
 for(i=0;i<6;i=i+1) begin
  repeat(3000+$unsigned($random(seed))%2000) @(negedge clk);
  rst_n=0; repeat(2+i) @(negedge clk); rst_n=1;
 end
 repeat(3000) @(negedge clk);
 if(mism==0 && edges>20000 && nbr>100 && nirq>0 && npf>100 && nac>100 && nclr>20)
  $display("STATUS_JOIN_FA_RELAY_PASS edges=%0d block_ready=%0d irq=%0d pfault=%0d a_cause=%0d clears=%0d mism=0",edges,nbr,nirq,npf,nac,nclr);
 else $display("STATUS_JOIN_FA_RELAY_FAIL mism=%0d edges=%0d block_ready=%0d irq=%0d pfault=%0d a_cause=%0d clears=%0d",mism,edges,nbr,nirq,npf,nac,nclr);
 $finish;
end
endmodule
