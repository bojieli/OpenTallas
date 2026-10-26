`timescale 1ns/1ps
module tb_qkd_ahub_static;
    parameter integer MUT=0;
    reg ck=0,rst_n=0,start=0,epoch=1;
    always #0.5 ck=~ck;
    reg [3:0] sv=0,sg=0,sa=0;reg [63:0] se=0;
    reg [7:0] ty=0,hh=0;
    reg [15:0] kk=0;
    reg [127:0] dd=0;
    wire [143:0] am;wire rv,rp,fault;wire [15:0] re;wire [1:0] rh;wire [31:0] rd;wire [127:0] rz4;
    ot_qkd_ahub_static_die #(.LMAX_IN_AGE({4{16'd100}}),.Z_IN_AGE({4{16'd200}}),.Z_IN_STRIDE(16),
        .LMAX_ISSUE_AGE(110),.Z_START_AGE(470),.RECIP_ISSUE_AGE(555),
        .RECIP_RETURN_AGE((MUT==4)?625:624),.RZ_PUBLISH_AGE(630)) dut (
        .ck_core(ck),.ck_zh({4{ck}}),.ck_recip(ck),.rst_n(rst_n),.start(start),.active_layer_parity(epoch),.request_epoch(16'h1234),.active_layer(6'd7),.T(14'd8192),
        .si_valid(sv),.si_type(ty),.si_g(sg),.si_hh(hh),.si_k(kk),.si_any(sa),.si_epoch(se),.si_layer({4{6'd7}}),.si_data(dd),
        .am(am),.rz_valid(rv),.rz_head(rh),.rz_data(rd),.rz_epoch(re),.rz_publish(rp),.rz_vector(rz4),.fault(fault));
    function automatic [31:0] lval(input integer n);
        case(n)
        1:lval=32'h3f800000;2:lval=32'h40000000;3:lval=32'h40400000;4:lval=32'h40800000;
        5:lval=32'h40a00000;6:lval=32'h40c00000;7:lval=32'h40e00000;8:lval=32'h41000000;
        9:lval=32'h41100000;10:lval=32'h41200000;11:lval=32'h41300000;12:lval=32'h41400000;
        13:lval=32'h41500000;14:lval=32'h41600000;15:lval=32'h41700000;default:lval=32'h41800000;endcase
    endfunction
    function automatic [31:0] fpint(input integer n);
        integer top;begin top=0;for(integer b=0;b<16;b=b+1)if((n>>b)!=0)top=b;
        fpint=((127+top)<<23)|((n<<(23-top))&32'h007fffff);end
    endfunction
    // External expected answers: golden FP32 seed and three rounded Newton steps.
    function automatic [31:0] reciprocal_expected(input integer head);
        case(head)0:reciprocal_expected=32'h39fc0fc0;1:reciprocal_expected=32'h397c0fc0;
        2:reciprocal_expected=32'h39280a81;default:reciprocal_expected=32'h38fc0fc0;endcase
    endfunction
    integer c,h,k,amcount=0,rcount=0,pcount=0,expected;
    initial begin
        repeat(6)@(negedge ck);rst_n=1;
        repeat(80)@(negedge ck);
        for(c=0;c<680;c=c+1)begin
            start=(c==0);sv=0;ty=0;sg=0;sa=0;se={4{16'h1234}};hh=0;kk=0;dd=0;
            if(c>=100&&c<104)begin
                h=c-100;sv=15;sa=15;hh={4{2'(h)}};
                for(integer s=0;s<4;s=s+1)dd[32*s+:32]=lval(1+4*s+h);
            end
            if(c>=200&&c<456&&(c-200)%16<4)begin
                h=(c-200)%16;k=(c-200)/16;sv=15;ty={4{2'd1}};sa=15;hh={4{2'(h)}};kk={4{4'(k)}};for(integer a=0;a<4;a=a+1)dd[32*a+:32]=fpint((a*16+k+1)*(h+1));
                if(MUT==1&&c==264)sv[0]=0;
                if(MUT==2&&c==264)begin sv[0]=0;end
                if(MUT==3&&c==264)se[0]=~se[0];
            end
            if(MUT==2&&c==268)begin sv[0]=1;ty[1:0]=1;hh[1:0]=0;kk[3:0]=4;dd[31:0]=32'h3f800000;end
            if(c==456)begin sv=15;ty={4{2'd2}};end
            @(posedge ck);#0.1;
            if(c>=548&&c<553)$display("AHUB_TRACE c%0d root%h",c,dut.zh_root);
            if(dut.rc_vo)$display("AHUB_RECIP c%0d vo%0d y%h",c,dut.rc_vo,dut.rc_y);
            expected=c>=113&&c<117;
            if(am[35]!==expected[0])$fatal(1,"AM calendar c%0d valid%0d",c,am[35]);
            if(am[35])begin
                h=c-113;amcount=amcount+1;
                for(integer s=0;s<4;s=s+1)if(am[36*s+:35]!=={1'b0,2'(h),lval(13+h)})$fatal(1,"AM data c%0d %h",c,am);
            end
            expected=(MUT==4)?(c>=625&&c<629):(c>=624&&c<628);
            if(rv!==expected[0])$fatal(1,"recip calendar c%0d valid%0d",c,rv);
            if(rv)begin rcount=rcount+1;if(MUT==0&&(rd!==reciprocal_expected(c-624)||rh!==2'(c-624)||re!=16'h1234))$fatal(1,"recip data c%0d h%0d %h",c,rh,rd);end
            if(rp)begin pcount=pcount+1;if(c!=630)$fatal(1,"publication calendar");if(MUT==0)for(integer a=0;a<4;a=a+1)if(rz4[32*a+:32]!==reciprocal_expected(a))$fatal(1,"RZ4 %h",rz4);end
            @(negedge ck);
        end
        if(amcount!=4||rcount!=4||pcount!=1||(MUT==0&&fault)||(MUT!=0&&!fault))$fatal(1,"AHUB final counts%0d/%0d/%0d fault%0d mut%0d",amcount,rcount,pcount,fault,MUT);
        $display("AHUB_STATIC PASS mutant=%0d am=%0d recip=%0d publish=%0d fault=%0d",MUT,amcount,rcount,pcount,fault);$finish;
    end
endmodule
