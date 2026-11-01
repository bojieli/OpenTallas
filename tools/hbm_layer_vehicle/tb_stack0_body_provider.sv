`timescale 1ps/1fs
`default_nettype none
module tb_stack0_body_provider #(parameter integer ND=2,NP=128,NW=1024);
 reg clk=0,rst_n=0;always begin #416 clk=1;#417 clk=0;end
 integer cyc=0,phase=0,got=0,acks=0,read_sent=0,read_got=0,dram_reads=0,mut_epoch=0,words=0,windows=0;
 reg cfg_v=0,desc_v=0,launch_v=0;reg[7:0]cfg_target=0;reg[11:0]cfg_addr=0;reg[255:0]cfg_data=0;
 reg[226:0]moves[0:ND-1];reg[280:0]expected[0:NP-1];reg[31:0]steps[0:ND-1],packet_ends[0:ND-1];reg[19:0]window_info[0:ND-1];
 wire half=window_info[phase][0];wire[3:0]window_col=window_info[phase][4:1];wire[14:0]window_row=window_info[phase][19:5];reg[255:0]bootlo[0:0],boothi[0:0];
 wire cal_v,cal_active,cal_done,cal_fault,cal_configured,cal_target_fault;wire[31:0]cal_ordinal;wire[88:0]cal_payload;
 hfd_hgi_vm_calendar_f20_role #(.W(89))cal(.clk(clk),.clk_cap(clk),.clk_mem(clk),.clk_tgt(clk),.rst_n(rst_n),.tgt(8'd58),
 .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(12'd0),.desc_limit(13'd18),.desc_loops(16'd1),.launch_v(launch_v),
 .tgt_configured(cal_configured),.tgt_fault(cal_target_fault),.calendar_v(cal_v),.active(cal_active),.done(cal_done),.fault(cal_fault),.ordinal(cal_ordinal),.payload(cal_payload));
 wire[31:0]rv,cv,cw,rdv;wire[95:0]rop;wire[159:0]rb,cb,cc;wire[607:0]rr;wire[8191:0]cd,rdd;wire[1023:0]cs;
 wire[15:0]lfv,lfb,hfv,hfb;wire[95:0]lfs,hfs;wire[255:0]lfe,hfe;wire[4095:0]lfd,hfd;
 wire[1:0]refresh_ready,refresh_active,refresh_fault;wire[31:0]pc_fault;wire[7:0]vmks_fault;wire source_fault;
 // These two target straps are fixture-only inputs, not production allocations.
 ot_hbm_static_load_stack0_service #(.TIMING_833(1))source0(.clk(clk),.rst_n(rst_n),.strap_refresh_lo_tgt(8'd127),.strap_refresh_hi_tgt(8'd126),
 .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.lo_calendar_v(cal_v&&half==0),.hi_calendar_v(cal_v&&half==1),.lo_calendar_payload(cal_payload),.hi_calendar_payload(cal_payload),
 .phy0_dram_rvalid(rdv),.phy0_dram_rdata(rdd),.phy0_row_v(rv),.phy0_row_op(rop),.phy0_row_bank(rb),.phy0_row_row(rr),.phy0_col_v(cv),.phy0_col_we(cw),.phy0_col_bank(cb),.phy0_col_col(cc),.phy0_col_data(cd),.phy0_col_strb(cs),
 .lo_fill_v(lfv),.lo_fill_bank(lfb),.lo_fill_slot(lfs),.lo_fill_epoch(lfe),.lo_fill_data(lfd),.hi_fill_v(hfv),.hi_fill_bank(hfb),.hi_fill_slot(hfs),.hi_fill_epoch(hfe),.hi_fill_data(hfd),
 .refresh_ready(refresh_ready),.refresh_active(refresh_active),.refresh_fault(refresh_fault),.pc_fault(pc_fault),.vmks_fault(vmks_fault),.source_fault_o(source_fault));
 ot_hbm3e_phy_rc_e8p5 #(.IMAGE_KEY("stack0"),.REQUIRE_INITIALIZED(1),.CLOCK_PERIOD_PS(833))dram(.clk(clk),.rst_n(rst_n),.row_v(rv),.row_op(rop),.row_bank(rb),.row_row(rr),.col_v(cv),.col_we(cw),.col_bank(cb),.col_col(cc),.col_data(cd),.col_strb(cs),.dram_rvalid(rdv),.dram_rdata(rdd));
 reg load_desc=0,step=0,release_v=0;reg[15:0]epoch=7;
 wire[1:0]active,provider_fault;wire[15:0]ready[0:1];wire[7:0]leaf_fault[0:1];wire[280:0]dq[0:1];
 for(genvar h=0;h<2;h=h+1)begin:PROVIDER
 ot_hbm_static_load_provider_quad #(.SOURCE_STACK(0),.SOURCE_LOW_QUAD(0),.SOURCE_QUAD(h))dut(.clk(clk),.rst_n(rst_n),.desc_v_i(load_desc&&half==h),.desc_i(moves[phase]),.step_i(step&&half==h),
 .window_buffer_i(1'b0),.window_epoch_i(epoch+16'(mut_epoch!=0)),.window_row_i(window_row),.window_col_i(window_col),
 .begin_v(cal_v&&cal_payload[0]&&half==h),.begin_bank(cal_payload[1]),.begin_epoch(cal_payload[17:2]),.begin_row(cal_payload[84:70]),.begin_col(cal_payload[88:85]),
 .fill_v(h==0?lfv:hfv),.fill_bank(h==0?lfb:hfb),.fill_slot(h==0?lfs:hfs),.fill_epoch(h==0?lfe:hfe),.fill_data(h==0?lfd:hfd),
 .release_v_i(release_v&&half==h),.release_buffer_i(1'b0),.release_epoch_i(epoch),.active_o(active[h]),.vm_dq(dq[h]),.block_ready(ready[h]),.leaf_fault(leaf_fault[h]),.fault_o(provider_fault[h]));
 end
 wire[280:0]vm_dq=dq[half];wire[8991:0]bank_dq;wire demux_fault;wire[31:0]native_done;
 wire[17:0]status[0:31];reg[16:0]rq[0:31];wire[256:0]readback[0:31];
 ot_hbm_static_load_vm_dq_demux demux(.packet_i(vm_dq),.bank_dq_o(bank_dq),.fault_o(demux_fault));
 for(genvar b=0;b<32;b=b+1)begin:VM
 hfd_vms_bank_native_q0_faces bank(.rq0(rq[b]),.rr0(readback[b]),.rq1(17'd0),.rr1(),.rq2(17'd0),.rr2(),.rq3(17'd0),.rr3(),.rq4(17'd0),.rr4(),
 .wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.bid(3'(b%8)),.sid(2'(b/8)),
 .clk(clk),.clk_n(clk),.clk_s(clk),.clk_e(clk),.clk_w(clk),.clk_macro0(clk),.clk_macro1(clk),.clk_macro2(clk),.rst_n(rst_n),
 .rslot_v(rq[b][16]),.rslot(3'd0),.wslot_v(bank_dq[b*281+280]),.wslot(3'd6),.dq(bank_dq[b*281+:281]),.dq_done(native_done[b]),
 .kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(status[b]));
 end
 always @(posedge clk)begin
 cyc=cyc+1;
 if(rst_n)begin
 for(integer p=0;p<32;p=p+1)if(cv[p]&&!cw[p])dram_reads=dram_reads+1;
 #1;
 if(source_fault||provider_fault!=0||demux_fault||cal_fault||cal_target_fault)$fatal(1,"S0_PROBE_FAULT cyc%0d phase%0d src%b pc%h vmks%h provider%b leaf%h/%h",cyc,phase,source_fault,pc_fault,vmks_fault,provider_fault,leaf_fault[0],leaf_fault[1]);
 if(vm_dq[280])begin if(got>=NP||vm_dq[279:264]!==expected[got][279:264]||vm_dq[7:0]!==expected[got][7:0])$fatal(1,"S0_PACKET_HEADER got%0d",got);
 for(integer w=0;w<8;w=w+1)if(expected[got][w]&&vm_dq[8+w*32+:32]!==expected[got][8+w*32+:32])$fatal(1,"S0_PACKET_DATA got%0d lane%0d",got,w);words=words+$countones(vm_dq[7:0]);got=got+1;end
 for(integer b=0;b<32;b=b+1)begin
 if(status[b][17]||status[b][16])$fatal(1,"S0_VM_FAULT bank%0d status%h",b,status[b]);
 if(native_done[b])acks=acks+1;
 if(readback[b][256])begin
 if(read_got>=read_sent)$fatal(1,"S0_UNSOLICITED_READBACK");
 for(integer w=0;w<8;w=w+1)if(expected[read_got][w]&&readback[b][w*32+:32]!==expected[read_got][8+w*32+:32])$fatal(1,"S0_READBACK_FAIL index%0d bank%0d lane%0d",read_got,b,w);
 read_got=read_got+1;
 end end
 end end
 task tick;@(negedge clk);endtask
 task write_word(input[11:0]addr,input[255:0]data);begin cfg_addr=addr;cfg_data=data;cfg_v=1;tick();cfg_v=0;tick();end endtask
 reg[255:0]entry;integer waiting,read_bank;
 initial begin
 void'($value$plusargs("MUT_EPOCH=%d",mut_epoch));
 for(integer b=0;b<32;b=b+1)rq[b]=0;
 $readmemh("body_desc.mem",moves);$readmemh("steps.mem",steps);$readmemh("packet_ends.mem",packet_ends);$readmemh("windows.mem",window_info);$readmemh("expected.mem",expected);$readmemh("timing_boot_lo.mem",bootlo);$readmemh("timing_boot_hi.mem",boothi);
 repeat(32)tick();rst_n=1;repeat(16)tick();
 cfg_target=127;write_word(12'h800,bootlo[0]);cfg_target=126;write_word(12'h800,boothi[0]);
 waiting=0;while(refresh_ready!=2'b11)begin tick();waiting=waiting+1;if(waiting>20000)$fatal(1,"S0_BOOT_TIMEOUT ready%b ref%b",refresh_ready,refresh_fault);end
 epoch=6;
 for(phase=0;phase<ND;phase=phase+1)begin
 if(phase==0||window_info[phase]!=window_info[phase-1])begin
 epoch=epoch+1;windows=windows+1;cfg_target=58;
 for(integer ci=0;ci<18;ci=ci+1)begin
 entry=0;entry[255:240]=16'hc7a1;entry[239:224]=16'(ci);
 if(ci==0)begin entry[0]=1;entry[17:2]=epoch;entry[84:70]=window_row;entry[88:85]=window_col;end
 if(ci==16)begin entry[52]=1;entry[69:54]=epoch;entry[84:70]=window_row;entry[88:85]=window_col;end
 write_word(12'(ci),entry);
 end
 repeat(16)tick();desc_v=1;tick();desc_v=0;repeat(40)tick();if(!cal_configured)$fatal(1,"S0_CAL_NOT_CONFIGURED");
 launch_v=1;tick();launch_v=0;repeat(24)tick();
 waiting=0;while((ready[half]&16'h5555)!=16'h5555)begin tick();waiting=waiting+1;if(waiting>20000)$fatal(1,"S0_FILL_TIMEOUT half%0d ready%h",phase,ready[half]);end
 $display("S0_OWNED_FILL half%0d row%0d col%0d cycle%0d RD%0d",half,window_row,window_col,cyc,dram_reads);
 end
 load_desc=1;tick();load_desc=0;step=1;repeat(steps[phase])tick();step=0;repeat(24)tick();
 if(got!=packet_ends[phase]||acks!=got||active[half])$fatal(1,"S0_COMMIT_FAIL half%0d packets%0d acks%0d",phase,got,acks);
 for(integer j=read_sent;j<got;j=j+1)begin
 for(integer b=0;b<32;b=b+1)rq[b]=0;
 read_bank=integer'({expected[j][278:277],expected[j][266:264]});rq[read_bank]={1'b1,expected[j][279:264]};read_sent=read_sent+1;tick();
 end
 for(integer b=0;b<32;b=b+1)rq[b]=0;
 repeat(16)tick();if(read_got!=read_sent)$fatal(1,"S0_READBACK_DRAIN");
 if(phase==ND-1||window_info[phase+1]!=window_info[phase])begin release_v=1;tick();release_v=0;repeat(24)tick();end
 end
 if(mut_epoch!=0)$fatal(1,"S0_MUTANT_ESCAPED");
 if(got!=NP||words!=NW||acks!=NP||read_got!=NP)$fatal(1,"S0_CONSERVATION_FAIL");
 $display("S0_BODY_PROVIDER PASS descriptors=%0d source_stack=0 windows=%0d packets=%0d words=%0d nativeACK=%0d SRAMreadback=%0d DRAMread=%0d clock_ps=833 externalRL=29",ND,windows,got,words,acks,read_got,dram_reads);$finish;
 end
endmodule
`default_nettype wire
