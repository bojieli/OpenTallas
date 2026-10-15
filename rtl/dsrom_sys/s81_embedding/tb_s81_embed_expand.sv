`timescale 1ns/1ps
module tb_s81_embed_expand # (parameter integer MUTANT=0, TOKEN=21946);
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,start=0;
 reg [12:0] base=0;
 wire rv,rb,busy,done,fault,vm_v,hop_v,hop_last;
 wire [8:0] ri;wire [511:0] rd,vm_d,hop_d;wire [13:0] vm_row;
 reg [511:0] expected[0:639];
 integer cycle=0,started=0,n=0,nh=0,errors=0,fd,i,delta;
 string outpath;
 ot_s81_embedding_bank #(.VIAMAP("embed.viamap.hex"),.OWNER(TOKEN/32320),
 .BANK(((TOKEN%32320)*320)/4096),.MUTANT(MUTANT)) dut(
 .clk(clk),.rst_n(rst_n),.start(start),.token(17'(TOKEN)),.base(base),
 .header(512'b0),.vm_base(14'd1024),.busy(busy),.done(done),.fault(fault),
 .vm_v(vm_v),.vm_row(vm_row),.vm_d(vm_d),.hop_v(hop_v),.hop_last(hop_last),.hop_d(hop_d));
 initial begin
 $readmemh("expected.mem",expected);
 if(!$value$plusargs("BASE=%d",i))i=0;base=13'(i);
 if(!$value$plusargs("OUT=%s",outpath))outpath="hin.actual.mem";
 fd=$fopen(outpath,"w");
 end
 always @(negedge clk) begin
 cycle=cycle+1;
 if(cycle==4)rst_n=1;
 start=(cycle==8);
 if(start)started=cycle+1;
 if(hop_v)begin
   $fdisplay(fd,"%0128h",hop_d);
   if(nh==0)begin if(hop_d!==512'b0 || cycle-started!=325)errors=errors+1;end
   else begin
     delta=(nh-1)/16*26+336+(nh-1)%16;
     if(cycle-started!=delta) begin $display("cycle mismatch got %0d expect %0d",cycle-started,delta);errors=errors+1;end
     if(hop_d!==expected[nh-1])errors=errors+1;
     if(hop_last!==(nh==640))errors=errors+1;
   end
   nh=nh+1;
 end
 if(vm_v)begin
   if(vm_row!=1024+n || vm_d!==expected[n])errors=errors+1;
   n=n+1;
 end
 if(done || cycle>2000)begin
   $fclose(fd);
   $display("EMBED_NATIVE rows=%0d hop=%0d fault=%0d errors=%0d cycles=%0d",n,nh,fault,errors,cycle-started);
   if(n!=640 || nh!=641 || fault || errors || cycle-started!=1365)$fatal(1,"EMBED_NATIVE FAIL");
   $display("EMBED_NATIVE PASS");$finish;
 end
 end
endmodule
