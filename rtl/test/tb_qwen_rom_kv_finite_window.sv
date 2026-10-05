`timescale 1ns/1ps
// Read-only transport diagnostic: existing connected KV system, real streamer,
// sector bridge and arbiter; finite delayed reads held until response acceptance.
// Small G4/SW16 fixture uses BF16 window/tail arrays, not tile SRAM macros or r14.
// No second token, layer switch, engine change, physical or full-token proof.
module tb_qwen_rom_kv_finite_window;
    parameter integer SW=16;
    parameter integer READ_SERVICE_CYCLES=41;
    parameter integer CORRUPT_RETURN=0;
    parameter integer V_MODE=0;
    parameter integer SPLIT_MODE=1;
    parameter integer HBM_SPLIT_MODE=1;
    parameter integer FLUSH_MODE=0;
    parameter integer BOOT_HBM_MODE=0;
    localparam AW=24,G=4,W=16,LWIN=4,NPC=2,BK=4,TAGW=1+LWIN+$clog2(G)+3,LBK=$clog2(BK);
    reg clk=0,rst_n=0,boot_v=0,boot_start=0,kvd_v=0,kv_re=0,tok_start=0;
    reg [15:0] tok_pos=0;
    always #5 clk=~clk;
    reg [AW-1:0] boot_word=0;
    reg [127:0] boot_data=0;
    reg [SW-1:0] kv_we=0;
    reg [SW*AW-1:0] kv_waddr=0;
    reg [SW*32-1:0] kv_wdata=0;
    wire [G*W*32-1:0] kv_q;
    wire kv_ok,drained,fault,boot_busy,boot_done;
    wire [G-1:0] win_we;
    wire [G*LWIN-1:0] win_waddr;
    wire [G*W*16-1:0] win_wdata;
    wire win_re;
    wire [LWIN-1:0] win_raddr;
    reg [G*W*16-1:0] win_q=0;
    reg [W*16-1:0] win_mem [0:G-1][0:(1<<LWIN)-1];
    wire [2*SW-1:0] bank_we,bank_re;
    wire [2*SW*AW-1:0] bank_wrow,bank_rrow;
    wire [2*SW*16-1:0] bank_wmask;
    wire [2*SW*128-1:0] bank_wdata;
    reg [2*SW*128-1:0] bank_q=0;
    reg [127:0] bank_mem [0:2*SW-1][0:15];
    wire h_req_v,h_req_we;
    wire [AW-1:0] h_req_sector;
    wire [LBK:0] h_req_len;
    wire [TAGW-1:0] h_req_tag;
    wire [255:0] h_req_data;
    wire [NPC-1:0] h_rsp_ready;
    reg [NPC-1:0] h_rsp_v=0;
    reg [NPC*TAGW-1:0] h_rsp_tag=0;
    reg [NPC*LBK-1:0] h_rsp_beat=0;
    reg [NPC*256-1:0] h_rsp_data=0;
    reg [255:0] h_mem [0:511];
    integer h_reads=0,h_writes=0;
    integer service_left=0,cycle=0,window_writes=0;
    reg read_pending=0;
    reg [AW-1:0] read_sector=0;
    reg [TAGW-1:0] read_tag=0;
    wire service_ready=!read_pending && !h_rsp_v && (cycle%7!=0);
    always @(posedge clk) begin
        cycle <= cycle+1;
        if (cycle>20000) $fatal(1,"finite window timeout");
        if (rst_n) for(integer g=0;g<G;g=g+1) if(win_we[g]) window_writes=window_writes+1;
    end
    integer b,r;
    ot_hdc_qwen_kv_system #(.W(W),.G(G),.SW(SW),.AW(AW),.LWIN(LWIN),
                             .NPC(NPC),.BK(BK),.LOG_HD(4),.LOG_TW(2),.LLG(3),.V0_WORD(512)) dut (
        .clk(clk),.rst_n(rst_n),.tok_start(tok_start),.tok_pos(tok_pos),.cfg_lead(16'd0),
        .kvd_v(kvd_v),.kvd_wbase(V_MODE ? 24'd512 : 24'd0),
        .kvd_ts(V_MODE ? 24'd1 : 24'd16),.kvd_ks(SPLIT_MODE ? 24'd4 : 24'd1),.kvd_js(24'd16),
        .kvd_wcs(SPLIT_MODE ? 24'd1 : 24'd0),.kvd_split(SPLIT_MODE ? 4'd2 : 4'd0),
        .kvd_jsh(SPLIT_MODE ? 3'd2 : 3'd3),.kvd_tiles(16'd1),
        .kvd_k(SPLIT_MODE ? 16'd16 : 16'd1),.kvd_nout(16'd16),
        .kvd_pos(HBM_SPLIT_MODE ? 16'd62 : 16'd0),.kvd_kindk(!V_MODE),.kv_ok(kv_ok),
        .kv_re(kv_re),.kv_raddr(SPLIT_MODE ? (V_MODE ? {24'd515,24'd514,24'd513,24'd512} :
                                                {24'd3,24'd2,24'd1,24'd0}) :
                                      (V_MODE ? {{((G-1)*AW){1'b0}},24'd512} : '0)),.kv_q(kv_q),
        .kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),
        .kv_write_flush(1'b1),.kv_write_drained(drained),
        .boot_v(boot_v),.boot_word(boot_word),.boot_data(boot_data),
        .boot_start(boot_start),.boot_busy(boot_busy),.boot_done(boot_done),
        .win_we(win_we),.win_waddr(win_waddr),.win_wdata(win_wdata),
        .win_re(win_re),.win_raddr(win_raddr),.win_q(win_q),
        .bank_we(bank_we),.bank_re(bank_re),.bank_wrow(bank_wrow),.bank_rrow(bank_rrow),
        .bank_wmask(bank_wmask),.bank_wdata(bank_wdata),.bank_q(bank_q),
        .h_req_v(h_req_v),.h_req_ready(service_ready),.h_req_we(h_req_we),
        .h_req_sector(h_req_sector),.h_req_len(h_req_len),.h_req_tag(h_req_tag),.h_req_data(h_req_data),
        .h_rsp_v(h_rsp_v),.h_rsp_ready(h_rsp_ready),.h_rsp_tag(h_rsp_tag),
        .h_rsp_beat(h_rsp_beat),.h_rsp_data(h_rsp_data),
        .fault(fault));
    always @(posedge clk) begin
        if (h_rsp_v[0] && h_rsp_ready[0]) h_rsp_v <= 0;
        if (read_pending) begin
            if(service_left==1) begin
                read_pending<=0;
                h_rsp_v[0]<=1;
                h_rsp_tag[0 +: TAGW]<=read_tag;
                h_rsp_beat[0 +: LBK]<=0;
                h_rsp_data[0 +: 256]<=h_mem[read_sector] ^ (CORRUPT_RETURN ? 256'h1 : 256'h0);
            end else service_left<=service_left-1;
        end
        if (h_req_v && service_ready) begin
            if (h_req_we) begin
                // This READ-only gate does not qualify delayed backing writes.
                $fatal(1,"unexpected external write in read-window gate");
            end else begin
                h_reads=h_reads+1;
                read_pending<=1;service_left<=READ_SERVICE_CYCLES;
                read_sector<=h_req_sector;read_tag<=h_req_tag;
            end
        end
        for (integer g=0;g<G;g=g+1) begin
            if (win_re) win_q[g*W*16 +: W*16] <= win_mem[g][win_raddr];
            if (win_we[g]) win_mem[g][win_waddr[g*LWIN +: LWIN]] <= win_wdata[g*W*16 +: W*16];
        end
        for (integer i=0;i<2*SW;i=i+1) begin
            if (bank_re[i]) bank_q[i*128 +: 128] <= bank_mem[i][bank_rrow[i*AW +: AW]];
            if (bank_we[i])
                for (integer j=0;j<16;j=j+1)
                    if (bank_wmask[i*16+j]) bank_mem[i][bank_wrow[i*AW +: AW]][j*8 +: 8] <=
                        bank_wdata[i*128+j*8 +: 8];
        end
    end
    initial begin
        for (b=0;b<2*SW;b=b+1)
            for (r=0;r<16;r=r+1) bank_mem[b][r]=0;
        for (b=0;b<512;b=b+1) h_mem[b]=0;
        if (HBM_SPLIT_MODE || BOOT_HBM_MODE) begin
            h_mem[0][0 +: 128]={16{8'h38}}; h_mem[0][128 +: 128]={16{8'h40}};
            h_mem[1][0 +: 128]={16{8'h48}}; h_mem[1][128 +: 128]={16{8'h50}};
        end
        if (V_MODE && SPLIT_MODE) begin
            h_mem[256][128 +: 128]={16{8'h40}};
            h_mem[257][0 +: 128]={16{8'h48}};
            h_mem[257][128 +: 128]={16{8'h50}};
        end
        for (b=0;b<G;b=b+1)
            for (r=0;r<(1<<LWIN);r=r+1) win_mem[b][r]=0;
        repeat(2) @(negedge clk); rst_n=1; boot_v=!BOOT_HBM_MODE; boot_start=BOOT_HBM_MODE;
        if (BOOT_HBM_MODE) begin
            @(negedge clk); boot_start=0;
            for (integer n=0;n<2000 && !boot_done;n=n+1) @(negedge clk);
            if (!boot_done || boot_busy || h_reads<128 || fault)
                $fatal(1,"HBM K boot incomplete: done=%b busy=%b reads=%0d fault=%b",
                       boot_done,boot_busy,h_reads,fault);
        end
        if ((SPLIT_MODE || FLUSH_MODE) && !BOOT_HBM_MODE) begin
            for (integer s=0;s<(FLUSH_MODE ? 128 : 4);s=s+1) begin
                boot_word=FLUSH_MODE ? ((s/16)*64+(s%16)) : s;
                boot_data={16{8'(s<4 ? (8'h38+s*8) : 8'h38)}};
                @(negedge clk);
            end
        end
        // The KV descriptor arrives with a vector K write. The system must
        // hold the descriptor until that write retires to the physical bank.
        @(negedge clk); boot_v=0; kvd_v=1;
        kv_we[0]=1; kv_waddr[0 +: AW]=V_MODE ? 8192 : 0; kv_wdata[0 +: 32]=32'h3f800000;
        @(negedge clk); kvd_v=0; kv_we=0;
        for (integer n=0;n<(HBM_SPLIT_MODE ? 2000 : 300) && !kv_ok;n=n+1) @(negedge clk);
        if (!kv_ok || !drained || fault) $fatal(1,"descriptor did not become ready");
        kv_re=1;
        @(posedge clk); #1;
        if (kv_q[31:0] !== 32'h3f800000 || fault || (!V_MODE && !HBM_SPLIT_MODE && h_req_v))
            $fatal(1,"KV physical read mismatch SW=%0d V=%0d got=%h fault=%b hq=%b",SW,V_MODE,kv_q[31:0],fault,h_req_v);
        if (SPLIT_MODE)
            for (integer s=1;s<4;s=s+1)
                if (kv_q[(s*W)*32 +: 32] !== (32'h3f800000 + (s<<23)))
                    $fatal(1,"split tail group %0d read %h",s,kv_q[(s*W)*32 +: 32]);
        if (HBM_SPLIT_MODE && h_reads < 4)
            $fatal(1,"split HBM walk did not fetch four group words: reads=%0d",h_reads);
        if (BOOT_HBM_MODE && (!boot_done || h_reads<128))
            $fatal(1,"tail read did not follow autonomous HBM boot");
        if (V_MODE && (h_mem[256][7:0] !== 8'h38 || h_reads<2 || h_writes!=1))
            $fatal(1,"V sector did not pass RMW+fetch: byte=%h reads=%0d writes=%0d",
                   h_mem[256][7:0],h_reads,h_writes);
        if (FLUSH_MODE) begin
            @(negedge clk); kv_re=0; tok_pos=16; tok_start=1;
            @(negedge clk); tok_start=0;
            for (integer n=0;n<5000 && h_writes<128;n=n+1) @(negedge clk);
            if (h_writes != 128 || fault)
                $fatal(1,"K tile flush incomplete: writes=%0d fault=%b",h_writes,fault);
            for (integer s=0;s<128;s=s+1) begin
                integer word_addr;
                reg [127:0] want;
                word_addr=(s/16)*64+(s%16);
                want=(s==0) ? 128'h38 : {16{8'(s<4 ? (8'h38+s*8) : 8'h38)}};
                if (h_mem[word_addr/2][(word_addr%2)*128 +: 128] !== want)
                    $fatal(1,"K tile flush word %0d address %0d mismatch: got=%h expect=%h",
                           s,word_addr,h_mem[word_addr/2][(word_addr%2)*128 +: 128],want);
            end
        end
        @(negedge clk); kv_re=0;
        for(integer n=0;n<2000 && (read_pending || h_rsp_v || h_req_v);n=n+1) @(negedge clk);
        if(window_writes==0 || h_writes!=0 || read_pending || h_rsp_v || h_req_v)
            $fatal(1,"window/transport drain incomplete writes=%0d pending=%b rsp=%b req=%b",window_writes,read_pending,h_rsp_v,h_req_v);
        $display("PASS QWEN_ROM_FINITE_WINDOW cycles=%0d reads=%0d window_writes=%0d service_cycles=%0d SW=%0d",cycle,h_reads,window_writes,READ_SERVICE_CYCLES,SW); $finish;
    end
endmodule
