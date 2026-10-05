`timescale 1ns/1ps
module tb_hdc_v41x_idx_shard_roundtrip_pc;
    localparam integer NPC=4,AW=28,NPORT=4*NPC;
    reg clk=0,rst_n=0,su_go=0,cmd_v=0;
    always #5 clk=~clk;
    reg [23:0] row=0;
    reg [7:0] kv_we=0;
    reg [8*24-1:0] kv_waddr=0;
    reg [8*32-1:0] kv_wdata=0;
    wire w_v,w_rdy,writer_fault;
    wire [3:0] mask;
    wire [AW-1:0] csec,ssec;
    wire [511:0] codes;
    wire [2:0] sslot;
    wire [31:0] scales,written_keys;
    ot_hdc_v41x_idx_pool_kwr #(.SHARDED(1)) writer (
        .clk(clk),.rst_n(rst_n),.cfg_ik_base(24'd0),.su_go(su_go),
        .i_dst(2'd3),.i_obase(24'd0),.i_orow(row),.i_nout(16'd1),.i_kdim(16'd32),
        .kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),
        .w_v(w_v),.w_rdy(w_rdy),.w_stack_mask(mask),.w_csec(csec),
        .w_codes(codes),.w_ssec(ssec),.w_sslot(sslot),.w_scales(scales),
        .fault(writer_fault),.dbg_keys(written_keys));

    reg [29:0] cmd_nkeys=0;
    wire reader_busy,reader_fault,o_valid;
    wire [NPORT-1:0] rv,rrdy,hv,hrdy,hwe,hwr_done,resp_v,resp_rdy;
    wire [NPORT*AW-1:0] ra,ha;
    wire [NPORT*4-1:0] rl,hl,resp_beat;
    wire [NPORT*16-1:0] rt,ht,resp_tag;
    wire [NPORT*256-1:0] hwdata,resp_data;
    wire [NPORT*32-1:0] hwstrb;
    wire [63:0] o_kv,o_ref;
    wire [3:0] o_last;
    wire [64*544-1:0] o_key;
    wire [47:0] keys_read,sectors_read,refused;
    ot_hdc_v41x_idx_shard_reader_pc #(.NPC(NPC),.HAW(AW)) reader (
        .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_base_sec(28'd0),.cmd_nkeys(cmd_nkeys),
        .busy(reader_busy),.fault(reader_fault),.req_v(rv),.req_rdy(rrdy),
        .req_addr(ra),.req_len(rl),.req_tag(rt),.rsp_v(resp_v),
        .rsp_rdy(resp_rdy),.rsp_tag(resp_tag),.rsp_beat(resp_beat),.rsp_data(resp_data),
        .o_valid(o_valid),.o_ready(1'b1),.o_kv(o_kv),.o_last(o_last),.o_key(o_key),
        .o_ref(o_ref),.cnt_keys_streamed(keys_read),.cnt_hbm_beats(sectors_read),
        .cnt_refused(refused));

    wire bridge_busy;
    wire [31:0] records,writes,highwater,read_stalls,writer_stalls;
    ot_hdc_v41x_idx_pool_hbm_bridge #(.NPC(NPC),.AW(AW)) bridge (
        .clk(clk),.rst_n(rst_n),.w_v(w_v),.w_rdy(w_rdy),.w_stack_mask(mask),
        .w_csec(csec),.w_codes(codes),.w_ssec(ssec),.w_sslot(sslot),.w_scales(scales),
        .r_v(rv),.r_rdy(rrdy),.r_addr(ra),.r_len(rl),.r_tag(rt),
        .h_v(hv),.h_rdy(hrdy),.h_addr(ha),.h_len(hl),.h_tag(ht),
        .h_we(hwe),.h_wdata(hwdata),.h_wstrb(hwstrb),.h_wr_done(hwr_done),
        .busy(bridge_busy),.dbg_records(records),.dbg_writes(writes),
        .dbg_fifo_highwater(highwater),.dbg_read_stalls(read_stalls),
        .dbg_writer_stalls(writer_stalls));
    for(genvar s=0;s<4;s=s+1) begin : g_hbm
        ot_hdc_v41x_idx_hbm #(.NPC(NPC),.AW(AW),.DW(256),.MEM_WORDS(512),
            .TAGW(16),.LENW(4),.BEATW(4),.QD(16),.RQD(8),.REFPB(3),.MEM_MODE(0)) hm (
            .clk(clk),.rst_n(rst_n),.req_v(hv[s*NPC +: NPC]),.req_rdy(hrdy[s*NPC +: NPC]),
            .req_addr(ha[s*NPC*AW +: NPC*AW]),.req_len(hl[s*NPC*4 +: NPC*4]),
            .req_tag(ht[s*NPC*16 +: NPC*16]),.req_we(hwe[s*NPC +: NPC]),
            .req_wdata(hwdata[s*NPC*256 +: NPC*256]),.req_wstrb(hwstrb[s*NPC*32 +: NPC*32]),
            .wr_done(hwr_done[s*NPC +: NPC]),.rsp_v(resp_v[s*NPC +: NPC]),
            .rsp_rdy(resp_rdy[s*NPC +: NPC]),.rsp_tag(resp_tag[s*NPC*16 +: NPC*16]),
            .rsp_beat(resp_beat[s*NPC*4 +: NPC*4]),.rsp_data(resp_data[s*NPC*256 +: NPC*256]));
        initial for(integer i=0;i<512;i=i+1) hm.mem[i]=0;
    end
    integer cycle=0;
    always @(posedge clk) begin
        cycle<=cycle+1;
        if(cycle>300000) $fatal(1,"shard roundtrip timeout");
        if(writer_fault || reader_fault) $fatal(1,"writer/reader fault");
    end

    task automatic write_row(input integer r);
        integer i,l,vm_base;
        begin
            vm_base=(r>>4)*32*16+(r&15);
            @(negedge clk);row=r;su_go=1;
            @(negedge clk);su_go=0;
            for(i=0;i<32;i=i+8) begin
                kv_we=8'hff;
                for(l=0;l<8;l=l+1) begin
                    kv_waddr[l*24 +:24]=vm_base+16*(i+l);
                    kv_wdata[l*32 +:32]={16'((127+r)<<7),16'd0};
                end
                @(negedge clk);
            end
            kv_we=0;
            wait(w_v && w_rdy);
            @(posedge clk);
            @(negedge clk);
        end
    endtask

    task automatic read_scan(input integer n);
        integer prior_k,prior_s,qs,l3,beats,b,q,l,k,j,qlen,start_cycle;
        reg [543:0] got;
        begin
            prior_k=keys_read;prior_s=sectors_read;
            @(negedge clk);cmd_nkeys=n;cmd_v=1;start_cycle=cycle;
            @(negedge clk);cmd_v=0;
            qs=8*(n/32);l3=n-3*qs;beats=(l3+15)/16;
            for(b=0;b<beats;b=b+1) begin
                wait(o_valid);#1;
                for(q=0;q<4;q=q+1) begin
                    qlen=q==3 ? l3 : qs;
                    if(o_last[q] !== ((qlen==0) ? (b==0) : (b==(qlen-1)/16)))
                        $fatal(1,"roundtrip last n=%0d b=%0d q=%0d",n,b,q);
                    for(l=0;l<16;l=l+1) begin
                        k=q*qs+16*b+l;
                        if(o_kv[16*q+l] !== (16*b+l<qlen))
                            $fatal(1,"roundtrip valid n=%0d key=%0d",n,k);
                        if(16*b+l<qlen) begin
                            got=o_key[544*(16*q+l) +:544];
                            for(j=0;j<64;j=j+1)
                                if(got[8*j +:8] !== (j<16 ? 8'h66 : 8'h00))
                                    $fatal(1,"roundtrip code n=%0d key=%0d byte=%0d got=%0h",n,k,j,got[8*j +:8]);
                            if(got[543:512] !== {24'd0,8'(125+k)})
                                $fatal(1,"roundtrip scale n=%0d key=%0d scale=%h",n,k,got[543:512]);
                            if(o_ref[16*q+l] !== 1'b0) $fatal(1,"roundtrip refusal key=%0d",k);
                        end
                    end
                end
                @(posedge clk);#1;
            end
            wait(!reader_busy);
            if(keys_read-prior_k!=n || sectors_read-prior_s!=2*n+(n+7)/8 || refused!=0)
                $fatal(1,"roundtrip counts n=%0d keys=%0d sectors=%0d",n,
                    keys_read-prior_k,sectors_read-prior_s);
            $display("ROUNDTRIP n=%0d keys=%0d sectors=%0d cycles=%0d",n,n,
                     sectors_read-prior_s,cycle-start_cycle);
        end
    endtask
    initial begin
        repeat(3) @(negedge clk);rst_n=1;
        write_row(0);
        if(!bridge_busy) $fatal(1,"read-after-write not pending");
        read_scan(1);
        for(integer r=1;r<=64;r=r+1) write_row(r);
        wait(!bridge_busy);
        read_scan(40); // Qs=8: several quarter groups straddle stack stripes
        read_scan(65); // row 63/64 crosses a 64-key global stripe cycle
        if(records!=65 || writes!=195 || read_stalls==0 || written_keys!=65)
            $fatal(1,"writer/bridge accounting records=%0d writes=%0d stalls=%0d keys=%0d",
                   records,writes,read_stalls,written_keys);
        $display("V41X_SHARD_ROUNDTRIP_PASS rows=65 records=%0d writes=%0d stalls=%0d",
                 records,writes,read_stalls);
        $finish;
    end
endmodule
