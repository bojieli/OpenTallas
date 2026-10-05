`timescale 1ps/1ps
// PREPARATION ONLY: compile requires parent GO. Actual source observer is
// generated from pin4535; this bench neither repairs nor extends its service.
// Three finite stimulus clients: RMW reads, marker WRs, next-matrix prefetch.
// No actual XOR/AND/XOR engine, encoded KV, WRvisible/CDC/provider completion.
module tb_actual_controller;
    localparam integer CLK_PS=1000, NPC=32, AW=34, TAGW=16, LENW=6, BEATW=5;
    `include "stimulus_r3.svh"
    reg clk=0,rst_n=0,req_v=0,req_we=0;
    always #(CLK_PS/2) clk=~clk;
    reg [AW-1:0] req_addr=0;
    reg [TAGW-1:0] req_tag=0;
    reg [LENW-1:0] req_len=1;
    reg [255:0] req_wdata=0;
    wire req_rdy;
    wire [NPC-1:0] pc_room,rsp_v;
    reg [NPC-1:0] rsp_rdy=0;
    wire [NPC*TAGW-1:0] rsp_tag;
    wire [NPC*BEATW-1:0] rsp_beat;
    wire [NPC*256-1:0] rsp_data;
    ot_hdc_hbm_model #(.NPC(NPC),.AW(AW),.TAGW(TAGW),.LENW(LENW),
        .BEATW(BEATW),.QD(64),.RQD(32),.CLK_PS(CLK_PS),.PC_RDY(1),.MEM_WORDS(4096)) dut (.*);
    integer case_id=0,fd,rr=0,grant_client=0,accepted=0,read_beats=0,wr_accepted=0;
    integer seq[0:2],live_reads[0:2],peak_reads[0:2];
    bit taken=0,alias_observed=0;
    bit issued[0:63],done[0:63];
    integer length[0:63],owner[0:63],done_cycle[0:63];
    reg [31:0] seen[0:63];
    reg [NPC-1:0] prev_held=0;
    reg [NPC*TAGW-1:0] prev_tag=0;
    reg [NPC*BEATW-1:0] prev_beat=0;
    reg [NPC*256-1:0] prev_data=0;
    string journal;
    integer c,p,j,tag,beat,total_wr,qtotal,rtotal;
    function automatic [AW-1:0] kv_addr(input integer index);
        case(index)
            0:kv_addr=QHP_KV0;1:kv_addr=QHP_KV1;
            2:kv_addr=QHP_KV2;default:kv_addr=QHP_KV3;
        endcase
    endfunction
    function automatic [255:0] marker(input integer tag_id);
        marker={8{32'h71000000+tag_id}};
    endfunction
    initial begin
        if (!$value$plusargs("CASE=%d",case_id)) case_id=0;
        if (case_id<0 || case_id>2) $fatal(1,"unsupported bounded case");
        if (!$value$plusargs("QHP_CLIENT_JOURNAL=%s",journal))
            $fatal(1,"QHP_CLIENT_JOURNAL required");
        fd=$fopen(journal,"w");
        if (!fd) $fatal(1,"client journal open failed");
        $fdisplay(fd,"kind|sim_ps|model_ps|tag|len_or_beat|sector|owner");
        for (j=0;j<64;j=j+1) begin issued[j]=0;done[j]=0;seen[j]=0;length[j]=0;owner[j]=0;done_cycle[j]=0;end
        for (j=0;j<3;j=j+1) begin seq[j]=0;live_reads[j]=0;peak_reads[j]=0;end
        // Bounded synthetic initialization, not a checkpoint image.
        for (j=0;j<4096;j=j+1) dut.mem[j]={8{32'h51000000+j}};
        repeat(6) @(negedge clk);
        rst_n=1;
    end
    always @(negedge clk) if (rst_n) begin
        rsp_rdy=(case_id==1 && dut.cyc<4100) ? '0 :
                (case_id==0 && dut.cyc%11<4) ? '0 : '1;
        // Retain request identity until the actual source ready handshake.
        if (!(req_v && !taken)) begin
            req_v=0;
            if (case_id==0) begin
                for (integer step=0;step<3;step=step+1) begin
                    c=(rr+step)%3;
                    if (!req_v && seq[c]<4 &&
                        (c!=1 || (done[seq[1]] && dut.cyc>=done_cycle[seq[1]]+30)) &&
                        (c==1 ? wr_accepted<4 : live_reads[c]<4)) begin
                        req_v=1;grant_client=c;req_we=(c==1);
                        req_tag=16'(c*4+seq[c]);req_len=(c==2 ? 6'd32 : 6'd1);
                        req_addr=(c==2 ? QHP_WEIGHT+AW'(seq[c]*32) : kv_addr(seq[c]));
                        req_wdata=marker(c*4+seq[c]);
                    end
                end
            end else if (case_id==1 && seq[0]<34) begin
                req_v=1;grant_client=0;req_we=0;req_tag=16'(seq[0]);req_len=1;
                req_addr=(seq[0]<32 ? 0 : AW'(seq[0]-31));req_wdata=0;
            end else if (case_id==2 && seq[0]<4) begin
                total_wr=0;for (p=0;p<NPC;p=p+1) total_wr+=dut.st_wr[p];
                if (seq[0]<2 || total_wr==2) begin
                    req_v=1;grant_client=0;req_we=(seq[0]<2);req_tag=16'(seq[0]);req_len=1;
                    req_addr=(seq[0]%2==0 ? 34'd0 : (34'd1<<32));
                    req_wdata=marker(seq[0]);
                end
            end
        end
        total_wr=0;qtotal=0;rtotal=0;
        for (p=0;p<NPC;p=p+1) begin total_wr+=dut.st_wr[p];qtotal+=dut.q_n[p];rtotal+=dut.r_n[p];end
        if (dut.cyc>8000) $fatal(1,"bounded horizon; no timeout completion");
        if ((case_id==0 && accepted==12 && read_beats==132 && total_wr==4) ||
            (case_id==1 && accepted==34 && read_beats==34) ||
            (case_id==2 && accepted==4 && read_beats==2 && total_wr==2)) begin
            if (qtotal==0 && rtotal==0 && rsp_v==0) begin
                if (case_id==2 && !alias_observed) $fatal(1,"expected source modulo alias witness absent");
                $display("SOURCE_TRACE_COMPLETE_NOT_WR_PROVIDER_DONE case=%0d accepts=%0d read_beats=%0d WRpops=%0d retained_WRcredits=%0d alias_gap=%0d",case_id,accepted,read_beats,total_wr,wr_accepted,alias_observed);
                $finish;
            end
        end
    end
    always @(posedge clk) if (rst_n) begin
        taken=req_v && req_rdy;
        if (taken) begin
            tag=req_tag;
            if (tag>=64 || issued[tag]) $fatal(1,"unique bounded request tag");
            issued[tag]=1;length[tag]=req_len;owner[tag]=grant_client;
            accepted+=1;seq[grant_client]+=1;rr=(grant_client+1)%3;
            if (req_we) begin
                wr_accepted+=1; // Never released: source has no WR-visible port.
                if (case_id==0 && wr_accepted>4) $fatal(1,"finite WR budget");
            end else begin
                live_reads[grant_client]+=1;
                if (live_reads[grant_client]>peak_reads[grant_client]) peak_reads[grant_client]=live_reads[grant_client];
                if (case_id==0 && live_reads[grant_client]>4) $fatal(1,"finite read credit");
                if (case_id==1 && live_reads[grant_client]>34) $fatal(1,"finite stress credit");
            end
            $fdisplay(fd,"ACCEPT|%0d|%0d|%0d|%0d|%0d|%0d",$time,dut.cyc*CLK_PS,tag,req_len,req_addr,grant_client);
        end
        for (p=0;p<NPC;p=p+1) begin
            if (prev_held[p] && (!rsp_v[p] || rsp_tag[p*TAGW +: TAGW]!==prev_tag[p*TAGW +: TAGW] ||
                rsp_beat[p*BEATW +: BEATW]!==prev_beat[p*BEATW +: BEATW] || rsp_data[p*256 +: 256]!==prev_data[p*256 +: 256]))
                $fatal(1,"immutable held source return");
            if (rsp_v[p] && rsp_rdy[p]) begin
                tag=rsp_tag[p*TAGW +: TAGW];beat=rsp_beat[p*BEATW +: BEATW];
                if (tag>=64 || !issued[tag] || beat>=length[tag] || seen[tag][beat]) $fatal(1,"response identity/duplicate");
                seen[tag][beat]=1;read_beats+=1;
                if (seen[tag]==(length[tag]==32 ? 32'hffffffff : (32'd1<<length[tag])-1)) begin
                    done[tag]=1;done_cycle[tag]=dut.cyc;live_reads[owner[tag]]-=1;
                end
                if (case_id==2 && tag==2 && rsp_data[p*256 +: 256]===marker(1)) alias_observed=1;
                $fdisplay(fd,"READ_TAKE|%0d|%0d|%0d|%0d|-1|%0d",$time,dut.cyc*CLK_PS,tag,beat,owner[tag]);
            end
        end
        prev_held=rsp_v & ~rsp_rdy;prev_tag=rsp_tag;prev_beat=rsp_beat;prev_data=rsp_data;
    end
    final $fclose(fd);
endmodule
