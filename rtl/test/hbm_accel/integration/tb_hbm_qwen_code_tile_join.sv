`timescale 1ps/1fs
module tb_hbm_qwen_code_tile_join;
 import ot_hbm_r14_pkg::*;
 reg sc=0,cc=0,por=0;always #512 sc=~sc;always #416.666 cc=~cc;
 reg sv=0,published=0;wire rv;owned_t o;identity_t expected;
 wire[23:0] addr;reg[23:0] base=0;reg[1:0] kind=2;
 wire sr,ready,fault,empty;wire[1:0] rsp;wire[2659:0] rom;wire[1:0] accepted,tile_rsp;wire[511:0] data;wire[2:0] bank;
 reg[255:0] payload[0:1023];string image;integer w,p;integer edges=0;
 always @(posedge cc)edges<=edges+1;
 ot_hbm_qwen_code_pair_join #(.ENABLE(1),.NSEG(1),.READ_ALIGN(2)) dut(
 .service_clk(sc),.core_clk(cc),.por_n(por),.service_v(sv),.service_r(sr),.service_owned(o),
 .installed(1'b1),.span_stack(2'd3),.first_sector(34'h20000000),.span_rows(14'd512),.first_row(13'd100),
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
 reg[127:0] xl=0;reg[2047:0] kv=0;
 wire[511:0] nt,ot;wire nv,ov, nf,of;
 wire[4:0] nce,oce;wire[11:0] na,oa;wire nkre,okre;
 wire[95:0] nkaddr,okaddr;
 reg[2659:0] original_rom=0;
 reg[511:0] original_result;
 integer issues=0,results=0,run_length=0,continuous_max=0,tag_checks=0,x_checks=0,kv_checks=0;
 function automatic[378:0] instruction(input bit kvop);
 instruction={18'd128,18'd1,18'd4,kvop,24'd0,24'd0,24'd8,24'd1,
  24'd0,24'd1,24'd0,24'd1,3'd0,4'd7,24'd0,1'b0,24'd0,24'd0,24'd1,
  1'b0,1'b1,1'b0,1'b0,24'd0};
 endfunction
 ot_qwen_hbm_code_tile_logic_w12 #(.ENABLE(1),.CODE_BANKS(5),.KV_LOCAL(0),.SMIN(7),.MEM_EXTRA(EXTRA)) newtile(
 .clk(cc),.rst_n(por),.tile_id(16'd0),.ib_go(ib_go),.ib(ib),.xl(xl),
 .t_out(nt),.t_vout(nv),.n_a(512'b0),.n_b(512'b0),.n_va(1'b0),.n_y(),.n_vy(),.fault(nf),
 .rom_ce(nce),.rom_addr(na),.rom_rd(rom),.kvs_r_ce(),.kvs_r_addr(),.kvs_rd(512'b0),
 .kv_re(nkre),.kv_addr(nkaddr),.kv_q(kv),
 .code_span_retained(published),.code_storage_fault(fault),.code_read_accepted(accepted),
 .code_response_valid(tile_rsp),.code_read_request(rv),.code_virtual_address(addr));
 ot_qwen_rom_tile_logic_w12 #(.CODE_BANKS(5),.KV_LOCAL(0),.SMIN(7),.MEM_EXTRA(EXTRA)) reference(
 .clk(cc),.rst_n(por),.tile_id(16'd0),.ib_go(ib_go),.ib(ib),.xl(xl),
 .t_out(ot),.t_vout(ov),.n_a(512'b0),.n_b(512'b0),.n_va(1'b0),.n_y(),.n_vy(),.fault(of),
 .rom_ce(oce),.rom_addr(oa),.rom_rd(original_rom),.kvs_r_ce(),.kvs_r_addr(),.kvs_rd(512'b0),
 .kv_re(okre),.kv_addr(okaddr),.kv_q(kv));
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
 always @(negedge cc)if(por)begin
  for(integer g=0;g<4;g=g+1)xl[g*32+:32]=32'h3f800000+32'(edges+g);
  // Actual C+1 external memory-port response stimuli, changing every clock.
  for(integer g=0;g<64;g=g+1)kv[g*32+:32]=32'h3f000000+32'(edges+g);
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
   if(nv)begin if(nt!==old_result_data)$fatal(1,"actual arithmetic differs from original");if(!kv_phase)results=results+1;end
  end else #2;
  old_v=reference.u_me.m_v;old_tag=reference.u_me.m_tag;old_gm=reference.u_me.m_gm;
  old_round=reference.u_me.m_t;old_first=reference.u_me.m_first;
  old_wsrc=reference.u_me.m_wsrc;old_rnd=reference.u_me.m_round;
  old_x=reference.u_me.mq_x;old_kv=reference.u_me.mq_kv;old_code=reference.u_me.mq_wrom;
  old_result_v=ov;old_result_data=ot;
 end
 initial begin
 if(!$value$plusargs("payload=%s",image))$fatal(1,"actual source payload required");
 $readmemh(image,payload);o='0;expected='0;repeat(3)cedge();por=1;
 // No physical SRAM preload: all 1024 sectors travel through the real CDC.
 for(w=0;w<1024;w=w+1)transfer(w);
 while(!empty)cedge();
 @(negedge cc);published=1;ib_go=1;ib=instruction(0);
 cedge();@(negedge cc);ib_go=0;
 wait(reference.u_me.active_o==1);
 wait(reference.u_me.active_o==0);
 wait(newtile.on.u_me.m_v==0);
 repeat(80)cedge();
 if(issues!=32||results!=32||continuous_max!=32)$fatal(1,"actual tile issue/result counts %0d %0d %0d",issues,results,continuous_max);
 // A separate actual external KV response-port alignment control, not a
 // released KV numerical qualification or claim of installed KV SRAM.
 @(negedge cc);kv_phase=1;ib_go=1;ib=instruction(1);
 cedge();@(negedge cc);ib_go=0;
 wait(reference.u_me.active_o==1);wait(reference.u_me.active_o==0);
 repeat(80)cedge();
 if(kv_checks==0||tag_checks<32||x_checks<32)$fatal(1,"no meaningful operand/tag coverage");
 if(fault||nf||of)$fatal(1,"join/real engine fault");
 // A real mismatched leaf response must quarantine the same pipeline.
 force dut.read_response_valid=2'b11;#2;
 if(!fault||tile_rsp!=0)$fatal(1,"extra response not quarantined");
 cedge();release dut.read_response_valid;cedge();
 if(!fault)$fatal(1,"response fault was not retained");
 $display("PASS_CODE_REAL_TILE continuous_issues=%0d continuous_max=%0d code_results=%0d tags=%0d x=%0d kv_port_control=%0d extra_edges=1 MEM_EXTRA=%0d arithmetic_reference=pinned_original_tile fulltoken=0",issues,continuous_max,results,tag_checks,x_checks,kv_checks,EXTRA);
 $finish;
 end
endmodule
