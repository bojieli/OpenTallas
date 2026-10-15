`timescale 1ns/1ps
`default_nettype none
module tb_hgi_coll_pring;
    parameter integer RLY=8, MUT_CARRY=0, MUT_ORDER=0, ROUNDS=4;
    import "DPI-C" function int unsigned f32add(input int unsigned a,input int unsigned b);
    reg clk=0,rst_n=0;always #0.4167 clk=~clk;
    reg [3:0] rv=0,ep=0,ed=0;reg [2:0] rt[0:3];reg rm[0:3];reg [255:0] rd[0:3];
    wire [3:0] ready,outv,fault;wire [2:0] ot[0:3];wire [255:0] od[0:3];
    wire [279:0] co[0:3],ci[0:3],no[0:3],ni[0:3];wire [3:0] hp[0:3],hd[0:3],hf[0:3];
    function automatic integer nextq(input integer q);case(q)0:nextq=1;1:nextq=3;3:nextq=2;default:nextq=0;endcase endfunction
    function automatic integer prevq(input integer q);case(q)0:prevq=2;1:prevq=0;3:prevq=1;default:prevq=3;endcase endfunction
    for(genvar q=0;q<4;q=q+1)begin:g_q
        ot_hgi_coll_pring #(.SPLIT_CLOCKS(1),.MUT_CARRY(MUT_CARRY),.MUT_ORDER(MUT_ORDER)) u(.clk(clk),.rst_n(rst_n),
            .clk_state({8{clk}}),.clk_add({8{clk}}),.qid(2'(q)),.cw_i(ci[q]),.cw_o(co[q]),.ccw_i(ni[q]),.ccw_o(no[q]),
            .ev_pop(ep[q]),.ev_done(ed[q]),.ev_fault(1'b0),.h_pop(hp[q]),.h_done(hd[q]),.h_fault(hf[q]),
            .rc_v(rv[q]),.rc_rdy(ready[q]),.rc_tag(rt[q]),.rc_mode(rm[q]),.rc_d(rd[q]),.rr_v(outv[q]),.rr_tag(ot[q]),.rr_d(od[q]),.fault(fault[q]));
        reg[279:0] cf[0:RLY-1],nf[0:RLY-1];
        always @(posedge clk)begin cf[0]<=co[q];nf[0]<=no[q];for(integer j=1;j<RLY;j=j+1)begin cf[j]<=cf[j-1];nf[j]<=nf[j-1];end end
        assign ci[nextq(q)]=cf[RLY-1];assign ni[prevq(q)]=nf[RLY-1];
    end
    function automatic [31:0] partial(input integer q,input integer tag,input integer lane,input integer round);
        case(q)
            0: partial=32'h60ad78ec+32'(tag*3+lane+round);
            1: partial=32'h3f400000+32'(tag*1031+lane*57+round);
            2: partial=32'he0ad78ec+32'(tag*3+lane+round);
            default: partial=32'hbf200000+32'(tag*311+lane*29+round);
        endcase
    endfunction
    function automatic [255:0] expected(input integer tag,input integer round);
        reg[255:0] d;reg[31:0]a,b;begin for(integer l=0;l<8;l=l+1)begin
            a=f32add(partial(0,tag,l,round),partial(1,tag,l,round));
            if(round%2)b=f32add(a,f32add(partial(2,tag,l,round),partial(3,tag,l,round)));
            else b=f32add(f32add(a,partial(2,tag,l,round)),partial(3,tag,l,round));
            d[l*32+:32]=b;
        end expected=d;end
    endfunction
    integer round=0,issued[0:3],got[0:3],cycles=0,checked=0,pops[0:3],dones[0:3],pop_sent[0:3],done_sent[0:3];reg[7:0]seen[0:3];
    initial begin for(integer q=0;q<4;q=q+1)begin issued[q]=0;got[q]=0;seen[q]=0;pops[q]=0;dones[q]=0;pop_sent[q]=0;done_sent[q]=0;rt[q]=0;rm[q]=0;rd[q]=0;end
        repeat(8)@(negedge clk);rst_n=1;end
    always @(posedge clk)if(rst_n)begin
        cycles<=cycles+1;if(|fault)$fatal(1,"ring protocol fault");
        for(integer q=0;q<4;q=q+1)begin
            if(rv[q]&&ready[q])issued[q]=issued[q]+1;
            if(outv[q])begin
                if(seen[q][ot[q]])$fatal(1,"duplicate result q%0d tag%0d",q,ot[q]);
                if(od[q]!==expected(int'(ot[q]),round))$fatal(1,"carry arithmetic mismatch q%0d tag%0d round%0d",q,ot[q],round);
                seen[q][ot[q]]=1;got[q]=got[q]+1;checked=checked+8;
            end
            if(ep[q])pop_sent[q]=pop_sent[q]+1;if(ed[q])done_sent[q]=done_sent[q]+1;
            if(hp[0][q])pops[q]=pops[q]+1;if(hd[0][q])dones[q]=dones[q]+1;
        end
        if(cycles>100000)$fatal(1,"ring timeout round%0d got%0d/%0d/%0d/%0d",round,got[0],got[1],got[2],got[3]);
    end
    always @(negedge clk)if(rst_n)begin
        rv=0;ep=0;ed=0;
        for(integer q=0;q<4;q=q+1)if(issued[q]<8)begin
            rt[q]=3'(issued[q]);rm[q]=1'(round%2);
            for(integer l=0;l<8;l=l+1)rd[q][l*32+:32]=partial(q,issued[q],l,round);
            if(ready[q])rv[q]=1;
        end
        if(cycles%32==0&&cycles<=320)begin ep=4'hf;ed=4'hf;end
        if(got[0]==8&&got[1]==8&&got[2]==8&&got[3]==8)begin
            round=round+1;
            if(round==ROUNDS)begin
                // Give CTRL traffic its full relay time before comparing exactly-once counts.
                rv=0;repeat(100)@(negedge clk);
                for(integer q=0;q<4;q=q+1)if(pops[q]!=pop_sent[q]||dones[q]!=done_sent[q]||pops[q]==0)$fatal(1,"CTRL counts q%0d pop%0d done%0d",q,pops[q],dones[q]);
                $display("PRING_NATIVE PASS checked=%0d cycles=%0d rounds=%0d",checked,cycles,round);$finish;
            end
            for(integer q=0;q<4;q=q+1)begin issued[q]=0;got[q]=0;seen[q]=0;end
        end
    end
endmodule
`default_nettype wire
