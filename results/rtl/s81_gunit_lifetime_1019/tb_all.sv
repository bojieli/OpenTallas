`timescale 1ns/1ps
module tb;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,wv=0,tj_set=0,tj_w=0,launch=0,cw_v=0; reg[9:0]wa=0,cw_a=0;reg[255:0]wd=0;
wire[767:0] bases;wire[95:0]scales;wire tbl_f,fault;
vehicle dut(.*);
integer checks=0,gaps=0,misses=0; reg[767:0] snapshot;
task step;begin @(posedge clk); #1; checks++; @(negedge clk);end endtask
task reset;begin rst_n=0;wv=0;launch=0;repeat(3)step();rst_n=1;repeat(7)step();end endtask
task data(input integer r,input integer tag);begin for(integer k=0;k<8;k++)wd[32*k+:32]=32'h41000000+(tag<<16)+(r<<8)+k;end endtask
task write_row(input integer setid,input integer rowid,input integer tag);begin wv=1;wa=(setid<<8)+56+rowid;data(rowid,tag);step();wv=0;end endtask
initial begin
// No macro initialization: cold launch is unqualified, never compare unknown payload to a fake zero gold.
reset();launch=1;step();launch=0;
$display("COLD_UNPROGRAMMED_GAP fault=%0d (no table-valid protection)",fault);
for(integer s=0;s<2;s++)for(integer r=0;r<6;r++)write_row(s,r,1+s);
repeat(8)step();
for(integer s=0;s<2;s++)for(integer w=0;w<2;w++)begin
 tj_set=1'(s);tj_w=1'(w);repeat(5)step();
 for(integer k=0;k<24;k++)begin
  if(bases[32*k+:32] !== (32'h41000000+((1+s)<<16)+((w*3+k/8)<<8)+(k%8)))$fatal(1,"PROGRAMMED_DATA_FAIL s=%0d w=%0d k=%0d got=%h",s,w,k,bases[32*k+:32]);
  checks++;
 end
 launch=1;step();step();launch=0;step(); // consecutive qualified captures
end
$display("PROGRAMMED_DATA_PASS words=96 back_to_back_launches=8");
tj_set=0;tj_w=0;repeat(6)step();
for(integer gap=0;gap<=6;gap++)begin
 reset();wv=1;wa=56;data(0,7+gap);launch=(gap==0);step();wv=0;
 if(gap>0)begin repeat(gap-1)step();launch=1;step();end
 launch=0;step();
 $display("WRITE_LAUNCH gap=%0d fault=%0d expected=%0d",gap,fault,gap<=4);
 `ifndef FIXED
 if(gap==0 && !fault)begin misses++;$display("CAUSAL_SAME_EDGE_MISS");end
 else
`endif
 if(fault !== (gap<=4))$fatal(1,"WINDOW_FAIL gap=%0d",gap);
 gaps++;
end
reset();tj_w=0;repeat(5)step();tj_w=1;wv=1;wa=59;data(3,25);step();wv=0;repeat(2)step();launch=1;step();launch=0;step();
$display("SELECTOR_SWITCH_WRITE gap=3 fault=%0d expected=1",fault);
if(!fault)begin
`ifdef FIXED
$fatal(1,"SELECTOR_HISTORY_FAIL");
`else
misses++;$display("CAUSAL_SELECTOR_HISTORY_MISS");
`endif
end
// Abort a live guarded window, recover without clearing SRAM data.
launch=0;reset();repeat(5)step();launch=1;step();launch=0;step();if(fault)$fatal(1,"RESET_RECOVERY_FAIL");
$display("RESET_ABORT_RECOVERY_PASS");
// All logical rows, all prior-to-next selector pairs, every boundary distance.
for(integer sel=0;sel<4;sel++)for(integer gap=0;gap<=6;gap++)begin
 reset();tj_set=1'(sel/2);tj_w=1'(sel%2);repeat(5)step();
 wv=1;wa=(sel/2)*256+56+(sel%2)*3;data((sel%2)*3,31+sel);launch=(gap==0);step();wv=0;
 if(gap>0)begin repeat(gap-1)step();launch=1;step();end
 launch=0;step();if(fault !== (gap<=4))$fatal(1,"ALL_ROW_WINDOW_FAIL sel=%0d gap=%0d",sel,gap);
end
for(integer oldsel=0;oldsel<4;oldsel++)for(integer newsel=0;newsel<4;newsel++)begin
 reset();tj_set=1'(oldsel/2);tj_w=1'(oldsel%2);repeat(5)step();
 tj_set=1'(newsel/2);tj_w=1'(newsel%2);wv=1;wa=(newsel/2)*256+56+(newsel%2)*3;data((newsel%2)*3,40+newsel);step();wv=0;
 repeat(2)step();launch=1;step();launch=0;step();if(!fault)$fatal(1,"ALL_SELECTOR_HISTORY_FAIL old=%0d new=%0d",oldsel,newsel);
end
for(integer selected=0;selected<4;selected++)for(integer written=0;written<4;written++)if(selected!=written)begin
 reset();tj_set=1'(selected/2);tj_w=1'(selected%2);repeat(5)step();
 wv=1;wa=(written/2)*256+56+(written%2)*3;data((written%2)*3,50+written);launch=1;step();wv=0;launch=0;step();
 if(fault)$fatal(1,"NONSELECTED_FALSE_FAULT selected=%0d written=%0d",selected,written);
end
repeat(6)step();snapshot=bases;reset();repeat(5)step();if(bases!==snapshot)$fatal(1,"WARM_RESET_DATA_RETENTION_FAIL");
$display("ALL_ROWS_TRANSITIONS_PASS windows=28 transitions=16 nonselected_collisions=12 warm_reset_payload_retained=1");
$display("LIFETIME_SOURCE_CHARACTERIZATION checks=%0d gaps=%0d missing_guards=%0d physical_contact_density=206/32=6.4375",checks,gaps,misses);
`ifdef FIXED
if(misses!=0)$fatal(1,"FIXED_GUARD_FAIL");
$display("CORRECTED_LIFETIME_PASS");
`else
if(misses!=2)$fatal(1,"EXPECTED_TWO_CAUSAL_SOURCE_GAPS");
`endif
$finish;
end
endmodule
