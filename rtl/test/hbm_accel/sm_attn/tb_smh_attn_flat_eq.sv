`timescale 1ns/1ps
// HF-5c 10-18: random lockstep ot_hbm_accel_smh_attn (generate form) vs ot_hbm_accel_smh_attn_flat (wires-only flat form,
// front split into launch + result halves, be_cmd glue child).  Same reset, same inputs, every output compared every
// cycle from the first edge after reset release (offset 0: the flat form adds no register).
// EMUT (negative control): 1 = the reference runs BE_DELAY 9 (one BE control stage more) -> must FAIL;
//                          2 = the reference runs HOPD 5 (per-hop BE control delay +1)        -> must FAIL.
module tb_smh_attn_flat_eq;
    parameter integer EMUT = 0;
    parameter integer CYCLES = 6000;
    reg clk = 1'b0;  always #0.5 clk = ~clk;
    reg rst_n = 1'b0;
    reg [191:0] command; reg [63:0] kv_desc; reg [1098:0] packet;
    reg xw_en; reg [6:0] xw_addr, xw_grp; reg [2047:0] xw_data;
    wire [42:0] req_a, req_b; wire rv_a, rv_b, f_a, f_b, sf_a, sf_b; wire [11:0] rr_a, rr_b; wire [255:0] rd_a, rd_b;
    ot_hbm_accel_smh_attn #(.BE_DELAY(EMUT == 1 ? 9 : 8), .HOPD(EMUT == 2 ? 5 : 4)) u_ref (.clk(clk), .rst_n(rst_n),
        .command(command), .kv_desc(kv_desc), .packet(packet), .request(req_a), .xw_en(xw_en), .xw_addr(xw_addr),
        .xw_grp(xw_grp), .xw_data(xw_data), .rv(rv_a), .rrow(rr_a), .rdata(rd_a), .fault(f_a), .schedule_fault(sf_a));
    ot_hbm_accel_smh_attn_flat u_flat (.clk(clk), .rst_n(rst_n),
        .command(command), .kv_desc(kv_desc), .packet(packet), .request(req_b), .xw_en(xw_en), .xw_addr(xw_addr),
        .xw_grp(xw_grp), .xw_data(xw_data), .rv(rv_b), .rrow(rr_b), .rdata(rd_b), .fault(f_b), .schedule_fault(sf_b));
    integer cyc, nc, bad, nrv;
    task automatic rnd_inputs;
        integer k;
        begin
            for (k = 0; k < 6; k = k + 1) command[32*k +: 32] = $urandom;
            // half of the cycles carry the 0xa2 magic so the revisioned front parses them (the rest are fault traffic)
            if ($urandom % 2) command[191:184] = 8'ha2;
            kv_desc = {$urandom, $urandom};
            for (k = 0; k < 34; k = k + 1) packet[32*k +: 32] = $urandom;
            packet[1098:1088] = $urandom;
            xw_en = $urandom; xw_addr = $urandom; xw_grp = $urandom % 13;
            for (k = 0; k < 64; k = k + 1) xw_data[32*k +: 32] = $urandom;
        end
    endtask
    initial begin
        nc = 0; bad = 0; nrv = 0;
        command = 0; kv_desc = 0; packet = 0; xw_en = 0; xw_addr = 0; xw_grp = 0; xw_data = 0;
        for (cyc = 0; cyc < CYCLES; cyc = cyc + 1) begin
            @(negedge clk);
            if (cyc == 16) rst_n = 1'b1;
            if (cyc > 20) rnd_inputs;
            if (cyc > 17) begin
                nc = nc + 1;
                if (rv_b) nrv = nrv + 1;
                if ({req_a, rv_a, rr_a, rd_a, f_a, sf_a} !== {req_b, rv_b, rr_b, rd_b, f_b, sf_b}) begin
                    bad = bad + 1;
                    if (bad <= 5) $display("EQ_MISMATCH cycle=%0d req %h/%h rv %b/%b rrow %h/%h rdata %h/%h fault %b/%b sfault %b/%b",
                        cyc, req_a, req_b, rv_a, rv_b, rr_a, rr_b, rd_a, rd_b, f_a, f_b, sf_a, sf_b);
                end
            end
        end
        if (bad == 0 && nc > 0) $display("FLAT_EQ PASS EMUT=%0d compared=%0d rv_cycles=%0d", EMUT, nc, nrv);
        else $display("FLAT_EQ FAIL EMUT=%0d mismatches=%0d of %0d rv_cycles=%0d", EMUT, bad, nc, nrv);
        $finish;
    end
endmodule
