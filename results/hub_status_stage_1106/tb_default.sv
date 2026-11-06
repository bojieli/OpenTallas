module tb_default;
reg clk=0,rst_n=0;reg [143:0]bank_status=0;reg[2:0]hub_status=0;reg ring_fault=0,ring_fault_late=0;
wire[18:0]r0,r2,e0,e2,o0,o2,n0,n2;
status_reference #(.DMUT(0)) ref0(.*,.vmstat(r0));
status_reference #(.DMUT(2)) ref2(.*,.vmstat(r2));
status_enabled_reference #(.DMUT(0)) oldon0(.*,.vmstat(e0));
status_enabled_reference #(.DMUT(2)) oldon2(.*,.vmstat(e2));
ot_vms_status_static_pc #(.DMUT(0)) off0(.*,.vmstat(o0));
ot_vms_status_static_pc #(.DMUT(2)) off2(.*,.vmstat(o2));
ot_vms_status_static_pc #(.DMUT(0),.STATUS_INPUT_STAGE(1)) on0(.*,.vmstat(n0));
ot_vms_status_static_pc #(.DMUT(2),.STATUS_INPUT_STAGE(1)) on2(.*,.vmstat(n2));
integer checks=0,errors=0;
task step;begin clk=0;#2;clk=1;#2;checks+=4;
 if(o0!==r0 || o2!==r2 || n0!==e0 || n2!==e2)errors++;
end endtask
integer episode,k,b;
initial begin
 if($bits(off0.sum_valid)!=2 || $bits(on0.sum_valid)!=3)$fatal(1,"conditional warmup width wrong");
 for(episode=0;episode<4;episode++)begin
  clk=0;rst_n=0;#2;step();rst_n=1;
  for(k=0;k<16;k++)begin
   for(b=0;b<8;b++)begin bank_status[b*18+:16]=(k%4==0)?16'hffff:16'(17*k+13*b+episode);bank_status[b*18+16+:2]=(k%4<2)?0:2'(b+k);end
   hub_status=(k%4<2)?0:3'(k);ring_fault=(k%4<2)?0:k[1];ring_fault_late=k[0];step();
  end
 end
 $display("DEFAULT0_RELEASE_EQ_AND_ENABLED1_D818_EQ checks=%0d errors=%0d default_warmup_bits=2 enabled_warmup_bits=3",checks,errors);
 if(errors)$fatal(1,"conditional status relation failed");$finish;
end
endmodule
