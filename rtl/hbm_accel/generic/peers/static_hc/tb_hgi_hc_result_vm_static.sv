`timescale 1ns/1ps
`default_nettype none
module tb_hgi_hc_result_vm_static;
    parameter integer MUT=0;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;
    reg [135:0] local_rq[0:2];
    wire [2247:0] local_wq[0:2];
    reg [7:0] local_read[0:2];
    wire [7:0] local_write[0:2];
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
        ot_hbm_vm_lg_static_tap #(.READ_RETURN(10+4*s),.WRITE_RETURN(7+4*s),.MUT(0)) tap(
            .clk(clk),.rst_n(rst_n),.local_rq(local_rq[s]),.far_rq(frq),
            .local_wq(local_wq[s]),.far_wq(fwq),.local_read(local_read[s]),.local_write(local_write[s]),
            .near_rq(near_rq[s]),.near_wq(near_wq[s]),.near_rr(nrr),.near_w_done(ndone),
            .local_rr(local_rr[s]),.far_rr(far_rr[s]),.local_w_done(local_done[s]),.far_w_done(far_done[s]),.fault(tap_fault[s]));
    end
    reg store_slot=0,result_v=0;
    reg [2:0] position=0;
    reg [767:0] result=0;
    wire producer_fault;
    localparam [15:0] BASE=16'd8198; // bank6 ->7 ->0, then further bank/row wraps
    assign local_wq[0]=0;assign local_wq[1]=0;
    assign local_write[0]=0;assign local_write[1]=0;
    ot_hgi_hc_result_vm_static producer(.clk(clk),.rst_n(rst_n),.store_slot(store_slot && MUT!=2),
        .base_sector(BASE),.store_position(position),.result_v(result_v),
        .result_position(position ^ (MUT==1 ? 3'd1 : 3'd0)),.result(result ^ (MUT==3 ? 768'd1 : 768'd0)),
        .local_wq(local_wq[2]),.local_write(local_write[2]),.fault(producer_fault));
    function automatic [31:0] word_value(input integer p,w);
        word_value=32'h3f800001 ^ (32'(p)*32'h00110011) ^ (32'(w)*32'h00010301);
    endfunction
    function automatic [255:0] sector_data(input integer sector);
        integer offset;
        begin
            offset=sector-int'(BASE);
            for(integer w=0;w<8;w=w+1)
                sector_data[w*32+:32]=(offset>=0 && offset<24) ? word_value(offset/3,(offset%3)*8+w) : 0;
        end
    endfunction
    reg [7:0] exp_done[0:1023],exp_valid[0:1023];
    reg [2047:0] exp_data[0:1023];
    integer cycle=0,writes=0,readbacks=0,consumer_reads=0;
    task clear_reads;
        begin for(integer s=0;s<3;s=s+1)begin local_rq[s]=0;local_read[s]=0;end end
    endtask
    task tick;
        integer sector;
        begin
            @(posedge clk);
            // A real consumer FF samples the old registered return on edge n+19.
            if(rst_n && cycle>0)for(integer b=0;b<8;b=b+1)begin
                if(local_rr[2][b*257+256]!==exp_valid[cycle-1][b])$fatal(1,"consumer phase mismatch");
                if(exp_valid[cycle-1][b])begin
                    if(local_rr[2][b*257+:256]!==exp_data[cycle-1][b*256+:256])$fatal(1,"consumer data mismatch");
                    consumer_reads=consumer_reads+1;
                end
            end
            if(rst_n)for(integer b=0;b<8;b=b+1)begin
                if(local_write[2][b]&&local_wq[2][b*281+280])exp_done[cycle+15][b]=1;
                if(local_read[2][b]&&local_rq[2][b*17+16])begin
                    sector=int'(local_rq[2][b*17+:16]);
                    exp_valid[cycle+18][b]=1;
                    exp_data[cycle+18][b*256+:256]=sector_data(sector);
                end
            end
            #2;
            if(rst_n)begin
                if(producer_fault||tap_fault!==0||bank_status!==0)$fatal(1,"source identity/calendar fault cycle=%0d producer=%b taps=%b banks=%h",cycle,producer_fault,tap_fault,bank_status);
                if(local_done[2]!==exp_done[cycle])$fatal(1,"write phase mismatch cycle=%0d",cycle);
                for(integer b=0;b<8;b=b+1)begin
                    if(local_done[2][b])writes=writes+1;
                    if(local_rr[2][b*257+256]!==exp_valid[cycle][b])$fatal(1,"read phase mismatch cycle=%0d",cycle);
                    if(exp_valid[cycle][b])begin
                        if(local_rr[2][b*257+:256]!==exp_data[cycle][b*256+:256])$fatal(1,"actual SRAM result readback mismatch cycle=%0d bank=%0d",cycle,b);
                        readbacks=readbacks+1;
                    end
                    if(far_rr[2][b*257+256]||far_done[2][b])$fatal(1,"return leaked past HC");
                end
            end
            cycle=cycle+1;@(negedge clk);
        end
    endtask
    initial begin
        integer sector,bank;
        clear_reads();
        for(integer c=0;c<1024;c=c+1)begin exp_done[c]=0;exp_valid[c]=0;exp_data[c]=0;end
        repeat(8)tick();rst_n=1;
        for(integer p=0;p<8;p=p+1)begin
            store_slot=1;result_v=1;position=3'(p);
            for(integer w=0;w<24;w=w+1)result[w*32+:32]=word_value(p,w);
            tick();
        end
        store_slot=0;result_v=0;repeat(24)tick();
        // All192 words plus untouched neighboring sectors. One native eight-bank wave/cycle.
        for(integer offset=-1;offset<25;offset=offset+8)begin
            clear_reads();
            for(integer j=0;j<8;j=j+1)if(offset+j<25)begin
                sector=int'(BASE)+offset+j;bank=sector%8;
                local_read[2][bank]=1;local_rq[2][bank*17+:17]={1'b1,16'(sector)};
            end
            tick();
        end
        clear_reads();repeat(24)tick();
        if(writes!=24||readbacks!=26||consumer_reads!=26)$fatal(1,"traffic missing writes=%0d readbacks=%0d consumer=%0d",writes,readbacks,consumer_reads);
        $display("HC_RESULT_VM_STATIC PASS positions=8 result_words=192 sectors=24 neighbor_sectors=2 banks=8 SRAMs=24 tap_write_edges=15 tap_read_edges=18 consumer_read_edges=19 writes=%0d readbacks=%0d",writes,readbacks);
        $finish;
    end
endmodule
`default_nettype wire
