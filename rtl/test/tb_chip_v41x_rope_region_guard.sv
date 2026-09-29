`timescale 1ns/1ps
module tb_chip_v41x_rope_region_guard;
    reg [1:0] present;
    reg [119:0] reserved_end, plain_base, yarn_base;
    wire valid;
    wire [3:0] bad_stack;
    integer checks=0;
    localparam [29:0] R=30'd620000000, T=30'd2097152;
    ot_chip_v41x_rope_region_guard dut (
        .present(present),.reserved_end(reserved_end),
        .plain_base(plain_base),.yarn_base(yarn_base),
        .valid(valid),.bad_stack(bad_stack));
    task automatic check_case(input bit want);
        #1;
        if(valid!==want) $fatal(1,"region valid=%b want=%b bad=%b",valid,want,bad_stack);
        checks++;
    endtask
    initial begin
        present=2'b11;
        for(integer s=0;s<4;s++) begin
            reserved_end[s*30 +: 30]=R;
            plain_base[s*30 +: 30]=R;
            yarn_base[s*30 +: 30]=R+T;
        end
        check_case(1); // stage 0 plain+YaRN, nonoverlapping
        present=2'b10; yarn_base[29:0]=R; check_case(1); // YaRN-only stage
        present=2'b11; yarn_base[29:0]=R+T-1; check_case(0); // one-sector overlap
        yarn_base[29:0]=R+T; reserved_end[29:0]=0; check_case(0); // no runtime placement
        reserved_end[29:0]=R; plain_base[29:0]=R-1; check_case(0); // collides with state
        plain_base[29:0]=R; yarn_base[29:0]=30'd631000000; check_case(0); // beyond 0.9 cap
        yarn_base[29:0]=R+T; present=0; check_case(0); // no table allocated
        $display("ROPE_REGION_PASS checks=%0d",checks);
        $finish;
    end
endmodule
