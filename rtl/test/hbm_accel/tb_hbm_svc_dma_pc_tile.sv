`timescale 1ns/1ps
module tb_hbm_svc_dma_pc_tile #(parameter MUT=0);
 reg clk=0;always #5 clk=~clk;
 reg rst=1,rq_v=0,phy_ready=0,rs_v=0;
 reg[16:0]rq_tag=0,rs_tag=0;reg[3:0]rq_len=4,rs_beat=0;
 wire capacity,rq_rdy,phy_v,rs_rdy,out_v;wire[2:0]out_slot;wire[7:0]out_idx;
 integer issued=0,returned=0,a,b,c,lease;
 ot_hbm_svc_dma_pc_tile dut(.*);
 function automatic[16:0]tag(input integer id);tag={6'h36,3'(id%8),8'((id/8)*4)};endfunction
 function automatic integer length(input integer id);length=1+id%4;endfunction
 task tick;begin @(posedge clk);#1;end endtask
 task send_beat(input integer id,input integer beat);
 begin
 @(negedge clk);rs_v=1;rs_tag=tag(id);rs_beat=beat;#1;
 if(MUT==0&&(!rs_rdy||!out_v||out_slot!==3'(id%8)||out_idx!==8'((id/8)*4+beat)))$fatal(1,"tagged return identity id=%0d beat=%0d",id,beat);
 tick();returned=returned+1;
 @(negedge clk);rs_v=0;
 end endtask
 initial begin
 repeat(3)tick();@(negedge clk);rst=0;rq_v=1;rq_tag=tag(0);rq_len=length(0);
 repeat(3)begin #1;if(!capacity||rq_rdy||!phy_v)$fatal(1,"request backpressure identity");tick();end
 for(a=0;a<16;a=a+1)begin
 @(negedge clk);phy_ready=1;rq_v=1;rq_tag=tag(a);rq_len=length(a);#1;
 if(!capacity||!rq_rdy||!phy_v)$fatal(1,"CAM did not admit16leases id=%0d",a);
 tick();issued=issued+1;
 end
 @(negedge clk);rq_tag=17'h1fffc;rq_len=4;#1;
 if(capacity||rq_rdy||phy_v)$fatal(1,"CAM exceeded finite16leases");
 repeat(3)tick();@(negedge clk);rq_v=0;
 if(MUT==1)begin rs_v=1;rs_tag=17'h1ffff;rs_beat=0;tick();$display("UNEXPECTED_ACCEPT unknown tag accepted");$finish;end
 if(MUT==2)begin rs_v=1;rs_tag=tag(1);rs_beat=4;tick();$display("UNEXPECTED_ACCEPT out-of-bounds beat accepted");$finish;end
 if(MUT==3)begin send_beat(1,1);send_beat(1,1);$display("UNEXPECTED_ACCEPT duplicate beat accepted");$finish;end
 if(MUT==4)begin send_beat(0,0);send_beat(0,0);$display("UNEXPECTED_ACCEPT retired tag accepted");$finish;end
 // Permutation over16 leases starts at9; each lease returns its beats backwards.
 for(c=0;c<16;c=c+1)begin
 lease=(7*c+9)%16;
 for(b=length(lease)-1;b>=0;b=b-1)send_beat(lease,b);
 if(!capacity)$fatal(1,"CAM lease not retired after all unique beats");
 end
 if(issued!=16||returned!=40)$fatal(1,"transaction conservation");
 $display("PASS minimal_one_PC sixteen_CAM_leases finite_admission out_of_order_tags reverse_beat_order exact_slot_index lease_retirement");$finish;
 end
endmodule
