`timescale 1ns/1ps
// Minimum OD tile: identical isolated frame through legacy and successor.
// 300-word malformed frame also checks sticky fault; exact payload/order and
// no loss on all 512 bits; uninterrupted output proves II=1 after startup.
module tb_s81ph_svc_od_latency;
    reg ck=0, rst=0;
    always #0.416666 ck=~ck;
    wire [3:0] ready [0:1];
    reg [3:0] valid [0:1];
    reg [2047:0] data [0:1];
    wire [513:0] od [0:1];
    wire bad [0:1];
    integer sent[0:1], got[0:1], first_in[0:1], first_out[0:1], last_out[0:1];
    integer cyc=0;
    function automatic [511:0] word_at(input integer idx);
        reg [511:0] v;
        begin
            for (integer k=0;k<16;k=k+1) v[32*k+:32]=32'h913bf167 ^ (idx*7919+k*104729);
            if (idx==0) v[491:480]=299;
            word_at=v;
        end
    endfunction
    generate for (genvar g=0;g<2;g=g+1) begin : g_dut
        dsfd_svcio_od #(.MARGIN(g)) dut(.ck(ck),.rst(rst),.od_v(valid[g]),.od_d(data[g]),
            .od_r(ready[g]),.od(od[g]),.of(),.bad(bad[g]));
    end endgenerate
    initial begin
        for (integer k=0;k<2;k=k+1) begin
            sent[k]=0;got[k]=0;first_in[k]=-1;first_out[k]=-1;last_out[k]=-1;valid[k]=0;data[k]=0;
        end
        repeat(6) @(negedge ck);
        rst=1;
    end
    always @(negedge ck) if (rst) begin
        for(integer k=0;k<2;k=k+1) begin
            valid[k]=sent[k]<300 ? 1 : 0;
            data[k][511:0]=word_at(sent[k]);
        end
    end
    always @(posedge ck) if (rst) begin
        cyc=cyc+1;
        for(integer k=0;k<2;k=k+1) begin
            if(valid[k][0] && ready[k][0]) begin
                if(sent[k]==0) first_in[k]=cyc;
                sent[k]=sent[k]+1;
            end
            if(od[k][1]) begin
                if(got[k]>=300 || od[k][513:2] !== word_at(got[k])) $fatal(1,"OD_LAT FAIL payload k=%0d n=%0d",k,got[k]);
                if(got[k]==0) first_out[k]=cyc;
                else if(cyc!=last_out[k]+1) $fatal(1,"OD_LAT FAIL II k=%0d n=%0d",k,got[k]);
                last_out[k]=cyc;got[k]=got[k]+1;
            end
        end
        if(got[0]==300 && got[1]==300) begin
            if(!bad[0] || !bad[1]) $fatal(1,"OD_LAT FAIL missing malformed-header fault");
            if((first_out[1]-first_in[1])-(first_out[0]-first_in[0])!=2) $fatal(1,"OD_LAT FAIL latency");
            $display("OD_LAT PASS words=300 legacy=%0d margin=%0d delta=2 II=1 malformed_fault=1",first_out[0]-first_in[0],first_out[1]-first_in[1]);
            $finish;
        end
        if(cyc>3000) $fatal(1,"OD_LAT FAIL timeout");
    end
endmodule
