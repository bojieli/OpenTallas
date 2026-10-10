`timescale 1ns/1ps
module tb_s81_engram_aperture;
 parameter BAD=0;
 reg ck=0,rst_n=0,stack_v=0,stack_sel=0,pc_v=0,commit=0;
 reg[5:0]pc=0;reg[29:0]base=2929688,limit=16430408;
 wire valid,ce,fault;wire[1919:0] pb,pl;
 always #0.416667 ck=~ck;
 ot_s81_engram_aperture #(.ENABLE(1)) dut(.ck(ck),.rst_n(rst_n),.stack_v(stack_v),.stack_sel(stack_sel),
 .usable(30'd632812500),.rsv(30'd93750016),.plain(30'd525773056),.yarn(30'd527870208),.span(30'd2097152),
 .pc_v(pc_v),.pc(pc),.base(base),.limit(limit),.commit(commit),.aperture_valid(valid),.pc_base(pb),.pc_limit(pl),.corrected(ce),.fault(fault));
 integer i;
 initial begin
 repeat(4)@(negedge ck);rst_n=1;
 for(i=0;i<2;i=i+1)begin @(negedge ck);stack_v=1;stack_sel=i;end
 @(negedge ck);stack_v=0;
 if(BAD==1)base=0;
 for(i=0;i<64;i=i+1)begin @(negedge ck);pc_v=1;pc=i;end
 @(negedge ck);pc_v=0;commit=1;
 @(negedge ck);commit=0;repeat(2)@(negedge ck);
 if(BAD==1)begin if(valid||!fault)$fatal(1,"invalid overlap accepted");$display("APERTURE INVALID_REJECTED");$finish;end
 if(!valid||fault)$fatal(1,"valid install rejected");
 for(i=0;i<64;i=i+1)if(pb[i*30+:30]!=2929688||pl[i*30+:30]!=16430408)$fatal(1,"wrong bound");
 dut.pmem[0]=dut.pmem[0]^72'd1;#0.1;
 if(!valid||!ce||pb[29:0]!=2929688)$fatal(1,"single correction failed");
 dut.pmem[0]=dut.pmem[0]^72'd2;repeat(2)@(negedge ck);
 if(valid||!fault)$fatal(1,"double corruption accepted");
 $display("APERTURE PASS 64PC installed single corrected double rejected");$finish;
 end
endmodule
