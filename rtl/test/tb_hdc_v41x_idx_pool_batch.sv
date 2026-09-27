`timescale 1ns/1ps
// One kmerge-format four-quarter beat through the pooled indexer batch bridge.
module tb_hdc_v41x_idx_pool_batch (input wire clk);
    localparam integer G=4, M=2, IH=32, AW=20, L=8*G, XW=264;
    reg [543:0] km [0:63];
    reg [XW-1:0] xm [0:(IH/M)*4*M-1];
    reg [47:0] wm [0:IH-1];
    reg [1:0] mm [0:63];
    reg [16:0] em [0:63];
    integer nk=0;
    initial begin
        if (!$value$plusargs("NKEY=%d",nk)) nk=0;
        $readmemh("bk.mem",km);
        $readmemh("bx.mem",xm);
        $readmemh("bw.mem",wm);
        $readmemh("bm.mem",mm);
        $readmemh("be.mem",em);
    end
    reg rst_n=0, cmd_v=0, b_valid=0;
    reg [29:0] cmd_nkeys=0;
    wire b_ready, o_valid, o_write, o_fault, busy, protocol_fault;
    wire [29:0] o_index;
    wire [15:0] o_score;
    reg [63:0] b_kv=0,b_ref=0,b_keep=0;
    reg [64*544-1:0] b_key=0;
    reg w_v=0;
    reg [7:0] w_head=0;
    reg [15:0] w_w=0;
    reg [31:0] w_qsc=0;
    wire [7:0] rq_v,rq_src,rq_split;
    wire [8*AW-1:0] rq_a;
    wire [8*14-1:0] rq_q;
    wire [8*4-1:0] rq_plg,rq_tag;
    wire [8*16-1:0] rq_rg;
    wire [L*M*XW-1:0] rd_x;
    ot_hdc_v41x_idx_pool_batch dut (
        .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_nkeys(cmd_nkeys),
        .b_valid(b_valid),.b_ready(b_ready),.b_kv(b_kv),.b_ref(b_ref),.b_keep(b_keep),.b_key(b_key),
        .w_v(w_v),.w_head(w_head),.w_w(w_w),.w_qsc(w_qsc),
        .rq_v(rq_v),.rq_a(rq_a),.rq_q(rq_q),.rq_plg(rq_plg),.rq_tag(rq_tag),.rq_src(rq_src),
        .rq_split(rq_split),.rq_rg(rq_rg),.rd_x(rd_x),
        .o_valid(o_valid),.o_write(o_write),.o_index(o_index),.o_score(o_score),.o_fault(o_fault),.busy(busy),
        .protocol_fault(protocol_fault));
    reg [L*M*XW-1:0] xp [0:1];
    assign rd_x=xp[1];
    integer j,p,c,row,blk,cyc=0;
    always @(posedge clk) begin
        for(j=0;j<L;j=j+1) begin
            c=j%8;
            row=rq_a[c*AW +: AW]*2*G+2*(j/8)+((j%8)>=4);
            blk=j%4;
            for(p=0;p<M;p=p+1)
                xp[0][(j*M+p)*XW +: XW] <= rq_v[c] ? xm[((row%(IH/M))*4+blk)*M+p] : 264'd0;
        end
        xp[1]<=xp[0];
    end
    integer st=0,h=0,checked=0,errors=0,expected_faults=0,got_faults=0,seen[0:63];
    integer q,slot,base,qlen,i;
    initial for(i=0;i<64;i=i+1) seen[i]=0;
    always @(posedge clk) begin
        cyc<=cyc+1;
        if(cyc==4) rst_n<=1;
        if(o_valid && o_write) begin
            if(o_index>=nk || seen[o_index]!=0 ||
                (em[o_index][16] ? !o_fault : (o_fault || o_score!=em[o_index][15:0]))) begin
                errors=errors+1;
                if(errors<10) $display("BATCH_MISMATCH idx=%0d got=%h fault=%0d exp=%h",o_index,o_score,o_fault,em[o_index]);
            end
            seen[o_index]=seen[o_index]+1;
            checked=checked+1;
            if(o_fault) got_faults=got_faults+1;
        end
        cmd_v<=0; b_valid<=0; w_v<=0;
        if(rst_n) case(st)
            0: begin
                cmd_nkeys<=nk;cmd_v<=1;
                base=8*(nk/32);
                for(q=0;q<4;q=q+1) begin
                    qlen=(q==3)?nk-3*base:base;
                    for(i=0;i<16;i=i+1) begin
                        slot=q*16+i;
                        b_key[slot*544 +: 544]<=km[slot];
                        b_kv[slot]<=i<qlen;
                        b_keep[slot]<=mm[slot][0];
                        b_ref[slot]<=mm[slot][1];
                    end
                end
                st=1;
            end
            1: begin
                w_v<=1;w_head<=h[7:0];{w_qsc,w_w}<=wm[h];
                if(h==IH-1) begin h=0;st=2;end else h=h+1;
            end
            2: if(b_ready) begin b_valid<=1;st=3;end
            3: if(checked==nk) begin
                if(protocol_fault) errors=errors+1;
                for(i=0;i<nk;i=i+1) if(seen[i]!=1) errors=errors+1;
                $display("V41XBATCH keys=%0d checked=%0d errors=%0d faults=%0d cycles=%0d protocol=%0d",
                         nk,checked,errors,got_faults,cyc,protocol_fault);
                $finish;
            end
        endcase
        if(cyc>100000) begin $display("V41XBATCH TIMEOUT checked=%0d",checked);$finish;end
    end
endmodule
