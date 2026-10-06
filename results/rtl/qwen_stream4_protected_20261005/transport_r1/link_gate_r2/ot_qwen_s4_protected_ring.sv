`timescale 1ns/1ps
// Finite, sealed mutable ring. Same 64/72 Hamming matrix as W6 and the W2
// static seal. Source reserves before the two-edge encoder, then publishes.
// Destination holds four checked stages. Retirement is separate from fetch;
// the write ring can hand off to a cache while its source debt stays owned.
// Warm reset is NOT connected to por_n. No accepted record is erased/replayed.
module ot_qwen_s4_protected_ring #(
    parameter integer WIDTH=281, DEPTH=64, PC_ID=0, KIND=0, SYNC=2,
    parameter integer WIRE_STAGES=0,
    parameter integer P=$clog2(DEPTH)+1,
    parameter integer PIECES=(WIDTH+1+43)/44,
    parameter integer CW=PIECES*72
) (
    input wire wr_clk, rd_clk, por_n,
    input wire allow_new,
    input wire wr_valid, output wire wr_ready,
    input wire [WIDTH-1:0] wr_data,
    output wire [P-1:0] wr_occupancy,
    output wire [P-1:0] retired_source,
    output wire retired_source_valid,
    output wire wr_fault,
    output wire rd_valid, input wire rd_ready,
    output wire [WIDTH-1:0] rd_data,
    output wire [P-1:0] rd_owner,
    input wire retire,
    output wire [P-1:0] retired,
    output wire rd_fault
);
    import ot_gpu_w6_secded_pkg::*;
    localparam integer A=P-1, E1W=PIECES*104+P+1;
    localparam integer D0W=CW+P+1, D1W=CW+PIECES*40+P+1;
    localparam integer D2W=CW+PIECES*8+P+1, D3W=WIDTH+P+2;
    initial if (SYNC!=2 || DEPTH<4 || (DEPTH&(DEPTH-1)) || PIECES*DEPTH>1024 || WIRE_STAGES<0)
        $fatal(1,"protected ring model geometry");
    // Duplicate the existing cold-release conditioner; neither warm request
    // nor the other domain's warm request enters these asynchronous resets.
    wire wr_r0,wr_r1,rd_r0,rd_r1;
    ot_reset_sync u_wr0(.clk(wr_clk),.async_rst_n(por_n),.sync_rst_n(wr_r0));
    ot_reset_sync u_wr1(.clk(wr_clk),.async_rst_n(por_n),.sync_rst_n(wr_r1));
    ot_reset_sync u_rd0(.clk(rd_clk),.async_rst_n(por_n),.sync_rst_n(rd_r0));
    ot_reset_sync u_rd1(.clk(rd_clk),.async_rst_n(por_n),.sync_rst_n(rd_r1));
    wire wr_online=wr_r0&&wr_r1, rd_online=rd_r0&&rd_r1;
    // Source has three pointers; destination additionally counts deliveries.
    // Fetch is not proof that a checked record reached its consumer/cache.
    wire [3*P:0] ws,wsi;
    wire [4*P:0] rs,rsi;
    wire ws_bad,rs_bad;
    wire [P-1:0] accept_bin=ws[0+:P],publish_bin=ws[P+:P],publish_gray=ws[2*P+:P];
    wire [P-1:0] fetch_bin=rs[0+:P],release_bin=rs[P+:P],release_gray=rs[2*P+:P];
    wire [P-1:0] delivered_bin=rs[3*P+:P];
    wire w_sticky=ws[3*P],r_sticky=rs[4*P];
    // Two rails cross independently. Only receiving stage2 is used, and only
    // while complementary. A metastability-induced rail disagreement stalls
    // conservatively; it is not a sticky fault, credit, or acknowledgment.
    (* async_reg="true", keep *) reg [P-1:0] rr0,rr1,ri0,ri1,ww0,ww1,wi0,wi1;
    wire rr_ok=(rr1==~ri1), ww_ok=(ww1==~wi1);
    wire [P-1:0] wire_release,wire_release_i,wire_publish,wire_publish_i;
    wire wire_receive_fault,wire_remote_fault;
    always @(posedge wr_clk or negedge por_n)
        if(!por_n)begin rr0<=0;rr1<=0;ri0<='1;ri1<='1;end
        else begin rr0<=wire_release;rr1<=rr0;ri0<=wire_release_i;ri1<=ri0;end
    always @(posedge rd_clk or negedge por_n)
        if(!por_n)begin ww0<=0;ww1<=0;wi0<='1;wi1<='1;end
        else begin ww0<=wire_publish;ww1<=ww0;wi0<=wire_publish_i;wi1<=wi0;end
    function automatic [P-1:0] gray_to_bin(input [P-1:0] g);
        integer k;begin gray_to_bin[P-1]=g[P-1];for(k=P-2;k>=0;k=k-1)gray_to_bin[k]=gray_to_bin[k+1]^g[k];end
    endfunction
    // The transmitted complement is formed from the stored inverse rail,
    // not a fresh inverter on a potentially corrupted primary pointer.
    // Access to each kept state's inverse also appears in the state census.
    wire [P-1:0] released_w=gray_to_bin(rr1), published_r=gray_to_bin(ww1);
    assign retired_source=released_w;
    assign retired_source_valid=rr_ok;
    assign wr_occupancy=accept_bin-released_w;
    wire [E1W-1:0] e1;
    wire e1_bad,d0_bad,d1_bad,d2_bad,d3_bad;
    wire [D0W-1:0] d0;
    wire [D1W-1:0] d1;
    wire [D2W-1:0] d2;
    wire [D3W-1:0] d3;
    wire ev=e1[E1W-1],v0=d0[D0W-1],v1=d1[D1W-1],v2=d2[D2W-1],v3=d3[D3W-1];
    assign wr_fault=ws_bad||e1_bad||w_sticky||enc_order_bad||wire_remote_fault;
    assign rd_fault=rs_bad||d0_bad||d1_bad||d2_bad||d3_bad||r_sticky||due_bad||delivery_order_bad||wire_receive_fault;
    assign wr_ready=wr_online&&rr_ok&&!wr_fault&&allow_new&&(wr_occupancy<DEPTH);
    wire accept=wr_valid&&wr_ready;
    // Encode cut1: raw64 + five partial8 parity/syndrome groups. Code-position
    // groups have <=15 XOR inputs; cut2 combines at most five partials.
    function automatic [71:0] scatter(input [63:0] raw);
        integer pos,k;begin scatter='0;k=0;for(pos=1;pos<=71;pos=pos+1)if((pos&(pos-1))!=0)begin scatter[pos-1]=raw[k];k=k+1;end end
    endfunction
    function automatic [39:0] partials(input [71:0] code);
        integer pos,g,k;begin partials='0;
        for(pos=1;pos<=72;pos=pos+1)begin
            g=(pos-1)/15;partials[g*8+7]=partials[g*8+7]^code[pos-1];
            if(pos<=71)for(k=0;k<7;k=k+1)if(pos&(1<<k))partials[g*8+k]=partials[g*8+k]^code[pos-1];
        end end
    endfunction
    function automatic [7:0] combine(input [39:0] parts);
        integer g;begin combine='0;for(g=0;g<5;g=g+1)combine=combine^parts[g*8+:8];end
    endfunction
    function automatic [19:0] seal(input [A-1:0] slot,input integer piece);
        seal={3'(KIND),10'(integer'(slot)*PIECES+piece),7'(PC_ID)};
    endfunction
    reg [E1W-1:0] e1_next;
    reg [PIECES*44-1:0] padded;
    reg [63:0] raw;
    integer k;
    always @* begin
        padded='0;padded[0+:WIDTH]=wr_data;padded[WIDTH]=accept_bin[P-1];
        e1_next='0;e1_next[E1W-1]=accept;e1_next[PIECES*104+:P]=accept_bin;
        for(integer b=0;b<PIECES;b=b+1)begin
            raw={seal(accept_bin[A-1:0],b),padded[b*44+:44]};
            e1_next[b*104+:64]=raw;e1_next[b*104+64+:40]=partials(scatter(raw));
        end
        if(!accept)e1_next='0;
    end
    ot_qwen_s4_checked_state #(.W(E1W)) u_e1(.clk(wr_clk),.por_n(por_n),.en(wr_online&&!wr_fault),.d(e1_next),.q(e1),.bad(e1_bad));
    reg [CW-1:0] encoded;
    reg [71:0] word;
    reg [7:0] parity;
    always @* begin
        encoded='0;
        for(integer b=0;b<PIECES;b=b+1)begin
            word=scatter(e1[b*104+:64]);parity=combine(e1[b*104+64+:40]);
            for(integer h=0;h<7;h=h+1)word[(1<<h)-1]=parity[h];
            word[71]=parity[7]^(^parity[6:0]);encoded[b*72+:72]=word;
        end
    end
    reg [CW-1:0] mem [0:DEPTH-1];
    wire [P-1:0] enc_owner=e1[PIECES*104+:P];
    wire commit=ev&&!wr_fault&&wr_online;
    generate if(WIRE_STAGES==0)begin:local_memory
        assign wire_release=release_gray;assign wire_release_i=rsi[2*P+:P];
        assign wire_publish=publish_gray;assign wire_publish_i=wsi[2*P+:P];
        assign wire_receive_fault=0;assign wire_remote_fault=0;
        always @(posedge wr_clk)if(commit)mem[enc_owner[A-1:0]]<=encoded;
    end else begin:wire_path
        // The entire wire uses the real source clock. Storage, publication
        // Gray and credit-source synchronizers are at the remote endpoint.
        // The existing read-domain SYNC2/checked decoder remains the CDC cut.
        // Payload stays sealed SECDED72 throughout every physical hop.
        wire [CW-1:0] code[0:WIRE_STAGES];
        wire [WIRE_STAGES:0] valid,poison;
        assign code[0]=encoded;assign valid[0]=commit;assign poison[0]=wr_fault;
        for(genvar s=0;s<WIRE_STAGES;s=s+1)begin:hop
            reg [CW-1:0] coded_q;
            wire [1:0] control;wire control_bad;
            // A failed node never replays its previously held valid record.
            // Its sticky poison propagates to the receiver on adjacent hops.
            ot_qwen_s4_checked_state #(.W(2)) u_control(.clk(wr_clk),.por_n(por_n),.en(1'b1),
                .d({poison[s]||control[1],valid[s]&&!poison[s]}),.q(control),.bad(control_bad));
            always @(posedge wr_clk)if(valid[s]&&!poison[s])coded_q<=code[s];
            assign code[s+1]=coded_q;
            assign valid[s+1]=control[0]&&!control_bad&&!control[1];
            assign poison[s+1]=control_bad||control[1];
        end
        wire [2*P:0] arrived,arrived_i;wire arrived_bad;
        wire [P-1:0] arrived_bin=arrived[0+:P];
        wire release_here_ok=(cr1==~ci1);
        wire [P-1:0] release_here=gray_to_bin(cr1);
        wire arrival_overflow=valid[WIRE_STAGES]&&release_here_ok&&((arrived_bin-release_here)>=DEPTH);
        wire arrival_fault=arrived_bad||arrived[2*P]||poison[WIRE_STAGES]||arrival_overflow;
        wire arrival_take=valid[WIRE_STAGES]&&!arrival_fault;
        wire [P-1:0] arrived_next=arrived_bin+P'(arrival_take);
        // Release is only used for this diagnostic through the checked local
        // source-clock synchronizer below. The source-owned capacity bound is
        // authoritative; no unsynchronized read pointer authorizes a write.
        ot_qwen_s4_checked_state #(.W(2*P+1)) u_arrived(.clk(wr_clk),.por_n(por_n),.en(!arrived_bad),
            .d({arrived[2*P]||poison[WIRE_STAGES]||arrival_overflow,(arrived_next>>1)^arrived_next,arrived_next}),
            .q(arrived),.qi(arrived_i),.bad(arrived_bad));
        always @(posedge wr_clk)if(arrival_take)mem[arrived_bin[A-1:0]]<=code[WIRE_STAGES];
        assign wire_publish=arrived[P+:P];assign wire_publish_i=arrived_i[P+:P];
        assign wire_receive_fault=arrival_fault;
        (* async_reg="true", keep *) reg [P-1:0] cr0,cr1,ci0,ci1;
        (* async_reg="true", keep *) reg cf0,cf1,cfi0,cfi1;
        always @(posedge wr_clk or negedge por_n)
            if(!por_n)begin cr0<=0;cr1<=0;ci0<='1;ci1<='1;cf0<=0;cf1<=0;cfi0<=1;cfi1<=1;end
            else begin cr0<=release_gray;cr1<=cr0;ci0<=rsi[2*P+:P];ci1<=ci0;
                cf0<=rd_fault;cf1<=cf0;cfi0<=!rd_fault;cfi1<=cfi0;end
        wire [2*P+1:0] credit[0:WIRE_STAGES];
        assign credit[0]={cfi1,cf1,ci1,cr1};
        for(genvar s=0;s<WIRE_STAGES;s=s+1)begin:credit_hop
            wire [2*P+1:0] cq;wire cb;
            ot_qwen_s4_checked_state #(.W(2*P+2)) u_credit(.clk(wr_clk),.por_n(por_n),.en(1'b1),
                .d(credit[s]),.q(cq),.bad(cb));
            // Preserve invalid rails through subsequent captures. A node's
            // own upset cannot become a newly valid credit at its neighbor.
            assign credit[s+1]=cb?{1'b0,1'b1,{2*P{1'b0}}}:cq;
        end
        assign wire_release=credit[WIRE_STAGES][0+:P];
        assign wire_release_i=credit[WIRE_STAGES][P+:P];
        assign wire_remote_fault=(credit[WIRE_STAGES][2*P+1:2*P]==2'b01);
    end endgenerate
    wire [P-1:0] ab_next=accept_bin+P'(accept),pb_next=publish_bin+P'(commit);
    wire enc_order_bad=ev&&(enc_owner!=publish_bin);
    ot_qwen_s4_checked_state #(.W(3*P+1)) u_ws(.clk(wr_clk),.por_n(por_n),.en(wr_online&&!ws_bad&&!e1_bad),
        .d({w_sticky||enc_order_bad,(pb_next>>1)^pb_next,pb_next,ab_next}),.q(ws),.qi(wsi),.bad(ws_bad));
    // Four read cuts, advanced together or held. A bad output cannot retire;
    // its complete owner and source slot remain occupied through quarantine.
    wire advance=rd_online&&!rd_fault&&(!v3||rd_ready);
    wire fetch=advance&&ww_ok&&(fetch_bin!=published_r);
    wire [P-1:0] fetch_next=fetch_bin+P'(fetch);
    wire delivery_order_bad=v3&&(rd_owner!=delivered_bin);
    wire delivered_now=rd_valid&&rd_ready;
    wire [P-1:0] delivered_next=delivered_bin+P'(delivered_now);
    wire retire_ok=retire&&!rd_fault&&(release_bin!=delivered_next);
    wire [P-1:0] release_next=release_bin+P'(retire_ok);
    wire bad_retire=retire&&(release_bin==delivered_next);
    ot_qwen_s4_checked_state #(.W(4*P+1)) u_rs(.clk(rd_clk),.por_n(por_n),.en(rd_online&&!rd_fault),
        .d({r_sticky||bad_retire,delivered_next,(release_next>>1)^release_next,release_next,fetch_next}),.q(rs),.qi(rsi),.bad(rs_bad));
    assign retired=release_bin;
    ot_qwen_s4_checked_state #(.W(D0W)) u_d0(.clk(rd_clk),.por_n(por_n),.en(advance),
        .d(fetch ? {1'b1,fetch_bin,mem[fetch_bin[A-1:0]]} : {D0W{1'b0}}),.q(d0),.bad(d0_bad));
    reg [D1W-1:0] d1_next;
    always @* begin
        d1_next='0;d1_next[0+:CW]=d0[0+:CW];d1_next[CW+PIECES*40+:P+1]=d0[CW+:P+1];
        for(integer b=0;b<PIECES;b=b+1)d1_next[CW+b*40+:40]=partials(d0[b*72+:72]);
    end
    ot_qwen_s4_checked_state #(.W(D1W)) u_d1(.clk(rd_clk),.por_n(por_n),.en(advance),.d(d1_next),.q(d1),.bad(d1_bad));
    reg [D2W-1:0] d2_next;
    always @* begin
        d2_next='0;d2_next[0+:CW]=d1[0+:CW];d2_next[CW+PIECES*8+:P+1]=d1[CW+PIECES*40+:P+1];
        for(integer b=0;b<PIECES;b=b+1)d2_next[CW+b*8+:8]=combine(d1[CW+b*40+:40]);
    end
    ot_qwen_s4_checked_state #(.W(D2W)) u_d2(.clk(rd_clk),.por_n(por_n),.en(advance),.d(d2_next),.q(d2),.bad(d2_bad));
    wire [P-1:0] dec_owner=d2[CW+PIECES*8+:P];
    reg [PIECES*44-1:0] decoded_payload;
    reg [71:0] fixed_word;
    reg [63:0] fixed_raw;
    reg [7:0] syn;
    reg decode_bad;
    integer data_index;
    always @* begin
        decoded_payload='0;decode_bad=0;fixed_word='0;fixed_raw='0;syn='0;data_index=0;
        for(integer b=0;b<PIECES;b=b+1)begin
            fixed_word=d2[b*72+:72];syn=d2[CW+b*8+:8];
            if(syn[6:0]!=0)begin
                if(syn[7]&&syn[6:0]<=71)fixed_word[syn[6:0]-1]=~fixed_word[syn[6:0]-1];
                else decode_bad=1;
            end else if(syn[7])fixed_word[71]=~fixed_word[71];
            fixed_raw='0;data_index=0;
            for(integer pos=1;pos<=71;pos=pos+1)if((pos&(pos-1))!=0)begin fixed_raw[data_index]=fixed_word[pos-1];data_index=data_index+1;end
            if(fixed_raw[63:44]!=seal(dec_owner[A-1:0],b))decode_bad=1;
            decoded_payload[b*44+:44]=fixed_raw[43:0];
        end
        if(decoded_payload[WIDTH]!=dec_owner[P-1])decode_bad=1;
        for(integer b=WIDTH+1;b<PIECES*44;b=b+1)if(decoded_payload[b])decode_bad=1;
    end
    wire due_bad=v2&&decode_bad;
    // UE stays in stage2; it never produces valid output or returns a source
    // slot. The held stage2 code and owner preserve the fault and debt.
    wire [D3W-1:0] d3_next={v2&&!decode_bad,dec_owner,decoded_payload[WIDTH:0]};
    ot_qwen_s4_checked_state #(.W(D3W)) u_d3(.clk(rd_clk),.por_n(por_n),.en(advance&&!due_bad),.d(d3_next),.q(d3),.bad(d3_bad));
    assign rd_valid=v3&&!rd_fault&&!due_bad;
    assign rd_data=d3[WIDTH-1:0];assign rd_owner=d3[WIDTH+1+:P];
    // A decode UE prevents this edge's pipeline advance immediately. It is
    // retained independently of warm reset in the held reader pipeline.
endmodule
