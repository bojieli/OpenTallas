`timescale 1ns/1ps
`default_nettype none
module tb_hgi_hc_owned_p1_sys1_prepared(input wire clk,sink_clk);

    reg rst_n=0;
    wire [135:0] local_rq[0:2];
    reg [2247:0] local_wq[0:2];
    wire [7:0] local_read[0:2];
    reg [7:0] local_write[0:2];
    wire [135:0] near_rq[0:2];
    wire [2247:0] near_wq[0:2];
    wire [2055:0] local_rr[0:2],far_rr[0:2];
    wire [7:0] local_done[0:2],far_done[0:2];
    wire [2:0] tap_fault;
    wire [2055:0] bank_rr;
    reg drop_response=0;
    wire [2055:0] bank_rr_input;
    wire [7:0] bank_done;
    wire [143:0] bank_status;
    for(genvar b=0;b<8;b=b+1)begin:memory
        wire [770:0] rr;
        assign bank_rr[b*257+:257]=rr[0+:257];
        assign bank_rr_input[b*257+:257]={bank_rr[b*257+256]&&!(drop_response&&b==0),bank_rr[b*257+:256]};
        ot_vms_bank_static #(.RG(3),.WG(1)) bank(
            .clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd2),
            .rslot_v(1'b1),.rslot(2'd0),.wslot_v(1'b1),.wslot(3'd0),
            .rq({34'd0,near_rq[0][b*17+:17]}),.rr(rr),
            .wq(near_wq[0][b*281+:281]),.wq_done(bank_done[b]),
            .dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),
            .xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
            .eg(),.pq(285'd0),.pr(),.status(bank_status[b*18+:18]));
    end
    for(genvar s=0;s<3;s=s+1)begin:station
        wire [135:0] frq;
        wire [2247:0] fwq;
        wire [2055:0] nrr;
        wire [7:0] ndone;
        if(s==2)begin:end_station
            assign frq=0;assign fwq=0;
        end else begin:far_station
            assign frq=near_rq[s+1];assign fwq=near_wq[s+1];
        end
        if(s==0)begin:vm_return
            assign nrr=bank_rr_input;assign ndone=bank_done;
        end else begin:forward_return
            assign nrr=far_rr[s-1];assign ndone=far_done[s-1];
        end
        ot_hbm_vm_lg_static_tap #(.READ_RETURN(10+4*s),.WRITE_RETURN(7+4*s),.MUT(0)) tap(
            .clk(clk),.rst_n(rst_n),.local_rq(local_rq[s]),.far_rq(frq),
            .local_wq(local_wq[s]),.far_wq(fwq),.local_read(local_read[s]),.local_write(local_write[s]),
            .near_rq(near_rq[s]),.near_wq(near_wq[s]),.near_rr(nrr),.near_w_done(ndone),
            .local_rr(local_rr[s]),.far_rr(far_rr[s]),.local_w_done(local_done[s]),.far_w_done(far_done[s]),.fault(tap_fault[s]));
    end
    localparam integer ROW_FIRST=4096,GATHER=4496,TAIL_FIRST=4544;
    integer cycle=0,owned_seen=0,mix_seen=0,tail_seen=0;
    reg [31:0] weights[0:20479],mix_expected[0:23],tail_expected[0:23],base[0:23],scale[0:2];
    reg [15:0] residual[0:20479];
    reg [255:0] programme[0:2047];
    integer programme_words,expected_tail_cycle;
    wire [767:0] bases,result;
    wire [95:0] scales;
    wire row_v,tail_v,ef,af,gd,pa,pd;
    wire [4:0] row_id,mix_row;
    wire [2:0] row_pos,tail_pos,mix_pos;
    wire [31:0] row_data,mix_data;
    wire mix_v;
    reg [2223:0] weight_ap;
    reg [8191:0] x_wave;
    wire [2055:0] unused_residual_rr;
    wire gather_phase=cycle>=GATHER&&cycle<=GATHER+44;
    wire gather_launch=cycle==GATHER;
    wire cfg_we=cycle>=16&&cycle<16+programme_words;
    wire [10:0] cfg_addr=11'(cycle-16);
    wire [255:0] cfg_data=programme[cfg_addr];
    wire x_v=cycle>=16&&cycle<96;
    wire [9:0] x_word=10'(cycle-16);
    initial begin
        if(!$value$plusargs("WORDS=%d",programme_words))$fatal(1,"WORDS required");
        if(!$value$plusargs("TAIL_RESULT=%d",expected_tail_cycle))$fatal(1,"TAIL_RESULT required");
        $readmemh("owned_p1_programme.mem",programme,0,programme_words-1);
        $readmemh("owned_weights.mem",weights);$readmemh("residual.mem",residual);
        $readmemh("mix_expected.mem",mix_expected);$readmemh("tail_expected.mem",tail_expected);
        $readmemh("bases.mem",base);$readmemh("scales.mem",scale);
    end
    for(genvar j=0;j<24;j=j+1)assign bases[j*32+:32]=base[j];
    for(genvar j=0;j<3;j=j+1)assign scales[j*32+:32]=scale[j];
    assign local_rq[0]=0;assign local_rq[1]=0;assign local_read[0]=0;assign local_read[1]=0;
    always @*begin
        integer i,b,q;
        reg [31:0] word_;
        weight_ap=0;x_wave=0;
        for(integer st=0;st<3;st=st+1)begin local_wq[st]=0;local_write[st]=0;end
        // All24 words are an explicitly DECLARED post-collective fixture,
        // not a local projection bypass or an implemented HCOLL producer.
        if(cycle>=100&&cycle<103)begin
            i=cycle-100;b=(18136+i)%8;local_write[0][b]=1;
            local_wq[0][b*281+280]=1;local_wq[0][b*281+264+:16]=16'(18136+i);local_wq[0][b*281+:8]=8'hff;
            for(q=0;q<8;q=q+1)begin
                word_=mix_expected[i*8+q];
                if($test$plusargs("MUT_GATHER")&&i==0&&q==0)word_=32'h40000000;
                local_wq[0][b*281+8+32*q+:32]=word_;
            end
        end
        // One640-edge startup drain:320valid8-bank APbeats every2edges.
        if(cycle>=2048&&cycle<2688&&(cycle-2048)%2==0)begin
            i=(cycle-2048)/2;
            for(b=0;b<8;b=b+1)begin
                weight_ap[b*278+277]=1;weight_ap[b*278+276]=0;weight_ap[b*278+273+:3]=3'(b);
                weight_ap[b*278+264+:9]=9'(i);weight_ap[b*278+:8]=8'hff;
                for(q=0;q<8;q=q+1)begin
                    word_=weights[(b*80+i/4)*32+(i%4)*8+q];
                    if($test$plusargs("MUT_OWNED_ROW")&&b==0&&i==0&&q==0)word_=32'h3f800000;
                    weight_ap[b*278+8+q*32+:32]=word_;
                end
            end
        end
        if(x_v)for(integer l=0;l<32;l=l+1)for(b=0;b<8;b=b+1)
            x_wave[l*256+b*32+:32]={residual[(b*80+int'(x_word))*32+l],16'd0};
    end
    ot_hgi_hc_vm_gather_adapter_static #(.ENABLE_GATHER_READER(1)) gather(
        .clk(clk),.rst_n(rst_n),.gather_phase(gather_phase),.gather_launch(gather_launch),
        .gather_npos(4'd1),.gather_base_sector(16'd18136),.gather_stride_sector(16'd0),
        .residual_rq(136'd0),.residual_read(8'd0),.residual_rr(unused_residual_rr),
        .local_rq(local_rq[2]),.local_read(local_read[2]),.local_rr(local_rr[2]),
        .external_mix_v(1'b0),.external_mix_row(5'd0),.external_mix_pos(3'd0),.external_mix_data(32'd0),
        .gathered_mix_v(mix_v),.gathered_mix_row(mix_row),.gathered_mix_pos(mix_pos),.gathered_mix_data(mix_data),.gather_done(gd),.fault(af));
    ot_hgi_hc_programmed_sys1_split_mtp_static #(.ROW_LOOP(0),.TAIL_LOOP(0)) dut(
        .clk(clk),.reduction_clk(clk),.scalar_clk(clk),.sink_clk(sink_clk),.rst_n(rst_n),
        .weight_clk({32{clk}}),.residual_clk({16{clk}}),.bank_clk({8{clk}}),.mac_clk({32{clk}}),
        .cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .start_v(cycle==ROW_FIRST-5),.start_base(11'd0),.start_limit(12'(programme_words)),.start_loops(16'd1),
        .weight_ap(weight_ap),.x_wave_v(x_v),.x_wave_word(x_word),.x_wave(x_wave),
        .gathered_mix_v(mix_v),.gathered_mix_row(mix_row),.gathered_mix_pos(mix_pos),.gathered_mix_data(mix_data),
        .bases(bases),.scales(scales),.row_result_v(row_v),.row_result_id(row_id),.row_result_pos(row_pos),.row_result(row_data),
        .result_v(tail_v),.result(result),.tail_result_pos(tail_pos),.tail_e_ready(),.program_active(pa),.program_done(pd),.fault(ef));
    always @(posedge clk)begin
        cycle<=cycle+1;
        if(cycle==4)rst_n<=1;
        if(rst_n&&(ef||af||tap_fault!==0||bank_status!==0))$fatal(1,"P1 component source fault cycle=%0d arithmetic=%b adapter=%b",cycle,ef,af);
        if(row_v)begin
            if(cycle!=ROW_FIRST+322||row_id!=0||row_pos!=0||row_data!==mix_expected[0])$fatal(1,"owned row independently differs");
            owned_seen<=owned_seen+1;
        end
        if(mix_v)begin
            if(cycle!=GATHER+21+int'(mix_row)||mix_pos!=0||mix_data!==mix_expected[mix_row])$fatal(1,"actual VM declared gather mismatch");
            mix_seen<=mix_seen+1;
        end
        if(tail_v)begin
            if(cycle!=expected_tail_cycle||tail_pos!=0)$fatal(1,"tail fixed capture moved");
            for(integer j=0;j<24;j=j+1)if(result[j*32+:32]!==tail_expected[j])$fatal(1,"actual tail differs word=%0d",j);
            tail_seen<=tail_seen+1;
        end
        if(cycle==expected_tail_cycle+8)begin
            if(owned_seen!=1||mix_seen!=24||tail_seen!=1||pa)$fatal(1,"missing P1 mechanism coverage");
            $display("HC_OWNED_P1_COMPONENT PASS owned_row0_rank3=1 declared_postcollective_mix24=1 actual_VM_SRAM24=1 engine92=1 real_weight_SRAM64=1 tail24=1 synthetic_residual_bases_scales=1 no_wholeprofile_claim");$finish;
        end
    end
endmodule
`default_nettype wire
