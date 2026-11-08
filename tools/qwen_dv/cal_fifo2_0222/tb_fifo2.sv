`timescale 1ns/1ps
module tb_fifo2;
reg clk=0;always #0.4165 clk=~clk;
reg rce=0,wce=0;reg[5:0]ra=0,wa=0;reg[511:0]wd=0,mask=0;
wire[511:0]gold,dut,row_mut,edge_raw;reg[511:0]edge_mut;
ot_sram_1r1w_64x512_m1_r2c2 old(.clk(clk),.r_ce_in(rce),.r_addr_in(ra),.rd_out(gold),.w_ce_in(wce),.w_addr_in(wa),.wd_in(wd),.w_mask_in(mask),.rr_en(2'd0),.rr_addr(12'd0),.cr_en(2'd0),.cr_sel(18'd0));
ot_qc_cal_fifo2_512 good(.clk(clk),.r_ce_in(rce),.r_addr_in(ra),.rd_out(dut),.w_ce_in(wce),.w_addr_in(wa),.wd_in(wd),.w_mask_in(mask),.rr_en(2'd0),.rr_addr(12'd0),.cr_en(2'd0),.cr_sel(18'd0));
// Two seeded negative controls: read the wrong row, or add one unpriced output edge.
ot_qc_cal_fifo2_512 bad_row(.clk(clk),.r_ce_in(rce),.r_addr_in({ra[5:1],!ra[0]}),.rd_out(row_mut),.w_ce_in(wce),.w_addr_in(wa),.wd_in(wd),.w_mask_in(mask),.rr_en(2'd0),.rr_addr(12'd0),.cr_en(2'd0),.cr_sel(18'd0));
ot_qc_cal_fifo2_512 bad_edge(.clk(clk),.r_ce_in(rce),.r_addr_in(ra),.rd_out(edge_raw),.w_ce_in(wce),.w_addr_in(wa),.wd_in(wd),.w_mask_in(mask),.rr_en(2'd0),.rr_addr(12'd0),.cr_en(2'd0),.cr_sel(18'd0));
always @(posedge clk)edge_mut<=edge_raw;
reg[511:0]ref0=0,ref1=0,expected;reg seen=0;integer cycle=0,checks=0,errors=0,golden_errors=0,row_errors=0,edge_errors=0,collisions=0,partial=0,holds=0;integer combos[0:15];reg[31:0]rng=32'h618c8b39;
function automatic[31:0]next_rng(input[31:0]v);reg[31:0]t;begin t=v^(v<<13);t=t^(t>>17);next_rng=t^(t<<5);end endfunction
initial for(integer j=0;j<16;j=j+1)combos[j]=0;
always @(posedge clk)begin
if(rce)begin expected=ra[0]?ref1:ref0;seen=1;end
if(wce)begin if(wa[0])ref1=(wd&mask)|(ref1&~mask);else ref0=(wd&mask)|(ref0&~mask);end
if(rce&&wce&&ra==wa)collisions=collisions+1;
if(wce&&mask!==0&&mask!=={512{1'b1}})partial=partial+1;
if(!rce)holds=holds+1;
combos[{rce,wce,ra[0],wa[0]}]=combos[{rce,wce,ra[0],wa[0]}]+1;
end
always @(negedge clk)begin
if(seen)begin
checks=checks+1;
if(gold!==expected)golden_errors=golden_errors+1;
if(dut!==gold)begin errors=errors+1;if(errors<4)$display("DIFF cycle=%0d gold=%h dut=%h",cycle,gold,dut);end
if(row_mut!==gold)row_errors=row_errors+1;
if(edge_mut!==gold)edge_errors=edge_errors+1;
end
cycle=cycle+1;
if(cycle==800)begin
$display("FIFO2 checks=%0d errors=%0d golden_errors=%0d row_mutant=%0d edge_mutant=%0d collisions=%0d partial=%0d holds=%0d",checks,errors,golden_errors,row_errors,edge_errors,collisions,partial,holds);
for(integer k=0;k<16;k=k+1)begin $display("CE_ROW_COMBO %0d count=%0d",k,combos[k]);if(combos[k]==0)errors=errors+1;end
if(errors||golden_errors||row_errors==0||edge_errors==0||collisions==0||partial==0||holds==0)$fatal(1,"FIFO2 exactness/control coverage failed");
$finish;
end
// Drive one complete CE/address combination every16cycles, full512-bit changing payload/masks.
rce=cycle[3];wce=cycle[2];ra={5'd0,cycle[1]};wa={5'd0,cycle[0]};
for(integer j=0;j<16;j=j+1)begin rng=next_rng(rng);wd[j*32+:32]=rng;rng=next_rng(rng);mask[j*32+:32]=rng;end
case(cycle%7)0:mask=0;1:mask={512{1'b1}};2:begin mask=0;mask[0]=1;mask[511]=1;end 3:mask={256{2'b10}};default:begin end endcase
// Extended CE hold phase preserves both SRAM state and registered output without any reset.
if(cycle>=640&&cycle<672)begin rce=0;wce=0;end
end
endmodule
