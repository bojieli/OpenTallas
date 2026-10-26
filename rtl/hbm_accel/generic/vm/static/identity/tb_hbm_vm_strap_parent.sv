`timescale 1ns/1ps
`default_nettype none
// Native group-count successors: RG7/WG3(NW/NE), RG5/WG1(SW/SE).
// Real eight-bank SRAM vehicle; no bank or response substitute.
module tb_hbm_vm_strap_parent;
    parameter integer SID=0,RG=5,WG=1;
    parameter integer MUT=0; //1: wrong response-group wiring at actual bank output
    localparam RB=$clog2(RG+1),WB=$clog2(WG+5);
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;
    reg [8*RG*17-1:0] rq=0;
    reg [8*281-1:0] dq=0;
    reg [7:0] rslot_v=0,wslot_v=0;
    reg [8*RB-1:0] rslot=0;
    reg [8*WB-1:0] wslot=0;
    reg [8*285-1:0] pq=0;
    wire [8*RG*257-1:0] actual_rr,rr;
    wire [8*266-1:0] pr;
    wire [7:0] dq_done;
    wire [143:0] status;
    wire [8*RG*17-1:0] parent_rq;
    wire [8*RG*257-1:0] parent_rr;
    for(genvar b=0;b<8;b=b+1)begin:transpose
      for(genvar g=0;g<RG;g=g+1)begin:group_wire
        assign parent_rq[(g*8+b)*17+:17]=rq[(b*RG+g)*17+:17];
        assign actual_rr[(b*RG+g)*257+:257]=parent_rr[(g*8+b)*257+:257];
      end
    end
    assign rr=actual_rr;
    assign pr=0; // packet path is outside this DMA/wide-group integration gate
    generate
    if(SID==0)begin:quadrant_SW
      hfd_hgi_vms_static_SW #(.STRAP_BANKS(1),.STRAP_MUT(MUT)) u_die_master (
       .clk_bank({8{clk}}),
       .clk_hub(clk),
       .clk_ring({2{clk}}),
       .clk_replay(clk),
       .rst_n(rst_n),
       .client_seq(8'd0),
       .response_enable(4'd0),
       .response_seq(8'd0),
       .bank_enable(8'd0),
       .bank_client(16'd0),
       .hub_ring_enable(2'd0),
       .hub_ring_client(4'd0),
       .rslot_v(rslot_v),
       .wslot_v(wslot_v),
       .rslot(rslot),
       .wslot(wslot),
       .rq(parent_rq),
       .rr(parent_rr),
       .wq((WG*8*281)'(0)),
       .wq_done(),
       .dq(dq),
       .kq(2248'd0),
       .dq_done(dq_done),
       .kq_done(),
       .cw_in(2224'd0),
       .ccw_in(2224'd0),
       .cw_out(),
       .ccw_out(),
       .ring_tx_enable(2'd0),
       .ring_tx_source(6'd0),
       .replay_enable(1'b0),
       .replay_source(1'b0),
       .bank_status(status),
       .hub_status(),
       .mirror_busy(),
       .vmstat(),
       .ring_fault(),
       .cq(1014'd0),
       .cr());
    end
    if(SID==1)begin:quadrant_SE
      hfd_hgi_vms_static_SE #(.STRAP_BANKS(1),.STRAP_MUT(MUT)) u_die_master (
       .clk_bank({8{clk}}),
       .clk_hub(clk),
       .clk_ring({2{clk}}),
       .clk_replay(clk),
       .rst_n(rst_n),
       .client_seq(2'd0),
       .response_enable(1'd0),
       .response_seq(2'd0),
       .bank_enable(8'd0),
       .bank_client(8'd0),
       .hub_ring_enable(2'd0),
       .hub_ring_client(2'd0),
       .rslot_v(rslot_v),
       .wslot_v(wslot_v),
       .rslot(rslot),
       .wslot(wslot),
       .rq(parent_rq),
       .rr(parent_rr),
       .wq((WG*8*281)'(0)),
       .wq_done(),
       .dq(dq),
       .kq(2248'd0),
       .dq_done(dq_done),
       .kq_done(),
       .cw_in(2224'd0),
       .ccw_in(2224'd0),
       .cw_out(),
       .ccw_out(),
       .ring_tx_enable(2'd0),
       .ring_tx_source(6'd0),
       .replay_enable(1'b0),
       .replay_source(1'b0),
       .bank_status(status),
       .hub_status(),
       .mirror_busy(),
       .vmstat(),
       .ring_fault());
    end
    if(SID==2)begin:quadrant_NW
      hfd_hgi_vms_static_NW #(.STRAP_BANKS(1),.STRAP_MUT(MUT)) u_die_master (
       .clk_bank({8{clk}}),
       .clk_hub(clk),
       .clk_ring({2{clk}}),
       .clk_replay(clk),
       .rst_n(rst_n),
       .client_seq(10'd0),
       .response_enable(5'd0),
       .response_seq(10'd0),
       .bank_enable(8'd0),
       .bank_client(24'd0),
       .hub_ring_enable(2'd0),
       .hub_ring_client(6'd0),
       .rslot_v(rslot_v),
       .wslot_v(wslot_v),
       .rslot(rslot),
       .wslot(wslot),
       .rq(parent_rq),
       .rr(parent_rr),
       .wq((WG*8*281)'(0)),
       .wq_done(),
       .dq(dq),
       .kq(2248'd0),
       .dq_done(dq_done),
       .kq_done(),
       .cw_in(2224'd0),
       .ccw_in(2224'd0),
       .cw_out(),
       .ccw_out(),
       .ring_tx_enable(2'd0),
       .ring_tx_source(6'd0),
       .replay_enable(1'b0),
       .replay_source(1'b0),
       .bank_status(status),
       .hub_status(),
       .mirror_busy(),
       .vmstat(),
       .ring_fault(),
       .cq(1352'd0),
       .cr());
    end
    if(SID==3)begin:quadrant_NE
      hfd_hgi_vms_static_NE #(.STRAP_BANKS(1),.STRAP_MUT(MUT)) u_die_master (
       .clk_bank({8{clk}}),
       .clk_hub(clk),
       .clk_ring({2{clk}}),
       .clk_replay(clk),
       .rst_n(rst_n),
       .client_seq(2'd0),
       .response_enable(1'd0),
       .response_seq(2'd0),
       .bank_enable(8'd0),
       .bank_client(8'd0),
       .hub_ring_enable(2'd0),
       .hub_ring_client(2'd0),
       .rslot_v(rslot_v),
       .wslot_v(wslot_v),
       .rslot(rslot),
       .wslot(wslot),
       .rq(parent_rq),
       .rr(parent_rr),
       .wq((WG*8*281)'(0)),
       .wq_done(),
       .dq(dq),
       .kq(2248'd0),
       .dq_done(dq_done),
       .kq_done(),
       .cw_in(2224'd0),
       .ccw_in(2224'd0),
       .cw_out(),
       .ccw_out(),
       .ring_tx_enable(2'd0),
       .ring_tx_source(6'd0),
       .replay_enable(1'b0),
       .replay_source(1'b0),
       .bank_status(status),
       .hub_status(),
       .mirror_busy(),
       .vmstat(),
       .ring_fault());
    end
    endgenerate
    function automatic [255:0] payload(input integer b,row);
        for(integer w=0;w<8;w=w+1)payload[w*32+:32]=32'hbeaf1280^32'(b<<24)^32'(row<<9)^32'(w*31);
    endfunction
    reg [7:0] exp_done[0:4095],exp_pr_v[0:4095];
    reg [8*RG-1:0] exp_rr_v[0:4095];
    reg [2047:0] exp_data[0:4095];
    reg [63:0] exp_pr_tag[0:4095];
    integer cycle=0,writes=0,reads=0,packet_reads=0;
    integer group_reads[0:RG-1];
    reg fault_expected=0;
    task clear_inputs;
        begin rq=0;dq=0;rslot_v=0;wslot_v=0;rslot=0;wslot=0;pq=0;end
    endtask
    task tick;
        integer group_id,row;
        begin
            @(posedge clk);
            if(rst_n)for(integer b=0;b<8;b=b+1)begin
                if(dq[b*281+280])exp_done[cycle+3][b]=1;
                if(rslot_v[b])begin
                    group_id=int'(rslot[b*RB+:RB]);
                    if(group_id<RG&&rq[(b*RG+group_id)*17+16])begin
                        row=int'(rq[(b*RG+group_id)*17+3+:10]);
                        exp_rr_v[cycle+6][b*RG+group_id]=1;
                        exp_data[cycle+6][b*256+:256]=payload(b,row);
                    end else if(group_id==RG&&pq[b*285+284])begin
                        row=int'(pq[b*285+272+:10]);exp_pr_v[cycle+6][b]=1;
                        exp_data[cycle+6][b*256+:256]=payload(b,row);
                        exp_pr_tag[cycle+6][b*8+:8]=pq[b*285+:8];
                    end
                end
            end
            #2;
            if(rst_n)begin
                if(!fault_expected&&status!==0)$fatal(1,"bank fault RG=%0d cycle=%0d status=%h",RG,cycle,status);
                if(dq_done!==exp_done[cycle])$fatal(1,"DMA commit phase RG=%0d cycle=%0d",RG,cycle);
                for(integer b=0;b<8;b=b+1)begin
                    if(dq_done[b])writes=writes+1;
                    for(integer g=0;g<RG;g=g+1)begin
                        if(rr[(b*RG+g)*257+256]!==exp_rr_v[cycle][b*RG+g])
                            $fatal(1,"actual bank response group mismatch RG=%0d cycle=%0d bank=%0d group=%0d",RG,cycle,b,g);
                        if(exp_rr_v[cycle][b*RG+g])begin
                            if(rr[(b*RG+g)*257+:256]!==exp_data[cycle][b*256+:256])$fatal(1,"actual SRAM readback mismatch");
                            reads=reads+1;group_reads[g]=group_reads[g]+1;
                        end
                    end
                    if(pr[b*266+265]!==exp_pr_v[cycle][b])$fatal(1,"packet phase mismatch");
                    if(exp_pr_v[cycle][b])begin
                        if(pr[b*266+:266]!=={1'b1,1'b0,exp_pr_tag[cycle][b*8+:8],exp_data[cycle][b*256+:256]})$fatal(1,"packet memory/tag mismatch");
                        packet_reads=packet_reads+1;
                    end
                end
            end
            cycle=cycle+1;@(negedge clk);
        end
    endtask
    initial begin
        integer row,group_id;
        for(integer c=0;c<4096;c=c+1)begin exp_done[c]=0;exp_pr_v[c]=0;exp_rr_v[c]=0;exp_data[c]=0;exp_pr_tag[c]=0;end
        for(integer g=0;g<RG;g=g+1)group_reads[g]=0;
        repeat(3)tick();rst_n=1;repeat(3) @(negedge clk); /* ot_rst_relay release: initialization mode, 3 edges */
        // Actual DMA port fills128rows inall8banks at8sectors/cycle.
        for(row=0;row<128;row=row+1)begin
            clear_inputs();wslot_v=8'hff;
            for(integer b=0;b<8;b=b+1)begin
                wslot[b*WB+:WB]=WB'(WG+4);
                dq[b*281+:281]={1'b1,1'b0,2'(SID),10'(row),3'(b),payload(b,row),8'hff};
            end
            tick();
        end
        clear_inputs();repeat(8)tick();
        // Every wide group reads every row in every bank. Group selection
        // varies every cycle and independently by bank; unselected outputs
        // must stay invalid. Includes addedCOLL5/IDX6 onRG7.
        for(integer t=0;t<RG*128;t=t+1)begin
            clear_inputs();rslot_v=8'hff;
            for(integer b=0;b<8;b=b+1)begin
                group_id=(t+b)%RG;row=(t/RG+b*3)%128;
                rslot[b*RB+:RB]=RB'(group_id);
                rq[(b*RG+group_id)*17+:17]={1'b1,1'b0,2'(SID),10'(row),3'(b)};
            end
            tick();
        end
        clear_inputs();repeat(9)tick();
        if(writes!=1024||reads!=RG*1024)$fatal(1,"missing allgroup inventory");
        for(integer g=0;g<RG;g=g+1)if(group_reads[g]!=1024)$fatal(1,"group throughput mismatch group=%0d count=%0d",g,group_reads[g]);
        // Deliberately activate two groups but reserveonlygroup0. Thebank
        // must execute exactlygroup0, raiseFAULT, andneverdefergroup1.
        fault_expected=1;rslot_v=8'hff;
        for(integer b=0;b<8;b=b+1)begin
            rslot[b*RB+:RB]=0;
            rq[(b*RG+0)*17+:17]={1'b1,1'b0,2'(SID),10'd7,3'(b)};
            rq[(b*RG+1)*17+:17]={1'b1,1'b0,2'(SID),10'd33,3'(b)};
        end
        tick();clear_inputs();repeat(12)tick();
        for(integer b=0;b<8;b=b+1)if(status[b*18+17]!==1)$fatal(1,"unselected secondgroup didnotfault");
        $display("VM_STRAP_PARENT PASS RG=%0d WG=%0d banks=8 SRAMs=24 DMAwrites=1024 exactwide_reads=%0d eachgroup_reads=1024 packet_reads=0 (outside gate) sectors_per_cycle=8 return_edges=6 conflict_fault_no_arbitration=1",RG,WG,RG*1024);
        $finish;
    end
endmodule
`default_nettype wire
