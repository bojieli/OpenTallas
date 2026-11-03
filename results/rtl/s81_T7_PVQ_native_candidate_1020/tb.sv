`timescale 1ps/1ps
module tb;
reg clk=0;always begin #416 clk=1;#417 clk=0;end
reg rst_n=0,cfg_v=0,cfg_valid=0,launch=0,launch_ok=0;
reg[19:0]cfg_owner=0;reg[9:0]user_id=0;reg[7:0]tag_id=0;reg[1:0]quarter=0;reg[3:0]tile=0;reg[20:0]position=0;
wire[439:0]prov;wire bad;
dsdv_pv_source_identity #(.ENABLE(1)) id(.*,.provenance(prov));
reg dr_on=0;reg[2:0]p_i=0,ra=0,wa=0;reg[2119:0]wd=0,wm=0;wire[2119:0]pb;wire[512:0]gold,good,wrong;
ot_bind_native_9c28130c03bbd6a26f6fd9a5 mem(ra,pb,wa,clk,wd,wm);
native_capture cap(clk,dr_on,p_i,pb,prov,gold);
integer mutant=0;reg old_dr=0;reg[47:0]early[0:7];
always@(posedge clk)begin old_dr<=dr_on;if(|wm)early[wa]<=prov[47:0];end
wire ce=(mutant==3)?old_dr:dr_on;
wire[47:0]candidate_prov=(mutant==2)?early[ra]:prov[47:0];
pvq_sram_candidate dut(clk,ce,p_i,ra,wa,wd,wm,candidate_prov,good);
pvq_sram_candidate #(.WRONG_COLLISION(1)) neg(clk,dr_on,p_i,ra,wa,wd,wm,prov[47:0],wrong);
wire[512:0]observed=(mutant==1)?wrong:good;
integer i,j,reads=0,writes=0,collisions=0,resets=0,held=0,headers=0;reg[31:0]rng=32'h92ac741f;
function automatic[31:0]nextword(input[31:0]v);nextword=v^(v<<13);nextword=nextword^(nextword>>17);nextword=nextword^(nextword<<5);endfunction
initial begin
 void'($value$plusargs("mutant=%d",mutant));
 for(i=0;i<4096;i=i+1)begin
  @(negedge clk);
  rng=nextword(rng);rst_n=(i>1)&&(i%67!=40);cfg_v=(i%3==0);cfg_valid=1;cfg_owner=rng[19:0];launch=(i%3==2);launch_ok=1;user_id=rng[17:8];tag_id=rng[7:0];quarter=i;tile=i>>2;position=i*23;
  dr_on=(i>=8)&&(i%7!=6);p_i=(i/8)%5;ra=i;wa=(i%3==0)?ra:(i>>3);
  for(j=0;j<67;j=j+1)begin rng=nextword(rng);if(j<66)wd[32*j+:32]=rng;end
  wd[2119:2112]=rng[7:0];
  wm=(i<8||i%4!=0)?'1:'0;
  if(i%4==0&&i>=8)for(j=0;j<2120;j=j+1)wm[j]=(j+i)%3==0;
  if(i%11==0&&i>=8)wm=0;
  if(dr_on)begin reads++;if(p_i==0)headers++;end else held++;
  if(|wm)writes++;if(dr_on&&|wm&&ra==wa)collisions++;if(!rst_n)resets++;
  @(posedge clk);#2;
  if(gold!==observed)begin $display("PVQ_NATIVE_FAIL mutant=%0d edge=%0d pi=%0d ra=%0d wa=%0d dr=%0d rst=%0d gold=%h observed=%h",mutant,i,p_i,ra,wa,dr_on,rst_n,gold,observed);$fatal(1);end
 end
 $display("PVQ_NATIVE_PASS edges=4096 reads=%0d headers=%0d writes=%0d collisions=%0d resets=%0d held=%0d",reads,headers,writes,collisions,resets,held);$finish;
end
endmodule
