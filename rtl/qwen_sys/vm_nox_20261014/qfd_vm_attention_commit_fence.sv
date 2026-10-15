`timescale 1ns/1ps
// Compiler-owned visibility checker. Nothing here gates an issue, retries a write,
// or acknowledges elapsed time. A commit pulse requires the actual SRAM consume
// event for all16 words of the expected row in its reserved cycle.
module qfd_vm_attention_commit_fence #(
    parameter integer COMMIT_EDGES=8
)(
    input wire ck,rst_n,
    input wire request_slot,
    input wire [58:0] request_tag59,
    input wire write_v,
    input wire [4:0] write_beat,
    input wire [58:0] write_tag59,
    input wire visibility_slot,
    input wire [38:0] write_commit_v,
    input wire [311:0] write_commit_line,
    input wire [623:0] write_commit_mask,
    output reg vm_commit_v,
    output reg [4:0] vm_commit_beat,
    output reg [58:0] vm_commit_tag59,
    output wire complete,
    output reg fault
);
    reg active;
    reg [58:0] tag;
    reg [31:0] issued,covered;
    reg [COMMIT_EDGES-1:0] pending;
    reg [4:0] beat_pipe[0:COMMIT_EDGES-1];
    reg [58:0] tag_pipe[0:COMMIT_EDGES-1];
    integer i,b,n;
    reg actual,valid_event;
    reg [4:0] actual_beat;
    always @* begin
        n=0;actual=0;actual_beat=0;valid_event=1;
        // Q (line13) coexists; only ATTN's reserved line49 is checked here.
        for(b=7;b<39;b=b+1)if(write_commit_v[b] && write_commit_line[8*b+:8]==49)begin
            n=n+1;actual=1;actual_beat=5'(b-7);
            if(write_commit_mask[16*b+:16]!=16'hffff)valid_event=0;
        end
        if(n!=1)valid_event=0;
    end
    assign complete=active && (&covered) && !fault;
    always @(posedge ck or negedge rst_n)begin
        if(!rst_n)begin
            active<=0;tag<=0;issued<=0;covered<=0;pending<=0;
            vm_commit_v<=0;vm_commit_beat<=0;vm_commit_tag59<=0;fault<=0;
            for(i=0;i<COMMIT_EDGES;i=i+1)begin beat_pipe[i]<=0;tag_pipe[i]<=0;end
        end else begin
            vm_commit_v<=0;
            pending<={pending[COMMIT_EDGES-2:0],write_v};
            beat_pipe[0]<=write_beat;tag_pipe[0]<=write_tag59;
            for(i=1;i<COMMIT_EDGES;i=i+1)begin beat_pipe[i]<=beat_pipe[i-1];tag_pipe[i]<=tag_pipe[i-1];end
            if(request_slot)begin
                if((active && !(&covered)) || (|pending) || write_v || actual)fault<=1;
                active<=1;tag<=request_tag59;issued<=0;covered<=0;
            end
            if(write_v)begin
                if(!active || request_slot || write_tag59!=tag || issued[write_beat])fault<=1;
                issued[write_beat]<=1;
            end
            if(pending[COMMIT_EDGES-1] || actual)begin
                if(!active || request_slot || !pending[COMMIT_EDGES-1] || !actual || !valid_event ||
                    actual_beat!=beat_pipe[COMMIT_EDGES-1] || tag_pipe[COMMIT_EDGES-1]!=tag || covered[actual_beat])fault<=1;
                else begin
                    covered[actual_beat]<=1;
                    if(!fault)begin
                        vm_commit_v<=1;vm_commit_beat<=actual_beat;vm_commit_tag59<=tag_pipe[COMMIT_EDGES-1];
                    end
                end
            end
            // This is an explicit compiled slot, not a timer-generated success.
            if(visibility_slot && (!active || !(&issued) || !(&covered) || (|pending)))fault<=1;
        end
    end
`ifndef SYNTHESIS
    initial if(COMMIT_EDGES<2)$fatal(1,"COMMIT_EDGES must include the actual VM pipeline");
`endif
endmodule
