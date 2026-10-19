`timescale 1ns/1ps
// Lockstep (HBMA-HOST2 2026-10-17, coordinator 0dc+ (d)): ot_hbm_status_join RRELAY=1 (own regional reset relay, die
// defaults NT67/NF105/NH6) against the r1 join (RRELAY=0) reset by one ot_rst_relay with the same 2+1 stages. Every
// output compared every edge (4-state !==) under random cfg/desc/launch frames on the die target ids, ready/active/fault
// traffic and 6 resets whose release edges see input activity. MUT 1 participation ignored, 3 DUT without the relay
// (raw rst_n): must FAIL.
module tb_hbm_status_join_relay;
parameter integer MUT=0;
localparam integer NT=67, NF=105, NH=6;
localparam [NT*8-1:0] TGTS=536'hd7d6d5d4d3d2d1d0c7c6c5c4c3c2c1c0a5a4a2a0878685846f6e6d6c6a68666463626160575655545352515047464544434241403b3a39387877767574703736353430;
reg clk=0,rst_n=0; always #1 clk=~clk;
reg cv=0,dv=0,lv=0; reg [7:0] ct=0; reg [NT-1:0] rdy=0,act=0; reg [NF-1:0] tf=0; reg [NH-1:0] hf=0;
wire d_br,d_pa,d_pf,d_df,d_irq, r_br,r_pa,r_pf,r_df,r_irq;
ot_hbm_status_join #(.MUT(MUT==1?1:0),.RRELAY(MUT==3?0:1)) dut(.clk(clk),.rst_n(rst_n),.cfg_v(cv),.desc_v(dv),.launch_v(lv),
 .cfg_target(ct),.t_ready(rdy),.t_active(act),.t_fault(tf),.h_fault(hf),
 .block_ready(d_br),.program_active(d_pa),.program_fault(d_pf),.die_fault(d_df),.irq(d_irq));
wire [0:0] r_rst;
ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) r_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(r_rst));
ot_hbm_status_join ref0(.clk(clk),.rst_n(r_rst[0]),.cfg_v(cv),.desc_v(dv),.launch_v(lv),
 .cfg_target(ct),.t_ready(rdy),.t_active(act),.t_fault(tf),.h_fault(hf),
 .block_ready(r_br),.program_active(r_pa),.program_fault(r_pf),.die_fault(r_df),.irq(r_irq));
integer edges=0,mism=0,nbr=0,nirq=0,npf=0,started=0;
always @(posedge clk) if(started) begin
 edges=edges+1;
 if({d_br,d_pa,d_pf,d_df,d_irq}!=={r_br,r_pa,r_pf,r_df,r_irq}) begin
  mism=mism+1; if(mism<=5) $display("MISMATCH t=%0t br %b/%b pa %b/%b pf %b/%b df %b/%b irq %b/%b",$time,d_br,r_br,d_pa,r_pa,d_pf,r_pf,d_df,r_df,d_irq,r_irq);
 end
 if(r_br) nbr=nbr+1; if(r_irq) nirq=nirq+1; if(r_pf) npf=npf+1;
end
integer seed=5,i,r,k,cyc;
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
end
initial begin
 started=1; repeat(4) @(posedge clk); rst_n=1;
 for(i=0;i<6;i=i+1) begin
  repeat(3000+$unsigned($random(seed))%2000) @(negedge clk);
  rst_n=0; repeat(2+i) @(negedge clk); rst_n=1;
 end
 repeat(3000) @(negedge clk);
 if(mism==0 && edges>20000 && nbr>100 && nirq>0 && npf>100)
  $display("STATUS_JOIN_RELAY_PASS edges=%0d block_ready=%0d irq=%0d pfault=%0d mism=0",edges,nbr,nirq,npf);
 else $display("STATUS_JOIN_RELAY_FAIL mism=%0d edges=%0d block_ready=%0d irq=%0d pfault=%0d",mism,edges,nbr,nirq,npf);
 $finish;
end
endmodule
