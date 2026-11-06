#!/usr/bin/env python3
"""Add default-off native HOST programming to the pinned native-KS S81 bench."""
from pathlib import Path
import argparse
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('input',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args();s=a.input.read_text()
def one(old,new):
 global s
 if s.count(old)!=1:raise SystemExit('unsupported native-KS TB: '+old[:80])
 s=s.replace(old,new,1)
one('bit native_ks_link = 0;', 'bit native_ks_link = 0; bit native_host_link = 0;')
one('initial native_ks_link = $test$plusargs("NATIVE_KS_LINK");','initial begin native_host_link=$test$plusargs("NATIVE_HOST_LINK"); native_ks_link=$test$plusargs("NATIVE_KS_LINK")||$test$plusargs("NATIVE_HOST_LINK"); end')
one('wire native_ks_queued,native_ks_accepted; wire [5:0] native_ks_fault;','''wire native_ks_queued,native_ks_accepted; wire [5:0] native_old_ks_fault;
  reg native_host_send=0;reg[514:0]native_host_word=0;
  wire native_host_ready,native_host_accepted,native_host_ks_accepted;
  wire[543:0]native_host_pma0,native_host_pma1;
  wire[76:0]native_remote_status;wire native_remote_valid;
  wire[6:0]native_host_fault;
  wire[6:0]native_ks_fault=native_host_link?native_host_fault:{1'b0,native_old_ks_fault};''')
one('.rst_n(rst_n && native_ks_link)', '.rst_n(rst_n && native_ks_link && !native_host_link)')
one('.fault(native_ks_fault));', '''.fault(native_old_ks_fault));
  ot_tb_s81_native_host_peer native_host_peer(.clk(clk),.rst_n(rst_n&&native_host_link),
    .host_send(native_host_send),.host_word(native_host_word),.host_ready(native_host_ready),.host_accepted(native_host_accepted),
    .ks_send(native_ks_send),.ks_word(native_ks_word),.ks_accepted(native_host_ks_accepted),
    .pma_from_die0(lk_EN0_pma_tx),.pma_from_die1(lk_EN1_pma_tx),
    .pma_die_tck0(lk_EN0_pma_tck[0]),.pma_die_tck1(lk_EN1_pma_tck[0]),
    .pma_to_die0(native_host_pma0),.pma_to_die1(native_host_pma1),
    .remote_host_status(native_remote_status),.remote_host_valid(native_remote_valid),.fault(native_host_fault));''')
for n in [0,1]:one(f'lk_EN{n}_pma_rx = native_ks_link ? native_ks_pma{n} : 544\'d0;',f'lk_EN{n}_pma_rx = native_host_link ? native_host_pma{n} : native_ks_link ? native_ks_pma{n} : 544\'d0;')
one('      force dut.s_7N_LP.w_u_lep_f_host = hword;','      if (!$test$plusargs("NATIVE_HOST_LINK")) force dut.s_7N_LP.w_u_lep_f_host = hword;')
one('always @(negedge clk) if (rst_n && nh > 0) begin','always @(negedge clk) if (rst_n && nh > 0 && !native_host_link) begin')
one('if ($test$plusargs("NATIVE_KS_LINK")) ksm=2;','if ($test$plusargs("NATIVE_KS_LINK")||$test$plusargs("NATIVE_HOST_LINK")) ksm=2;')
mark='''  always @(negedge clk) if (rst_n && cyc >= 0) begin
    if (dut.seqhost.w_u_seqhost_t_host[76] === 1'b1 && alive_at < 0)'''
provider='''  // Preserve the source fixture's valid-word gaps, but start from real returned
  // THOST alive and stretch for physical peer backpressure. Record actual dates.
  // The die fault ring can report MU faults after a short first-VO smoke ends.
  // Observe the real selected mux's fault output directly in this native mode.
  integer native_boot_mc_words=0,native_boot_mw_words=0;
  initial begin
    #1;
    if($test$plusargs("NATIVE_HOST_LINK"))begin
      for(integer boot_i=0;boot_i<nh;boot_i=boot_i+1)if(hmem[boot_i][0]&&hmem[boot_i][514:513]==2'd0)begin
        if(hmem[boot_i][8:1]==8'h15)native_boot_mc_words=native_boot_mc_words+1;
        if(hmem[boot_i][8:1]==8'h16)native_boot_mw_words=native_boot_mw_words+1;
      end
      $display("NATIVE_HOST_MU_BOOT mc_words=%0d mw_words=%0d",native_boot_mc_words,native_boot_mw_words);
    end
  end
  integer native_host_index=0,native_host_rx_index=0,native_host_seq_index=0;
  integer native_host_ordinal=0,native_host_rx_count=0,native_host_seq_count=0;
  integer native_host_base=-1,native_host_next=-1,native_host_prev=0;
  bit native_host_indices_init=0;reg[6:0]native_host_fault_prev=0;
  function automatic integer native_next_valid(input integer start_index);
    integer j;begin j=start_index;while(j<nh&&hmem[j][0]!==1'b1)j=j+1;native_next_valid=j;end
  endfunction
  always @(negedge clk) if(rst_n&&cyc>=0&&native_host_link&&nh>0)begin
    native_host_send<=0;
    if(!native_host_indices_init)begin
      native_host_index=native_next_valid(0);native_host_rx_index=native_next_valid(0);
      native_host_seq_index=native_next_valid(0);native_host_indices_init=1;
    end
    if(native_remote_valid)$display("NATIVE_HOST_RETURN edge=%0d status=%h",cyc,native_remote_status);
    if(native_remote_valid&&native_remote_status[76]===1'b1&&native_host_base<0)begin
      native_host_base=cyc+1+ht0;native_host_next=native_host_base;
      $display("NATIVE_HOST_REMOTE_ALIVE edge=%0d base=%0d status=%h",cyc,native_host_base,native_remote_status);
    end
    if(native_host_accepted)begin
      native_host_ordinal=native_host_ordinal+1;
      $display("NATIVE_HOST_ENQUEUE index=%0d ordinal=%0d edge=%0d word=%h",native_host_index,native_host_ordinal,cyc,hmem[native_host_index]);
      native_host_prev=native_host_index;native_host_index=native_next_valid(native_host_index+1);
      native_host_next=cyc+((native_host_index-native_host_prev>0)?native_host_index-native_host_prev:1);
      if(native_host_index>=nh)$display("NATIVE_HOST_SOURCE_DONE edge=%0d count=%0d",cyc,native_host_ordinal);
    end
    if(native_host_base>=0&&native_host_index<nh&&cyc+1>=native_host_next&&native_host_ready)begin
      native_host_word<=hmem[native_host_index];native_host_send<=1;
    end
    if(dut.s_7N_LP.w_u_lep_f_host[0]===1'b1)begin
      if(native_host_rx_index>=nh||dut.s_7N_LP.w_u_lep_f_host!==hmem[native_host_rx_index])
        $fatal(1,"NATIVE_HOST_LEP_MISMATCH index=%0d edge=%0d got=%h expected=%h",native_host_rx_index,cyc,dut.s_7N_LP.w_u_lep_f_host,hmem[native_host_rx_index]);
      native_host_rx_count=native_host_rx_count+1;
      $display("NATIVE_HOST_LEP_RX index=%0d ordinal=%0d edge=%0d word=%h",native_host_rx_index,native_host_rx_count,cyc,dut.s_7N_LP.w_u_lep_f_host);
      native_host_rx_index=native_next_valid(native_host_rx_index+1);
    end
    if(native_host_ks_accepted)$display("NATIVE_KS_PEER_ACCEPT edge=%0d word=%h",cyc,native_ks_word);
    if(dut.seqhost.u_u_seqhost.t_mf!==4'd0)
      $fatal(1,"NATIVE_HOST_MU_FAULT edge=%0d value=%h mc_words=%0d mw_words=%0d",cyc,dut.seqhost.u_u_seqhost.t_mf,native_boot_mc_words,native_boot_mw_words);
    if(native_host_fault!==native_host_fault_prev)begin
      $display("NATIVE_HOST_PEER_FAULT edge=%0d value=%h",cyc,native_host_fault);native_host_fault_prev=native_host_fault;
    end
  end
'''
one(mark,provider+mark)
mark="    if (dut.seqhost.u_u_seqhost.u.u_u.f_host[0] === 1'b1) nhv_seen = nhv_seen + 1;"
one(mark,'''    if(native_host_link&&dut.seqhost.u_u_seqhost.u.u_u.f_host[0]===1'b1)begin
      if(native_host_seq_index>=nh||dut.seqhost.u_u_seqhost.u.u_u.f_host!==hmem[native_host_seq_index])
        $fatal(1,"NATIVE_HOST_SEQ_MISMATCH index=%0d edge=%0d got=%h expected=%h",native_host_seq_index,cyc,dut.seqhost.u_u_seqhost.u.u_u.f_host,hmem[native_host_seq_index]);
      native_host_seq_count=native_host_seq_count+1;
      $display("NATIVE_HOST_SEQ_RX index=%0d ordinal=%0d edge=%0d word=%h",native_host_seq_index,native_host_seq_count,cyc,dut.seqhost.u_u_seqhost.u.u_u.f_host);
      native_host_seq_index=native_next_valid(native_host_seq_index+1);
    end
'''+mark)
a.output.write_text(s);print('NATIVE_HOST_LINK_TB',a.output)
