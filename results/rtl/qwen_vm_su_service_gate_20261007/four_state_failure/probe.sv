`timescale 1ns/1ps
// Changed-adapter protocol component ONLY. Full16 bank geometry is unchanged;
// five read/16write seats keep this independent test finite, not a production
// capacity or native-SU/numerical qualification. Initial raw bytes are from
// Ampere's pinned, authorized HEAD initial fixture, not normalized activations.
module tb_qwen_su_service_gate;
    localparam NR=5,NW=16,VX0=3,NVX=2;
    reg clk=0,rst_n=0;
    always #5 clk=~clk;
    reg me_wanted=0;reg tracking=0;
 wire[15:0]progress,progress_rows;wire chased;
 source_progress p(.clk(native_clk),.rst_n(rst_n && tracking),.retire(tracking && (|we)),.emit(tracking && (|we)),.accept(1'b0),.v_last_r(1'b1),.l_last(1'b1),.progress(progress),.progress_rows(progress_rows),.chased_out(chased));
    reg [NR-1:0] re=0;
    reg [NR*24-1:0] ra=0;
    wire [NR*32-1:0] rq;
    reg [NW-1:0] we=0;
    reg [NW*24-1:0] wa=0;
    reg [NW*32-1:0] wd=0;
    wire tick,lease,drained,fault;
    wire [63:0] epoch,reads,writes,acks,held;
    wire native_clk;
    reg [63:0] native_edges=0,raw_acks=0;
    reg [31:0] initial_x[0:4095];
    reg [1023:0] fixture_path;
    integer negative=0;
    ot_hdc_cg u_gate(.clk(clk),.en(!rst_n||tick||(negative==2 && tracking && dut.pack_valid)),.gclk(native_clk));
    always @(posedge native_clk)if(rst_n)native_edges<=native_edges+1;
    ot_qwen_finite_vm_adapter #(.ENABLE(1),.HEAD_CACHE(0),
        .NR(NR),.NW(NW),.VX0(VX0),.NVX(NVX)) dut(
        .clk(clk),.rst_n(rst_n),.source_me_wanted(me_wanted),.head_source_producer_go(1'b0),
        .read_en(re),.read_addr(ra),.read_q(rq),.write_en(we),.write_addr(wa),.write_data(wd),
        .native_tick(tick),.native_me_lease(lease),.drained(drained),.fault(fault),
        .native_epoch(epoch),.physical_reads(reads),.physical_writes(writes),.physical_ACKs(acks),
        .held_edges(held),.head_fill_reads(),.head_hit_edges());
    always @(posedge clk)if(rst_n)begin
        if(|dut.g_bound.u_bank.raw_ack)raw_acks<=raw_acks+1;
        if(tick && dut.pack_valid)$fatal(1,"native admission with unpaid write pack");
        if(tick && fault)$fatal(1,"faulted native admission");
    end
    // Bound is derived from all seats missing independently and all writes
    // flushing independently, with the actual9/28 calendar and control seats.
    // This detects a protocol deadlock; no process/wall/resource time limit.
    localparam FRAME_BOUND=2+NR*14+NW*33+32;
    task automatic frame;
        integer steps;reg [63:0] before_epoch,before_native,before_acks;
        begin
            before_epoch=epoch;before_native=native_edges;before_acks=acks;
            steps=0;
            do begin
                @(posedge clk);#1;steps=steps+1;
                if(fault)begin
                    if(negative==1 && tracking && !tick && !lease && native_edges==before_native && progress==0 && !chased)begin $display("REJECTED foreign_postverified_ACK_owner native_held progress0");$finish;end
                    $fatal(1,"unexpected frame fault");
                end
                if(tracking && epoch==before_epoch && (progress!=0 || chased))$fatal(1,"PREMATURE_CHASE_WITH_UNPAID_FRAME");
                if(epoch==before_epoch && native_edges!=before_native)$fatal(1,"UNPAID_NATIVE_ADVANCE");
                if(steps>FRAME_BOUND)$fatal(1,"finite frame failed to drain within source-derived bound");
            end while(epoch==before_epoch);
            if(native_edges!=before_native+1)$fatal(1,"native controller/adapter edge mismatch");
            if((|we) && acks==before_acks)$fatal(1,"write admitted without positive physical ACK");
            if(!drained)$fatal(1,"native source admitted before frame drain");
            $display("FRAME steps=%0d native=%0d checked_ACK_delta=%0d reads=%0d writes=%0d progress=%0d chased=%0d",steps,native_edges,acks-before_acks,reads,writes,progress,chased);
            @(negedge clk);re=0;we=0;
        end
    endtask
    task automatic install(input integer base,input integer fixture_offset);
        begin
            for(integer i=0;i<16;i=i+1)begin
                we[i]=1;wa[i*24+:24]=base+i;wd[i*32+:32]=initial_x[fixture_offset+i];
            end
            frame();
        end
    endtask
    initial begin
        if(!$value$plusargs("FIXTURE=%s",fixture_path))$fatal(1,"mandatory actual initial fixture missing");
        if($value$plusargs("NEGATIVE=%d",negative))begin end
        $readmemh(fixture_path,initial_x);
        if(^initial_x[0]===1'bx || ^initial_x[4095]===1'bx)$fatal(1,"incomplete initial fixture");
        repeat(3)@(negedge clk);rst_n=1;
        // Actual PC19/27 cycle39 fold128 bank0 witness: VA lane48=6192, VB lane0=0, VC lane16=2064.
        // Original bank4 service sees these real addresses; no fold128 RTL claim.
        install(6192,0);install(0,64);install(2064,128);
        if(acks!=3 || raw_acks!=3)$fatal(1,"initial source installation missing checked ACK");
        re=7;ra[0+:24]=6192;ra[24+:24]=0;ra[48+:24]=2064;
        frame();
        $display("CONFLICT got=%h,%h,%h expected=%h,%h,%h",rq[0+:32],rq[32+:32],rq[64+:32],initial_x[0],initial_x[64],initial_x[128]);
        if(rq[0+:32]!==initial_x[0] || rq[32+:32]!==initial_x[64] || rq[64+:32]!==initial_x[128])$fatal(1,"captured SU conflict address returns mismatch");
        // Actual PC18/26 cycle26 contains B scalar0 read and SU lane0 scalar0 write.
        tracking=1;re=3;ra[0+:24]=0;ra[24+:24]=1;
        we=1;wa[0+:24]=0;wd[0+:32]=initial_x[65];
        frame();
        if(rq[0+:32]!==initial_x[64] || rq[32+:32]!==initial_x[65])$fatal(1,"captured alias lost pre-edge old read");
        if(acks!=4 || raw_acks!=4)$fatal(1,"alias release before actual postverified ACK");
        // Native production counter equations become visible only on admitted native edges.
        repeat(2)begin @(posedge clk);#1;end
        if(progress!=1 || !chased)$fatal(1,"paid native progress did not reach CHASE1");
        @(negedge clk);tracking=0;
        re=3;ra[0+:24]=0;ra[24+:24]=1;frame();
        if(rq[0+:32]!==initial_x[65] || rq[32+:32]!==initial_x[65])$fatal(1,"postverified alias readback or neighbor mismatch");
        $display("PASS captured_SU_conflict oldread_alias postverified_ACK gated_native_progress CHASE1 writes=%0d checked_ACKs=%0d raw_ACKs=%0d reads=%0d held=%0d native=%0d",writes,acks,raw_acks,reads,held,native_edges);
        $finish;
    end
    initial begin
        wait(tracking);
        if(negative==1)begin
            wait(|dut.wr_ACK);
            force dut.wr_ACK_owner=908'h1;
        end
        if(negative==3)begin
            wait(dut.pack_valid);
            force progress=16'd1;
        end
    end
    // Measure provider latency from real accepted command to checked response/ACK.
    integer physical_cycle=0,read_start=-1,write_start=-1;
    always @(posedge clk)begin
        physical_cycle<=physical_cycle+1;
        if(rst_n)begin
            if(dut.rd_accept)read_start=physical_cycle;
            if(|dut.wr_accept)write_start=physical_cycle;
            if(dut.rd_valid)begin
                if(read_start<0 || physical_cycle-read_start!=9)$fatal(1,"read service changed from model9");
                $display("READ_SERVICE edges=%0d words=%h decoded=%h raw=%h checks=%h",physical_cycle-read_start,dut.rd_words[31:0],dut.g_bound.u_bank.decoded[31:0],dut.g_bound.u_bank.raw_words[31:0],dut.g_bound.u_bank.sampled_checks[7:0]);$display("DETAIL macro=%h mask=%h part=%h sel=%b salt=%b group=%h",dut.g_bound.u_bank.u_data.g_masked.u_native.g_bank[0].g_group[0].g_live.macro_word[31:0],dut.g_bound.u_bank.u_data.g_masked.u_native.g_bank[0].g_group[0].g_live.mask_q[31:0],dut.g_bound.u_bank.u_data.g_masked.u_native.g_bank[0].partial_q[0][31:0],dut.g_bound.u_bank.u_data.g_masked.u_native.g_bank[0].g_group[0].g_live.g_segment[0].sel_code_q,dut.g_bound.u_bank.u_data.g_masked.u_native.g_bank[0].g_group[0].g_live.g_segment[0].salt_q,dut.g_bound.u_bank.u_data.g_masked.u_native.g_bank[0].rd_group_cmd_q);$display("OTHER part1=%h part2=%h part3=%h bank=%h output=%h",dut.g_bound.u_bank.u_data.g_masked.u_native.g_bank[0].partial_q[1][31:0],dut.g_bound.u_bank.u_data.g_masked.u_native.g_bank[0].partial_q[2][31:0],dut.g_bound.u_bank.u_data.g_masked.u_native.g_bank[0].partial_q[3][31:0],dut.g_bound.u_bank.u_data.g_masked.u_native.bank_word[0][31:0],dut.g_bound.u_bank.u_data.g_masked.u_native.rd_out_bank_words[31:0]);$display("READ_MACRO_BASE base_word=%0d bank0=%h bank1=%h bank2=%h bank3=%h",dut.requested_base,dut.g_bound.u_bank.u_data.g_masked.u_native.g_bank[0].g_group[0].g_live.macro_word[31:0],dut.g_bound.u_bank.u_data.g_masked.u_native.g_bank[1].g_group[0].g_live.macro_word[31:0],dut.g_bound.u_bank.u_data.g_masked.u_native.g_bank[2].g_group[0].g_live.macro_word[31:0],dut.g_bound.u_bank.u_data.g_masked.u_native.g_bank[3].g_group[0].g_live.macro_word[31:0]);read_start=-1;
            end
            if(|dut.wr_ACK)begin
                if(write_start<0 || physical_cycle-write_start!=28)$fatal(1,"write service changed from model28");
                $display("POSTVERIFIED_ACK bank=%d decoded_unknown=%b merged_unknown=%b equality_result=%b",dut.g_bound.u_bank.bank,$isunknown(dut.g_bound.u_bank.decoded[dut.g_bound.u_bank.bank*512+:512]),$isunknown(dut.g_bound.u_bank.merged),dut.g_bound.u_bank.decoded[dut.g_bound.u_bank.bank*512+:512]!=dut.g_bound.u_bank.merged);
                $display("WRITE_SERVICE checked_edges=%0d",physical_cycle-write_start);write_start=-1;
            end
        end
    end
endmodule
