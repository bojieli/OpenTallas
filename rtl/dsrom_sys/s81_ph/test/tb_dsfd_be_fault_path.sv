`timescale 1ns/1ps
module tb_dsfd_be_fault_path;
    reg ck=0, rn=0; reg [15:0] i=0;
    always #5 ck=~ck;
    wire [15:0] o0,o1,o2,o6;
    dsfd_be_fault_path #(.STAGES(0)) u0(ck,rn,i,o0);
    dsfd_be_fault_path #(.STAGES(1)) u1(ck,rn,i,o1);
    dsfd_be_fault_path #(.STAGES(2)) u2(ck,rn,i,o2);
    dsfd_be_fault_path #(.STAGES(6)) u6(ck,rn,i,o6);
    reg [15:0] model [0:5]; integer k,t,errors=0,checks=0;
    initial begin
        for(k=0;k<6;k=k+1) model[k]=0;
        for(t=0;t<160;t=t+1) begin
            @(negedge ck);
            rn = !(t<3 || (t>=42 && t<45) || (t>=110 && t<114));
            // all bits walking, changes every cycle, sticky episodes, reset with live input
            if (t<35) i = 16'b1 << (t%16);
            else if(t<90) i = 16'hffff >> (t%16);
            else i = (t*16'h1327)^16'ha56c;
            if(o0 !== i) begin $display("FAIL bypass t=%0d",t); errors=errors+1; end
            @(posedge ck);
            for(k=5;k>0;k=k-1) model[k] = rn ? model[k-1] : 0;
            model[0] = rn ? i : 0;
            #1;
            if(o0!==i || o1!==model[0] || o2!==model[1] || o6!==model[5]) begin
                $display("FAIL waveform t=%0d rn=%b i=%h got=%h/%h/%h expected=%h/%h/%h",t,rn,i,o1,o2,o6,model[0],model[1],model[5]);
                errors=errors+1;
            end
            checks=checks+1;
        end
        $display("RESULT checks=%0d errors=%0d stages=0,1,2,6",checks,errors);
        if(errors) $fatal(1,"FAIL");
        $display("PASS FAULT_PATH_EXACT_LATENCY_RESET"); $finish;
    end
endmodule
