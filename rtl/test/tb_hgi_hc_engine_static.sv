`timescale 1ns/1ps
module tb_hgi_hc_engine_static(input wire clk,sink_clk);
    localparam R=80,W=32,ROWS=24;
    reg rst_n=0;
    integer cycle=0,state=0,fill=0,row=0,age=0,seen=0,errors=0,tailseen=0,sinkslot=0;
    reg [31:0] wm[0:ROWS*8*R*W-1],expm[0:ROWS-1],tail_exp[0:23],bm[0:23],sm[0:2];
    reg [15:0] xm[0:8*R*W-1];
    reg [2223:0] ap;
    reg [8191:0] xwave;
    wire [767:0] bases,results[0:1];
    wire [95:0] scales;
    wire [1:0] rv,fault,tv;
    wire [31:0] rd[0:1];
    wire [4:0] ri[0:1];
    wire mutate=$test$plusargs("MUTANT");
    wire overlap=$test$plusargs("OVERLAP");
    initial begin
        $readmemh("hc_static_w.mem",wm);$readmemh("hc_static_x.mem",xm);$readmemh("hc_static_exp.mem",expm);
        $readmemh("engine_tail_exp.mem",tail_exp);$readmemh("engine_base.mem",bm);$readmemh("engine_scale.mem",sm);
    end
    for(genvar j=0;j<24;j=j+1)assign bases[j*32+:32]=bm[j];
    for(genvar j=0;j<3;j=j+1)assign scales[j*32+:32]=sm[j];
    always @*begin
        ap=0;xwave=0;
        if(state==2)for(integer b=0;b<8;b=b+1)begin
            ap[b*278+277]=1;ap[b*278+273+:3]=3'(b);ap[b*278+264+:9]=9'(fill);ap[b*278+:8]=8'hff;
            for(integer q=0;q<8;q=q+1)ap[b*278+8+32*q+:32]=wm[((row*8+b)*R+fill/4)*W+(fill%4)*8+q];
        end
        if(overlap&&state==3&&age<320&&row<23)for(integer b=0;b<8;b=b+1)begin
            ap[b*278+277]=1;ap[b*278+276]=1'((row+1)%2);
            ap[b*278+273+:3]=3'(b);ap[b*278+264+:9]=9'(age);ap[b*278+:8]=8'hff;
            for(integer q=0;q<8;q=q+1)ap[b*278+8+32*q+:32]=wm[(((row+1)*8+b)*R+age/4)*W+(age%4)*8+q];
        end
        if(state==1)for(integer l=0;l<32;l=l+1)for(integer b=0;b<8;b=b+1)
            xwave[l*256+b*32+:32]={xm[(b*R+fill)*W+l],16'd0};
    end
    for(genvar m=0;m<2;m=m+1)begin:engines
        ot_hgi_hc_engine_static #(.MUT_PRE(m)) dut(.clk(clk),.sink_clk(sink_clk),.rst_n(rst_n),
            .clear(cycle==4),.weight_ap(ap),.x_wave_v(state==1),.x_wave_row(7'(fill)),.x_wave(xwave),
            .row_launch(state==3&&age==0),.row_raw_read(state==3&&(age==180||age==340)),
            .row_weight_slot(overlap?1'(row%2):1'b0),.row_id(5'(row)),.norm_eps(32'h358637bd),
            .gathered_mix_v(1'b0),.gathered_mix_row(5'd0),.gathered_mix_data(32'd0),
            .tail_launch(state==5&&age==0),.sink_launch(state==5&&cycle==sinkslot),
            .sink_capture(state==5&&cycle==sinkslot+289),.bases(bases),.scales(scales),
            .row_result_v(rv[m]),.row_result_id(ri[m]),.row_result(rd[m]),.result_v(tv[m]),.result(results[m]),
            .tail_e_ready(),.fault(fault[m]));
    end
    always @(posedge clk)begin
        cycle<=cycle+1;
        if(cycle==4)begin rst_n<=1;state<=1;fill<=0;end
        if(state==1)begin if(fill==79)begin state<=2;fill<=0;end else fill<=fill+1;end
        if(state==2)begin if(fill==319)begin state<=4;age<=0;fill<=0;end else fill<=fill+1;end
        if(state==4)begin if(age==4)begin state<=3;age<=0;end else age<=age+1;end
        if(rst_n&&fault[mutate])$fatal(1,"engine calendar fault state%0d row%0d age%0d",state,row,age);
        if(state==3)begin
            age<=age+1;
            if(rv[mutate])begin
                seen<=seen+1;
                if(age!=345||ri[mutate]!=row||rd[mutate]!==expm[row])$fatal(1,"row mismatch/time row%0d age%0d",row,age);
            end
            if(age==355)begin
                if(seen!=row+1)$fatal(1,"missing result");
                if(row==23)begin state<=5;age<=0;sinkslot<=((cycle+1+217+6)/7)*7;end
                else begin row<=row+1;state<=overlap?3:2;fill<=0;age<=0;end
            end
        end
        if(state==5)begin
            age<=age+1;
            if(tv[mutate])begin
                tailseen<=tailseen+1;
                if(cycle!=sinkslot+290)$fatal(1,"tail capture moved");
                for(integer j=0;j<24;j=j+1)if(results[mutate][j*32+:32]!==tail_exp[j])begin
                    errors=errors+1;$display("ENGINE_TAIL_MISMATCH word%0d got=%08x exp=%08x",j,results[mutate][j*32+:32],tail_exp[j]);
                end
            end
            if(age==600)begin
                $display("HC_ENGINE_DONE rows=%0d tail=%0d errors=%0d cycles=%0d",seen,tailseen,errors,cycle);
                if(tailseen!=1||errors)$fatal(1,"engine tail mismatch");
                $finish;
            end
        end
        if(cycle>19000)$fatal(1,"engine bench watchdog");
    end
endmodule
