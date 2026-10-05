`timescale 1ns/1ps
// Deterministic randomized stalls with two interleaved users and four
// exchanges at one position: three complete vectors and one explicit abort. Every beat,
// terminal status, FIFO bound, and stalled output is checked.
module tb_qwen_activation_handoff;
    localparam integer DATA_W=256, TXN_W=12, USER_W=3, POS_W=16, CUT_W=5, XCHG_W=8;
    // One 16 KiB opaque vector at 256 bits/beat, plus interleaved exchanges.
    localparam integer DEPTH=4, N=536, NT=4;
    localparam integer BEAT_W=DATA_W+TXN_W+USER_W+POS_W+CUT_W+XCHG_W+3;
    localparam integer DONE_W=TXN_W+USER_W+POS_W+CUT_W+XCHG_W+1;
    reg clk=0, rst_n=0;
    always #0.5 clk=~clk;

    reg s_valid=0, m_ready=0, done_ready=0;
    wire s_ready, m_valid, m_first, m_last, m_abort, done_valid, done_aborted, fault;
    wire [DATA_W-1:0] s_data,m_data;
    wire [TXN_W-1:0] s_txn,m_txn,done_txn;
    wire [USER_W-1:0] s_user,m_user,done_user;
    wire [POS_W-1:0] s_pos,m_pos,done_pos;
    wire [CUT_W-1:0] s_cut,m_cut,done_cut;
    wire [XCHG_W-1:0] s_exchange,m_exchange,done_exchange;
    wire s_first,s_last,s_abort;
    wire [$clog2(DEPTH+1)-1:0] level;

    reg [DATA_W-1:0] e_data [0:N-1];
    reg [TXN_W-1:0] e_txn [0:N-1];
    reg [USER_W-1:0] e_user [0:N-1];
    reg [POS_W-1:0] e_pos [0:N-1];
    reg [CUT_W-1:0] e_cut [0:N-1];
    reg [XCHG_W-1:0] e_exchange [0:N-1];
    reg e_first [0:N-1],e_last [0:N-1],e_abort [0:N-1];
    reg [DONE_W-1:0] e_done [0:NT-1];
    integer built=0, done_built=0;

    task automatic add_beat(input integer which, input integer beat_no,
                            input integer length, input bit abort_final);
        reg [31:0] word;
        reg [TXN_W-1:0] txn;
        reg [USER_W-1:0] user;
        reg [POS_W-1:0] pos;
        reg [CUT_W-1:0] cut;
        reg [XCHG_W-1:0] exchange;
        reg last,aborted;
        begin
            txn=TXN_W'(100+which);
            user=USER_W'(which[0]);
            pos=POS_W'(2047);
            cut=CUT_W'(7);
            exchange=XCHG_W'(which);
            word=32'hA509_6D3B ^ (which<<24) ^ (beat_no<<8) ^ built;
            last=(beat_no==length-1) && !abort_final;
            aborted=(beat_no==length-1) && abort_final;
            e_data[built]={8{word}};
            e_txn[built]=txn; e_user[built]=user;
            e_pos[built]=pos; e_cut[built]=cut; e_exchange[built]=exchange;
            e_first[built]=(beat_no==0);
            e_last[built]=last; e_abort[built]=aborted;
            if (last || aborted) begin
                e_done[done_built]={aborted,exchange,cut,pos,user,txn};
                done_built=done_built+1;
            end
            built=built+1;
        end
    endtask

    integer j;
    initial begin
        // Interleave beats within four tagged vectors. Transaction 2 aborts
        // after five accepted beats; the others transmit their whole vector.
        for (j=0;j<512;j=j+1) begin
            add_beat(0,j,512,0);
            if (j<12) add_beat(1,j,12,0);
            if (j<5) add_beat(2,j,5,1);
            if (j<7) add_beat(3,j,7,0);
        end
        if (built!=N || done_built!=NT) $fatal(1,"bad test schedule");
        repeat (4) @(posedge clk);
        @(negedge clk) rst_n=1;
    end

    integer sent=0,got=0,terminals_seen=0,done_got=0,aborts_seen=0,cycles=0,max_level=0;
    reg [1:0] users_seen=0;
    integer source_stalls=0,sink_stalls=0,status_stalls=0,terminal_wait=0;
    reg [31:0] rng=32'h71AC_E55D;
    reg prev_m_stall=0,prev_done_stall=0;
    reg [BEAT_W-1:0] prev_m;
    reg [DONE_W-1:0] prev_done;
    wire [BEAT_W-1:0] packed_m={m_abort,m_last,m_first,m_exchange,m_cut,m_pos,m_user,m_txn,m_data};
    wire [DONE_W-1:0] packed_done={done_aborted,done_exchange,done_cut,done_pos,done_user,done_txn};

    function automatic [31:0] next_rng(input [31:0] x);
        reg [31:0] y;
        begin
            y=x^(x<<13); y=y^(y>>17); next_rng=y^(y<<5);
        end
    endfunction

    assign s_data=(sent<N)?e_data[sent]:0;
    assign s_txn=(sent<N)?e_txn[sent]:0;
    assign s_user=(sent<N)?e_user[sent]:0;
    assign s_pos=(sent<N)?e_pos[sent]:0;
    assign s_cut=(sent<N)?e_cut[sent]:0;
    assign s_exchange=(sent<N)?e_exchange[sent]:0;
    assign s_first=(sent<N)?e_first[sent]:0;
    assign s_last=(sent<N)?e_last[sent]:0;
    assign s_abort=(sent<N)?e_abort[sent]:0;

    ot_qwen_activation_handoff #(.DATA_W(DATA_W),.TXN_W(TXN_W),.USER_W(USER_W),
        .POS_W(POS_W),.CUT_W(CUT_W),.XCHG_W(XCHG_W),.DEPTH(DEPTH)) dut (
        .clk(clk),.rst_n(rst_n),.s_valid(s_valid),.s_ready(s_ready),
        .s_data(s_data),.s_txn(s_txn),.s_user(s_user),.s_pos(s_pos),.s_cut(s_cut),
        .s_exchange(s_exchange),
        .s_first(s_first),.s_last(s_last),.s_abort(s_abort),
        .m_valid(m_valid),.m_ready(m_ready),.m_data(m_data),.m_txn(m_txn),
        .m_user(m_user),.m_pos(m_pos),.m_cut(m_cut),.m_exchange(m_exchange),.m_first(m_first),
        .m_last(m_last),.m_abort(m_abort),.done_valid(done_valid),
        .done_ready(done_ready),.done_txn(done_txn),.done_user(done_user),
        .done_pos(done_pos),.done_cut(done_cut),.done_exchange(done_exchange),
        .done_aborted(done_aborted),
        .level(level),.fault(fault));

    always @(posedge clk) if (rst_n) begin
        cycles<=cycles+1;
        rng<=next_rng(rng);
        m_ready<=rng[7:0]<8'd65;
        // Hold the completion sink through two terminal beats so the next
        // terminal must wait at the FIFO head, then apply random stalls.
        done_ready<=(cycles>=120) && (rng[15:8]<8'd42);
        if (!s_valid && sent<N && rng[23:16]<8'd230) s_valid<=1;
        if (s_valid && s_ready) begin sent<=sent+1; s_valid<=0; end
        if (s_valid && !s_ready) source_stalls<=source_stalls+1;
        if (m_valid && !m_ready) sink_stalls<=sink_stalls+1;
        if (done_valid && !done_ready) status_stalls<=status_stalls+1;
        if (dut.count!=0 && dut.terminal_head && dut.done_valid)
            terminal_wait<=terminal_wait+1;
        if (int'(level)>DEPTH || fault) $fatal(1,"FIFO bound/fault level=%0d fault=%0d",level,fault);
        if (int'(level)>max_level) max_level<=int'(level);
        if (prev_m_stall && (!m_valid || packed_m!==prev_m))
            $fatal(1,"payload changed under stall at beat %0d",got);
        if (prev_done_stall && (!done_valid || packed_done!==prev_done))
            $fatal(1,"completion changed under stall at status %0d",done_got);
        prev_m_stall<=m_valid && !m_ready;
        prev_done_stall<=done_valid && !done_ready;
        prev_m<=packed_m;
        prev_done<=packed_done;
        if (m_valid && m_ready) begin
            if (got>=N || packed_m!=={e_abort[got],e_last[got],e_first[got],
                                      e_exchange[got],e_cut[got],e_pos[got],e_user[got],e_txn[got],e_data[got]})
                $fatal(1,"beat mismatch/reorder at %0d",got);
            users_seen[m_user[0]]<=1'b1;
            if (m_last || m_abort) terminals_seen<=terminals_seen+1;
            got<=got+1;
        end
        if (done_valid && done_ready) begin
            if (done_got>=terminals_seen)
                $fatal(1,"completion before terminal beat at %0d",done_got);
            if (done_got>=NT || packed_done!==e_done[done_got])
                $fatal(1,"completion mismatch/reorder at %0d",done_got);
            if (done_aborted) aborts_seen<=aborts_seen+1;
            done_got<=done_got+1;
        end
        if (sent==N && got==N && done_got==NT && level==0 && !done_valid) begin
            if (max_level!=DEPTH || source_stalls==0 || sink_stalls==0 ||
                status_stalls==0 || terminal_wait==0 || aborts_seen!=1 || users_seen!=2'b11)
                $fatal(1,"insufficient stress max=%0d src=%0d sink=%0d status=%0d term=%0d",
                       max_level,source_stalls,sink_stalls,status_stalls,terminal_wait);
            $display("HANDOFF beats=%0d completions=%0d aborts=%0d users=%0d cycles=%0d max_level=%0d source_stalls=%0d sink_stalls=%0d status_stalls=%0d terminal_wait=%0d fault=%0d seed=71ace55d",
                     got,done_got,aborts_seen,int'(users_seen[0])+int'(users_seen[1]),
                     cycles,max_level,source_stalls,sink_stalls,
                     status_stalls,terminal_wait,fault);
            $display("PASS");
            $finish;
        end
        if (cycles>10000) $fatal(1,"timeout sent=%0d got=%0d done=%0d",sent,got,done_got);
    end
endmodule
