`timescale 1ns/1ps
// Diagnostic reference: one contiguous range on one timed 32-PC HBM stack.
module tb_hdc_v41x_idx_single_diag;
    localparam integer NPC=32;
    tb_hdc_v41x_idx_kstream_range #(.SKIP(0),.COUNT(65536)) ut();
    longint act,hit,conf,refresh;
    integer idle=0,blocked=0;
    reg printed=0;
    integer a,b;
    always @(posedge ut.clk) if(ut.rst_n) begin
        a=0;b=0;
        for(integer p=0;p<NPC;p=p+1) begin
            if(!ut.req_v[p]) a=a+1;
            if(ut.req_v[p] && !ut.req_rdy[p]) b=b+1;
        end
        idle<=idle+a;
        blocked<=blocked+b;
        if(!printed && ut.cycle>10 && !ut.busy) begin
            act=0;hit=0;conf=0;refresh=0;
            for(integer p=0;p<NPC;p=p+1) begin
                act=act+ut.hm.st_act[p];
                hit=hit+ut.hm.st_hit[p];
                conf=conf+ut.hm.st_conf[p];
                refresh=refresh+ut.hm.st_ref[p];
            end
            $display("V41X_SINGLE_DIAG act=%0d hit=%0d conf=%0d ref=%0d idle_pc_slots=%0d blocked_req_slots=%0d bp=%0d rd_lat_sum_ps=%0d rd_lat_max_ps=%0d",
                     act,hit,conf,refresh,idle,blocked,ut.hm.st_bp_cycles,
                     ut.hm.st_rd_lat_sum,ut.hm.st_rd_lat_max);
            printed<=1;
        end
    end
endmodule
