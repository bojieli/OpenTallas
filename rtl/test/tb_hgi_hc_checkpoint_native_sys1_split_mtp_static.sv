`timescale 1ns/1ps
// One actual 92-root PMAX8 engine; all roots tied for this functional gate.
// The 473756fb3 residual halves add one write edge. Actual cold priming
// finishes before any projection launch; no read-calendar extension is added.
// One actual PMAX8 engine. NPOS6/8 reuse every row's weights across all
// positions. The compiler-staging mutant swaps position addresses in the real
// residual SRAM; expected answers retain original position identity.
module tb_hgi_hc_checkpoint_native_sys1_split_mtp_static #(parameter integer COMMAND_NATIVE=0)(input wire clk,sink_clk,hbm_clk);
    localparam R=80,W=32,ROWS=24;
    localparam integer SYS_LAT=86, SYS_DELTA=SYS_LAT-33;
    reg rst_n=0;integer prime_i=0,cold_start=0;
    integer npos=8,cycle=0,state=0,fill=0,row=0,age=0,seen=0,errors=0,tailseen=0,sinkslot=0,pc=0;
    integer imagewords=0,cfgwords=0,cfgi=0,startedge=0;
    reg [255:0] image[0:2047];
    string imagefile;
    wire cfgwe=(state==6);
    wire vm_launch=(state==8&&age==10);
    wire [135:0] vm_rq,bridge_rq;wire [7:0] vm_read;
    wire [2247:0] result_wq;wire [7:0] result_write;
    integer result_sectors=0;
    for(genvar rb=0;rb<8;rb=rb+1)assign vm_rq[rb*17+:17]=(state==9)?{age>=24&&age<27,16'(28672+(age-24)*8+rb)}:bridge_rq[rb*17+:17];wire [2055:0] vm_rr;
    wire native_done;
    reg [4*8*281-1:0] fill_q;
    wire [4*2056-1:0] responses;wire [4*8*18-1:0] bank_status;wire [11:0] tapfault;
    wire startv=(state==7&&cycle==startedge);
    wire [255:0] cfgdata=image[cfgi];
    wire [9:0] staged_xword=10'(fill);
    wire program_done,program_active;
    task loadimage(input integer kind,input integer idx);
        begin
            imagefile=$sformatf("full_sys1_n%0d.mem",npos);imagewords=period;cfgwords=period+497;
            $readmemh(imagefile,image,0,cfgwords-1);
        end
    endtask
    reg [31:0] expm[0:8*24-1],tail_exp[0:8*24-1],bm[0:23],sm[0:2];
    reg [15:0] xm[0:8*8*R*W-1];
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
    wire [15:0] ssbase=early?(160+SYS_DELTA):(180+SYS_DELTA);
    wire [15:0] rowbase=early?(264+SYS_DELTA):(284+SYS_DELTA);
    wire [15:0] period=(early?280:300)+160*(npos-1)+SYS_DELTA;
    wire [9:0] xword=10'(fill);
    initial begin
        if($value$plusargs("NPOS=%d",npos))begin end
        if(npos!=6&&npos!=8)$fatal(1,"production NPOS6/8 only");
        $readmemh("hc_static_x.mem",xm);$readmemh("hc_static_exp.mem",expm);
        $readmemh("engine_tail_exp.mem",tail_exp);$readmemh("engine_base.mem",bm);$readmemh("engine_scale.mem",sm);
    end
    for(genvar j=0;j<24;j=j+1)assign bases[j*32+:32]=bm[j];
    for(genvar j=0;j<3;j=j+1)assign scales[j*32+:32]=sm[j];
    always @*begin
        xwave=0;raw_read=0;
        fill_q=0;
        for(integer b=0;b<8;b=b+1)begin:fillsector
            integer sector,sid,position,chunk,word_,lane;
            reg [255:0] data;
            sector=0;sid=0;position=0;chunk=0;word_=0;lane=0;data=0;
            if(state==1)begin
            sector=fill*8+b;sid=(sector>>13)&3;position=sector/2560;chunk=sector%2560;
            word_=position*80+chunk/32;lane=chunk%32;
            for(integer j=0;j<8;j=j+1)data[j*32+:32]={xm[(j*640+word_)*32+lane],16'd0};
            if(mutate&&sector==0)data[31:0]=32'h3f800000;
            fill_q[(sid*8+b)*281+:281]={1'b1,16'(sector),data,8'hff};
            end
        end
        if(state==3)for(integer p=0;p<8;p=p+1)
            if(p<npos&&(age==ssbase+160*p||age==rowbase+160*p))raw_read=1;
    end
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
                .clk(clk),.rst_n(rst_n),.local_rq(localq),.far_rq(136'd0),
                .local_wq(result_localwq),.far_wq(2248'd0),
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

 wire [127:0] k_v,k_we,kr_rdy,k_rdy,k_wr_done,kr_v;
 wire [3839:0] k_addr;wire [511:0] k_len;wire [2175:0] k_tag;
 wire [32767:0] k_wdata;wire [4095:0] k_wstrb;
 wire [2175:0] kr_tag;wire [511:0] kr_beat;wire [32767:0] kr_data;
 reg [255:0] checkpoint_image[0:61439];
 integer requests=0,phyresponses=0;
 function automatic [4:0] pc_of(input [29:0] s);pc_of=s[6:2]^s[11:7]^s[16:12];endfunction
 for(genvar st=0;st<4;st=st+1)begin:physical_stack
  if(COMMAND_NATIVE)begin:command_native
  wire native_fault;wire [31:0] row_v,col_v,col_we,dram_rvalid;
  wire [95:0] row_op;wire [159:0] row_bank,col_bank,col_col;wire [607:0] row_row;
  wire [8191:0] col_data,dram_rdata;wire [1023:0] col_strb;
  wire [31:0] pc_clk={32{hbm_clk}};
  ot_hbm_svc_native_sector_owned_stack #(.FAST_IDLE_DESC(1),.AQ_ROW_LEASE(1),.COLUMN_CLOSE_GUARD(1)) u_controller(
   .clk(hbm_clk),.rst_n(rst_n),.pc_clk(pc_clk),
   .k_v(k_v[st*32+:32]),.k_rdy(k_rdy[st*32+:32]),.k_we(k_we[st*32+:32]),.k_addr(k_addr[st*960+:960]),.k_len(k_len[st*128+:128]),
   .k_tag(k_tag[st*544+:544]),.k_wdata(k_wdata[st*8192+:8192]),.k_wstrb(k_wstrb[st*1024+:1024]),.k_wr_done(k_wr_done[st*32+:32]),
   .kr_v(kr_v[st*32+:32]),.kr_rdy(kr_rdy[st*32+:32]),.kr_tag(kr_tag[st*544+:544]),.kr_beat(kr_beat[st*128+:128]),.kr_data(kr_data[st*8192+:8192]),
   .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),
   .dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.fault(native_fault));
  ot_hbm_svc_command_dram_pipeline_fixture #(.K_BASE(671088640),.K_MEM(61440)) dram(
   .clk(hbm_clk),.rst_n(rst_n),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),
   .col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata));
  reg image_copied=0;
  always @(negedge hbm_clk)if(!image_copied)begin
   for(integer a=0;a<61440;a=a+1)dram.mem[a]=checkpoint_image[a];
   if($test$plusargs("WEIGHT_MUTANT"))dram.mem[5*320+319] ^= 256'h10000000;
   image_copied=1;
  end
  always @(posedge hbm_clk)if(rst_n&&native_fault)$fatal(1,"actual native command controller fault stack%0d",st);
  end else begin:request_model
  wire k_oor,w_oor;wire [63:0] refreshes;
  ot_chip_v41x_hbm3e_phy #(.K_AW(30),.KTAGW(17),.K_MEM(61440),.K_BASE(64'd671088640),.CLK_PS(1024)) u_phy(
   .clk(hbm_clk),.rst_n(rst_n),.k_v(k_v[st*32+:32]),.k_rdy(k_rdy[st*32+:32]),.k_addr(k_addr[st*960+:960]),.k_len(k_len[st*128+:128]),
   .k_tag(k_tag[st*544+:544]),.k_we(k_we[st*32+:32]),.k_wdata(k_wdata[st*8192+:8192]),.k_wstrb(k_wstrb[st*1024+:1024]),.k_wr_done(k_wr_done[st*32+:32]),
   .kr_v(kr_v[st*32+:32]),.kr_rdy(kr_rdy[st*32+:32]),.kr_tag(kr_tag[st*544+:544]),.kr_beat(kr_beat[st*128+:128]),.kr_data(kr_data[st*8192+:8192]),
   .w_v(1'b0),.w_rdy(),.w_addr(24'b0),.w_len(6'b0),.w_tag(10'b0),.w_room(),.wr_v(),.wr_rdy(8'b0),.wr_tag(),.wr_beat(),.wr_data(),
   .k_oor(k_oor),.w_oor(w_oor),.refreshes(refreshes),.w_reads());
  reg image_copied=0;
  always @(negedge hbm_clk)if(!image_copied)begin
   for(integer a=0;a<61440;a=a+1)u_phy.u_k.mem[(64'd671088640+a)%61440]=checkpoint_image[a];
   if($test$plusargs("WEIGHT_MUTANT"))u_phy.u_k.mem[(64'd671088640+5*320+319)%61440] ^= 256'h10000000;
   image_copied=1;
  end
  always @(posedge hbm_clk)if(rst_n&&(k_oor||w_oor))$fatal(1,"actual PHY address aperture error");
  end
 end
 always @(posedge hbm_clk)begin:check_actual_phy
  integer pc,st,bank,row,offset;reg [29:0]sector;reg [34:0]byte_address;
  if(rst_n)for(integer i=0;i<128;i=i+1)begin
   if(k_v[i]&&k_rdy[i])begin
    st=i/32;pc=i%32;sector=k_addr[i*30+:30];byte_address={sector,5'b0};
    if(pc_of(sector)!=pc||k_we[i]||k_len[i*4+:4]!=1)$fatal(1,"actual PHY command/PC error");
    if(byte_address<35'd21474836480||byte_address>=35'd21474836480+24*81920)$fatal(1,"actual20GiB image bounds");
    bank=((byte_address-35'd21474836480)%81920)/10240;
    if(bank%4!=st)$fatal(1,"actual stripe stack mismatch");
    requests=requests+1;
   end
   if(kr_v[i]&&kr_rdy[i])phyresponses=phyresponses+1;
  end
 end
 wire [3:0] reserve_ready;wire [7:0] fetched_ready;wire [31:0] resident_ready;
 wire reserve_v=(state==4&&prime_i<8&&reserve_ready==15)||
  (state==2&&(age==330||age==660))||
  (state==3&&row<19&&(age==330||age==660));
 wire reserve_half=(state==4)?1'(prime_i%2):age==660;
 wire [4:0] reserve_row=(state==4)?5'(prime_i/2):(state==2)?5'd4:5'(row+5);
 wire [34:0] reserve_row_local_byte=35'd21474836480+reserve_row*81920;
 wire [15:0] reserve_epoch=16'h6001+reserve_row;
 wire drain_v=(state==2&&(age==0||age==330))||
  (state==3&&row<23&&(age==0||age==330));
 wire drain_half=age==330;
 wire [4:0] drain_row=(state==2)?5'd0:5'(row+1);
 wire drain_slot=drain_row[0];wire [15:0] drain_epoch=16'h6001+drain_row;
 wire half_done,done_half;
 ot_hgi_hc_native_sys1_split_mtp_static #(.TAIL_LOOP(1),.NATIVE_GATHER_READER(0)) dut(
  .clk(clk),.reduction_clk(clk),.scalar_clk(clk),.bank_clk({8{clk}}),.weight_clk({32{clk}}),.residual_clk({16{clk}}),.mac_clk({32{clk}}),.sink_clk(sink_clk),.rst_n(rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(rst_n),
  .cfg_we(cfgwe),.cfg_addr(11'(cfgi)),.cfg_data(cfgdata),
  .gather_phase(1'b0),.gather_launch(1'b0),.gather_npos(4'd0),.gather_base_sector(16'd0),.gather_stride_sector(16'd0),.gather_done(),
  .start_v(startv),.start_base(row<24?11'd0:11'(period)),.start_limit(row<24?12'(period):12'(period+497)),.start_loops((row<24)?16'd24:16'(npos)),
  .reserve_v(reserve_v),.reserve_half(reserve_half),.reserve_row_local_byte(reserve_row_local_byte),
  .reserve_epoch(reserve_epoch),.reserve_ready(reserve_ready),.fetched_ready(fetched_ready),.resident_ready(resident_ready),
  .drain_v(drain_v),.drain_half(drain_half),.drain_slot(drain_slot),.drain_epoch(drain_epoch),
  .half_done(half_done),.done_half(done_half),
  .residual_launch(vm_launch),.residual_npos(4'(npos)),.residual_base_sector(16'd0),
  .local_rq(bridge_rq),.local_read(vm_read),.local_rr(state==9?2056'd0:vm_rr),.residual_done(native_done),
  .store_slot(state==5&&age%497==493),.result_base_sector(16'd28672),.store_position(3'(pc)),
  .local_wq(result_wq),.local_write(result_write),
  .gathered_mix_v(1'b0),.gathered_mix_row(5'd0),.gathered_mix_pos(3'd0),.gathered_mix_data(32'd0),
  .bases(bases),.scales(scales),.row_result_v(rv),.row_result_id(ri),.row_result_pos(rp),.row_result(rd),
  .result_v(tv),.result(result),.tail_result_pos(tp),.tail_e_ready(),
  .program_done(program_done),.program_active(program_active),.fault(fault),
  .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),
  .k_wdata(k_wdata),.k_wstrb(k_wstrb),.k_wr_done(k_wr_done),
  .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data));
 always @(posedge clk)if(rst_n)begin
  if(reserve_v&&reserve_ready!=15)$fatal(1,"checkpoint reserve deadline");
  if(drain_v&&(fetched_ready&(drain_half?8'haa:8'h55))!=(drain_half?8'haa:8'h55))
   $fatal(1,"checkpoint drain deadline row%0d age%0d ready%h",drain_row,age,fetched_ready);
 end
 initial begin
  $readmemh("all24rows.hex",checkpoint_image);

 end

    always @(posedge clk)begin
        cycle<=cycle+1;
        if(cycle==4)begin rst_n<=1;state<=1;fill<=0;end
        if(state==1)begin if(fill==320*npos-1)begin state<=8;age<=0;fill<=0;end else fill<=fill+1;end
        if(state==8)begin age<=age+1;if(native_done)begin state<=4;age<=0;prime_i<=0;cold_start<=cycle;end end
        if(state==4)begin
            age<=age+1;
            if(prime_i<8&&reserve_ready==15)prime_i<=prime_i+1;
            if(prime_i==8&&resident_ready==32'hffffffff)begin
                $display("HC_SYS1_COLD_READY cycle=%0d cold_cycles=%0d resident=%h",cycle,cycle-cold_start,resident_ready);
                state<=2;age<=0;fill<=0;
            end
        end
        if(state==2)begin age<=age+1;if(age==670)begin loadimage(0,0);state<=6;cfgi<=0;end end
        if(state==6)begin
            if(cfgi==cfgwords-1)begin
                state<=7;
                // Every first consumer edge is aligned to global sink phase0.
                startedge<=((cycle+1+10+5+6)/7)*7-5;
            end else cfgi<=cfgi+1;
        end
        if(state==7&&cycle==startedge)begin state<=(row<24)?3:5;age<=-4;end
        if(rst_n&&(fault||(|tapfault)||(|bank_status)))$fatal(1,"PROGRAMMED_MTP fault state%0d row%0d age%0d",state,row,age);
        if(state==3||state==5)age<=age+1;
        if(state==3)begin
            if(rv)begin
                seen<=seen+1;
                if(age!=269+SYS_DELTA+160*rp||ri!=row||rp>=npos||rd!==expm[rp*24+row])$fatal(1,"programmed row data/time mismatch row%0d pos%0d age%0d",row,rp,age);
            end
            if(age==period-1)begin
                if(seen!=(row+1)*npos)$fatal(1,"missing repeated programme row results");
                if(row==23)begin
                    if(!program_done)$fatal(1,"programme failed final fixed loop boundary");
                    row<=24;pc<=0;state<=7;
                    // Fixed next start, reusing the preinstalled tail range.
                    startedge<=((cycle+1+10+5+6)/7)*7-5;
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
            if(age%497==496)begin
                if(tailseen!=pc+1)$fatal(1,"programmed tail missing");
                if(pc==npos-1)begin
                    if(!program_done)$fatal(1,"tail programme failed final loop");
                    state<=9;age<=0;
                end else begin
                    if(program_done)$fatal(1,"tail programme ended early");
                    pc<=pc+1;
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
                $display("HC_CHECKPOINT_NATIVE_SYS1_SPLIT_MTP_DONE npos=%0d rows=%0d tails=%0d nativeVMresultwords=%0d cycles=%0d",npos,seen,tailseen,result_sectors*8,cycle);$finish;
            end
        end
        if(cycle>105000)$fatal(1,"programmed MTP bench watchdog");
    end
endmodule
