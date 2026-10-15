`timescale 1ns/1ps
// One actual PMAX8 engine. NPOS6/8 reuse every row's weights across all
// positions. The compiler-staging mutant swaps position addresses in the real
// residual SRAM; expected answers retain original position identity.
module tb_hgi_hc_programmed_mtp_static(input wire clk,sink_clk);
    localparam R=80,W=32,ROWS=24;
    reg rst_n=0;
    integer npos=8,cycle=0,state=0,fill=0,row=0,age=0,seen=0,errors=0,tailseen=0,sinkslot=0,pc=0;
    integer imagewords=0,cfgi=0,startedge=0;
    reg [255:0] image[0:2047];
    string imagefile;
    wire cfgwe=(state==6);
    wire startv=(state==7&&cycle==startedge);
    wire [255:0] cfgdata=image[cfgi]^((mutate&&cfgi==1024)?(256'd1<<233):256'd0);
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
        if(state==1)for(integer l=0;l<32;l=l+1)for(integer b=0;b<8;b=b+1)
            xwave[l*256+b*32+:32]={xm[(b*640+fill)*W+l],16'd0};
        if(state==3)for(integer p=0;p<8;p=p+1)
            if(p<npos&&(age==ssbase+160*p||age==rowbase+160*p))raw_read=1;
    end
    ot_hgi_hc_programmed_mtp_static dut(.clk(clk),.sink_clk(sink_clk),.rst_n(rst_n),
        .cfg_we(cfgwe),.cfg_addr(11'(cfgi)),.cfg_data(cfgdata),
        .start_v(startv),.start_base(11'd0),.start_limit(12'(imagewords)),.start_loops(16'd1),
        .weight_ap(ap),.x_wave_v(state==1),.x_wave_word(xword),.x_wave(xwave),
        .gathered_mix_v(1'b0),.gathered_mix_row(5'd0),.gathered_mix_pos(3'd0),.gathered_mix_data(32'd0),
        .bases(bases),.scales(scales),.row_result_v(rv),.row_result_id(ri),.row_result_pos(rp),.row_result(rd),
        .result_v(tv),.result(result),.tail_result_pos(tp),.tail_e_ready(),
        .program_done(program_done),.program_active(program_active),.fault(fault));
    always @(posedge clk)begin
        cycle<=cycle+1;
        if(cycle==4)begin rst_n<=1;state<=1;fill<=0;end
        if(state==1)begin if(fill==80*npos-1)begin state<=2;fill<=0;end else fill<=fill+1;end
        if(state==2)begin if(fill==319)begin loadimage(0,0);state<=6;cfgi<=0;end else fill<=fill+1;end
        if(state==6)begin
            if(cfgi==imagewords-1)begin
                state<=7;
                // Every first consumer edge is aligned to global sink phase0.
                startedge<=((cycle+1+10+5+6)/7)*7-5;
            end else cfgi<=cfgi+1;
        end
        if(state==7&&cycle==startedge)begin state<=(row<24)?3:5;age<=-4;end
        if(rst_n&&fault)$fatal(1,"PROGRAMMED_MTP fault state%0d row%0d age%0d",state,row,age);
        if(state==3||state==5)age<=age+1;
        if(state==3)begin
            if(rv)begin
                seen<=seen+1;
                if(age!=269+160*rp||ri!=row||rp>=npos||rd!==expm[rp*24+row])$fatal(1,"programmed row data/time mismatch row%0d pos%0d age%0d",row,rp,age);
            end
            if(program_done)begin
                // Final word emits done one edge before the consumer observes it.
                if(seen!=(row+1)*npos)$fatal(1,"missing programmed row results");
                if(row==23)begin row<=24;pc<=0;loadimage(1,0);end
                else begin row<=row+1;loadimage(0,row+1);end
                state<=6;cfgi<=0;
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
                    $display("HC_PROGRAMMED_MTP_DONE npos=%0d rows=%0d tails=%0d cycles=%0d",npos,seen,tailseen,cycle);$finish;
                end else begin
                    pc<=pc+1;loadimage(1,pc+1);state<=6;cfgi<=0;
                end
            end
        end
        if(cycle>85000)$fatal(1,"programmed MTP bench watchdog");
    end
endmodule
