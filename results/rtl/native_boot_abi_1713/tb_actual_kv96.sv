`timescale 1ps/1fs
module tb;
 reg ck=0; always #416.5 ck=~ck;
 reg rst_n=0,ready=0; reg[142:0] pr[0:2]; reg[63:0] words[0:95]; integer i,cyc=0;
 wire[2:0] fault,cfgwe,sealed,cfgfault; wire[7:0] code[0:2],addr[0:2]; wire[63:0] data[0:2];
 wire[31:0] att[0:2]; wire[15:0] pv[0:2]; wire[255:0] vp[0:2];
 integer seal_edge[0:2]; integer writes[0:2];
 genvar g; generate for(g=0;g<3;g=g+1) begin:G
 qkd_static_kv_boot_dispatch_mu_nc32 #(.MUT(0),.DIECFG(1),.NRST(43),.LINKCFG(1),.ESCFG(1),.DIECAP(1),.AGES(g==1),.MU(1),.WMUT(0),.SRQ(2),.DSTG(1)) dut(
 .ck(ck),.rst_n(rst_n),.boot_pr(pr[g]),.boot_image_target(4'd10),.boot_image_ready(ready),.boot_image_fault(1'b0),.boot_image_epoch(16'h0b0b),.boot_image_digest(64'h0),.execution_active(1'b0),.sink_applied({160{1'b1}}),.local_configured(3'b111),.sink_fault(1'b0),.diecfg_sealed(sealed[g]),.diecfg_fault(cfgfault[g]),.diecfg_we(cfgwe[g]),.diecfg_addr(addr[g]),.diecfg_data(data[g]),.fault(fault[g]),.fault_code(code[g]));
 qkd_kv_die_cfg_a_c32 #(.NRST(43),.CAP(1),.AGES(g!=2),.MUT(0)) cfg(
 .ck(ck),.por_n(rst_n),.cfg_we(cfgwe[g]),.cfg_addr(addr[g]),.cfg_data(data[g]),.sealed(sealed[g]),.fault(cfgfault[g]),.age_attn(att[g]),.age_pv(pv[g]),.age_vport(vp[g]));
 end endgenerate
 wire lf,lw; wire[7:0] lc,la; wire[63:0] ld;
 qkd_static_kv_boot_dispatch_mu_nc32_legacy #(.MUT(0),.DIECFG(1),.NRST(43),.LINKCFG(1),.ESCFG(1),.DIECAP(1),.MU(1),.WMUT(0),.SRQ(2),.DSTG(1)) legacy(
 .ck(ck),.rst_n(rst_n),.boot_pr(pr[2]),.boot_image_target(4'd10),.boot_image_ready(ready),.boot_image_fault(1'b0),.boot_image_epoch(16'h0b0b),.boot_image_digest(64'h0),.execution_active(1'b0),.sink_applied({160{1'b1}}),.local_configured(3'b111),.sink_fault(1'b0),.diecfg_sealed(sealed[2]),.diecfg_fault(cfgfault[2]),.diecfg_we(lw),.diecfg_addr(la),.diecfg_data(ld),.fault(lf),.fault_code(lc));
 always @(negedge ck) begin
 #1;
 if(rst_n) begin
 cyc=cyc+1;
 if({lf,lc,lw,la,ld} !== {fault[2],code[2],cfgwe[2],addr[2],data[2]}) $fatal(1,"DEFAULT_AGES0_LOCKSTEP_MISMATCH");
 for(integer k=0;k<3;k=k+1) begin
 if(cfgwe[k]) writes[k]=writes[k]+1;
 if(sealed[k] && seal_edge[k]<0) seal_edge[k]=cyc;
 end
 end
 end
 initial begin
 for(i=0;i<3;i=i+1)begin pr[i]=0; seal_edge[i]=-1; writes[i]=0;end
 $readmemh("target10.hex",words); repeat(5)@(negedge ck); #2;rst_n=1;
 repeat(12)@(negedge ck);
 for(i=0;i<96;i=i+1)begin
 #2;
 pr[0]=0;pr[0][74]=1;pr[0][73:64]=10'(i);pr[0][63:0]=words[i];pr[1]=pr[0];
 pr[2]=0;if(i<77)begin pr[2][74]=1;pr[2][73:64]=10'(i);pr[2][63:0]=(i==76)?words[95]:words[i];end
 @(negedge ck);
 end
 #2;for(i=0;i<3;i=i+1)pr[i]=0;
 repeat(12)@(negedge ck);#2;ready=1;repeat(6)@(negedge ck);#2;
 if(!fault[0]||sealed[0])$fatal(1,"OLD77_MISMATCH_NEGATIVE_ESCAPED");
 if(fault[1]||!sealed[1]||cfgfault[1]||att[1]!==words[76][31:0]||pv[1]!=={words[78][7:0],words[77][7:0]})$fatal(1,"NATIVE96_CONFIG_NOT_INSTALLED");
 for(i=0;i<16;i=i+1)if(vp[1][16*i+:16]!==words[79+i][15:0])$fatal(1,"VPORT_AGE_MISMATCH");
 if(fault[2]||!sealed[2]||cfgfault[2])$fatal(1,"PROPER77_AGES0_NOT_SEALED");
 if(writes[1]!=96||writes[2]!=77||seal_edge[1]-seal_edge[2]!=19)$fatal(1,"CONFIG_CYCLE_PRICE writes=%0d/%0d seal=%0d/%0d",writes[1],writes[2],seal_edge[1],seal_edge[2]);
 $display("PASS ACTUAL_PARENT_PARAMS NATIVE96 OLD77_NEGATIVE DEFAULT_AGES0_LOCKSTEP cfg_words=%0d/%0d seal_edges=%0d/%0d delta=%0d word_cycles clock_ps=833",writes[1],writes[2],seal_edge[1],seal_edge[2],seal_edge[1]-seal_edge[2]);
 $finish;
 end
endmodule
