`timescale 1ns/1ps
module tb_vm_service_wordbank;
 reg clk=0;always #1 clk=~clk;
 reg rst_n=0,expect_v=0,capture_v=0,check_v=0,check_write=0;
 reg[3:0]expect_slot=0,check_slot=0;reg[255:0]expect_data=0;wire[287:0]encoded;
 reg[287:0]returned=0;wire valid,error;wire[255:0]repaired_data;
 vm_service_wordbank #(.OWNER_BANK(1)) dut(.*);
 reg[255:0]raw[0:15];reg[287:0]codes[0:15];
 integer errors=0,compared=0;reg want_v=0,want_error=0;reg[255:0]want_data=0;
 reg cur_error;reg[255:0]cur_data;
 task step;
  begin
   @(posedge clk);#0.1;
   if(want_v)begin
    compared=compared+1;
    if(!valid||error!==want_error||(!want_error&&repaired_data!==want_data))begin
     errors=errors+1;if(errors<6)$display("mismatch at%0d error%0b expected%0b",compared,error,want_error);
    end
   end
   want_v=capture_v;want_error=cur_error;want_data=cur_data;
   @(negedge clk);
  end
 endtask
 initial begin
  step();rst_n=1;
  for(integer k=0;k<16;k=k+1)begin
   raw[k]={49'b0,64'(k+91),64'(k+812),64'(k+1992),15'(k+128)};
   expect_v=1;expect_slot=4'(k);expect_data=raw[k];#0.1;codes[k]=encoded;step();
  end
  expect_v=0;
  for(integer n=0;n<4096;n=n+1)begin
   capture_v=1;check_v=(n!=0);check_slot=4'(n);check_write=(n%2==0);
   returned=codes[n%16];cur_data=raw[n%16];cur_error=0;
   if(n%23==0)begin returned[0]=~returned[0];returned[1]=~returned[1];cur_error=1;end
   else if(n%17==0)begin
    cur_data[33]=~cur_data[33];returned[0+:72]=dut.encode64(cur_data[0+:64]);cur_error=1;
   end else if(n%29==0)begin
    cur_data[217]=1;returned[216+:72]=dut.encode64(cur_data[192+:64]);cur_error=1;
   end else if(n%31==0&&check_write)begin
    cur_data[4]=~cur_data[4];returned[0+:72]=dut.encode64(cur_data[0+:64]);cur_error=1;
   end else returned[n%288]=~returned[n%288];
   step();
  end
  capture_v=0;check_v=1;step();check_v=0;step();
  $display("SERVICE_WORDBANK compared=%0d errors=%0d II=1 expected_entries=16",compared,errors);
  if(errors)$fatal(1,"SERVICE_WORDBANK FAIL");$finish;
 end
endmodule
