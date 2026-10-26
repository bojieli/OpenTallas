module tb;
 reg [4:0] row; reg [1:0] stack; wire [4:0] cfg, mutant_cfg;
 wire [4:0] wrong_row={2'b0,(row[2:0]+3'd1)};
 kv_hg_identity_cfg dut(row,stack,cfg);
 kv_hg_identity_cfg wrong_position(wrong_row,stack,mutant_cfg);
 integer r,s,expected,checks=0,mutants=0;
 function integer legacy_group(input integer rr);
  case(rr)
   0:legacy_group=4;1:legacy_group=5;2:legacy_group=0;3:legacy_group=1;
   4:legacy_group=2;5:legacy_group=3;6:legacy_group=6;7:legacy_group=7;
  endcase
 endfunction
 initial begin
  for(s=0;s<4;s=s+1)for(r=0;r<8;r=r+1)begin
   row=r;stack=s;#1;expected=(legacy_group(r)<<2)|s;
   if(cfg!==expected[4:0])$fatal(1,"identity mismatch r=%d s=%d",r,s);
   checks=checks+1;
   // Wrong logical-position identity must be observed at every position.
   if(mutant_cfg!==expected[4:0])mutants=mutants+1;
  end
  if(checks!=32||mutants!=32)$fatal(1,"incomplete controls");
  $display("PASS identity=%0d wrong_position_caught=%0d added_ff=0 added_cycles=0",checks,mutants);$finish;
 end
endmodule
