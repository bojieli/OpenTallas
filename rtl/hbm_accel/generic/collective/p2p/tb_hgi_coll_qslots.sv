`timescale 1ns/1ps
`default_nettype none
module tb_hgi_coll_qslots;
    parameter integer G=96, PF=384, MUT_SELECT=0, MUT_PIN_LATENCY=0, BAD_SLOT=0, CALENDAR=0;
    parameter string CALDIR="";
    reg clk=0,rst_n=0; always #0.41665 clk=~clk;
    integer cyc=0, checked=0;
    wire [3:0] fault;
    for(genvar q=0;q<4;q=q+1) begin:gq
        localparam integer NP=(q==0)?3:2, NS=2+NP+4+1, ND=NP+3*4+1, SW=$clog2(NS);
        localparam integer CW=NS+ND+ND*SW;
        reg [CW-1:0] program_words[0:G*(PF/4)+3];
        initial if(CALENDAR!=0) begin
            for(integer c=0;c<G*(PF/4)+4;c=c+1) program_words[c]=0;
            $readmemh($sformatf("%s/npt%0d.mem",CALDIR,NP),program_words,0,G*(PF/4));
        end
        reg [NS-1:0] sv=0,cs=0;
        reg [NS*545-1:0] sd=0;
        reg [ND-1:0] ds=0;
        reg [ND*SW-1:0] sel=0;
        wire [ND-1:0] ov;
        wire [ND*545-1:0] od;
        wire [3:0] fk;
        reg [NS*545-1:0] prev_d=0;
        reg [NS-1:0] prev_slot=0;
        reg [ND-1:0] expected_v=0;
        reg [ND*545-1:0] expected_d=0, next_d=0, now_d=0;
        reg [ND-1:0] next_v=0;
        ot_hgi_coll_qslots #(.NPT(NP),.MUT_SELECT(MUT_SELECT),.MUT_PIN_LATENCY(MUT_PIN_LATENCY)) u(
            .clk_capture(clk),.clk_output(clk),.rst_n(rst_n),.src_v(sv),.src_d(sd),.capture_slot(cs),
            .sink_slot(ds),.sink_select(sel),.dst_v(ov),.dst_d(od),.fault(fault[q]),.fault_kind(fk));
        function automatic [544:0] value(input integer cycle,input integer src);
            reg [544:0] v;
            begin
                // Every 32b payload segment changes with rank/quarter/flit/source.
                // Includes all 33 routing/header bits, not only low data words.
                for(integer b=0;b<17;b=b+1) v[b*32+:32]=32'(cycle*1000003+src*104729+q*65537+b*8191);
                v[544]=1'(cycle+src+q);
                value=v;
            end
        endfunction
        always @(negedge clk) if(rst_n) begin
            sv='1; cs='1;
            for(integer s=0;s<NS;s=s+1) sd[s*545+:545]=value(cyc,s);
            ds=(cyc>0)?'1:'0;
            for(integer d=0;d<ND;d=d+1) sel[d*SW+:SW]=SW'((d+cyc)%NS);
            if(CALENDAR!=0) begin
                cs=program_words[cyc][0+:NS]; sv=cs;
                ds=program_words[cyc][NS+:ND];
                sel=program_words[cyc][NS+ND+:ND*SW];
            end
            if(BAD_SLOT==1 && cyc==8) cs[0]=0;
            if(BAD_SLOT==2 && cyc==8) sel[0+:SW]=SW'(NS);
            if(BAD_SLOT==3 && cyc==8) begin cs='0; sv='0; end
        end
        always @(posedge clk) if(rst_n) begin
            expected_v=next_v; expected_d=next_d;
            for(integer d=0;d<ND;d=d+1) now_d[d*545+:545]=prev_d[int'(sel[d*SW+:SW])*545+:545];
            next_v=ds; next_d=now_d;
            prev_d=sd;
            prev_slot=cs;
            #0.01;
            if(ov!==expected_v) $fatal(1,"fixed output cycle mismatch q%0d",q);
            if(BAD_SLOT==0) begin
                if(fault[q]) $fatal(1,"unexpected schedule fault q%0d kind%h",q,fk);
                for(integer d=0;d<ND;d=d+1) if(ov[d]) begin
                    if(od[d*545+:545]!==expected_d[d*545+:545]) $fatal(1,"bit-exact transport mismatch q%0d d%0d cyc%0d",q,d,cyc);
                    checked=checked+1;
                end
            end
        end
    end
    initial begin
        repeat(4) @(negedge clk); rst_n=1;
        repeat(G*(PF/4)+3) begin @(posedge clk); #0.02; cyc=cyc+1; end
        if(BAD_SLOT!=0 && fault!=4'hf) $fatal(1,"schedule mutant escaped fault mask=%h",fault);
        $display("QSLOTS PASS G=%0d PF=%0d quadrants=4 checked=%0d cycles=%0d BAD_SLOT=%0d CALENDAR=%0d",G,PF,checked,cyc,BAD_SLOT,CALENDAR); $finish;
    end
endmodule
`default_nettype wire
