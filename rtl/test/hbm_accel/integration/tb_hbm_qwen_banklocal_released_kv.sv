`timescale 1ps/1fs
module tb_hbm_qwen_banklocal_released_kv;
 import ot_hbm_r14_pkg::*;
 reg sc=0,cc=0,por=0;always #512 sc=~sc;always #416.666 cc=~cc;
 reg sv=0,published=0;wire rv;owned_t o;identity_t expected;
 wire[23:0] addr;reg[23:0] base=0;reg[1:0] kind=2;
 wire sr,ready,fault,empty;wire[1:0] rsp;wire[2659:0] rom;wire[1:0] accepted,tile_rsp;wire[511:0] data;wire[2:0] bank;
 reg[255:0] payload[0:1023];string image;integer w,p;integer edges=0;
 always @(posedge cc)edges<=edges+1;
 ot_hbm_qwen_code_pair_join_banklocal #(.ENABLE(1),.NSEG(1),.READ_ALIGN(2)) dut(
 .service_clk(sc),.core_clk(cc),.por_n(por),.service_v(sv),.service_r(sr),.service_owned(o),
 .installed(1'b1),.span_stack(2'd3),.first_sector(34'h20000000),.span_rows(14'd512),.first_row(13'd3980),
 .operation(64'd77),.phase(32'd9),.rank(7'd0),.hardware_owner_valid(1'b1),.expected_identity(expected),
 .seg_base(base),.seg_len(24'd512),.seg_sidx(32'd0),.seg_kind(kind),.installed_segment(3'd0),
 .installed_base(base),.installed_length(24'd512),.installed_sidx(32'd0),.installed_kind(kind),.published(published),
 .read_v(rv),.read_accepted(accepted),.virtual_address(addr),.read_ready(ready),.read_response_valid(rsp),.read_data(data),.read_bank(bank),
 .consumer_enable(1'b1),.response_ready(2'b11),.rom_rd(rom),.tile_response_valid(tile_rsp),.fault(fault),.crossing_empty(empty));
 task cedge;begin @(posedge cc);#1;end endtask
 task transfer(input integer n);
 begin
 @(negedge sc);o='0;o.id.stack=3;o.id.sector=34'h20000000+n;
 o.id.producer=64'h12345678;o.id.transport=9;o.id.caller=16'h8123;
 o.id.client=16;o.id.irs_serial=n+1;o.physical_tag=12'(n);o.beat=5'(n%16);
 o.data=payload[n];expected=o.id;sv=1;
 @(posedge sc);while(!sr)begin @(posedge sc);if(fault)$fatal(1,"delivery fault n=%0d",n);end
 @(negedge sc);sv=0;@(posedge sc);#1;
 end endtask
 parameter integer EXTRA=0;
 reg kv_phase=0;reg ib_go=0;reg[378:0] ib=0;
 reg[127:0] xl=0;
 wire kread;wire[6:0] krow;wire[511:0] kvdata;
 wire rread;wire[6:0] rrow;reg[511:0] reference_kv=0;
 reg[511:0] reference_rows[0:1];
 reg[255:0] prior[0:3];reg[31:0] operands[0:1023];
 string priorfile,operandfile,outfile;integer outfd;
 reg kv_source_v=0;owned_t ko;identity_t kid;wire kv_source_r,kfault,kempty,kcomm;
 integer kv_returns=0,kv_results=0,nonzero_results=0;
 ot_hbm_qwen_kv_tile_landing #(.ENABLE(1)) kvlanding(
 .service_clk(sc),.core_clk(cc),.por_n(por),.service_v(kv_source_v),.service_r(kv_source_r),
 .service_owned(ko),.retained_prior_owner(1'b1),.expected_identity(kid),
 .rd_v(kread),.rd_row(krow),.rd_data(kvdata),.private_committed(kcomm),
 .crossing_empty(kempty),.fault(kfault));
 task kv_transfer(input integer n);
 integer sector;
 begin
 sector=(n>=2?32768:0)+(n%2);
 @(negedge sc);ko='0;ko.id.sector=34'(sector);ko.id.stack=2'(sector%4);
 ko.id.producer=64'h4c305f5038313931;ko.id.transport=32'd11;ko.id.caller=16'hb101;
 ko.id.client=17;ko.id.irs_serial=n+1;ko.physical_tag=12'(n+32);ko.beat=5'(n);
 ko.data=prior[n];kid=ko.id;kv_source_v=1;
 @(posedge sc);while(!kv_source_r)begin @(posedge sc);if(kfault)$fatal(1,"KV landing fault");end
 kv_returns=kv_returns+1;
 @(negedge sc);kv_source_v=0;@(posedge sc);#1;
 end endtask
 wire[511:0] nt,ot;wire nv,ov, nf,of;
 wire[4:0] nce,oce;wire[11:0] na,oa;wire nkre,okre;
 wire[95:0] nkaddr,okaddr;
 reg[2659:0] original_rom=0;
 reg[511:0] original_result;
 integer issues=0,results=0,run_length=0,continuous_max=0,tag_checks=0,x_checks=0,kv_checks=0;
 function automatic[378:0] instruction(input bit kvop);
 instruction={18'd128,18'd1,(kvop?18'd128:18'd4),kvop,(kvop?24'd0:24'd96),(kvop?24'd128:24'd0),(kvop?24'd128:24'd8),(kvop?24'd65536:24'd1),
  24'd0,(kvop?24'd128:24'd1),(kvop?24'd128:24'd0),24'd1,(kvop?3'd2:3'd0),4'd7,(kvop?24'd1:24'd0),1'b0,24'd0,24'd0,24'd1,
  1'b0,1'b1,1'b0,1'b0,24'd0};
 endfunction
 ot_qwen_hbm_code_tile_logic_w12 #(.ENABLE(1),.CODE_BANKS(5),.KV_LOCAL(1),.KV_VB(131072),.KV_NH(2),.SMIN(7),.MEM_EXTRA(EXTRA)) newtile(
 .clk(cc),.rst_n(por),.tile_id(16'd0),.ib_go(ib_go),.ib(ib),.xl(xl),
 .t_out(nt),.t_vout(nv),.n_a(512'b0),.n_b(512'b0),.n_va(1'b0),.n_y(),.n_vy(),.fault(nf),
 .rom_ce(nce),.rom_addr(na),.rom_rd(rom),.kvs_r_ce(kread),.kvs_r_addr(krow),.kvs_rd(kvdata),
 .kv_re(nkre),.kv_addr(nkaddr),.kv_q(2048'b0),
 .code_span_retained(published),.code_storage_fault(fault),.code_read_accepted(accepted),
 .code_response_valid(tile_rsp),.code_read_request(rv),.code_virtual_address(addr));
 ot_qwen_rom_tile_logic_w12 #(.CODE_BANKS(5),.KV_LOCAL(1),.KV_VB(131072),.KV_NH(2),.SMIN(7),.MEM_EXTRA(EXTRA)) reference(
 .clk(cc),.rst_n(por),.tile_id(16'd0),.ib_go(ib_go),.ib(ib),.xl(xl),
 .t_out(ot),.t_vout(ov),.n_a(512'b0),.n_b(512'b0),.n_va(1'b0),.n_y(),.n_vy(),.fault(of),
 .rom_ce(oce),.rom_addr(oa),.rom_rd(original_rom),.kvs_r_ce(rread),.kvs_r_addr(rrow),.kvs_rd(reference_kv),
 .kv_re(okre),.kv_addr(okaddr),.kv_q(2048'b0));
 // Reference ONLY has the original C+1 macro contract. DUT SRAM can be
 // populated exclusively by returned owned payload through actual CDC.
 always @(posedge cc) if(por)begin
  for(integer b=0;b<5;b=b+1)if(oce[b])begin
   original_rom[b*266+:266]<={10'b0,payload[oa*2]};
   original_rom[(5+b)*266+:266]<={10'b0,payload[oa*2+1]};
  end
 end
 reg[166:0] old_tag;reg[3:0] old_gm;reg[17:0] old_round;
 reg old_v,old_first,old_wsrc,old_rnd;
 reg[127:0] old_x;reg[2047:0] old_kv;reg[511:0] old_code;
 reg old_result_v=0;reg[511:0] old_result_data;
 // DUT operand is saved ACTUAL native producer output, never expected Q/K.
 // Diagnostic partialK uses real native X source; canonical QR is not captured.
 always @(negedge cc)if(por)begin
  for(integer g=0;g<4;g=g+1)begin
   if(reference.u_me.x_addr[g*24+:24]<1024)
    xl[g*32+:32]=operands[reference.u_me.x_addr[g*24+:24]];
   else if(reference.u_me.x_re[g])$fatal(1,"native operand source aperture");
  end
 end
 // Comparator ONLY has original C+1 SRAM contract with SAME accepted bytes.
 always @(posedge cc)if(por&&rread)begin
  if(rrow>=2)$fatal(1,"reference row outside two accepted prior heads");
  reference_kv<=reference_rows[rrow];
 end
 always @(posedge cc)begin
  if(por&&published)begin
   if(rv)begin issues=issues+1;run_length=run_length+1;if(run_length>continuous_max)continuous_max=run_length;end
   else run_length=0;
   #2;
   if(newtile.on.u_me.m_v!==old_v)$fatal(1,"tag valid edge misalignment");
   if(old_v)begin
    if(newtile.on.u_me.m_tag!==old_tag||newtile.on.u_me.m_gm!==old_gm||
       newtile.on.u_me.m_t!==old_round||newtile.on.u_me.m_first!==old_first||
       newtile.on.u_me.m_wsrc!==old_wsrc||newtile.on.u_me.m_round!==old_rnd)
      $fatal(1,"tag/round/gm/first/wsrc mismatch");
    tag_checks=tag_checks+1;
   end
   if(newtile.on.u_me.s1_v)begin
    if(newtile.on.u_me.mq_x!==old_x)$fatal(1,"X extra-edge mismatch");x_checks=x_checks+1;
    if(newtile.on.u_me.s1_wsrc)begin
     if(newtile.on.u_me.mq_kv!==old_kv)$fatal(1,"KV extra-edge mismatch");kv_checks=kv_checks+1;
    end else if(newtile.on.u_me.mq_wrom!==old_code)$fatal(1,"CODE extra-edge mismatch");
   end
   if(nv!==old_result_v)$fatal(1,"result valid timing");
   if(nv)begin if(nt!==old_result_data)$fatal(1,"actual arithmetic differs from original");if(!kv_phase)results=results+1;
    else begin kv_results=kv_results+1;if(nt!=0)nonzero_results=nonzero_results+1;$fdisplay(outfd,"%0128h",nt);endend
  end else #2;
  old_v=reference.u_me.m_v;old_tag=reference.u_me.m_tag;old_gm=reference.u_me.m_gm;
  old_round=reference.u_me.m_t;old_first=reference.u_me.m_first;
  old_wsrc=reference.u_me.m_wsrc;old_rnd=reference.u_me.m_round;
  old_x=reference.u_me.mq_x;old_kv=reference.u_me.mq_kv;old_code=reference.u_me.mq_wrom;
  old_result_v=ov;old_result_data=ot;
 end
 initial begin
 if(!$value$plusargs("payload=%s",image))$fatal(1,"actual source payload required");
 if(!$value$plusargs("prior=%s",priorfile)||!$value$plusargs("operand=%s",operandfile)||!$value$plusargs("out=%s",outfile))$fatal(1,"retained source paths required");
 $readmemh(priorfile,prior);$readmemh(operandfile,operands);
 reference_rows[0]={prior[1],prior[0]};reference_rows[1]={prior[3],prior[2]};
 outfd=$fopen(outfile,"w");if(!outfd)$fatal(1,"output open");
 ko='0;kid='0;
 $readmemh(image,payload);o='0;expected='0;repeat(3)cedge();por=1;
 // No physical SRAM preload: all 1024 sectors travel through the real CDC.
 for(w=0;w<1024;w=w+1)transfer(w);
 while(!empty)cedge();
 for(integer n=0;n<4;n=n+1)kv_transfer(n);
 while(!kempty)cedge();if(kv_returns!=4||kfault)$fatal(1,"missing actual KV returns");
 @(negedge cc);published=1;ib_go=1;ib=instruction(0);
 cedge();@(negedge cc);ib_go=0;
 wait(reference.u_me.active_o==1);
 wait(reference.u_me.active_o==0);
 wait(newtile.on.u_me.m_v==0);
 repeat(80)cedge();
 if(issues!=32||results!=32||continuous_max!=32)$fatal(1,"actual tile issue/result counts %0d %0d %0d",issues,results,continuous_max);
 // SAME actual native tile consumes retained prior K via real landing/SRAM.
 // Diagnostic partial arithmetic, not full canonical attention query.
 @(negedge cc);kv_phase=1;ib_go=1;ib=instruction(1);
 cedge();@(negedge cc);ib_go=0;
 wait(reference.u_me.active_o==1);wait(reference.u_me.active_o==0);
 repeat(80)cedge();
 if(kv_checks==0||tag_checks<32||x_checks<32)$fatal(1,"no meaningful operand/tag coverage");
 if(kv_results!=8||nonzero_results==0)$fatal(1,"missing/nonmeaningful released KV numeric results");
 if(fault||nf||of||kfault)$fatal(1,"join/real engine fault");
 // A real mismatched leaf response must quarantine the same pipeline.
 force dut.read_response_valid=2'b11;#2;
 if(!fault||tile_rsp!=0)$fatal(1,"extra response not quarantined");
 cedge();release dut.read_response_valid;cedge();
 if(!fault)$fatal(1,"response fault was not retained");
 $display("PASS_BANKLOCAL_CODE_RELEASED_PRIOR_KV_TILE continuous_issues=%0d continuous_max=%0d code_results=%0d tags=%0d x=%0d kv_consumed_issues=%0d extra_edges=1 MEM_EXTRA=%0d arithmetic_reference=pinned_original_tile actual_K_sectors=4 kv_outputs=8x16 canonical_query=0 currentKV=0 fulltoken=0",issues,continuous_max,results,tag_checks,x_checks,kv_checks,EXTRA);
 $fclose(outfd);$finish;
 end
endmodule
