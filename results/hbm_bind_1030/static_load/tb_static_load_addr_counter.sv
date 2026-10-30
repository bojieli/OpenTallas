`timescale 1ns/1ps
module tb_static_load_addr_counter;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,dv=0,step=0;reg[226:0]desc=0;
 wire[3:0]count;wire active,fault,av,last;wire[39:0]sa,da;wire[2:0]fmt;
 ot_hbm_static_load_addr_counter #(.MUT_ZERO_STRIDE(MUT==1),.MUT_STRIPE(MUT==2),.COALESCE(0)) dut(clk,rst_n,dv,desc,step,active,fault,av,last,sa,da,fmt,count);
 integer fs[0:5];integer mode,base_stack;integer f,si,di,r,i,esize,sc,dc,checked=0;
 task tick;begin @(posedge clk);#1;end endtask
 task reset;begin @(negedge clk);rst_n=0;dv=0;step=0;repeat(2)tick();@(negedge clk);rst_n=1;end endtask
 initial begin
 fs[0]=0;fs[1]=1;fs[2]=2;fs[3]=4;fs[4]=5;fs[5]=6;
 for(mode=0;mode<2;mode=mode+1)for(base_stack=0;base_stack<4;base_stack=base_stack+1)for(f=0;f<6;f=f+1)for(si=0;si<3;si=si+1)for(di=0;di<3;di=di+1)begin
 reset();sc=si==2?3:si;dc=di;esize=(fs[f]==0||fs[f]==5)?4:(fs[f]==1)?2:1;
 desc=0;desc[4:2]=3'(fs[f]);desc[44:5]=40'h100000;desc[44:42]=3'(mode);desc[41:40]=2'(base_stack);desc[76:45]=512;desc[92:77]=16'(sc);
 desc[94:93]=1;desc[97:95]=(fs[f]==5)?3'd5:3'd0;desc[137:98]=12345;desc[169:138]=128;desc[185:170]=16'(dc);desc[205:186]=3;desc[226:206]=7;
 dv=1;tick();@(negedge clk);dv=0;
 for(r=0;r<3;r=r+1)for(i=0;i<7;i=i+1)begin
 step=1;tick();
 if(!av||fault||sa!=((40'((base_stack+(mode?r:0))%4)<<35)+40'h100000+r*512+i*sc*esize)||da!=(12345+r*128+i*dc)||fmt!=fs[f]||last!=(r==2&&i==6))
 $fatal(1,"COUNTER_MISMATCH f=%0d sis=%0d dis=%0d row=%0d col=%0d src=%h dst=%h fault=%b",fs[f],sc,dc,r,i,sa,da,fault);
 checked=checked+1;@(negedge clk);
 end
 step=0;tick();if(active||av||fault)$fatal(1,"COUNTER_DRAIN");
 end
 // Resolved227 excludes zero extents; malformed dates fail closed.
 reset();desc=0;dv=1;tick();if(!fault||active)$fatal(1,"COUNTER_ZERO_EXTENT");
 reset();step=1;tick();if(!fault||av)$fatal(1,"COUNTER_LATE_STEP");
 reset();desc=0;desc[94:93]=1;desc[205:186]=1;desc[226:206]=1;desc[4:2]=5;desc[97:95]=0;dv=1;tick();if(!fault||active)$fatal(1,"COUNTER_U32_DST_MISMATCH");
 reset();desc[4:2]=0;desc[97:95]=3;dv=1;tick();if(!fault||active)$fatal(1,"COUNTER_RESERVED_DST");
 reset();desc=0;desc[94:93]=1;desc[205:186]=1;desc[226:206]=1;desc[44:42]=2;dv=1;tick();if(!fault||active)$fatal(1,"COUNTER_BAD_SOURCE_CODE");
 reset();desc[44:42]=0;desc[4:2]=3;dv=1;tick();if(!fault||active)$fatal(1,"COUNTER_BAD_FORMAT");
 $display("PASS STATIC_LOAD_ADDR_COUNTER formats=6 destination_controls=U32_to_FP32_rejected/reserved3_rejected descriptors=432 sourcecodes=linear0/stripe4_1 all4stacks/wrap words=%0d istride0=broadcast II=1 scalar_VMbytes_per_step=4 added_output_cycles=1",checked);$finish;
 end
endmodule
