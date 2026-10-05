`timescale 1ns/1ps
module tb_qwen_me_add_bypass_w12;
    reg clk=0,rst_n=0,v=0;
    reg [31:0] a=0,b=0;
    wire [31:0] yr,yo,yn;
    wire [1:0] er,eo,en;
    wire vr,vo,vn;
    ot_hdc_fp32_add_lat #(.LAT(7)) refadd(clk,rst_n,v,a,b,yr,er,vr);
    ot_qwen_me_add_bypass_w12 #(.LAT(7)) offadd(clk,rst_n,v,a,b,yo,eo,vo);
    ot_qwen_me_add_bypass_w12 #(.LAT(7),.BYPASS_AFTER_CAPTURE(1)) onadd(clk,rst_n,v,a,b,yn,en,vn);
    reg [6:0] expected_v=0;
    integer cycles=0,valid_count=0,i,j;
    reg [31:0] seed=32'h59c017a1;
    reg [31:0] corners[0:23];
    function automatic [31:0] random_word(input [31:0] old);
        reg [31:0] x;
        begin x=old^(old<<13);x=x^(x>>17);x=x^(x<<5);random_word=x;end
    endfunction
    task edge_check;
        begin
            #2;clk=1;
            if(!rst_n)expected_v=0;else expected_v={expected_v[5:0],v};
            #1;cycles=cycles+1;
            if({vo,yo,eo} !== {vr,yr,er} || {vn,yn,en} !== {vr,yr,er})
                $fatal(1,"arithmetic/held/reset mismatch cycle=%0d a=%h b=%h ref=%h/%h/%b off=%h/%h/%b on=%h/%h/%b",cycles,a,b,yr,er,vr,yo,eo,vo,yn,en,vn);
            if(vr !== expected_v[6])$fatal(1,"LAT7 edge mismatch cycle=%0d",cycles);
            if(vr)valid_count=valid_count+1;
            clk=0;#1;
        end
    endtask
    initial begin
        corners[0]=32'h00000000;corners[1]=32'h80000000;
        corners[2]=32'h00000001;corners[3]=32'h80000001;
        corners[4]=32'h007fffff;corners[5]=32'h807fffff;
        corners[6]=32'h00800000;corners[7]=32'h80800000;
        corners[8]=32'h3f800000;corners[9]=32'hbf800000;
        corners[10]=32'h7f7fffff;corners[11]=32'hff7fffff;
        corners[12]=32'h7f800000;corners[13]=32'hff800000;
        corners[14]=32'h7fc00001;corners[15]=32'hffc00001;
        corners[16]=32'h7f800001;corners[17]=32'hff800001;
        corners[18]=32'h3f000000;corners[19]=32'h3f800001;
        corners[20]=32'h33800000;corners[21]=32'hb3800000;
        corners[22]=32'h00800001;corners[23]=32'h80800001;
        repeat(9)edge_check();rst_n=1;v=1;
        // All ordered corner pairs, uninterrupted II1, including both signs
        // of zero, subnormals, cancellation, overflow and NaN/Inf bypass.
        for(i=0;i<24;i=i+1)for(j=0;j<24;j=j+1)begin a=corners[i];b=corners[j];edge_check();end
        // Raw exponent/mantissa coverage, alternating bypass/normal values
        // ensures reconstruction uses the captured operand, never live pins.
        for(i=0;i<16384;i=i+1)begin
            seed=random_word(seed);a=seed;seed=random_word(seed);b=seed;
            if(i%8==0)a=0;if(i%8==1)b=32'h80000000;
            if(i%8==2)a={a[31],8'd0,a[22:0]};
            v=(i%11!=0);rst_n=(i!=211&&i!=9321);edge_check();
        end
        rst_n=1;v=0;a=32'h7fc11111;b=32'h008fffff;repeat(10)edge_check();
        $display("PASS qme_bypass old/off/on cycles=%0d valid_results=%0d LAT7 II1 corners576 raw16384 reset2 held_operand_alignment",cycles,valid_count);$finish;
    end
endmodule
