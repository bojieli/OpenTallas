`timescale 1ns/1ps
// One NPC32/full128 configuration: actual FF WINDOW stage -> new merge,
// compared cycle-for-cycle with the unchanged merge and released payload.
module tb_window_stage_merge_decode;
    localparam integer NPC=32, NSECT=2176, ROWB=4224, PACK=4240;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, job_v=0, start_v=0;
    reg [9:0] job_user=66;
    reg [20:0] job_first=97;
    reg [7:0] job_count=128;
    reg [31:0] in_v=0;
    reg [415:0] in_tag=0;
    reg [127:0] in_beat=0;
    reg [8191:0] in_data=0;
    wire [31:0] in_rdy, acc_v;
    wire [415:0] acc_tag;
    wire [127:0] acc_beat;
    wire [8191:0] acc_data;
    wire all_rows, stage_fault;
    wire [11:0] sectors_landed;
    wire wb_req_v, stage_ready, wb_rsp_v, wb_rsp_fault;
    wire [9:0] wb_req_user, wb_rsp_user;
    wire [20:0] wb_req_first, wb_rsp_first;
    wire [3:0] wb_req_m, wb_rsp_m, wb_rsp_lane_valid;
    wire [16895:0] wb_rsp_rows;
    reg kv_ready=0, allow_request=0;
    reg inject_address=0, expected_fault=0, response_bad_user=0;
    wire wb_req_ready=stage_ready && allow_request;
    wire stage_req_v=wb_req_v && wb_req_ready;
    ot_dsrom_window_stage_pipeline #(.NPC(NPC)) stage (
        .clk(clk),.rst_n(rst_n),.job_v(job_v),.job_user(job_user),
        .job_first(job_first),.job_count(job_count),.all_rows(all_rows),
        .sectors_landed(sectors_landed),.fault(stage_fault),
        .in_v(in_v),.in_rdy(in_rdy),.in_tag(in_tag),.in_beat(in_beat),.in_data(in_data),
        .acc_v(acc_v),.acc_tag(acc_tag),.acc_beat(acc_beat),.acc_data(acc_data),
        .req_v(stage_req_v),.req_ready(stage_ready),.req_user(wb_req_user),
        .req_first_row(wb_req_first),.req_mask(wb_req_m),.rsp_v(wb_rsp_v),
        .rsp_user(wb_rsp_user),.rsp_first_row(wb_rsp_first),.rsp_mask(wb_rsp_m),
        .rsp_valid_mask(wb_rsp_lane_valid),.rsp_rows(wb_rsp_rows),.rsp_fault(wb_rsp_fault));

    wire start_ready, kv_v, done, fault;
    wire [3:0] kv_m;
    wire [16959:0] kv_w;
    wire ref_start_ready, ref_kv_v, ref_done, ref_fault, ref_req_v;
    wire [9:0] ref_req_user;
    wire [20:0] ref_req_first;
    wire [3:0] ref_req_m, ref_kv_m;
    wire [16959:0] ref_kv_w;
    // Invalid response fields are deliberately undriven/X. Source-original
    // valid/fault priority must prevent an invalid payload from publishing.
    wire [9:0] rsp_user_checked=wb_rsp_v ? wb_rsp_user ^ (response_bad_user?10'd1:10'd0) : 10'bx;
    wire [20:0] rsp_first_checked=wb_rsp_v ? wb_rsp_first : 21'bx;
    wire [3:0] rsp_mask_checked=wb_rsp_v ? wb_rsp_m : 4'bx;
    wire [3:0] rsp_lanes_checked=wb_rsp_v ? wb_rsp_lane_valid : 4'bx;
    wire [16895:0] rsp_rows_checked=wb_rsp_v ? wb_rsp_rows : {16896{1'bx}};
    wire rsp_fault_checked=wb_rsp_v ? wb_rsp_fault : 1'bx;

`define MERGE_INPUTS \
        .clk(clk),.rst_n(rst_n),.start_v(start_v),.start_user(job_user), \
        .window_start_pos(job_first),.window_count(job_count),.selected_count(10'd0), \
        .published_source_count(21'd0),.win_need(),.win_user(),.win_rrow(), \
        .win_packed_valid(1'b0),.win_packed_row({4224{1'bx}}),.win_fault(1'b0), \
        .wb_req_ready(wb_req_ready),.wb_rsp_v(wb_rsp_v),.wb_rsp_user(rsp_user_checked), \
        .wb_rsp_first(rsp_first_checked),.wb_rsp_m(rsp_mask_checked), \
        .wb_rsp_lane_valid(rsp_lanes_checked),.wb_rsp_rows(rsp_rows_checked), \
        .wb_rsp_fault(rsp_fault_checked),.selected_id_valid(1'b0),.selected_id_ready(), \
        .selected_source_id(21'bx),.ckv_fetch_v(),.ckv_fetch_ready(1'b0), \
        .ckv_fetch_local_row(),.ckv_fetch_source_id(),.ckv_packed_valid(1'b0), \
        .ckv_packed_row({2304{1'bx}}),.ckv_packed_local_row(10'bx), \
        .ckv_packed_source_id(21'bx),.ckv_fault(1'b0),.ckv_remote_needed(1'b0), \
        .ckv_remote_die(2'bx),.remote_req_v(),.remote_req_ready(1'b0), \
        .remote_req_die(),.remote_req_local_row(),.remote_req_source_id(), \
        .remote_rsp_v(1'b0),.remote_rsp_die(2'bx),.remote_rsp_local_row(10'bx), \
        .remote_rsp_source_id(21'bx),.remote_rsp_row({2304{1'bx}}),.remote_fault(1'b0), \
        .kv_ready(kv_ready)
    ot_dsrom_window_row_merge_pipeline dut (
        `MERGE_INPUTS,.start_ready(start_ready),.wb_req_v(wb_req_v),
        .wb_req_user(wb_req_user),.wb_req_first(wb_req_first),.wb_req_m(wb_req_m),
        .kv_v(kv_v),.kv_m(kv_m),.kv_w(kv_w),.done(done),.fault(fault));
    ot_chip_v41x_attn_row_merge reference_merge (
        `MERGE_INPUTS,.start_ready(ref_start_ready),.wb_req_v(ref_req_v),
        .wb_req_user(ref_req_user),.wb_req_first(ref_req_first),.wb_req_m(ref_req_m),
        .kv_v(ref_kv_v),.kv_m(ref_kv_m),.kv_w(ref_kv_w),.done(ref_done),.fault(ref_fault));
`undef MERGE_INPUTS

    reg [ROWB-1:0] golden[0:127];
    integer writes=0, checked_beats=0, checked_lanes=0, requests=0;
    integer stalls=0, cycles=0, faults_seen=0, resets_in_flight=0;
    integer seen_rows=0, absolute_row, sector, lane, group_id, port_id;
    reg [16959:0] expected_beat;
    reg held=0;
    reg [16959:0] held_data;
    reg [3:0] held_mask;
    string rows_path;

    function automatic [255:0] sector_data(input integer sec);
        integer row,col;
        begin
            row=sec/17; col=sec%17;
            if(col==16) sector_data={128'b0,golden[row][4096+:128]};
            else sector_data=golden[row][256*col+:256];
        end
    endfunction

    // Checks observe the acceptance edge before NBA, then compare all control
    // and visible payload after NBA. No second stimulus seed or gate replay.
    always @(posedge clk) begin
        if(!rst_n) begin writes=0; held=0; end
        else begin
            if(job_v) writes=0;
            else for(port_id=0;port_id<NPC;port_id=port_id+1) if(acc_v[port_id]) begin
                sector=4*acc_tag[port_id*13+:13]+acc_beat[port_id*4+:4];
                if(sector>=NSECT || acc_data[port_id*256+:256]!==sector_data(sector))
                    $fatal(1,"accepted landing identity/payload mismatch sector=%0d",sector);
                writes=writes+1;
            end
            if(wb_req_v && wb_req_ready) requests=requests+1;
            if(kv_v && !kv_ready) stalls=stalls+1;
            if(held && (kv_v!==1 || kv_m!==held_mask || kv_w!==held_data))
                $fatal(1,"held accepted beat changed");
            held=kv_v && !kv_ready;
            if(held) begin held_data=kv_w; held_mask=kv_m; end
            if(kv_v && kv_ready) begin
                if(expected_fault) $fatal(1,"invalid identity published a beat");
                expected_beat=0;
                for(lane=0;lane<4;lane=lane+1) if(kv_m[lane]) begin
                    absolute_row=(job_first+seen_rows)%128;
                    for(group_id=0;group_id<16;group_id=group_id+1)
                        expected_beat[(lane*16+group_id)*265+:265]=
                            {1'b0,golden[absolute_row][4096+8*group_id+:8],
                             golden[absolute_row][256*group_id+:256]};
                    seen_rows=seen_rows+1; checked_lanes=checked_lanes+1;
                end
                if(kv_w!==expected_beat) $fatal(1,"released packed golden mismatch rows=%0d",seen_rows);
                checked_beats=checked_beats+1;
            end
        end
        #1;
        if({start_ready,kv_v,kv_m,kv_w,done,fault} !==
           {ref_start_ready,ref_kv_v,ref_kv_m,ref_kv_w,ref_done,ref_fault})
            $fatal(1,"source-original merge cycle/identity/payload/fault mismatch");
        if(!inject_address && {wb_req_v,wb_req_user,wb_req_first,wb_req_m} !==
                             {ref_req_v,ref_req_user,ref_req_first,ref_req_m})
            $fatal(1,"registered request address changed source timing/value");
        if(stage_fault) $fatal(1,"unexpected stage landing fault");
    end
    always @(negedge clk) begin
        cycles=cycles+1;
        kv_ready=(cycles%5)!=0 && (cycles%5)!=1;
        allow_request=(cycles%7)!=0 && (cycles%7)!=1;
    end

    task automatic reset_all;
        begin
            @(negedge clk); rst_n=0; start_v=0; job_v=0; in_v=0;
            repeat(2) @(negedge clk);
            rst_n=1; inject_address=0; expected_fault=0; response_bad_user=0;
        end
    endtask
    task automatic fill_window(input integer count);
        integer cursor[0:NPC-1];
        integer p,tick;
        reg [31:0] takes;
        begin
            @(negedge clk); job_count=8'(count); job_v=1;
            @(negedge clk); job_v=0;
            for(p=0;p<NPC;p=p+1) cursor[p]=p;
            tick=0;
            while(writes<NSECT && tick<NSECT+NPC*9+128) begin
                @(negedge clk); in_v=0;
                for(p=0;p<NPC;p=p+1) if(cursor[p]<NSECT) begin
                    in_v[p]=1; in_tag[p*13+:13]=13'(cursor[p]/4);
                    in_beat[p*4+:4]=4'(cursor[p]%4);
                    in_data[p*256+:256]=sector_data(cursor[p]);
                end
                @(posedge clk); takes=in_v & in_rdy;
                #2;
                for(p=0;p<NPC;p=p+1) if(takes[p]) cursor[p]=cursor[p]+NPC;
                tick=tick+1;
            end
            @(negedge clk); in_v=0;
            if(writes!=NSECT || !all_rows) $fatal(1,"full NPC32/window fill failed");
        end
    endtask
    task automatic start_merge;
        begin
            @(negedge clk); seen_rows=0; start_v=1;
            @(negedge clk); start_v=0;
        end
    endtask
    task automatic finish_merge(input integer rows);
        integer tick;
        begin
            tick=0;
            while(!done && tick<128*16+32) begin @(negedge clk); tick=tick+1; end
            if(!done || fault || seen_rows!=rows) $fatal(1,"merge completion/rows failed");
            @(negedge clk);
        end
    endtask
    task automatic wait_fault;
        integer tick;
        begin
            tick=0;
            while(!fault && tick<32) begin @(negedge clk); tick=tick+1; end
            if(!fault || done || kv_v) $fatal(1,"identity protection failed to fault before publication");
            faults_seen=faults_seen+1;
        end
    endtask

    initial begin
        if(!$value$plusargs("rows=%s",rows_path)) $fatal(1,"released rows required");
        $readmemh(rows_path,golden);
        reset_all; fill_window(128); start_merge; finish_merge(128);
        fill_window(7); start_merge; finish_merge(7);
        // Cancel a pending accepted bank read asynchronously between edges.
        fill_window(128); start_merge;
        wait(stage_req_v); @(posedge clk); #2;
        rst_n=0; start_v=0; in_v=0; resets_in_flight=resets_in_flight+1;
        repeat(2) @(negedge clk); rst_n=1;
        // Independent expected identity must reject a corrupted lookahead.
        fill_window(128);
        @(negedge clk); inject_address=1; expected_fault=1;
        force dut.read_address_q[1]=1'b1; // job_first97 bit1=0; request becomes99, still in bounds.
        start_merge;
        wait(stage_req_v); @(posedge clk); #2;
        release dut.read_address_q[1];
        wait_fault;
        reset_all; fill_window(128);
        response_bad_user=1; expected_fault=1; start_merge; wait_fault;
        if(checked_beats!=34 || checked_lanes!=135 || stalls==0 ||
           requests<38 || faults_seen!=2 || resets_in_flight!=1)
            $fatal(1,"coverage absent beats=%0d lanes=%0d requests=%0d stalls=%0d faults=%0d reset=%0d",
                checked_beats,checked_lanes,requests,stalls,faults_seen,resets_in_flight);
        $display("PASS NPC32 full128 connected stage/merge golden beats=%0d lanes=%0d requests=%0d stalls=%0d identity_faults=%0d reset_inflight=%0d unchanged_cycles maskedX independent_expected",checked_beats,checked_lanes,requests,stalls,faults_seen,resets_in_flight);
        $finish;
    end
endmodule
