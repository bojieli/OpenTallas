`timescale 1ns/1ps
`default_nettype none
module tb_hbm_vm_lg_static_programmed;
    parameter integer MUT=0;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;
    reg [135:0] local_rq[0:2];
    reg [2247:0] local_wq[0:2];
    wire [7:0] local_read[0:2],local_write[0:2];
    wire [23:0] programmed_read,programmed_write;
    wire [7:0] programmed_rv,programmed_wv;
    wire [23:0] programmed_rs,programmed_ws;
    reg cfg_we=0,start_v=0;
    reg [9:0] cfg_addr=0;
    reg [255:0] cfg_data=0;
    reg [255:0] image[0:811];
    wire cal_v,cal_done,cal_active,cal_fault;
    wire [31:0] ordinal;
    hfd_hgi_vm_calendar_NE controller(.clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.start_v(start_v),.start_base(10'd0),.start_limit(11'd812),.start_loops(16'd1),.calendar_v(cal_v),.active(cal_active),.done(cal_done),.fault(cal_fault),.ordinal(ordinal),.rslot_v(programmed_rv),.wslot_v(programmed_wv),.rslot(programmed_rs),.wslot(programmed_ws),.lg_local_read(programmed_read),.lg_local_write(programmed_write));
    for(genvar c=0;c<3;c++)begin:controlassign
        assign local_read[c]=programmed_read[c*8+:8];
        assign local_write[c]=programmed_write[c*8+:8];
    end
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
        wire [1798:0] rr;
        wire [2:0] all_w_done;
        assign bank_done[b]=all_w_done[0];
        assign bank_rr[b*257+:257]=rr[0+:257];
        assign bank_rr_input[b*257+:257]={bank_rr[b*257+256]&&!(drop_response&&b==0),bank_rr[b*257+:256]};
        ot_vms_bank_static #(.RG(7),.WG(3)) bank(
            .clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd1),
            .rslot_v(programmed_rv[b]),.rslot(programmed_rs[b*3+:3]),.wslot_v(programmed_wv[b]),.wslot(programmed_ws[b*3+:3]),
            .rq({102'd0,near_rq[0][b*17+:17]}),.rr(rr),
            .wq({562'd0,near_wq[0][b*281+:281]}),.wq_done(all_w_done),
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
        ot_hbm_vm_lg_static_split #(.READ_RETURN(10+4*s),.WRITE_RETURN(7+4*s),.MUT(MUT)) tap(
            .clk({8{clk}}),.rst_n(rst_n),.local_rq(local_rq[s]),.far_rq(frq),
            .local_wq(local_wq[s]),.far_wq(fwq),.local_read(local_read[s]),.local_write(local_write[s]),
            .near_rq(near_rq[s]),.near_wq(near_wq[s]),.near_rr(nrr),.near_w_done(ndone),
            .local_rr(local_rr[s]),.far_rr(far_rr[s]),.local_w_done(local_done[s]),.far_w_done(far_done[s]),.bank_fault(bank_fault));
    end
    function automatic [255:0] payload(input integer station_id,row,bank_id);
        for(integer w=0;w<8;w=w+1)payload[w*32+:32]=32'h9e3779b9^32'(station_id<<28)^32'(row<<10)^32'(bank_id<<5)^32'(w);
    endfunction
    reg [7:0] exp_done[0:2][0:4095],exp_valid[0:2][0:4095];
    reg [2047:0] exp_data[0:2][0:4095];
    integer cycle=0,writes=0,reads=0;
    reg allow_fault=0,check_data=1;
    task clear_inputs;
        begin for(integer s=0;s<3;s=s+1)begin local_rq[s]=0;local_wq[s]=0;end end
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
        $readmemh("NE_812.hex",image);
        for(integer pc=0;pc<812;pc++)begin cfg_we=1;cfg_addr=10'(pc);cfg_data=image[pc];tick();end
        cfg_we=0;repeat(3)tick();start_v=1;tick();start_v=0;
        while(!cal_v)tick();
        // Fill 128 distinct rows per producer/bank, one eight-bank wave each
        // source per three cycles, all three issue together. Forward delays
        // (2/4/6edges to VM sample) pack arrival phases2/1/0 mod3:
        // eight sectors every VM cycle after initial pipeline fill.
        for(integer t=0;t<384;t=t+1)begin
            clear_inputs();
            if(t%3==0)for(owner=0;owner<3;owner=owner+1)begin
                row=t/3;

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
                row=t/3;
                for(integer b=0;b<8;b=b+1)local_rq[owner][b*17+:17]={1'b1,1'b0,2'd1,10'(owner*256+row),3'(b)};
            end
            tick();
        end
        clear_inputs();repeat(24)tick();
        if(writes!=3072||reads!=3072)$fatal(1,"missing production traffic writes=%0d reads=%0d",writes,reads);
        if(cal_fault)$fatal(1,"actual programme calendar fault");
        $display("VM_LG_PROGRAMMED PASS actualNEprogrammeSRAM812words24leaves24SRAM3072writes3072reads same10/14/18and7/11/15");
        $finish;
    end
endmodule
`default_nettype wire
