`timescale 1ns/1ps
// L2H-IDXSEL s3: full-shape exact bench of the landed IDX selector cluster ot_hbm_idx_selector_s3 (die master: lp.py
// landed parent of ctl + 4 x quadrant tile).  Same check as tb_selector_static on the die's SELECTED stream (the die
// reads selected_v / selected_line / fault only): every chosen lane (valid bit of selected_line during the op6 scan)
// must be a gold top-512 member with its exact BF16 score, each id once, all 512 found, fault 0.  Frame 0 is the
// crafted margin frame (tools/hbm_idx_s3_selector_vectors.py), frames 1..3 the historical frames.
// Schedule = the compiler's registered_s3 PIN table: in_line is presented SKEW = sel_in 7 - sel_in_line 2 = 5 edges
// after its op2 slot; RT = sel_choose_rt idle edges after every op5 run; DRAIN = scan drain edges before the first op5.
// Mutants (must FAIL "fullshape exact selector mismatch"): DMUT 1 tie compare, 3 lane-5 write-data copy late, 5 hrd one
// edge late vs its tags, 6 ctl tags one edge early; RT 7 (choose spacing one edge short); DRAIN 3 (drain one short);
// MUT 1 / 2 lp landing 0 bypassed / read K+1.
module tb_selector_s3;
 parameter integer DMUT=0,MUT=0,RT=8,DRAIN=4,SKEW=5;
 reg clk=0;always #5 clk=~clk;
 reg clk_x=0;
 reg rst_n=0;reg[3:0]op=0;reg[1:0]pass=0;reg[7:0]addr=0;reg[9:0]k=512;
 reg[2367:0]in_line=0;wire fault;
 wire[3:0]selected_v;wire[2367:0]selected_line;
 ot_hbm_idx_selector_s3 #(.DMUT(DMUT),.MUT(MUT)) dut(.clk_ctl(clk),.clk_q({4{clk}}),.clk_mem({12{clk_x}}),.*);
 reg[2367:0]lines[0:170];reg gold[0:10943];reg[15:0]scores[0:10943];reg seen[0:10943];
 reg[2367:0]dl[0:7];reg[2367:0]nxt=0;
 integer errors=0,checked=0,frame,cyc=0,firstsel,beginframe;string fn;
 always @(posedge clk)cyc<=cyc+1;
 task automatic tick(input integer o,input integer a,input integer p);
  begin @(negedge clk);op=4'(o);addr=8'(a);pass=2'(p);
   in_line=dl[SKEW-1];for(integer j=7;j>0;j=j-1)dl[j]=dl[j-1];dl[0]=nxt;
  end
 endtask
 always @(negedge clk)begin
  for(integer q=0;q<4;q=q+1)if(selected_v[q])begin
   if(firstsel<0)firstsel=cyc;
   for(integer l=0;l<16;l=l+1)if(selected_line[q*592+l*37])begin
    integer id;id=int'(selected_line[q*592+l*37+17+:20]);checked++;
    if(id>=10944)errors++;
    else begin
     if(!gold[id]||seen[id]||scores[id]!==selected_line[q*592+l*37+1+:16])begin errors++;if(errors<8)$display("bad id%0d frame%0d",id,frame);end
     seen[id]=1;
    end
   end
  end
 end
 initial begin
  for(integer j=0;j<8;j=j+1)dl[j]=0;
  repeat(4)@(negedge clk);rst_n=1;repeat(12)@(negedge clk); // lp reset runs (2) + child ot_rst_relay (3) + ring warm-up
  for(frame=0;frame<4;frame=frame+1)begin
   fn=$sformatf("lines%0d.hex",frame);$readmemh(fn,lines);
   fn=$sformatf("gold%0d.hex",frame);$readmemh(fn,gold);
   fn=$sformatf("scores%0d.hex",frame);$readmemh(fn,scores);
   for(integer j=0;j<10944;j=j+1)seen[j]=0;
   checked=0;firstsel=-1;beginframe=cyc;
   tick(1,0,0);tick(3,0,0);
   for(integer a=0;a<171;a=a+1)begin nxt=lines[a];tick(2,a,0);end
   tick(0,0,0);tick(0,0,0);
   for(integer b=31;b>=0;b=b-1)tick(5,b,0);
   repeat(1+RT)tick(0,0,0);
   for(integer p=1;p<3;p=p+1)begin
    tick(3,0,p);
    for(integer a=0;a<171;a=a+1)tick(4,a,p);
    repeat(DRAIN)tick(0,0,p); // scan drain: op4 -> hist H3 is 4 edges (pipelined core), quadrant-internal
    for(integer b=(p==2?63:31);b>=0;b=b-1)tick(5,b,p);
    repeat(1+RT)tick(0,0,p);  // choose loop: threshold / ties come back through two landings (+8 vs the flat core)
   end
   for(integer a=0;a<171;a=a+1)tick(6,a,2);
   repeat(24)tick(0,0,2);
   for(integer j=0;j<10944;j=j+1)if(gold[j]!==seen[j])errors++;
   if(checked!=512||fault)errors++;
   $display("IDX_SELECTOR_S3 DMUT%0d MUT%0d RT%0d DRAIN%0d frame%0d checked%0d errors%0d fault%0d edges%0d firstsel%0d",
            DMUT,MUT,RT,DRAIN,frame,checked,errors,fault,cyc-beginframe,firstsel-beginframe);
  end
  if(errors)$fatal(1,"fullshape exact selector mismatch");$finish;
 end
endmodule
