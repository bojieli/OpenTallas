`timescale 1ns/1ps
// Actual full128 banked WINDOW prefetch plus both production tag-owner muxes.
// Functional clock only. Synthetic memory inputs; expected words assertion-only.
module tb_window_owner_tag_r2 #(parameter integer OWNER_SAFE=0);
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0,prime_v=0,prefetch_v=0,bank_req_v=0;
    reg [20:0] prime_row=0,prefetch_row=0,bank_first=0;
    wire prime_ready,prefetch_ready,kv_ok,bank_ready,bank_rsp_v,bank_fault;
    wire [3:0] bank_mask,bank_valid;
    wire [4*4224-1:0] bank_rows;
    wire pf_fault,mux_fault;
    wire [4:0] pf_code;
    wire [31:0] rows_fetched,sectors_read;
    wire [3:0] wv,wrdy,wwe,wsv,wsrdy,wwdone,mv,mwe,srdy;
    wire [119:0] wa,ma;
    wire [15:0] wl,ml,wb;
    wire [63:0] wt,wstag,mt;
    wire [1023:0] wd,wsdata,md;
    wire [127:0] wm,mm;
    reg [3:0] sv=0;
    reg [63:0] stag=0;
    reg [1023:0] sd=0;
    integer cycle=0,reads=0,replies=0,pending=0,peak=0,chosen=-1,free_slot=-1;
    reg qa[0:7];integer due[0:7];reg [15:0] qt[0:7];reg [29:0] addr[0:7];
    integer current_refill=0;
    function automatic [255:0] image(input integer row,input integer sec);
        reg [255:0] word;
        begin
            word=0;
            if(sec<16) for(integer n=0;n<32;n=n+1) word[8*n+:8]=8'(1+(row*3+sec+n)%100);
            else for(integer n=0;n<16;n=n+1) word[8*n+:8]=8'd127;
            image=word;
        end
    endfunction
    function automatic [4223:0] expected_row(input integer row);
        reg [4223:0] value;
        begin
            value=0;
            for(integer s=0;s<16;s=s+1)value[256*s+:256]=image(row,s);
            for(integer n=0;n<16;n=n+1)value[4096+8*n+:8]=8'd127;
            expected_row=value;
        end
    endfunction
`ifdef OWNER_SAFE_BUILD
    ot_chip_v41x_window_kv_prefetch_owner_safe #(.REFILL_OWNER_SAFE(OWNER_SAFE),
`else
    ot_chip_v41x_window_kv_prefetch #(
`endif
        .WIN_STACK(0),.REFILL_CREDITS(8),.BANKED_STAGE(1)) dut (
        .clk(clk),.rst_n(rst_n),.region_base_sector(30'd64),.region_sector_count(30'd2176),
        .prime_v(prime_v),.prime_ready(prime_ready),.prime_user(10'd0),.prime_row(prime_row),
        .blk_v(1'b0),.blk_user(10'd0),.blk_row(21'd0),.blk_idx(4'd0),.blk_codes(256'd0),.blk_scale(8'd127),
        .prefetch_v(prefetch_v),.prefetch_ready(prefetch_ready),.prefetch_user(10'd0),.prefetch_row(prefetch_row),.kv_ok(kv_ok),
        .re(1'b0),.ruser(10'd0),.rrow(21'd0),.relem(9'd0),
        .packed_re(1'b0),.packed_ruser(10'd0),.packed_rrow(21'd0),.packed_ridx(4'd0),
        .bank_req_v(bank_req_v),.bank_req_ready(bank_ready),.bank_req_user(10'd0),.bank_req_first(bank_first),.bank_req_mask(4'd1),
        .bank_rsp_v(bank_rsp_v),.bank_rsp_mask(bank_mask),.bank_rsp_valid_mask(bank_valid),.bank_rsp_rows(bank_rows),.bank_rsp_fault(bank_fault),
        .fault(pf_fault),.fault_code(pf_code),.st_rows_fetched(rows_fetched),.st_sectors_read(sectors_read),
        .m_v(wv),.m_rdy(wrdy),.m_addr(wa),.m_len(wl),.m_tag(wt),.m_we(wwe),.m_wdata(wd),.m_wstrb(wm),
        .m_wr_done(wwdone),.s_v(wsv),.s_rdy(wsrdy),.s_tag(wstag),.s_beat(wb),.s_data(wsdata));
    ot_chip_v41x_kv_rope_reqmux mux (
        .clk(clk),.rst_n(rst_n),.w_v(wv),.w_rdy(wrdy),.w_addr(wa),.w_len(wl),.w_tag(wt),.w_we(wwe),.w_wdata(wd),.w_wstrb(wm),
        .w_wr_done(wwdone),.w_sv(wsv),.w_srdy(wsrdy),.w_stag(wstag),.w_sbeat(wb),.w_sdata(wsdata),
        .c_v(4'd0),.c_addr(120'd0),.c_len(16'd0),.c_tag(64'd0),.c_we(4'd0),.c_wdata(1024'd0),.c_wstrb(128'd0),.c_srdy(4'hf),
        .p_v(4'd0),.p_addr(120'd0),.p_len(16'd0),.p_tag(64'd0),.p_we(4'd0),.p_srdy(4'hf),
        .m_v(mv),.m_rdy(4'hf),.m_addr(ma),.m_len(ml),.m_tag(mt),.m_we(mwe),.m_wdata(md),.m_wstrb(mm),.m_wr_done(4'd0),
        .s_v(sv),.s_rdy(srdy),.s_tag(stag),.s_beat(16'd0),.s_data(sd),.fault(mux_fault));
    always @(posedge clk) begin
        cycle=cycle+1;sv<=0;chosen=-1;free_slot=-1;
        for(integer j=0;j<8;j=j+1)begin
            if(qa[j] && due[j]<=cycle)chosen=j;
            if(!qa[j])free_slot=j;
        end
        if(chosen>=0)begin
            sv[0]<=1;stag[15:0]<=qt[chosen];sd[255:0]<=image((addr[chosen]-64)/17,(addr[chosen]-64)%17);
            qa[chosen]=0;pending=pending-1;replies=replies+1;
        end
        if(rst_n && mv[0])begin
            if(mwe[0] || ml[3:0]!=1 || mt[15:14]!=0 || free_slot<0)$fatal(1,"OTHER_FAULT backend request");
            qa[free_slot]=1;due[free_slot]=cycle+9+(ma[29:0]%3);qt[free_slot]=mt[15:0];addr[free_slot]=ma[29:0];pending=pending+1;reads=reads+1;
            if(pending>peak)peak=pending;
        end
    end
    task automatic check_bank(input integer r);
        begin
            @(negedge clk);bank_first=21'(r);bank_req_v=1;
            @(negedge clk);bank_req_v=0;
            while(!bank_rsp_v)begin @(negedge clk);end
            if(bank_fault || bank_mask!=1 || bank_valid!=1 || bank_rows[4223:0]!==expected_row(r))$fatal(1,"OTHER_FAULT exact staged words row=%0d",r);
        end
    endtask
    initial begin
        for(integer j=0;j<8;j=j+1)qa[j]=0;
        repeat(3)@(negedge clk);rst_n=1;
        for(integer r=0;r<128;r=r+1)begin
            while(!prime_ready)@(negedge clk);
            prime_row=21'(r);prime_v=1;@(negedge clk);prime_v=0;
        end
        for(integer epoch=1;epoch<=(OWNER_SAFE ? 1536 : 512);epoch=epoch+1)begin
            current_refill=epoch;
            while(!prefetch_ready)@(negedge clk);
            prefetch_row=21'((epoch-1)%128);prefetch_v=1;@(negedge clk);prefetch_v=0;
            while(!kv_ok && !mux_fault && !pf_fault)@(negedge clk);
            if(mux_fault)begin
                if(OWNER_SAFE || epoch!=512 || rows_fetched!=511 || reads!=8687 || replies!=reads || pending!=0 || !wv[0] || wrdy[0] || mv[0] || wt[15:0]!=16'h4000 || pf_fault)
                    $fatal(1,"OTHER_FAULT unexpected mux failure epoch=%0d rows=%0d reads=%0d tag=%h",epoch,rows_fetched,reads,wt[15:0]);
                $display("WINDOW_OWNER_NEGATIVE_CONFIRMED refill=512 rows=511 reads=8687 replies=8687 client_tag=4000 sector=0 owner=01 w_valid=1 w_ready=0 master_valid=0 mux_fault=1 pf_fault=0 peak=%0d",peak);$finish;
            end
            if(pf_fault || !kv_ok || pending || replies!=reads || reads!=17*epoch || rows_fetched!=epoch)$fatal(1,"OTHER_FAULT row drain epoch=%0d code=%h",epoch,pf_code);
            check_bank((epoch-1)%128);
            if(epoch==511 || epoch==512 || epoch==513 || epoch==1023 || epoch==1024 || epoch==1025 || epoch==1535 || epoch==1536)
                $display("ROW_BOUNDARY refill=%0d epoch=%0d rows=%0d reads=%0d pending=%0d",epoch,dut.refill_epoch,rows_fetched,reads,pending);
        end
        if(!OWNER_SAFE)$fatal(1,"MISSING_EXPECTED_OWNER_FAILURE");
        if(reads!=26112 || replies!=26112 || peak!=8)$fatal(1,"OTHER_FAULT final counters/credit stress");
        $display("WINDOW_OWNER_SAFE_PASS rows=%0d reads=%0d replies=%0d checks=1536 wraps=3 peak=%0d",rows_fetched,reads,replies,peak);$finish;
    end
endmodule
