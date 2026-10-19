`timescale 1ns/1ps
module tb_qfd_dv_calendar_rom;
    reg ck=0;always #5 ck=~ck;
    reg rst_n=0,req=0,install=0,running=0;
    reg [9:0] first=0;reg[2:0] count=0;reg[1:0] user_id=0;reg[5:0] stage=0;
    wire valid,fault;wire[511:0]data;wire[1:0]ou;wire[5:0]os;wire[2:0]on;
    parameter integer MUT=0;
    qfd_dv_calendar_rom #(.NENT(783),.MUT(MUT)) dut(.*,.out_user(ou),.out_stage(os),.out_count(on));
    reg[511:0] expected[0:4095];reg[8191:0]path;
    integer checks=0,cycle=0,code=0;
    reg qv[0:2];integer qrow[0:2],qu[0:2],qs[0:2],qn[0:2];
    task tick;
        begin
            @(posedge ck);#1;
            if(valid!==qv[1])$fatal(1,"CAL_VALID_MISMATCH cycle%0d",cycle);
            if(valid)begin
                if(data!==expected[qrow[1]] || ou!==qu[1][1:0] || os!==qs[1][5:0] || on!==qn[1][2:0])
                    $fatal(1,"CAL_DATA_MISMATCH cycle%0d row%0d user%0d stage%0d",cycle,qrow[1],qu[1],qs[1]);
                checks++;
            end
            qv[1]=qv[0];qrow[1]=qrow[0];qu[1]=qu[0];qs[1]=qs[0];qn[1]=qn[0];
            qv[0]=req;qrow[0]=first/4;qu[0]=user_id;qs[0]=stage;qn[0]=count;
            cycle++;
            @(negedge ck);
        end
    endtask
    initial begin
        if(!$value$plusargs("EXPECTED=%s",path))$fatal(1,"missing oracle");
        $readmemh(path,expected);
        for(integer k=0;k<3;k++)qv[k]=0;
        repeat(3)@(negedge ck);rst_n=1;repeat(4)@(negedge ck);
        for(integer s=0;s<38;s++)for(integer u=0;u<4;u++)for(integer row=0;row<196;row++)begin
            req=1;first=row*4;count=(row==195)?3:4;user_id=u;stage=s;tick();
        end
        req=0;repeat(4)tick();
        if(fault)$fatal(1,"unexpected fault");
        $display("CAL_ROM_PASS checks=%0d all38stages4users back_to_back",checks);
        // Fault guard vehicle uses separate executions to retain each witness.
        if($value$plusargs("FAULT=%d",code))begin
            case(code)
                1:begin req=1;first=780;count=4;end
                2:begin req=1;first=1;count=1;end
                3:begin req=1;first=0;count=0;end
                4:begin req=1;first=0;count=1;stage=38;end
                5:begin install=1;running=1;end
            endcase
            @(posedge ck);#1;if(!fault)$fatal(1,"guard missed%0d",code);
            $display("CAL_GUARD_PASS fault=%0d",code);
        end
        $finish;
    end
endmodule
