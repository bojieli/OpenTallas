`timescale 1ns/1ps
// Component regression for d3911f382 in the selected HA3=0 accelerator copy.
// Only instruction loading and real LSU responses drive the SM. X-memory
// observations are passive, compared with independently assembled fixture bits.
module tb_hbm_accel_sm_capture_lsu;
    reg clk=0, rst_n=0;
    always #0.4165 clk=~clk;
    reg im_we=0, launch_v=0;
    reg [12:0] im_addr=0;
    reg [63:0] im_data=0;
    wire done, fault, busy, req_v, req_we, rsp_rdy;
    wire [31:0] req_addr, req_strb;
    wire [255:0] req_data;
    wire [15:0] req_tag;
    reg req_rdy=0, rsp_v=0, rsp_we=0;
    reg [15:0] rsp_tag=0;
    reg [255:0] rsp_data=0;
`ifdef OT_CAPTURE_DS20
    ot_ds_hbm_simt_sm20 #(.ENABLE(1),.TW(17),.PW(20),.NL(128),.HAS_BD(1)) dut (
`else
    ot_hbm_accel_simt_sm #(.ENABLE(1),.HA3(0),.NL(128),.HAS_BD(1)) dut (
`endif
        .clk(clk),.rst_n(rst_n),.sm_id(8'd0),.die_id(8'd0),
        .im_we(im_we),.im_addr(im_addr),.im_data(im_data),
        .launch_v(launch_v),.launch_pc(32'd0),
`ifdef OT_CAPTURE_DS20
        .launch_token(17'h1ffff),.launch_pos(20'habcd0),
`else
        .launch_token(16'd0),.launch_pos(16'd0),
`endif
        .sm_done(done),.sm_fault(fault),.busy(busy),.res_v(),.res_data(),
        .bar_arrive(),.bar_release(1'b0),
        .lreq_v(req_v),.lreq_rdy(req_rdy),.lreq_we(req_we),.lreq_addr(req_addr),
        .lreq_wdata(req_data),.lreq_wstrb(req_strb),.lreq_tag(req_tag),
        .lrsp_v(rsp_v),.lrsp_rdy(rsp_rdy),.lrsp_we(rsp_we),.lrsp_tag(rsp_tag),.lrsp_data(rsp_data),
        .treq_v(),.treq_rdy(1'b0),.treq_addr(),.treq_tag(),
        .trsp_v(1'b0),.trsp_rdy(),.trsp_tag(16'd0),.trsp_data(256'd0),
        .coll_req_v(),.coll_req_rdy(1'b0),.coll_mode(),.coll_count(),.coll_data(),
        .coll_rsp_v(1'b0),.coll_rsp_rdy(),.coll_rsp_data(4096'd0),
`ifndef OT_CAPTURE_DS20
        .coll_x(),.coll_off(),.coll_nown(),.coll_fuse(),.coll_resid(),
        .coll_rsp_ss(32'd0),.coll_rsp_err(1'b0),
`endif
        .st_instr(),.st_cycles(),.st_stall_mem(),.st_tc_rows());

    function automatic [31:0] word(input integer r, input integer lane);
        // Codes differ at every block/lane; exponents include signed 10-bit values.
        if(r==2 || r==5) word=32'((lane*7+r*19)&1023);
        else word=32'((lane*13+r*41+1)&255);
    endfunction
    function automatic [63:0] ins(input [7:0] op,d,a,b,input [31:0] imm);
        ins={op,d,a,b,imm};
    endfunction
    reg [63:0] program_words[0:63];
    integer np=0;
    task automatic emit(input [63:0] w);
        program_words[np]=w; np++;
    endtask
    // Six 128-lane F32 loads/stores start four bytes into a sector. Each spans
    // 17 sectors, covering partial masks and response-tag to lane reconstruction.
    reg [7:0] memory_bytes[0:65535];
    reg stored[0:3071];
    reg q_valid[0:63], q_we[0:63];
    reg [15:0] q_tag[0:63];
    reg [255:0] q_data[0:63];
    integer q_due[0:63];
    integer cycle=0, reads=0, writes=0, acknowledgments=0;
    integer written_bytes=0;
    always @(posedge clk) begin : responder
        integer free_slot,pick,base,r,lane,byte_in_word;
        reg [255:0] payload;
        cycle<=cycle+1;
        if(!rst_n) begin
            req_rdy<=0; rsp_v<=0;
            for(integer s=0;s<64;s++) q_valid[s]<=0;
        end else begin
            free_slot=-1;
            for(integer s=0;s<64;s++) if(!q_valid[s] && free_slot<0) free_slot=s;
            req_rdy<=free_slot>=0 && cycle%5!=0;
            if(req_v && req_rdy) begin
                if(free_slot<0 || req_addr[4:0]!=0 || req_addr>65504)
                    $fatal(1,"LSU request bounds/queue addr=%h",req_addr);
                base=int'(req_addr); payload=0;
                for(integer b=0;b<32;b++) begin
                    if(req_we && req_strb[b]) begin
                        r=(base+b-32772)/1024;
                        lane=((base+b-32772)%1024)/4;
                        byte_in_word=(base+b-32772)%4;
                        if(base+b<32772 || r<0 || r>=6 || lane<0 || lane>=128)
                            $fatal(1,"unexpected LSU enabled byte addr=%h byte=%0d",req_addr,b);
                        if(req_data[b*8+:8] !== 8'(word(r,lane)>>(8*byte_in_word)))
                            $fatal(1,"LSU mismatch r=%0d lane=%0d byte=%0d expected=%h actual=%h tag=%0d",
                                r,lane,byte_in_word,8'(word(r,lane)>>(8*byte_in_word)),req_data[b*8+:8],req_tag);
                        if(stored[r*512+lane*4+byte_in_word]) $fatal(1,"duplicate enabled LSU byte");
                        stored[r*512+lane*4+byte_in_word]=1;
                        memory_bytes[base+b]<=req_data[b*8+:8]; written_bytes++;
                    end
                    payload[b*8+:8]=memory_bytes[base+b];
                end
                if(req_we) writes++; else reads++;
                q_valid[free_slot]<=1; q_we[free_slot]<=req_we;
                q_tag[free_slot]<=req_tag; q_data[free_slot]<=payload;
                // Deterministically reorder responses; writes ACK only accepted stores.
                q_due[free_slot]<=cycle+2+int'(req_tag%7);
            end
            if(rsp_v && rsp_rdy) begin rsp_v<=0; acknowledgments++; end
            if(!rsp_v || rsp_rdy) begin
                pick=-1;
                for(integer s=0;s<64;s++) if(q_valid[s] && q_due[s]<=cycle) pick=s;
                if(pick>=0) begin
                    rsp_v<=1; rsp_tag<=q_tag[pick]; rsp_we<=q_we[pick];
                    rsp_data<=q_data[pick]; q_valid[pick]<=0;
                end
            end
        end
    end

    reg [2127:0] expected_x[0:1], known_x[0:1];
    reg pending=0, captured=0;
    reg [5:0] pending_addr=0, captured_addr=0;
    reg [2127:0] pending_bits=0,pending_mask=0,captured_bits=0,captured_mask=0;
    integer issued_x=0, checked_x=0, adjacent_x=0;
    reg previous_issue_x=0;
    always @(posedge clk) begin : x_observer
        integer a,ra,rb;
        reg this_issue;
        this_issue=rst_n && dut.g_on.can_issue &&
                   (dut.g_on.op==8'h43 || dut.g_on.op==8'h45);
        captured<=rst_n && dut.g_on.bd_xw;
        if(rst_n && dut.g_on.bd_xw) begin
            if(!pending || dut.g_on.bd_xa!==pending_addr)
                $fatal(1,"X-write owner/address mismatch");
            captured_addr<=pending_addr; captured_bits<=pending_bits; captured_mask<=pending_mask;
        end
        pending<=this_issue;
        previous_issue_x<=this_issue;
        if(this_issue) begin
            a=int'(dut.g_on.imm); ra=int'(dut.g_on.fa); rb=int'(dut.g_on.fb);
            if(a>1) $fatal(1,"unexpected X fixture address");
            if(previous_issue_x) adjacent_x++;
            for(integer block=0;block<8;block++) begin
                if(dut.g_on.op==8'h43) begin
                    for(integer b=0;b<32;b++) begin
                        expected_x[a][block*266+b*8+:8]=8'(word(block<4?ra:rb,(block%4)*32+b));
                        known_x[a][block*266+b*8+:8]=8'hff;
                    end
                end else begin
                    expected_x[a][block*266+256+:10]=10'(word(ra,block));
                    known_x[a][block*266+256+:10]=10'h3ff;
                end
            end
            pending_addr<=6'(a); pending_bits<=expected_x[a]; pending_mask<=known_x[a]; issued_x++;
        end
    end
    always @(negedge clk) if(captured) begin
        if((dut.g_on.g_bd.u_bdtc.xmem[captured_addr]&captured_mask) !== (captured_bits&captured_mask))
            $fatal(1,"X capture mismatch write=%0d address=%0d expected=%h observed=%h mask=%h",
                checked_x,captured_addr,captured_bits,dut.g_on.g_bd.u_bdtc.xmem[captured_addr],captured_mask);
        checked_x++;
    end
    always @(negedge clk) if(rst_n && fault) $fatal(1,"SM reported an actual fault");
    initial begin
        for(integer b=0;b<65536;b++) memory_bytes[b]=0;
        for(integer b=0;b<3072;b++) stored[b]=0;
        for(integer a=0;a<2;a++) begin expected_x[a]=0; known_x[a]=0; end
        for(integer r=0;r<6;r++) begin
            for(integer l=0;l<128;l++) for(integer b=0;b<4;b++)
                memory_bytes[4100+r*1024+l*4+b]=8'(word(r,l)>>(8*b));
            emit(ins(8'h28,4,0,0,32'(4100+r*1024)));
            emit(ins(8'h38,8'(r),4,127,0));
        end
        // Initialise exponents via real instructions, without assuming old code bits.
        emit(ins(8'h45,0,2,0,0)); emit(ins(8'h45,0,5,0,1));
        // Six consecutive writes: same-row partial updates and a row change.
        emit(ins(8'h43,0,0,1,0)); emit(ins(8'h45,0,2,0,0));
        emit(ins(8'h43,0,3,4,1)); emit(ins(8'h45,0,5,0,1));
        emit(ins(8'h43,0,3,4,0)); emit(ins(8'h45,0,5,0,0));
        for(integer r=0;r<6;r++) begin
            emit(ins(8'h28,4,0,0,32'(32772+r*1024)));
            emit(ins(8'h39,8'(r),4,127,0));
        end
        emit(ins(8'h32,0,0,0,0));
        repeat(4) @(negedge clk); rst_n=1;
        for(integer p=0;p<np;p++) begin
            @(negedge clk); im_we=1; im_addr=13'(p); im_data=program_words[p];
        end
        @(negedge clk); im_we=0; launch_v=1;
        @(negedge clk); launch_v=0;
        wait(done); @(negedge clk);
`ifdef OT_CAPTURE_DS20
        if(dut.g_on.ur[0]!==32'h1ffff || dut.g_on.ur[1]!==32'habcd0)
            $fatal(1,"DS20 full token17/position20 identity lost");
`endif
        if(fault || issued_x!=8 || checked_x!=8 || adjacent_x!=7 ||
           reads!=102 || writes!=102 || acknowledgments!=204 || written_bytes!=3072)
            $fatal(1,"coverage/debt fault=%b X=%0d/%0d adjacent=%0d LSU=%0d/%0d ACK=%0d bytes=%0d",
                fault,issued_x,checked_x,adjacent_x,reads,writes,acknowledgments,written_bytes);
        for(integer s=0;s<64;s++) if(q_valid[s]) $fatal(1,"pending memory request at retirement");
        for(integer b=0;b<3072;b++) if(!stored[b]) $fatal(1,"missing enabled LSU byte %0d",b);
        $display("PASS sm_capture_lsu X=8 adjacent=7 LSUread=102 LSUwrite=102 ACK=204 exactbytes=3072");
        $finish;
    end
endmodule
