module ot_ds_su_kv_related_visible #(
    parameter integer ENABLE = 0,
    parameter integer G        = 4,
    parameter integer W        = 16,
    parameter integer SW       = 8,
    parameter integer SUN      = 16,
    parameter integer AW       = 24,
    parameter integer STG      = 2048,        // words per staging slot
    parameter integer SAW      = 11,          // log2(STG)
    parameter integer KV_SBASE = 1 << 18,     // KV region, sector base on every stack
    parameter integer KV_SECTORS = 1 << 14,   // KV region size per stack (sectors)
    parameter integer TROWS    = 160,         // the attention adapter's rows per job (ot_hdc_v41x_att_adapt)
    parameter integer D        = 32,          // its head dim
    parameter integer HAW      = 28,
    parameter integer TAGW     = 16,
    parameter integer WQD      = 128,          // write-queue sectors per stack
    parameter integer CMB      = SW + SUN     // sectors combined a cycle (every lane a different sector)
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire [AW-1:0]       base,          // the running user's KV word base
    // descriptor / permission
    input  wire                kvd_v,
    input  wire [AW-1:0]       kvd_wbase,
    input  wire [AW-1:0]       kvd_ts,
    input  wire [AW-1:0]       kvd_ks,
    input  wire [AW-1:0]       kvd_js,
    input  wire [15:0]         kvd_tiles,
    input  wire [15:0]         kvd_k,
    input  wire [1:0]          kvd_hg,
    output wire                kv_ok,
    // the core's KV port
    input  wire                re,
    input  wire [G*AW-1:0]     raddr,
    output wire  [G*W*32-1:0]   q,
    input  wire [SW-1:0]       we,
    input  wire [SW*AW-1:0]    waddr,
    input  wire [SW*32-1:0]    wdata,
    // one request channel and one response channel per stack (ot_chip_v41x_hbm_karb K side)
    output wire  [3:0]          m_v,
    input  wire [3:0]          m_rdy,
    output wire  [4*HAW-1:0]    m_addr,
    output wire  [4*4-1:0]      m_len,
    output wire  [4*TAGW-1:0]   m_tag,
    output wire  [3:0]          m_we,
    output wire  [4*256-1:0]    m_wdata,
    output wire  [4*32-1:0]     m_wstrb,
    input  wire [3:0]          s_v,
    output wire [3:0]          s_rdy,
    input  wire [4*TAGW-1:0]   s_tag,
    input  wire [4*4-1:0]      s_beat,
    input  wire [4*256-1:0]    s_data,
    input wire slow_clk, cold_n, slow_rst_n, abort_slow, abort_fast,
    input wire src_launch,
    output wire src_launch_credit,
    input wire [SUN-1:0] src_xwe,
    input wire [SUN*AW-1:0] src_xwaddr,
    input wire [SUN*32-1:0] src_xwdata,
    input wire [3:0] m_wr_done,
    output wire owner_debt, owner_quarantined,
    // status
    output wire                 fault,
    output wire  [4:0]          fault_code,    // [0] slots / size, [1] read, [2] write into a slot being read,
                                              // [3] queue, [4] a sector outside the KV region
    output wire  [31:0]         st_ops,
    output wire  [31:0]         st_words,
    output wire  [31:0]         st_sectors_written,
    output wire  [31:0]         st_refetches,
    output wire  [31:0]         st_wq_high,
    output wire  [31:0]         st_hold_cycles  // cycles kv_ok was low with a descriptor pending
);
    reg [1:0] kstate;
    localparam integer PW=SUN*(1+AW+32);
    initial if(SUN!=256 || AW!=30) $error("full retained SU staging profile required");
    reg reserved, holding, sent, source_fault, source_quarantine;
    reg [PW-1:0] held_payload;
    reg [227:0] held_owner;
    reg [31:0] epoch;reg [15:0] batch;reg [10:0] rid;
    wire in_ready,cross_valid,cross_pending,cross_quarantine;
    wire [PW-1:0] crossed_payload;wire [227:0] crossed_owner;
    wire retired_ready;reg retired;
    wire [227:0] active_owner;
    wire exhausted=(epoch==32'hffffffff && rid==11'h7ff);
    assign src_launch_credit=ENABLE&&cold_n&&slow_rst_n&&!abort_slow&&!reserved&&!source_fault&&!source_quarantine&&!exhausted&&in_ready;
    always @(posedge slow_clk)begin
      if(!cold_n)begin reserved<=0;holding<=0;sent<=0;source_fault<=0;source_quarantine<=0;epoch<=0;batch<=0;rid<=0;held_owner<=0;held_payload<=0;end
      else begin
       if(src_launch)begin
        if(!src_launch_credit)source_fault<=1;
        else begin
          reserved<=1;
          held_owner<={4'd0,165'b0,epoch,batch,rid};
          if(rid==11'h7ff)begin rid<=0;epoch<=epoch+1'b1;batch<=batch+1'b1;end else rid<=rid+1'b1;
        end
       end
       if(|src_xwe)begin
        if(!reserved||holding||sent)source_fault<=1;
        else begin held_payload<={src_xwe,src_xwaddr,src_xwdata};holding<=1;end
       end
       if(holding&&in_ready&&!source_quarantine)begin holding<=0;sent<=1;end
       if(sent&&!cross_pending)begin reserved<=0;sent<=0;end
       if((abort_slow||!slow_rst_n)&&reserved)source_quarantine<=1;
      end
    end
    ot_ds_owned_ratio_boundary #(.W(PW),.ENABLE(ENABLE)) KV_crossing(
      .sclk(slow_clk),.dclk(clk),.cold_n(cold_n),.srst_n(slow_rst_n),.drst_n(rst_n),
      .abort_s(abort_slow),.abort_d(abort_fast),.in_v(holding&&!source_quarantine),.in_ready(in_ready),
      .in_data(held_payload),.in_owner(held_owner),.out_v(cross_valid),.out_ready(kstate==0),
      .out_data(crossed_payload),.out_owner(crossed_owner),.retire_v(retired),.retire_ready(retired_ready),
      .retire_owner(active_owner),.reconcile_v(1'b0),.allcopies_fenced(1'b0),.reconcile_owner(228'b0),
      .pending(cross_pending),.quarantined(cross_quarantine),.pending_owner());
    reg [PW-1:0] burst;
    reg [227:0] kv_owner;
    reg [8:0] cursor;
    reg service_fault;
    assign active_owner=kv_owner;
    wire [SUN-1:0] enables=burst[PW-1-:SUN];
    reg [SUN-1:0] stage_xwe;
    wire [SUN*AW-1:0] stage_xwaddr=burst[SUN*32+:SUN*AW];
    wire [SUN*32-1:0] stage_xwdata=burst[SUN*32-1:0];
    wire sink_ready,sink_visible,kv_fault;
    always @(*)begin
       stage_xwe=0;
       if(kstate==1 && cursor<SUN && enables[cursor])stage_xwe[cursor]=1;
    end
    assign owner_debt=reserved||cross_pending||kstate!=0;
    assign owner_quarantined=source_quarantine||cross_quarantine||service_fault;
    assign fault=source_fault||service_fault||kv_fault;
    always @(posedge clk)begin
       if(!cold_n)begin kstate<=0;burst<=0;kv_owner<=0;cursor<=0;service_fault<=0;retired<=0;end
       else begin
        retired<=0;
        if((abort_fast||!rst_n)&&kstate!=0)service_fault<=1;
        // The old SW writer has no READY. It cannot share the owned SU burst.
        if(kstate!=0 && (|we))service_fault<=1;
        if(!service_fault && rst_n && !abort_fast)case(kstate)
          0:if(cross_valid)begin burst<=crossed_payload;kv_owner<=crossed_owner;cursor<=0;kstate<=1;end
          1:if(!enables[cursor]||sink_ready)begin
              if(cursor==SUN-1)kstate<=2;else cursor<=cursor+1'b1;
            end
          2:if(sink_visible&&retired_ready&&!kv_fault)begin retired<=1;kstate<=0;end
          default:service_fault<=1;
        endcase
       end
    end
    ot_chip_v41x_kv_prefetch_visible #(.WR_VISIBLE(1),.G(G),.W(W),.SW(SW),.SUN(SUN),.AW(AW),.STG(STG),.SAW(SAW),.KV_SBASE(KV_SBASE),.KV_SECTORS(KV_SECTORS),.TROWS(TROWS),.D(D),.HAW(HAW),.TAGW(TAGW),.WQD(WQD),.CMB(CMB)) native_KV(
        .clk(clk),
        .rst_n(cold_n),
        .base(base),
        .kvd_v(kvd_v),
        .kvd_wbase(kvd_wbase),
        .kvd_ts(kvd_ts),
        .kvd_ks(kvd_ks),
        .kvd_js(kvd_js),
        .kvd_tiles(kvd_tiles),
        .kvd_k(kvd_k),
        .kvd_hg(kvd_hg),
        .kv_ok(kv_ok),
        .re(re),
        .raddr(raddr),
        .q(q),
        .we(we),
        .waddr(waddr),
        .wdata(wdata),
        .xwe(stage_xwe),
        .xwaddr(stage_xwaddr),
        .xwdata(stage_xwdata),
        .m_v(m_v),
        .m_rdy(m_rdy),
        .m_addr(m_addr),
        .m_len(m_len),
        .m_tag(m_tag),
        .m_we(m_we),
        .m_wdata(m_wdata),
        .m_wstrb(m_wstrb),
        .s_v(s_v),
        .s_rdy(s_rdy),
        .s_tag(s_tag),
        .s_beat(s_beat),
        .s_data(s_data),
        .fault(kv_fault),
        .fault_code(fault_code),
        .st_ops(st_ops),
        .st_words(st_words),
        .st_sectors_written(st_sectors_written),
        .st_refetches(st_refetches),
        .st_wq_high(st_wq_high),
        .st_hold_cycles(st_hold_cycles),
        .m_wr_done(m_wr_done),.x_ready(sink_ready),.writes_visible(sink_visible));
endmodule
