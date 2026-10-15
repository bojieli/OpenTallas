`timescale 1ns/1ps
// One actual PMAX8 engine. NPOS6/8 reuse every row's weights across all
// positions. The compiler-staging mutant swaps position addresses in the real
// residual SRAM; expected answers retain original position identity.
module tb_hgi_hc_checkpoint_native_mtp_static(input wire clk,sink_clk,hbm_clk);
    localparam R=80,W=32,ROWS=24;
    reg rst_n=0;
    integer npos=8,cycle=0,state=0,fill=0,row=0,age=0,seen=0,errors=0,tailseen=0,sinkslot=0,pc=0;
    integer imagewords=0,cfgi=0,startedge=0;
    reg [255:0] image[0:2047];
    string imagefile;
    wire cfgwe=(state==6);
    wire vm_launch=(state==8&&age==10);
    wire [135:0] vm_rq,bridge_rq;wire [7:0] vm_read;
    wire [2247:0] result_wq;wire [7:0] result_write;wire result_fault;
    integer result_sectors=0;
    for(genvar rb=0;rb<8;rb=rb+1)assign vm_rq[rb*17+:17]=(state==9)?{age>=24&&age<27,16'(28672+(age-24)*8+rb)}:bridge_rq[rb*17+:17];wire [2055:0] vm_rr;
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
    wire [2223:0] ap;
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
        xwave=0;raw_read=0;
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
        .local_rq(bridge_rq),.local_read(vm_read),.local_rr(state==9?2056'd0:vm_rr),.x_wave_v(native_wave_v),
        .x_wave_word(native_word),.x_wave(native_wave),.done(native_done),.fault(native_fault));
    ot_hgi_hc_result_vm_static result_writer(.clk(clk),.rst_n(rst_n),
        .store_slot(state==5&&age==493),.base_sector(16'd28672),.store_position(3'(pc)),
        .result_v(tv),.result_position(tp),.result(result),.local_wq(result_wq),.local_write(result_write),.fault(result_fault));
    for(genvar sid=0;sid<4;sid=sid+1)begin:quadrant
        wire [407:0] nrq;wire [6743:0] nwq;
        wire [6167:0] lrr,frr;wire [23:0] ld,fd;
        wire [2055:0] bankrr;wire [7:0] bankdone;
        assign responses[sid*2056+:2056]=lrr[(2)*2056+:2056];
        for(genvar b=0;b<8;b=b+1)begin:bank
            wire [770:0] r;
            assign bankrr[b*257+:257]=r[0+:257];
            ot_vms_bank_static #(.RG(3),.WG(1)) mem(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'(sid)),
                .rslot_v(1'b1),.rslot(2'd0),.wslot_v(1'b1),.wslot(state==1?3'd5:3'd0),
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
            wire [2247:0] result_localwq;
            wire [7:0] result_localselect;
            for(genvar wb=0;wb<8;wb=wb+1)begin:result_route
                assign result_localwq[wb*281+:281]={result_wq[wb*281+280]&&result_wq[wb*281+277+:2]==sid,result_wq[wb*281+:280]};
                assign result_localselect[wb]=result_write[wb]&&result_wq[wb*281+277+:2]==sid;
            end
            for(genvar b=0;b<8;b=b+1)assign localq[b*17+:17]={2==2&&vm_rq[b*17+16]&&vm_rq[b*17+13+:2]==sid,vm_rq[b*17+:16]};
            ot_hbm_vm_lg_static_tap #(.READ_RETURN(10+4*2),.WRITE_RETURN(7+4*2)) tap(
                .clk(clk),.rst_n(rst_n),.local_rq(localq),.far_rq(2==2?136'd0:nrq[(2+1)*136+:136]),
                .local_wq(result_localwq),.far_wq(2==2?2248'd0:nwq[(2+1)*2248+:2248]),
                .local_read({8{2==2}}),.local_write(result_localselect),.near_rq(nrq[(2)*136+:136]),.near_wq(nwq[(2)*2248+:2248]),
                .near_rr(2==0?bankrr:frr[(2-1)*2056+:2056]),.near_w_done(2==0?bankdone:fd[(2-1)*8+:8]),
                .local_rr(lrr[(2)*2056+:2056]),.far_rr(frr[(2)*2056+:2056]),.local_w_done(ld[(2)*8+:8]),.far_w_done(fd[(2)*8+:8]),.fault(tapfault[sid*3+2]));
        end
    end
    for(genvar b=0;b<8;b=b+1)begin:return_mux
        wire [256:0] sid_response[0:3];
        for(genvar q=0;q<4;q=q+1)assign sid_response[q]=responses[q*2056+b*257+:257]&{257{responses[q*2056+b*257+256]}};
        assign vm_rr[b*257+:257]=sid_response[0]|sid_response[1]|sid_response[2]|sid_response[3];
    end

 wire [127:0] k_v,k_we,kr_rdy;reg [127:0] k_rdy='1,k_wr_done=0,kr_v=0;
 wire [3839:0] k_addr;wire [511:0] k_len;wire [2175:0] k_tag;
 wire [32767:0] k_wdata;wire [4095:0] k_wstrb;
 reg [2175:0] kr_tag=0;reg [511:0] kr_beat=0;reg [32767:0] kr_data=0;
 reg [255:0] checkpoint_image[0:61439];reg pending[0:127][0:7];integer delay_q[0:127][0:7];
 reg [16:0] tag_q[0:127][0:7];reg [255:0] data_q[0:127][0:7];
 reg injected=0;reg [16:0] oldest_tag[0:127];reg have_oldest[0:127];
 integer fault_mode=0;
 integer requests=0,phyresponses=0;
 localparam PHY_LATENCY=80;
 function automatic [4:0] pc_of(input [29:0] s);pc_of=s[6:2]^s[11:7]^s[16:12];endfunction
 always @(posedge hbm_clk)begin:phy
  integer s,pc,i,bank,offset,row,free_slot,reply_slot;reg [29:0] sector;reg [34:0] byte_address;
  if(rst_n)begin
   for(i=0;i<128;i=i+1)begin
    if(kr_v[i]&&kr_rdy[i])begin kr_v[i]<=0;phyresponses=phyresponses+1;end
    reply_slot=-1;
    for(integer os=0;os<8;os=os+1)if(pending[i][os])begin
     if(delay_q[i][os]==0&&reply_slot<0)reply_slot=os;
     else if(delay_q[i][os]>0)delay_q[i][os]=delay_q[i][os]-1;
    end
    if(reply_slot>=0&&!kr_v[i])begin
     kr_v[i]<=1;kr_tag[i*17+:17]<=tag_q[i][reply_slot];
     if(fault_mode==1&&!injected)begin kr_tag[i*17+:17]<=tag_q[i][reply_slot]^17'h10000;injected<=1;end
     if(fault_mode==2&&!injected&&requests>=2800)begin kr_tag[i*17+:17]<=oldest_tag[i];injected<=1;end
     kr_data[i*256+:256]<=data_q[i][reply_slot];pending[i][reply_slot]=0;
    end
    if(i==0&&fault_mode==3&&!injected&&phyresponses>=2560&&!kr_v[0])begin
     kr_v[0]<=1;kr_tag[0+:17]<=oldest_tag[0];injected<=1;
    end
    if(k_v[i]&&k_rdy[i])begin
     s=i/32;pc=i%32;sector=k_addr[i*30+:30];byte_address={sector,5'b0};
     if(pc_of(sector)!=pc)$fatal(1,"actual XOR PC mismatch");
     free_slot=-1;
     for(integer os=0;os<8;os=os+1)if(!pending[i][os]&&free_slot<0)free_slot=os;
     if(k_we[i]||k_len[i*4+:4]!=1||free_slot<0)$fatal(1,"PHY command ownership");
     if(byte_address<35'd21474836480||byte_address>=35'd21474836480+24*81920)$fatal(1,"not actual20GiB row address %h",byte_address);
     row=(byte_address-35'd21474836480)/81920;bank=((byte_address-35'd21474836480)%81920)/10240;offset=((byte_address-35'd21474836480)%10240)/32;
     if(bank%4!=s||offset>=320)$fatal(1,"stripe bank stack/segment mismatch");
     data_q[i][free_slot]=checkpoint_image[row*2560+bank*320+offset] ^ (($test$plusargs("WEIGHT_MUTANT")&&row==0&&bank==5&&offset==319)?256'h10000000:256'd0);tag_q[i][free_slot]=k_tag[i*17+:17];pending[i][free_slot]=1;delay_q[i][free_slot]=PHY_LATENCY+(requests*7+i)%13;
     if(!have_oldest[i])begin oldest_tag[i]=k_tag[i*17+:17];have_oldest[i]=1;end
     requests=requests+1;
    end
   end
  end
 end

 wire [3:0] reserve_ready;wire [7:0] fetched_ready;
 wire reserve_v=(state==4&&(age==0||age==1))||
  (state==2&&(age==330||age==660))||
  (state==3&&row<22&&(age==330||age==660));
 wire reserve_half=(state==4)?age==1:age==660;
 wire [4:0] reserve_row=(state==4)?5'd0:(state==2)?5'd1:5'(row+2);
 wire [34:0] reserve_row_local_byte=35'd21474836480+reserve_row*81920;
 wire [15:0] reserve_epoch=16'h6001+reserve_row;
 wire drain_v=(state==2&&(age==0||age==330))||
  (state==3&&row<23&&(age==0||age==330));
 wire drain_half=age==330;
 wire [4:0] drain_row=(state==2)?5'd0:5'(row+1);
 wire drain_slot=drain_row[0];wire [15:0] drain_epoch=16'h6001+drain_row;
 wire half_done,done_half,weight_fault;
 ot_hgi_hc_prefetch_direct_static prefetch(
  .stream_clk(clk),.stream_rst_n(rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(rst_n),
  .reserve_v(reserve_v),.reserve_half(reserve_half),.reserve_row_local_byte(reserve_row_local_byte),
  .reserve_epoch(reserve_epoch),.reserve_ready(reserve_ready),.fetched_ready(fetched_ready),
  .drain_v(drain_v),.drain_half(drain_half),.drain_slot(drain_slot),.drain_epoch(drain_epoch),
  .half_done(half_done),.done_half(done_half),.ap(ap),.fault(weight_fault),
  .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),
  .k_wdata(k_wdata),.k_wstrb(k_wstrb),.k_wr_done(k_wr_done),
  .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data));
 always @(posedge clk)if(rst_n)begin
  if(weight_fault)$fatal(1,"actual checkpoint weight prefetch fault row%0d age%0d",row,age);
  if(reserve_v&&reserve_ready!=15)$fatal(1,"checkpoint reserve deadline");
  if(drain_v&&(fetched_ready&(drain_half?8'haa:8'h55))!=(drain_half?8'haa:8'h55))
   $fatal(1,"checkpoint drain deadline row%0d age%0d ready%h",drain_row,age,fetched_ready);
 end
 initial begin
  $readmemh("all24rows.hex",checkpoint_image);
  for(integer i=0;i<128;i=i+1)begin have_oldest[i]=0;oldest_tag[i]=0;
   for(integer os=0;os<8;os=os+1)begin pending[i][os]=0;delay_q[i][os]=0;end
  end
 end

    always @(posedge clk)begin
        cycle<=cycle+1;
        if(cycle==4)begin rst_n<=1;state<=1;fill<=0;end
        if(state==1)begin if(fill==320*npos-1)begin state<=8;age<=0;fill<=0;end else fill<=fill+1;end
        if(state==8)begin age<=age+1;if(native_done)begin state<=4;age<=0;end end
        if(state==4)begin age<=age+1;if(age>4&&fetched_ready==255)begin state<=2;age<=0;fill<=0;end end
        if(state==2)begin age<=age+1;if(age==670)begin loadimage(0,0);state<=6;cfgi<=0;end end
        if(state==6)begin
            if(cfgi==imagewords-1)begin
                state<=7;
                // Every first consumer edge is aligned to global sink phase0.
                startedge<=((cycle+1+10+5+6)/7)*7-5;
            end else cfgi<=cfgi+1;
        end
        if(state==7&&cycle==startedge)begin state<=(row<24)?3:5;age<=-4;end
        if(rst_n&&(fault||result_fault||native_fault||(|tapfault)||(|bank_status)))$fatal(1,"PROGRAMMED_MTP fault state%0d row%0d age%0d",state,row,age);
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
                    state<=9;age<=0;
                end else begin
                    pc<=pc+1;loadimage(1,pc+1);state<=6;cfgi<=0;
                end
            end
        end
        if(state==9)begin
            age<=age+1;
            if(age>=43&&age<46)for(integer b=0;b<8;b=b+1)begin:verify_result
                integer sector,position,part;
                sector=(age-43)*8+b;position=sector/3;part=sector%3;
                if(position<npos)begin
                    if(!vm_rr[b*257+256])$fatal(1,"missing nativeHCwriteback read response");
                    for(integer w=0;w<8;w=w+1)
                        if(vm_rr[b*257+w*32+:32]!==tail_exp[position*24+part*8+w])
                            $fatal(1,"nativeHCwriteback data mismatch pos%0d word%0d",position,part*8+w);
                    result_sectors<=sector+1;
                end
            end
            if(age==50)begin
                if(requests!=61440||phyresponses!=61440)$fatal(1,"checkpoint PHY count requests%0d responses%0d",requests,phyresponses);
                if(result_sectors!=npos*3)$fatal(1,"nativeHCwritebackcount%0d",result_sectors);
                $display("HC_CHECKPOINT_NATIVE_MTP_DONE npos=%0d rows=%0d tails=%0d nativeVMresultwords=%0d cycles=%0d",npos,seen,tailseen,result_sectors*8,cycle);$finish;
            end
        end
        if(cycle>105000)$fatal(1,"programmed MTP bench watchdog");
    end
endmodule
