`timescale 1ns/1ps
module tb;
reg ck=0;always #0.4165 ck=~ck;
reg rst_top=0,head_prepare_v=0,p_hev=0,p_hfc=1;
reg[1:0]head_prepare_user=0,p_hg=2;
reg[17:0]head_prepare_token=0,head_prepare_position=0;
reg[15:0]p_he=16'h10;
reg[58:0]p_ht=0;wire head_descriptor_v;wire[58:0]head_descriptor_tag;wire[1:0]head_descriptor_generation;
dut u(.*);
integer checks=0;
task edge_check(input bit want);
 @(posedge ck);#0.001;checks=checks+1;
 if(head_descriptor_v!==want)$fatal(1,"PREP_FAIL check=%0d got=%0b want=%0b",checks,head_descriptor_v,want);
endtask
task drive(input bit prep,input[1:0]user,input[17:0]token,pos,input bit host,input[17:0]hosttoken);
 @(negedge ck);head_prepare_v=prep;head_prepare_user=user;head_prepare_token=token;head_prepare_position=pos;p_hev=host;
 p_ht={p_he,6'd0,hosttoken,pos[12:0],6'd0};
endtask
task reset;
 @(negedge ck);rst_top=0;head_prepare_v=0;p_hev=0;
 edge_check(0);edge_check(0);@(negedge ck);rst_top=1;
endtask
initial begin
 reset();
 drive(1,1,123,79,0,0);edge_check(0);
 drive(0,1,123,79,0,0);edge_check(0);
 drive(0,1,123,79,0,0);edge_check(1);
 if(head_descriptor_tag!={14'd0,2'd1,6'd0,18'd123,13'd79,6'd0}||head_descriptor_generation!=2)$fatal(1,"PREP_FAIL filler tuple");
 drive(0,1,123,79,0,0);edge_check(0);
 $display("FILLER_NATIVE_CAPTURE_EDGES=3");
 reset();
 // A matching pulse before prepare is not a substitute for the pending cohort.
 drive(0,0,321,81,1,321);edge_check(0);
 drive(1,0,321,81,0,0);edge_check(0);
 drive(0,0,321,81,0,0);edge_check(0);
 drive(0,0,321,81,0,0);edge_check(0);
 drive(0,0,321,81,0,0);edge_check(0);
 drive(0,0,321,81,1,322);edge_check(0);
 drive(0,0,321,81,1,321);edge_check(1);
 if(head_descriptor_tag!={16'h10,6'd0,18'd321,13'd81,6'd0}||head_descriptor_generation!=2)$fatal(1,"PREP_FAIL HOST tuple");
 drive(0,0,321,81,1,321);edge_check(0);
 $display("HOST_LATE_MATCH_REQUIRED=1 EARLY_AND_WRONG_TOKEN_REJECTED=1");
 reset();
 drive(1,0,456,83,1,456);edge_check(0);
 drive(0,0,456,83,1,456);edge_check(0);
 drive(0,0,456,83,1,456);edge_check(0);
 drive(0,0,456,83,1,456);edge_check(1);
 $display("USER0_PREPARE_MIN_CAPTURE_EDGES=4");
 $display("PREP_PASS checks=%0d",checks);$finish;
end
endmodule
