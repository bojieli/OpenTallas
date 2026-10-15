`timescale 1ns/1ps
// Full production K=20480, 24 independent row windows. Inputs are external
// fixture payloads; every DUT weight/residual read passes real SRAM macros.
module tb_hgi_hc_projection_static(input wire clk);
    localparam R=80,W=32,ROWS=24;
    reg rst_n=0;
    integer cycle=0,state=0,fill=0,row=0,age=0,seen=0,errors=0;
    reg [31:0] wm[0:ROWS*8*R*W-1];
    reg [15:0] xm[0:8*R*W-1];
    reg [31:0] expected[0:ROWS-1];
    reg [2223:0] ap;
    wire [7:0] wr,xr,rdv,done;
    wire [127:0] wa,xa;
    wire [8191:0] raw;
    reg [8191:0] wd;
    wire [4095:0] rawx;
    reg [4095:0] xd;
    wire outv,last,fault,mfault;
    wire [31:0] data;
    wire launch=(state==3&&age==0);
    wire pop=(state==3&&(age==180||age==340));
    wire mutant=$test$plusargs("MUTANT");
    initial begin
        $readmemh("hc_static_w.mem",wm);
        $readmemh("hc_static_x.mem",xm);
        $readmemh("hc_static_exp.mem",expected);
    end
    always @* begin
        ap=0;
        if(state==2)for(integer b=0;b<8;b=b+1)begin
            ap[b*278+277]=1;
            ap[b*278+273+:3]=3'(b);
            ap[b*278+264+:9]=9'(fill);
            ap[b*278+:8]=8'hff;
            for(integer q=0;q<8;q=q+1)
                ap[b*278+8+32*q+:32]=wm[((row*8+b)*R+fill/4)*W+(fill%4)*8+q];
        end
    end
    wire [55:0] ra;
    for(genvar b=0;b<8;b=b+1)begin:banks
        assign ra[b*7+:7]=wa[b*16+:7];
        for(genvar m=0;m<2;m=m+1)begin:xmem
            reg [255:0] din;
            always @* for(integer j=0;j<16;j=j+1)
                din[j*16+:16]=xm[(b*R+(fill/2)%R)*W+m*16+j];
            ot_sram_1r1w_128x256_m1_r2c2 u_x(
                .clk(clk),.r_ce_in(xr[b]),.r_addr_in(xa[b*16+:7]),
                .rd_out(rawx[b*512+m*256+:256]),
                .w_ce_in(state==1&&fill%2==m),.w_addr_in(7'(fill/2)),
                .wd_in(din),.w_mask_in({256{1'b1}}),
                .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
        end
    end
    ot_hgi_hc_aperture_static weights(.clk(clk),.rst_n(rst_n),.ap(ap),
        .write_done(done),.read_v(wr),.read_slot(8'd0),.read_row(ra),
        .read_valid(rdv),.raw_weight(raw),.fault(mfault));
    always @(posedge clk)begin
        wd<=raw;xd<=rawx;
        // Corrupt actual FP32 lane operand, leaving memory/command timing intact.
        if(mutant)wd[31:0]<=32'h3f800000;
    end
    ot_hgi_hc_projection_static #(.PMAX(1),.OMAX(2),.DF(4)) dut(
        .clk(clk),.rst_n(rst_n),.launch(launch),.raw_read(pop),
        .npos(2'd1),.nout(2'd1),.nchunk(16'd2560),.scale(1'b1),
        .nf(32'h46a00000),.eps(32'h358637bd),.wbase(16'd0),.xbase(16'd0),
        .w_re(wr),.x_re(xr),.w_addr(wa),.x_addr(xa),.w_data(wd),.x_data(xd),
        .result_v(outv),.result_last(last),.result_pos(),.result_row(),
        .result_data(data),.fault(fault));
    always @(posedge clk)begin
        cycle<=cycle+1;
        if(cycle==4)begin rst_n<=1;state<=1;fill<=0;end
        if(state==1)begin
            if(fill==159)begin state<=2;fill<=0;end else fill<=fill+1;
        end
        if(state==2)begin
            if(fill==319)begin state<=4;age<=0;fill<=0;end else fill<=fill+1;
        end
        if(state==4)begin
            if(age==4)begin state<=3;age<=0;end else age<=age+1;
        end
        if(state==3)begin
            age<=age+1;
            if(fault||mfault)$fatal(1,"STATIC_SCHEDULE_FAULT row=%0d age=%0d",row,age);
            if(outv)begin
                seen<=seen+1;
                if(data!==expected[row]||!last)begin
                    errors<=errors+1;
                    $display("MISMATCH row=%0d got=%08x expected=%08x",row,data,expected[row]);
                end
                $display("STATIC_ROW row=%0d cycle=%0d",row,age);
            end
            if(age==355)begin
                if(seen!=row+1)$fatal(1,"missing fixed-calendar result row=%0d",row);
                if(row==ROWS-1)begin
                    $display("HC_STATIC_DONE rows=%0d K=20480 errors=%0d cycles=%0d",seen,errors,cycle);
                    if(errors)$fatal(1,"exact arithmetic mismatch");
                    $finish;
                end else begin row<=row+1;state<=2;fill<=0;end
            end
        end
        if(cycle>20000)$fatal(1,"testbench watchdog");
    end
endmodule
