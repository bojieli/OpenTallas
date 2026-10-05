`timescale 1ns/1ps
// Default-off selected W12 instruction codec/acceptance boundary. NW18/AW24.
// Exact packing is ot_qwen_me_spine_w12.ib (379 bits), not the 1024-bit ISA.
// Cold POR is destructive. Warm reset closes new admission, drains every
// accepted beat and consumer obligation, and never resets accepted state.
// consumer_retire must come from actual result/ACK retirement, not array.ready.
// all_copy_drained must include both crossings/branches and late writes.
module ot_qwen_w12_instruction_transport_r1 #(
    parameter integer ENABLE_TWO_BEAT = 0
) (
    input wire clk, cold_por_n,
    input wire warm_request, warm_release, all_copy_drained,
    input wire in_valid, output wire in_ready, input wire [378:0] in_word,
    input wire beat_ready,
    output wire beat_valid, beat_last, output wire [189:0] beat_data,
    output wire consumer_valid, input wire consumer_ready,
    output wire [378:0] consumer_word, input wire consumer_retire,
    output wire warm_fence_done, fault, accepted_debt
);
    import ot_gpu_w6_secded_pkg::*;
    generate if (ENABLE_TWO_BEAT == 0) begin : g_original
        assign in_ready=consumer_ready && cold_por_n;
        assign consumer_valid=in_valid && cold_por_n;
        assign consumer_word=in_word;
        assign beat_valid=0; assign beat_last=0; assign beat_data=0;
        assign warm_fence_done=0; assign fault=0;
        assign accepted_debt=0; // bypass preserves original interface, no fence claim
    end else begin : g_selected
        // q0/q1 form a finite two-entry beat FIFO. assembly and control protected.
        reg [215:0] q0,q1;
        reg [431:0] assembly;
        reg [71:0] control;
        wire [65:0] dc=decode64(control);
        wire [1:0] phase=dc[1:0]; // 0 empty, 1 low beat, 2 high beat, 3 held
        wire issued=dc[2], warm=dc[3], bad=dc[4];
        reg [63:0] next_control;

        function automatic [215:0] enc190(input [189:0] d);
            reg [191:0] p;
            begin p={2'b0,d}; enc190={encode64(p[191:128]),encode64(p[127:64]),encode64(p[63:0])}; end
        endfunction
        // {uncorrectable,corrected,data190}
        function automatic [191:0] dec190(input [215:0] d);
            reg [65:0] a,b,c;
            begin
                a=decode64(d[71:0]); b=decode64(d[143:72]); c=decode64(d[215:144]);
                dec190={a[65]|b[65]|c[65],a[64]|b[64]|c[64],c[61:0],b[63:0],a[63:0]};
            end
        endfunction
        function automatic [431:0] enc379(input [378:0] d);
            reg [383:0] p; integer k;
            begin p={5'b0,d}; for(k=0;k<6;k=k+1) enc379[k*72+:72]=encode64(p[k*64+:64]); end
        endfunction
        // {uncorrectable,corrected,data379}
        function automatic [380:0] dec379(input [431:0] d);
            reg [383:0] p; reg [65:0] c; reg ue,fix; integer k;
            begin
                ue=0; fix=0;
                for(k=0;k<6;k=k+1) begin c=decode64(d[k*72+:72]); p[k*64+:64]=c[63:0]; ue=ue|c[65]; fix=fix|c[64]; end
                dec379={ue,fix,p[378:0]};
            end
        endfunction
        wire [191:0] dq=dec190(phase==2 ? q1:q0);
        wire [380:0] da=dec379(assembly);
        wire coding_bad=dc[65] || (phase==1 || phase==2 ? dq[191]:0) || (phase==2 || phase==3 ? da[380]:0);
        assign fault=bad || coding_bad;
        // A failed control decode cannot prove which phase owns accepted work.
        // Preserve quarantine even after the sticky fault itself is re-encoded.
        assign accepted_debt=(phase!=0) || fault;
        assign in_ready=cold_por_n && phase==0 && !warm && !warm_request && !fault;
        assign beat_valid=cold_por_n && (phase==1 || phase==2) && !fault;
        assign beat_last=phase==2;
        assign beat_data=dq[189:0];
        assign consumer_valid=cold_por_n && phase==3 && !issued && !fault;
        assign consumer_word=da[378:0];
        assign warm_fence_done=cold_por_n && warm && phase==0 && all_copy_drained && !fault;
        always @* begin
            next_control=dc[63:0];
            if(warm_request) next_control[3]=1;
            if(coding_bad) next_control[4]=1;
            if(consumer_retire && !(phase==3 && issued)) next_control[4]=1;
            if(warm_release) begin
                if(warm_fence_done && !warm_request) next_control[3]=0;
                else next_control[4]=1;
            end
            if(!fault) begin
                if(in_valid && in_ready) begin next_control[1:0]=1; next_control[2]=0; end
                if(beat_valid && beat_ready) next_control[1:0]=phase==1 ? 2:3;
                if(consumer_valid && consumer_ready) next_control[2]=1;
                if(consumer_retire && phase==3 && issued) begin next_control[1:0]=0; next_control[2]=0; end
            end
        end
        always @(posedge clk or negedge cold_por_n) begin
            if(!cold_por_n) control<=encode64(64'b0);
            else control<=encode64(next_control);
        end
        // Payload is never asynchronously reset. Validity/control owns visibility.
        always @(posedge clk) begin
            if(in_valid && in_ready) begin q0<=enc190(in_word[189:0]); q1<=enc190({1'b0,in_word[378:190]}); end
            if(beat_valid && beat_ready && phase==1) assembly<=enc379({189'b0,beat_data});
            if(beat_valid && beat_ready && phase==2) assembly<=enc379({beat_data[188:0],da[189:0]});
        end
    end endgenerate
endmodule
