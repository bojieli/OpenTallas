`timescale 1ns/1ps
module tb_hgi_att_row_sources;
    parameter integer MUT_RING_ZERO=0, MUT_DROP_C=0, MUT_C_REVERSE=0;
    reg clk=0; always #416.6665 clk=~clk;
    reg rst_n=0,cmd_v=0,ring=0;
    reg [20:0] pos1=0,b_n=0,b_m=0,c_n=0;
    wire cmd_r,c_id_r,row_v,row_source,row_last,busy,done,fault;
    reg c_id_v=0,row_r=0; reg [31:0] c_id=0;
    wire [19:0] row_index; wire [20:0] row_ordinal;
    reg lv=0,ls=0,ll=0; reg [19:0] li=0; reg [20:0] lo=0;
    wire lr,lrv,lrs,lrl; wire [19:0] lri; wire [20:0] lro;
    integer tests=0, rows=0, cycle=0;
    ot_hgi_att_row_sources_p #(.MUT_RING_ZERO(MUT_RING_ZERO),.MUT_DROP_C(MUT_DROP_C),.MUT_C_REVERSE(MUT_C_REVERSE)) dut(
        .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_r(cmd_r),.ring(ring),.pos1(pos1),.b_n(b_n),.b_m(b_m),.c_n(c_n),
        .c_id_v(c_id_v),.c_id_r(c_id_r),.c_id(c_id),.row_v(row_v),.row_r(row_r),.row_source(row_source),.row_last(row_last),
        .row_index(row_index),.row_ordinal(row_ordinal),.busy(busy),.done(done),.fault(fault));
    ot_hgi_att_row_sources legacy(.clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_r(),.ring(ring),.pos1(pos1),.b_n(b_n),.b_m(b_m),.c_n(c_n),
        .c_id_v(c_id_v),.c_id_r(),.c_id(c_id),.legacy_v(lv),.legacy_r(lr),.legacy_source(ls),.legacy_last(ll),
        .legacy_row(li),.legacy_ordinal(lo),.row_v(lrv),.row_r(row_r),.row_source(lrs),.row_last(lrl),
        .row_index(lri),.row_ordinal(lro),.busy(),.done(),.fault());
    function automatic integer selected(input integer j);
        selected=(j*977+53)%1048576;
    endfunction
    task automatic run_case(input integer rb,p,nb,mb,nc);
        integer got,sent,t,exp_index,first;
        reg seen_done; reg [43:0] held; reg had_hold;
        begin
            @(negedge clk); if(!cmd_r) $fatal(1,"not ready before case");
            ring=rb;pos1=p;b_n=nb;b_m=mb;c_n=nc;cmd_v=1;row_r=0;
            @(negedge clk);cmd_v=0;got=0;sent=0;t=0;seen_done=done;had_hold=0;
            first=rb?((p-nb)&(mb-1)):0;
            while(!seen_done) begin
                row_r=(t%7!=0 && t%7!=1 && t%7!=2);
                c_id_v=(sent<nc && t%5!=0);c_id=selected(sent);
                @(posedge clk);
                if(had_hold && {row_v,row_source,row_last,row_index,row_ordinal}!==held) $fatal(1,"stall changed row");
                had_hold=row_v && !row_r; held={row_v,row_source,row_last,row_index,row_ordinal};
                if(row_v && row_r) begin
                    exp_index=(got<nb)?(rb?((first+got)%mb):got):selected(got-nb);
                    if(row_index!==exp_index[19:0] || row_ordinal!==got[20:0] || row_source!==(got>=nb) || row_last!== (got==nb+nc-1))
                        $fatal(1,"ordered row mismatch case%0d got%0d index%0d expected%0d source%0d ordinal%0d",tests,got,row_index,exp_index,row_source,row_ordinal);
                    got=got+1;rows=rows+1;
                end
                if(c_id_v && c_id_r) sent=sent+1;
                @(negedge clk);seen_done=done;
                if(fault) $fatal(1,"valid command fault");
                t=t+1;cycle=cycle+1;
                if(t>(nb+nc)*10+64) $fatal(1,"bounded deterministic handshake failed case%0d got%0d sent%0d",tests,got,sent);
            end
            if(got!=nb+nc || sent!=nc) $fatal(1,"early completion got%0d expected%0d sent%0d",got,nb+nc,sent);
            c_id_v=0;tests=tests+1;
        end
    endtask
    task automatic invalid_ring(input integer nb,mb,p);
        begin
            @(negedge clk);cmd_v=1;ring=1;b_n=nb;b_m=mb;pos1=p;c_n=0;
            @(negedge clk);cmd_v=0;
            @(negedge clk);
            if(!fault || !done || row_v) $fatal(1,"invalid ring not rejected");
            tests=tests+1;
        end
    endtask
    integer phase,j;
    initial begin
        repeat(3) @(negedge clk);rst_n=1;
        // Default-off DS contract: actual combinational pins are identical on every cycle, including stalls.
        for(j=0;j<300;j=j+1) begin
            @(negedge clk);lv=j%3!=0;ls=j%2;ll=j%17==0;li=j*977;lo=j;row_r=j%5!=0;
            #1;if({lrv,lrs,lrl,lri,lro,lr}!=={lv,ls,ll,li,lo,row_r}) $fatal(1,"legacy lockstep changed");
        end
        lv=0;
        run_case(0,8192,8192,0,0);
        run_case(0,1048576,1048576,0,0); // effective DYN count includes the 1M endpoint
        run_case(1,1048576,128,128,2048); // POS1 must not truncate at ring wrap // full Qwen 8K single B source
        for(phase=0;phase<128;phase=phase+1) run_case(1,4096+phase,128,128,17);
        run_case(1,8191,128,128,2048); // full DS selected rows + window
        run_case(1,128,128,128,0);
        run_case(1,1,1,128,2);
        run_case(0,0,0,0,2048); // second list only
        run_case(0,0,0,0,0);
        invalid_ring(1,0,1);invalid_ring(4,3,4);invalid_ring(129,128,256);invalid_ring(3,128,2);
        // Out-of-range selected id must fail closed, without truncating.
        @(negedge clk);ring=0;b_n=0;c_n=1;cmd_v=1;
        @(negedge clk);cmd_v=0;c_id_v=1;c_id=32'h00100000;row_r=1;
        @(negedge clk);
        @(negedge clk);if(!fault || !done || row_v) $fatal(1,"invalid C id truncated");
        $display("PASS CF-ATT cases=%0d rows=%0d cycles=%0d legacy_lockstep=300",tests+1,rows,cycle);$finish;
    end
endmodule
