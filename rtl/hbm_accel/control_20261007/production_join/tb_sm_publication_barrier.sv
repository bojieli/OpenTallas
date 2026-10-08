module tb_sm_publication_barrier;
reg clk=0;always #5 clk=~clk;reg rst_n=0,source_valid=0,su_publication_ready=0,su_release_valid=0,owner_ready=0;
reg[93:0]source_context=94'hfedcba987654321,su_release_context=0;
wire source_ready,su_publication_valid,su_release_ready,owner_valid,fault;wire[93:0]su_publication_context;
ot_hbm_sm_publication_barrier #(.ENABLE(1)) dut(.*);
integer mode=0;
task tick;begin @(posedge clk);#1;@(negedge clk);#1;end endtask
initial begin
if($value$plusargs("MODE=%d",mode))begin end
repeat(2)tick;rst_n=1;tick;source_valid=1;#1;
if(!su_publication_valid||owner_valid||source_ready)$fatal(1,"publication phase");
repeat(4)tick;su_publication_ready=1;tick;su_publication_ready=0;
repeat(6)begin if(owner_valid||source_ready)$fatal(1,"retire before real consumer");tick;end
if(mode==2)begin force dut.state_n=0;#1;if(!fault||owner_valid||source_ready)$fatal(1,"state fault escaped");$display("PASS state fault");$finish;end
su_release_context=source_context;su_release_valid=1;
if(mode==1)begin su_release_context[73]=~su_release_context[73];#1;if(!fault||su_release_ready||owner_valid)$fatal(1,"wrong owner escaped");tick;su_release_valid=0;tick;if(!fault)$fatal(1,"fault not sticky");$display("PASS identity fault");$finish;end
#1;if(!su_release_ready)$fatal(1,"release missing");tick;su_release_valid=0;
if(!owner_valid||source_ready)$fatal(1,"owner hold");repeat(3)tick;owner_ready=1;#1;if(!source_ready)$fatal(1,"source not released");tick;source_valid=0;owner_ready=0;tick;
if(fault||owner_valid||source_ready)$fatal(1,"normal completion");$display("PASS actual publication+consumer release precede native retirement");$finish;
end
endmodule
