`timescale 1ns/1ps
`default_nettype none
module tb_hgi_coll_b2_vmport;
    parameter integer RLY=8, MUT=0, N=128, KLINES=256, PHYSICAL_RING=1, ROUTE_MUT=0;
    function automatic integer next_sid(input integer s);
        if(!PHYSICAL_RING)next_sid=(s+1)%4;else case(s)0:next_sid=1;1:next_sid=3;3:next_sid=2;default:next_sid=0;endcase
    endfunction
    function automatic integer prev_sid(input integer s);
        if(!PHYSICAL_RING)prev_sid=(s+3)%4;else case(s)0:prev_sid=2;2:prev_sid=3;3:prev_sid=1;default:prev_sid=0;endcase
    endfunction
    reg clk=0, rst_n=0; always #1 clk=~clk;
    reg [3:0] iv=0; wire [3:0] ir; reg [159:0] ia=0; reg [2047:0] id=0;
    wire [3:0] tv, fc; wire [159:0] ta; wire [2047:0] td; wire tvm, ff, xf, ridle;
    reg kv=0; wire kr; reg [567:0] kd=0; wire ktv,kfc,kidle,kfault; wire [567:0] ktd;
    ot_hgi_coll_rgx_wtx u_tx (.clk(clk),.rst_n(rst_n),.rg_w_v(iv),.rg_w_addr(ia),.rg_w_vm(1'b1),.rg_w_data(id),
        .rg_w_rdy(ir),.idle(ridle),.t_v(tv),.t_addr(ta),.t_data(td),.t_vm(tvm),.f_cr(br[RLY-1][3:0]),.f_fault(br[RLY-1][5]),.fault(xf));
    ot_hgi_coll_crl_tx u_kt (.clk(clk),.rst_n(rst_n),.in_v(kv),.in_d(kd),.in_rdy(kr),.idle(kidle),
        .t_v(ktv),.t_d(ktd),.f_cr(br[RLY-1][4]),.fault(kfault));
    reg [2781:0] fr[0:RLY-1]; reg [5:0] br[0:RLY-1];
    always @(posedge clk) begin
        fr[0]<={ktv,ktd,tvm,tv,ta,td}; br[0]<={ff,kfc,fc};
        for(integer i=1;i<RLY;i=i+1)begin fr[i]<=fr[i-1];br[i]<=br[i-1];end
    end
    reg [337:0] readq[0:3]; wire [273:0] readr[0:3];
    wire [2223:0] co[0:3],ci[0:3],no[0:3],ni[0:3]; wire [1:0] coc[0:3],cic[0:3],noc[0:3],nic[0:3];
    reg [271:0] verify_rq[0:3]; wire [4111:0] verify_rr[0:3];
    wire [143:0] bs[0:3]; wire [2:0] hs[0:3]; wire [1:0] mb[0:3];
    for(genvar s=0;s<4;s=s+1) begin:g_slice
        wire [273:0] rsp;
        if(s==0)begin:g_sw
            ot_vms_slice_coll_sw #(.PHYSICAL_RING(PHYSICAL_RING&&!ROUTE_MUT),.MUT(MUT)) u(.clk(clk),.rst_n(rst_n),.clk_coll_rx({5{clk}}),.clk_vm_child({13{clk}}),
                .rgx_t_v(fr[RLY-1][2208 +:4]),.rgx_t_addr(fr[RLY-1][2048 +:160]),.rgx_t_data(fr[RLY-1][0 +:2048]),
                .rgx_t_vm(fr[RLY-1][2212]),.rgx_f_cr(fc),.tkw_t_v(fr[RLY-1][2781]),.tkw_t_d(fr[RLY-1][2213 +:568]),
                .tkw_f_cr(kfc),.coll_fault(ff),.coll_xw(),.coll_xwa(2'b0),
                .cq(readq[s]),.cr(rsp),.rq(verify_rq[s]),.rq_cr(),.rr(verify_rr[s]),.wq('0),.wq_cr(),.wq_done(),.dq('0),.dq_done(),
                .vcb('0),.vcb_cr(),.kq_done(),.cw_in(ci[s]),.cw_in_cr(cic[s]),.cw_out(co[s]),.cw_out_cr(coc[s]),
                .ccw_in(ni[s]),.ccw_in_cr(nic[s]),.ccw_out(no[s]),.ccw_out_cr(noc[s]),.bank_status(bs[s]),.hub_status(hs[s]),.mirror_busy(mb[s]));
        end else begin:g_peer
            assign rsp='0;
            ot_vms_slice_no_cq #(.PHYSICAL_RING(PHYSICAL_RING&&!ROUTE_MUT)) u(.child_clk({13{clk}}),.rst_n(rst_n),.sid(2'(s)),
                .rq(verify_rq[s]),.rq_cr(),.rr(verify_rr[s]),.wq('0),.wq_cr(),.wq_done(),.dq('0),.dq_done(),.vcb('0),.vcb_cr(),.kq_done(),
                .cw_in(ci[s]),.cw_in_cr(cic[s]),.cw_out(co[s]),.cw_out_cr(coc[s]),
                .ccw_in(ni[s]),.ccw_in_cr(nic[s]),.ccw_out(no[s]),.ccw_out_cr(noc[s]),.bank_status(bs[s]),.hub_status(hs[s]),.mirror_busy(mb[s]));
        end
        assign readr[s]=rsp[273:0];
        wire [2223:0] cf[0:RLY],nf[0:RLY];wire[1:0] cb[0:RLY],nb[0:RLY];
        assign cf[0]=co[s];assign ci[next_sid(s)]=cf[RLY];assign cb[RLY]=cic[next_sid(s)];assign coc[s]=cb[0];
        assign nf[0]=no[s];assign ni[prev_sid(s)]=nf[RLY];assign nb[RLY]=nic[prev_sid(s)];assign noc[s]=nb[0];
        for(genvar j=0;j<RLY;j=j+1)begin:g_relay
            ot_vms_relay #(.W(2224),.C(2)) rc(.clk(clk),.rst_n(rst_n),.f_in(cf[j]),.f_out(cf[j+1]),.cr_in(cb[j+1]),.cr_out(cb[j]));
            ot_vms_relay #(.W(2224),.C(2)) rn(.clk(clk),.rst_n(rst_n),.f_in(nf[j]),.f_out(nf[j+1]),.cr_in(nb[j+1]),.cr_out(nb[j]));
        end
    end
    reg [255:0] golden[int]; integer keys[$];
    function automatic [255:0] dataword(input integer lane,input integer i,input integer h);
        reg [255:0] d;begin for(integer w=0;w<8;w=w+1)d[w*32+:32]=32'h3f000000 ^ 32'(lane*100000+i*32+h*8+w);dataword=d;end
    endfunction
    function automatic [39:0] addr(input integer lane,input integer i);
        integer s;begin s=((i%5)==4)?(32768+lane*512+i*2):((i%4)*8192+lane*512+i*2);addr=40'(s*8);end
    endfunction
    task automatic record_write(input[39:0]a,input[511:0]d,input[15:0]m);
        integer key;reg[255:0]o;begin for(integer h=0;h<2;h=h+1)begin
            key=int'(a>>3)+h; if(!golden.exists(key))begin golden[key]=0;keys.push_back(key);end
            o=golden[key];for(integer w=0;w<8;w=w+1)if(m[h*8+w])o[w*32+:32]=d[(h*8+w)*32+:32];golden[key]=o;
        end end
    endtask
    integer sent[0:3], ks=0, cycles=0, write_start=0, phase=0, ri=0, copies=0, checking=0, read_sid=0, checked=0, scalar_checked=0, returned=0;
    integer cw_hops[0:3],ccw_hops[0:3],cw_credits[0:3],ccw_credits[0:3];
    reg [255:0] expected; reg [15:0] rtag=0;
    integer seed_i=0,seed_pending[0:3],seed_done=0;
    initial begin for(integer l=0;l<4;l=l+1)sent[l]=0;for(integer s=0;s<4;s=s+1)begin readq[s]=0;verify_rq[s]=0;seed_pending[s]=0;cw_hops[s]=0;ccw_hops[s]=0;cw_credits[s]=0;ccw_credits[s]=0;end
        // Seed every touched sector with nonzero data so TOPK masks must preserve real prior words.
        for(integer l=0;l<5;l=l+1)for(integer i=0;i<(l==4?KLINES:N);i=i+1)begin
            integer key;key=int'(addr(l,i)>>3);
            for(integer h=0;h<2;h=h+1)if(!golden.exists(key+h))begin golden[key+h]=dataword(31,key+h,0);keys.push_back(key+h);end
        end
        repeat(8)@(negedge clk);rst_n=1;phase=0;end
    always @(posedge clk)if(rst_n)begin
        cycles<=cycles+1; if(xf||kfault||ff)$fatal(1,"adapter protocol fault");
        for(integer s=0;s<4;s=s+1)begin
            if(hs[s]!=0)$fatal(1,"native hub fault %0d %0h",s,hs[s]);
            for(integer b=0;b<8;b=b+1)if(bs[s][b*18+17]||bs[s][b*18+16])$fatal(1,"native bank fault slice%0d bank%0d",s,b);
        end
        if(phase==0)for(integer a=0;a<4;a=a+1)if(readr[a][273])begin
            if(!readr[a][256]||seed_pending[a]==0)$fatal(1,"bad seed response");
            seed_pending[a]=seed_pending[a]-1;seed_done=seed_done+1;
        end
        if(phase==1)begin
            for(integer l=0;l<4;l=l+1)if(iv[l]&&ir[l])begin record_write(ia[l*40+:40],id[l*512+:512],16'hffff);sent[l]=sent[l]+1;end
            if(kv&&kr)begin record_write(kd[567:528],kd[511:0],kd[527:512]);ks=ks+1;end
        end
        if(phase>=1)for(integer s=0;s<4;s=s+1)begin
            if(PHYSICAL_RING)begin
                if(co[s][2223]&&!co[s][2222]&&co[s][2216:2215]==2'(s)&&
                   (co[s][2220:2217]&~((4'b1<<next_sid(s))|(4'b1<<next_sid(next_sid(s)))))!=0)$fatal(1,"physical hop bound CW sid%0d",s);
                if(no[s][2223]&&!no[s][2222]&&no[s][2216:2215]==2'(s)&&
                   (no[s][2220:2217]&~(4'b1<<prev_sid(s)))!=0)$fatal(1,"physical hop bound CCW sid%0d",s);
            end
            if(co[s][2223])cw_hops[s]=cw_hops[s]+1;
            if(no[s][2223])ccw_hops[s]=ccw_hops[s]+1;
            cw_credits[s]=cw_credits[s]+int'(coc[s][0])+int'(coc[s][1]);
            ccw_credits[s]=ccw_credits[s]+int'(noc[s][0])+int'(noc[s][1]);
        end
        if(phase==2&&checking&&readr[0][273])begin
            if(readr[0][272:257]!=rtag||readr[0][256]||readr[0][255:0]!==expected)$fatal(1,"scalar readback mismatch key%0d",keys[ri]);
            scalar_checked=scalar_checked+1;checking=0;ri=ri+1;
        end
        if(phase==3&&checking&&verify_rr[read_sid][257*(keys[ri]%8)+256])begin
            if(verify_rr[read_sid][257*(keys[ri]%8)+:256]!==expected)$fatal(1,"readback mismatch key%0d copy%0d",keys[ri],copies);
            checked=checked+1;checking=0;
            if(keys[ri]>=32768&&copies<3)copies=copies+1;else begin ri=ri+1;copies=0;end
        end
        if(cycles>1000000)$fatal(1,"B2 writer did not drain sent%0d/%0d/%0d/%0d tk%0d checked%0d",sent[0],sent[1],sent[2],sent[3],ks,checked);
    end
    always @(negedge clk)if(rst_n)begin
        iv=0;kv=0;for(integer s=0;s<4;s=s+1)begin readq[s]=0;verify_rq[s]=0;end
        if(phase==0)begin
            if(seed_i<keys.size())begin
                integer dest,key;key=keys[seed_i];dest=0; // all seed requests use the one real SW scalar client and route remotely
                if(seed_pending[dest]<4)begin
                    readq[dest]={1'b1,1'b1,11'd0,16'(key),5'd0,golden[key],32'hffffffff,16'(seed_i)};
                    seed_pending[dest]=seed_pending[dest]+1;seed_i=seed_i+1;
                end
            end
            if(seed_done==keys.size())begin write_start=cycles;phase=1;end
        end else if(phase==1)begin
            for(integer l=0;l<4;l=l+1)if(sent[l]<N)begin iv[l]=1;ia[l*40+:40]=addr(l,sent[l]);id[l*512+:512]={dataword(l,sent[l],1),dataword(l,sent[l],0)};end
            if(ks<KLINES)begin kv=1;kd={addr(4,ks),16'(ks%3==0?16'h5555:16'hffff),dataword(4,ks,1),dataword(4,ks,0)};end
            if(sent[0]==N&&sent[1]==N&&sent[2]==N&&sent[3]==N&&ks==KLINES&&ridle&&kidle)begin
                // End-to-end drained means no packet write remains outstanding at the receiver.
                for(integer l=0;l<5;l=l+1)if(g_slice[0].g_sw.u.u_coll.pc[l]!=4)$fatal(1,"premature credit drain lane%0d",l);
                for(integer b=0;b<8;b=b+1)if(g_slice[0].g_sw.u.u_coll.on[b]!=0)$fatal(1,"premature wide write drain bank%0d",b);
                $display("B2_WRITE cycles=%0d rgx=%0d topk=%0d",cycles-write_start,4*N,KLINES);phase=2;
            end
        end else if(phase==2&&!checking)begin
            if(ri==keys.size())begin phase=3;ri=0;end
            else begin
                expected=golden[keys[ri]];rtag=16'(scalar_checked);
                readq[0]={1'b1,1'b0,11'd0,16'(keys[ri]),5'd0,256'd0,32'd0,rtag};checking=1;
            end
        end else if(phase==3&&!checking)begin
            if(ri==keys.size())begin
                for(integer s=0;s<4;s=s+1)$display("B2_RING sid=%0d CW_hops=%0d CCW_hops=%0d CW_credits=%0d CCW_credits=%0d RLY=%0d VC=2 C=2",s,cw_hops[s],ccw_hops[s],cw_credits[s],ccw_credits[s],RLY);
                $display("B2_COLL_VMPORT PASS flits=%0d checked=%0d scalar_checked=%0d",4*N+KLINES,checked,scalar_checked);$finish;
            end
            read_sid=keys[ri]>=32768?copies:(keys[ri]>>13);expected=golden[keys[ri]];rtag=16'(checked);
            verify_rq[read_sid][17*(keys[ri]%8)+:17]={1'b1,16'(keys[ri])};checking=1;
        end
    end
endmodule
`default_nettype wire
