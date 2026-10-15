`timescale 1ns/1ps
`default_nettype none
module tb_hgi_coll_pring_captured_static;
    parameter integer MUT_CARRY=0,MUT_TAG=0,MUT_RING_ORDER=0,MUT_READ_LEAD=0;
    localparam integer NC=800,LAT=8,READ_LEAD=(MUT_READ_LEAD?1:2);
    import "DPI-C" function int unsigned f32add(input int unsigned a,input int unsigned b);
    reg clk=0,rst_n=0;always #0.5 clk=~clk;
    typedef struct packed {
        bit lp_we;bit[2:0] lp_tag;bit[255:0] lp_data;
        bit read_add,read_tx,read_rr;bit[2:0] read_add_tag,read_tx_tag,read_rr_tag;
        bit[1:0] read_add_src;bit read_rhs_acc,read_tx_acc;
        bit add_v;bit[2:0] add_tag;bit[1:0] add_src;bit rhs_acc;
        bit[1:0] inject,fwd;bit[2:0] tx_tag;bit[1:0] dst;bit result,acc;
        bit[1:0] rx;bit[3:0] kind,src;bit[5:0] tag;
        bit rr;bit[2:0] rr_tag;
    } slot_t;
    slot_t prog[0:3][0:NC-1],cmd[0:3];
    bit expect_v[0:3][0:NC-1];bit[2:0] expect_tag[0:3][0:NC-1];
    bit[255:0] expect_data[0:3][0:NC-1];
    wire [279:0] co[0:3],no[0:3];
    wire [3:0] rr_v,fault;
    wire [2:0] rr_tag[0:3];wire [255:0] rr_data[0:3];
    function automatic integer nextq(input integer q);case(q)0:nextq=1;1:nextq=3;3:nextq=2;default:nextq=0;endcase endfunction
    function automatic integer prevq(input integer q);case(q)0:prevq=2;1:prevq=0;3:prevq=1;default:prevq=3;endcase endfunction
    function automatic integer pos(input integer q);case(q)0:pos=0;1:pos=1;3:pos=2;default:pos=3;endcase endfunction
    for(genvar q=0;q<4;q=q+1)begin:g_q
        ot_hgi_coll_pring_captured_static #(.SPLIT_CLOCKS(1),.MUT_CARRY(MUT_CARRY),.MUT_TAG(MUT_TAG)) dut(
            .clk(clk),.rst_n(rst_n),.clk_state({8{clk}}),.clk_add({8{clk}}),.qid(2'(q)),.cw_i(co[prevq(q)]),.ccw_i(no[nextq(q)]),.cw_o(co[q]),.ccw_o(no[q]),
            .lp_we(cmd[q].lp_we),.lp_tag(cmd[q].lp_tag),.lp_data(cmd[q].lp_data),
            .state_read_add(cmd[q].read_add),.state_read_tx(cmd[q].read_tx),.state_read_rr(cmd[q].read_rr),
            .state_add_tag(cmd[q].read_add_tag),.state_add_src(cmd[q].read_add_src),.state_add_rhs_acc(cmd[q].read_rhs_acc),
            .state_tx_tag(cmd[q].read_tx_tag),.state_tx_acc(cmd[q].read_tx_acc),.state_rr_tag(cmd[q].read_rr_tag),
            .add_v(cmd[q].add_v),.add_tag(cmd[q].add_tag),.add_src(cmd[q].add_src),.add_rhs_acc(cmd[q].rhs_acc),
            .tx_inject(cmd[q].inject),.tx_forward(cmd[q].fwd),.tx_tag(cmd[q].tx_tag),.tx_dst(cmd[q].dst),
            .tx_result(cmd[q].result),.tx_acc(cmd[q].acc),.rx_slot(cmd[q].rx),.rx_kind(cmd[q].kind),.rx_src(cmd[q].src),.rx_tag(cmd[q].tag),
            .rr_local(cmd[q].rr),.rr_local_tag(cmd[q].rr_tag),.rr_v(rr_v[q]),.rr_tag(rr_tag[q]),.rr_d(rr_data[q]),.fault(fault[q]));
    end
    function automatic [31:0] partial(input integer q,input integer tag,input integer lane,input integer round);
        case(q)
            0:partial=32'h60ad78ec+32'(tag*3+lane+round);
            1:partial=32'h3f400000+32'(tag*1031+lane*57+round);
            2:partial=32'he0ad78ec+32'(tag*3+lane+round);
            default:partial=32'hbf200000+32'(tag*311+lane*29+round);
        endcase
    endfunction
    function automatic [255:0] golden(input integer tag,input integer round);
        reg [31:0] a,b;reg [255:0] y;
        for(integer l=0;l<8;l=l+1)begin
            a=f32add(partial(0,tag,l,round),partial(1,tag,l,round));
            b=f32add(a,f32add(partial(2,tag,l,round),partial(3,tag,l,round)));
            y[l*32+:32]=b;
        end
        return y;
    endfunction
    task automatic expect_result(input integer q,input integer cyc,input integer tag,input integer round);
        if(expect_v[q][cyc])$fatal(1,"compiler result collision");
        expect_v[q][cyc]=1;expect_tag[q][cyc]=3'(tag);expect_data[q][cyc]=golden(tag,round);
    endtask
    // A small compiler emits the *entire* route: no DUT transit priority or
    // empty-slot opportunism. Every directed link edge is checked for collision.
    task automatic send(input integer source,input integer dest,input integer cyc,input integer tag,
                        input bit result,input bit acc,input integer round);
        integer d,q,t,hops;
        d=result?0:(((pos(dest)-pos(source)+4)%4)==3?1:0);
        if(prog[source][cyc].inject[d] || prog[source][cyc].fwd[d])$fatal(1,"compiler injection collision");
        if(|prog[source][cyc].inject && (prog[source][cyc].tx_tag!=3'(tag) ||
           prog[source][cyc].dst!=2'(dest) || prog[source][cyc].result!=result ||
           prog[source][cyc].acc!=acc))$fatal(1,"compiler shared injection payload collision");
        prog[source][cyc].inject[d]=1;prog[source][cyc].tx_tag=3'(tag);prog[source][cyc].dst=2'(dest);
        prog[source][cyc].result=result;prog[source][cyc].acc=acc;
        if(prog[source][cyc-READ_LEAD].read_tx)$fatal(1,"compiler TX state read collision");
        prog[source][cyc-READ_LEAD].read_tx=1;prog[source][cyc-READ_LEAD].read_tx_tag=3'(tag);prog[source][cyc-READ_LEAD].read_tx_acc=acc;
        q=source;t=cyc;hops=result?3:((d==0)?(pos(dest)-pos(source)+4)%4:(pos(source)-pos(dest)+4)%4);
        if(hops==0)$fatal(1,"compiler zero route");
        for(integer h=1;h<=hops;h=h+1)begin
            q=d?prevq(q):nextq(q);t=t+2;
            if(prog[q][t].rx[d])$fatal(1,"compiler receive collision");
            prog[q][t].rx[d]=1;prog[q][t].kind[d*2+:2]=result?2:1;
            prog[q][t].src[d*2+:2]=2'(source);prog[q][t].tag[d*3+:3]=3'(tag);
            if(h<hops)begin
                if(prog[q][t].inject[d] || prog[q][t].fwd[d])$fatal(1,"compiler forwarding collision");
                prog[q][t].fwd[d]=1;
            end
            if(result)expect_result(q,t,tag,round);
        end
        if(result)begin
            prog[source][cyc].rr=1;prog[source][cyc].rr_tag=3'(tag);
            prog[source][cyc-READ_LEAD].read_rr=1;prog[source][cyc-READ_LEAD].read_rr_tag=3'(tag);expect_result(source,cyc,tag,round);
        end
    endtask
    task automatic add(input integer q,input integer cyc,input integer tag,input integer source,input bit rhsacc);
        if(prog[q][cyc].add_v)$fatal(1,"compiler adder collision");
        if(prog[q][cyc-READ_LEAD].read_add)$fatal(1,"compiler ADD state read collision");
        prog[q][cyc-READ_LEAD].read_add=1;prog[q][cyc-READ_LEAD].read_add_tag=3'(tag);prog[q][cyc-READ_LEAD].read_add_src=2'(source);prog[q][cyc-READ_LEAD].read_rhs_acc=rhsacc;
        prog[q][cyc].add_v=1;prog[q][cyc].add_tag=3'(tag);prog[q][cyc].add_src=2'(source);prog[q][cyc].rhs_acc=rhsacc;
    endtask
    integer scenario=0,checked=0,last_cycle=0;bit saw_fault=0;
    initial begin
        if($value$plusargs("fault=%d",scenario))begin end
        for(integer q=0;q<4;q=q+1)begin
            cmd[q]='0;
            for(integer c=0;c<NC;c=c+1)begin prog[q][c]='0;expect_v[q][c]=0;end
        end
        // Six full eight-tag waves. All four actual parents run the balanced
        // golden tree. Last Q1 result is B+41; tag lifetime is 42; the shared CW resource requires 44-edge waves.
        for(integer r=0;r<6;r=r+1)begin
            for(integer tag=0;tag<8;tag=tag+1)begin
                integer b,dest;
                b=r*44+tag;
                for(integer q=0;q<4;q=q+1)begin
                    prog[q][b].lp_we=1;prog[q][b].lp_tag=3'(tag);
                    for(integer l=0;l<8;l=l+1)prog[q][b].lp_data[l*32+:32]=partial(q,tag,l,r);
                end
                send(0,1,b+3,tag,0,0,r);send(2,3,b+3,tag,0,0,r);
                add(1,b+8,tag,0,0);add(3,b+8,tag,2,0);
                dest=MUT_RING_ORDER?2:3;
                send(1,dest,b+19,tag,0,1,r);
                add(3,b+24,tag,1,1);
                send(3,3,b+35,tag,1,1,r);
                last_cycle=b+44;
            end
        end
        // Faults are compiler reservation violations, detected without stalling.
        case(scenario)
            1:begin prog[2][37].inject[0]=1;prog[2][37].tx_tag=0;end
            2:prog[1][5].tag[2:0]=1;
            3:prog[1][5].rx[0]=0;
            4:begin prog[0][1].lp_we=1;prog[0][1].lp_tag=0;end
            5:begin prog[2][2].add_v=1;prog[2][2].add_tag=0;prog[2][2].add_src=1;end
            6:prog[2][37].tag[2:0]=1;
            7:prog[1][5].rx[1]=1;
            8:begin prog[0][20].lp_we=1;prog[0][20].lp_tag=0;end
            10:prog[1][6].read_add=0;
            11:prog[1][6].read_add_tag=1;
            12:begin prog[0][9].read_tx=1;prog[0][9].read_tx_tag=7;end
            9:send(0,1,3,0,0,0,0);
            default:begin end
        endcase
        repeat(5)@(negedge clk);rst_n=1;
        for(integer c=0;c<=last_cycle;c=c+1)begin
            for(integer q=0;q<4;q=q+1)cmd[q]=prog[q][c];
            @(posedge clk);#0.01;
            if(|fault)saw_fault=1;
            if(scenario==0)begin
                if(|fault)$fatal(1,"unexpected schedule fault cycle%0d mask%h",c,fault);
                for(integer q=0;q<4;q=q+1)begin
                    if(rr_v[q]!==expect_v[q][c])$fatal(1,"result cycle q%0d cyc%0d got%0d expected%0d",q,c,rr_v[q],expect_v[q][c]);
                    if(rr_v[q])begin
                        if(rr_tag[q]!==expect_tag[q][c] || rr_data[q]!==expect_data[q][c])
                            $fatal(1,"golden mismatch q%0d cyc%0d tag%0d got%h expected%h",q,c,rr_tag[q],rr_data[q],expect_data[q][c]);
                        checked=checked+8;
                    end
                end
            end
            @(negedge clk);
        end
        if(scenario!=0)begin
            if(!saw_fault)$fatal(1,"reservation mutant escaped %0d",scenario);
            $display("CAPTURED_RING FAULT PASS scenario=%0d exact timeline=%0d",scenario,last_cycle);
        end else begin
            if(checked!=6*8*4*8)$fatal(1,"coverage missing %0d",checked);
            $display("CAPTURED_RING PASS quadrants=4 tags=8 rounds=6 lanes_checked=%0d cycles=%0d read_lead=2 wave=44 tag_lifetime=42 last_q1_offset=41",checked,last_cycle);
        end
        $finish;
    end
endmodule
`default_nettype wire
