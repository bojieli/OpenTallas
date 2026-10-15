`timescale 1ns/1ps
module tb_hgi_hc_residual_vm_static;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,launch=0;
    reg [31:0] fill_v=0;
    reg [4*8*281-1:0] fill_q=0;
    wire [135:0] rq;
    wire [7:0] rd;
    wire [2055:0] rr;
    wire wavev,done,fault;
    wire [9:0] word_;
    wire [8191:0] wave;
    wire [4*2056-1:0] responses;
    wire [4*8*18-1:0] status;
    wire [11:0] tapfault;
    reg [8191:0] observed;
    integer cycle=0,words=0;
    parameter integer MUT=0;
    function automatic [255:0] payload(input integer sector);
        for(integer j=0;j<8;j=j+1)payload[j*32+:32]=(32'h3f000000|32'(((sector*8+j)&8'hff)<<16));
    endfunction
    ot_hgi_hc_residual_vm_static #(.MUT_POSITION(MUT)) producer(
        .clk(clk),.rst_n(rst_n),.launch(launch),.npos(4'd8),.base_sector(16'd0),
        .local_rq(rq),.local_read(rd),.local_rr(rr),.x_wave_v(wavev),.x_wave_word(word_),.x_wave(wave),.done(done),.fault(fault));
    for(genvar sid=0;sid<4;sid=sid+1)begin:quadrant
        wire [407:0] nrq;wire [6743:0] nwq;
        wire [6167:0] lrr,frr;wire [23:0] ld,fd;
        wire [2055:0] bankrr;wire [7:0] bankdone;
        assign responses[sid*2056+:2056]=lrr[(2)*2056+:2056];
        for(genvar b=0;b<8;b=b+1)begin:bank
            wire [770:0] r;
            assign bankrr[b*257+:257]=r[0+:257];
            ot_vms_bank_static #(.RG(3),.WG(1)) mem(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'(sid)),
                .rslot_v(1'b1),.rslot(2'd0),.wslot_v(1'b1),.wslot(3'd5),
                .rq({34'd0,nrq[b*17+:17]}),.rr(r),.wq(nwq[b*281+:281]),.wq_done(bankdone[b]),
                .dq(fill_q[(sid*8+b)*281+:281]),.dq_done(),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
                .eg(),.pq(285'd0),.pr(),.status(status[(sid*8+b)*18+:18]));
        end
        for(genvar st=0;st<3;st=st+1)begin:station
            wire [135:0] localq;
            for(genvar b=0;b<8;b=b+1)assign localq[b*17+:17]={st==2&&rq[b*17+16]&&rq[b*17+13+:2]==sid,rq[b*17+:16]};
            ot_hbm_vm_lg_static_tap #(.READ_RETURN(10+4*st),.WRITE_RETURN(7+4*st)) tap(
                .clk(clk),.rst_n(rst_n),.local_rq(localq),.far_rq(st==2?136'd0:nrq[(st+1)*136+:136]),
                .local_wq(2248'd0),.far_wq(st==2?2248'd0:nwq[(st+1)*2248+:2248]),
                .local_read({8{st==2}}),.local_write(8'd0),.near_rq(nrq[(st)*136+:136]),.near_wq(nwq[(st)*2248+:2248]),
                .near_rr(st==0?bankrr:frr[(st-1)*2056+:2056]),.near_w_done(st==0?bankdone:fd[(st-1)*8+:8]),
                .local_rr(lrr[(st)*2056+:2056]),.far_rr(frr[(st)*2056+:2056]),.local_w_done(ld[(st)*8+:8]),.far_w_done(fd[(st)*8+:8]),.fault(tapfault[sid*3+st]));
        end
    end
    for(genvar b=0;b<8;b=b+1)assign rr[b*257+:257]=responses[b*257+:257]|responses[2056+b*257+:257]|responses[4112+b*257+:257]|responses[6168+b*257+:257];
    always @(posedge clk)begin
        cycle<=cycle+1;
        if(rst_n&&(fault||(|tapfault)||(|status)))$fatal(1,"native VM fault cycle%0d",cycle);
        if(wavev)begin
            if(word_!=words)$fatal(1,"position calendar mutant observed word%0d expected%0d",word_,words);
            for(integer l=0;l<32;l=l+1)if(wave[l*256+:256]!==payload(words*32+l))$fatal(1,"actual VM residual data mismatch word%0d lane%0d",words,l);
            words<=words+1;
        end
    end
    initial begin
        repeat(5)@(negedge clk);rst_n=1;
        for(integer group=0;group<2560;group=group+1)begin
            fill_q=0;
            for(integer b=0;b<8;b=b+1)begin
                integer sector,sid;sector=group*8+b;sid=(sector>>13)&3;
                fill_q[(sid*8+b)*281+:281]={1'b1,16'(sector),payload(sector),8'hff};
            end
            @(negedge clk);
        end
        fill_q=0;repeat(10)@(negedge clk);launch=1;@(negedge clk);launch=0;
        repeat(2600)@(negedge clk);
        if(words!=640)$fatal(1,"native residual wave count%0d",words);
        $display("HC_NATIVE_VM_RESIDUAL_PASS waves=%0d sectors=20480 actualbanks32 SRAM96 tap12",words);$finish;
    end
endmodule
