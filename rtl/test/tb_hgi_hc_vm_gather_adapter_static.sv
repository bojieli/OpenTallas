`timescale 1ns/1ps
`default_nettype none
module tb_hgi_hc_vm_gather_adapter_static;

    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;
    wire [135:0] local_rq[0:2];
    reg [2247:0] local_wq[0:2];
    wire [7:0] local_read[0:2];
    reg [7:0] local_write[0:2];
    wire [135:0] near_rq[0:2];
    wire [2247:0] near_wq[0:2];
    wire [2055:0] local_rr[0:2],far_rr[0:2];
    wire [7:0] local_done[0:2],far_done[0:2];
    wire [2:0] tap_fault;
    wire [2055:0] bank_rr;
    reg drop_response=0;
    wire [2055:0] bank_rr_input;
    wire [7:0] bank_done;
    wire [143:0] bank_status;
    for(genvar b=0;b<8;b=b+1)begin:memory
        wire [770:0] rr;
        assign bank_rr[b*257+:257]=rr[0+:257];
        assign bank_rr_input[b*257+:257]={bank_rr[b*257+256]&&!(drop_response&&b==0),bank_rr[b*257+:256]};
        ot_vms_bank_static #(.RG(3),.WG(1)) bank(
            .clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd2),
            .rslot_v(1'b1),.rslot(2'd0),.wslot_v(1'b1),.wslot(3'd0),
            .rq({34'd0,near_rq[0][b*17+:17]}),.rr(rr),
            .wq(near_wq[0][b*281+:281]),.wq_done(bank_done[b]),
            .dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),
            .xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
            .eg(),.pq(285'd0),.pr(),.status(bank_status[b*18+:18]));
    end
    for(genvar s=0;s<3;s=s+1)begin:station
        wire [135:0] frq;
        wire [2247:0] fwq;
        wire [2055:0] nrr;
        wire [7:0] ndone;
        if(s==2)begin:end_station
            assign frq=0;assign fwq=0;
        end else begin:far_station
            assign frq=near_rq[s+1];assign fwq=near_wq[s+1];
        end
        if(s==0)begin:vm_return
            assign nrr=bank_rr_input;assign ndone=bank_done;
        end else begin:forward_return
            assign nrr=far_rr[s-1];assign ndone=far_done[s-1];
        end
        ot_hbm_vm_lg_static_tap #(.READ_RETURN(10+4*s),.WRITE_RETURN(7+4*s),.MUT(0)) tap(
            .clk(clk),.rst_n(rst_n),.local_rq(local_rq[s]),.far_rq(frq),
            .local_wq(local_wq[s]),.far_wq(fwq),.local_read(local_read[s]),.local_write(local_write[s]),
            .near_rq(near_rq[s]),.near_wq(near_wq[s]),.near_rr(nrr),.near_w_done(ndone),
            .local_rr(local_rr[s]),.far_rr(far_rr[s]),.local_w_done(local_done[s]),.far_w_done(far_done[s]),.fault(tap_fault[s]));
    end
    reg launch=0;
    reg [3:0] npos=8;
    reg [15:0] stride=3,base_sector=18136;
    wire mix_v,done,reader_fault;
    wire [4:0] mix_row;
    wire [2:0] mix_pos;
    wire [31:0] mix_data;
    reg suppress=0,unsolicited=0;
    wire [2055:0] reader_rr;
    for(genvar b=0;b<8;b=b+1)begin:rr_pin
        assign reader_rr[b*257+:257]={((local_rr[2][b*257+256]&&!suppress)||(unsolicited&&b==0)),local_rr[2][b*257+:256]};
    end
    reg [135:0] neighbor_rq=0;reg [7:0] neighbor_read=0;
    assign local_rq[0]=neighbor_rq;assign local_rq[1]=0;
    assign local_read[0]=neighbor_read;assign local_read[1]=0;
    reg gather_phase=1;
    reg [135:0] residual_rq=0;
    reg [7:0] residual_read=0;
    wire [2055:0] residual_rr;
    ot_hgi_hc_vm_gather_adapter_static #(.ENABLE_GATHER_READER(1)) dut(
        .clk(clk),.rst_n(rst_n),.gather_phase(gather_phase),.gather_launch(launch),
        .gather_npos(npos),.gather_base_sector(base_sector),.gather_stride_sector(stride),
        .residual_rq(residual_rq),.residual_read(residual_read),.residual_rr(residual_rr),
        .local_rq(local_rq[2]),.local_read(local_read[2]),.local_rr(reader_rr),
        .external_mix_v(1'b0),.external_mix_row(5'd0),.external_mix_pos(3'd0),.external_mix_data(32'd0),
        .gathered_mix_v(mix_v),.gathered_mix_row(mix_row),.gathered_mix_pos(mix_pos),.gathered_mix_data(mix_data),.gather_done(done),.fault(reader_fault));
    // Disabled opt-in must preserve every residual/external payload bit with
    // no added pipeline, even when future gather controls are asserted.
    wire [135:0] legacy_rq;
    wire [7:0] legacy_read;
    wire [2055:0] legacy_rr;
    wire [40:0] legacy_mix;
    wire legacy_done,legacy_fault;
    ot_hgi_hc_vm_gather_adapter_static legacy(
        .clk(clk),.rst_n(rst_n),.gather_phase(1'b1),.gather_launch(launch),
        .gather_npos(npos),.gather_base_sector(base_sector),.gather_stride_sector(stride),
        .residual_rq(residual_rq),.residual_read(residual_read),.residual_rr(legacy_rr),
        .local_rq(legacy_rq),.local_read(legacy_read),.local_rr(reader_rr),
        .external_mix_v(launch),.external_mix_row(5'd23),.external_mix_pos(3'd7),.external_mix_data(32'h89abcdef),
        .gathered_mix_v(legacy_mix[40]),.gathered_mix_row(legacy_mix[39:35]),.gathered_mix_pos(legacy_mix[34:32]),.gathered_mix_data(legacy_mix[31:0]),.gather_done(legacy_done),.fault(legacy_fault));
    function automatic [255:0] payload(input integer sector);
        for(integer w=0;w<8;w=w+1)payload[w*32+:32]=32'h3f804321^(32'(sector)*32'h00010101)^(32'(w)*32'h000f1249);
    endfunction
    integer cycle=0,start_cycle=-10000,seen=0,consumed=0,requests=0,cases=0;
    integer expected_words=0,total_words=0;
    reg check=0,allow_fault=0,mutant=0;
    task tick;
        integer t,p,r,sector;
        reg [255:0] data;
        begin
            @(posedge clk);
            if(check&&mix_v)begin
                t=cycle-start_cycle-21;p=t/24;r=t%24;
                if(t<0||t>=expected_words||mix_pos!==3'(p)||mix_row!==5'(r))$fatal(1,"engine capture phase/tag mismatch");
                consumed=consumed+1;
            end
            if(check)for(integer b=0;b<8;b=b+1)if(local_read[2][b])requests=requests+1;
            #2;
            if(rst_n)begin
                if(legacy_rq!==residual_rq||legacy_read!==residual_read||legacy_rr!==reader_rr||
                   legacy_mix!=={launch,5'd23,3'd7,32'h89abcdef}||legacy_done||legacy_fault)$fatal(1,"disabled interface changed");
                if(bank_status!==0||tap_fault!==0||(!allow_fault&&reader_fault))$fatal(1,"native/reader fault cycle=%0d reader=%b taps=%b bank=%h",cycle,reader_fault,tap_fault,bank_status);
                if(check)begin
                    t=cycle-start_cycle-20;
                    if(mix_v!==(t>=0&&t<expected_words))$fatal(1,"fixed output slot mismatch cycle=%0d age=%0d",cycle,cycle-start_cycle);
                    if(mix_v)begin
                        p=t/24;r=t%24;sector=int'(base_sector)+p*int'(stride)+r/8;data=payload(sector);
                        if(mix_pos!==3'(p)||mix_row!==5'(r)||mix_data!==data[(r%8)*32+:32])
                            $fatal(1,"actual SRAM gathered_mix mismatch cycle=%0d pos=%0d row=%0d got=%h expected=%h",cycle,p,r,mix_data,data[(r%8)*32+:32]);
                        seen=seen+1;total_words=total_words+1;
                    end
                    if(done!==(t==expected_words-1))$fatal(1,"done phase mismatch");
                end
            end
            cycle=cycle+1;@(negedge clk);
        end
    endtask
    task reset_reader;
        begin launch=0;check=0;rst_n=0;suppress=0;unsolicited=0;repeat(6)tick();rst_n=1;repeat(4)tick();end
    endtask
    task neighbors;
        integer s,b;
        reg [255:0] data;
        begin
            neighbor_rq=0;neighbor_read=0;
            for(integer j=0;j<2;j=j+1)begin
                s=j==0?18135:18174;b=s%8;neighbor_read[b]=1;neighbor_rq[b*17+:17]={1'b1,16'(s)};
            end
            tick();neighbor_rq=0;neighbor_read=0;repeat(10)tick();
            for(integer j=0;j<2;j=j+1)begin
                s=j==0?18135:18174;b=s%8;data=payload(s);
                if(local_rr[0][b*257+:257]!=={1'b1,data})$fatal(1,"neighbor SRAM changed");
            end
            tick();
        end
    endtask
    task execute(input integer n,st);
        begin
            npos=4'(n);stride=16'(st);seen=0;consumed=0;requests=0;expected_words=24*n;
            start_cycle=cycle;launch=1;check=1;
            if($test$plusargs("COLLISION")&&n==1)begin residual_read=1;residual_rq[0+:17]={1'b1,16'd18136};end
            tick();launch=0;residual_read=0;residual_rq=0;
            repeat(20+24*n+2)tick();check=0;
            if(seen!=24*n||consumed!=24*n||requests!=3*n)$fatal(1,"missing real traffic");
            if(dut.native_gather.reader.issued!==4'(n)||dut.native_gather.reader.returned!==4'(n)||dut.native_gather.reader.active||mix_v||done)$fatal(1,"finish counter underflow or late stream");
            if(n==1&&st==0)$display("HC_GATHERED_MIX_CANONICAL_P1 PASS base18136 SID2 stride0 words24 requests3 output20 last43 capture21_last44 finish_counters1 inactive_no_late_stream");
            cases=cases+1;
        end
    endtask
    initial begin
        integer sector,bank;
        reg [255:0] data;
        mutant=$test$plusargs("MUTANT");
        for(integer s=0;s<3;s=s+1)begin local_wq[s]=0;local_write[s]=0;end
        repeat(8)tick();rst_n=1;
        // Real SRAM write path preloads full source region and both neighbors.
        for(integer offset=-1;offset<44;offset=offset+1)begin
            sector=18136+offset;bank=sector%8;data=payload(sector);
            if(mutant&&sector==18136)data=data^256'd1;
            local_wq[0]=0;local_write[0]=0;local_write[0][bank]=1;
            local_wq[0][bank*281+:281]={1'b1,16'(sector),data,8'hff};tick();
        end
        local_wq[0]=0;local_write[0]=0;repeat(12)tick();
        // Actual residual read travels through the SAME far-HC port in its
        // compiler phase; adapter adds no request/return edge.
        gather_phase=0;residual_read=1;residual_rq[0+:17]={1'b1,16'd18136};tick();residual_read=0;residual_rq=0;
        repeat(18)tick();
        if(residual_rr[0+:257]!=={1'b1,payload(18136)})$fatal(1,"residual mux readback mismatch");
        tick();gather_phase=1;
        neighbors();execute(1,0);execute(6,3);execute(8,3);execute(6,5);execute(8,5);neighbors();
        // Guards diagnose exceptions without normal-cycle rescheduling.
        allow_fault=1;reset_reader();npos=8;stride=3;launch=1;tick();launch=0;tick();launch=1;tick();launch=0;
        if(!reader_fault)$fatal(1,"overlapping launch not diagnosed");
        repeat(220)tick();reset_reader();npos=0;launch=1;tick();launch=0;
        if(!reader_fault||local_read[2]!==0)$fatal(1,"invalid npos not rejected");
        reset_reader();npos=8;base_sector=24574;launch=1;tick();launch=0;
        if(!reader_fault||local_read[2]!==0)$fatal(1,"SID-crossing bounds not rejected");
        base_sector=18136;reset_reader();unsolicited=1;tick();unsolicited=0;
        if(!reader_fault)$fatal(1,"unsolicited response not diagnosed");
        reset_reader();npos=1;start_cycle=cycle;launch=1;tick();launch=0;suppress=1;repeat(20)tick();
        if(!reader_fault||!mix_v)$fatal(1,"missing response stalled or undiagnosed");
        suppress=0;repeat(28)tick();
        if(total_words!=696)$fatal(1,"production coverage incomplete");
        $display("HC_VM_GATHER_ADAPTER PASS cases=%0d words=%0d canonical_P1_stride0 plus_component_npos6_8_stride3_5 sector18136 SID2 banks8 SRAM24 taps3 request1 output20 capture21 fixed_stream1 faultguards5",cases,total_words);
        $finish;
    end
endmodule
`default_nettype wire
