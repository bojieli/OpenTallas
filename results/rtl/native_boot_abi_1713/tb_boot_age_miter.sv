`timescale 1ns/1ps
module tb;
 reg ck=0;always #5 ck=~ck;reg rst_n=0;reg[142:0]pr=0;reg ready=0;reg[63:0]words[0:95];integer i;
 wire[1:0]fault,cfgwe,sealed,cfgfault;wire[7:0]code[0:1],addr[0:1];wire[63:0]data[0:1];wire[31:0]att[0:1];wire[15:0]pv[0:1];wire[255:0]vp[0:1];
 genvar g;generate for(g=0;g<2;g=g+1)begin:G
 qkd_static_kv_boot_dispatch_mu_nc32 #(.MU(1),.DIECFG(1),.NRST(43),.DIECAP(1),.AGES(g),.SRQ(2),.DSTG(1)) dut(.ck(ck),.rst_n(rst_n),.boot_pr(pr),.boot_image_target(4'd10),.boot_image_ready(ready),.boot_image_fault(1'b0),.boot_image_epoch(16'h0b0b),.boot_image_digest(64'h0),.execution_active(1'b0),.sink_applied({160{1'b1}}),.local_configured(3'b111),.sink_fault(1'b0),.diecfg_sealed(sealed[g]),.diecfg_fault(cfgfault[g]),.diecfg_we(cfgwe[g]),.diecfg_addr(addr[g]),.diecfg_data(data[g]),.fault(fault[g]),.fault_code(code[g]));
 qkd_kv_die_cfg_a_c32 #(.NRST(43),.CAP(1),.AGES(1)) cfg(.ck(ck),.por_n(rst_n),.cfg_we(cfgwe[g]),.cfg_addr(addr[g]),.cfg_data(data[g]),.sealed(sealed[g]),.fault(cfgfault[g]),.age_attn(att[g]),.age_pv(pv[g]),.age_vport(vp[g]));
 end endgenerate
 wire lf,lw;wire[7:0]lc,la;wire[63:0]ld;
 qkd_static_kv_boot_dispatch_mu_nc32_legacy #(.MU(1),.DIECFG(1),.NRST(43),.DIECAP(1),.SRQ(2),.DSTG(1)) legacy(.ck(ck),.rst_n(rst_n),.boot_pr(pr),.boot_image_target(4'd10),.boot_image_ready(ready),.boot_image_fault(1'b0),.boot_image_epoch(16'h0b0b),.boot_image_digest(64'h0),.execution_active(1'b0),.sink_applied({160{1'b1}}),.local_configured(3'b111),.sink_fault(1'b0),.diecfg_sealed(sealed[0]),.diecfg_fault(cfgfault[0]),.diecfg_we(lw),.diecfg_addr(la),.diecfg_data(ld),.fault(lf),.fault_code(lc));
 always@(negedge ck)if(rst_n && {lf,lc,lw,la,ld} !== {fault[0],code[0],cfgwe[0],addr[0],data[0]})$fatal(1,"DEFAULT_AGES0_LOCKSTEP_MISMATCH");
 initial begin
 $readmemh("target10.hex",words);repeat(5)@(negedge ck);rst_n=1;repeat(12)@(negedge ck);
 for(i=0;i<96;i=i+1)begin pr=0;pr[74]=1;pr[73:64]=10'(i);pr[63:0]=words[i];@(negedge ck);end
 pr=0;repeat(12)@(negedge ck);ready=1;repeat(6)@(negedge ck);
 $display("OLD_COUNT77 fault=%b code=%h sealed=%b",fault[0],code[0],sealed[0]);
 $display("NATIVE_AGES96 fault=%b code=%h sealed=%b cfgfault=%b att=%h pv=%h",fault[1],code[1],sealed[1],cfgfault[1],att[1],pv[1]);
 if(!fault[0]||sealed[0])$fatal(1,"OLD_COUNT_MUTANT_ESCAPED");
 if(fault[1]||!sealed[1]||cfgfault[1]||att[1]!==words[76][31:0]||pv[1]!=={words[78][7:0],words[77][7:0]})$fatal(1,"NATIVE_CONFIG_NOT_INSTALLED");
 for(i=0;i<16;i=i+1)if(vp[1][16*i+:16]!==words[79+i][15:0])$fatal(1,"VPORT_AGE_MISMATCH");
 $display("DEFAULT_AGES0_LOCKSTEP_PASS");$display("ACTUAL_DISPATCH_DCFG_AGES96_PASS");$finish;
 end
endmodule
