`timescale 1ns/1ps
// One actual PMAX8 engine. NPOS6/8 reuse every row's weights across all
// positions. The compiler-staging mutant swaps position addresses in the real
// residual SRAM; expected answers retain original position identity.
module tb_hgi_hc_native_vm_mtp_static(input wire clk,sink_clk);
    localparam R=80,W=32,ROWS=24;
    reg rst_n=0;
    integer npos=8,cycle=0,state=0,fill=0,row=0,age=0,seen=0,errors=0,tailseen=0,sinkslot=0,pc=0;
    integer imagewords=0,cfgi=0,startedge=0;
    reg [255:0] image[0:2047];
    string imagefile;
    wire cfgwe=(state==6);
    wire vm_launch=(state==8&&age==10);
    wire [135:0] vm_rq;wire [7:0] vm_read;wire [2055:0] vm_rr;
    wire native_wave_v,native_done,native_fault;wire [9:0] native_word;wire [8191:0] native_wave;
    reg [4*8*281-1:0] fill_q;
    wire [4*2056-1:0] responses;wire [4*8*18-1:0] bank_status;wire [11:0] tapfault;
    wire startv=(state==7&&cycle==startedge);
    wire [255:0] cfgdata=image[cfgi];
    wire [9:0] staged_xword=10'(fill);
    wire program_done,program_active;
    task loadimage(input integer kind,input integer idx);
        begin
            if(kind==0)begin imagefile=$sformatf("row_n%0d_r%0d.mem",npos,idx);imagewords=period;end
            else begin imagefile=$sformatf("tail_p%0d.mem",idx);imagewords=500;end
            $readmemh(imagefile,image,0,imagewords-1);
        end
    endtask
    reg [31:0] wm[0:ROWS*8*R*W-1],expm[0:8*24-1],tail_exp[0:8*24-1],bm[0:23],sm[0:2];
    reg [15:0] xm[0:8*8*R*W-1];
    reg [2223:0] ap;
    reg [8191:0] xwave;
    reg raw_read;
    wire [767:0] bases,result;
    wire [95:0] scales;
    wire rv,fault,tv;
    wire [31:0] rd;
    wire [4:0] ri;
    wire [2:0] rp,tp;
    wire mutate=$test$plusargs("MUTANT");
    wire early=1;
    wire [15:0] ssbase=early?160:180;
    wire [15:0] rowbase=early?264:284;
    wire [15:0] period=(early?280:300)+160*(npos-1);
    wire [9:0] xword=10'(fill);
    initial begin
        if($value$plusargs("NPOS=%d",npos))begin end
        if(npos!=6&&npos!=8)$fatal(1,"production NPOS6/8 only");
        $readmemh("hc_static_w.mem",wm);$readmemh("hc_static_x.mem",xm);$readmemh("hc_static_exp.mem",expm);
        $readmemh("engine_tail_exp.mem",tail_exp);$readmemh("engine_base.mem",bm);$readmemh("engine_scale.mem",sm);
    end
    for(genvar j=0;j<24;j=j+1)assign bases[j*32+:32]=bm[j];
    for(genvar j=0;j<3;j=j+1)assign scales[j*32+:32]=sm[j];
    always @*begin
        ap=0;xwave=0;raw_read=0;
        if(state==2)for(integer b=0;b<8;b=b+1)begin
            ap[b*278+277]=1;ap[b*278+273+:3]=3'(b);ap[b*278+264+:9]=9'(fill);ap[b*278+:8]=8'hff;
            for(integer q=0;q<8;q=q+1)ap[b*278+8+32*q+:32]=wm[((row*8+b)*R+fill/4)*W+(fill%4)*8+q];
        end
        if(state==3&&age>=0&&age<320&&row<23)for(integer b=0;b<8;b=b+1)begin
            ap[b*278+277]=1;ap[b*278+276]=1'((row+1)%2);
            ap[b*278+273+:3]=3'(b);ap[b*278+264+:9]=9'(age);ap[b*278+:8]=8'hff;
            for(integer q=0;q<8;q=q+1)ap[b*278+8+32*q+:32]=wm[(((row+1)*8+b)*R+age/4)*W+(age%4)*8+q];
        end
        fill_q=0;
        if(state==1)for(integer b=0;b<8;b=b+1)begin:fillsector
            integer sector,sid,position,chunk,word_,lane;
            reg [255:0] data;
            sector=fill*8+b;sid=(sector>>13)&3;position=sector/2560;chunk=sector%2560;
            word_=position*80+chunk/32;lane=chunk%32;
            for(integer j=0;j<8;j=j+1)data[j*32+:32]={xm[(j*640+word_)*32+lane],16'd0};
            if(mutate&&sector==0)data[31:0]=32'h3f800000;
            fill_q[(sid*8+b)*281+:281]={1'b1,16'(sector),data,8'hff};
        end
        if(state==3)for(integer p=0;p<8;p=p+1)
            if(p<npos&&(age==ssbase+160*p||age==rowbase+160*p))raw_read=1;
    end
    ot_hgi_hc_programmed_mtp_static #(.ROW_LOOP(1)) dut(.clk(clk),.sink_clk(sink_clk),.rst_n(rst_n),
        .cfg_we(cfgwe),.cfg_addr(11'(cfgi)),.cfg_data(cfgdata),
        .start_v(startv),.start_base(11'd0),.start_limit(12'(imagewords)),.start_loops((row<24)?16'd24:16'd1),
        .weight_ap(ap),.x_wave_v(native_wave_v),.x_wave_word(native_word),.x_wave(native_wave),
        .gathered_mix_v(1'b0),.gathered_mix_row(5'd0),.gathered_mix_pos(3'd0),.gathered_mix_data(32'd0),
        .bases(bases),.scales(scales),.row_result_v(rv),.row_result_id(ri),.row_result_pos(rp),.row_result(rd),
        .result_v(tv),.result(result),.tail_result_pos(tp),.tail_e_ready(),
        .program_done(program_done),.program_active(program_active),.fault(fault));
    ot_hgi_hc_residual_vm_static #(.MUT_POSITION(0)) residual_reader(
        .clk(clk),.rst_n(rst_n),.launch(vm_launch),.npos(4'(npos)),.base_sector(16'd0),
        .local_rq(vm_rq),.local_read(vm_read),.local_rr(vm_rr),.x_wave_v(native_wave_v),
        .x_wave_word(native_word),.x_wave(native_wave),.done(native_done),.fault(native_fault));
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
                .eg(),.pq(285'd0),.pr(),.status(bank_status[(sid*8+b)*18+:18]));
        end
        begin:station0
            wire [135:0] localq;
            for(genvar b=0;b<8;b=b+1)assign localq[b*17+:17]={0==2&&vm_rq[b*17+16]&&vm_rq[b*17+13+:2]==sid,vm_rq[b*17+:16]};
            ot_hbm_vm_lg_static_tap #(.READ_RETURN(10+4*0),.WRITE_RETURN(7+4*0)) tap(
                .clk(clk),.rst_n(rst_n),.local_rq(localq),.far_rq(0==2?136'd0:nrq[(0+1)*136+:136]),
                .local_wq(2248'd0),.far_wq(0==2?2248'd0:nwq[(0+1)*2248+:2248]),
                .local_read({8{0==2}}),.local_write(8'd0),.near_rq(nrq[(0)*136+:136]),.near_wq(nwq[(0)*2248+:2248]),
                .near_rr(0==0?bankrr:frr[(0-1)*2056+:2056]),.near_w_done(0==0?bankdone:fd[(0-1)*8+:8]),
                .local_rr(lrr[(0)*2056+:2056]),.far_rr(frr[(0)*2056+:2056]),.local_w_done(ld[(0)*8+:8]),.far_w_done(fd[(0)*8+:8]),.fault(tapfault[sid*3+0]));
        end
        begin:station1
            wire [135:0] localq;
            for(genvar b=0;b<8;b=b+1)assign localq[b*17+:17]={1==2&&vm_rq[b*17+16]&&vm_rq[b*17+13+:2]==sid,vm_rq[b*17+:16]};
            ot_hbm_vm_lg_static_tap #(.READ_RETURN(10+4*1),.WRITE_RETURN(7+4*1)) tap(
                .clk(clk),.rst_n(rst_n),.local_rq(localq),.far_rq(1==2?136'd0:nrq[(1+1)*136+:136]),
                .local_wq(2248'd0),.far_wq(1==2?2248'd0:nwq[(1+1)*2248+:2248]),
                .local_read({8{1==2}}),.local_write(8'd0),.near_rq(nrq[(1)*136+:136]),.near_wq(nwq[(1)*2248+:2248]),
                .near_rr(1==0?bankrr:frr[(1-1)*2056+:2056]),.near_w_done(1==0?bankdone:fd[(1-1)*8+:8]),
                .local_rr(lrr[(1)*2056+:2056]),.far_rr(frr[(1)*2056+:2056]),.local_w_done(ld[(1)*8+:8]),.far_w_done(fd[(1)*8+:8]),.fault(tapfault[sid*3+1]));
        end
        begin:station2
            wire [135:0] localq;
            for(genvar b=0;b<8;b=b+1)assign localq[b*17+:17]={2==2&&vm_rq[b*17+16]&&vm_rq[b*17+13+:2]==sid,vm_rq[b*17+:16]};
            ot_hbm_vm_lg_static_tap #(.READ_RETURN(10+4*2),.WRITE_RETURN(7+4*2)) tap(
                .clk(clk),.rst_n(rst_n),.local_rq(localq),.far_rq(2==2?136'd0:nrq[(2+1)*136+:136]),
                .local_wq(2248'd0),.far_wq(2==2?2248'd0:nwq[(2+1)*2248+:2248]),
                .local_read({8{2==2}}),.local_write(8'd0),.near_rq(nrq[(2)*136+:136]),.near_wq(nwq[(2)*2248+:2248]),
                .near_rr(2==0?bankrr:frr[(2-1)*2056+:2056]),.near_w_done(2==0?bankdone:fd[(2-1)*8+:8]),
                .local_rr(lrr[(2)*2056+:2056]),.far_rr(frr[(2)*2056+:2056]),.local_w_done(ld[(2)*8+:8]),.far_w_done(fd[(2)*8+:8]),.fault(tapfault[sid*3+2]));
        end
    end
    for(genvar b=0;b<8;b=b+1)begin:return_mux
        wire [256:0] sid_response[0:3];
        for(genvar q=0;q<4;q=q+1)assign sid_response[q]=responses[q*2056+b*257+:257]&{257{responses[q*2056+b*257+256]}};
        assign vm_rr[b*257+:257]=sid_response[0]|sid_response[1]|sid_response[2]|sid_response[3];
    end

    always @(posedge clk)begin
        cycle<=cycle+1;
        if(cycle==4)begin rst_n<=1;state<=1;fill<=0;end
        if(state==1)begin if(fill==320*npos-1)begin state<=8;age<=0;fill<=0;end else fill<=fill+1;end
        if(state==8)begin age<=age+1;if(native_done)begin state<=4;age<=0;end end
        if(state==4)begin age<=age+1;if(age==3)begin state<=2;fill<=0;end end
        if(state==2)begin if(fill==319)begin loadimage(0,0);state<=6;cfgi<=0;end else fill<=fill+1;end
        if(state==6)begin
            if(cfgi==imagewords-1)begin
                state<=7;
                // Every first consumer edge is aligned to global sink phase0.
                startedge<=((cycle+1+10+5+6)/7)*7-5;
            end else cfgi<=cfgi+1;
        end
        if(state==7&&cycle==startedge)begin state<=(row<24)?3:5;age<=-4;end
        if(rst_n&&(fault||native_fault||(|tapfault)||(|bank_status)))$fatal(1,"PROGRAMMED_MTP fault state%0d row%0d age%0d",state,row,age);
        if(state==3||state==5)age<=age+1;
        if(state==3)begin
            if(rv)begin
                seen<=seen+1;
                if(age!=269+160*rp||ri!=row||rp>=npos||rd!==expm[rp*24+row])$fatal(1,"programmed row data/time mismatch row%0d pos%0d age%0d",row,rp,age);
            end
            if(age==period-1)begin
                if(seen!=(row+1)*npos)$fatal(1,"missing repeated programme row results");
                if(row==23)begin
                    if(!program_done)$fatal(1,"programme failed final fixed loop boundary");
                    row<=24;pc<=0;loadimage(1,0);state<=6;cfgi<=0;
                end else begin
                    if(program_done)$fatal(1,"programme ended before24row loop");
                    row<=row+1;age<=0;
                end
            end
        end
        if(state==5)begin
            if(tv)begin
                tailseen<=tailseen+1;
                if(tp!=pc)$fatal(1,"programmed tail identity");
                for(integer j=0;j<24;j=j+1)if(result[j*32+:32]!==tail_exp[pc*24+j])$fatal(1,"programmed tail arithmetic pos%0d word%0d",pc,j);
            end
            if(program_done)begin
                if(tailseen!=pc+1)$fatal(1,"programmed tail missing");
                if(pc==npos-1)begin
                    $display("HC_NATIVE_VM_PROGRAMMED_MTP_DONE npos=%0d rows=%0d tails=%0d cycles=%0d",npos,seen,tailseen,cycle);$finish;
                end else begin
                    pc<=pc+1;loadimage(1,pc+1);state<=6;cfgi<=0;
                end
            end
        end
        if(cycle>95000)$fatal(1,"programmed MTP bench watchdog");
    end
endmodule
