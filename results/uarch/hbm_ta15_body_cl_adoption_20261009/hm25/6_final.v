module ot_hbm_production_clock_digital_body (aon_clk,
    bist_done,
    bist_pass,
    clk_hbm,
    clk_link,
    clk_serial,
    clk_stream,
    cmd_reset_serial_n,
    cmd_reset_stream_n,
    coll_reset_serial_n,
    coll_reset_stream_n,
    fatal_error,
    pll_lock,
    pll_reset_n,
    por_n,
    power_good,
    ready,
    requalify,
    link_reset_n,
    links_ready,
    phy_ready,
    phy_reset_n,
    state);
 input aon_clk;
 input bist_done;
 input bist_pass;
 input clk_hbm;
 input clk_link;
 input clk_serial;
 input clk_stream;
 output cmd_reset_serial_n;
 output cmd_reset_stream_n;
 output coll_reset_serial_n;
 output coll_reset_stream_n;
 input fatal_error;
 input pll_lock;
 output pll_reset_n;
 input por_n;
 input power_good;
 output ready;
 input requalify;
 output [8:0] link_reset_n;
 input [8:0] links_ready;
 input [3:0] phy_ready;
 output [3:0] phy_reset_n;
 output [3:0] state;

 wire _000_;
 wire _001_;
 wire _002_;
 wire _003_;
 wire _004_;
 wire _005_;
 wire _006_;
 wire _007_;
 wire _008_;
 wire _009_;
 wire _010_;
 wire _011_;
 wire _012_;
 wire _013_;
 wire _014_;
 wire _015_;
 wire _016_;
 wire _017_;
 wire _018_;
 wire _019_;
 wire _020_;
 wire _021_;
 wire _022_;
 wire _023_;
 wire _024_;
 wire _025_;
 wire _026_;
 wire _027_;
 wire _028_;
 wire _029_;
 wire _030_;
 wire _031_;
 wire _032_;
 wire _033_;
 wire _034_;
 wire _035_;
 wire _036_;
 wire _037_;
 wire _038_;
 wire _039_;
 wire _040_;
 wire _041_;
 wire _042_;
 wire _043_;
 wire _044_;
 wire _045_;
 wire _046_;
 wire _047_;
 wire _048_;
 wire _049_;
 wire _050_;
 wire _051_;
 wire _052_;
 wire _053_;
 wire _054_;
 wire _055_;
 wire _056_;
 wire _057_;
 wire _058_;
 wire _059_;
 wire _060_;
 wire _061_;
 wire _062_;
 wire _063_;
 wire _064_;
 wire _065_;
 wire _066_;
 wire _067_;
 wire _068_;
 wire _069_;
 wire _073_;
 wire _074_;
 wire _075_;
 wire _076_;
 wire _077_;
 wire _078_;
 wire _079_;
 wire _080_;
 wire _081_;
 wire _082_;
 wire _083_;
 wire _084_;
 wire _085_;
 wire _086_;
 wire _087_;
 wire _088_;
 wire _089_;
 wire _090_;
 wire _091_;
 wire _092_;
 wire _093_;
 wire _094_;
 wire _095_;
 wire _096_;
 wire _097_;
 wire _098_;
 wire _099_;
 wire _100_;
 wire _101_;
 wire _102_;
 wire _103_;
 wire _104_;
 wire _105_;
 wire _107_;
 wire _108_;
 wire _109_;
 wire _110_;
 wire net1;
 wire net80;
 wire net81;
 wire net100;
 wire net101;
 wire net102;
 wire net103;
 wire \collars.cmd_serial.async_reset_n ;
 wire \collars.cmd_serial.sync_q[0] ;
 wire \collars.cmd_serial.sync_q[1] ;
 wire \collars.cmd_stream.sync_q[0] ;
 wire \collars.cmd_stream.sync_q[1] ;
 wire \collars.coll_serial.async_reset_n ;
 wire \collars.coll_serial.sync_q[0] ;
 wire \collars.coll_serial.sync_q[1] ;
 wire \collars.coll_stream.sync_q[0] ;
 wire \collars.coll_stream.sync_q[1] ;
 wire \collars.link[0].c.async_reset_n ;
 wire \collars.link[0].c.sync_q[0] ;
 wire \collars.link[0].c.sync_q[1] ;
 wire \collars.phy[0].c.async_reset_n ;
 wire \collars.phy[0].c.sync_q[0] ;
 wire \collars.phy[0].c.sync_q[1] ;
 wire net82;
 wire net104;
 wire net83;
 wire net84;
 wire net85;
 wire net86;
 wire net87;
 wire net88;
 wire net89;
 wire net90;
 wire net91;
 wire net92;
 wire net93;
 wire net94;
 wire net95;
 wire net105;
 wire net96;
 wire net106;
 wire net97;
 wire net98;
 wire net107;
 wire \rel_sync_q0[0] ;
 wire \rel_sync_q0[10] ;
 wire \rel_sync_q0[13] ;
 wire \rel_sync_q0[1] ;
 wire \rel_sync_q0[2] ;
 wire \rel_sync_q0[3] ;
 wire net99;
 wire \sequence_control.status_meta[0] ;
 wire \sequence_control.status_meta[10] ;
 wire \sequence_control.status_meta[11] ;
 wire \sequence_control.status_meta[12] ;
 wire \sequence_control.status_meta[13] ;
 wire \sequence_control.status_meta[14] ;
 wire \sequence_control.status_meta[15] ;
 wire \sequence_control.status_meta[16] ;
 wire \sequence_control.status_meta[1] ;
 wire \sequence_control.status_meta[2] ;
 wire \sequence_control.status_meta[3] ;
 wire \sequence_control.status_meta[4] ;
 wire \sequence_control.status_meta[5] ;
 wire \sequence_control.status_meta[6] ;
 wire \sequence_control.status_meta[7] ;
 wire \sequence_control.status_meta[8] ;
 wire \sequence_control.status_meta[9] ;
 wire net108;
 wire net109;
 wire net110;
 wire net2;
 wire net3;
 wire net4;
 wire net5;
 wire net6;
 wire net7;
 wire net8;
 wire net9;
 wire net10;
 wire net11;
 wire net12;
 wire net13;
 wire net14;
 wire net15;
 wire net16;
 wire net17;
 wire net18;
 wire net19;
 wire net20;
 wire net21;
 wire net22;
 wire net23;
 wire net24;
 wire net25;
 wire net26;
 wire net27;
 wire net28;
 wire net29;
 wire net30;
 wire net31;
 wire net32;
 wire net33;
 wire net34;
 wire net35;
 wire net36;
 wire net37;
 wire net38;
 wire net39;
 wire net40;
 wire net41;
 wire net42;
 wire net43;
 wire net44;
 wire net45;
 wire net46;
 wire net47;
 wire net48;
 wire net49;
 wire net50;
 wire net51;
 wire net52;
 wire net53;
 wire net54;
 wire net55;
 wire net56;
 wire net57;
 wire net58;
 wire net59;
 wire net60;
 wire net61;
 wire net62;
 wire net63;
 wire net64;
 wire net65;
 wire net66;
 wire net67;
 wire net68;
 wire net69;
 wire net70;
 wire net71;
 wire net72;
 wire net73;
 wire net74;
 wire net75;
 wire net76;
 wire net77;
 wire net78;
 wire net79;
 wire net115;
 wire net116;
 wire clknet_2_0__leaf_aon_clk;
 wire clknet_0_aon_clk;
 wire clknet_2_1__leaf_aon_clk;
 wire clknet_2_2__leaf_aon_clk;
 wire clknet_2_3__leaf_aon_clk;
 wire clknet_0_clk_stream;
 wire clknet_1_0__leaf_clk_stream;
 wire clknet_1_1__leaf_clk_stream;
 wire clknet_0_clk_serial;
 wire clknet_1_0__leaf_clk_serial;
 wire clknet_1_1__leaf_clk_serial;
 wire clknet_0_clk_hbm;
 wire clknet_1_0__leaf_clk_hbm;
 wire clknet_1_1__leaf_clk_hbm;
 wire clknet_0_clk_link;
 wire clknet_1_0__leaf_clk_link;
 wire clknet_1_1__leaf_clk_link;
 wire net117;
 wire net118;
 wire net119;
 wire net120;
 wire net121;
 wire net122;
 wire net123;
 wire net124;
 wire net125;
 wire net126;
 wire net127;
 wire net128;
 wire net129;
 wire net130;
 wire net131;
 wire net132;
 wire net133;
 wire net134;
 wire net135;
 wire net136;
 wire net137;
 wire net138;
 wire net139;
 wire net140;
 wire net141;
 wire net142;
 wire net143;
 wire net144;
 wire net145;
 wire net146;
 wire net147;
 wire net148;
 wire net149;
 wire net150;
 wire net151;
 wire net152;
 wire net153;
 wire net154;
 wire net155;
 wire net156;
 wire net157;
 wire net158;
 wire net159;
 wire net160;
 wire net161;
 wire net162;
 wire net163;
 wire net164;
 wire net165;
 wire net166;
 wire net167;
 wire net168;
 wire net169;
 wire net170;
 wire net171;
 wire net172;
 wire net173;
 wire net174;
 wire net175;
 wire net176;
 wire net177;
 wire net178;
 wire net179;
 wire net180;
 wire net181;
 wire net182;
 wire net183;
 wire net184;
 wire net185;
 wire net186;
 wire net187;
 wire net188;
 wire net189;
 wire net190;
 wire net191;
 wire net192;
 wire net193;
 wire net194;
 wire net195;
 wire net196;
 wire net197;

 INVx1_ASAP7_75t_R _113_ (.A(net151),
    .Y(\rel_sync_q0[3] ));
 INVx3_ASAP7_75t_R _115_ (.A(_001_),
    .Y(net108));
 INVx2_ASAP7_75t_R _116_ (.A(_002_),
    .Y(net109));
 INVx1_ASAP7_75t_R _117_ (.A(net173),
    .Y(\sequence_control.status_meta[3] ));
 INVx1_ASAP7_75t_R _118_ (.A(net143),
    .Y(\collars.cmd_stream.sync_q[0] ));
 INVx2_ASAP7_75t_R _120_ (.A(_000_),
    .Y(net110));
 INVx1_ASAP7_75t_R _121_ (.A(net131),
    .Y(\collars.cmd_serial.sync_q[0] ));
 INVx1_ASAP7_75t_R _122_ (.A(net137),
    .Y(\collars.phy[0].c.sync_q[0] ));
 INVx1_ASAP7_75t_R _123_ (.A(net155),
    .Y(\sequence_control.status_meta[13] ));
 INVx1_ASAP7_75t_R _124_ (.A(net153),
    .Y(\collars.link[0].c.sync_q[0] ));
 INVx1_ASAP7_75t_R _125_ (.A(_010_),
    .Y(\sequence_control.status_meta[15] ));
 INVx1_ASAP7_75t_R _126_ (.A(net165),
    .Y(\sequence_control.status_meta[14] ));
 INVx1_ASAP7_75t_R _127_ (.A(net139),
    .Y(\sequence_control.status_meta[0] ));
 INVx1_ASAP7_75t_R _128_ (.A(net145),
    .Y(\sequence_control.status_meta[1] ));
 INVx1_ASAP7_75t_R _129_ (.A(net169),
    .Y(\sequence_control.status_meta[2] ));
 INVx1_ASAP7_75t_R _130_ (.A(net167),
    .Y(\rel_sync_q0[10] ));
 OR4x1_ASAP7_75t_R _132_ (.A(_009_),
    .B(_042_),
    .C(_049_),
    .D(_053_),
    .Y(_073_));
 AND2x2_ASAP7_75t_R _133_ (.A(_001_),
    .B(net109),
    .Y(_074_));
 AND2x4_ASAP7_75t_R _134_ (.A(_001_),
    .B(_014_),
    .Y(_075_));
 AO21x1_ASAP7_75t_R _135_ (.A1(net108),
    .A2(_013_),
    .B(_075_),
    .Y(_076_));
 AO22x1_ASAP7_75t_R _136_ (.A1(_073_),
    .A2(_074_),
    .B1(_076_),
    .B2(_002_),
    .Y(_077_));
 AND3x1_ASAP7_75t_R _137_ (.A(net108),
    .B(net109),
    .C(_000_),
    .Y(_078_));
 OR4x1_ASAP7_75t_R _138_ (.A(_039_),
    .B(_040_),
    .C(_041_),
    .D(_043_),
    .Y(_079_));
 OR3x1_ASAP7_75t_R _139_ (.A(_035_),
    .B(_036_),
    .C(_038_),
    .Y(_080_));
 OR4x1_ASAP7_75t_R _140_ (.A(_047_),
    .B(_048_),
    .C(_079_),
    .D(_080_),
    .Y(_081_));
 NAND2x1_ASAP7_75t_R _141_ (.A(_001_),
    .B(net110),
    .Y(_082_));
 INVx1_ASAP7_75t_R _142_ (.A(net82),
    .Y(_083_));
 NOR2x1_ASAP7_75t_R _143_ (.A(_002_),
    .B(_014_),
    .Y(_084_));
 INVx1_ASAP7_75t_R _144_ (.A(_034_),
    .Y(_085_));
 AO32x1_ASAP7_75t_R _145_ (.A1(net99),
    .A2(_083_),
    .A3(_084_),
    .B1(_085_),
    .B2(_002_),
    .Y(_086_));
 OR5x1_ASAP7_75t_R _146_ (.A(_001_),
    .B(net109),
    .C(_000_),
    .D(_051_),
    .E(_073_),
    .Y(_087_));
 OAI22x1_ASAP7_75t_R _147_ (.A1(_082_),
    .A2(_086_),
    .B1(_081_),
    .B2(_087_),
    .Y(_088_));
 AO221x2_ASAP7_75t_R _148_ (.A1(_000_),
    .A2(_077_),
    .B1(_078_),
    .B2(_081_),
    .C(_088_),
    .Y(_089_));
 NAND2x1_ASAP7_75t_R _149_ (.A(_002_),
    .B(_089_),
    .Y(_090_));
 AND2x2_ASAP7_75t_R _150_ (.A(_002_),
    .B(net110),
    .Y(_091_));
 OR3x1_ASAP7_75t_R _151_ (.A(_001_),
    .B(_002_),
    .C(net110),
    .Y(_092_));
 AO21x1_ASAP7_75t_R _152_ (.A1(net109),
    .A2(_000_),
    .B(net108),
    .Y(_093_));
 AO221x1_ASAP7_75t_R _153_ (.A1(_051_),
    .A2(_091_),
    .B1(_092_),
    .B2(_093_),
    .C(_089_),
    .Y(_094_));
 XOR2x2_ASAP7_75t_R _154_ (.A(_002_),
    .B(_000_),
    .Y(_095_));
 AO21x1_ASAP7_75t_R _155_ (.A1(net108),
    .A2(_014_),
    .B(_095_),
    .Y(_096_));
 OR2x2_ASAP7_75t_R _156_ (.A(_013_),
    .B(_014_),
    .Y(_097_));
 AO21x2_ASAP7_75t_R _157_ (.A1(_096_),
    .A2(_097_),
    .B(net82),
    .Y(_098_));
 AO21x2_ASAP7_75t_R _158_ (.A1(_090_),
    .A2(_094_),
    .B(_098_),
    .Y(_067_));
 OA21x2_ASAP7_75t_R _159_ (.A1(net109),
    .A2(_051_),
    .B(net110),
    .Y(_099_));
 OR3x1_ASAP7_75t_R _160_ (.A(net108),
    .B(_089_),
    .C(_099_),
    .Y(_100_));
 NAND2x1_ASAP7_75t_R _161_ (.A(net108),
    .B(_089_),
    .Y(_101_));
 AOI21x1_ASAP7_75t_R _162_ (.A1(_100_),
    .A2(_101_),
    .B(_098_),
    .Y(_068_));
 OA21x2_ASAP7_75t_R _163_ (.A1(_002_),
    .A2(_081_),
    .B(_000_),
    .Y(_102_));
 NOR2x1_ASAP7_75t_R _164_ (.A(_074_),
    .B(_102_),
    .Y(_103_));
 OR3x1_ASAP7_75t_R _165_ (.A(_098_),
    .B(_088_),
    .C(_103_),
    .Y(_069_));
 INVx1_ASAP7_75t_R _166_ (.A(net135),
    .Y(\collars.coll_serial.sync_q[0] ));
 AND3x1_ASAP7_75t_R _167_ (.A(_001_),
    .B(_002_),
    .C(_000_),
    .Y(_104_));
 INVx1_ASAP7_75t_R _168_ (.A(_104_),
    .Y(_105_));
 OA211x2_ASAP7_75t_R _169_ (.A1(_002_),
    .A2(_000_),
    .B(net97),
    .C(_105_),
    .Y(net106));
 AND3x1_ASAP7_75t_R _171_ (.A(net116),
    .B(net96),
    .C(_095_),
    .Y(\collars.phy[0].c.async_reset_n ));
 OA211x2_ASAP7_75t_R _172_ (.A1(_091_),
    .A2(_078_),
    .B(net116),
    .C(net96),
    .Y(\collars.link[0].c.async_reset_n ));
 AND3x1_ASAP7_75t_R _173_ (.A(net116),
    .B(net96),
    .C(_091_),
    .Y(\collars.coll_serial.async_reset_n ));
 AND4x1_ASAP7_75t_R _174_ (.A(net108),
    .B(net96),
    .C(_091_),
    .D(net106),
    .Y(\collars.cmd_serial.async_reset_n ));
 INVx1_ASAP7_75t_R _175_ (.A(net177),
    .Y(net100));
 INVx1_ASAP7_75t_R _176_ (.A(net117),
    .Y(\collars.cmd_serial.sync_q[1] ));
 INVx1_ASAP7_75t_R _177_ (.A(net189),
    .Y(net101));
 INVx1_ASAP7_75t_R _178_ (.A(net121),
    .Y(\collars.cmd_stream.sync_q[1] ));
 INVx1_ASAP7_75t_R _179_ (.A(net191),
    .Y(net102));
 INVx1_ASAP7_75t_R _180_ (.A(net125),
    .Y(\collars.coll_serial.sync_q[1] ));
 INVx1_ASAP7_75t_R _181_ (.A(net187),
    .Y(net103));
 INVx1_ASAP7_75t_R _182_ (.A(net127),
    .Y(\collars.coll_stream.sync_q[1] ));
 INVx1_ASAP7_75t_R _183_ (.A(_032_),
    .Y(net104));
 INVx1_ASAP7_75t_R _184_ (.A(net119),
    .Y(\collars.link[0].c.sync_q[1] ));
 INVx1_ASAP7_75t_R _185_ (.A(net129),
    .Y(\collars.coll_stream.sync_q[0] ));
 INVx1_ASAP7_75t_R _186_ (.A(net133),
    .Y(\sequence_control.status_meta[4] ));
 INVx1_ASAP7_75t_R _187_ (.A(_045_),
    .Y(net105));
 INVx1_ASAP7_75t_R _188_ (.A(net123),
    .Y(\collars.phy[0].c.sync_q[1] ));
 INVx1_ASAP7_75t_R _189_ (.A(net141),
    .Y(\sequence_control.status_meta[16] ));
 NAND2x1_ASAP7_75t_R _190_ (.A(net116),
    .B(net96),
    .Y(_107_));
 OR4x1_ASAP7_75t_R _191_ (.A(_020_),
    .B(_021_),
    .C(_023_),
    .D(_058_),
    .Y(_108_));
 OR4x1_ASAP7_75t_R _192_ (.A(_001_),
    .B(net109),
    .C(_000_),
    .D(_108_),
    .Y(_109_));
 OR4x1_ASAP7_75t_R _193_ (.A(_012_),
    .B(_015_),
    .C(_107_),
    .D(_109_),
    .Y(_110_));
 INVx1_ASAP7_75t_R _194_ (.A(_110_),
    .Y(net107));
 INVx1_ASAP7_75t_R _195_ (.A(net171),
    .Y(\rel_sync_q0[13] ));
 INVx1_ASAP7_75t_R _196_ (.A(net147),
    .Y(\sequence_control.status_meta[9] ));
 INVx1_ASAP7_75t_R _197_ (.A(net157),
    .Y(\sequence_control.status_meta[8] ));
 INVx1_ASAP7_75t_R _198_ (.A(net181),
    .Y(\sequence_control.status_meta[12] ));
 INVx1_ASAP7_75t_R _199_ (.A(net159),
    .Y(\rel_sync_q0[2] ));
 INVx1_ASAP7_75t_R _200_ (.A(net183),
    .Y(\sequence_control.status_meta[6] ));
 INVx1_ASAP7_75t_R _201_ (.A(net163),
    .Y(\sequence_control.status_meta[5] ));
 INVx1_ASAP7_75t_R _202_ (.A(net175),
    .Y(\sequence_control.status_meta[10] ));
 INVx1_ASAP7_75t_R _203_ (.A(net179),
    .Y(\rel_sync_q0[0] ));
 INVx1_ASAP7_75t_R _204_ (.A(net161),
    .Y(\rel_sync_q0[1] ));
 INVx1_ASAP7_75t_R _205_ (.A(net185),
    .Y(\sequence_control.status_meta[7] ));
 INVx1_ASAP7_75t_R _206_ (.A(net149),
    .Y(\sequence_control.status_meta[11] ));
 TIELOx1_ASAP7_75t_R _222__1 (.L(state[3]));
 BUFx24_ASAP7_75t_R clkbuf_0_aon_clk (.A(aon_clk),
    .Y(clknet_0_aon_clk));
 BUFx24_ASAP7_75t_R clkbuf_0_clk_hbm (.A(clk_hbm),
    .Y(clknet_0_clk_hbm));
 BUFx24_ASAP7_75t_R clkbuf_0_clk_link (.A(clk_link),
    .Y(clknet_0_clk_link));
 BUFx24_ASAP7_75t_R clkbuf_0_clk_serial (.A(clk_serial),
    .Y(clknet_0_clk_serial));
 BUFx24_ASAP7_75t_R clkbuf_0_clk_stream (.A(clk_stream),
    .Y(clknet_0_clk_stream));
 BUFx24_ASAP7_75t_R clkbuf_1_0__f_clk_hbm (.A(clknet_0_clk_hbm),
    .Y(clknet_1_0__leaf_clk_hbm));
 BUFx24_ASAP7_75t_R clkbuf_1_0__f_clk_link (.A(clknet_0_clk_link),
    .Y(clknet_1_0__leaf_clk_link));
 BUFx24_ASAP7_75t_R clkbuf_1_0__f_clk_serial (.A(clknet_0_clk_serial),
    .Y(clknet_1_0__leaf_clk_serial));
 BUFx24_ASAP7_75t_R clkbuf_1_0__f_clk_stream (.A(clknet_0_clk_stream),
    .Y(clknet_1_0__leaf_clk_stream));
 BUFx24_ASAP7_75t_R clkbuf_1_1__f_clk_hbm (.A(clknet_0_clk_hbm),
    .Y(clknet_1_1__leaf_clk_hbm));
 BUFx24_ASAP7_75t_R clkbuf_1_1__f_clk_link (.A(clknet_0_clk_link),
    .Y(clknet_1_1__leaf_clk_link));
 BUFx24_ASAP7_75t_R clkbuf_1_1__f_clk_serial (.A(clknet_0_clk_serial),
    .Y(clknet_1_1__leaf_clk_serial));
 BUFx24_ASAP7_75t_R clkbuf_1_1__f_clk_stream (.A(clknet_0_clk_stream),
    .Y(clknet_1_1__leaf_clk_stream));
 BUFx24_ASAP7_75t_R clkbuf_2_0__f_aon_clk (.A(clknet_0_aon_clk),
    .Y(clknet_2_0__leaf_aon_clk));
 BUFx24_ASAP7_75t_R clkbuf_2_1__f_aon_clk (.A(clknet_0_aon_clk),
    .Y(clknet_2_1__leaf_aon_clk));
 BUFx24_ASAP7_75t_R clkbuf_2_2__f_aon_clk (.A(clknet_0_aon_clk),
    .Y(clknet_2_2__leaf_aon_clk));
 BUFx24_ASAP7_75t_R clkbuf_2_3__f_aon_clk (.A(clknet_0_aon_clk),
    .Y(clknet_2_3__leaf_aon_clk));
 INVx2_ASAP7_75t_R clkload0 (.A(clknet_2_0__leaf_aon_clk));
 INVx4_ASAP7_75t_R clkload1 (.A(clknet_2_1__leaf_aon_clk));
 INVx2_ASAP7_75t_R clkload2 (.A(clknet_2_3__leaf_aon_clk));
 BUFx2_ASAP7_75t_R clkload3 (.A(clknet_1_1__leaf_clk_hbm));
 BUFx2_ASAP7_75t_R clkload4 (.A(clknet_1_1__leaf_clk_link));
 DFFASRHQNx1_ASAP7_75t_R \collars.cmd_serial.sync_q[0]$_DFF_PN0_  (.CLK(clknet_1_1__leaf_clk_serial),
    .D(net1),
    .QN(_006_),
    .RESETN(\collars.cmd_serial.async_reset_n ),
    .SETN(net2));
 TIEHIx1_ASAP7_75t_R \collars.cmd_serial.sync_q[0]$_DFF_PN0__2  (.H(net1));
 TIEHIx1_ASAP7_75t_R \collars.cmd_serial.sync_q[0]$_DFF_PN0__3  (.H(net2));
 DFFASRHQNx1_ASAP7_75t_R \collars.cmd_serial.sync_q[1]$_DFF_PN0_  (.CLK(clknet_1_1__leaf_clk_serial),
    .D(net132),
    .QN(_025_),
    .RESETN(\collars.cmd_serial.async_reset_n ),
    .SETN(net3));
 TIEHIx1_ASAP7_75t_R \collars.cmd_serial.sync_q[1]$_DFF_PN0__4  (.H(net3));
 DFFASRHQNx1_ASAP7_75t_R \collars.cmd_serial.tree[0].q$_DFF_PN0_  (.CLK(clknet_1_1__leaf_clk_serial),
    .D(net4),
    .QN(_024_),
    .RESETN(net118),
    .SETN(net5));
 TIEHIx1_ASAP7_75t_R \collars.cmd_serial.tree[0].q$_DFF_PN0__5  (.H(net4));
 TIEHIx1_ASAP7_75t_R \collars.cmd_serial.tree[0].q$_DFF_PN0__6  (.H(net5));
 DFFASRHQNx1_ASAP7_75t_R \collars.cmd_stream.sync_q[0]$_DFF_PN0_  (.CLK(clknet_1_1__leaf_clk_stream),
    .D(net6),
    .QN(_005_),
    .RESETN(\collars.cmd_serial.async_reset_n ),
    .SETN(net7));
 TIEHIx1_ASAP7_75t_R \collars.cmd_stream.sync_q[0]$_DFF_PN0__7  (.H(net6));
 TIEHIx1_ASAP7_75t_R \collars.cmd_stream.sync_q[0]$_DFF_PN0__8  (.H(net7));
 DFFASRHQNx1_ASAP7_75t_R \collars.cmd_stream.sync_q[1]$_DFF_PN0_  (.CLK(clknet_1_1__leaf_clk_stream),
    .D(net144),
    .QN(_027_),
    .RESETN(\collars.cmd_serial.async_reset_n ),
    .SETN(net8));
 TIEHIx1_ASAP7_75t_R \collars.cmd_stream.sync_q[1]$_DFF_PN0__9  (.H(net8));
 DFFASRHQNx1_ASAP7_75t_R \collars.cmd_stream.tree[0].q$_DFF_PN0_  (.CLK(clknet_1_1__leaf_clk_stream),
    .D(net9),
    .QN(_026_),
    .RESETN(net122),
    .SETN(net10));
 TIEHIx1_ASAP7_75t_R \collars.cmd_stream.tree[0].q$_DFF_PN0__10  (.H(net9));
 TIEHIx1_ASAP7_75t_R \collars.cmd_stream.tree[0].q$_DFF_PN0__11  (.H(net10));
 DFFASRHQNx1_ASAP7_75t_R \collars.coll_serial.sync_q[0]$_DFF_PN0_  (.CLK(clknet_1_0__leaf_clk_serial),
    .D(net11),
    .QN(_022_),
    .RESETN(\collars.coll_serial.async_reset_n ),
    .SETN(net12));
 TIEHIx1_ASAP7_75t_R \collars.coll_serial.sync_q[0]$_DFF_PN0__12  (.H(net11));
 TIEHIx1_ASAP7_75t_R \collars.coll_serial.sync_q[0]$_DFF_PN0__13  (.H(net12));
 DFFASRHQNx1_ASAP7_75t_R \collars.coll_serial.sync_q[1]$_DFF_PN0_  (.CLK(clknet_1_0__leaf_clk_serial),
    .D(net136),
    .QN(_029_),
    .RESETN(\collars.coll_serial.async_reset_n ),
    .SETN(net13));
 TIEHIx1_ASAP7_75t_R \collars.coll_serial.sync_q[1]$_DFF_PN0__14  (.H(net13));
 DFFASRHQNx1_ASAP7_75t_R \collars.coll_serial.tree[0].q$_DFF_PN0_  (.CLK(clknet_1_0__leaf_clk_serial),
    .D(net14),
    .QN(_028_),
    .RESETN(net126),
    .SETN(net15));
 TIEHIx1_ASAP7_75t_R \collars.coll_serial.tree[0].q$_DFF_PN0__15  (.H(net14));
 TIEHIx1_ASAP7_75t_R \collars.coll_serial.tree[0].q$_DFF_PN0__16  (.H(net15));
 DFFASRHQNx1_ASAP7_75t_R \collars.coll_stream.sync_q[0]$_DFF_PN0_  (.CLK(clknet_1_0__leaf_clk_stream),
    .D(net16),
    .QN(_037_),
    .RESETN(\collars.coll_serial.async_reset_n ),
    .SETN(net17));
 TIEHIx1_ASAP7_75t_R \collars.coll_stream.sync_q[0]$_DFF_PN0__17  (.H(net16));
 TIEHIx1_ASAP7_75t_R \collars.coll_stream.sync_q[0]$_DFF_PN0__18  (.H(net17));
 DFFASRHQNx1_ASAP7_75t_R \collars.coll_stream.sync_q[1]$_DFF_PN0_  (.CLK(clknet_1_0__leaf_clk_stream),
    .D(net130),
    .QN(_031_),
    .RESETN(\collars.coll_serial.async_reset_n ),
    .SETN(net18));
 TIEHIx1_ASAP7_75t_R \collars.coll_stream.sync_q[1]$_DFF_PN0__19  (.H(net18));
 DFFASRHQNx1_ASAP7_75t_R \collars.coll_stream.tree[0].q$_DFF_PN0_  (.CLK(clknet_1_0__leaf_clk_stream),
    .D(net19),
    .QN(_030_),
    .RESETN(net128),
    .SETN(net20));
 TIEHIx1_ASAP7_75t_R \collars.coll_stream.tree[0].q$_DFF_PN0__20  (.H(net19));
 TIEHIx1_ASAP7_75t_R \collars.coll_stream.tree[0].q$_DFF_PN0__21  (.H(net20));
 DFFASRHQNx1_ASAP7_75t_R \collars.link[0].c.sync_q[0]$_DFF_PN0_  (.CLK(clknet_1_0__leaf_clk_link),
    .D(net21),
    .QN(_008_),
    .RESETN(\collars.link[0].c.async_reset_n ),
    .SETN(net22));
 TIEHIx1_ASAP7_75t_R \collars.link[0].c.sync_q[0]$_DFF_PN0__22  (.H(net21));
 TIEHIx1_ASAP7_75t_R \collars.link[0].c.sync_q[0]$_DFF_PN0__23  (.H(net22));
 DFFASRHQNx1_ASAP7_75t_R \collars.link[0].c.sync_q[1]$_DFF_PN0_  (.CLK(clknet_1_0__leaf_clk_link),
    .D(net154),
    .QN(_033_),
    .RESETN(\collars.link[0].c.async_reset_n ),
    .SETN(net23));
 TIEHIx1_ASAP7_75t_R \collars.link[0].c.sync_q[1]$_DFF_PN0__24  (.H(net23));
 DFFASRHQNx1_ASAP7_75t_R \collars.link[0].c.tree[0].q$_DFF_PN0_  (.CLK(clknet_1_1__leaf_clk_link),
    .D(net24),
    .QN(_032_),
    .RESETN(net120),
    .SETN(net25));
 TIEHIx1_ASAP7_75t_R \collars.link[0].c.tree[0].q$_DFF_PN0__25  (.H(net24));
 TIEHIx1_ASAP7_75t_R \collars.link[0].c.tree[0].q$_DFF_PN0__26  (.H(net25));
 DFFASRHQNx1_ASAP7_75t_R \collars.phy[0].c.sync_q[0]$_DFF_PN0_  (.CLK(clknet_1_1__leaf_clk_hbm),
    .D(net26),
    .QN(_007_),
    .RESETN(\collars.phy[0].c.async_reset_n ),
    .SETN(net27));
 TIEHIx1_ASAP7_75t_R \collars.phy[0].c.sync_q[0]$_DFF_PN0__27  (.H(net26));
 TIEHIx1_ASAP7_75t_R \collars.phy[0].c.sync_q[0]$_DFF_PN0__28  (.H(net27));
 DFFASRHQNx1_ASAP7_75t_R \collars.phy[0].c.sync_q[1]$_DFF_PN0_  (.CLK(clknet_1_0__leaf_clk_hbm),
    .D(net138),
    .QN(_046_),
    .RESETN(\collars.phy[0].c.async_reset_n ),
    .SETN(net28));
 TIEHIx1_ASAP7_75t_R \collars.phy[0].c.sync_q[1]$_DFF_PN0__29  (.H(net28));
 DFFASRHQNx1_ASAP7_75t_R \collars.phy[0].c.tree[0].q$_DFF_PN0_  (.CLK(clknet_1_0__leaf_clk_hbm),
    .D(net29),
    .QN(_045_),
    .RESETN(net124),
    .SETN(net30));
 TIEHIx1_ASAP7_75t_R \collars.phy[0].c.tree[0].q$_DFF_PN0__30  (.H(net29));
 TIEHIx1_ASAP7_75t_R \collars.phy[0].c.tree[0].q$_DFF_PN0__31  (.H(net30));
 BUFx2_ASAP7_75t_R hold129 (.A(net193),
    .Y(net117));
 BUFx2_ASAP7_75t_R hold130 (.A(\collars.cmd_serial.sync_q[1] ),
    .Y(net118));
 BUFx2_ASAP7_75t_R hold131 (.A(net194),
    .Y(net119));
 BUFx2_ASAP7_75t_R hold132 (.A(\collars.link[0].c.sync_q[1] ),
    .Y(net120));
 BUFx2_ASAP7_75t_R hold133 (.A(net195),
    .Y(net121));
 BUFx2_ASAP7_75t_R hold134 (.A(\collars.cmd_stream.sync_q[1] ),
    .Y(net122));
 BUFx2_ASAP7_75t_R hold135 (.A(net196),
    .Y(net123));
 BUFx2_ASAP7_75t_R hold136 (.A(\collars.phy[0].c.sync_q[1] ),
    .Y(net124));
 BUFx2_ASAP7_75t_R hold137 (.A(net197),
    .Y(net125));
 BUFx2_ASAP7_75t_R hold138 (.A(\collars.coll_serial.sync_q[1] ),
    .Y(net126));
 BUFx2_ASAP7_75t_R hold139 (.A(_031_),
    .Y(net127));
 BUFx2_ASAP7_75t_R hold140 (.A(\collars.coll_stream.sync_q[1] ),
    .Y(net128));
 BUFx2_ASAP7_75t_R hold141 (.A(_037_),
    .Y(net129));
 BUFx2_ASAP7_75t_R hold142 (.A(\collars.coll_stream.sync_q[0] ),
    .Y(net130));
 BUFx2_ASAP7_75t_R hold143 (.A(_006_),
    .Y(net131));
 BUFx2_ASAP7_75t_R hold144 (.A(\collars.cmd_serial.sync_q[0] ),
    .Y(net132));
 BUFx2_ASAP7_75t_R hold145 (.A(_044_),
    .Y(net133));
 BUFx2_ASAP7_75t_R hold146 (.A(\sequence_control.status_meta[4] ),
    .Y(net134));
 BUFx2_ASAP7_75t_R hold147 (.A(_022_),
    .Y(net135));
 BUFx2_ASAP7_75t_R hold148 (.A(\collars.coll_serial.sync_q[0] ),
    .Y(net136));
 BUFx2_ASAP7_75t_R hold149 (.A(_007_),
    .Y(net137));
 BUFx2_ASAP7_75t_R hold150 (.A(\collars.phy[0].c.sync_q[0] ),
    .Y(net138));
 BUFx2_ASAP7_75t_R hold151 (.A(_016_),
    .Y(net139));
 BUFx2_ASAP7_75t_R hold152 (.A(\sequence_control.status_meta[0] ),
    .Y(net140));
 BUFx2_ASAP7_75t_R hold153 (.A(_050_),
    .Y(net141));
 BUFx2_ASAP7_75t_R hold154 (.A(\sequence_control.status_meta[16] ),
    .Y(net142));
 BUFx2_ASAP7_75t_R hold155 (.A(_005_),
    .Y(net143));
 BUFx2_ASAP7_75t_R hold156 (.A(\collars.cmd_stream.sync_q[0] ),
    .Y(net144));
 BUFx2_ASAP7_75t_R hold157 (.A(_017_),
    .Y(net145));
 BUFx2_ASAP7_75t_R hold158 (.A(\sequence_control.status_meta[1] ),
    .Y(net146));
 BUFx2_ASAP7_75t_R hold159 (.A(_054_),
    .Y(net147));
 BUFx2_ASAP7_75t_R hold160 (.A(\sequence_control.status_meta[9] ),
    .Y(net148));
 BUFx2_ASAP7_75t_R hold161 (.A(_065_),
    .Y(net149));
 BUFx2_ASAP7_75t_R hold162 (.A(\sequence_control.status_meta[11] ),
    .Y(net150));
 BUFx2_ASAP7_75t_R hold163 (.A(_003_),
    .Y(net151));
 BUFx2_ASAP7_75t_R hold164 (.A(\rel_sync_q0[3] ),
    .Y(net152));
 BUFx2_ASAP7_75t_R hold165 (.A(_008_),
    .Y(net153));
 BUFx2_ASAP7_75t_R hold166 (.A(\collars.link[0].c.sync_q[0] ),
    .Y(net154));
 BUFx2_ASAP7_75t_R hold167 (.A(_066_),
    .Y(net155));
 BUFx2_ASAP7_75t_R hold168 (.A(\sequence_control.status_meta[13] ),
    .Y(net156));
 BUFx2_ASAP7_75t_R hold169 (.A(_055_),
    .Y(net157));
 BUFx2_ASAP7_75t_R hold170 (.A(\sequence_control.status_meta[8] ),
    .Y(net158));
 BUFx2_ASAP7_75t_R hold171 (.A(_057_),
    .Y(net159));
 BUFx2_ASAP7_75t_R hold172 (.A(\rel_sync_q0[2] ),
    .Y(net160));
 BUFx2_ASAP7_75t_R hold173 (.A(_063_),
    .Y(net161));
 BUFx2_ASAP7_75t_R hold174 (.A(\rel_sync_q0[1] ),
    .Y(net162));
 BUFx2_ASAP7_75t_R hold175 (.A(_060_),
    .Y(net163));
 BUFx2_ASAP7_75t_R hold176 (.A(\sequence_control.status_meta[5] ),
    .Y(net164));
 BUFx2_ASAP7_75t_R hold177 (.A(_011_),
    .Y(net165));
 BUFx2_ASAP7_75t_R hold178 (.A(\sequence_control.status_meta[14] ),
    .Y(net166));
 BUFx2_ASAP7_75t_R hold179 (.A(_019_),
    .Y(net167));
 BUFx2_ASAP7_75t_R hold180 (.A(\rel_sync_q0[10] ),
    .Y(net168));
 BUFx2_ASAP7_75t_R hold181 (.A(_018_),
    .Y(net169));
 BUFx2_ASAP7_75t_R hold182 (.A(\sequence_control.status_meta[2] ),
    .Y(net170));
 BUFx2_ASAP7_75t_R hold183 (.A(_052_),
    .Y(net171));
 BUFx2_ASAP7_75t_R hold184 (.A(\rel_sync_q0[13] ),
    .Y(net172));
 BUFx2_ASAP7_75t_R hold185 (.A(_004_),
    .Y(net173));
 BUFx2_ASAP7_75t_R hold186 (.A(\sequence_control.status_meta[3] ),
    .Y(net174));
 BUFx2_ASAP7_75t_R hold187 (.A(_061_),
    .Y(net175));
 BUFx2_ASAP7_75t_R hold188 (.A(\sequence_control.status_meta[10] ),
    .Y(net176));
 BUFx2_ASAP7_75t_R hold189 (.A(_024_),
    .Y(net177));
 BUFx2_ASAP7_75t_R hold190 (.A(net100),
    .Y(net178));
 BUFx2_ASAP7_75t_R hold191 (.A(_062_),
    .Y(net179));
 BUFx2_ASAP7_75t_R hold192 (.A(\rel_sync_q0[0] ),
    .Y(net180));
 BUFx2_ASAP7_75t_R hold193 (.A(_056_),
    .Y(net181));
 BUFx2_ASAP7_75t_R hold194 (.A(\sequence_control.status_meta[12] ),
    .Y(net182));
 BUFx2_ASAP7_75t_R hold195 (.A(_059_),
    .Y(net183));
 BUFx2_ASAP7_75t_R hold196 (.A(\sequence_control.status_meta[6] ),
    .Y(net184));
 BUFx2_ASAP7_75t_R hold197 (.A(_064_),
    .Y(net185));
 BUFx2_ASAP7_75t_R hold198 (.A(\sequence_control.status_meta[7] ),
    .Y(net186));
 BUFx2_ASAP7_75t_R hold199 (.A(_030_),
    .Y(net187));
 BUFx2_ASAP7_75t_R hold200 (.A(net103),
    .Y(net188));
 BUFx2_ASAP7_75t_R hold201 (.A(_026_),
    .Y(net189));
 BUFx2_ASAP7_75t_R hold202 (.A(net101),
    .Y(net190));
 BUFx2_ASAP7_75t_R hold203 (.A(_028_),
    .Y(net191));
 BUFx2_ASAP7_75t_R hold204 (.A(net102),
    .Y(net192));
 BUFx2_ASAP7_75t_R hold205 (.A(_025_),
    .Y(net193));
 BUFx2_ASAP7_75t_R hold206 (.A(_033_),
    .Y(net194));
 BUFx2_ASAP7_75t_R hold207 (.A(_027_),
    .Y(net195));
 BUFx2_ASAP7_75t_R hold208 (.A(_046_),
    .Y(net196));
 BUFx2_ASAP7_75t_R hold209 (.A(_029_),
    .Y(net197));
 BUFx2_ASAP7_75t_R input100 (.A(requalify),
    .Y(net99));
 BUFx2_ASAP7_75t_R input81 (.A(bist_done),
    .Y(net80));
 BUFx2_ASAP7_75t_R input82 (.A(bist_pass),
    .Y(net81));
 BUFx2_ASAP7_75t_R input83 (.A(fatal_error),
    .Y(net82));
 BUFx2_ASAP7_75t_R input84 (.A(links_ready[0]),
    .Y(net83));
 BUFx2_ASAP7_75t_R input85 (.A(links_ready[1]),
    .Y(net84));
 BUFx2_ASAP7_75t_R input86 (.A(links_ready[2]),
    .Y(net85));
 BUFx2_ASAP7_75t_R input87 (.A(links_ready[3]),
    .Y(net86));
 BUFx2_ASAP7_75t_R input88 (.A(links_ready[4]),
    .Y(net87));
 BUFx2_ASAP7_75t_R input89 (.A(links_ready[5]),
    .Y(net88));
 BUFx2_ASAP7_75t_R input90 (.A(links_ready[6]),
    .Y(net89));
 BUFx2_ASAP7_75t_R input91 (.A(links_ready[7]),
    .Y(net90));
 BUFx2_ASAP7_75t_R input92 (.A(links_ready[8]),
    .Y(net91));
 BUFx2_ASAP7_75t_R input93 (.A(phy_ready[0]),
    .Y(net92));
 BUFx2_ASAP7_75t_R input94 (.A(phy_ready[1]),
    .Y(net93));
 BUFx2_ASAP7_75t_R input95 (.A(phy_ready[2]),
    .Y(net94));
 BUFx2_ASAP7_75t_R input96 (.A(phy_ready[3]),
    .Y(net95));
 BUFx2_ASAP7_75t_R input97 (.A(pll_lock),
    .Y(net96));
 BUFx2_ASAP7_75t_R input98 (.A(por_n),
    .Y(net97));
 BUFx2_ASAP7_75t_R input99 (.A(power_good),
    .Y(net98));
 BUFx2_ASAP7_75t_R output101 (.A(net100),
    .Y(cmd_reset_serial_n));
 BUFx2_ASAP7_75t_R output102 (.A(net101),
    .Y(cmd_reset_stream_n));
 BUFx2_ASAP7_75t_R output103 (.A(net102),
    .Y(coll_reset_serial_n));
 BUFx2_ASAP7_75t_R output104 (.A(net103),
    .Y(coll_reset_stream_n));
 BUFx2_ASAP7_75t_R output105 (.A(net104),
    .Y(link_reset_n[0]));
 BUFx2_ASAP7_75t_R output106 (.A(net104),
    .Y(link_reset_n[1]));
 BUFx2_ASAP7_75t_R output107 (.A(net104),
    .Y(link_reset_n[2]));
 BUFx2_ASAP7_75t_R output108 (.A(net104),
    .Y(link_reset_n[3]));
 BUFx2_ASAP7_75t_R output109 (.A(net104),
    .Y(link_reset_n[4]));
 BUFx2_ASAP7_75t_R output110 (.A(net104),
    .Y(link_reset_n[5]));
 BUFx2_ASAP7_75t_R output111 (.A(net104),
    .Y(link_reset_n[6]));
 BUFx2_ASAP7_75t_R output112 (.A(net104),
    .Y(link_reset_n[7]));
 BUFx2_ASAP7_75t_R output113 (.A(net104),
    .Y(link_reset_n[8]));
 BUFx2_ASAP7_75t_R output114 (.A(net105),
    .Y(phy_reset_n[0]));
 BUFx2_ASAP7_75t_R output115 (.A(net105),
    .Y(phy_reset_n[1]));
 BUFx2_ASAP7_75t_R output116 (.A(net105),
    .Y(phy_reset_n[2]));
 BUFx2_ASAP7_75t_R output117 (.A(net105),
    .Y(phy_reset_n[3]));
 BUFx2_ASAP7_75t_R output118 (.A(net106),
    .Y(pll_reset_n));
 BUFx2_ASAP7_75t_R output119 (.A(net107),
    .Y(ready));
 BUFx2_ASAP7_75t_R output120 (.A(net108),
    .Y(state[0]));
 BUFx2_ASAP7_75t_R output121 (.A(net109),
    .Y(state[1]));
 BUFx2_ASAP7_75t_R output122 (.A(net110),
    .Y(state[2]));
 BUFx3_ASAP7_75t_R place127 (.A(net97),
    .Y(net115));
 BUFx3_ASAP7_75t_R place128 (.A(net97),
    .Y(net116));
 DFFASRHQNx1_ASAP7_75t_R \rel_sync_q0[0]$_DFF_PN0_  (.CLK(clknet_2_1__leaf_aon_clk),
    .D(net178),
    .QN(_062_),
    .RESETN(net116),
    .SETN(net31));
 TIEHIx1_ASAP7_75t_R \rel_sync_q0[0]$_DFF_PN0__32  (.H(net31));
 DFFASRHQNx1_ASAP7_75t_R \rel_sync_q0[12]$_DFF_PN0_  (.CLK(clknet_2_1__leaf_aon_clk),
    .D(net104),
    .QN(_019_),
    .RESETN(net116),
    .SETN(net32));
 TIEHIx1_ASAP7_75t_R \rel_sync_q0[12]$_DFF_PN0__33  (.H(net32));
 DFFASRHQNx1_ASAP7_75t_R \rel_sync_q0[15]$_DFF_PN0_  (.CLK(clknet_2_0__leaf_aon_clk),
    .D(net105),
    .QN(_052_),
    .RESETN(net116),
    .SETN(net33));
 TIEHIx1_ASAP7_75t_R \rel_sync_q0[15]$_DFF_PN0__34  (.H(net33));
 DFFASRHQNx1_ASAP7_75t_R \rel_sync_q0[1]$_DFF_PN0_  (.CLK(clknet_2_1__leaf_aon_clk),
    .D(net190),
    .QN(_063_),
    .RESETN(net116),
    .SETN(net34));
 TIEHIx1_ASAP7_75t_R \rel_sync_q0[1]$_DFF_PN0__35  (.H(net34));
 DFFASRHQNx1_ASAP7_75t_R \rel_sync_q0[2]$_DFF_PN0_  (.CLK(clknet_2_0__leaf_aon_clk),
    .D(net192),
    .QN(_057_),
    .RESETN(net116),
    .SETN(net35));
 TIEHIx1_ASAP7_75t_R \rel_sync_q0[2]$_DFF_PN0__36  (.H(net35));
 DFFASRHQNx1_ASAP7_75t_R \rel_sync_q0[3]$_DFF_PN0_  (.CLK(clknet_2_0__leaf_aon_clk),
    .D(net188),
    .QN(_003_),
    .RESETN(net116),
    .SETN(net36));
 TIEHIx1_ASAP7_75t_R \rel_sync_q0[3]$_DFF_PN0__37  (.H(net36));
 DFFASRHQNx1_ASAP7_75t_R \rel_sync_q1[0]$_DFF_PN0_  (.CLK(clknet_2_1__leaf_aon_clk),
    .D(net180),
    .QN(_020_),
    .RESETN(net116),
    .SETN(net37));
 TIEHIx1_ASAP7_75t_R \rel_sync_q1[0]$_DFF_PN0__38  (.H(net37));
 DFFASRHQNx1_ASAP7_75t_R \rel_sync_q1[12]$_DFF_PN0_  (.CLK(clknet_2_1__leaf_aon_clk),
    .D(net168),
    .QN(_058_),
    .RESETN(net116),
    .SETN(net38));
 TIEHIx1_ASAP7_75t_R \rel_sync_q1[12]$_DFF_PN0__39  (.H(net38));
 DFFASRHQNx1_ASAP7_75t_R \rel_sync_q1[15]$_DFF_PN0_  (.CLK(clknet_2_1__leaf_aon_clk),
    .D(net172),
    .QN(_023_),
    .RESETN(net116),
    .SETN(net39));
 TIEHIx1_ASAP7_75t_R \rel_sync_q1[15]$_DFF_PN0__40  (.H(net39));
 DFFASRHQNx1_ASAP7_75t_R \rel_sync_q1[1]$_DFF_PN0_  (.CLK(clknet_2_1__leaf_aon_clk),
    .D(net162),
    .QN(_021_),
    .RESETN(net116),
    .SETN(net40));
 TIEHIx1_ASAP7_75t_R \rel_sync_q1[1]$_DFF_PN0__41  (.H(net40));
 DFFASRHQNx1_ASAP7_75t_R \rel_sync_q1[2]$_DFF_PN0_  (.CLK(clknet_2_1__leaf_aon_clk),
    .D(net160),
    .QN(_012_),
    .RESETN(net116),
    .SETN(net41));
 TIEHIx1_ASAP7_75t_R \rel_sync_q1[2]$_DFF_PN0__42  (.H(net41));
 DFFASRHQNx1_ASAP7_75t_R \rel_sync_q1[3]$_DFF_PN0_  (.CLK(clknet_2_0__leaf_aon_clk),
    .D(net152),
    .QN(_015_),
    .RESETN(net116),
    .SETN(net42));
 TIEHIx1_ASAP7_75t_R \rel_sync_q1[3]$_DFF_PN0__43  (.H(net42));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.state[0]$_DFFE_PN0P_  (.CLK(clknet_2_0__leaf_aon_clk),
    .D(_068_),
    .QN(_001_),
    .RESETN(net116),
    .SETN(net43));
 TIEHIx1_ASAP7_75t_R \sequence_control.state[0]$_DFFE_PN0P__44  (.H(net43));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.state[1]$_DFFE_PN0P_  (.CLK(clknet_2_0__leaf_aon_clk),
    .D(_067_),
    .QN(_002_),
    .RESETN(net116),
    .SETN(net44));
 TIEHIx1_ASAP7_75t_R \sequence_control.state[1]$_DFFE_PN0P__45  (.H(net44));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.state[2]$_DFFE_PN0P_  (.CLK(clknet_2_1__leaf_aon_clk),
    .D(_069_),
    .QN(_000_),
    .RESETN(net116),
    .SETN(net45));
 TIEHIx1_ASAP7_75t_R \sequence_control.state[2]$_DFFE_PN0P__46  (.H(net45));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_meta[0]$_DFF_PN0_  (.CLK(clknet_2_0__leaf_aon_clk),
    .D(net98),
    .QN(_016_),
    .RESETN(net116),
    .SETN(net46));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_meta[0]$_DFF_PN0__47  (.H(net46));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_meta[10]$_DFF_PN0_  (.CLK(clknet_2_3__leaf_aon_clk),
    .D(net87),
    .QN(_061_),
    .RESETN(net115),
    .SETN(net47));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_meta[10]$_DFF_PN0__48  (.H(net47));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_meta[11]$_DFF_PN0_  (.CLK(clknet_2_3__leaf_aon_clk),
    .D(net88),
    .QN(_065_),
    .RESETN(net115),
    .SETN(net48));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_meta[11]$_DFF_PN0__49  (.H(net48));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_meta[12]$_DFF_PN0_  (.CLK(clknet_2_3__leaf_aon_clk),
    .D(net89),
    .QN(_056_),
    .RESETN(net115),
    .SETN(net49));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_meta[12]$_DFF_PN0__50  (.H(net49));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_meta[13]$_DFF_PN0_  (.CLK(clknet_2_2__leaf_aon_clk),
    .D(net90),
    .QN(_066_),
    .RESETN(net115),
    .SETN(net50));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_meta[13]$_DFF_PN0__51  (.H(net50));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_meta[14]$_DFF_PN0_  (.CLK(clknet_2_2__leaf_aon_clk),
    .D(net91),
    .QN(_011_),
    .RESETN(net115),
    .SETN(net51));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_meta[14]$_DFF_PN0__52  (.H(net51));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_meta[15]$_DFF_PN0_  (.CLK(clknet_2_3__leaf_aon_clk),
    .D(net80),
    .QN(_010_),
    .RESETN(net115),
    .SETN(net52));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_meta[15]$_DFF_PN0__53  (.H(net52));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_meta[16]$_DFF_PN0_  (.CLK(clknet_2_0__leaf_aon_clk),
    .D(net81),
    .QN(_050_),
    .RESETN(net116),
    .SETN(net53));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_meta[16]$_DFF_PN0__54  (.H(net53));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_meta[1]$_DFF_PN0_  (.CLK(clknet_2_0__leaf_aon_clk),
    .D(net96),
    .QN(_017_),
    .RESETN(net116),
    .SETN(net54));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_meta[1]$_DFF_PN0__55  (.H(net54));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_meta[2]$_DFF_PN0_  (.CLK(clknet_2_2__leaf_aon_clk),
    .D(net92),
    .QN(_018_),
    .RESETN(net115),
    .SETN(net55));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_meta[2]$_DFF_PN0__56  (.H(net55));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_meta[3]$_DFF_PN0_  (.CLK(clknet_2_2__leaf_aon_clk),
    .D(net93),
    .QN(_004_),
    .RESETN(net115),
    .SETN(net56));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_meta[3]$_DFF_PN0__57  (.H(net56));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_meta[4]$_DFF_PN0_  (.CLK(clknet_2_2__leaf_aon_clk),
    .D(net94),
    .QN(_044_),
    .RESETN(net115),
    .SETN(net57));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_meta[4]$_DFF_PN0__58  (.H(net57));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_meta[5]$_DFF_PN0_  (.CLK(clknet_2_2__leaf_aon_clk),
    .D(net95),
    .QN(_060_),
    .RESETN(net115),
    .SETN(net58));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_meta[5]$_DFF_PN0__59  (.H(net58));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_meta[6]$_DFF_PN0_  (.CLK(clknet_2_2__leaf_aon_clk),
    .D(net83),
    .QN(_059_),
    .RESETN(net115),
    .SETN(net59));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_meta[6]$_DFF_PN0__60  (.H(net59));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_meta[7]$_DFF_PN0_  (.CLK(clknet_2_2__leaf_aon_clk),
    .D(net84),
    .QN(_064_),
    .RESETN(net115),
    .SETN(net60));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_meta[7]$_DFF_PN0__61  (.H(net60));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_meta[8]$_DFF_PN0_  (.CLK(clknet_2_3__leaf_aon_clk),
    .D(net85),
    .QN(_055_),
    .RESETN(net115),
    .SETN(net61));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_meta[8]$_DFF_PN0__62  (.H(net61));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_meta[9]$_DFF_PN0_  (.CLK(clknet_2_3__leaf_aon_clk),
    .D(net86),
    .QN(_054_),
    .RESETN(net115),
    .SETN(net62));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_meta[9]$_DFF_PN0__63  (.H(net62));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_sync[0]$_DFF_PN0_  (.CLK(clknet_2_0__leaf_aon_clk),
    .D(net140),
    .QN(_014_),
    .RESETN(net116),
    .SETN(net63));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_sync[0]$_DFF_PN0__64  (.H(net63));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_sync[10]$_DFF_PN0_  (.CLK(clknet_2_3__leaf_aon_clk),
    .D(net176),
    .QN(_040_),
    .RESETN(net115),
    .SETN(net64));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_sync[10]$_DFF_PN0__65  (.H(net64));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_sync[11]$_DFF_PN0_  (.CLK(clknet_2_3__leaf_aon_clk),
    .D(net150),
    .QN(_039_),
    .RESETN(net115),
    .SETN(net65));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_sync[11]$_DFF_PN0__66  (.H(net65));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_sync[12]$_DFF_PN0_  (.CLK(clknet_2_3__leaf_aon_clk),
    .D(net182),
    .QN(_038_),
    .RESETN(net115),
    .SETN(net66));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_sync[12]$_DFF_PN0__67  (.H(net66));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_sync[13]$_DFF_PN0_  (.CLK(clknet_2_2__leaf_aon_clk),
    .D(net156),
    .QN(_036_),
    .RESETN(net115),
    .SETN(net67));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_sync[13]$_DFF_PN0__68  (.H(net67));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_sync[14]$_DFF_PN0_  (.CLK(clknet_2_2__leaf_aon_clk),
    .D(net166),
    .QN(_035_),
    .RESETN(net115),
    .SETN(net68));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_sync[14]$_DFF_PN0__69  (.H(net68));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_sync[15]$_DFF_PN0_  (.CLK(clknet_2_1__leaf_aon_clk),
    .D(\sequence_control.status_meta[15] ),
    .QN(_034_),
    .RESETN(net116),
    .SETN(net69));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_sync[15]$_DFF_PN0__70  (.H(net69));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_sync[16]$_DFF_PN0_  (.CLK(clknet_2_0__leaf_aon_clk),
    .D(net142),
    .QN(_051_),
    .RESETN(net116),
    .SETN(net70));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_sync[16]$_DFF_PN0__71  (.H(net70));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_sync[1]$_DFF_PN0_  (.CLK(clknet_2_0__leaf_aon_clk),
    .D(net146),
    .QN(_013_),
    .RESETN(net116),
    .SETN(net71));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_sync[1]$_DFF_PN0__72  (.H(net71));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_sync[2]$_DFF_PN0_  (.CLK(clknet_2_2__leaf_aon_clk),
    .D(net170),
    .QN(_042_),
    .RESETN(net115),
    .SETN(net72));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_sync[2]$_DFF_PN0__73  (.H(net72));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_sync[3]$_DFF_PN0_  (.CLK(clknet_2_2__leaf_aon_clk),
    .D(net174),
    .QN(_009_),
    .RESETN(net115),
    .SETN(net73));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_sync[3]$_DFF_PN0__74  (.H(net73));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_sync[4]$_DFF_PN0_  (.CLK(clknet_2_2__leaf_aon_clk),
    .D(net134),
    .QN(_053_),
    .RESETN(net115),
    .SETN(net74));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_sync[4]$_DFF_PN0__75  (.H(net74));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_sync[5]$_DFF_PN0_  (.CLK(clknet_2_2__leaf_aon_clk),
    .D(net164),
    .QN(_049_),
    .RESETN(net115),
    .SETN(net75));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_sync[5]$_DFF_PN0__76  (.H(net75));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_sync[6]$_DFF_PN0_  (.CLK(clknet_2_2__leaf_aon_clk),
    .D(net184),
    .QN(_048_),
    .RESETN(net115),
    .SETN(net76));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_sync[6]$_DFF_PN0__77  (.H(net76));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_sync[7]$_DFF_PN0_  (.CLK(clknet_2_3__leaf_aon_clk),
    .D(net186),
    .QN(_047_),
    .RESETN(net115),
    .SETN(net77));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_sync[7]$_DFF_PN0__78  (.H(net77));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_sync[8]$_DFF_PN0_  (.CLK(clknet_2_3__leaf_aon_clk),
    .D(net158),
    .QN(_043_),
    .RESETN(net115),
    .SETN(net78));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_sync[8]$_DFF_PN0__79  (.H(net78));
 DFFASRHQNx1_ASAP7_75t_R \sequence_control.status_sync[9]$_DFF_PN0_  (.CLK(clknet_2_3__leaf_aon_clk),
    .D(net148),
    .QN(_041_),
    .RESETN(net115),
    .SETN(net79));
 TIEHIx1_ASAP7_75t_R \sequence_control.status_sync[9]$_DFF_PN0__80  (.H(net79));
endmodule
