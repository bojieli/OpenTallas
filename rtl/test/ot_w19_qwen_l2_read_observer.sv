`timescale 1ns/1ps
// Passive simulation-only fixture adapter. Never instantiate in production.
// Model: w19_qwen_hbm_l2_read_observer_preflight.json, 2x4x8 bank reads.
// No outputs, expected-data memory, numerical work, or DUT input injection.
module ot_w19_qwen_l2_read_observer #(
    parameter integer ENABLE_OBSERVER=0
) (
    input wire clk, rst_n,
    input wire [63:0] read_v, read_ready,
    input wire [64*18-1:0] canonical_row,
    input wire [64*16-1:0] local_row, read_epoch,
    input wire [64*32-1:0] read_data,
    input wire [15:0] expected_epoch,
    input wire DUT_fault,
    input wire finish_capture
);
    reg [3071:0] seen[0:1];
    integer trace_fd, cycle, count, p, die, producer, row, local_index;
    reg [1023:0] trace_path;
    initial begin
        trace_fd=0; cycle=0; count=0;
        seen[0]=0; seen[1]=0;
        if (ENABLE_OBSERVER) begin
            if (!$value$plusargs("W19_READ_TRACE=%s", trace_path))
                $fatal(1,"observer requires explicit trace path");
            // Caller must choose a new path; preserve prior attempts.
            trace_fd=$fopen(trace_path,"r");
            if (trace_fd) begin $fclose(trace_fd); $fatal(1,"trace already exists"); end
            trace_fd=$fopen(trace_path,"w");
            if (!trace_fd) $fatal(1,"cannot create trace");
        end
    end
    always @(posedge clk) if (ENABLE_OBSERVER) begin
        if (!rst_n) begin
            seen[0]=0;seen[1]=0;count=0;cycle=0;
        end else begin
            if (DUT_fault !== 1'b0) $fatal(1,"DUT fault or unknown");
            if ((^{read_v,read_ready,finish_capture}) === 1'bx)
                $fatal(1,"unknown handshake");
            for (p=0;p<64;p=p+1) if (read_v[p] && read_ready[p]) begin
                die=p/32;producer=p%32;
                if ((^{canonical_row[p*18+:18],local_row[p*16+:16],
                       read_epoch[p*16+:16],read_data[p*32+:32],expected_epoch}) === 1'bx)
                    $fatal(1,"unknown accepted metadata or data");
                row=canonical_row[p*18+:18]; local_index=local_row[p*16+:16];
                if (local_index>=96 || row!=producer*96+local_index ||
                    read_epoch[p*16+:16]!=expected_epoch)
                    $fatal(1,"read identity/epoch port%0d row%0d",p,row);
                if (seen[die][row]) $fatal(1,"duplicate accepted read");
                seen[die][row]=1;count=count+1;
                $fdisplay(trace_fd,"{\"die\":%0d,\"boundary\":\"raw_qkv_bits\",\"index\":%0d,\"bits\":%0d,\"cycle\":%0d,\"fault\":0}",
                          die,row,read_data[p*32+:32],cycle);
            end
            cycle=cycle+1;
            if (finish_capture) begin
                if (count!=6144 || !(&seen[0]) || !(&seen[1]))
                    $fatal(1,"incomplete full32SM read census count%0d",count);
                $fclose(trace_fd);trace_fd=0;
                $display("PASS PASSIVE_READ_OBSERVER rows=%0d cycles=%0d",count,cycle);
            end
        end
    end
endmodule
