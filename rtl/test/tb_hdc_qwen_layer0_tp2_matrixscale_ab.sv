`timescale 1ns/1ps
// Real Qwen3-8B layer-0 TP2 RTL gate. The program starts with X already in VM;
// token 0, position 0, and zero KV make the first step reproducible.
// MATRIX_HBM selects bounded PC-local HBM sectors for every layer-0 INT8
// matrix code and BF16 row scale. POST_SCALE_HBM separately selects the
// post-TP o/down scales. Program, images, arithmetic, VM and KV are shared.
module tb_hdc_qwen_layer0_tp2_matrixscale_ab #(
    parameter integer G = 6144,
    parameter integer MATRIX_HBM=0,
    parameter integer POST_SCALE_HBM=0,
    parameter integer VM_ELEMS=177808, KV_ELEMS=8388608,
    parameter integer CODE_WORDS=1488, SCALE_WORDS=50616, CROM_WORDS=543233
) (input wire clk);
    localparam integer D=2, W=16, AW=24, NW=16, PAW=12, DAW=6, FW=512;
    localparam integer X_BASE=4096, H=4096, TMAX=8192, KVH=4, HD=128;
    reg rst_n=0, start=0;
    integer cyc=0;
    wire [D-1:0] s_done, s_fault, core_fault, coll_fault;
    wire [D-1:0] post_ready, post_fault, matrix_fault, norm_ready, norm_fault;
    wire [D-1:0] cv, crdy, cl, cm, rv, rl, rerr;
    wire [D*FW-1:0] cd, rd;
    wire [D*32-1:0] ct;
    wire [D-1:0] rr;
    wire [D*3-1:0] fault_code;
    wire [31:0] link_stalls;
    reg [8*512-1:0] dir;

    ot_rom_oneshot_allreduce #(.N(D),.LANES(W),.TAGW(32),.DEPTH(16),
        .LAT(11),.BPC_NUM(3600)) u_coll (
        .clk(clk),.rst_n(rst_n),
        .in_valid(cv),.in_ready(crdy),.in_data(cd),.in_last(cl),
        .in_mode(cm),.in_tag(ct),
        .out_valid(rv),.out_data(rd),.out_last(rl),.out_rank(rr),
        .out_err(rerr),.fault(coll_fault),.fault_code(fault_code),
        .link_stalls(link_stalls));

    genvar d;
    generate for (d=0; d<D; d=d+1) begin : die
        localparam [7:0] DC=8'h30+d;
        reg [1023:0] prog [0:63];
        reg [63:0] desc [0:7];
        reg [G*W*8-1:0] codes [0:CODE_WORDS-1];
        reg [W*16-1:0] scales [0:SCALE_WORDS-1];
        reg [63:0] constants [0:CROM_WORDS-1];
        reg [31:0] vm [0:VM_ELEMS-1];
        reg [31:0] t1_o_scaled [0:H-1], t1_down_scaled [0:H-1];
        reg [W*32-1:0] kv [0:KV_ELEMS/W-1];

        wire core_start, core_done;
        wire [NW-1:0] core_tok, core_pos, core_ntok, seq_ntok;
        wire [31:0] core_nval, seq_nval, cycles;
        wire [PAW-1:0] prog_base, prog_addr;
        wire prog_re, desc_re;
        wire [DAW-1:0] desc_addr;
        reg [1023:0] prog_q;
        reg [63:0] desc_q;
        wire s_vre, s_vwe;
        wire [7:0] s_vraddr, s_vwaddr;
        wire [FW-1:0] s_vwdata;
        reg [FW-1:0] s_vrq;
        wire coll_busy;

        wire wrom_re, int8_wrom_re, scale_re, crom_re;
        wire [G-1:0] scale_gre, vx_re, vw_me_we;
        wire [AW-1:0] wrom_addr, int8_wrom_addr, crom_addr;
        wire [G*AW-1:0] scale_addr, kv_raddr, vx_addr, vw_me_addr, me_oaddr;
        reg [G*W*8-1:0] int8_wrom_q;
        reg [G*W*16-1:0] scale_q;
        wire [G*W*8-1:0] matrix_hbm_code_q;
        wire [G*W*16-1:0] matrix_hbm_scale_q;
        wire wd_v, w_ok;
        wire [AW-1:0] wd_wbase, wd_sbase;
        wire [NW-1:0] wd_tiles, wd_k, wd_nout;
        wire [63:0] crom_q;
        reg [63:0] crom_local_q;
        reg crom_post_sel_q=0;
        reg crom_norm_sel_q=0;
        wire [63:0] crom_post_q;
        wire [63:0] crom_norm_q;
        wire kv_re, kv_we, va_re, vb_re, vc_re;
        wire [AW-1:0] kv_waddr, va_addr, vb_addr, vc_addr;
        reg [G*W*32-1:0] kv_q;
        reg [G*32-1:0] vx_q;
        reg [31:0] va_q, vb_q, vc_q;
        wire [31:0] kv_wdata, vw_su_data, vw_rd_data;
        wire [AW-1:0] vw_su_addr, vw_rd_addr, vw_mx_addr;
        wire vw_su_we, vw_rd_we, vw_mx_we;
        wire [G*W-1:0] vw_me_mask, me_omask;
        wire [G*W*32-1:0] vw_me_data, me_odata;
        wire [W-1:0] vw_mx_mask;
        wire [W*32-1:0] vw_mx_data;
        wire me_ov;
        wire crom_post_hit = crom_addr>=535041 && crom_addr<543233;
        wire crom_norm_hit = crom_addr>=4096 && crom_addr<6656;
        assign crom_q = (MATRIX_HBM && crom_norm_sel_q) ? crom_norm_q :
                        (POST_SCALE_HBM && crom_post_sel_q) ? crom_post_q : crom_local_q;

        if (MATRIX_HBM != 0) begin : g_norm_hbm
            localparam integer PC=32, HAW=28, TAGW=8;
            wire [PC-1:0] rq_v;
            wire [PC*HAW-1:0] rq_addr;
            wire [PC*TAGW-1:0] rq_tag;
            reg [PC-1:0] rsp_v=0;
            reg [PC*TAGW-1:0] rsp_tag=0;
            reg [PC*256-1:0] rsp_data=0;
            integer sectors=0, pp, jj, sector;
            ot_hdc_qwen_post_tp_scale_hbm #(.PCS(PC),.TAGW(TAGW),
                .ROWS_PER_SCALE(1280),.CROM_BASE(4096)) source (
                .clk(clk),.rst_n(rst_n),.load(cyc==6),
                .hbm_base_sector(28'h3000000),.ready(norm_ready[d]),.fault(norm_fault[d]),
                .crom_re(crom_re && crom_norm_hit),.crom_addr(crom_addr),.crom_q(crom_norm_q),
                .rq_v(rq_v),.rq_rdy({PC{1'b1}}),.rq_addr(rq_addr),.rq_tag(rq_tag),
                .rsp_v(rsp_v),.rsp_tag(rsp_tag),.rsp_data(rsp_data));
            always @(posedge clk) begin
                rsp_v<=rq_v; rsp_tag<=rq_tag;
                for (pp=0;pp<PC;pp=pp+1) if (rq_v[pp]) begin
                    sector=rq_addr[pp*HAW +: HAW]-28'h3000000;
                    if (sector<0 || sector>=640) $fatal(1,"qk-norm sector %0d",sector);
                    for (jj=0;jj<4;jj=jj+1)
                        rsp_data[pp*256+jj*64 +:64]<=constants[4096+sector*4+jj];
                    sectors=sectors+1;
                end
            end
            final $display("NORM_HBM die=%0d sectors=%0d",d,sectors);
        end else begin : g_norm_rom
            assign norm_ready[d]=1'b1;
            assign norm_fault[d]=1'b0;
            assign crom_norm_q=0;
        end
        if (POST_SCALE_HBM != 0) begin : g_post_hbm
            localparam integer PC=32, HAW=28, TAGW=8;
            wire [PC-1:0] rq_v;
            wire [PC*HAW-1:0] rq_addr;
            wire [PC*TAGW-1:0] rq_tag;
            reg [PC-1:0] rsp_v=0;
            reg [PC*TAGW-1:0] rsp_tag=0;
            reg [PC*256-1:0] rsp_data=0;
            integer sectors=0, pp, jj, sector;
            ot_hdc_qwen_post_tp_scale_hbm #(.PCS(PC),.TAGW(TAGW)) source (
                .clk(clk),.rst_n(rst_n),.load(cyc==6),
                .hbm_base_sector(28'h4000000),.ready(post_ready[d]),.fault(post_fault[d]),
                .crom_re(crom_re && crom_post_hit),.crom_addr(crom_addr),.crom_q(crom_post_q),
                .rq_v(rq_v),.rq_rdy({PC{1'b1}}),.rq_addr(rq_addr),.rq_tag(rq_tag),
                .rsp_v(rsp_v),.rsp_tag(rsp_tag),.rsp_data(rsp_data));
            always @(posedge clk) begin
                rsp_v<=rq_v; rsp_tag<=rq_tag;
                for (pp=0;pp<PC;pp=pp+1) if (rq_v[pp]) begin
                    sector=rq_addr[pp*HAW +: HAW]-28'h4000000;
                    if (sector<0 || sector>=2048) $fatal(1,"post-scale sector %0d",sector);
                    for (jj=0;jj<4;jj=jj+1)
                        rsp_data[pp*256+jj*64 +:64]<=constants[535041+sector*4+jj];
                    sectors=sectors+1;
                end
            end
            final $display("POST_SCALE_HBM die=%0d sectors=%0d",d,sectors);
        end else begin : g_post_rom
            assign post_ready[d]=1'b1;
            assign post_fault[d]=1'b0;
            assign crom_post_q=0;
        end

        if (MATRIX_HBM != 0) begin : g_matrix_hbm
            localparam integer PC=32, HAW=28, TAGW=17;
            localparam integer CODE_SECTORS=G*W/32;
            localparam [HAW-1:0] SCALE_REGION=28'h1000000;
            wire [PC-1:0] rq_v;
            wire [PC*HAW-1:0] rq_addr;
            wire [PC*TAGW-1:0] rq_tag;
            reg [PC-1:0] rsp_v=0;
            reg [PC*TAGW-1:0] rsp_tag=0;
            reg [PC*256-1:0] rsp_data=0;
            wire [NW-1:0] wd_words=wd_tiles*wd_k*8;
            ot_hdc_qwen_int8_pc_window #(.G(G),.W(W),.AW(AW),.HAW(HAW),
                .NW(NW),.PCS(PC),.WIN_WORDS(512),.SCALE_WORDS(768),
                .TAGW(TAGW)) source (
                .clk(clk),.rst_n(rst_n),.load(wd_v),
                .op_base(wd_wbase),.op_scale_base(wd_sbase),
                .op_words(wd_words),.op_nout(wd_nout),
                .code_base_sector(28'd0),.scale_base_sector(SCALE_REGION),
                .ready(w_ok),.fault(matrix_fault[d]),
                .code_re(int8_wrom_re),.code_addr(int8_wrom_addr),
                .code_q(matrix_hbm_code_q),
                .scale_re(scale_re),.scale_gre(scale_gre),.scale_addr(scale_addr),
                .scale_q(matrix_hbm_scale_q),
                .rq_v(rq_v),.rq_rdy({PC{1'b1}}),.rq_addr(rq_addr),.rq_tag(rq_tag),
                .rsp_v(rsp_v),.rsp_tag(rsp_tag),.rsp_data(rsp_data));
            for (genvar pc=0;pc<PC;pc=pc+1) begin : g_pc
                integer sector;
                integer code_sectors=0, scale_sectors=0;
                always @(posedge clk) begin
                    rsp_v[pc] <= rq_v[pc];
                    if (rq_v[pc]) begin
                        rsp_tag[pc*TAGW +: TAGW] <= rq_tag[pc*TAGW +: TAGW];
                        if (rq_addr[pc*HAW +: HAW] < SCALE_REGION) begin
                            sector=rq_addr[pc*HAW +: HAW];
                            if (sector/CODE_SECTORS >= CODE_WORDS)
                                $fatal(1,"matrix code HBM sector %0d",sector);
                            rsp_data[pc*256 +: 256] <=
                                codes[sector/CODE_SECTORS][(sector%CODE_SECTORS)*256 +: 256];
                            code_sectors <= code_sectors+1;
                        end else begin
                            sector=rq_addr[pc*HAW +: HAW]-SCALE_REGION;
                            if (sector >= SCALE_WORDS)
                                $fatal(1,"matrix scale HBM sector %0d",sector);
                            rsp_data[pc*256 +: 256] <= scales[sector];
                            scale_sectors <= scale_sectors+1;
                        end
                    end
                end
                final $display("MATRIX_HBM die=%0d pc=%0d code_sectors=%0d scale_sectors=%0d",
                    d,pc,code_sectors,scale_sectors);
            end
        end else begin : g_matrix_rom
            assign w_ok=1'b1;
            assign matrix_fault[d]=1'b0;
            assign matrix_hbm_code_q=0;
            assign matrix_hbm_scale_q=0;
        end

        ot_hdc_core_vector_weight #(.W(W),.G(G),.AW(AW),.NW(NW),.PAW(PAW),
            .W_HBM(MATRIX_HBM),
            .INT8_WEIGHT(1),.INT8_SCALE_WCS_BASE(1),.INT8_EMBED(0)) core (
            .clk(clk),.rst_n(rst_n),.start(core_start),.token(core_tok),.pos(core_pos),
            .done(core_done),.next_token(core_ntok),.next_val(core_nval),
            .cycles(cycles),.fault(core_fault[d]),
            .prog_re(prog_re),.prog_addr(prog_addr),.prog_q(prog_q),
            .wrom_re(wrom_re),.wrom_addr(wrom_addr),.wrom_q({(G*W*16){1'b0}}),
            .int8_wrom_re(int8_wrom_re),.int8_wrom_addr(int8_wrom_addr),
            .int8_wrom_q(MATRIX_HBM ? matrix_hbm_code_q : int8_wrom_q),
            .scale_re(scale_re),.scale_gre(scale_gre),.scale_addr(scale_addr),
            .scale_q(MATRIX_HBM ? matrix_hbm_scale_q : scale_q),
            .embed_code_q(512'd0),.embed_scale_q(16'd0),
            .crom_re(crom_re),.crom_addr(crom_addr),.crom_q(crom_q),
            .kv_re(kv_re),.kv_raddr(kv_raddr),.kv_q(kv_q),
            .kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),
            .vx_re(vx_re),.vx_addr(vx_addr),.vx_q(vx_q),
            .va_re(va_re),.va_addr(va_addr),.va_q(va_q),
            .vb_re(vb_re),.vb_addr(vb_addr),.vb_q(vb_q),
            .vc_re(vc_re),.vc_addr(vc_addr),.vc_q(vc_q),
            .vw_me_we(vw_me_we),.vw_me_addr(vw_me_addr),.vw_me_mask(vw_me_mask),.vw_me_data(vw_me_data),
            .vw_mx_we(vw_mx_we),.vw_mx_addr(vw_mx_addr),.vw_mx_mask(vw_mx_mask),.vw_mx_data(vw_mx_data),
            .vw_su_we(vw_su_we),.vw_su_addr(vw_su_addr),.vw_su_data(vw_su_data),
            .vw_rd_we(vw_rd_we),.vw_rd_addr(vw_rd_addr),.vw_rd_data(vw_rd_data),
            .me_ov(me_ov),.me_oaddr(me_oaddr),.me_omask(me_omask),.me_odata(me_odata),
            .kv_ok(1'b1),.kv_write_drained(1'b1),
            .wd_v(wd_v),.wd_wbase(wd_wbase),.wd_sbase(wd_sbase),
            .wd_tiles(wd_tiles),.wd_k(wd_k),.wd_nout(wd_nout),
            .w_ok(w_ok),.emb_ok(1'b1));

        ot_rom_tp_seq #(.N(D),.NW(NW),.PAW(PAW),.VWA(8),.DAW(DAW),.FW(FW),.TAGW(32)) seq (
            .clk(clk),.rst_n(rst_n),.start(start),.token(16'd0),.pos(16'd0),
            .done(s_done[d]),.next_token(seq_ntok),.next_val(seq_nval),
            .fault(s_fault[d]),.coll_busy(coll_busy),
            .core_start(core_start),.core_token(core_tok),.core_pos(core_pos),
            .core_done(core_done),.core_next_token(core_ntok),.core_next_val(core_nval),
            .core_fault(core_fault[d]),.prog_base(prog_base),
            .desc_re(desc_re),.desc_addr(desc_addr),.desc_q(desc_q),
            .vm_re(s_vre),.vm_raddr(s_vraddr),.vm_rq(s_vrq),
            .vm_we(s_vwe),.vm_waddr(s_vwaddr),.vm_wdata(s_vwdata),
            .c_valid(cv[d]),.c_ready(crdy[d]),.c_data(cd[d*FW +: FW]),
            .c_last(cl[d]),.c_mode(cm[d]),.c_tag(ct[d*32 +: 32]),
            .r_valid(rv[d]),.r_data(rd[d*FW +: FW]),.r_last(rl[d]),
            .r_rank(rr[d]),.r_err(rerr[d]));

        integer i, g, l;
        reg [8*512-1:0] pdir;
        initial begin
            if (!$value$plusargs("DIR=%s",pdir)) $fatal(1,"+DIR required");
            $readmemh({pdir,"/die",DC,"/program.hex"},prog);
            $readmemh({pdir,"/die",DC,"/segments.hex"},desc);
            $readmemh({pdir,"/die",DC,"/matrix_int8.hex"},codes);
            $readmemh({pdir,"/die",DC,"/matrix_scale_bf16.hex"},scales);
            $readmemh({pdir,"/die",DC,"/crom.hex"},constants);
            for (i=0;i<VM_ELEMS;i=i+1) vm[i]=0;
            for (i=0;i<H;i=i+1) begin t1_o_scaled[i]=0; t1_down_scaled[i]=0; end
            for (i=0;i<KV_ELEMS/W;i=i+1) kv[i]=0;
            $readmemh({pdir,"/vm_x_fp32.hex"},vm);
        end
        always @(posedge clk) begin
            if (prog_re) prog_q <= prog[prog_base+prog_addr];
            if (desc_re) desc_q <= desc[desc_addr];
            if (wrom_re) $fatal(1,"BF16 weight ROM requested");
            if (int8_wrom_re && !MATRIX_HBM) begin
                if (int8_wrom_addr >= CODE_WORDS) $fatal(1,"code ROM address %0d",int8_wrom_addr);
                int8_wrom_q <= codes[int8_wrom_addr];
            end
            for (g=0;g<G;g=g+1) if (scale_gre[g] && !MATRIX_HBM) begin
                if (scale_addr[g*AW +: AW] >= SCALE_WORDS)
                    $fatal(1,"scale ROM address %0d group %0d",scale_addr[g*AW +: AW],g);
                scale_q[g*W*16 +: W*16] <= scales[scale_addr[g*AW +: AW]];
            end
            if (crom_re) begin
                if (crom_addr >= CROM_WORDS) $fatal(1,"constant ROM address %0d",crom_addr);
                crom_post_sel_q <= POST_SCALE_HBM && crom_post_hit;
                crom_norm_sel_q <= MATRIX_HBM && crom_norm_hit;
                if (!(POST_SCALE_HBM && crom_post_hit) &&
                    !(MATRIX_HBM && crom_norm_hit)) crom_local_q <= constants[crom_addr];
            end
            for (g=0;g<G;g=g+1) begin
                if (kv_re) kv_q[g*W*32 +: W*32] <= kv[kv_raddr[g*AW +: AW]];
                if (vx_re[g]) vx_q[g*32 +: 32] <= vm[vx_addr[g*AW +: AW]];
                if (vw_me_we[g])
                    for (l=0;l<W;l=l+1)
                        if (vw_me_mask[g*W+l]) vm[(vw_me_addr[g*AW +: AW]<<4)+l] <= vw_me_data[(g*W+l)*32 +: 32];
            end
            if (va_re) va_q <= vm[va_addr];
            if (vb_re) vb_q <= vm[vb_addr];
            if (vc_re) vc_q <= vm[vc_addr];
            if (kv_we) kv[kv_waddr>>4][(kv_waddr[3:0])*32 +: 32] <= kv_wdata;
            if (vw_mx_we) for (l=0;l<W;l=l+1)
                if (vw_mx_mask[l]) vm[(vw_mx_addr<<4)+l] <= vw_mx_data[l*32 +: 32];
            if (vw_su_we) begin
                vm[vw_su_addr] <= vw_su_data;
                if (vw_su_addr < H && prog_base==21) t1_o_scaled[vw_su_addr] <= vw_su_data;
                if (vw_su_addr < H && prog_base==30) t1_down_scaled[vw_su_addr] <= vw_su_data;
            end
            if (vw_rd_we) vm[vw_rd_addr] <= vw_rd_data;
            if (s_vre) for (l=0;l<W;l=l+1) s_vrq[l*32 +: 32] <= vm[(s_vraddr<<4)+l];
            if (s_vwe) for (l=0;l<W;l=l+1) vm[(s_vwaddr<<4)+l] <= s_vwdata[l*32 +: 32];
        end

        integer fd_x, fd_t, fd_to, fd_td, fd_k, fd_v, h, dim, ka, va;
        task automatic dump_result;
            begin
                fd_x=$fopen({pdir,"/die",DC,"/x_final.hex"},"w");
                fd_t=$fopen({pdir,"/die",DC,"/t1_final.hex"},"w");
                fd_to=$fopen({pdir,"/die",DC,"/t1_after_o_scale.hex"},"w");
                fd_td=$fopen({pdir,"/die",DC,"/t1_after_down_scale.hex"},"w");
                fd_k=$fopen({pdir,"/die",DC,"/k_pos0.hex"},"w");
                fd_v=$fopen({pdir,"/die",DC,"/v_pos0.hex"},"w");
                for (i=0;i<H;i=i+1) begin
                    $fdisplay(fd_x,"%08x",vm[X_BASE+i]);
                    $fdisplay(fd_t,"%08x",vm[i]);
                    $fdisplay(fd_to,"%08x",t1_o_scaled[i]);
                    $fdisplay(fd_td,"%08x",t1_down_scaled[i]);
                end
                for (h=0;h<KVH;h=h+1) for (dim=0;dim<HD;dim=dim+1) begin
                    ka=((h*(TMAX/W))*HD+dim)*W;
                    va=KVH*TMAX*HD+(h*TMAX)*HD+dim;
                    $fdisplay(fd_k,"%08x",kv[ka/W][(ka%W)*32 +: 32]);
                    $fdisplay(fd_v,"%08x",kv[va/W][(va%W)*32 +: 32]);
                end
                $fclose(fd_x); $fclose(fd_t); $fclose(fd_to); $fclose(fd_td);
                $fclose(fd_k); $fclose(fd_v);
            end
        endtask
    end endgenerate

    initial begin
        if (!$value$plusargs("DIR=%s",dir)) $fatal(1,"+DIR required");
    end
    reg finished=0;
    reg started=0;
    always @(posedge clk) begin
        cyc <= cyc+1;
        if (cyc==5) rst_n <= 1;
        if (cyc>=7 && (&post_ready) && (&norm_ready) && !started) begin
            start <= 1; started <= 1;
        end
        else start <= 0;
        if (cyc>8 && &s_done && !finished) begin
            finished <= 1;
            if (|s_fault || |core_fault || |coll_fault || |post_fault ||
                |matrix_fault || |norm_fault)
                $fatal(1,"layer0 fault seq=%b core=%b coll=%b post=%b matrix=%b norm=%b",
                    s_fault,core_fault,coll_fault,post_fault,matrix_fault,norm_fault);
            die[0].dump_result(); die[1].dump_result();
            $display("QWEN_LAYER0_TP2_MATRIXSCALE PASS dies=2 token=0 pos=0 matrix_hbm=%0d post_hbm=%0d cycles=%0d seq_fault=%b core_fault=%b coll_fault=%b post_fault=%b matrix_fault=%b",
                MATRIX_HBM,POST_SCALE_HBM,cyc,s_fault,core_fault,coll_fault,post_fault,matrix_fault);
            $finish;
        end
        if (cyc>10000000) $fatal(1,"layer0 timeout");
    end
endmodule
