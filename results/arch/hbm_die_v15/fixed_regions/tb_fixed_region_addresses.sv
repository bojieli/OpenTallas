module tb;
reg[36:0]a;wire[1:0]st;wire[4:0]pc;wire[29:0]sec;wire valid;
reg[37:0]v[0:33082-1];integer i;reg[29:0]expected_s;
ot_hbm_loader_kport_address #(.ENABLE(1))u(.byte_address(a),.stack_bytes(36'd22500000000),.stack(st),.pc(pc),.sector_address(sec),.valid(valid));
initial begin $readmemh("/home/ubuntu/wt/hbm-die-feas-1014/results/arch/hbm_die_v15/fixed_regions/address_vectors.hex",v);for(i=0;i<33082;i=i+1)begin
 a=v[i][36:0];#1;expected_s=a[34:5];
 if(valid!==v[i][37]||st!==a[36:35]||sec!==expected_s||pc!==(expected_s[6:2]^expected_s[11:7]^expected_s[16:12]))$fatal(1,"address vector %0d",i);
 end $display("FIXED_REGION_ADDRESS_PASS vectors=%0d",33082);$finish;end
endmodule
