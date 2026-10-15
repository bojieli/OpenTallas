`timescale 1ns/1ps
// Declared CTL-boundary stimuli prove reserved publication slots and faults.
// Arithmetic and the native ASTK producers are proved by the composition owner.
module tb_qkd_astk_ctl_static;
    parameter integer MUT=0;
    reg ck=0,rst_n=0;
    always #0.5 ck=~ck;
    reg [539:0] aq=0;
    reg [35:0] am=0;
    reg [266:0] xi=0;
    reg [137:0] zi=0;
    wire [564:0] ap;
    wire af;
    qkd_astk_ctl_tp8 #(.STATIC_SCHEDULE(1),.LMAX_START_AGE(300),.Z_START_AGE(400),.Z_STRIDE(16)) dut (
        .ck(ck),.rst_n(rst_n),.st(2'd0),.aq(aq),.lt(),.am(am),.ap(ap),.af(af),.qo(),
        .xi(xi),.co(),.px(263'd0),.py(263'd0),.zi(zi),.fx(1'b0),.fy(1'b0),.fz(1'b0));
    integer cyc,nsent=0,k,h,expected;
    initial begin
        repeat(6)@(negedge ck);rst_n=1;
        repeat(4)@(negedge ck);
        for(cyc=0;cyc<680;cyc=cyc+1)begin
            aq=0;aq[14:1]=8192;aq[0]=(cyc==0);
            xi=0;am=0;zi=0;
            if(cyc>=1&&cyc<=256)xi[4:1]=8;
            if(cyc>=310&&cyc<314)begin am[0]=1;am[3:2]=cyc-310;end
            if(cyc>=398&&(cyc-398)%16==0&&(cyc-398)/16<16)begin
                k=(cyc-398)/16;zi[0]=1;zi[5:2]=(MUT==2&&k==4)?5:k;
                for(h=0;h<4;h=h+1)zi[10+h*32+:32]=32'h3f800000+k*4+h;
                if(MUT==1&&k==4)zi[0]=0;
            end
            @(posedge ck);#0.1;
            expected=(cyc>=301&&cyc<=304)||(cyc>=401&&cyc<657&&(cyc-401)%16<4)||(cyc==657);
            if(ap[0]!==expected[0])$fatal(1,"publication timeline c%0d valid%0d expected%0d",cyc,ap[0],expected);
            if(ap[0])begin
                nsent=nsent+1;
                if(MUT==0&&cyc>=401&&cyc<657)begin
                    k=(cyc-401)/16;h=(cyc-401)%16;
                    if(ap[2:1]!=1||ap[9:6]!=k||ap[5:4]!=h||ap[42:11]!=32'h3f800000+k*4+h)$fatal(1,"publication data/tag c%0d %h",cyc,ap[42:1]);
                end
            end
            @(negedge ck);
        end
        if(nsent!=69||(MUT==0&&af)||(MUT!=0&&!af))$fatal(1,"fault/count mutant%0d sent%0d af%0d",MUT,nsent,af);
        $display("ASTK_CTL_STATIC PASS mutant=%0d words=%0d fixed_lmax=301 fixed_z=401 stride=16 done=657 fault=%0d",MUT,nsent,af);$finish;
    end
endmodule
