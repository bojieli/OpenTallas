`timescale 1ns/1ps
`default_nettype none
module tb_hbm_vm_lg_static_split;
    parameter integer MUT=0;
    parameter integer TERMINAL=0;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;
    reg [135:0] local_rq[0:2];
    reg [2247:0] local_wq[0:2];
    reg [7:0] local_read[0:2],local_write[0:2];
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
            .clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd1),
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
        wire [7:0] bank_fault;
        assign tap_fault[s]=|bank_fault;
        if(s==2&&TERMINAL)begin:terminal_tap
            assign far_rr[s]=0;assign far_done[s]=0;
            ot_hbm_vm_lg_static_split_term #(.READ_RETURN(18),.WRITE_RETURN(15),.MUT(MUT)) tap(
                .clk({8{clk}}),.rst_n(rst_n),.local_rq(local_rq[s]),.local_wq(local_wq[s]),
                .local_read(local_read[s]),.local_write(local_write[s]),.near_rq(near_rq[s]),
                .near_wq(near_wq[s]),.near_rr(nrr),.near_w_done(ndone),.local_rr(local_rr[s]),
                .local_w_done(local_done[s]),.bank_fault(bank_fault));
        end else begin:through_tap
        ot_hbm_vm_lg_static_split #(.READ_RETURN(10+4*s),.WRITE_RETURN(7+4*s),.MUT(TERMINAL?0:MUT)) tap(
            .clk({8{clk}}),.rst_n(rst_n),.local_rq(local_rq[s]),.far_rq(frq),
            .local_wq(local_wq[s]),.far_wq(fwq),.local_read(local_read[s]),.local_write(local_write[s]),
            .near_rq(near_rq[s]),.near_wq(near_wq[s]),.near_rr(nrr),.near_w_done(ndone),
            .local_rr(local_rr[s]),.far_rr(far_rr[s]),.local_w_done(local_done[s]),.far_w_done(far_done[s]),.bank_fault(bank_fault));
        end
    end
    function automatic [255:0] payload(input integer station_id,row,bank_id);
        for(integer w=0;w<8;w=w+1)payload[w*32+:32]=32'h9e3779b9^32'(station_id<<28)^32'(row<<10)^32'(bank_id<<5)^32'(w);
    endfunction
    reg [7:0] exp_done[0:2][0:4095],exp_valid[0:2][0:4095];
    reg [2047:0] exp_data[0:2][0:4095];
    integer cycle=0,writes=0,reads=0;
    reg allow_fault=0,check_data=1;
    task clear_inputs;
        begin for(integer s=0;s<3;s=s+1)begin local_rq[s]=0;local_wq[s]=0;local_read[s]=0;local_write[s]=0;end end
    endtask
    task tick;
        integer row;
        begin
            @(posedge clk);
            if(rst_n)for(integer s=0;s<3;s=s+1)for(integer b=0;b<8;b=b+1)begin
                if(local_wq[s][b*281+280]&&local_write[s][b])exp_done[s][cycle+7+4*s][b]=1;
                if(local_rq[s][b*17+16]&&local_read[s][b])begin
                    row=int'(local_rq[s][b*17+3+:10]);
                    exp_valid[s][cycle+10+4*s][b]=1;
                    exp_data[s][cycle+10+4*s][b*256+:256]=payload(s,row%256,b);
                end
            end
            #2;
            if(rst_n)begin
                if(bank_status!==0||(!allow_fault&&tap_fault!==0))$fatal(1,"static LG fault cycle=%0d tap=%b banks=%h",cycle,tap_fault,bank_status);
                for(integer s=0;s<3;s=s+1)begin
                    if(local_done[s]!==exp_done[s][cycle])$fatal(1,"write phase mismatch cycle=%0d station=%0d got=%h expected=%h",cycle,s,local_done[s],exp_done[s][cycle]);
                    for(integer b=0;b<8;b=b+1)begin
                        if(local_done[s][b])writes=writes+1;
                        if(local_rr[s][b*257+256]!==exp_valid[s][cycle][b])$fatal(1,"read phase mismatch cycle=%0d station=%0d bank=%0d",cycle,s,b);
                        if(exp_valid[s][cycle][b])begin
                            if(check_data&&local_rr[s][b*257+:256]!==exp_data[s][cycle][b*256+:256])
                                $fatal(1,"actual bank readback mismatch cycle=%0d station=%0d bank=%0d got=%h expected=%h",cycle,s,b,local_rr[s][b*257+:32],exp_data[s][cycle][b*256+:32]);
                            reads=reads+1;
                        end
                    end
                end
                for(integer b=0;b<8;b=b+1)if(far_rr[2][b*257+256]||far_done[2][b])$fatal(1,"local return leaked beyond far HC");
            end
            cycle=cycle+1;@(negedge clk);
        end
    endtask
    initial begin
        integer owner,row;
        clear_inputs();
        for(integer s=0;s<3;s=s+1)for(integer c=0;c<4096;c=c+1)begin exp_done[s][c]=0;exp_valid[s][c]=0;exp_data[s][c]=0;end
        repeat(8)tick();rst_n=1;
        // Fill 128 distinct rows per producer/bank, one eight-bank wave each
        // source per three cycles, all three issue together. Forward delays
        // (2/4/6edges to VM sample) pack arrival phases2/1/0 mod3:
        // eight sectors every VM cycle after initial pipeline fill.
        for(integer t=0;t<384;t=t+1)begin
            clear_inputs();
            if(t%3==0)for(owner=0;owner<3;owner=owner+1)begin
                row=t/3;
                local_write[owner]=8'hff;
                for(integer b=0;b<8;b=b+1)local_wq[owner][b*281+:281]=
                    {1'b1,1'b0,2'd1,10'(owner*256+row),3'(b),payload(owner,row,b),8'hff};
            end
            tick();
        end
        clear_inputs();repeat(20)tick();
        // Same calendar reads every source's exact stored payload.
        for(integer t=0;t<384;t=t+1)begin
            clear_inputs();
            if(t%3==0)for(owner=0;owner<3;owner=owner+1)begin
                row=t/3;local_read[owner]=8'hff;
                for(integer b=0;b<8;b=b+1)local_rq[owner][b*17+:17]={1'b1,1'b0,2'd1,10'(owner*256+row),3'(b)};
            end
            tick();
        end
        clear_inputs();repeat(24)tick();
        if(writes!=3072||reads!=3072)$fatal(1,"missing production traffic writes=%0d reads=%0d",writes,reads);
        // Deliberately suppress one real VM response valid. The HC reservation
        // still emits at+18 and faults; no credit/wait or late local replay.
        allow_fault=1;drop_response=1;local_read[2]=1;
        local_rq[2][0+:17]={1'b1,1'b0,2'd1,10'd512,3'd0};tick();
        clear_inputs();repeat(21)tick();
        if(!tap_fault[2]||writes!=3072||reads!=3073)$fatal(1,"missing response was delayed rather than faulted");
        drop_response=0;check_data=0;
        // An active local request without its compiler select is diagnosed and
        // cannot enter the downstream path on a later edge.
        local_rq[0][0+:17]={1'b1,1'b0,2'd1,10'd0,3'd0};tick();clear_inputs();
        repeat(3)tick();if(!tap_fault[0])$fatal(1,"unselected local request not diagnosed");
        // HC's wave reaches the middle tap two edges after HC input sample.
        // Issue SFU on that same bank/edge to violate the calendar explicitly.
        local_read[2]=1;local_rq[2][0+:17]={1'b1,1'b0,2'd1,10'd512,3'd0};tick();
        clear_inputs();tick();
        local_read[1]=1;local_rq[1][0+:17]={1'b1,1'b0,2'd1,10'd256,3'd0};tick();
        clear_inputs();repeat(21)tick();
        if(!tap_fault[1])$fatal(1,"far/local collision not diagnosed");
        $display("VM_LG_STATIC_SPLIT PASS taps=3 banks=8 SRAMs=24 writes=3072 exact_readbacks=3072 issue_cycles_per_phase=384 sectors_per_cycle=8 SU_RD=10 SFU_RD=14 HC_RD=18 SU_WR=7 SFU_WR=11 HC_WR=15 missing_response_fixed_phase=1 unselected_local_fault=1 collision_fault=1");
        $finish;
    end
endmodule
`default_nettype wire
