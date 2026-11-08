`timescale 1ns/1ps
module tb_svc_pvq_h8_capture_pad;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg dr_on=0;reg[2:0]p_i=0,ra=0,wa=0;reg[1063:0]wd=0,wm=0;
 reg[47:0]provenance=0;reg head_pass=0;
 wire[512:0]out;
 ot_svc_pvq_h8_capture_pad #(.MUT(MUT))dut(.*);
 reg[1063:0]mem[0:7];reg[512:0]ref_o;reg started=0;
 integer checks=0,errors=0,headers=0,payloads=0,warm_holds=0,k,j,r;
 reg[31:0]rng=32'h1113b19d;
 function automatic[31:0]next_r(input[31:0]v);next_r=(v^(v<<13))^((v^(v<<13))>>17)^(((v^(v<<13))^((v^(v<<13))>>17))<<5);endfunction
 always @(posedge clk)begin
  if(dr_on)begin
   if(p_i==0)ref_o<={1'b1,392'd0,provenance,mem[ra][1063:1056],31'd0,head_pass,mem[ra][31:0]};
   else ref_o<={1'b0,256'd0,mem[ra][32+256*(p_i-1)+:256]};
   started<=1;
  end
  if(|wm)mem[wa]<=(mem[wa]&~wm)|(wd&wm);
  #1;if(started)begin
   checks++;
   if(out!==ref_o)begin if(errors<8)$display("mismatch k%0d pass%b pi%0d row%0d out%h ref%h",k,head_pass,p_i,ra,out,ref_o);errors++;end
   if(dr_on&&p_i==0)headers++;if(dr_on&&p_i!=0)payloads++;if(!dr_on)warm_holds++;
  end
 end
 task stimulus(input integer edge_n);
 begin
  for(integer z=0;z<33;z++)begin rng=next_r(rng);wd[32*z+:32]=rng;end
  rng=next_r(rng);wd[1063:1056]=rng[7:0];
  wm={1064{1'b1}};
  if(edge_n%7==0)wm=0;
  else if(edge_n%11==0)begin wm=0;wm[31:0]=32'h55aa33cc;wm[32+256*(edge_n%4)+:256]={8{32'ha55a0ff0}};wm[1063:1056]=8'h5a;end
  wa=3'(edge_n/3);
  ra=3'(edge_n/5);
  p_i=3'(edge_n%5);
  dr_on=(edge_n%13!=0);
  head_pass=(edge_n/37)%2;
  provenance={21'(edge_n*7),1'b1,4'(edge_n),2'(edge_n/8),20'(edge_n*11)};
 end endtask
 initial begin
  for(j=0;j<8;j++)mem[j]=0;
  // Prime rows, then two-pass headers, all four payload groups, partial masks,
  // simultaneous read/write and warm-reset control gaps with storage retained.
  for(k=0;k<1400;k++)begin
   @(negedge clk);stimulus(k);
   if(k<8)begin dr_on=0;wa=3'(k);wm={1064{1'b1}};end
   if((k>=400&&k<416)||(k>=900&&k<916))begin dr_on=0;wm=0;head_pass=0;provenance=0;end
  end
  @(negedge clk);dr_on=0;wm=0;repeat(2)@(negedge clk);
  if(errors)$fatal(1,"PVQ_H8_PAD FAIL MUT%0d errors%0d checks%0d",MUT,errors,checks);
  $display("PVQ_H8_PAD PASS checks%0d headers%0d payloads%0d holds%0d MUT%0d",checks,headers,payloads,warm_holds,MUT);$finish;
 end
endmodule
