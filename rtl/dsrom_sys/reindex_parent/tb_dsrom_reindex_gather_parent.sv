`timescale 1ns/1ps
// Candidate-block gather bench: four HBM3E stacks of one rank (die), each stack its own
// ot_hdc_v41x_idx_kgather straight into its timing-faithful ot_hdc_v41x_idx_hbm
// (MEM_MODE 1: the sector-address pattern), placement as tb_w11_idx_quarter_stack
// (stack q: base block BASE + q BSTEP, ring head (q OSTEP) mod 1,024 keys).
// +PFX=<path>: stack q's candidate list in <path>.s<q> (first line the count, then one
// local block index per line, hex, ascending).  The lists are written into the units,
// then one command starts all four stacks at once (cycle 0).  Every key of every beat is
// checked against the pattern of the sectors that hold it, every block index against the
// list, in order; the HBM sectors read must be exactly 17 a block.
// Prints KGSTACK lines (per stack: blocks, sectors, first / last output cycle, HBM
// stats) and KGATHER_PASS with the rank's last output cycle.
module tb_hdc_v41x_idx_kgather #(
    parameter integer OPT_KC6 = 1,
    parameter integer OPT_KC7 = 0,
    parameter integer OPT_KC8 = 0,
    parameter integer MAX_CYCLES=200000,
    parameter integer WB=128, DF=8, QD=64, RQD=32, RW=16, MAXSKIP=16, CLK_PS=833,
    parameter integer BASE=0, BSTEP=1000, OSTEP=136,
    parameter longint REFI_PS=3900000
) (input wire clk);
    localparam integer NPC=32,AW=28,HW=20,TAGW=16,LENW=4,BEATW=4,DW=256,LBW=14,LMW=11;
    reg rst_n=0, cmd_v=0;
    reg [3:0] lw_v=0;
    reg [LMW-1:0] lw_addr=0;
    reg [LBW-1:0] lw_blk [0:3];
    wire [3:0] s_busy,s_valid,s_fault;
    wire [4*16-1:0] s_kv;
    wire [4*16*544-1:0] s_key;
    wire [4*2*LBW-1:0] s_blk;
    wire [4*48-1:0] s_keys,s_beats;
    wire [4*NPC-1:0] h_req_v,h_req_rdy,h_rsp_v,h_rsp_rdy;
    wire [4*NPC*AW-1:0] h_req_addr;
    wire [4*NPC*LENW-1:0] h_req_len;
    wire [4*NPC*TAGW-1:0] h_req_tag,h_rsp_tag;
    wire [4*NPC*BEATW-1:0] h_rsp_beat;
    wire [4*NPC*DW-1:0] h_rsp_data;
    integer nlist [0:3];
    reg [LBW-1:0] list [0:4*2048-1];
    reg dump=0;
    function automatic integer ooff(input integer q);  ooff=(q*OSTEP)%1024; endfunction
    function automatic integer obase(input integer q); obase=BASE+q*BSTEP; endfunction
    genvar s;
    generate for(s=0;s<4;s=s+1) begin:g_stack
        always @(posedge clk) if(dump) begin : g_dump
            longint rd,act,hit,conf,refs,rmin,rmax;
            rd=0;act=0;hit=0;conf=0;refs=0;rmin=64'h7fffffffffffffff;rmax=0;
            for(integer p=0;p<NPC;p=p+1) begin
                rd+=hm.st_rd[p];act+=hm.st_act[p];hit+=hm.st_hit[p];
                conf+=hm.st_conf[p];refs+=hm.st_ref[p];
                if(hm.st_rd[p]<rmin) rmin=hm.st_rd[p];
                if(hm.st_rd[p]>rmax) rmax=hm.st_rd[p];
            end
            $display("KGHBM s=%0d rd=%0d act=%0d hit=%0d conf=%0d ref=%0d bp=%0d lat_sum_ps=%0d lat_max_ps=%0d pc_rd_min=%0d pc_rd_max=%0d",
                     s,rd,act,hit,conf,refs,hm.st_bp_cycles,hm.st_rd_lat_sum,hm.st_rd_lat_max,rmin,rmax);
        end
        ot_hdc_v41x_idx_hbm #(.NPC(NPC),.AW(AW),.DW(DW),.MEM_WORDS(1),
            .TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),.QD(QD),.RQD(RQD),.RW(RW),.MAXSKIP(MAXSKIP),.CLK_PS(CLK_PS),
            .REFPB(3),.REFI_PS(REFI_PS),.MEM_MODE(1)) hm (
            .clk(clk),.rst_n(rst_n),.req_v(h_req_v[s*NPC +:NPC]),
            .req_rdy(h_req_rdy[s*NPC +:NPC]),
            .req_addr(h_req_addr[s*NPC*AW +:NPC*AW]),
            .req_len(h_req_len[s*NPC*LENW +:NPC*LENW]),
            .req_tag(h_req_tag[s*NPC*TAGW +:NPC*TAGW]),
            .req_we({NPC{1'b0}}),.req_wdata({NPC*DW{1'b0}}),
            .req_wstrb({NPC*32{1'b0}}),.wr_done(),
            .rsp_v(h_rsp_v[s*NPC +:NPC]),.rsp_rdy(h_rsp_rdy[s*NPC +:NPC]),
            .rsp_tag(h_rsp_tag[s*NPC*TAGW +:NPC*TAGW]),
            .rsp_beat(h_rsp_beat[s*NPC*BEATW +:NPC*BEATW]),
            .rsp_data(h_rsp_data[s*NPC*DW +:NPC*DW]));
        ot_dsrom_reindex_gather_parent #( .NPC(NPC),.WB(WB),.AW(AW),.HW(HW),.TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),
            .DW(DW),.LBW(LBW),.LMW(LMW),.DF(DF)) kg (
            .clk(clk),.rst_n(rst_n),.lw_v(lw_v[s]),.lw_slot(3'd0),.lw_addr(lw_addr),.lw_blk(lw_blk[s]),
            .cmd_v(cmd_v),.cmd_slot(3'd0),.cmd_base(HW'(BASE+s*BSTEP)),.cmd_skip(10'((s*OSTEP)%1024)),
            .cmd_n(12'(nlist[s])),.busy(s_busy[s]),.fault(s_fault[s]),
            .req_v(h_req_v[s*NPC +:NPC]),.req_rdy(h_req_rdy[s*NPC +:NPC]),
            .req_addr(h_req_addr[s*NPC*AW +:NPC*AW]),
            .req_len(h_req_len[s*NPC*LENW +:NPC*LENW]),
            .req_tag(h_req_tag[s*NPC*TAGW +:NPC*TAGW]),
            .rsp_v(h_rsp_v[s*NPC +:NPC]),.rsp_rdy(h_rsp_rdy[s*NPC +:NPC]),
            .rsp_tag(h_rsp_tag[s*NPC*TAGW +:NPC*TAGW]),
            .rsp_beat(h_rsp_beat[s*NPC*BEATW +:NPC*BEATW]),
            .rsp_data(h_rsp_data[s*NPC*DW +:NPC*DW]),
            .o_valid(s_valid[s]),.o_ready(1'b1),
            .o_kv(s_kv[s*16 +:16]),.o_key(s_key[s*16*544 +:16*544]),.o_blk(s_blk[s*2*LBW +:2*LBW]),
            .cnt_keys_streamed(s_keys[s*48 +:48]),
            .cnt_hbm_beats(s_beats[s*48 +:48]));
        always @(posedge clk) if(rst_n && s_fault[s]) begin
            $display("PARENT_FAULT stack=%0d core=%b list=%b command=%b bad_command=%b req=%h drain=%b rd_seq=%0d list_v=%b count=%0d reserved=%0d",s,kg.cfault,kg.mfault,kg.command_fault,kg.bad_command,kg.qfault,kg.dfault,kg.u_c.rd_seq,kg.u_c.list_v,kg.list_count,kg.u_d.u_queue.reserved);
            $fatal(1,"production parent fault");
        end
    end endgenerate
    function automatic [255:0] pat(input [AW-1:0] sec);
        integer w;
        begin for(w=0;w<8;w=w+1)
            pat[32*w +:32]=(sec*32'd8+w)*32'h9E3779B1 ^ 32'h5bd1e995;
        end
    endfunction
    // stack a, local block lb, key k of the block
    function automatic [543:0] expkey(input integer a,input integer lb,input integer k);
        integer lk,sb,pos;
        reg [AW-1:0] sc,cs;
        reg [255:0] sw;
        begin
            lk=ooff(a)+8*lb+k; sb=lk/1024; pos=lk%1024;
            sc=AW'((obase(a)+17*sb)*128+pos/8);
            cs=AW'((obase(a)+17*sb+1)*128+2*pos);
            sw=pat(sc);
            expkey={sw[32*(pos%8) +:32],pat(cs+1),pat(cs)};
        end
    endfunction
    // -- load lists ------------------------------------------------------------------------
    string pfx;
    initial begin : load
        integer fd,q,i,v,r;
        if(!$value$plusargs("PFX=%s",pfx)) $fatal(1,"+PFX required");
        for(q=0;q<4;q=q+1) begin
            fd=$fopen($sformatf("%s.s%0d",pfx,q),"r");
            if(fd==0) $fatal(1,"cannot open list %0d",q);
            r=$fscanf(fd,"%d",nlist[q]);
            if(nlist[q]>2048) $fatal(1,"list too long");
            for(i=0;i<nlist[q];i=i+1) begin r=$fscanf(fd,"%h",v); list[q*2048+i]=LBW'(v); end
            $fclose(fd);
        end
    end
    integer cyc=0, t0=-1, wi=0, lastc=-1;
    integer ptr [0:3];
    integer firsto [0:3];
    integer lasto [0:3];
    integer q,b,k,nk;
    reg [3:0] done4;
    initial for(q=0;q<4;q=q+1) begin ptr[q]=0; firsto[q]=-1; lasto[q]=-1; end
    always @(posedge clk) begin
        cyc<=cyc+1;
        if(cyc==4) rst_n<=1;
        // write the lists (one entry per stack per cycle), then start
        lw_v<=0; cmd_v<=0;
        if(rst_n && t0<0) begin
            if(wi<2048) begin
                for(q=0;q<4;q=q+1) begin lw_v[q]<=(wi<nlist[q]); lw_blk[q]<=list[q*2048+wi]; end
                lw_addr<=LMW'(wi); wi<=wi+1;
            end else if(wi==2048) begin wi<=wi+1; end
            else begin cmd_v<=1; t0<=cyc+1; end
        end
        if(t0>=0 && cyc>t0+MAX_CYCLES) $fatal(1,"timeout");
        for(q=0;q<4;q=q+1) if(s_valid[q]) begin
            if(s_fault[q]) $fatal(1,"fault stack %0d",q);
            if(firsto[q]<0) firsto[q]=cyc-t0;
            lasto[q]=cyc-t0;
            nk=(s_kv[q*16+8]) ? 2 : 1;
            if(s_kv[q*16 +:16] !== ((nk==2) ? 16'hffff : 16'h00ff)) $fatal(1,"kv stack %0d",q);
            for(b=0;b<nk;b=b+1) begin
                if(ptr[q]+b>=nlist[q]) $fatal(1,"extra block stack %0d",q);
                if(s_blk[q*2*LBW+b*LBW +:LBW] !== list[q*2048+ptr[q]+b])
                    $fatal(1,"block order stack %0d idx %0d got %0d want %0d",q,ptr[q]+b,s_blk[q*2*LBW+b*LBW +:LBW],list[q*2048+ptr[q]+b]);
                for(k=0;k<8;k=k+1)
                    if(s_key[(q*16+8*b+k)*544 +:544] !== expkey(q,int'(list[q*2048+ptr[q]+b]),k))
                        $fatal(1,"key stack %0d block %0d key %0d",q,list[q*2048+ptr[q]+b],k);
            end
            ptr[q]=ptr[q]+nk;
        end
        for(q=0;q<4;q=q+1) done4[q]=(ptr[q]==nlist[q]) && !s_busy[q];
        if(t0>=0 && cyc>t0+2 && &done4 && lastc<0) begin lastc<=cyc; dump<=1; end
        if(dump) dump<=0;
        if(lastc>=0 && cyc==lastc+3) begin : fin
            integer tot,mx;
            tot=0; mx=-1;
            for(q=0;q<4;q=q+1) begin
                if(s_beats[q*48 +:48]!=17*nlist[q]) $fatal(1,"sectors stack %0d got %0d want %0d",q,s_beats[q*48 +:48],17*nlist[q]);
                if(s_keys[q*48 +:48]!=8*nlist[q]) $fatal(1,"keys stack %0d",q);
                $display("KGSTACK s=%0d blocks=%0d sectors=%0d first=%0d last=%0d",q,nlist[q],17*nlist[q],firsto[q],lasto[q]);
                tot+=17*nlist[q]; if(lasto[q]>mx) mx=lasto[q];
            end
            $display("KGATHER_PASS blocks=%0d,%0d,%0d,%0d sectors=%0d last=%0d clk_ps=%0d wb=%0d",
                     nlist[0],nlist[1],nlist[2],nlist[3],tot,mx,CLK_PS,WB);
            $finish;
        end
    end
endmodule
