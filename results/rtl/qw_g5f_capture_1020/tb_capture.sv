module tb;
 reg ck=0; always #5 ck=~ck;
 reg rs=0; reg [15:0] f=0; wire o; wire one;
 qfd_fault_capture #(.N(16)) d(ck,rs,f,o);
 qfd_fault_capture #(.N(1)) d1(ck,rs,f[0],one);
 integer tests=0;
 task tick; begin @(posedge ck); #1; end endtask
 task check(input bit condition, input string label_); begin
 tests=tests+1; if (!condition) begin $display("CAPTURE_FAIL %s",label_); $fatal(1); end end endtask
 task reset; begin @(negedge ck); rs=0; f=0; #1; check(o===0 && one===0,"reset_epoch_clears"); tick(); tick(); @(negedge ck); rs=1; end endtask
 initial begin
 #1; rs=1; #1; rs=0;
 // Each pin pulses on first or second real edge, then disappears before release.
 for (int phase=1;phase<=2;phase++) for(int pin=0;pin<16;pin++) begin
 reset();
 if(phase==2) begin tick(); @(negedge ck); end
 f=16'b1<<pin; tick(); @(negedge ck); f=0;
 repeat(4) tick(); check(o===1,"first_two_edge_pulse_retained");
 if(pin==0)check(one===1,"N1_first_edge_pulse");
 else check(one===0,"N1_no_foreign_pin");
 repeat(8) tick(); check(o===1,"steady_sticky_retained");
 end
 reset(); repeat(8) tick(); check(o===0 && one===0,"no_fault_after_rearm");
 @(negedge ck); f=1; tick(); @(negedge ck); f=0;
 repeat(4)tick();check(o===1 && one===1,"steady_pulse");
 reset(); repeat(8)tick();check(o===0 && one===0,"second_reset_rearm");
 $display("CAPTURE_PASS checks=%0d",tests); $finish;
 end
endmodule
