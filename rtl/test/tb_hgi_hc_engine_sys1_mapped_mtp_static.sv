`timescale 1ns/1ps
// One actual PMAX8 engine. NPOS6/8 reuse every row's weights across all
// positions. The compiler-staging mutant swaps position addresses in the real
// residual SRAM; expected answers retain original position identity.
module tb_hgi_hc_engine_sys1_mapped_mtp_static(input wire clk,sink_clk);
    localparam R=80,W=32,ROWS=24;
    reg rst_n=0;
    integer npos=8,cycle=0,state=0,fill=0,row=0,age=0,seen=0,errors=0,tailseen=0,sinkslot=0,pc=0;
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
    wire mask_mutate=$test$plusargs("MASK_MUTANT");
    wire early=$test$plusargs("EARLY");
    wire [15:0] ssbase=53+(early?160:180);
    wire [15:0] rowbase=53+(early?264:284);
    wire [15:0] period=53+(early?280:300)+160*(npos-1);
    wire [9:0] xword=10'(mutate?(((fill/80)^1)*80+fill%80):fill);
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
        // Warm row0 is already stored. An attempted poison write to FP32word0
        // must be blocked by its zero mask bit; enabling it is the mutant.
        if(state==10)begin
            ap[277]=1;ap[273+:3]=0;ap[264+:9]=0;
            ap[0+:8]=mask_mutate?8'hff:8'hfe;
            for(integer q=0;q<8;q=q+1)ap[8+32*q+:32]=wm[q];
            ap[8+:32]=32'h3f800000;
        end
        if(state==3&&age<320&&row<23)for(integer b=0;b<8;b=b+1)begin
            ap[b*278+277]=1;ap[b*278+276]=1'((row+1)%2);
            ap[b*278+273+:3]=3'(b);ap[b*278+264+:9]=9'(age);ap[b*278+:8]=8'hff;
            for(integer q=0;q<8;q=q+1)ap[b*278+8+32*q+:32]=wm[(((row+1)*8+b)*R+age/4)*W+(age%4)*8+q];
        end
        if(state==1)for(integer l=0;l<32;l=l+1)for(integer b=0;b<8;b=b+1)
            xwave[l*256+b*32+:32]={xm[(b*640+fill)*W+l],16'd0};
        if(state==3)for(integer p=0;p<8;p=p+1)
            if(p<npos&&(age==ssbase+160*p||age==rowbase+160*p))raw_read=1;
    end
    ot_hgi_hc_engine_sys1_split_mtp_static dut(.clk(clk),.reduction_clk(clk),.scalar_clk(clk),.bank_clk({8{clk}}),.weight_clk({32{clk}}),.residual_clk({16{clk}}),.mac_clk({32{clk}}),.sink_clk(sink_clk),.rst_n(rst_n),
        .clear(cycle==4),.weight_ap(ap),.x_wave_v(state==1),.x_wave_word(xword),.x_wave(xwave),
        .row_launch(state==3&&age==0),.row_raw_read(raw_read),.row_weight_slot(1'(row%2)),
        .row_id(5'(row)),.row_npos(4'(npos)),.norm_eps(32'h358637bd),
        .gathered_mix_v(1'b0),.gathered_mix_row(5'd0),.gathered_mix_pos(3'd0),.gathered_mix_data(32'd0),
        .tail_launch(state==5&&age==0),.tail_position(3'(pc)),.sink_launch(state==5&&cycle==sinkslot),
        .sink_capture(state==5&&cycle==sinkslot+289),.bases(bases),.scales(scales),
        .row_result_v(rv),.row_result_id(ri),.row_result_pos(rp),.row_result(rd),
        .result_v(tv),.result(result),.tail_result_pos(tp),.tail_e_ready(),.fault(fault));
    always @(posedge clk)begin
        cycle<=cycle+1;
        if(cycle==4)begin rst_n<=1;state<=1;fill<=0;end
        if(state==1)begin if(fill==80*npos-1)begin state<=2;fill<=0;end else fill<=fill+1;end
        if(state==2)begin if(fill==319)begin state<=10;age<=0;fill<=0;end else fill<=fill+1;end
        if(state==10)begin state<=4;age<=0;end
        if(state==4)begin if(age==4)begin state<=3;age<=0;end else age<=age+1;end
        if(rst_n&&fault)$fatal(1,"MTP calendar fault state%0d row%0d age%0d npos%0d",state,row,age,npos);
        if(state==3)begin
            age<=age+1;
            if(rv)begin
                seen<=seen+1;
                if(age!=rowbase+5+160*rp||ri!=row||rp>=npos)$fatal(1,"MTP result identity/time row%0d pos%0d age%0d",row,rp,age);
                if(rd!==expm[rp*24+row])begin
                    errors=errors+1;if(errors<9)$display("MTP_ROW_MISMATCH row%0d pos%0d got=%08x exp=%08x",row,rp,rd,expm[rp*24+row]);
                end
            end
            if(age==period-1)begin
                if(seen!=(row+1)*npos)$fatal(1,"missing MTP row results");
                age<=0;
                if(row==23)begin state<=5;pc<=0;sinkslot<=((cycle+1+198+6)/7)*7;end
                else row<=row+1;
            end
        end
        if(state==5)begin
            age<=age+1;
            if(tv)begin
                tailseen<=tailseen+1;
                if(cycle!=sinkslot+290||tp!=pc)$fatal(1,"MTP tail capture moved or wrong position");
                for(integer j=0;j<24;j=j+1)if(result[j*32+:32]!==tail_exp[pc*24+j])begin
                    errors=errors+1;if(errors<9)$display("MTP_TAIL_MISMATCH pos%0d word%0d got=%08x exp=%08x",pc,j,result[j*32+:32],tail_exp[pc*24+j]);
                end
            end
            if(age==499)begin
                if(tailseen!=pc+1)$fatal(1,"missing MTP tail");
                age<=0;
                if(pc==npos-1)begin
                    $display("HC_MTP_DONE npos=%0d rows=%0d tail=%0d errors=%0d rowperiod=%0d cycles=%0d",npos,seen,tailseen,errors,period,cycle);
                    if(errors)$fatal(1,"MTP exact mismatch");
                    $finish;
                end
                pc<=pc+1;sinkslot<=((cycle+1+198+6)/7)*7;
            end
        end
        if(cycle>46000)$fatal(1,"MTP bench watchdog");
    end
endmodule
