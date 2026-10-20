`timescale 1ps/1ps
module tb_ring_phase;
    reg cs=0,cd=0,rst=0;
    integer phase=0, release_ps=100000;
    initial begin #10000; forever #4000 cs=~cs; end
    initial begin
        if($value$plusargs("phase=%d",phase)) begin end
        #(10000+phase); forever #4000 cd=~cd;
    end
    initial begin
        if($value$plusargs("release=%d",release_ps)) begin end
        #(release_ps); rst=1;
        #400000;
        $display("RING_PHASE PASS phase=%0d release=%0d samples=%0d min_age_ps=%0d max_age_ps=%0d",phase,release_ps,samples,min_age,max_age); $finish;
    end
    reg [7:0] i=0;
    always @(negedge cs) i<=i+1;
    wire [31:0] bank; wire [11:0] epo; wire [3:0] vld; wire [7:0] o;
    ot_pl_land_local_w #(.W(8),.D(4)) w(.ck(cs),.rsi(rst),.i(i),.bank(bank),.epo(epo),.vld(vld));
    ot_pl_land_local_r #(.W(8),.D(4),.K(2)) r(.ck(cd),.rsi(rst),.bank(bank),.epo(epo),.vld(vld),.o(o));
    time last_write[0:3];
    integer min_age=1000000,max_age=0;
    always @(posedge cs) if(w.rq) begin
        for(integer j=0;j<4;j=j+1) if(w.write_oh[j]) last_write[j]=$time;
    end
    always @(posedge cd) if(r.warm && r.selected_valid) begin
        for(integer j=0;j<4;j=j+1) if(r.read_oh[j]) begin
            if(($time-last_write[j])<min_age) min_age=$time-last_write[j];
            if(($time-last_write[j])>max_age) max_age=$time-last_write[j];
        end
    end
    integer samples=0;
    always @(posedge cd) if(r.warm && r.selected_valid) samples<=samples+1;
endmodule
