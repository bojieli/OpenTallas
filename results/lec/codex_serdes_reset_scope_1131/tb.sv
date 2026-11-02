`timescale 1ps/1fs
module tb;
parameter real PMA_PHASE_PS=0;
reg clk=0, pma_rck=0, pma_enable=1, external_rst_n=1, measure=0;
always #416.5 clk=~clk;
initial begin #(PMA_PHASE_PS); forever begin #416.5; if(pma_enable) pma_rck=~pma_rck; else pma_rck=0; end end
wire [154:0] obs;
cone dut(.clk(clk),.pma_rck(pma_rck),.external_rst_n(external_rst_n),.obs(obs));
integer cur[0:154], longest[0:154];
genvar g;
generate for(g=0;g<155;g=g+1)begin:counter
  wire selected_clock = (g==146 || g==151 || g==152 || g==153 || g==154) ? pma_rck : clk;
  always @(posedge selected_clock) if(measure)begin
    if(obs[g] === 1'b0)begin cur[g]=cur[g]+1; if(cur[g]>longest[g])longest[g]=cur[g]; end
    else cur[g]=0;
  end
end endgenerate
task clear;
integer i;
begin measure=0; for(i=0;i<155;i=i+1)begin cur[i]=0;longest[i]=0;end measure=1;end
endtask
task report_case(input integer mode,input integer held);
integer i,mn,txmn,rxmn;
begin
 measure=0;mn=100000;txmn=100000;rxmn=100000;
 for(i=0;i<155;i=i+1)begin
  if(longest[i]<mn)mn=longest[i];
  if((i==146 || i==151 || i==152 || i==153 || i==154))begin if(longest[i]<rxmn)rxmn=longest[i];end
  else if(longest[i]<txmn)txmn=longest[i];
 end
 $display("RESET_CASE phase=%0.3f mode=%0d held=%0d minimum=%0d core_min=%0d rx_min=%0d rn_r_low=%0d rx_leaf_low=%0d",PMA_PHASE_PS,mode,held,mn,txmn,rxmn,longest[146],longest[154]);
 if(mode<=1 && mn<64)$fatal(1,"running-clock contract width failed");
 if(mode==2 && mn>=64)$fatal(1,"short-reset negative not caught");
 if(mode==3 && (mn>=64 || longest[146]!=2 || longest[154]!=2))$fatal(1,"stopped-clock scope negative did not expose two-edge RX pulse");
end endtask
task pulse(input integer mode,input integer held);
begin
 @(negedge clk);clear();external_rst_n=0;
 repeat(held)@(negedge clk);
 external_rst_n=1;
 repeat(40)@(negedge clk);
 if(mode==3)begin
  $display("STOPPED_STATE rn_r=%b rx_leaf=%b",dut.rn_r,dut.out_leaf[0]);
  if(dut.rn_r!==0 || dut.out_leaf[0]!==1)$fatal(1,"async versus synchronous reset distinction absent");
  pma_enable=1;repeat(40)@(negedge clk);
 end
 report_case(mode,held);
end endtask
initial begin
 #1;pulse(0,64);pulse(1,64);pulse(2,61);
 @(negedge pma_rck);pma_enable=0;pulse(3,64);
 $display("RESET_SCOPE_DIAGNOSTIC_COMPLETE clock_period_ps=833; no full PHY/boot/adoption claim");$finish;
end
endmodule
