`timescale 1ns/1ps
// KVJ-C2: qkd_embedding_static_return_head lock-step against qkd_embedding_static_return_hop with upi = 0 under random
// stimulus (legal and illegal slots, 40 reset windows).  MUT via -DOT_KVJ_HEAD_MUT.
`ifndef OT_KVJ_HEAD_MUT
`define OT_KVJ_HEAD_MUT 0
`endif
module tb_qkd_embedding_return_head;
    reg ck=0, rst_n=0, cs=0, cv=0, ts=0;
    reg [297:0] rec=0;
    wire [298:0] uh, ur;
    wire fh, fr;
    always #1 ck=~ck;
    qkd_embedding_static_return_head #(.MUT(`OT_KVJ_HEAD_MUT)) u_h (.ck(ck),.rst_n(rst_n),.capture_slot(cs),.capture_v(cv),
        .capture_record(rec),.transfer_slot(ts),.upo(uh),.fault(fh));
    qkd_embedding_static_return_hop u_r (.ck(ck),.rst_n(rst_n),.capture_slot(cs),.capture_v(cv),.capture_record(rec),
        .transfer_slot(ts),.upi(299'd0),.upo(ur),.fault(fr));
    integer cyc, err=0, w, k, fl=0, tr=0;
    initial begin
        for (w=0; w<40; w=w+1) begin
            rst_n=0; repeat(3) @(negedge ck); rst_n=1;
            for (k=0; k<2000; k=k+1) begin
                @(negedge ck);
                if (k>2 && (uh!==ur || fh!==fr)) begin err=err+1; if (err<5) $display("FAIL mismatch w%0d k%0d head %0b/%0b ref %0b/%0b", w,k,uh[0],fh,ur[0],fr); end
                if (fr) fl=fl+1; if (ur[0]) tr=tr+1;
                // legal-biased stimulus: mostly capture then transfer, rarely an illegal slot
                rec = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
                cv = ($random%64==0) ? $random : 1'b0; cs = cv ^ (($random%400)==0);
                ts = (($random%5)==0) ^ (($random%300)==0);
                if (w%2==0) begin cs = cv; end
            end
        end
        if (err==0 && tr>1000 && fl>0) $display("PASS return_head lock-step windows=40 transfers=%0d faulted_cycles=%0d", tr, fl);
        else $display("FAIL return_head err=%0d transfers=%0d faults=%0d", err, tr, fl);
        $finish;
    end
endmodule
