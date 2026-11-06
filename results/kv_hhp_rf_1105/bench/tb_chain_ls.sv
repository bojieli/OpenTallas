`timescale 1ns/1ps
// DIE-KV-71/HHP 11-05: old vs new qkd_kv_pc_chain_station_b_p.  Every output on every edge; land_es[287:1] only where land_es[0] (its
// only reader, qkd_host_static_pc*, loads a[287:1] behind a[0]).  Also a model of that reader: both queues of accepted words.  +seed= +cycles=
module tb_chain_ls;
  parameter [4:0] PCP=0;
  reg ck=0,rn=0; reg [1:0] st=0; reg [779:0] di=0; reg [260:0] er=0; always #1 ck=~ck;
  `define W(p) wire [779:0] p``dout; wire [287:0] p``land,p``wes; wire [317:0] p``ctx; wire p``ev,p``eiv,p``ehalf,p``esc,p``ers,p``cap,p``tr,p``f; wire [60:0] p``eid; wire [28:0] p``ead; wire [4:0] p``epc; wire [1:0] p``est; wire [17:0] p``etok; wire [5:0] p``ew; wire [15:0] p``eep;
  `W(o_) `W(n_)
  `define P(p) .ck(ck),.rst_n(rn),.cfg_stack(st),.di(di),.dout(p``dout),.land_es(p``land),.land_er(er),.wes(p``wes),.es_context(p``ctx),.es_expected_valid(p``ev),.es_expected_identity(p``eid),.es_expected_address(p``ead),.es_expected_pc(p``epc),.es_expected_stack(p``est),.emb_issue_v(p``eiv),.emb_token(p``etok),.emb_word_index(p``ew),.emb_half(p``ehalf),.emb_scale(p``esc),.emb_epoch(p``eep),.emb_return_slot(p``ers),.capture_slot(p``cap),.transfer_slot(p``tr),.fault(p``f)
  qkd_kv_pc_chain_station_b_p_old #(.PC(PCP)) old(`P(o_));
  qkd_kv_pc_chain_station_b_p     #(.PC(PCP)) dut(`P(n_));
  integer seed=1,cycles=400000,cyc=0,pb=20; longint c_w=0; reg [287:1] oa[0:3],na[0:3]; integer wp=0; reg oav=0,nav=0; reg [287:0] oaq=0,naq=0;
  function automatic int r(int m); return $urandom_range(m-1,0); endfunction
  initial begin
    if(!$value$plusargs("seed=%d",seed)) seed=1; if(!$value$plusargs("cycles=%d",cycles)) cycles=400000; void'($urandom(seed));
    repeat(8) @(negedge ck); rn=1;
    forever begin
      @(negedge ck); cyc++;
      if(cyc%2000==0) pb=r(60);
      for(int i=0;i<25;i++) di[i*32+:32]=$urandom;
      di[1:0]=r(4); di[6:2]=r(3)==0?PCP:r(32); di[11:7]=r(3)==0?PCP:r(32); di[779]=r(100)<pb;
      di[616:615]=r(4)==0?r(4):0; di[754]=r(20)==0; di[719]=r(50)==0; di[759:755]=r(2)==0?PCP:r(32);
      er=0; er[259]=r(30)==0; if(r(2000)==0) er[0]=1; if(r(2000)==0) er[260]=1;
    end
  end
  wire [1800:0] ov={o_dout,o_wes,o_ctx,o_ev,o_eiv,o_ehalf,o_esc,o_ers,o_cap,o_tr,o_f,o_eid,o_ead,o_epc,o_est,o_etok,o_ew,o_eep,o_land[0]};
  wire [1800:0] nv={n_dout,n_wes,n_ctx,n_ev,n_eiv,n_ehalf,n_esc,n_ers,n_cap,n_tr,n_f,n_eid,n_ead,n_epc,n_est,n_etok,n_ew,n_eep,n_land[0]};
  always @(posedge ck) if(rn && cyc>4) begin
    if(ov!==nv) begin $display("FAIL cycle %0d outputs differ",cyc); $finish; end
    oaq<=o_land; naq<=n_land;
    if(oaq[0]!==naq[0] || (oaq[0] && oaq[287:1]!==naq[287:1])) begin $display("FAIL cycle %0d reader word %h vs %h",cyc,oaq,naq); $finish; end
    c_w+=n_land[0];
    if(cyc>=cycles) begin $display("PASS cycles %0d land words %0d",cyc,c_w); $finish; end
  end
endmodule
