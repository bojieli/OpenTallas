`timescale 1ns/1ps
module tb_qfd_dv_table_rom_loader #(parameter integer BTAB_COMPACT=0);
    reg ck=0;always #5 ck=~ck;
    reg rst_n=0,start=0,other=0;
    reg [5:0] stage=1;reg [1:0] uid=0;
    wire [4:0] we,busy,done,fault;
    wire [9:0] kind;wire [119:0] addr;wire [5119:0] data;
    genvar g;generate for(g=0;g<5;g=g+1)begin: dut
        qfd_dv_table_rom_loader #(.MUT(g),.BTAB_COMPACT(BTAB_COMPACT)) u(.ck(ck),.rst_n(rst_n),.start(start),.stage(stage),.user_id(uid),
            .other_table_write(other),.tw_we(we[g]),.tw_kind(kind[2*g+:2]),.tw_addr(addr[24*g+:24]),
            .tw_data(data[1024*g+:1024]),.busy(busy[g]),.done(done[g]),.fault(fault[g]));
    end endgenerate
    reg [1050:0] expect_word[0:12671];
    string exp_file;integer mut=0,cycle=0,first=-1,checks=0,slot,ix,st,u,fault_case=0;
    reg [1050:0] want,got;
    always @(posedge ck)begin
        cycle=cycle+1;
        if(start)first=cycle+3;
        #1;
        if(rst_n && !fault_case && first>0 && cycle>=first && cycle<first+88)begin
            slot=cycle-first;ix=(((stage-1)*4)+uid)*88+slot;want=expect_word[ix];
            got={addr[24*mut+:24],kind[2*mut+:2],we[mut],data[1024*mut+:1024]};
            if(we[mut]!==want[1024] || (want[1024] && got!==want))
                $fatal(1,"TABLE_ROM_MISMATCH stage=%0d user=%0d slot=%0d cycle=%0d mut=%0d",stage,uid,slot,cycle,mut);
            if(fault[mut])$fatal(1,"TABLE_ROM_UNEXPECTED_FAULT");
            if(done[mut] !== (slot==87))$fatal(1,"TABLE_ROM_DONE_AGE slot=%0d",slot);
            checks=checks+1;
        end
    end
    initial begin
        if(!$value$plusargs("EXPECTED=%s",exp_file))$fatal(1,"EXPECTED required");
        if($value$plusargs("MUT=%d",mut))begin end
        if($value$plusargs("FAULT_CASE=%d",fault_case))begin end
        $readmemh(exp_file,expect_word);
        repeat(4)@(negedge ck);rst_n=1;repeat(5)@(negedge ck);
        if(fault_case==1)begin
            stage=37;start=1;@(negedge ck);start=0;repeat(5)@(negedge ck);
            if(!fault[0]||busy[0]||we[0])$fatal(1,"TABLE_ROM_BOUNDARY_NOT_REJECTED");
            $display("TABLE_ROM_STAGE37_REJECT_PASS");$finish;
        end
        if(fault_case==2)begin
            start=1;@(negedge ck);start=0;repeat(8)@(negedge ck);
            other=1;repeat(3)@(negedge ck);other=0;repeat(2)@(negedge ck);
            if(!fault[0])$fatal(1,"TABLE_ROM_WRITE_COLLISION_NOT_REJECTED");
            $display("TABLE_ROM_WRITE_COLLISION_REJECT_PASS");$finish;
        end
        for(st=1;st<=36;st=st+1)for(u=0;u<4;u=u+1)begin
            @(negedge ck);stage=st;uid=u;start=1;
            @(negedge ck);start=0;
            wait(done[mut]);repeat(3)@(negedge ck);
        end
        if(checks!=12672)$fatal(1,"TABLE_ROM_CHECK_COUNT %0d",checks);
        $display("TABLE_ROM_NATIVE_PASS checks=%0d first_age=3 slots=88 final_visibility_guard_open",checks);
        $finish;
    end
    initial begin repeat(20000)@(posedge ck);$fatal(1,"TABLE_ROM_BOUNDED_BENCH_PROGRESS");end
endmodule
