`timescale 1ns/1ps
module tb_chip_v41x_attn_row_merge;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0, start_v=0;
    wire start_ready;
    reg [9:0] start_user=0;
    reg [20:0] window_start_pos=0;
    reg [7:0] window_count=0;
    reg [9:0] selected_count=0;
    reg [20:0] published_source_count=21'd100;
    wire win_need;
    wire [9:0] win_user;
    wire [20:0] win_rrow;
    reg win_packed_valid=0;
    reg [4223:0] win_packed_row=0;
    reg win_fault=0;
    wire wb_req_v;
    reg wb_req_ready=0;
    wire [9:0] wb_req_user;
    wire [20:0] wb_req_first;
    wire [3:0] wb_req_m;
    reg wb_rsp_v=0;
    reg [9:0] wb_rsp_user=0;
    reg [20:0] wb_rsp_first=0;
    reg [3:0] wb_rsp_m=0, wb_rsp_lane_valid=0;
    reg [4*4224-1:0] wb_rsp_rows=0;
    reg wb_rsp_fault=0;
    reg selected_id_valid=0;
    wire selected_id_ready;
    reg [20:0] selected_source_id=0;
    wire ckv_fetch_v;
    reg ckv_fetch_ready=1;
    wire [9:0] ckv_fetch_local_row;
    wire [20:0] ckv_fetch_source_id;
    reg ckv_packed_valid=0;
    reg [2303:0] ckv_packed_row=0;
    reg [9:0] ckv_packed_local_row=0;
    reg [20:0] ckv_packed_source_id=0;
    reg ckv_fault=0;
    reg ckv_remote_needed=0;
    reg [1:0] ckv_remote_die=0;
    wire remote_req_v;
    reg remote_req_ready=1;
    wire [1:0] remote_req_die;
    wire [9:0] remote_req_local_row;
    wire [20:0] remote_req_source_id;
    reg remote_rsp_v=0;
    reg [1:0] remote_rsp_die=0;
    reg [9:0] remote_rsp_local_row=0;
    reg [20:0] remote_rsp_source_id=0;
    reg [2303:0] remote_rsp_row=0;
    reg remote_fault=0;
    wire kv_v;
    reg kv_ready=1;
    wire [3:0] kv_m;
    wire [4*16*265-1:0] kv_w;
    wire done, fault;
    integer job=0, beats=0, checked=0;
    reg [9:0] expected_user=0;
    ot_chip_v41x_attn_row_merge dut (.*);

    function automatic [4223:0] window_row(input integer row);
        reg [4223:0] x;
        integer g,b;
        begin
            x=0;
            for (g=0;g<16;g=g+1) begin
                for (b=0;b<32;b=b+1) x[256*g+8*b +: 8]=8'(row*13+g*7+b);
                x[4096+8*g +: 8]=8'(127+row+g);
            end
            return x;
        end
    endfunction
    function automatic [2303:0] compressed_row(input integer row);
        reg [2303:0] x;
        integer g,b;
        begin
            x=0;
            for (g=0;g<16;g=g+1) begin
                for (b=0;b<16;b=b+1) x[128*g+8*b +: 8]=8'(row*11+g*5+b);
                x[2048+16*g +: 8]=8'(90+row+g);
                x[2056+16*g +: 8]=8'(91+row+g);
            end
            return x;
        end
    endfunction
    function automatic [4239:0] expected_row(input integer row, input integer wcount);
        reg [4239:0] x;
        reg [4223:0] w;
        reg [2303:0] c;
        integer g;
        begin
            x=0;
            if (row < wcount) begin
                w=window_row(row);
                for (g=0;g<16;g=g+1)
                    x[265*g +: 265]={1'b0,w[4096+8*g +: 8],w[256*g +: 256]};
            end else begin
                c=compressed_row(row);
                for (g=0;g<16;g=g+1)
                    x[265*g +: 265]={1'b1,120'b0,c[2048+16*g +: 16],c[128*g +: 128]};
            end
            return x;
        end
    endfunction
    always @(posedge clk) if (rst_n && kv_v && kv_ready) begin
        integer n, r, w;
        reg [3:0] mask;
        n=(job==1) ? 8 : (job==5 ? 4 : 2);
        w=(job==1) ? 3 : (job==5 ? 4 : 1);
        mask=(job==2) ? 4'h3 : 4'hf;
        if (kv_m !== mask) $fatal(1,"mask job=%0d beat=%0d got=%h",job,beats,kv_m);
        for (integer l=0;l<4;l=l+1) begin
            r=beats*4+l;
            if (r<n) begin
                if (kv_w[l*4240 +: 4240] !== expected_row(r,w))
                    $fatal(1,"row job=%0d beat=%0d lane=%0d row=%0d",job,beats,l,r);
                checked=checked+1;
            end else if (kv_w[l*4240 +: 4240] !== 0)
                $fatal(1,"unmasked lane not zero");
        end
        beats=beats+1;
    end
    task automatic start_job(input integer base, input integer w, input integer s);
        @(negedge clk); window_start_pos=21'(base); window_count=8'(w);
        selected_count=10'(s); expected_user=start_user; start_v=1;
        @(negedge clk); start_v=0; start_user=start_user+1'b1;
    endtask
    task automatic send_window(input integer row);
        wait(win_need);
        @(negedge clk);
        if (!win_need || win_rrow !== window_start_pos+21'(row) || win_user !== expected_user)
            $fatal(1,"window request order/user");
        win_packed_row=window_row(row); win_packed_valid=1;
        @(negedge clk); win_packed_valid=0;
    endtask
    task automatic send_selected(input integer row, input integer source, input bit remote);
        wait(selected_id_ready);
        @(negedge clk); selected_source_id=21'(source); selected_id_valid=1;
        if (ckv_fetch_local_row !== 10'(row) || ckv_fetch_source_id !== 21'(source))
            $fatal(1,"CKV fetch tag");
        @(negedge clk); selected_id_valid=0;
        if (remote) begin
            ckv_remote_die=2'(source >> 4); ckv_remote_needed=1;
            @(negedge clk); ckv_remote_needed=0;
            wait(remote_req_v);
            if (remote_req_die !== 2'(source >> 4) || remote_req_local_row !== 10'(row) ||
                remote_req_source_id !== 21'(source)) $fatal(1,"remote request tag");
            @(negedge clk); remote_rsp_die=2'(source >> 4);
            remote_rsp_local_row=10'(row); remote_rsp_source_id=21'(source);
            remote_rsp_row=compressed_row(row); remote_rsp_v=1;
            @(negedge clk); remote_rsp_v=0;
        end else begin
            ckv_packed_local_row=10'(row); ckv_packed_source_id=21'(source);
            ckv_packed_row=compressed_row(row); ckv_packed_valid=1;
            @(negedge clk); ckv_packed_valid=0;
        end
    endtask
    initial begin
        #100000 $fatal(1,"timeout");
    end
    initial begin
        repeat(3) @(negedge clk); rst_n=1;
        job=1; beats=0; kv_ready=0; start_user=10'd7;
        start_job(100,3,5);
        for (integer r=0;r<3;r=r+1) send_window(r);
        send_selected(3,0,0);
        wait(kv_v);
        repeat(3) begin
            @(negedge clk);
            if (!kv_v || kv_m !== 4'hf || kv_w[0 +: 4240] !== expected_row(0,3))
                $fatal(1,"backpressured beat changed");
        end
        kv_ready=1;
        send_selected(4,1,0);
        send_selected(5,16,1);
        send_selected(6,2,0);
        send_selected(7,3,0);
        wait(done); if (beats!=2 || fault) $fatal(1,"first job");
        @(negedge clk); job=2; beats=0; start_user=10'd9;
        start_job(500,1,1);
        wait(wb_req_v);
        @(negedge clk);
        if (wb_req_user !== expected_user || wb_req_first !== 21'd500 || wb_req_m !== 4'h1)
            $fatal(1,"bank scalar request tag/mask");
        wb_req_ready=1;
        @(negedge clk); wb_req_ready=0;
        wb_rsp_user=expected_user; wb_rsp_first=21'd500;
        wb_rsp_m=4'h1; wb_rsp_lane_valid=4'h1;
        wb_rsp_rows[0 +: 4224]=window_row(0); wb_rsp_v=1;
        @(negedge clk); wb_rsp_v=0;
        send_selected(1,4,0);
        wait(done); if (beats!=1 || fault) $fatal(1,"partial job");
        @(negedge clk); job=5; beats=0; start_user=10'd11;
        start_job(700,4,0);
        wait(wb_req_v);
        @(negedge clk);
        if (wb_req_user !== expected_user || wb_req_first !== 21'd700 || wb_req_m !== 4'hf)
            $fatal(1,"bank request tag/mask");
        wb_req_ready=1;
        @(negedge clk); wb_req_ready=0;
        wb_rsp_user=expected_user; wb_rsp_first=21'd700;
        wb_rsp_m=4'hf; wb_rsp_lane_valid=4'hf;
        for (integer l=0;l<4;l=l+1) wb_rsp_rows[l*4224 +: 4224]=window_row(l);
        wb_rsp_v=1;
        @(negedge clk); wb_rsp_v=0;
        wait(done); if (beats!=1 || fault) $fatal(1,"four-bank job");
        @(negedge clk); job=6; beats=0; start_user=10'd13;
        start_job(900,4,0);
        wait(wb_req_v);
        @(negedge clk); wb_req_ready=1;
        @(negedge clk); wb_req_ready=0;
        wb_rsp_user=expected_user+1'b1; wb_rsp_first=21'd900;
        wb_rsp_m=4'hf; wb_rsp_lane_valid=4'hf; wb_rsp_v=1;
        @(negedge clk); wb_rsp_v=0;
        if (!fault || kv_v) $fatal(1,"bad bank response user did not fail closed");
        @(negedge clk); rst_n=0;
        repeat(2) @(negedge clk); rst_n=1;
        @(negedge clk); job=3; beats=0;
        start_job(0,0,1);
        wait(selected_id_ready);
        @(negedge clk); selected_source_id=21'd6; selected_id_valid=1;
        @(negedge clk); selected_id_valid=0;
        ckv_packed_valid=1; ckv_packed_local_row=0; ckv_packed_source_id=21'd7;
        @(negedge clk); ckv_packed_valid=0;
        if (!fault || kv_v) $fatal(1,"bad source tag did not fail closed");
        @(negedge clk); rst_n=0; selected_id_valid=0;
        repeat(2) @(negedge clk); rst_n=1; published_source_count=21'd5;
        job=4; beats=0;
        start_job(0,0,1);
        wait(selected_id_ready);
        @(negedge clk); selected_source_id=21'd6; selected_id_valid=1;
        if (ckv_fetch_v) $fatal(1,"out-of-range source was fetched");
        @(negedge clk); selected_id_valid=0;
        if (!fault || kv_v) $fatal(1,"out-of-range source did not fail closed");
        if (checked!=14) $fatal(1,"checked %0d rows expected 14",checked);
        $display("V41X_PACKED_MERGE PASS checked=%0d full_beats=3 partial_beats=1 remote=1 tag_fault=1 range_fault=1 batch=1 batch_tag_fault=1 batch_scalar=1",checked);
        $finish;
    end
endmodule
