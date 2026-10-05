`timescale 1ns/1ps
module tb_hdc_dyn_ttiles;
    reg [17:0] pos=0;
    reg [3:0] split=0;
    wire [17:0] r4, r6144;
    wire bad4, bad6144;
    integer s, p, n=0;
    ot_hdc_dyn_ttiles #(.W(16),.G(4),.NW(18)) a (
        .pos(pos),.split_log2(split),.rounds(r4),.invalid_split(bad4));
    ot_hdc_dyn_ttiles #(.W(16),.G(6144),.NW(18)) b (
        .pos(pos),.split_log2(split),.rounds(r6144),.invalid_split(bad6144));
    task automatic check(input integer position, input integer sp);
        integer expect4, expect6144;
        begin
            pos=position; split=sp; #1;
            if (sp<=2) expect4=position/(16*(4>>sp))+1;
            expect6144=position/(16*(6144>>sp))+1;
            if (sp<=2 && (bad4 || r4!==expect4))
                $fatal(1,"G4 pos=%0d split=%0d got=%0d expect=%0d",position,sp,r4,expect4);
            if (bad6144 || r6144!==expect6144)
                $fatal(1,"G6144 pos=%0d split=%0d got=%0d expect=%0d",position,sp,r6144,expect6144);
            n=n+1;
        end
    endtask
    initial begin
        for (s=0;s<=11;s=s+1) begin
            for (p=0;p<8192;p=p+137) check(p,s);
            check(16*(6144>>s)-1,s);
            check(16*(6144>>s),s);
            check(8191,s);
        end
        split=12; #1;
        if (!bad6144 || r6144!==0) $fatal(1,"invalid split accepted");
        $display("PASS exact DYN_TTILES: %0d position/split cases, G4 and G6144",n);
        $finish;
    end
endmodule
