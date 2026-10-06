`timescale 1ns/1ps
module tb_cfgrom_context;
    reg clk=0;
    always #0.416667 clk=~clk;
    reg rst_n=0, cfg_go=0, go=0, sh_free=1, bank_free=1;
    reg [5:0] phase=0;
    reg [2:0] np=0;
    wire [1:0] cv, rv, ge, rge, busy, rbusy, fault, rfault, ce;
    wire [4:0] ca[2], ra[2];
    wire [47:0] cd[2], rd[2];
    wire [10:0] addr[2], raddr[2];
    wire [11:0] read_addr[2];
    integer checks[2], words_seen[2], reads[2], admissions[2], faults[2];
    reg [47:0] payload[0:1599];
    function automatic [47:0] word_at(input integer a);
        reg [47:0] w;
        begin
            // Nonzero, address-distinct fixture; 24 spare physical bits unused.
            w = {16'(a^16'hb51d), 16'(a*37+19), 16'(a*73+7)};
            if (a%25>=8 && a%25<16) w[0]=1'b1;
            word_at=w;
        end
    endfunction
    for (genvar p=0;p<2;p++) begin : g
        ot_v41_pair_pq_ld_frontend #(.PHW(6),.PQ(p)) ref_ld (
            .clk(clk),.rst_n(rst_n),.cfg_go(cfg_go),.cfg_ph(phase),.cfg_np(np),
            .go(go),.e_sh_free(sh_free),.e_bank_free(bank_free),
            .cm_a(raddr[p]),.cm_q(payload[raddr[p]]),.c_v(rv[p]),.c_a(ra[p]),.c_d(rd[p]),
            .go_e(rge[p]),.ld_busy(rbusy[p]),.fault(rfault[p])
        );
        ot_v41_pair_cfgrom_context #(.HARD_CFG(1),.PQ(p)) dut (
            .clk(clk),.rst_n(rst_n),.cfg_go(cfg_go),.cfg_ph(phase),.cfg_np(np),
            .go(go),.e_sh_free(sh_free),.e_bank_free(bank_free),.external_cfg_q(48'hbad),
            .cfg_rom_a(addr[p]),.cfg_rom_read_a(read_addr[p]),.cfg_rom_read_ce(ce[p]),
            .c_v(cv[p]),.c_a(ca[p]),.c_d(cd[p]),.go_e(ge[p]),.ld_busy(busy[p]),.fault(fault[p])
        );
        initial begin
            checks[p]=0;words_seen[p]=0;reads[p]=0;admissions[p]=0;faults[p]=0;
            #0.001;
            for (int a=0;a<1600;a++) begin
                for (int b=0;b<48;b++)
                    dut.g_hard_cfg.u_cfg.arr[a/8][b*8+a%8]=(word_at(a)>>b)&1;
            end
        end
        always @(posedge clk) begin
            if (rst_n && ce[p]) begin
                if (read_addr[p]>=1600) $fatal(1,"ROM address bounds PQ%0d",p);
                reads[p]++;
            end
            #0.001;
            if (rst_n) begin
                checks[p]++;
                if ({cv[p],ge[p],busy[p],fault[p]} !== {rv[p],rge[p],rbusy[p],rfault[p]})
                    $fatal(1,"control mismatch PQ%0d check%0d",p,checks[p]);
                if (cv[p]) begin
                    if ({ca[p],cd[p]} !== {ra[p],rd[p]})
                        $fatal(1,"word mismatch PQ%0d check%0d addr%0d actual%h expected%h",p,checks[p],ca[p],cd[p],rd[p]);
                    if (!cd[p]) $fatal(1,"unexpected zero cfg fixture word");
                    words_seen[p]++;
                end
                if (ge[p]) admissions[p]++;
                if (fault[p]) faults[p]++;
            end else if (cv[p] || ge[p] || busy[p] || fault[p])
                $fatal(1,"reset/hold mismatch PQ%0d",p);
        end
    end
    task automatic tick;
        @(negedge clk);
    endtask
    integer old_reads0, old_reads1;
    reg [31:0] rng=32'h725ace19;
    initial begin
        for (int a=0;a<1600;a++) payload[a]=word_at(a);
        repeat(3) tick();rst_n=1;
        // Full 64-phase source extent; actual 25 reads and 25 valid words.
        for (int ph=0;ph<64;ph++) begin
            old_reads0=reads[0];old_reads1=reads[1];
            phase=6'(ph);np=3'(ph);cfg_go=1;tick();cfg_go=0;
            repeat(29) tick();
            if (reads[0]-old_reads0!=25 || reads[1]-old_reads1!=25)
                $fatal(1,"finite readcount differs phase%0d",ph);
            go=1;tick();go=0;tick();
        end
        if(words_seen[0]!=1600 || words_seen[1]!=1600)
            $fatal(1,"full phase extent not consumed");
        // Pending loader start, overlapping request, early GO, resets, and
        // deterministic varied phases/positions compare against original RTL.
        for (int n=0;n<4000;n++) begin
            rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
            rst_n=(n%311!=0);phase=rng[5:0];np=rng[8:6];
            cfg_go=(n==4 || n==7 || rng[12:9]==0);
            go=(n==11 || rng[15:13]==0);
            sh_free=(n<12?0:rng[16]);bank_free=(n<12?0:rng[17]);
            tick();
        end
        rst_n=1;cfg_go=0;go=0;sh_free=1;bank_free=1;repeat(35) tick();
        if(faults[0]!=0 || faults[1]==0 || admissions[0]==0 || admissions[1]==0)
            $fatal(1,"fault/go mechanism unexercised");
        $display("PASS cfgROM original-loader cycle equality PQ0/PQ1 checks=%0d/%0d words=%0d/%0d reads=%0d/%0d go=%0d/%0d faults=%0d/%0d full_phases64_reads25_each",checks[0],checks[1],words_seen[0],words_seen[1],reads[0],reads[1],admissions[0],admissions[1],faults[0],faults[1]);
        $finish;
    end
endmodule
