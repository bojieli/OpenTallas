`timescale 1ns/1ps
`default_nettype none
// Six fixed launches of REAL KS descriptors. This is an opt-in adapter on the
// existing HOST_EN=1 path, not a token generator or a completion-driven issuer.
// SYNC CSR 0x19 first supplies graph tag d[39:8] and global capture-edge
// timestamp d[87:40]. A real local counter then advances that explicit epoch;
// ARM's epoch must match it exactly. No global-zero assumption is made.
// ARM CSR 0x17 (class 0, d=f_host[512:1]):
// d[39:8] graph tag; [87:40] absolute epoch AT THIS CSR CAPTURE EDGE;
// [135:88] first KS capture edge at the original seqhost input;
// [183:136] first issuer-command edge from the actual stage programme;
// [193:184] owner; [195:194] actual issuer phase at the epoch edge.
// The actual PW row-0 issue age and seal phase are observed on the same host
// path. No default global epoch, descriptor token, or position is synthesized.
// The host must account for its real transport latency when constructing ARM.
// Six KS descriptors arriving AFTER ARM are retained unchanged and emitted at
// first_ks + n*SPAN. Missing/late data faults; it never moves a deadline.
module dsdv_static_ks6 #(
    parameter integer SPAN = 1259408,
    parameter [31:0] GRAPH_TAG = 32'h218d375d,
    parameter integer NOPS = 128
) (
    input wire ck, rst_n,
    input wire [514:0] f_host,
    input wire [52:0] f_ks,
    input wire upstream_fault,
    output wire [52:0] timed_ks,
    output reg selected,
    output reg armed,
    output reg done,
    output reg [3:0] fault
);
    wire hv = f_host[0];
    wire [511:0] hd = f_host[512:1];
    wire csr = hv && f_host[514:513] == 2'd0;
    wire arm = csr && hd[7:0] == 8'h17;
    wire disarm = csr && hd[7:0] == 8'h18;
    wire sync_epoch = csr && hd[7:0] == 8'h19;
    wire pw = csr && hd[7:0] == 8'h10;
    wire [6:0] pa = hd[102:96];
    wire [27:0] pd = hd[59:32];
    wire prog_write = csr && (hd[7:0] == 8'h10 || hd[7:0] == 8'h11 ||
                                      hd[7:0] == 8'h13 || hd[7:0] == 8'h14);
    wire [23:0] first_issue;
    reg first_seen, sealed, prog_len_seen;
    reg [7:0] prog_len, settle;
    reg [1:0] seal_phase;
    reg epoch_valid;
    wire [47:0] global_edge;
    reg [9:0] owner;
    // 312 payload bits: below the 2-kbit SRAM threshold. Data is unreset.
    reg timed_valid;
    assign timed_ks[52]=timed_valid;
    wire descriptor_write = !arm && fault == 0 && !immediate_bad && selected && armed && f_ks[52];
    genvar bank;
    generate for (bank=0;bank<4;bank=bank+1) begin : g_descriptor_bank
        // Each independent 13-bit selector has at most26 dynamic contacts
        // on a select root. Preserve hierarchy so identical decode cones stay
        // local to their actual narrow storage bank, with no added edge.
        (* keep_hierarchy = "yes" *) dsdv_static_ks6_bank13 u_data (
            .ck(ck), .we(descriptor_write), .active(running),
            .wait_one(wait_edges==1), .rd_ok(rd<6), .valid_rd(valid[rd]), .arm_good(arm_good),
            .advance(descriptor_emit && rd!=5), .wr(wr),
            .d(f_ks[13*bank+:13]), .q(timed_ks[13*bank+:13]));
    end endgenerate
    reg [5:0] valid;
    reg [2:0] wr, rd;
    wire [23:0] wait_edges;
    wire [47:0] epoch = hd[87:40];
    wire [47:0] first_ks = hd[135:88];
    wire [47:0] first_cmd = hd[183:136];
    wire [47:0] delta = first_ks - epoch;
    // Issuer samples KS at +3 and accepts only when phase_q+1 equals
    // the sealed start phase: +4 is zero modulo the four-phase cycle.
    wire [1:0] expected_phase = hd[195:194] + delta[1:0];
    wire bad_arm = hd[39:8] != GRAPH_TAG || !epoch_valid || epoch != global_edge || first_ks <= epoch ||
                   delta[47:24] != 0 || delta < 3 || !first_seen || !sealed || settle != 0 ||
                   first_cmd != first_ks + 48'd4 + {24'd0, first_issue} ||
                   expected_phase != seal_phase || (selected && !done) || f_ks[52];
    wire bad_desc = selected && f_ks[52] &&
                    (!armed || wr >= 6 || f_ks[51:42] != owner);
    wire config_race = selected && armed && (prog_write || sync_epoch);
    wire immediate_bad = upstream_fault || bad_desc || config_race || (arm && bad_arm);
    wire arm_good=arm && !bad_arm && fault==0 && !upstream_fault;
    wire running=!arm && fault==0 && !immediate_bad && selected && armed;
    wire descriptor_emit=running && wait_edges==1 && rd<6 && valid[rd];
    wire wait_dec=running && wait_edges>1;
    wire wait_reload=descriptor_emit && rd!=5;
    wire [23:0] initial_wait=delta[23:0]-1'b1;
    wire [47:0] sync_value=hd[87:40]+1'b1;
    // Wide data is unreset and valid only after its explicit producer writes:
    // SYNC for epoch, ARM for owner/countdown, row0 for first issue, seal for
    // settle, and timed_valid for the opaque output. Reset only control state.
    genvar rg;
    generate for(rg=0;rg<4;rg=rg+1) begin:g_epoch
        (* keep_hierarchy="yes" *) dsdv_static_ks6_epoch12 u_epoch(
            .ck(ck),.sync(sync_epoch),.selected_armed(selected && armed),
            .tag_ok(hd[39:8]==GRAPH_TAG),.rst_n(rst_n),
            .carry(&(global_edge | (48'hffffffffffff << (12*rg)))),
            .d(sync_value[12*rg+:12]),.q(global_edge[12*rg+:12]));
    end
    for(rg=0;rg<2;rg=rg+1) begin:g_wide
        (* keep_hierarchy="yes" *) dsdv_static_ks6_load12 u_first(
            .ck(ck),.pw(pw),.pa_zero(pa==0),.kind_one(pd[27:26]==1),.d(pd[2+12*rg+:12]),.q(first_issue[12*rg+:12]));
        (* keep_hierarchy="yes" *) dsdv_static_ks6_wait12 #(.RELOAD((SPAN>>(12*rg)) & 4095)) u_wait(
            .ck(ck),.arm(arm),.bad_arm(bad_arm),.fault_clear(fault==0),
            .upstream_fault(upstream_fault),.reload(wait_reload),.dec(wait_dec),
            .borrow(rg==0 ? 1'b1 : wait_edges[11:0]==0),
            .d(initial_wait[12*rg+:12]),.q(wait_edges[12*rg+:12]));
    end endgenerate
    always @(posedge ck) begin
        if (csr && hd[7:0]==8'h11) prog_len<=hd[39:32];
        if (arm_good) begin owner <= hd[193:184]; wr<=0; rd<=0; end
        else if (running) begin
            if(f_ks[52]) wr<=wr+1'b1;
            if(descriptor_emit && rd!=5) rd<=rd+1'b1;
        end
        if (settle != 0) settle <= settle - 1'b1;
        if (pw && pd[27:26]==3 && !pd[25]) settle <= 0;
        if (pw && pd[27:26]==3 && pd[25]) settle <= NOPS+16;
    end
    initial begin
        if (SPAN < 4 || SPAN >= (1<<24) || (SPAN % 4) != 0 || NOPS > 239)
            $fatal(1, "static KS: invalid immutable schedule parameters");
    end
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            timed_valid <= 0; selected <= 0; armed <= 0; done <= 0; fault <= 0;
            valid <= 0;
            first_seen <= 0; sealed <= 0; prog_len_seen <= 0;
            seal_phase <= 0;
            epoch_valid <= 0;
        end else begin
            timed_valid <= 0;
            if (sync_epoch && !(selected && armed)) begin
                if (hd[39:8] != GRAPH_TAG) begin fault[1] <= 1; epoch_valid <= 0; end
                else begin
                    epoch_valid <= 1;
                    // global_edge represents the NEXT capture edge after
                    // SYNC, hence the +1 on the synchronizing edge itself.
                end
            end
            if (csr && hd[7:0] == 8'h11) prog_len_seen <= 1;
            if (pw && pd[27:26] == 3 && !pd[25]) begin
                first_seen <= 0; sealed <= 0;
            end
            if (pw && pa == 0 && pd[27:26] == 1) begin
                first_seen <= 1;
            end
            if (pw && pd[27:26] == 3 && pd[25]) begin
                sealed <= first_seen && prog_len_seen && prog_len != 0 && prog_len == pd[16:9];
                seal_phase <= pd[8:7];
                // The real walker performs a one-row/edge seal scan. This
                // conservative fixed BOOT guard covers its staging; it does
                // not delay a token or wait for a completion.
            end
            if (upstream_fault && selected) fault[3] <= 1;
            if (bad_desc) fault[0] <= 1;
            if (config_race) fault[1] <= 1;
            if (arm) begin
                selected <= 1;
                if (bad_arm || fault != 0 || upstream_fault) begin
                    fault[1] <= 1; armed <= 0;
                end else begin
                    valid <= 0;
                    armed <= 1; done <= 0;
                end
            end else if (fault != 0 || immediate_bad) begin
                armed <= 0;
            end else if (selected && armed) begin
                if (f_ks[52]) begin
                    valid[wr] <= 1;
                end
                if (wait_edges == 1) begin
                    // Registered output is sampled by the original seqhost
                    // on the following edge: exactly the declared KS edge.
                    if (rd >= 6 || !valid[rd]) begin
                        fault[0] <= 1; armed <= 0;
                    end else begin
                        timed_valid <= 1;
                        valid[rd] <= 0;
                        if (rd == 5) begin armed <= 0; done <= 1; end
                    end
                end
            end
            if (disarm) begin
                if (done && !armed && fault == 0) begin selected <= 0; done <= 0; end
                else begin fault[2] <= 1; armed <= 0; end
            end
        end
    end
endmodule
// Six opaque descriptors; payload unreset and below2kbit. Fixed slots and
// explicit onehot read selection replace variable wide part-select barrels.
(* keep_hierarchy = "yes" *)
module dsdv_static_ks6_bank13 (
    input wire ck,we,active,wait_one,rd_ok,valid_rd,arm_good,advance,
    input wire [2:0] wr,
    input wire [12:0] d,
    output reg [12:0] q
);
    reg [2:0] rd;
    always @(posedge ck) if(arm_good) rd<=0; else if(advance) rd<=rd+1'b1;
    wire emit=active && wait_one && rd_ok && valid_rd;
    reg [12:0] word0,word1,word2,word3,word4,word5;
    always @(posedge ck) begin
        if (we && wr==0) word0<=d;
        if (we && wr==1) word1<=d;
        if (we && wr==2) word2<=d;
        if (we && wr==3) word3<=d;
        if (we && wr==4) word4<=d;
        if (we && wr==5) word5<=d;
    end
    wire [12:0] chosen=({13{rd==0}}&word0)|({13{rd==1}}&word1)|
             ({13{rd==2}}&word2)|({13{rd==3}}&word3)|
             ({13{rd==4}}&word4)|({13{rd==5}}&word5);
    always @(posedge ck) q <= emit ? chosen : 13'd0;
endmodule
(* keep_hierarchy="yes" *)
module dsdv_static_ks6_epoch12(input wire ck,sync,selected_armed,tag_ok,rst_n,carry,input wire[11:0] d,output reg[11:0] q);
    reg inc;
    always @(posedge ck or negedge rst_n)
        if(!rst_n) inc<=0; else if(sync && !selected_armed) inc<=tag_ok;
    wire load=sync && !selected_armed && tag_ok;
    always @(posedge ck) if(load) q<=d; else if(inc) q<=q+carry;
endmodule
(* keep_hierarchy="yes" *)
module dsdv_static_ks6_load12(input wire ck,pw,pa_zero,kind_one,input wire[11:0] d,output reg[11:0] q);
    wire load=pw && pa_zero && kind_one;
    always @(posedge ck) if(load) q<=d;
endmodule
(* keep_hierarchy="yes" *)
module dsdv_static_ks6_wait12 #(parameter[11:0] RELOAD=0)
(input wire ck,arm,bad_arm,fault_clear,upstream_fault,reload,dec,borrow,input wire[11:0] d,output reg[11:0] q);
    wire load=arm && !bad_arm && fault_clear && !upstream_fault;
    always @(posedge ck) if(load) q<=d; else if(reload) q<=RELOAD; else if(dec) q<=q-borrow;
endmodule
`default_nettype wire
