`timescale 1ns/1ps
module tbmask #(parameter SHARDTAIL=0);
 reg clk=0;always #0.4165 clk=~clk;reg rst_n=0,start=0;wire start_ready;
 reg[16:0]row0=0;reg[31:0]transaction=32'h55;reg embed_valid=0;wire embed_ready;
 reg[255:0]embed_data=0;reg[3:0]embed_beat=0;reg[31:0]embed_id=32'h55;reg embed_last=0;
 wire head_go;reg head_valid=0;reg[31:0]head_bits=0;reg head_fault=0;
 wire joined_valid,done,best_valid,fault;wire[31:0]joined_bits,best_bits;wire[16:0]joined_row,best_row;
 ot_dsrom_markov_head_driver #(.ENABLE(1),.PINREG(1),.VALID_ROWS(SHARDTAIL?6:32)) dut(.*);
 reg[255:0]vec[0:15];reg[31:0]gold[0:15];integer i,n,transaction_case=0,wanted=0,got=0,best=0;
 reg[8*1024-1:0]dir;
 always @(negedge clk)if(rst_n)begin
  if(fault)$fatal(1,"mask driverfault");
  if(joined_valid)begin
   if(got>=wanted||joined_row!=row0+got||joined_row>=129280||joined_bits!==gold[got])$fatal(1,"padded row reached join %0d %0d",got,joined_row);
   got=got+1;
  end
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR");
  $readmemh({dir,"/embed.hex"},vec);$readmemh({dir,"/gold.hex"},gold);
  for(transaction_case=0;transaction_case<2;transaction_case=transaction_case+1)begin
   rst_n=0;start=0;head_valid=0;embed_valid=0;got=0;
   row0=transaction_case==1?129280:(SHARDTAIL?21920:129264);
   wanted=transaction_case==1?0:(SHARDTAIL?6:16);
   best=13;if(SHARDTAIL)best=0;
   repeat(5)@(negedge clk);rst_n=1;repeat(3)@(negedge clk);start=1;@(negedge clk);start=0;
   for(i=0;i<16;i=i+1)begin
    while(!embed_ready)@(negedge clk);embed_valid=1;embed_data=vec[i];embed_beat=i;embed_last=i==15;@(negedge clk);
   end
   embed_valid=0;embed_last=0;repeat(3)@(negedge clk);
   // Valid rows have all-negative logits; scheduledpadding haszero, which wouldwin.
   for(n=0;n<32;n=n+1)begin
    head_valid=1;head_bits=n<wanted?32'hc9800000:32'b0;@(negedge clk);head_valid=0;
    repeat(255)@(negedge clk);
   end
   while(!done)@(negedge clk);
   if(got!=wanted||best_valid!=(wanted!=0))$fatal(1,"valid rowcount %0d %0d",got,wanted);
   if(wanted!=0&&(best_row!=row0+best||best_bits!==gold[best]||best_bits[31]!=1))$fatal(1,"zero padding won overnegative realrows");
   $display("PASS paddedmask shardtail=%0d row0=%0d valid=%0d skipped=%0d bestvalid=%0d",SHARDTAIL,row0,got,32-got,best_valid);
  end
  $finish;
 end
 initial begin #40000;$fatal(1,"timeout");end
endmodule
