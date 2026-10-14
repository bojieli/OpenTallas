`timescale 1ps/1ps
// ---------------------------------------------------------------------------
// End-to-end exact bench of the ROM dies' host block (ot_rom_host_ingest): host link stream -> CDC -> KV ingest
// engine (clk_i) -> CDC -> die fabric (ck) -> HBM image, compared sector by sector with the golden's image
// (tools/kv_ingest_ref.py, through tools/rtl_rom_host_ingest_bench.py).  Three unrelated clocks.
// Files (run directory): desc.mem (256-b descriptors), pay.mem (512-b beats), nb.mem (payload beats of each
// descriptor), init.mem / exp.mem (HBM image before / expected after, 32-B sectors).
// Host: CSR share (+SHARE, x256), then descriptor k and its nb[k] beats, credit-limited, +HGAP % idle cycles.
// Completions: every fenced descriptor must complete once, tags in order, no fault word.
// Fabric: takes a word per credit; drains it after +MSTALL % stall cycles; writes land, reads return in order after
// LAT ck cycles.  Prints one line: HING ... errors=E ...
// ---------------------------------------------------------------------------
module tb_qkd_host_native_transport #(
    parameter integer ORDER_MUT=0,
    parameter integer CLASS_MUT=0,
    parameter integer BP=1000,
    parameter integer MEMW   = 65536,
    parameter integer ND     = 64,
    parameter integer NP     = 4096,
    parameter integer HDMAX  = 128,
    parameter integer KVHMAX = 2,
    parameter integer QKV_EN = 1,
    parameter integer RMW_EN = 1,
    parameter integer MUT    = 0,
    parameter integer NATIVE_ROWS=1,
    parameter integer QPIPE  = 2,
    parameter integer HP     = 1000,     // clk_h period (ps)
    parameter integer IP     = 1666,     // clk_i period (ps): the die clock / 2
    parameter integer CP     = 833,      // ck period (ps)
    parameter integer LAT    = 40
) ();
    localparam integer AW = 32, HFA = 4, OCRED = 8;
    reg clk_h = 0, clk_i = 0, ck = 0, rst_n = 0;
    reg clk_b=0;initial begin #197;forever #(BP/2)clk_b=~clk_b;end
    always #(HP / 2) clk_h = ~clk_h;
    always #(IP / 2) clk_i = ~clk_i;
    always #(CP / 2) ck = ~ck;

    reg [255:0] dmem [0:ND-1];
    reg [511:0] pmem [0:NP-1];
    reg [31:0]  nbm  [0:ND-1];
    reg[255:0]hbm[int unsigned],expm[int unsigned];
    reg[287:0]gold[0:4095];integer nsector;
    int unsigned expected_addr;
    integer emitted=0,actual_prefix=0;int unsigned order_by_addr[int unsigned];bit retired_order[0:4095];
    integer nd, np, share, hgap, mstall, maxcyc, seed, nfence, i;
    initial begin
        if (!$value$plusargs("ND=%d", nd)) nd = ND;
        if (!$value$plusargs("NP=%d", np)) np = NP;
        if (!$value$plusargs("SHARE=%d", share)) share = 0;
        if (!$value$plusargs("HGAP=%d", hgap)) hgap = 0;
        if (!$value$plusargs("MSTALL=%d", mstall)) mstall = 0;
        if (!$value$plusargs("MAXCYC=%d", maxcyc)) maxcyc = 4000000;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        $readmemh("desc.mem", dmem);
        $readmemh("pay.mem", pmem);
        $readmemh("nb.mem", nbm);
        if(!$value$plusargs("NSECTOR=%d",nsector))nsector=2048;
        $readmemh("native.mem",gold);
        for(integer x=0;x<nsector;x++)begin
         expm[gold[x][31:0]]=gold[x][287:32];hbm[gold[x][31:0]]=0;
        end
        nfence = 0;
        for (i = 0; i < nd; i = i + 1) if (dmem[i][7]) nfence = nfence + 1;
        #(20 * HP) rst_n = 1;
    end

    // ---- DUT ------------------------------------------------------------------------------------------------------
    reg          h_v;
    reg  [1:0]   h_cls;
    reg  [511:0] h_d;
    wire [HFA:0] h_crn;
    wire q_t_v,t_v,core_t_v,core_t_cr;
    wire[63:0]q_t_d,t_d,core_t_d;wire q_t_cr;
    reg          t_cr;
    wire         o_v, o_we;
    wire [AW-1:0] o_addr;
    wire [255:0] o_d;
    wire o_cr;reg i_rv=0;
    reg[255:0]i_rd=0;
    wire         fault;
    wire qm_hv;wire[1:0]qm_hcls;wire[511:0]qm_hd;wire[4:0]qm_hcrn;
    ot_rom_host_ingest #(.AW(AW), .HDMAX(HDMAX), .KVHMAX(KVHMAX), .QKV_EN(QKV_EN), .RMW_EN(RMW_EN), .HFA(HFA),
                         .OCRED(OCRED), .MUT(MUT), .QPIPE(QPIPE),.NATIVE_ROWS(NATIVE_ROWS)) dut (
        .rst_n(rst_n), .clk_h(clk_h), .h_v(qm_hv), .h_cls(qm_hcls), .h_d(qm_hd), .h_crn(qm_hcrn), .t_v(q_t_v), .t_d(q_t_d),
        .t_cr(q_t_cr), .clk_i(clk_i), .ck(ck), .o_v(o_v), .o_we(o_we), .o_addr(o_addr), .o_d(o_d), .o_cr(o_cr),
        .i_rv(i_rv), .i_rd(i_rd), .fault(fault));

    // Exact normalized DATA1024 board face; actual FDI adapter binds outside
    // this diagnostic until its source/clock ABI is supplied by the IO owner.
    wire board_rx_cr,board_tx_v;wire[1023:0]board_tx_d;reg board_tx_cr=0,peer_v=0;
    integer physical_credit=4,peer_pending=0;reg peer_sending;
    wire[1023:0]board_rx_d={496'd0,peer_v?{4'd7,12'd0,488'd0,8'd1,16'd0}:{(4'(h_cls)+4'd2),12'd0,h_d}};
    wire rx_v,rx_cr,tx_v,tx_cr;wire[527:0]rx_d,tx_d;wire[4:0]phy_faults;
    wire[23:0]credit_return,peer_credit;wire rx_fault,tx_fault;
    qkd_host_phy_cdc #(.MUT(CLASS_MUT))u_phy(.ck_pad(clk_b),.rx_wck(clk_b),.rx_rck(clk_h),.tx_wck(clk_h),.tx_rck(clk_b),.rst_n(rst_n),
     .phy_rx_v(h_v||peer_v),.phy_rx_d(board_rx_d),.phy_rx_cr(board_rx_cr),
     .phy_tx_v(board_tx_v),.phy_tx_d(board_tx_d),.phy_tx_cr(board_tx_cr),
     .core_rx_v(rx_v),.core_rx_d(rx_d),.core_rx_cr(rx_cr),.core_tx_v(tx_v),.core_tx_d(tx_d),.core_tx_cr(tx_cr),.faults(phy_faults));
    qkd_host_rx_class #(.STRAPPED(1))u_rx(.ck(clk_h),.rst_n(rst_n),.die_id(3'd0),.rx_v(rx_v),.rx_d(rx_d),.rx_cr(rx_cr),
     .host_v(),.host_d(),.host_cr(1'b0),.ctrl_v(),.ctrl_d(),.ctrl_cr(1'b0),
     .ing_v(qm_hv),.ing_cls(qm_hcls),.ing_d(qm_hd),.ing_crn(qm_hcrn),.credit_return(credit_return),.peer_credit(peer_credit),.fault(rx_fault));
    qkd_host_tx_class u_tx(.ck(clk_h),.rst_n(rst_n),.host_v(1'b0),.host_d(512'd0),.host_cr(),.ctrl_v(1'b0),.ctrl_d(512'd0),.ctrl_cr(),
     .ing_v(core_t_v),.ing_d(core_t_d),.ing_cr(core_t_cr),.credit_return(credit_return),.peer_credit(peer_credit),.irq(1'b0),
     .tx_v(tx_v),.tx_d(tx_d),.tx_cr(tx_cr),.fault(tx_fault));
    assign h_crn=board_tx_v&&board_tx_d[527:524]==7?board_tx_d[20:16]:5'd0;
    assign t_v=board_tx_v&&board_tx_d[527:524]==5;
    assign t_d=board_tx_d[63:0];

    // ---- host (clk_h) ---------------------------------------------------------------------------------------------
    integer hcred = 1 << HFA, di = 0, pi = 0, pleft = 0, csr_done = 0, hcyc = 0;
    integer dones = 0, fwords = 0, tag_err = 0, exp_tag_i = 0, hup = 0;
    reg [31:0] rnd_h;
    integer bootend, bcount, breg, mark_sent = 0;
    initial begin
        if (!$value$plusargs("BOOTEND=%d", bootend)) bootend = 0;
        if (!$value$plusargs("BCOUNT=%d", bcount)) bcount = 0;
        if (!$value$plusargs("BREG=%d", breg)) breg = 0;
    end
    wire host_done = csr_done && di == nd && pleft == 0 && (bootend == 0 || mark_sent);
    always @(posedge clk_b) begin
        hcyc <= hcyc + 1;
        rnd_h = $random(seed);
        h_v <= 1'b0; t_cr <= 1'b0; peer_v<=0;board_tx_cr<=0;
        peer_sending=0;physical_credit=physical_credit+board_rx_cr;
        if(board_tx_v)board_tx_cr<=1;
        if(t_v)peer_pending=peer_pending+1;
        if(rst_n&&hup>=8&&peer_pending>0&&physical_credit>0)begin
         peer_sending=1;peer_v<=1;peer_pending=peer_pending-1;physical_credit=physical_credit-1;
        end
        if (rst_n) hup <= hup + 1;
        if (rst_n && hup >= 8) begin                              // link up: the block's synchronised resets are released
            if (hcred + h_crn > 0 && physical_credit>0 && !peer_sending && !host_done && (rnd_h % 100) >= hgap) begin
                h_v <= 1'b1;physical_credit=physical_credit-1;
                if (!csr_done) begin
                    h_cls <= 2'd0; h_d <= {448'd0, 23'd0, share[8:0], 32'd0}; csr_done <= 1;
                end else if (di == nd && pleft == 0) begin
                    h_cls <= 2'd0; h_d <= {382'd0, breg[1:0], 32'h1234abcd, bcount[31:0], 56'd0, 8'd2}; mark_sent <= 1;
                end else if (pleft > 0) begin
                    h_cls <= 2'd2; h_d <= pmem[pi]; pi <= pi + 1; pleft <= pleft - 1;
                end else begin
                    h_cls <= 2'd1; h_d <= {256'd0, dmem[di]}; pleft <= nbm[di]; di <= di + 1;
                end
                hcred <= hcred + h_crn - 1;
            end else hcred <= hcred + h_crn;
            // completions
            if (t_v) begin
                t_cr <= 1'b1;
                if (t_d[63:56] == 8'h01) begin
                    while(actual_prefix<emitted&&retired_order[actual_prefix])actual_prefix++;
                    if(t_d[31:0]>actual_prefix)$fatal(1,"descriptor completed before fully retired issue prefix target=%0d prefix=%0d total=%0d",t_d[31:0],actual_prefix,retired);
                    // fenced descriptors complete in order: the k-th done word carries the k-th fenced tag
                    while (exp_tag_i < nd && !dmem[exp_tag_i][7]) exp_tag_i = exp_tag_i + 1;
                    if (exp_tag_i >= nd || t_d[47:40] != dmem[exp_tag_i][15:8]) tag_err <= tag_err + 1;
                    exp_tag_i = exp_tag_i + 1;
                    dones <= dones + 1;
                end else fwords <= fwords + 1;
            end
        end
    end

    // ---- die fabric + HBM (ck) ------------------------------------------------------------------------------------

 reg hclk=0;always #512 hclk=~hclk;
 wire[36863:0]ctrl_es;wire[33407:0]ctrl_er,land_er;wire[127:0]cv,cw;wire[7:0]ack_n;
 wire[31:0]issued,landed;wire map_fault,order_fault;wire[3:0]chain_fault;wire marker_v;wire[65:0]marker;wire fence_fault;wire[31:0]fence_landed;
 qkd_host_ingest_chain #(.ORDER_MUT(ORDER_MUT))u_chain(.ck_map(ck),.ck_sum(ck),.ck_order(ck),.ck_station({128{ck}}),.ck_static({128{ck}}),.rst_n(rst_n),
 .ing({o_d,o_addr,o_we,o_v}),.ing_cr(o_cr),.land_es(36864'd0),.land_er(land_er),.ctrl_es(ctrl_es),.ctrl_er(ctrl_er),
 .completion_v(cv),.completion_we(cw),.marker_v(marker_v),.marker(marker),.marker_cr(1'b0),.issued(issued),.landed(landed),.map_fault(map_fault),.chain_fault(chain_fault),.ack_n(ack_n),.order_fault(order_fault));
 qkd_host_visibility_fence u_fence(.rst_n(rst_n),.ck(ck),.clk_h(clk_h),.ack_n(ack_n),.in_v(q_t_v),.in_d(q_t_d),.in_cr(q_t_cr),
 .out_v(core_t_v),.out_d(core_t_d),.out_cr(core_t_cr),.fault(fence_fault),.landed_debug(fence_landed));
 integer ccyc=0,idle=0,sectors=0,retired=0,first_o=-1,last_o=-1;
 always @(posedge ck)begin
  ccyc<=ccyc+1;
  for(integer k=0;k<128;k++)if(cv[k])begin if(!cw[k])$fatal(1,"nativeunexpected read retirement");retired++;end
  if(o_v&&o_addr!=32'hffffffff)begin
   if(!o_we||!expm.exists(o_addr)||o_d!==expm[o_addr])$fatal(1,"original BF16 native sector source mismatch addr=%h",o_addr);
   order_by_addr[o_addr]=emitted;emitted++;if(first_o<0)first_o=ccyc;last_o=ccyc;
  end
  if(rst_n&&(fault||map_fault||chain_fault||fence_fault||order_fault||rx_fault||tx_fault||phy_faults))$fatal(1,"native actual composed fault q=%b map=%b chain=%b fence=%b",fault,map_fault,chain_fault,fence_fault);
  if(landed>retired)$fatal(1,"native HBM visibility precedes actual retirement");
  if(marker_v && (issued!=landed||marker!={breg[1:0],32'h1234abcd,bcount[31:0]}))$fatal(1,"native marker beforephysicalcommit");
  idle<=(host_done&&dones>=nfence&&issued==landed&&sectors==nsector&&!o_v)?idle+1:0;
  if(rst_n&&(idle>=400||ccyc>maxcyc))begin
   foreach(expm[expected_addr])if(hbm[expected_addr]!==expm[expected_addr])$fatal(1,"native actual physical image mismatch addr=%h",expected_addr);
   if(ccyc>maxcyc||tag_err||fwords||dones!=nfence||sectors!=nsector||issued!=nsector||retired!=nsector||landed!=nsector)$fatal(1,"native actual final gate counts issued%0d retired%0d physical%0d done%0d/%0d",issued,retired,sectors,dones,nfence);
   $display("PASS NATIVE_TRANSPORT_DATA1024 sectors=%0d ck=%0d first=%0d last=%0d fenced=%0d image=exact128controllersPHY",sectors,ccyc,first_o,last_o,dones);$finish;
  end
 end
    function automatic [71:0] enc64(input [63:0] data);
        reg [71:0] c; integer p, k, j;
        begin
            c = '0; j = 0;
            for (p = 1; p <= 71; p = p + 1) if ((p & (p - 1)) != 0) begin c[p-1] = data[j]; j = j + 1; end
            for (k = 0; k < 7; k = k + 1)
                for (p = 1; p <= 71; p = p + 1)
                    if ((p & (1 << k)) != 0 && p != (1 << k)) c[(1<<k)-1] = c[(1<<k)-1] ^ c[p-1];
            c[71] = ^c[70:0]; enc64 = c;
        end
    endfunction
    function automatic [287:0] enc256(input [255:0] d);
        enc256 = {enc64(d[255:192]), enc64(d[191:128]), enc64(d[127:64]), enc64(d[63:0])};
    endfunction

 for(genvar id=0;id<128;id++)begin:g_pc
  wire[327:0]po;wire[293:0]co;wire[32:0]ko;wire ff,ef;
  qkd_ctrl_pc_host u_ctrl(.pll_hbm(hclk),.hrst(rst_n),.ck(ck),.rsi(rst_n),.pc(5'(id%32)),.ci(319'd0),.co(co),
   .es(ctrl_es[id*288+:288]),.er(ctrl_er[id*261+:261]),.po(po),.pi(289'd0),.ki(33'd0),.ko(ko),.fi(1'b0),.fo(ff),
   .completion_v(cv[id]),.completion_we(cw[id]),.completion_fault(ef));
  reg[286:0]posts[0:511];integer ordinals[0:511];integer wp=0,rp=0,ap=0;reg[286:0]meta;
  reg[4:0]mb[0:4],mc[0:4];reg[18:0]mr[0:4];reg[4:0]dv=0;reg[255:0]dd[0:4];reg[18:0]open_row[0:31];reg[31:0]open_bank=0;
  always @(posedge ck)begin
   if(rst_n&&ctrl_es[id*288])begin
    reg[286:0]m;reg[9:0]j;reg[31:0]a;
    m=ctrl_es[id*288+1+:287];j={m[284:282],m[279:275],m[281:280]};
    a=(32'(m[274:256]-64)<<18)|(32'({j[9:7],1'b0,j[6:0]})<<7)|32'(id);
    if(!order_by_addr.exists(a))$fatal(1,"controller post before original issue ordinal");
    ordinals[wp]=order_by_addr[a];posts[wp]=m;wp++;
   end
   if(cv[id])begin if(ap>=wp)$fatal(1,"ghost ordered retirement");retired_order[ordinals[ap]]=1;ap++;end
  end
  always @(posedge hclk)begin
   if(rst_n&&(ff||ef))$fatal(1,"actual controller fault PC=%0d",id);
   dv<={dv[3:0],po[28]&&po[29]};for(integer j=1;j<5;j++)begin dd[j]<=dd[j-1];mb[j]<=mb[j-1];mc[j]<=mc[j-1];mr[j]<=mr[j-1];end
   if(po[0])begin if(po[3:1]==1)begin open_bank[po[8:4]]=1;open_row[po[8:4]]=po[27:9];end else if(po[3:1]==0)open_bank[po[8:4]]=0;end
   if(po[28])begin
    if(!po[29]||rp>=wp)$fatal(1,"unexpected static physical column PC=%0d",id);
    meta=posts[rp];rp++;
    if(!open_bank[po[34:30]]||{po[34:30],po[39:35],open_row[po[34:30]]}!==meta[284:256])$fatal(1,"actual HBM bank/column/row ownership PC=%0d",id);
    dd[0]<=meta[255:0];mb[0]<=po[34:30];mc[0]<=po[39:35];mr[0]<=open_row[po[34:30]];
   end
   if(dv[4])begin
    if(po[327:40]!==enc256(dd[4]))$fatal(1,"actual ECC PHY256 write payload PC=%0d",id);
    begin
     reg[4:0]bb,cc;reg[9:0]j;reg[18:0]row;reg[31:0]addr;reg[255:0]payload;
     bb=mb[4];cc=mc[4];row=mr[4];j={bb[4:2],cc,bb[1:0]};
     addr=(32'(row-64)<<18)|(32'({j[9:7],1'b0,j[6:0]})<<7)|32'(id);
     payload=dd[4];if(!expm.exists(addr)||payload!==expm[addr])$fatal(1,"native actual independentgold mismatch PC=%0d addr=%h",id,addr);
     hbm[addr]=payload;sectors++;
    end
   end
  end
 end
endmodule
