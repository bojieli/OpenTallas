`timescale 1ns/1ps
module tb_kvs_domsplit;
  reg ck = 0; always #1 ck = ~ck;
  integer t, bad, chk, act, nland; reg phb;
  reg [0:0] rst_n;
  reg [0:0] afk;
  reg [0:0] afv;
  reg [0:0] afu;
  reg [0:0] hrst_n;
  reg [1:0] slg__cfg_stack;
  reg [2:0] slg__cfg_group;
  reg [37:0] kreq;
  reg [14:0] vreq;
  reg [12:0] x__est;
  reg [17:0] x__tok;
  reg [15:0] x__tep;
  reg [270:0] i_ctl;
  reg [304:0] i_pc0;
  reg [304:0] i_pc1;
  reg [304:0] i_pc2;
  reg [304:0] i_pc3;
  reg [143:0] i_up;
  wire [1055:0] o__rsp;
  wire [1061:0] o__krsp;
  wire [0:0] o__af__fault;
  wire [0:0] o__y__est__0_1;
  wire [17:0] o__y__tok;
  wire [15:0] o__y__tep;
  wire [127:0] o__o_pc0;
  wire [127:0] o__o_pc1;
  wire [127:0] o__o_pc2;
  wire [127:0] o__o_pc3;
  wire [270:0] o__o_dn;
  wire [143:0] o__o_ctl;
  wire [1055:0] n__rsp;
  wire [1061:0] n__krsp;
  wire [0:0] n__af__fault;
  wire [0:0] n__y__est__0_1;
  wire [17:0] n__y__tok;
  wire [15:0] n__y__tep;
  wire [32:0] n__o_pc0;
  wire [94:0] n__o_pc0_h;
  wire [32:0] n__o_pc1;
  wire [94:0] n__o_pc1_h;
  wire [32:0] n__o_pc2;
  wire [94:0] n__o_pc2_h;
  wire [32:0] n__o_pc3;
  wire [94:0] n__o_pc3_h;
  wire [270:0] n__o_dn;
  wire [143:0] n__o_ctl;
  old_tile u_old (.ck(ck), .rst_n(rst_n), .afk(afk), .afv(afv), .afu(afu), .hck(ck), .hrst_n(hrst_n), .slg__cfg_stack(slg__cfg_stack), .slg__cfg_group(slg__cfg_group), .kreq(kreq), .vreq(vreq), .x__est(x__est), .x__tok(x__tok), .x__tep(x__tep), .rsp(o__rsp), .krsp(o__krsp), .af__fault(o__af__fault), .y__est__0_1(o__y__est__0_1), .y__tok(o__y__tok), .y__tep(o__y__tep), .i_ctl(i_ctl), .i_pc0(i_pc0), .i_pc1(i_pc1), .i_pc2(i_pc2), .i_pc3(i_pc3), .o_pc0(o__o_pc0), .o_pc1(o__o_pc1), .o_pc2(o__o_pc2), .o_pc3(o__o_pc3), .o_dn(o__o_dn), .i_up(i_up), .o_ctl(o__o_ctl));
  new_tile u_new (.ck(ck), .rst_n(rst_n), .afk(afk), .afv(afv), .afu(afu), .hck(ck), .hrst_n(hrst_n), .slg__cfg_stack(slg__cfg_stack), .slg__cfg_group(slg__cfg_group), .kreq(kreq), .vreq(vreq), .x__est(x__est), .x__tok(x__tok), .x__tep(x__tep), .rsp(n__rsp), .krsp(n__krsp), .af__fault(n__af__fault), .y__est__0_1(n__y__est__0_1), .y__tok(n__y__tok), .y__tep(n__y__tep), .i_ctl(i_ctl), .i_pc0({i_pc0[303:303], i_pc0[301:301], i_pc0[299:299], i_pc0[293:293], i_pc0[291:291], i_pc0[290:290], i_pc0[288:288], i_pc0[287:278], i_pc0[277:272], i_pc0[271:256], i_pc0[255:0]}), .i_pc0_h({i_pc0[304:304], i_pc0[302:302], i_pc0[300:300], i_pc0[298:298], i_pc0[297:297], i_pc0[296:296], i_pc0[295:295], i_pc0[294:294], i_pc0[292:292], i_pc0[289:289]}), .i_pc1({i_pc1[303:303], i_pc1[301:301], i_pc1[299:299], i_pc1[293:293], i_pc1[291:291], i_pc1[290:290], i_pc1[288:288], i_pc1[287:278], i_pc1[277:272], i_pc1[271:256], i_pc1[255:0]}), .i_pc1_h({i_pc1[304:304], i_pc1[302:302], i_pc1[300:300], i_pc1[298:298], i_pc1[297:297], i_pc1[296:296], i_pc1[295:295], i_pc1[294:294], i_pc1[292:292], i_pc1[289:289]}), .i_pc2({i_pc2[303:303], i_pc2[301:301], i_pc2[299:299], i_pc2[293:293], i_pc2[291:291], i_pc2[290:290], i_pc2[288:288], i_pc2[287:278], i_pc2[277:272], i_pc2[271:256], i_pc2[255:0]}), .i_pc2_h({i_pc2[304:304], i_pc2[302:302], i_pc2[300:300], i_pc2[298:298], i_pc2[297:297], i_pc2[296:296], i_pc2[295:295], i_pc2[294:294], i_pc2[292:292], i_pc2[289:289]}), .i_pc3({i_pc3[303:303], i_pc3[301:301], i_pc3[299:299], i_pc3[293:293], i_pc3[291:291], i_pc3[290:290], i_pc3[288:288], i_pc3[287:278], i_pc3[277:272], i_pc3[271:256], i_pc3[255:0]}), .i_pc3_h({i_pc3[304:304], i_pc3[302:302], i_pc3[300:300], i_pc3[298:298], i_pc3[297:297], i_pc3[296:296], i_pc3[295:295], i_pc3[294:294], i_pc3[292:292], i_pc3[289:289]}), .o_pc0(n__o_pc0), .o_pc0_h(n__o_pc0_h), .o_pc1(n__o_pc1), .o_pc1_h(n__o_pc1_h), .o_pc2(n__o_pc2), .o_pc2_h(n__o_pc2_h), .o_pc3(n__o_pc3), .o_pc3_h(n__o_pc3_h), .o_dn(n__o_dn), .i_up(i_up), .o_ctl(n__o_ctl));
  reg [143:0] h1, h2;
  reg [0:0] f_w_af__fault;
  reg [0:0] f_w_bcdc0__applied_hbm;
  reg [0:0] f_w_bcdc0__fault_core;
  reg [0:0] f_w_bcdc0__fault_hbm;
  reg [7:0] f_w_bcdc0__sink_addr;
  reg [63:0] f_w_bcdc0__sink_data;
  reg [0:0] f_w_bcdc0__sink_seal;
  reg [0:0] f_w_bcdc0__sink_we;
  reg [0:0] f_w_bcdc1__applied_hbm;
  reg [0:0] f_w_bcdc1__fault_core;
  reg [0:0] f_w_bcdc1__fault_hbm;
  reg [7:0] f_w_bcdc1__sink_addr;
  reg [63:0] f_w_bcdc1__sink_data;
  reg [0:0] f_w_bcdc1__sink_seal;
  reg [0:0] f_w_bcdc1__sink_we;
  reg [0:0] f_w_bcdc2__applied_hbm;
  reg [0:0] f_w_bcdc2__fault_core;
  reg [0:0] f_w_bcdc2__fault_hbm;
  reg [7:0] f_w_bcdc2__sink_addr;
  reg [63:0] f_w_bcdc2__sink_data;
  reg [0:0] f_w_bcdc2__sink_seal;
  reg [0:0] f_w_bcdc2__sink_we;
  reg [0:0] f_w_bcdc3__applied_hbm;
  reg [0:0] f_w_bcdc3__fault_core;
  reg [0:0] f_w_bcdc3__fault_hbm;
  reg [7:0] f_w_bcdc3__sink_addr;
  reg [63:0] f_w_bcdc3__sink_data;
  reg [0:0] f_w_bcdc3__sink_seal;
  reg [0:0] f_w_bcdc3__sink_we;
  reg [0:0] f_w_bcdcf__applied_hbm;
  reg [0:0] f_w_bcdcf__fault_core;
  reg [0:0] f_w_bcdcf__fault_hbm;
  reg [7:0] f_w_bcdcf__sink_addr;
  reg [63:0] f_w_bcdcf__sink_data;
  reg [0:0] f_w_bcdcf__sink_seal;
  reg [0:0] f_w_bcdcf__sink_we;
  reg [0:0] f_w_cf1__fault;
  reg [0:0] f_w_drain__drained;
  reg [0:0] f_w_drain__fault;
  reg [3:0] f_w_fcal__blk_go;
  reg [0:0] f_w_fcal__fault;
  reg [0:0] f_w_lcal__arm;
  reg [0:0] f_w_lcal__fault;
  reg [15:0] f_w_lcal__l_epoch;
  reg [5:0] f_w_lcal__l_layer;
  reg [3:0] f_w_lcal__l_put;
  reg [39:0] f_w_lcal__l_sector;
  reg [15:0] f_w_lcal__r_epoch;
  reg [5:0] f_w_lcal__r_layer;
  reg [3:0] f_w_lcal__r_put;
  reg [39:0] f_w_lcal__r_sector;
  reg [0:0] f_w_phase__ctrl_go_h;
  reg [13:0] f_w_phase__ctx_t_h;
  reg [15:0] f_w_phase__epoch_h;
  reg [0:0] f_w_phase__fault_core;
  reg [0:0] f_w_phase__fault_hbm;
  reg [0:0] f_w_phase__idle_core;
  reg [0:0] f_w_phase__idle_hbm;
  reg [0:0] f_w_phase__kgo_h;
  reg [5:0] f_w_phase__layer_h;
  reg [0:0] f_w_phase__vgo_h;
  reg [0:0] f_w_slg__fault;
  reg [1023:0] f_w_slg__rsp_data;
  reg [15:0] f_w_slg__rsp_epoch;
  reg [5:0] f_w_slg__rsp_layer;
  reg [13:0] f_w_slg__rsp_t;
  reg [0:0] f_w_slg__rsp_v;
  reg [0:0] f_w_slg__rsp_valid;
  initial begin
    bad = 0; chk = 0; act = 0; nland = 0; phb = 0;
    rst_n = 0;
    afk = 0;
    afv = 0;
    afu = 0;
    hrst_n = 0;
    slg__cfg_stack = 0;
    slg__cfg_group = 0;
    kreq = 0;
    vreq = 0;
    x__est = 0;
    x__tok = 0;
    x__tep = 0;
    i_ctl = 0;
    i_pc0 = 0;
    i_pc1 = 0;
    i_pc2 = 0;
    i_pc3 = 0;
    i_up = 0;
    repeat (6) @(negedge ck);
    rst_n = 1; hrst_n = 1;
    for (t = 0; t < 2000; t = t + 1) begin
      @(negedge ck);
      if (t == 1000) begin phb = 1;
        force u_old.w_af__fault = f_w_af__fault; force u_new.w_af__fault = f_w_af__fault;
        force u_old.w_bcdc0__applied_hbm = f_w_bcdc0__applied_hbm; force u_new.w_bcdc0__applied_hbm = f_w_bcdc0__applied_hbm;
        force u_old.w_bcdc0__fault_core = f_w_bcdc0__fault_core; force u_new.w_bcdc0__fault_core = f_w_bcdc0__fault_core;
        force u_old.w_bcdc0__fault_hbm = f_w_bcdc0__fault_hbm; force u_new.w_bcdc0__fault_hbm = f_w_bcdc0__fault_hbm;
        force u_old.w_bcdc0__sink_addr = f_w_bcdc0__sink_addr; force u_new.w_bcdc0__sink_addr = f_w_bcdc0__sink_addr;
        force u_old.w_bcdc0__sink_data = f_w_bcdc0__sink_data; force u_new.w_bcdc0__sink_data = f_w_bcdc0__sink_data;
        force u_old.w_bcdc0__sink_seal = f_w_bcdc0__sink_seal; force u_new.w_bcdc0__sink_seal = f_w_bcdc0__sink_seal;
        force u_old.w_bcdc0__sink_we = f_w_bcdc0__sink_we; force u_new.w_bcdc0__sink_we = f_w_bcdc0__sink_we;
        force u_old.w_bcdc1__applied_hbm = f_w_bcdc1__applied_hbm; force u_new.w_bcdc1__applied_hbm = f_w_bcdc1__applied_hbm;
        force u_old.w_bcdc1__fault_core = f_w_bcdc1__fault_core; force u_new.w_bcdc1__fault_core = f_w_bcdc1__fault_core;
        force u_old.w_bcdc1__fault_hbm = f_w_bcdc1__fault_hbm; force u_new.w_bcdc1__fault_hbm = f_w_bcdc1__fault_hbm;
        force u_old.w_bcdc1__sink_addr = f_w_bcdc1__sink_addr; force u_new.w_bcdc1__sink_addr = f_w_bcdc1__sink_addr;
        force u_old.w_bcdc1__sink_data = f_w_bcdc1__sink_data; force u_new.w_bcdc1__sink_data = f_w_bcdc1__sink_data;
        force u_old.w_bcdc1__sink_seal = f_w_bcdc1__sink_seal; force u_new.w_bcdc1__sink_seal = f_w_bcdc1__sink_seal;
        force u_old.w_bcdc1__sink_we = f_w_bcdc1__sink_we; force u_new.w_bcdc1__sink_we = f_w_bcdc1__sink_we;
        force u_old.w_bcdc2__applied_hbm = f_w_bcdc2__applied_hbm; force u_new.w_bcdc2__applied_hbm = f_w_bcdc2__applied_hbm;
        force u_old.w_bcdc2__fault_core = f_w_bcdc2__fault_core; force u_new.w_bcdc2__fault_core = f_w_bcdc2__fault_core;
        force u_old.w_bcdc2__fault_hbm = f_w_bcdc2__fault_hbm; force u_new.w_bcdc2__fault_hbm = f_w_bcdc2__fault_hbm;
        force u_old.w_bcdc2__sink_addr = f_w_bcdc2__sink_addr; force u_new.w_bcdc2__sink_addr = f_w_bcdc2__sink_addr;
        force u_old.w_bcdc2__sink_data = f_w_bcdc2__sink_data; force u_new.w_bcdc2__sink_data = f_w_bcdc2__sink_data;
        force u_old.w_bcdc2__sink_seal = f_w_bcdc2__sink_seal; force u_new.w_bcdc2__sink_seal = f_w_bcdc2__sink_seal;
        force u_old.w_bcdc2__sink_we = f_w_bcdc2__sink_we; force u_new.w_bcdc2__sink_we = f_w_bcdc2__sink_we;
        force u_old.w_bcdc3__applied_hbm = f_w_bcdc3__applied_hbm; force u_new.w_bcdc3__applied_hbm = f_w_bcdc3__applied_hbm;
        force u_old.w_bcdc3__fault_core = f_w_bcdc3__fault_core; force u_new.w_bcdc3__fault_core = f_w_bcdc3__fault_core;
        force u_old.w_bcdc3__fault_hbm = f_w_bcdc3__fault_hbm; force u_new.w_bcdc3__fault_hbm = f_w_bcdc3__fault_hbm;
        force u_old.w_bcdc3__sink_addr = f_w_bcdc3__sink_addr; force u_new.w_bcdc3__sink_addr = f_w_bcdc3__sink_addr;
        force u_old.w_bcdc3__sink_data = f_w_bcdc3__sink_data; force u_new.w_bcdc3__sink_data = f_w_bcdc3__sink_data;
        force u_old.w_bcdc3__sink_seal = f_w_bcdc3__sink_seal; force u_new.w_bcdc3__sink_seal = f_w_bcdc3__sink_seal;
        force u_old.w_bcdc3__sink_we = f_w_bcdc3__sink_we; force u_new.w_bcdc3__sink_we = f_w_bcdc3__sink_we;
        force u_old.w_bcdcf__applied_hbm = f_w_bcdcf__applied_hbm; force u_new.w_bcdcf__applied_hbm = f_w_bcdcf__applied_hbm;
        force u_old.w_bcdcf__fault_core = f_w_bcdcf__fault_core; force u_new.w_bcdcf__fault_core = f_w_bcdcf__fault_core;
        force u_old.w_bcdcf__fault_hbm = f_w_bcdcf__fault_hbm; force u_new.w_bcdcf__fault_hbm = f_w_bcdcf__fault_hbm;
        force u_old.w_bcdcf__sink_addr = f_w_bcdcf__sink_addr; force u_new.w_bcdcf__sink_addr = f_w_bcdcf__sink_addr;
        force u_old.w_bcdcf__sink_data = f_w_bcdcf__sink_data; force u_new.w_bcdcf__sink_data = f_w_bcdcf__sink_data;
        force u_old.w_bcdcf__sink_seal = f_w_bcdcf__sink_seal; force u_new.w_bcdcf__sink_seal = f_w_bcdcf__sink_seal;
        force u_old.w_bcdcf__sink_we = f_w_bcdcf__sink_we; force u_new.w_bcdcf__sink_we = f_w_bcdcf__sink_we;
        force u_old.w_cf1__fault = f_w_cf1__fault; force u_new.w_cf1__fault = f_w_cf1__fault;
        force u_old.w_drain__drained = f_w_drain__drained; force u_new.w_drain__drained = f_w_drain__drained;
        force u_old.w_drain__fault = f_w_drain__fault; force u_new.w_drain__fault = f_w_drain__fault;
        force u_old.w_fcal__blk_go = f_w_fcal__blk_go; force u_new.w_fcal__blk_go = f_w_fcal__blk_go;
        force u_old.w_fcal__fault = f_w_fcal__fault; force u_new.w_fcal__fault = f_w_fcal__fault;
        force u_old.w_lcal__arm = f_w_lcal__arm; force u_new.w_lcal__arm = f_w_lcal__arm;
        force u_old.w_lcal__fault = f_w_lcal__fault; force u_new.w_lcal__fault = f_w_lcal__fault;
        force u_old.w_lcal__l_epoch = f_w_lcal__l_epoch; force u_new.w_lcal__l_epoch = f_w_lcal__l_epoch;
        force u_old.w_lcal__l_layer = f_w_lcal__l_layer; force u_new.w_lcal__l_layer = f_w_lcal__l_layer;
        force u_old.w_lcal__l_put = f_w_lcal__l_put; force u_new.w_lcal__l_put = f_w_lcal__l_put;
        force u_old.w_lcal__l_sector = f_w_lcal__l_sector; force u_new.w_lcal__l_sector = f_w_lcal__l_sector;
        force u_old.w_lcal__r_epoch = f_w_lcal__r_epoch; force u_new.w_lcal__r_epoch = f_w_lcal__r_epoch;
        force u_old.w_lcal__r_layer = f_w_lcal__r_layer; force u_new.w_lcal__r_layer = f_w_lcal__r_layer;
        force u_old.w_lcal__r_put = f_w_lcal__r_put; force u_new.w_lcal__r_put = f_w_lcal__r_put;
        force u_old.w_lcal__r_sector = f_w_lcal__r_sector; force u_new.w_lcal__r_sector = f_w_lcal__r_sector;
        force u_old.w_phase__ctrl_go_h = f_w_phase__ctrl_go_h; force u_new.w_phase__ctrl_go_h = f_w_phase__ctrl_go_h;
        force u_old.w_phase__ctx_t_h = f_w_phase__ctx_t_h; force u_new.w_phase__ctx_t_h = f_w_phase__ctx_t_h;
        force u_old.w_phase__epoch_h = f_w_phase__epoch_h; force u_new.w_phase__epoch_h = f_w_phase__epoch_h;
        force u_old.w_phase__fault_core = f_w_phase__fault_core; force u_new.w_phase__fault_core = f_w_phase__fault_core;
        force u_old.w_phase__fault_hbm = f_w_phase__fault_hbm; force u_new.w_phase__fault_hbm = f_w_phase__fault_hbm;
        force u_old.w_phase__idle_core = f_w_phase__idle_core; force u_new.w_phase__idle_core = f_w_phase__idle_core;
        force u_old.w_phase__idle_hbm = f_w_phase__idle_hbm; force u_new.w_phase__idle_hbm = f_w_phase__idle_hbm;
        force u_old.w_phase__kgo_h = f_w_phase__kgo_h; force u_new.w_phase__kgo_h = f_w_phase__kgo_h;
        force u_old.w_phase__layer_h = f_w_phase__layer_h; force u_new.w_phase__layer_h = f_w_phase__layer_h;
        force u_old.w_phase__vgo_h = f_w_phase__vgo_h; force u_new.w_phase__vgo_h = f_w_phase__vgo_h;
        force u_old.w_slg__fault = f_w_slg__fault; force u_new.w_slg__fault = f_w_slg__fault;
        force u_old.w_slg__rsp_data = f_w_slg__rsp_data; force u_new.w_slg__rsp_data = f_w_slg__rsp_data;
        force u_old.w_slg__rsp_epoch = f_w_slg__rsp_epoch; force u_new.w_slg__rsp_epoch = f_w_slg__rsp_epoch;
        force u_old.w_slg__rsp_layer = f_w_slg__rsp_layer; force u_new.w_slg__rsp_layer = f_w_slg__rsp_layer;
        force u_old.w_slg__rsp_t = f_w_slg__rsp_t; force u_new.w_slg__rsp_t = f_w_slg__rsp_t;
        force u_old.w_slg__rsp_v = f_w_slg__rsp_v; force u_new.w_slg__rsp_v = f_w_slg__rsp_v;
        force u_old.w_slg__rsp_valid = f_w_slg__rsp_valid; force u_new.w_slg__rsp_valid = f_w_slg__rsp_valid;
      end
      afk = {$random};
      afv = {$random};
      afu = {$random};
      slg__cfg_stack = {$random};
      slg__cfg_group = {$random};
      kreq = {$random, $random};
      vreq = {$random};
      x__est = {$random};
      x__tok = {$random};
      x__tep = {$random};
      i_ctl = {$random, $random, $random, $random, $random, $random, $random, $random, $random};
      i_pc0 = {$random, $random, $random, $random, $random, $random, $random, $random, $random, $random};
      i_pc1 = {$random, $random, $random, $random, $random, $random, $random, $random, $random, $random};
      i_pc2 = {$random, $random, $random, $random, $random, $random, $random, $random, $random, $random};
      i_pc3 = {$random, $random, $random, $random, $random, $random, $random, $random, $random, $random};
      i_up = {$random, $random, $random, $random, $random};
      f_w_af__fault = {$random};
      f_w_bcdc0__applied_hbm = {$random};
      f_w_bcdc0__fault_core = {$random};
      f_w_bcdc0__fault_hbm = {$random};
      f_w_bcdc0__sink_addr = {$random};
      f_w_bcdc0__sink_data = {$random, $random};
      f_w_bcdc0__sink_seal = {$random};
      f_w_bcdc0__sink_we = {$random};
      f_w_bcdc1__applied_hbm = {$random};
      f_w_bcdc1__fault_core = {$random};
      f_w_bcdc1__fault_hbm = {$random};
      f_w_bcdc1__sink_addr = {$random};
      f_w_bcdc1__sink_data = {$random, $random};
      f_w_bcdc1__sink_seal = {$random};
      f_w_bcdc1__sink_we = {$random};
      f_w_bcdc2__applied_hbm = {$random};
      f_w_bcdc2__fault_core = {$random};
      f_w_bcdc2__fault_hbm = {$random};
      f_w_bcdc2__sink_addr = {$random};
      f_w_bcdc2__sink_data = {$random, $random};
      f_w_bcdc2__sink_seal = {$random};
      f_w_bcdc2__sink_we = {$random};
      f_w_bcdc3__applied_hbm = {$random};
      f_w_bcdc3__fault_core = {$random};
      f_w_bcdc3__fault_hbm = {$random};
      f_w_bcdc3__sink_addr = {$random};
      f_w_bcdc3__sink_data = {$random, $random};
      f_w_bcdc3__sink_seal = {$random};
      f_w_bcdc3__sink_we = {$random};
      f_w_bcdcf__applied_hbm = {$random};
      f_w_bcdcf__fault_core = {$random};
      f_w_bcdcf__fault_hbm = {$random};
      f_w_bcdcf__sink_addr = {$random};
      f_w_bcdcf__sink_data = {$random, $random};
      f_w_bcdcf__sink_seal = {$random};
      f_w_bcdcf__sink_we = {$random};
      f_w_cf1__fault = {$random};
      f_w_drain__drained = {$random};
      f_w_drain__fault = {$random};
      f_w_fcal__blk_go = {$random};
      f_w_fcal__fault = {$random};
      f_w_lcal__arm = {$random};
      f_w_lcal__fault = {$random};
      f_w_lcal__l_epoch = {$random};
      f_w_lcal__l_layer = {$random};
      f_w_lcal__l_put = {$random};
      f_w_lcal__l_sector = {$random, $random};
      f_w_lcal__r_epoch = {$random};
      f_w_lcal__r_layer = {$random};
      f_w_lcal__r_put = {$random};
      f_w_lcal__r_sector = {$random, $random};
      f_w_phase__ctrl_go_h = {$random};
      f_w_phase__ctx_t_h = {$random};
      f_w_phase__epoch_h = {$random};
      f_w_phase__fault_core = {$random};
      f_w_phase__fault_hbm = {$random};
      f_w_phase__idle_core = {$random};
      f_w_phase__idle_hbm = {$random};
      f_w_phase__kgo_h = {$random};
      f_w_phase__layer_h = {$random};
      f_w_phase__vgo_h = {$random};
      f_w_slg__fault = {$random};
      f_w_slg__rsp_data = {$random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random};
      f_w_slg__rsp_epoch = {$random};
      f_w_slg__rsp_layer = {$random};
      f_w_slg__rsp_t = {$random};
      f_w_slg__rsp_v = {$random};
      f_w_slg__rsp_valid = {$random};
      #0.5;
      if (t > 2) begin
        chk = chk + 1; if (n__rsp !== o__rsp) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out rsp", t); end
        if (n__rsp != 0) act = act + 1;
        chk = chk + 1; if (n__krsp !== o__krsp) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out krsp", t); end
        if (n__krsp != 0) act = act + 1;
        chk = chk + 1; if (n__af__fault !== o__af__fault) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out af__fault", t); end
        if (n__af__fault != 0) act = act + 1;
        chk = chk + 1; if (n__y__est__0_1 !== o__y__est__0_1) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out y__est__0_1", t); end
        if (n__y__est__0_1 != 0) act = act + 1;
        chk = chk + 1; if (n__y__tok !== o__y__tok) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out y__tok", t); end
        if (n__y__tok != 0) act = act + 1;
        chk = chk + 1; if (n__y__tep !== o__y__tep) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out y__tep", t); end
        if (n__y__tep != 0) act = act + 1;
        chk = chk + 1; if (n__o_pc0 !== {o__o_pc0[104:95], o__o_pc0[94:94], o__o_pc0[93:88], o__o_pc0[87:72]}) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_pc0", t); end
        if (n__o_pc0 != 0) act = act + 1;
        chk = chk + 1; if (n__o_pc0_h !== {o__o_pc0[127:122], o__o_pc0[121:106], o__o_pc0[105:105], o__o_pc0[71:71], o__o_pc0[70:70], o__o_pc0[69:69], o__o_pc0[68:5], o__o_pc0[4:0]}) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_pc0_h", t); end
        if (n__o_pc0_h != 0) act = act + 1;
        chk = chk + 1; if (n__o_pc1 !== {o__o_pc1[104:95], o__o_pc1[94:94], o__o_pc1[93:88], o__o_pc1[87:72]}) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_pc1", t); end
        if (n__o_pc1 != 0) act = act + 1;
        chk = chk + 1; if (n__o_pc1_h !== {o__o_pc1[127:122], o__o_pc1[121:106], o__o_pc1[105:105], o__o_pc1[71:71], o__o_pc1[70:70], o__o_pc1[69:69], o__o_pc1[68:5], o__o_pc1[4:0]}) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_pc1_h", t); end
        if (n__o_pc1_h != 0) act = act + 1;
        chk = chk + 1; if (n__o_pc2 !== {o__o_pc2[104:95], o__o_pc2[94:94], o__o_pc2[93:88], o__o_pc2[87:72]}) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_pc2", t); end
        if (n__o_pc2 != 0) act = act + 1;
        chk = chk + 1; if (n__o_pc2_h !== {o__o_pc2[127:122], o__o_pc2[121:106], o__o_pc2[105:105], o__o_pc2[71:71], o__o_pc2[70:70], o__o_pc2[69:69], o__o_pc2[68:5], o__o_pc2[4:0]}) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_pc2_h", t); end
        if (n__o_pc2_h != 0) act = act + 1;
        chk = chk + 1; if (n__o_pc3 !== {o__o_pc3[104:95], o__o_pc3[94:94], o__o_pc3[93:88], o__o_pc3[87:72]}) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_pc3", t); end
        if (n__o_pc3 != 0) act = act + 1;
        chk = chk + 1; if (n__o_pc3_h !== {o__o_pc3[127:122], o__o_pc3[121:106], o__o_pc3[105:105], o__o_pc3[71:71], o__o_pc3[70:70], o__o_pc3[69:69], o__o_pc3[68:5], o__o_pc3[4:0]}) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_pc3_h", t); end
        if (n__o_pc3_h != 0) act = act + 1;
        chk = chk + 1; if (n__o_dn !== o__o_dn) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_dn", t); end
        if (n__o_dn != 0) act = act + 1;
        chk = chk + 1; if (n__o_ctl[0] !== h2[0]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[0] landed", t); end
        chk = chk + 1; if (n__o_ctl[1] !== o__o_ctl[1]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[1]", t); end
        chk = chk + 1; if (n__o_ctl[2] !== h2[2]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[2] landed", t); end
        chk = chk + 1; if (n__o_ctl[3] !== h2[3]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[3] landed", t); end
        chk = chk + 1; if (n__o_ctl[4] !== o__o_ctl[4]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[4]", t); end
        chk = chk + 1; if (n__o_ctl[5] !== h2[5]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[5] landed", t); end
        chk = chk + 1; if (n__o_ctl[6] !== h2[6]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[6] landed", t); end
        chk = chk + 1; if (n__o_ctl[7] !== o__o_ctl[7]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[7]", t); end
        chk = chk + 1; if (n__o_ctl[8] !== h2[8]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[8] landed", t); end
        chk = chk + 1; if (n__o_ctl[9] !== h2[9]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[9] landed", t); end
        chk = chk + 1; if (n__o_ctl[10] !== o__o_ctl[10]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[10]", t); end
        chk = chk + 1; if (n__o_ctl[11] !== h2[11]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[11] landed", t); end
        chk = chk + 1; if (n__o_ctl[12] !== h2[12]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[12] landed", t); end
        chk = chk + 1; if (n__o_ctl[13] !== o__o_ctl[13]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[13]", t); end
        chk = chk + 1; if (n__o_ctl[14] !== h2[14]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[14] landed", t); end
        chk = chk + 1; if (n__o_ctl[15] !== o__o_ctl[15]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[15]", t); end
        chk = chk + 1; if (n__o_ctl[16] !== o__o_ctl[16]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[16]", t); end
        chk = chk + 1; if (n__o_ctl[17] !== o__o_ctl[17]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[17]", t); end
        chk = chk + 1; if (n__o_ctl[18] !== o__o_ctl[18]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[18]", t); end
        chk = chk + 1; if (n__o_ctl[19] !== o__o_ctl[19]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[19]", t); end
        chk = chk + 1; if (n__o_ctl[20] !== o__o_ctl[20]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[20]", t); end
        chk = chk + 1; if (n__o_ctl[21] !== o__o_ctl[21]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[21]", t); end
        chk = chk + 1; if (n__o_ctl[22] !== o__o_ctl[22]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[22]", t); end
        chk = chk + 1; if (n__o_ctl[23] !== o__o_ctl[23]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[23]", t); end
        chk = chk + 1; if (n__o_ctl[24] !== o__o_ctl[24]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[24]", t); end
        chk = chk + 1; if (n__o_ctl[25] !== o__o_ctl[25]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[25]", t); end
        chk = chk + 1; if (n__o_ctl[26] !== o__o_ctl[26]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[26]", t); end
        chk = chk + 1; if (n__o_ctl[27] !== o__o_ctl[27]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[27]", t); end
        chk = chk + 1; if (n__o_ctl[28] !== o__o_ctl[28]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[28]", t); end
        chk = chk + 1; if (n__o_ctl[29] !== o__o_ctl[29]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[29]", t); end
        chk = chk + 1; if (n__o_ctl[30] !== o__o_ctl[30]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[30]", t); end
        chk = chk + 1; if (n__o_ctl[31] !== o__o_ctl[31]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[31]", t); end
        chk = chk + 1; if (n__o_ctl[32] !== o__o_ctl[32]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[32]", t); end
        chk = chk + 1; if (n__o_ctl[33] !== o__o_ctl[33]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[33]", t); end
        chk = chk + 1; if (n__o_ctl[34] !== o__o_ctl[34]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[34]", t); end
        chk = chk + 1; if (n__o_ctl[35] !== o__o_ctl[35]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[35]", t); end
        chk = chk + 1; if (n__o_ctl[36] !== o__o_ctl[36]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[36]", t); end
        chk = chk + 1; if (n__o_ctl[37] !== o__o_ctl[37]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[37]", t); end
        chk = chk + 1; if (n__o_ctl[38] !== o__o_ctl[38]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[38]", t); end
        chk = chk + 1; if (n__o_ctl[39] !== o__o_ctl[39]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[39]", t); end
        chk = chk + 1; if (n__o_ctl[40] !== o__o_ctl[40]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[40]", t); end
        chk = chk + 1; if (n__o_ctl[41] !== o__o_ctl[41]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[41]", t); end
        chk = chk + 1; if (n__o_ctl[42] !== o__o_ctl[42]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[42]", t); end
        chk = chk + 1; if (n__o_ctl[43] !== o__o_ctl[43]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[43]", t); end
        chk = chk + 1; if (n__o_ctl[44] !== o__o_ctl[44]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[44]", t); end
        chk = chk + 1; if (n__o_ctl[45] !== o__o_ctl[45]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[45]", t); end
        chk = chk + 1; if (n__o_ctl[46] !== o__o_ctl[46]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[46]", t); end
        chk = chk + 1; if (n__o_ctl[47] !== o__o_ctl[47]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[47]", t); end
        chk = chk + 1; if (n__o_ctl[48] !== o__o_ctl[48]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[48]", t); end
        chk = chk + 1; if (n__o_ctl[49] !== o__o_ctl[49]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[49]", t); end
        chk = chk + 1; if (n__o_ctl[50] !== o__o_ctl[50]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[50]", t); end
        chk = chk + 1; if (n__o_ctl[51] !== o__o_ctl[51]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[51]", t); end
        chk = chk + 1; if (n__o_ctl[52] !== o__o_ctl[52]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[52]", t); end
        chk = chk + 1; if (n__o_ctl[53] !== o__o_ctl[53]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[53]", t); end
        chk = chk + 1; if (n__o_ctl[54] !== o__o_ctl[54]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[54]", t); end
        chk = chk + 1; if (n__o_ctl[55] !== o__o_ctl[55]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[55]", t); end
        chk = chk + 1; if (n__o_ctl[56] !== o__o_ctl[56]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[56]", t); end
        chk = chk + 1; if (n__o_ctl[57] !== o__o_ctl[57]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[57]", t); end
        chk = chk + 1; if (n__o_ctl[58] !== o__o_ctl[58]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[58]", t); end
        chk = chk + 1; if (n__o_ctl[59] !== o__o_ctl[59]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[59]", t); end
        chk = chk + 1; if (n__o_ctl[60] !== o__o_ctl[60]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[60]", t); end
        chk = chk + 1; if (n__o_ctl[61] !== o__o_ctl[61]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[61]", t); end
        chk = chk + 1; if (n__o_ctl[62] !== o__o_ctl[62]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[62]", t); end
        chk = chk + 1; if (n__o_ctl[63] !== o__o_ctl[63]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[63]", t); end
        chk = chk + 1; if (n__o_ctl[64] !== o__o_ctl[64]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[64]", t); end
        chk = chk + 1; if (n__o_ctl[65] !== o__o_ctl[65]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[65]", t); end
        chk = chk + 1; if (n__o_ctl[66] !== o__o_ctl[66]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[66]", t); end
        chk = chk + 1; if (n__o_ctl[67] !== o__o_ctl[67]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[67]", t); end
        chk = chk + 1; if (n__o_ctl[68] !== o__o_ctl[68]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[68]", t); end
        chk = chk + 1; if (n__o_ctl[69] !== o__o_ctl[69]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[69]", t); end
        chk = chk + 1; if (n__o_ctl[70] !== o__o_ctl[70]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[70]", t); end
        chk = chk + 1; if (n__o_ctl[71] !== o__o_ctl[71]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[71]", t); end
        chk = chk + 1; if (n__o_ctl[72] !== o__o_ctl[72]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[72]", t); end
        chk = chk + 1; if (n__o_ctl[73] !== o__o_ctl[73]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[73]", t); end
        chk = chk + 1; if (n__o_ctl[74] !== o__o_ctl[74]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[74]", t); end
        chk = chk + 1; if (n__o_ctl[75] !== o__o_ctl[75]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[75]", t); end
        chk = chk + 1; if (n__o_ctl[76] !== o__o_ctl[76]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[76]", t); end
        chk = chk + 1; if (n__o_ctl[77] !== o__o_ctl[77]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[77]", t); end
        chk = chk + 1; if (n__o_ctl[78] !== o__o_ctl[78]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[78]", t); end
        chk = chk + 1; if (n__o_ctl[79] !== o__o_ctl[79]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[79]", t); end
        chk = chk + 1; if (n__o_ctl[80] !== o__o_ctl[80]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[80]", t); end
        chk = chk + 1; if (n__o_ctl[81] !== o__o_ctl[81]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[81]", t); end
        chk = chk + 1; if (n__o_ctl[82] !== o__o_ctl[82]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[82]", t); end
        chk = chk + 1; if (n__o_ctl[83] !== o__o_ctl[83]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[83]", t); end
        chk = chk + 1; if (n__o_ctl[84] !== o__o_ctl[84]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[84]", t); end
        chk = chk + 1; if (n__o_ctl[85] !== o__o_ctl[85]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[85]", t); end
        chk = chk + 1; if (n__o_ctl[86] !== o__o_ctl[86]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[86]", t); end
        chk = chk + 1; if (n__o_ctl[87] !== o__o_ctl[87]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[87]", t); end
        chk = chk + 1; if (n__o_ctl[88] !== o__o_ctl[88]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[88]", t); end
        chk = chk + 1; if (n__o_ctl[89] !== o__o_ctl[89]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[89]", t); end
        chk = chk + 1; if (n__o_ctl[90] !== o__o_ctl[90]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[90]", t); end
        chk = chk + 1; if (n__o_ctl[91] !== o__o_ctl[91]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[91]", t); end
        chk = chk + 1; if (n__o_ctl[92] !== o__o_ctl[92]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[92]", t); end
        chk = chk + 1; if (n__o_ctl[93] !== o__o_ctl[93]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[93]", t); end
        chk = chk + 1; if (n__o_ctl[94] !== o__o_ctl[94]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[94]", t); end
        chk = chk + 1; if (n__o_ctl[95] !== o__o_ctl[95]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[95]", t); end
        chk = chk + 1; if (n__o_ctl[96] !== o__o_ctl[96]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[96]", t); end
        chk = chk + 1; if (n__o_ctl[97] !== o__o_ctl[97]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[97]", t); end
        chk = chk + 1; if (n__o_ctl[98] !== o__o_ctl[98]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[98]", t); end
        chk = chk + 1; if (n__o_ctl[99] !== o__o_ctl[99]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[99]", t); end
        chk = chk + 1; if (n__o_ctl[100] !== o__o_ctl[100]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[100]", t); end
        chk = chk + 1; if (n__o_ctl[101] !== o__o_ctl[101]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[101]", t); end
        chk = chk + 1; if (n__o_ctl[102] !== o__o_ctl[102]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[102]", t); end
        chk = chk + 1; if (n__o_ctl[103] !== o__o_ctl[103]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[103]", t); end
        chk = chk + 1; if (n__o_ctl[104] !== o__o_ctl[104]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[104]", t); end
        chk = chk + 1; if (n__o_ctl[105] !== o__o_ctl[105]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[105]", t); end
        chk = chk + 1; if (n__o_ctl[106] !== o__o_ctl[106]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[106]", t); end
        chk = chk + 1; if (n__o_ctl[107] !== o__o_ctl[107]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[107]", t); end
        chk = chk + 1; if (n__o_ctl[108] !== o__o_ctl[108]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[108]", t); end
        chk = chk + 1; if (n__o_ctl[109] !== o__o_ctl[109]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[109]", t); end
        chk = chk + 1; if (n__o_ctl[110] !== o__o_ctl[110]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[110]", t); end
        chk = chk + 1; if (n__o_ctl[111] !== o__o_ctl[111]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[111]", t); end
        chk = chk + 1; if (n__o_ctl[112] !== o__o_ctl[112]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[112]", t); end
        chk = chk + 1; if (n__o_ctl[113] !== o__o_ctl[113]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[113]", t); end
        chk = chk + 1; if (n__o_ctl[114] !== o__o_ctl[114]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[114]", t); end
        chk = chk + 1; if (n__o_ctl[115] !== o__o_ctl[115]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[115]", t); end
        chk = chk + 1; if (n__o_ctl[116] !== o__o_ctl[116]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[116]", t); end
        chk = chk + 1; if (n__o_ctl[117] !== o__o_ctl[117]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[117]", t); end
        chk = chk + 1; if (n__o_ctl[118] !== o__o_ctl[118]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[118]", t); end
        chk = chk + 1; if (n__o_ctl[119] !== o__o_ctl[119]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[119]", t); end
        chk = chk + 1; if (n__o_ctl[120] !== o__o_ctl[120]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[120]", t); end
        chk = chk + 1; if (n__o_ctl[121] !== o__o_ctl[121]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[121]", t); end
        chk = chk + 1; if (n__o_ctl[122] !== o__o_ctl[122]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[122]", t); end
        chk = chk + 1; if (n__o_ctl[123] !== o__o_ctl[123]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[123]", t); end
        chk = chk + 1; if (n__o_ctl[124] !== o__o_ctl[124]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[124]", t); end
        chk = chk + 1; if (n__o_ctl[125] !== o__o_ctl[125]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[125]", t); end
        chk = chk + 1; if (n__o_ctl[126] !== o__o_ctl[126]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[126]", t); end
        chk = chk + 1; if (n__o_ctl[127] !== o__o_ctl[127]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[127]", t); end
        chk = chk + 1; if (n__o_ctl[128] !== o__o_ctl[128]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[128]", t); end
        chk = chk + 1; if (n__o_ctl[129] !== o__o_ctl[129]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[129]", t); end
        chk = chk + 1; if (n__o_ctl[130] !== o__o_ctl[130]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[130]", t); end
        chk = chk + 1; if (n__o_ctl[131] !== o__o_ctl[131]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[131]", t); end
        chk = chk + 1; if (n__o_ctl[132] !== o__o_ctl[132]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[132]", t); end
        chk = chk + 1; if (n__o_ctl[133] !== o__o_ctl[133]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[133]", t); end
        chk = chk + 1; if (n__o_ctl[134] !== o__o_ctl[134]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[134]", t); end
        chk = chk + 1; if (n__o_ctl[135] !== o__o_ctl[135]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[135]", t); end
        chk = chk + 1; if (n__o_ctl[136] !== o__o_ctl[136]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[136]", t); end
        chk = chk + 1; if (n__o_ctl[137] !== o__o_ctl[137]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[137]", t); end
        chk = chk + 1; if (n__o_ctl[138] !== o__o_ctl[138]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[138]", t); end
        chk = chk + 1; if (n__o_ctl[139] !== o__o_ctl[139]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[139]", t); end
        chk = chk + 1; if (n__o_ctl[140] !== o__o_ctl[140]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[140]", t); end
        chk = chk + 1; if (n__o_ctl[141] !== o__o_ctl[141]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[141]", t); end
        chk = chk + 1; if (n__o_ctl[142] !== o__o_ctl[142]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[142]", t); end
        chk = chk + 1; if (n__o_ctl[143] !== o__o_ctl[143]) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d out o_ctl[143]", t); end
        if (n__o_ctl != 0) act = act + 1;
        chk = chk + 1; if (u_old.u_af.ck !== u_new.u_af.ck) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_af.ck", t); end
        chk = chk + 1; if (u_old.u_af.rst_n !== u_new.u_af.rst_n) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_af.rst_n", t); end
        chk = chk + 1; if (u_old.u_af.fault_in !== u_new.u_af.fault_in) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_af.fault_in", t); end
        chk = chk + 1; if (u_old.u_bcdc0.ck !== u_new.u_bcdc0.ck) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc0.ck", t); end
        chk = chk + 1; if (u_old.u_bcdc0.rst_n !== u_new.u_bcdc0.rst_n) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc0.rst_n", t); end
        chk = chk + 1; if (u_old.u_bcdc0.hck !== u_new.u_bcdc0.hck) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc0.hck", t); end
        chk = chk + 1; if (u_old.u_bcdc0.hrst_n !== u_new.u_bcdc0.hrst_n) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc0.hrst_n", t); end
        chk = chk + 1; if (u_old.u_bcdc0.cfg_we !== u_new.u_bcdc0.cfg_we) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc0.cfg_we", t); end
        chk = chk + 1; if (u_old.u_bcdc0.cfg_addr !== u_new.u_bcdc0.cfg_addr) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc0.cfg_addr", t); end
        chk = chk + 1; if (u_old.u_bcdc0.cfg_data !== u_new.u_bcdc0.cfg_data) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc0.cfg_data", t); end
        chk = chk + 1; if (u_old.u_bcdc0.cfg_last !== u_new.u_bcdc0.cfg_last) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc0.cfg_last", t); end
        chk = chk + 1; if (u_old.u_bcdc1.ck !== u_new.u_bcdc1.ck) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc1.ck", t); end
        chk = chk + 1; if (u_old.u_bcdc1.rst_n !== u_new.u_bcdc1.rst_n) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc1.rst_n", t); end
        chk = chk + 1; if (u_old.u_bcdc1.hck !== u_new.u_bcdc1.hck) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc1.hck", t); end
        chk = chk + 1; if (u_old.u_bcdc1.hrst_n !== u_new.u_bcdc1.hrst_n) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc1.hrst_n", t); end
        chk = chk + 1; if (u_old.u_bcdc1.cfg_we !== u_new.u_bcdc1.cfg_we) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc1.cfg_we", t); end
        chk = chk + 1; if (u_old.u_bcdc1.cfg_addr !== u_new.u_bcdc1.cfg_addr) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc1.cfg_addr", t); end
        chk = chk + 1; if (u_old.u_bcdc1.cfg_data !== u_new.u_bcdc1.cfg_data) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc1.cfg_data", t); end
        chk = chk + 1; if (u_old.u_bcdc1.cfg_last !== u_new.u_bcdc1.cfg_last) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc1.cfg_last", t); end
        chk = chk + 1; if (u_old.u_bcdc2.ck !== u_new.u_bcdc2.ck) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc2.ck", t); end
        chk = chk + 1; if (u_old.u_bcdc2.rst_n !== u_new.u_bcdc2.rst_n) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc2.rst_n", t); end
        chk = chk + 1; if (u_old.u_bcdc2.hck !== u_new.u_bcdc2.hck) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc2.hck", t); end
        chk = chk + 1; if (u_old.u_bcdc2.hrst_n !== u_new.u_bcdc2.hrst_n) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc2.hrst_n", t); end
        chk = chk + 1; if (u_old.u_bcdc2.cfg_we !== u_new.u_bcdc2.cfg_we) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc2.cfg_we", t); end
        chk = chk + 1; if (u_old.u_bcdc2.cfg_addr !== u_new.u_bcdc2.cfg_addr) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc2.cfg_addr", t); end
        chk = chk + 1; if (u_old.u_bcdc2.cfg_data !== u_new.u_bcdc2.cfg_data) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc2.cfg_data", t); end
        chk = chk + 1; if (u_old.u_bcdc2.cfg_last !== u_new.u_bcdc2.cfg_last) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc2.cfg_last", t); end
        chk = chk + 1; if (u_old.u_bcdc3.ck !== u_new.u_bcdc3.ck) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc3.ck", t); end
        chk = chk + 1; if (u_old.u_bcdc3.rst_n !== u_new.u_bcdc3.rst_n) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc3.rst_n", t); end
        chk = chk + 1; if (u_old.u_bcdc3.hck !== u_new.u_bcdc3.hck) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc3.hck", t); end
        chk = chk + 1; if (u_old.u_bcdc3.hrst_n !== u_new.u_bcdc3.hrst_n) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc3.hrst_n", t); end
        chk = chk + 1; if (u_old.u_bcdc3.cfg_we !== u_new.u_bcdc3.cfg_we) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc3.cfg_we", t); end
        chk = chk + 1; if (u_old.u_bcdc3.cfg_addr !== u_new.u_bcdc3.cfg_addr) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc3.cfg_addr", t); end
        chk = chk + 1; if (u_old.u_bcdc3.cfg_data !== u_new.u_bcdc3.cfg_data) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc3.cfg_data", t); end
        chk = chk + 1; if (u_old.u_bcdc3.cfg_last !== u_new.u_bcdc3.cfg_last) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdc3.cfg_last", t); end
        chk = chk + 1; if (u_old.u_bcdcf.ck !== u_new.u_bcdcf.ck) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdcf.ck", t); end
        chk = chk + 1; if (u_old.u_bcdcf.rst_n !== u_new.u_bcdcf.rst_n) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdcf.rst_n", t); end
        chk = chk + 1; if (u_old.u_bcdcf.hck !== u_new.u_bcdcf.hck) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdcf.hck", t); end
        chk = chk + 1; if (u_old.u_bcdcf.hrst_n !== u_new.u_bcdcf.hrst_n) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdcf.hrst_n", t); end
        chk = chk + 1; if (u_old.u_bcdcf.cfg_we !== u_new.u_bcdcf.cfg_we) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdcf.cfg_we", t); end
        chk = chk + 1; if (u_old.u_bcdcf.cfg_addr !== u_new.u_bcdcf.cfg_addr) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdcf.cfg_addr", t); end
        chk = chk + 1; if (u_old.u_bcdcf.cfg_data !== u_new.u_bcdcf.cfg_data) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdcf.cfg_data", t); end
        chk = chk + 1; if (u_old.u_bcdcf.cfg_last !== u_new.u_bcdcf.cfg_last) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_bcdcf.cfg_last", t); end
        chk = chk + 1; if (u_old.u_cf1.ck !== u_new.u_cf1.ck) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_cf1.ck", t); end
        chk = chk + 1; if (u_old.u_cf1.rst_n !== u_new.u_cf1.rst_n) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_cf1.rst_n", t); end
        chk = chk + 1; if (u_old.u_cf1.fault_in !== u_new.u_cf1.fault_in) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_cf1.fault_in", t); end
        chk = chk + 1; if (u_old.u_drain.ck !== u_new.u_drain.ck) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_drain.ck", t); end
        chk = chk + 1; if (u_old.u_drain.rst_n !== u_new.u_drain.rst_n) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_drain.rst_n", t); end
        chk = chk + 1; if (u_old.u_drain.ctrl_idle_core !== u_new.u_drain.ctrl_idle_core) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_drain.ctrl_idle_core", t); end
        chk = chk + 1; if (u_old.u_drain.ring_idle_core !== u_new.u_drain.ring_idle_core) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_drain.ring_idle_core", t); end
        chk = chk + 1; if (u_old.u_drain.ctrl_idle_hbm !== u_new.u_drain.ctrl_idle_hbm) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_drain.ctrl_idle_hbm", t); end
        chk = chk + 1; if (u_old.u_drain.front_idle_hbm !== u_new.u_drain.front_idle_hbm) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_drain.front_idle_hbm", t); end
        chk = chk + 1; if (u_old.u_drain.ring_idle_hbm !== u_new.u_drain.ring_idle_hbm) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_drain.ring_idle_hbm", t); end
        chk = chk + 1; if (u_old.u_drain.ctrl_fault_core !== u_new.u_drain.ctrl_fault_core) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_drain.ctrl_fault_core", t); end
        chk = chk + 1; if (u_old.u_drain.ctrl_completion_fault_core !== u_new.u_drain.ctrl_completion_fault_core) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_drain.ctrl_completion_fault_core", t); end
        chk = chk + 1; if (u_old.u_drain.ctrl_intake_fault_core !== u_new.u_drain.ctrl_intake_fault_core) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_drain.ctrl_intake_fault_core", t); end
        chk = chk + 1; if (u_old.u_drain.ring_fault_core !== u_new.u_drain.ring_fault_core) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_drain.ring_fault_core", t); end
        chk = chk + 1; if (u_old.u_drain.ctrl_fault_hbm !== u_new.u_drain.ctrl_fault_hbm) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_drain.ctrl_fault_hbm", t); end
        chk = chk + 1; if (u_old.u_drain.ctrl_output_fault_hbm !== u_new.u_drain.ctrl_output_fault_hbm) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_drain.ctrl_output_fault_hbm", t); end
        chk = chk + 1; if (u_old.u_drain.ctrl_calendar_fault_hbm !== u_new.u_drain.ctrl_calendar_fault_hbm) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_drain.ctrl_calendar_fault_hbm", t); end
        chk = chk + 1; if (u_old.u_drain.ring_fault_hbm !== u_new.u_drain.ring_fault_hbm) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_drain.ring_fault_hbm", t); end
        chk = chk + 1; if (u_old.u_drain.front_fault_overflow_hbm !== u_new.u_drain.front_fault_overflow_hbm) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_drain.front_fault_overflow_hbm", t); end
        chk = chk + 1; if (u_old.u_drain.front_fault_go_hbm !== u_new.u_drain.front_fault_go_hbm) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_drain.front_fault_go_hbm", t); end
        chk = chk + 1; if (u_old.u_drain.front_hold_hbm !== u_new.u_drain.front_hold_hbm) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_drain.front_hold_hbm", t); end
        chk = chk + 1; if (u_old.u_drain.upstream_quiet !== u_new.u_drain.upstream_quiet) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_drain.upstream_quiet", t); end
        chk = chk + 1; if (u_old.u_drain.upstream_fault !== u_new.u_drain.upstream_fault) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_drain.upstream_fault", t); end
        chk = chk + 1; if (u_old.u_fcal.hck !== u_new.u_fcal.hck) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_fcal.hck", t); end
        chk = chk + 1; if (u_old.u_fcal.rst_n !== u_new.u_fcal.rst_n) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_fcal.rst_n", t); end
        chk = chk + 1; if (u_old.u_fcal.cfg_we !== u_new.u_fcal.cfg_we) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_fcal.cfg_we", t); end
        chk = chk + 1; if (u_old.u_fcal.cfg_addr !== u_new.u_fcal.cfg_addr) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_fcal.cfg_addr", t); end
        chk = chk + 1; if (u_old.u_fcal.cfg_data !== u_new.u_fcal.cfg_data) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_fcal.cfg_data", t); end
        chk = chk + 1; if (u_old.u_fcal.kgo_h !== u_new.u_fcal.kgo_h) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_fcal.kgo_h", t); end
        chk = chk + 1; if (u_old.u_fcal.vgo_h !== u_new.u_fcal.vgo_h) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_fcal.vgo_h", t); end
        chk = chk + 1; if (u_old.u_fcal.ctx_t !== u_new.u_fcal.ctx_t) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_fcal.ctx_t", t); end
        chk = chk + 1; if (u_old.u_lcal.ck !== u_new.u_lcal.ck) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_lcal.ck", t); end
        chk = chk + 1; if (u_old.u_lcal.rst_n !== u_new.u_lcal.rst_n) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_lcal.rst_n", t); end
        chk = chk + 1; if (u_old.u_lcal.cfg_we !== u_new.u_lcal.cfg_we) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_lcal.cfg_we", t); end
        chk = chk + 1; if (u_old.u_lcal.cfg_addr !== u_new.u_lcal.cfg_addr) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_lcal.cfg_addr", t); end
        chk = chk + 1; if (u_old.u_lcal.cfg_data !== u_new.u_lcal.cfg_data) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_lcal.cfg_data", t); end
        chk = chk + 1; if (u_old.u_lcal.kgo !== u_new.u_lcal.kgo) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_lcal.kgo", t); end
        chk = chk + 1; if (u_old.u_lcal.vgo !== u_new.u_lcal.vgo) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_lcal.vgo", t); end
        chk = chk + 1; if (u_old.u_lcal.ctx_t !== u_new.u_lcal.ctx_t) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_lcal.ctx_t", t); end
        chk = chk + 1; if (u_old.u_lcal.epoch !== u_new.u_lcal.epoch) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_lcal.epoch", t); end
        chk = chk + 1; if (u_old.u_lcal.layer !== u_new.u_lcal.layer) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_lcal.layer", t); end
        chk = chk + 1; if (u_old.u_phase.ck !== u_new.u_phase.ck) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_phase.ck", t); end
        chk = chk + 1; if (u_old.u_phase.rst_n !== u_new.u_phase.rst_n) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_phase.rst_n", t); end
        chk = chk + 1; if (u_old.u_phase.hck !== u_new.u_phase.hck) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_phase.hck", t); end
        chk = chk + 1; if (u_old.u_phase.hrst_n !== u_new.u_phase.hrst_n) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_phase.hrst_n", t); end
        chk = chk + 1; if (u_old.u_phase.ctrl_go !== u_new.u_phase.ctrl_go) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_phase.ctrl_go", t); end
        chk = chk + 1; if (u_old.u_phase.kgo !== u_new.u_phase.kgo) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_phase.kgo", t); end
        chk = chk + 1; if (u_old.u_phase.vgo !== u_new.u_phase.vgo) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_phase.vgo", t); end
        chk = chk + 1; if (u_old.u_phase.ctx_t !== u_new.u_phase.ctx_t) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_phase.ctx_t", t); end
        chk = chk + 1; if (u_old.u_phase.epoch !== u_new.u_phase.epoch) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_phase.epoch", t); end
        chk = chk + 1; if (u_old.u_phase.layer !== u_new.u_phase.layer) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_phase.layer", t); end
        chk = chk + 1; if (u_old.u_slg.ck !== u_new.u_slg.ck) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.ck", t); end
        chk = chk + 1; if (u_old.u_slg.rst_n !== u_new.u_slg.rst_n) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.rst_n", t); end
        chk = chk + 1; if (u_old.u_slg.cfg_stack !== u_new.u_slg.cfg_stack) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.cfg_stack", t); end
        chk = chk + 1; if (u_old.u_slg.cfg_group !== u_new.u_slg.cfg_group) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.cfg_group", t); end
        chk = chk + 1; if (u_old.u_slg.arm !== u_new.u_slg.arm) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.arm", t); end
        chk = chk + 1; if (u_old.u_slg.epoch !== u_new.u_slg.epoch) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.epoch", t); end
        chk = chk + 1; if (u_old.u_slg.layer !== u_new.u_slg.layer) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.layer", t); end
        chk = chk + 1; if (u_old.u_slg.expected_put !== u_new.u_slg.expected_put) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.expected_put", t); end
        chk = chk + 1; if (u_old.u_slg.expected_sector !== u_new.u_slg.expected_sector) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.expected_sector", t); end
        chk = chk + 1; if (u_old.u_slg.actual_valid !== u_new.u_slg.actual_valid) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.actual_valid", t); end
        chk = chk + 1; if (u_old.u_slg.actual_sector !== u_new.u_slg.actual_sector) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.actual_sector", t); end
        chk = chk + 1; if (u_old.u_slg.actual_epoch !== u_new.u_slg.actual_epoch) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.actual_epoch", t); end
        chk = chk + 1; if (u_old.u_slg.actual_layer !== u_new.u_slg.actual_layer) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.actual_layer", t); end
        chk = chk + 1; if (u_old.u_slg.actual_data !== u_new.u_slg.actual_data) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.actual_data", t); end
        chk = chk + 1; if (u_old.u_slg.req_valid !== u_new.u_slg.req_valid) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.req_valid", t); end
        chk = chk + 1; if (u_old.u_slg.req_t !== u_new.u_slg.req_t) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.req_t", t); end
        chk = chk + 1; if (u_old.u_slg.req_v !== u_new.u_slg.req_v) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.req_v", t); end
        chk = chk + 1; if (u_old.u_slg.req_epoch !== u_new.u_slg.req_epoch) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.req_epoch", t); end
        chk = chk + 1; if (u_old.u_slg.req_layer !== u_new.u_slg.req_layer) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.req_layer", t); end
        chk = chk + 1; if (u_old.u_slg.vreq_valid !== u_new.u_slg.vreq_valid) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.vreq_valid", t); end
        chk = chk + 1; if (u_old.u_slg.vreq_t !== u_new.u_slg.vreq_t) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0d child u_slg.vreq_t", t); end
        if ((h2 ^ o__o_ctl) & 144'b000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000101101101101101) nland = nland + 1;
      end
      h2 = h1; h1 = o__o_ctl;
    end
    if (bad == 0) $display("KVS_DOMSPLIT PASS tile=grp edges=2000 checks=%0d active_out=%0d split_ports=16 child_inputs=115 forced=68 landed_bits=10 landed_changes=%0d errors=0 mut=0 vs=unsplit_tile", chk, act, nland);
    else $display("KVS_DOMSPLIT FAIL tile=grp edges=2000 checks=%0d errors=%0d mut=0 (none)", chk, bad);
    $finish;
  end
endmodule
