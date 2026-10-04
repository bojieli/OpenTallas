`timescale 1ns/1ps
// Row-layout index-key reader bench: four HBM3E stacks of one rank (die), each stack its own
// ot_hdc_v41x_idx_kgrow straight into its timing-faithful controller (ot_hdc_v41x_idx_hbm_trace: the
// ot_hdc_v41x_idx_hbm model plus a DRAM command log and rule checker, refresh live: REFpb, REFPB = 3).
// +PFX=<path>: <path>.cmd holds one line per stack "range n row0 x0 cblk qbase" (decimal): list mode
// (range 0: the stack's candidate list in <path>.s<q>, first line the count, then one local block index
// per line, hex, ascending) or range mode (range 1: blocks 0 .. n - 1); the quarter starts at ring block
// x0 of a cblk-block ring, region row row0; qbase = the rank-local position of the quarter's key 0.
// One command starts all four stacks at once (cycle t0).
// RT = 0: the controllers return the sector-address pattern (MEM_MODE 1); every key of every beat is
//   checked against the pattern of the three sectors the row layout puts it in.
// RT = 1 (write -> read ROUND TRIP): the controllers hold a backing array (MEM_MODE 0); first the row-layout
//   WRITER (ot_hdc_v41x_idx_ring_kwr_row) runs the commands of <path>.wr ("op n pos", decimal: op 1 PLACE
//   position pos of a count-n state, op 0 STEP: append position n, count n + 1, with the ring migration
//   when n + 1 is a multiple of 32) with key(pos) = a 544-bit hash of (+RANK, pos), and waits until every
//   write has completed; then the readers run and every key of every beat must equal key(qbase + 8 j + k)
//   -- the bytes the writer wrote, through the controller's array.
// Every block index is checked against the list / range, in order; the HBM sectors read must be exactly 17
// a block (plus the writer's migration reads in RT mode).  <path>.out gets one line per output beat
// "stack cycle kv blk0 blk1".  Prints KGSTACK / KGHBM / DRAMCHK lines per stack and KGROW_PASS.
module tb_hdc_v41x_idx_kgrow #(
    parameter integer MAX_CYCLES=2000000,
    parameter integer WB=512, NE=16, QD=64, RQD=32, RW=16, MAXSKIP=16, CLK_PS=833,
    parameter integer RT=0, REFPB=3,
    parameter longint REFI_PS=3900000
) (input wire clk);
    localparam integer NPC=32,AW=28,TAGW=16,LENW=4,BEATW=4,DW=256,LBW=14,LMW=11;
    localparam integer MEMW = RT ? (1 << 21) : 1;
`include "ot_hdc_v41x_idx_rowmap.svh"
    reg rst_n=0, cmd_v=0;
    reg [3:0] lw_v=0;
    reg [LMW-1:0] lw_addr=0;
    reg [LBW-1:0] lw_blk [0:3];
    wire [3:0] s_busy,s_valid,s_fault;
    wire [4*16-1:0] s_kv;
    wire [4*16*544-1:0] s_key;
    wire [4*2*LBW-1:0] s_blk;
    wire [4*48-1:0] s_keys,s_beats;
    // reader ports
    wire [4*NPC-1:0] k_req_v,k_rsp_rdy;
    wire [4*NPC*AW-1:0] k_req_addr;
    wire [4*NPC*LENW-1:0] k_req_len;
    wire [4*NPC*TAGW-1:0] k_req_tag;
    // writer ports
    wire [4*NPC-1:0] w_req_v,w_req_we,w_rsp_rdy;
    wire [4*NPC*AW-1:0] w_req_addr;
    wire [4*NPC*LENW-1:0] w_req_len;
    wire [4*NPC*TAGW-1:0] w_req_tag;
    wire [4*NPC*DW-1:0] w_req_wdata;
    wire [4*NPC*(DW/8)-1:0] w_req_wstrb;
    // controller ports
    wire [4*NPC-1:0] h_req_v,h_req_rdy,h_req_we,h_rsp_v,h_rsp_rdy,h_wr_done;
    wire [4*NPC*AW-1:0] h_req_addr;
    wire [4*NPC*LENW-1:0] h_req_len;
    wire [4*NPC*TAGW-1:0] h_req_tag,h_rsp_tag;
    wire [4*NPC*BEATW-1:0] h_rsp_beat;
    wire [4*NPC*DW-1:0] h_rsp_data,h_req_wdata;
    wire [4*NPC*(DW/8)-1:0] h_req_wstrb;
    reg wphase = (RT != 0);
    assign h_req_v    = wphase ? w_req_v    : k_req_v;
    assign h_req_addr = wphase ? w_req_addr : k_req_addr;
    assign h_req_len  = wphase ? w_req_len  : k_req_len;
    assign h_req_tag  = wphase ? w_req_tag  : k_req_tag;
    assign h_req_we   = wphase ? w_req_we   : {4*NPC{1'b0}};
    assign h_req_wdata= wphase ? w_req_wdata: {4*NPC*DW{1'b0}};
    assign h_req_wstrb= wphase ? w_req_wstrb: {4*NPC*(DW/8){1'b0}};
    assign h_rsp_rdy  = wphase ? w_rsp_rdy  : k_rsp_rdy;
    wire [4*NPC-1:0] k_rsp_v = wphase ? {4*NPC{1'b0}} : h_rsp_v;
    wire [4*NPC-1:0] w_rsp_v = wphase ? h_rsp_v : {4*NPC{1'b0}};

    integer c_rng [0:3], c_n [0:3], c_row0 [0:3], c_x0 [0:3], c_cblk [0:3], c_qbase [0:3];
    integer nlist [0:3];
    reg [LBW-1:0] list [0:4*2048-1];
    integer RANK = 0;
    reg dump=0;
    integer evd=-1;
    genvar s;
    generate for(s=0;s<4;s=s+1) begin:g_stack
        always @(posedge clk) if(dump) begin : g_dump
            longint rd,wr,act,hit,conf,refs,rmin,rmax;
            rd=0;wr=0;act=0;hit=0;conf=0;refs=0;rmin=64'h7fffffffffffffff;rmax=0;
            for(integer p=0;p<NPC;p=p+1) begin
                rd+=hm.st_rd[p];wr+=hm.st_wr[p];act+=hm.st_act[p];hit+=hm.st_hit[p];
                conf+=hm.st_conf[p];refs+=hm.st_ref[p];
                if(hm.st_rd[p]<rmin) rmin=hm.st_rd[p];
                if(hm.st_rd[p]>rmax) rmax=hm.st_rd[p];
            end
            $display("KGHBM s=%0d rd=%0d act=%0d hit=%0d conf=%0d ref=%0d bp=%0d lat_sum_ps=%0d lat_max_ps=%0d pc_rd_min=%0d pc_rd_max=%0d wr=%0d",
                     s,rd,act,hit,conf,refs,hm.st_bp_cycles,hm.st_rd_lat_sum,hm.st_rd_lat_max,rmin,rmax,wr);
            hm.dram_check(s);
            if($value$plusargs("EVDUMP=%d",evd) && evd/100==s) begin : g_ev
                bit [127:0] eq [$];
                eq = hm.tq[evd%100]; eq.sort();
                foreach(eq[i]) $display("KGEV s=%0d pc=%0d t=%0d kind=%0d bank=%0d row=%0d",s,evd%100,
                                        eq[i][127:64],eq[i][63:60],eq[i][59:52],eq[i][51:20]);
            end
            if($test$plusargs("PCDUMP"))
                for(integer p=0;p<NPC;p=p+1)
                    $display("KGPC s=%0d pc=%0d rd=%0d act=%0d conf=%0d last_col_ps=%0d",s,p,hm.st_rd[p],hm.st_act[p],
                             hm.st_conf[p],hm.last_col[p]);
        end
        ot_hdc_v41x_idx_hbm_trace #(.NPC(NPC),.AW(AW),.DW(DW),.MEM_WORDS(MEMW),
            .TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),.QD(QD),.RQD(RQD),.RW(RW),.MAXSKIP(MAXSKIP),.CLK_PS(CLK_PS),
            .REFPB(REFPB),.REFI_PS(REFI_PS),.MEM_MODE(RT ? 0 : 1)) hm (
            .clk(clk),.rst_n(rst_n),.req_v(h_req_v[s*NPC +:NPC]),
            .req_rdy(h_req_rdy[s*NPC +:NPC]),
            .req_addr(h_req_addr[s*NPC*AW +:NPC*AW]),
            .req_len(h_req_len[s*NPC*LENW +:NPC*LENW]),
            .req_tag(h_req_tag[s*NPC*TAGW +:NPC*TAGW]),
            .req_we(h_req_we[s*NPC +:NPC]),.req_wdata(h_req_wdata[s*NPC*DW +:NPC*DW]),
            .req_wstrb(h_req_wstrb[s*NPC*(DW/8) +:NPC*(DW/8)]),.wr_done(h_wr_done[s*NPC +:NPC]),
            .rsp_v(h_rsp_v[s*NPC +:NPC]),.rsp_rdy(h_rsp_rdy[s*NPC +:NPC]),
            .rsp_tag(h_rsp_tag[s*NPC*TAGW +:NPC*TAGW]),
            .rsp_beat(h_rsp_beat[s*NPC*BEATW +:NPC*BEATW]),
            .rsp_data(h_rsp_data[s*NPC*DW +:NPC*DW]));
        ot_hdc_v41x_idx_kgrow #(.NPC(NPC),.WB(WB),.AW(AW),.TAGW(TAGW),.LENW(LENW),
            .DW(DW),.LBW(LBW),.LMW(LMW),.NE(NE)) kg (
            .clk(clk),.rst_n(rst_n),.lw_v(lw_v[s]),.lw_addr(lw_addr),.lw_blk(lw_blk[s]),
            .cmd_v(cmd_v),.cmd_range(c_rng[s]!=0),.cmd_row0((AW-15)'(c_row0[s])),.cmd_x0(LBW'(c_x0[s])),
            .cmd_cblk((LBW+1)'(c_cblk[s])),.cmd_n((LBW+1)'(c_rng[s]!=0 ? c_n[s] : nlist[s])),
            .busy(s_busy[s]),.fault(s_fault[s]),
            .req_v(k_req_v[s*NPC +:NPC]),.req_rdy(h_req_rdy[s*NPC +:NPC]),
            .req_addr(k_req_addr[s*NPC*AW +:NPC*AW]),
            .req_len(k_req_len[s*NPC*LENW +:NPC*LENW]),
            .req_tag(k_req_tag[s*NPC*TAGW +:NPC*TAGW]),
            .rsp_v(k_rsp_v[s*NPC +:NPC]),.rsp_rdy(k_rsp_rdy[s*NPC +:NPC]),
            .rsp_tag(h_rsp_tag[s*NPC*TAGW +:NPC*TAGW]),
            .rsp_data(h_rsp_data[s*NPC*DW +:NPC*DW]),
            .o_valid(s_valid[s]),.o_ready(1'b1),
            .o_kv(s_kv[s*16 +:16]),.o_key(s_key[s*16*544 +:16*544]),.o_blk(s_blk[s*2*LBW +:2*LBW]),
            .cnt_keys_streamed(s_keys[s*48 +:48]),
            .cnt_hbm_beats(s_beats[s*48 +:48]));
    end endgenerate

    // ---- writer (RT) -----------------------------------------------------------------------------
    reg          wc_v = 0, wc_op = 0;
    reg [32:0]   wc_n = 0, wc_pos = 0;
    reg [543:0]  wc_key = 0;
    wire         wc_rdy, w_busy, w_fault;
    wire [47:0]  w_nkeys, w_nmig, w_ncopy;
    generate if (RT != 0) begin : g_wr
        ot_hdc_v41x_idx_ring_kwr_row #(.NPC(NPC),.AW(AW),.HW(23),.TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),.DW(DW),
            .UW(10),.RSB(64),.RTAIL(32)) wr (
            .clk(clk),.rst_n(rst_n),.cfg_row0((AW-15)'(c_row0[0])),.c_v(wc_v),.c_rdy(wc_rdy),.c_op(wc_op),
            .c_user(10'd0),.c_n(wc_n),.c_pos(wc_pos),.c_key(wc_key),.busy(w_busy),.fault(w_fault),
            .h_req_v(w_req_v),.h_req_rdy(h_req_rdy),.h_req_addr(w_req_addr),.h_req_len(w_req_len),
            .h_req_tag(w_req_tag),.h_req_we(w_req_we),.h_req_wdata(w_req_wdata),.h_req_wstrb(w_req_wstrb),
            .h_wr_done(h_wr_done),.h_rsp_v(w_rsp_v),.h_rsp_rdy(w_rsp_rdy),.h_rsp_tag(h_rsp_tag),
            .h_rsp_data(h_rsp_data),.cnt_keys(w_nkeys),.cnt_migrations(w_nmig),.cnt_copied_sectors(w_ncopy));
    end else begin : g_nowr
        assign wc_rdy = 1'b0; assign w_busy = 1'b0; assign w_fault = 1'b0;
        assign w_req_v = 0; assign w_req_addr = 0; assign w_req_len = 0; assign w_req_tag = 0; assign w_req_we = 0;
        assign w_req_wdata = 0; assign w_req_wstrb = 0; assign w_rsp_rdy = {4*NPC{1'b1}};
        assign w_nkeys = 0; assign w_nmig = 0; assign w_ncopy = 0;
    end endgenerate

    function automatic [255:0] pat(input [AW-1:0] sec);
        integer w;
        begin for(w=0;w<8;w=w+1)
            pat[32*w +:32]=(sec*32'd8+w)*32'h9E3779B1 ^ 32'h5bd1e995;
        end
    endfunction
    function automatic [543:0] keyfn(input integer rank, input integer pos);
        integer w;
        begin for(w=0;w<17;w=w+1)
            keyfn[32*w +:32]=((32'(pos)*32'd17+32'(w))*32'h9E3779B1 + 32'(rank)*32'h85EBCA77) ^ 32'h7F4A7C15;
        end
    endfunction
    // stack a, local block lb, key k of the block
    function automatic [543:0] expkey(input integer a,input integer lb,input integer k);
        integer x;
        reg [255:0] sw;
        begin
            if (RT != 0) expkey = keyfn(RANK, c_qbase[a] + 8*lb + k);
            else begin
                x = c_x0[a] + lb; if (x >= c_cblk[a]) x = x - c_cblk[a];
                sw = pat(AW'(idx_rowmap_sec(32'(c_row0[a]), 32'(x), 5'd0)));
                expkey = {sw[32*k +:32], pat(AW'(idx_rowmap_sec(32'(c_row0[a]), 32'(x), 5'(2+2*k)))),
                                        pat(AW'(idx_rowmap_sec(32'(c_row0[a]), 32'(x), 5'(1+2*k))))};
            end
        end
    endfunction
    // ---- load ----------------------------------------------------------------------------------------
    string pfx;
    integer nwr = 0;
    integer wr_op [$], wr_n [$], wr_pos [$];
    integer fo;
    initial begin : load
        integer fd,q,i,v,r,a,b,c2;
        if(!$value$plusargs("PFX=%s",pfx)) $fatal(1,"+PFX required");
        void'($value$plusargs("RANK=%d",RANK));
        fd=$fopen($sformatf("%s.cmd",pfx),"r");
        if(fd==0) $fatal(1,"cannot open cmd");
        for(q=0;q<4;q=q+1) r=$fscanf(fd,"%d %d %d %d %d %d",c_rng[q],c_n[q],c_row0[q],c_x0[q],c_cblk[q],c_qbase[q]);
        $fclose(fd);
        for(q=0;q<4;q=q+1) begin
            nlist[q]=0;
            if(c_rng[q]==0) begin
                fd=$fopen($sformatf("%s.s%0d",pfx,q),"r");
                if(fd==0) $fatal(1,"cannot open list %0d",q);
                r=$fscanf(fd,"%d",nlist[q]);
                if(nlist[q]>2048) $fatal(1,"list too long");
                for(i=0;i<nlist[q];i=i+1) begin r=$fscanf(fd,"%h",v); list[q*2048+i]=LBW'(v); end
                $fclose(fd);
            end
        end
        if(RT!=0) begin
            fd=$fopen($sformatf("%s.wr",pfx),"r");
            if(fd==0) $fatal(1,"cannot open wr");
            while($fscanf(fd,"%d %d %d",a,b,c2)==3) begin wr_op.push_back(a); wr_n.push_back(b); wr_pos.push_back(c2); end
            $fclose(fd);
        end
        fo=$fopen($sformatf("%s.out",pfx),"w");
    end
    integer cyc=0, t0=-1, wi=0, lastc=-1, wcmd=0, tw0=-1, tw1=-1;
    integer ptr [0:3];
    integer firsto [0:3];
    integer lasto [0:3];
    integer q,b,k,nk,want;
    reg [3:0] done4;
    initial for(q=0;q<4;q=q+1) begin ptr[q]=0; firsto[q]=-1; lasto[q]=-1; end
    function automatic integer blk_at(input integer qq, input integer idx);
        blk_at = (c_rng[qq]!=0) ? idx : int'(list[qq*2048+idx]);
    endfunction
    function automatic integer nblk(input integer qq);
        nblk = (c_rng[qq]!=0) ? c_n[qq] : nlist[qq];
    endfunction
    always @(posedge clk) begin
        cyc<=cyc+1;
        if(cyc==4) rst_n<=1;
        lw_v<=0; cmd_v<=0; wc_v<=0;
        // write phase (RT): one writer command at a time, then wait until every write has completed
        if(rst_n && wphase) begin
            if(tw0<0) tw0=cyc;
            if(w_fault) $fatal(1,"writer fault");
            if(wcmd<wr_op.size()) begin
                if(wc_rdy && !wc_v) begin
                    wc_v<=1; wc_op<=wr_op[wcmd][0]; wc_n<=33'(wr_n[wcmd]); wc_pos<=33'(wr_pos[wcmd]);
                    wc_key<=keyfn(RANK, wr_op[wcmd] ? wr_pos[wcmd] : wr_n[wcmd]);
                    wcmd<=wcmd+1;
                end
            end else if(!wc_v && !w_busy && cyc>tw0+8) begin
                wphase<=0; tw1=cyc;
                $display("KGROW_WRITE cmds=%0d keys=%0d migrations=%0d copied=%0d cycles=%0d",
                         wcmd,w_nkeys,w_nmig,w_ncopy,tw1-tw0);
            end
        end
        // list load, then start
        if(rst_n && !wphase && t0<0) begin
            if(wi<2048) begin
                for(q=0;q<4;q=q+1) begin lw_v[q]<=(wi<nlist[q]); lw_blk[q]<=list[q*2048+wi]; end
                lw_addr<=LMW'(wi); wi<=wi+1;
            end else if(wi==2048) begin wi<=wi+1; end
            else begin cmd_v<=1; t0<=cyc+1; end
        end
        if(t0>=0 && cyc>t0+MAX_CYCLES) $fatal(1,"timeout");
        if(t0>=0 && cyc==t0+3) for(q=0;q<4;q=q+1) if(s_fault[q]) $fatal(1,"fault stack %0d",q);
        for(q=0;q<4;q=q+1) if(s_valid[q]) begin
            if(firsto[q]<0) firsto[q]=cyc-t0;
            lasto[q]=cyc-t0;
            nk=(s_kv[q*16+8]) ? 2 : 1;
            if(s_kv[q*16 +:16] !== ((nk==2) ? 16'hffff : 16'h00ff)) $fatal(1,"kv stack %0d",q);
            $fwrite(fo,"%0d %0d %h %0d %0d\n",q,cyc-t0,s_kv[q*16 +:16],s_blk[q*2*LBW +:LBW],
                    (nk==2) ? int'(s_blk[q*2*LBW+LBW +:LBW]) : -1);
            for(b=0;b<nk;b=b+1) begin
                if(ptr[q]+b>=nblk(q)) $fatal(1,"extra block stack %0d",q);
                want=blk_at(q,ptr[q]+b);
                if(s_blk[q*2*LBW+b*LBW +:LBW] !== LBW'(want))
                    $fatal(1,"block order stack %0d idx %0d got %0d want %0d",q,ptr[q]+b,s_blk[q*2*LBW+b*LBW +:LBW],want);
                for(k=0;k<8;k=k+1)
                    if(s_key[(q*16+8*b+k)*544 +:544] !== expkey(q,want,k))
                        $fatal(1,"key stack %0d block %0d key %0d got %h want %h",q,want,k,
                               s_key[(q*16+8*b+k)*544 +:544],expkey(q,want,k));
            end
            ptr[q]=ptr[q]+nk;
        end
        for(q=0;q<4;q=q+1) done4[q]=(ptr[q]==nblk(q)) && !s_busy[q];
        if(t0>=0 && cyc>t0+2 && &done4 && lastc<0) begin lastc<=cyc; dump<=1; end
        if(dump) dump<=0;
        if(lastc>=0 && cyc==lastc+3) begin : fin
            integer tot,mx;
            tot=0; mx=-1;
            for(q=0;q<4;q=q+1) begin
                if(s_beats[q*48 +:48]!=17*nblk(q)) $fatal(1,"sectors stack %0d got %0d want %0d",q,s_beats[q*48 +:48],17*nblk(q));
                if(s_keys[q*48 +:48]!=8*nblk(q)) $fatal(1,"keys stack %0d",q);
                $display("KGSTACK s=%0d blocks=%0d sectors=%0d first=%0d last=%0d",q,nblk(q),17*nblk(q),firsto[q],lasto[q]);
                tot+=17*nblk(q); if(lasto[q]>mx) mx=lasto[q];
            end
            $fclose(fo);
            $display("KGROW_PASS blocks=%0d,%0d,%0d,%0d sectors=%0d last=%0d clk_ps=%0d wb=%0d ne=%0d rt=%0d",
                     nblk(0),nblk(1),nblk(2),nblk(3),tot,mx,CLK_PS,WB,NE,RT);
            $finish;
        end
    end
endmodule
