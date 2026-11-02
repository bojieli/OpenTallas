`timescale 1ns/1fs
// PREP ONLY. Nominal component clock; selected regional clock providers are distinct.
// Eight sequential numerical contexts reuse actual two-lane station instances.
// L6 inputs are explicitly REFERENCE component-boundary values, not executed ME.
module tb_qwen_native_head_post_two_lane;
  reg clk=0; always #0.416500 clk=~clk;
  reg rst_n=0,cfg=0,tw_we=0;
  reg [7:0] kc=7; reg [7:0] nw=8; reg [8:0] sb=72;
  reg [23:0] tw_addr; reg [1023:0] tw_data;
  reg [63:0] sd[0:3],rd[0:3];
  reg [3:0] cs=0;
  wire [63:0] nb,yd; wire[1:0] nc; wire rv,rl,sfault,rfault;
  wire[7:0] ri; wire bre; wire[8:0] bw; wire[255:0] bq;
  integer region=0,block=0,cyc=0,outputs=0,nbbeats=0,btbeats=0;
  integer first_nb,last_nb,first_bt,last_bt,first_r,last_r,origin;
  reg[511:0] l6[0:703],gold[0:10];
  reg[1023:0] boots[0:2];
  integer n,t,k,j,ix,lo,hi,base,goal,bidx,watch=0;
  string dir,control="baseline";
  // The genuine sender's station_out is registered; receiver retains PIN_IN=1.
  // Identical own-input publication gives positive lead through those actual
  // source/destination stages. This cut does not model selected L9 transport.
  qfd_dv_s8_station_tail1_nb0 sender(
    .ck(clk),.rst_n(rst_n),.cfg_v_p(cfg),.cfg_mode_p(2'd3),.cfg_wsrc_p(1'b0),
    .cfg_nwords_p(nw),.cfg_sbase_p(9'd0),.cfg_kcm1_p(kc),
    .rs_s_lo_p(sd[0]),.rs_s_hi_p(sd[1]),.rs_n_lo_p(sd[2]),.rs_n_hi_p(sd[3]),
    .rs_s_c_p(cs),.rs_n_c_p(cs),.nb_od(nb),.nb_oc(nc),
    .bt_q_p(32'd0),.bt_re(),.bt_word(),.r_v(),.r_idx(),.r_last(),.r_d(),
    .flt_bank_i(4'd0),.flt_vld_i(4'd0),.flt_bank_o(),.flt_vld_o(),.fault(sfault));
  qfd_dv_s8_station_tail1 receiver(
    .ck(clk),.rst_n(rst_n),.cfg_v_p(cfg),.cfg_mode_p(2'd2),.cfg_wsrc_p(1'b0),
    .cfg_nwords_p(nw),.cfg_sbase_p(sb),.cfg_kcm1_p(kc),
    .rs_s_lo_p(rd[0]),.rs_s_hi_p(rd[1]),.rs_n_lo_p(rd[2]),.rs_n_hi_p(rd[3]),
    .rs_s_c_p(cs),.rs_n_c_p(cs),.nb_d_p(nb),.nb_c_p(nc),
    .nb_od(),.nb_oc(),.bt_q_p(bq[32*region+:32]),.bt_re(bre),.bt_word(bw),
    .r_v(rv),.r_idx(ri),.r_last(rl),.r_d(yd),
    .flt_bank_i(4'd0),.flt_vld_i(4'd0),.flt_bank_o(),.flt_vld_o(),.fault(rfault));
  qfd_dv_s6_btab btab(.ck(clk),.bt_re(bre),.bt_word(bw),.bt_q(bq),
    .tw_we(tw_we),.tw_kind(2'd2),.tw_addr(tw_addr),.tw_data(tw_data));
  always @(posedge clk) begin
    cyc=cyc+1;
    if (rst_n) begin
      watch=watch+1;
      if(watch>1000) $fatal(1,"watchdog region=%0d block=%0d outputs=%0d nb=%0d bt=%0d",region,block,outputs,nbbeats,btbeats);
      #0.2;
      if(sfault||rfault) $fatal(1,"native fault region=%0d block=%0d cycle=%0d sender=%b receiver=%b",region,block,cyc,sfault,rfault);
      if(nc[0]) begin
        if(nbbeats==0) first_nb=cyc-origin;
        last_nb=cyc-origin; nbbeats=nbbeats+1;
      end
      if(bre) begin
        if(btbeats==0) first_bt=cyc-origin;
        if(bw!==sb+btbeats) $fatal(1,"BTAB address got=%0d expected=%0d",bw,sb+btbeats);
        last_bt=cyc-origin;btbeats=btbeats+1;
      end
      if(rv) begin
        if(outputs==0) first_r=cyc-origin;
        if(outputs>=nw||ri!==8'(outputs)||rl!==(outputs==nw-1)) $fatal(1,"result identity/count");
        bidx=(block==0?0:8)+outputs;
        if(yd!==gold[bidx][64*region+:64]) $fatal(1,"post mismatch block=%0d region=%0d idx=%0d actual=%h expected=%h",block,region,outputs,yd,gold[bidx][64*region+:64]);
        last_r=cyc-origin;outputs=outputs+1;
      end
    end
  end
  initial begin
    if($value$plusargs("CONTROL=%s",control)) begin end
    if(control=="oldKC1") kc=0;
    if(!$value$plusargs("INPUT=%s",dir)) $fatal(1,"INPUT required");
    $readmemh({dir,"/l6_REFERENCE.hex"},l6);
    $readmemh({dir,"/scaled_REFERENCE.hex"},gold);
    $readmemh({dir,"/genuine_btab.hex"},boots);
    for(region=0;region<8;region=region+1) for(block=0;block<2;block=block+1) begin
      @(negedge clk);rst_n=0;cfg=0;cs=0;watch=0;
      for(j=0;j<4;j=j+1) begin sd[j]=0;rd[j]=0;end
      outputs=0;nbbeats=0;btbeats=0;
      nw=block==0?8:3;sb=block==0?72:264;base=block==0?0:512;
      // Reset/config setup are finite component preconditions, outside origin.
      repeat(24) @(negedge clk);
      rst_n=1;
      repeat(24) @(negedge clk);
      for(j=0;j<3;j=j+1) begin
        tw_we=1;tw_addr=(j==0?72:j==1?76:264);tw_data=boots[j];if(control=="wrongBTAB"&&j==0) tw_data[0]=~tw_data[0];@(negedge clk);
      end
      tw_we=0;cfg=1;@(negedge clk);cfg=0;
      repeat(8) @(negedge clk);
      // origin: first near L6 valid presented before its capture edge.
      // Native SKEW14 requires hi/far publication exactly14edges later.
      origin=cyc;
      for(t=0;t<8*nw+14;t=t+1) begin
        cs=0;
        for(j=0;j<4;j=j+1) begin sd[j]=0;rd[j]=0;end
        for(j=0;j<2;j=j+1) begin
          ix=t-(j==0?0:14+(control=="shiftedFar"?1:0));
          if(ix>=0&&ix<8*nw) begin
            cs[2*j]=1;
            // Source-proven block0 sender0..3/receiver4..7;
            // tail148 sender4..7/receiver0..3. Port ns,fs,nn,fn.
            lo=(block==0?0:4);hi=4-lo;
            sd[j]=l6[base+ix*8+lo+(j==0?1:0)][64*region+:64];
            sd[j+2]=l6[base+ix*8+lo+(j==0?2:3)][64*region+:64];
            rd[j]=l6[base+ix*8+hi+(j==0?1:0)][64*region+:64];
            rd[j+2]=l6[base+ix*8+hi+(j==0?2:3)][64*region+:64];
          end
        end
        @(negedge clk);
      end
      cs=0;
      while(outputs<nw) @(negedge clk);
      repeat(24) @(negedge clk);
      if(outputs!=nw||nbbeats!=nw||btbeats!=nw) $fatal(1,"count mismatch");
      $display("POST_CONTEXT block=%0d region=%0d values=%0d nb_age=%0d..%0d bt_age=%0d..%0d result_age=%0d..%0d",(block==0?0:148),region,2*nw,first_nb,last_nb,first_bt,last_bt,first_r,last_r);
    end
    $display("PASS_NATIVE_POST_COMPONENT_REFERENCE_BOUNDARY rows176 scaled_values176 nominal_clock833ps sequential_contexts16");
    $finish;
  end
endmodule
