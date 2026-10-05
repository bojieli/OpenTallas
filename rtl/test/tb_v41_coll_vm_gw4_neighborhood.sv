`timescale 1ns/1ps
// Exact gate for ot_v41_coll_vm_gw4_neighborhood: index-major four-rank
// gathers land rank-major in the four-bank macro VM through the static-bank
// transpose lanes, then every written word is read back through the VM read
// service (4-word beats, physical-bank order + rotation) and compared.
// Two back-to-back descriptors (5 words, then NW words) with input stalls.
module tb_v41_coll_vm_gw4_neighborhood #(parameter integer NW=266, parameter integer G=1,
                                         parameter integer DST0=3, parameter integer DST1=40);
    localparam integer WA=15, FW=512;
    reg clk=0, rst_n=0;
    always #5 clk=~clk;
    reg start=0, in_valid=0, in_last=0, rd_v=0;
    reg [WA-1:0] dst=0, n=0, rd_base_word=0;
    reg [2047:0] in_data=0;
    wire in_ready, coll_done, coll_fault, rd_out_v, rd_fault, wr_fault, rw_collision_fault;
    wire [1:0] rd_out_rot;
    wire [2047:0] rd_out_bank_words;
    integer cyc=0, done_cnt=0, errors=0, reads_checked=0;
    ot_v41_coll_vm_gw4_neighborhood #(.DEPTH_GROUPS(G), .WA(WA)) dut (.*);
    always @(posedge clk) begin
        cyc <= cyc+1;
        if (coll_done) done_cnt <= done_cnt+1;
        if (rst_n && (coll_fault || wr_fault || rd_fault || rw_collision_fault))
            $fatal(1, "fault coll=%0d wr=%0d rd=%0d rw=%0d at cyc %0d", coll_fault, wr_fault, rd_fault, rw_collision_fault, cyc);
    end
    function automatic [FW-1:0] payload(input integer desc, input integer rank, input integer idx);
        reg [FW-1:0] p;
        begin
            for (integer k=0;k<FW/32;k=k+1) p[32*k+:32]=(32'(desc)<<28)^(32'(rank)<<24)^(32'(idx)<<8)^32'(k*977);
            return p;
        end
    endfunction
    // expected VM image
    reg [FW-1:0] img [0:4*G*512-1];
    reg          imgv[0:4*G*512-1];
    task automatic gather(input integer desc, input integer d, input integer words);
        integer i; reg acc;
        begin
            @(negedge clk); start=1; dst=d; n=words; @(negedge clk); start=0;
            i=0;
            while (i<words) begin
                in_valid = ($urandom%5)!=0;
                in_last = (i==words-1);
                for (integer r=0;r<4;r=r+1) in_data[r*FW+:FW]=payload(desc,r,i);
                #2; acc = in_valid && in_ready;   // sampled before the capturing edge
                @(posedge clk);
                if (acc) begin
                    for (integer r=0;r<4;r=r+1) begin img[d+r*words+i]=payload(desc,r,i); imgv[d+r*words+i]=1; end
                    i=i+1;
                end
                if (cyc > 20000) $fatal(1,"gather stalled desc %0d at word %0d", desc, i);
                @(negedge clk);
            end
            in_valid=0; in_last=0;
            begin : wait_done
                integer t; t=0;
                while (done_cnt<desc+1) begin @(posedge clk); t=t+1; if (t>1000) $fatal(1,"no done desc %0d",desc); end
            end
            repeat (6) @(posedge clk); // write commit edges
        end
    endtask
    // read-back: issue a beat per cycle, check with fixed 5-edge fill
    integer q_base [0:4095]; integer q_head=0, q_tail=0;
    always @(negedge clk) if (rd_out_v) begin : chk
        integer base, delta, a;
        base=q_base[q_head]; q_head=q_head+1;
        if (rd_out_rot !== base[1:0]) begin errors=errors+1; $display("rot mismatch base %0d", base); end
        for (integer b=0;b<4;b=b+1) begin
            delta=(b-(base&3)+4)&3; a=base+delta;
            if (imgv[a] && rd_out_bank_words[b*FW+:FW] !== img[a]) begin
                errors=errors+1; if (errors<10) $display("word %0d mismatch bank %0d got %h exp %h", a, b, rd_out_bank_words[b*FW+:32], img[a][31:0]);
            end
            if (imgv[a]) reads_checked=reads_checked+1;
        end
    end
    integer lat_issue, lat_seen;
    initial begin
        for (integer a=0;a<4*G*512;a=a+1) imgv[a]=0;
        repeat(3) @(posedge clk); rst_n=1; repeat(2) @(posedge clk);
        gather(0, DST0, 5);
        gather(1, DST1, NW);
        // read back everything from DST0 up to the last written word, 4 words per beat, one beat/cycle
        for (integer base=DST0; base<DST1+4*NW; base=base+4) begin
            @(negedge clk); rd_v=1; rd_base_word=base; q_base[q_tail]=base; q_tail=q_tail+1;
        end
        @(negedge clk); rd_v=0;
        repeat (12) @(posedge clk);
        if (q_head!=q_tail) $fatal(1,"missing read beats %0d/%0d", q_head, q_tail);
        if (errors) $fatal(1,"%0d mismatches", errors);
        if (reads_checked != 4*5+4*NW) $fatal(1,"checked %0d words, expected %0d", reads_checked, 4*5+4*NW);
        $display("PASS coll->VM GW4 neighborhood G=%0d NW=%0d words=%0d beats=%0d cycles=%0d", G, NW, reads_checked, q_tail, cyc);
        $finish;
    end
endmodule
