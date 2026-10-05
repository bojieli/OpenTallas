`timescale 1ns/1ps
import ot_rom_coll_pkg::*;
module tb_head_hook;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,start=0;
    reg [63:0] valid=0,accept=0;
    reg [64*30-1:0] addr=0;
    reg [64*32-1:0] data=0;
    wire [3:0] dv,dr,dl,ur,busy,result_seen,fault,am_any;
    wire [511:0] dd[0:3];wire [46:0] di[0:3];
    wire [20:0] ai[0:3];wire [31:0] av[0:3];
    reg terminal_ready=0,final_valid=0;
    reg [511:0] final_data=0;
    reg [46:0] final_identity=0;
    wire [3:0] final_ready;
    reg [3:0] final_mask=0;
    genvar k;
    generate for(k=0;k<4;k=k+1) begin:r
        wire uv,ul;wire [511:0] ud;wire [46:0] ui;
        if(k==0) begin
            assign uv=0;assign ul=0;assign ud=0;assign ui=0;
        end else begin
            assign uv=dv[k-1];assign ul=dl[k-1];assign ud=dd[k-1];assign ui=di[k-1];
        end
        if(k==3) assign dr[k]=terminal_ready;
        else assign dr[k]=ur[k+1];
        ot_dsrom_s81_head_amax #(.R(64),.RANK(k)) u(
            .clk(clk),.rst_n(rst_n),.start(start),.identity(47'h0123456789ab),
            .nout(21'd32320),.obase(30'd1000),.write_valid(valid),.write_accept(accept),
            .write_address(addr),.write_bits(data),.upstream_valid(uv),.upstream_ready(ur[k]),
            .upstream_data(ud),.upstream_last(ul),.upstream_identity(ui),
            .downstream_valid(dv[k]),.downstream_ready(dr[k]),.downstream_data(dd[k]),
            .downstream_last(dl[k]),.downstream_identity(di[k]),
            .final_valid(final_mask[k]),.final_ready(final_ready[k]),.final_data(final_data),.final_identity(final_identity),
            .busy(busy[k]),.result_seen(result_seen[k]),.am_idx(ai[k]),.am_val(av[k]),.am_any(am_any[k]),.fault(fault[k]));
    end endgenerate
    integer b,l,steps=0;
    always @(posedge clk) begin
        steps=steps+1;if(steps>4*505+100) $fatal(1,"finite native progress");
        if(|fault) $fatal(1,"source return/argmax fault");
    end
    initial begin
        repeat(3) @(negedge clk);rst_n=1;start=1;@(negedge clk);start=0;
        // Actual R64 interface, all32320 rows/rank. Reversed row IDs within
        // each accepted beat force explicit-ID ties rather than lane0 wins.
        for(b=0;b<505;b=b+1) begin
            @(negedge clk);valid=~64'd0;accept=~64'd0;
            for(l=0;l<64;l=l+1) begin
                addr[30*l+:30]=1000+b*64+63-l;
                data[32*l+:32]=(b*64+63-l==0)?32'h40000000:32'h3f800000;
            end
        end
        @(negedge clk);valid=0;accept=0;
        wait(dv[3]);#1;
        if(dd[3][H_ARG_ID+:32]!=0 || dd[3][H_ARG_VAL+:32]!=32'h40000000 || !dd[3][H_ARG_OK] ||
           di[3]!=47'h0123456789ab || !dl[3]) $fatal(1,"native global explicit-ID tie/owner");
        repeat(20) @(negedge clk);
        if(!busy[3] || !dv[3] || result_seen[3]) $fatal(1,"held carried ACK");
        final_data=dd[3];final_identity=di[3];terminal_ready=1;
        @(negedge clk);#1;
        if(&busy!=1'b1 || |result_seen) $fatal(1,"forward is not global publication");
        final_mask=4'b1111;@(negedge clk);#1;final_mask=0;
        if((|busy) || (&result_seen)!=1'b1 || (&am_any)!=1'b1) $fatal(1,"native retirement");
        $display("PASS_ACTUAL_NATIVE_CARRIED_HEAD_FOUR_RANKS_129280_ROWS_EXPLICIT_ID_HELD_ACK");$finish;
    end
endmodule
