`timescale 1ns/1ps
module tb_programme_held_user_join;
  localparam integer IBW=379,DESC=73,HW=1+IBW+DESC+2+18+6+64+1024,FV=1+IBW+DESC;
  reg ck=0;always #5 ck=~ck;
  reg rst=0,pv=0,sv=0;reg[23:0] xb_file=0,sa=0;wire[23:0]xb,me_xb;reg[11:0] k=8;reg[3:0] sp=9;
  wire[HW-1:0] hw,he;wire fault,stream_fault,xt_v,xt_bad;wire[23:0]xt_a;wire[1023:0]xt_d;reg[191:0]lane_a;wire[2047:0]fp_data;
  reg pub=0,retire=0;reg[1:0]user_id=0;reg[15:0]epoch_id=0;
  wire guard_fault;wire[23:0]canonical=xb_file&24'hfcffff;
  qfd_dv_held_user_xbase #(.ENABLE(1)) guard(.ck(ck),.rst_n(rst),.publish(pub),
    .publish_user(user_id),.legacy_user(2'd0),.publish_epoch(epoch_id),
    .use_epoch(epoch_id^((mut==7)?16'd1:16'd0)),
    .profile_matches(mut!=9),.all_copies_authenticated(mut!=8),
    .me_apply(pv),.xpf_apply(pv),.epoch_class(2'(seed%4)),
    .me_base(canonical+((mut==10)?24'd1:24'd0)),.xpf_base(canonical),
    .retire_me(retire),.retire_xpf(retire),.me_final_read(mut!=6),.xpf_final_use(1'b1),
    .me_address(me_xb),.xpf_address(xb),.me_user(),.xpf_user(),.held_epoch(),.me_active(),.xpf_active(),.fault(guard_fault));
  wire[23:0]legacy_me,legacy_xpf;wire legacy_guard_fault;
  qfd_dv_held_user_xbase legacy_guard(.ck(ck),.rst_n(rst),.publish(pub),
    .publish_user(user_id),.legacy_user(user_id),.publish_epoch(epoch_id),.use_epoch(epoch_id),
    .profile_matches(1'b0),.all_copies_authenticated(1'b0),.me_apply(pv),.xpf_apply(pv),.epoch_class(2'(seed%4)),
    .me_base(canonical),.xpf_base(canonical),.retire_me(retire),.retire_xpf(retire),.me_final_read(1'b0),.xpf_final_use(1'b0),
    .me_address(legacy_me),.xpf_address(legacy_xpf),.me_user(),.xpf_user(),.held_epoch(),.me_active(),.xpf_active(),.fault(legacy_guard_fault));
  always@(posedge ck)if(rst&&pv)begin
    #1;
    if(me_xb!==xb_file||xb!==xb_file||legacy_me!==canonical||legacy_xpf!==canonical||legacy_guard_fault)errors=errors+1;
  end
  genvar l;generate for(l=0;l<64;l=l+1)assign fp_data[32*l+:32]={xt_d[16*l+:16],16'd0};endgenerate
  integer seed=0;reg[255:0]source_data;
  integer lane;always @*begin
    for(lane=0;lane<8;lane=lane+1)begin
      lane_a[24*lane+:24]=24'h400000|(sa+lane);
      source_data[32*lane+:32]={16'(16'h3e00+((seed*17+sa-producer+lane)%1024)),16'd0};
    end
  end
  qfd_dv_stream stream(.ck(ck),.rst_n(rst),.sid(4'd0),.cfg_v(pv),.cfg_dir(2'd1),.cfg_tag(28'd1|((xb>>16)<<6)),.sw_i(1088'd0),.se_i(1088'd0),.so_e(),.so_w(),.xw_we(sv?8'hff:8'd0),.xw_addr(lane_a),.xw_data(source_data),.tw_we(),.tw_kind(),.tw_addr(),.tw_data(),.xt_v(xt_v),.xt_a(xt_a),.xt_d(xt_d),.xt_bad(xt_bad),.fault(stream_fault));
  ot_qfd_xs_tap #(.STATIC_SCHEDULE(1),.NATIVE_AFFINE(1)) dut(.clk(ck),.rst_n(rst),.xpf_v(pv),.xpf_xbase(xb),
   .xpf_xcs(k),.xpf_xks(12'd1),.xpf_split(sp),.xpf_k({6'd0,k}),.xpf_round(1'b1),
   .sw_v(xt_v),.sw_a(xt_a),.sw_m(64'hffffffffffffffff),.sw_d(fp_data),
   .aw_v(1'b0),.aw_a(24'd0),.aw_m(16'd0),.aw_d(512'd0),.gi(380'd0),.hw(hw),.he(he),.fw_i(1'b0),.fe_i(1'b0),.fault(fault));
  integer fd,n,mut=0,cases=0,got=0,case_got=0,expected=0,errors=0,j,ret;reg[1023:0]expected_data;reg[23:0] producer;reg[1023:0] file;
  always @(negedge ck) if(rst && hw[FV]) begin
    got=got+1;
    for(integer i=0;i<64;i=i+1)
      expected_data[16*i+:16]=16'h3e00+((seed*17+64*case_got+i)%1024);
    if(hw!==he || hw[HW-1 -:1024]!==expected_data)begin
      if(errors<4)$display("NAMESPACE_DATA_MISMATCH case=%0d word=%0d seed=%0d got=%h want=%h",cases,case_got,seed,hw[HW-1 -:64],expected_data[1023-:64]);
      errors=errors+1;
    end
    case_got=case_got+1;
  end
  initial begin
    if(!$value$plusargs("INPUT=%s",file))$fatal(1,"INPUT");
    ret=$value$plusargs("MUT=%d",mut);fd=$fopen(file,"r");
    repeat(4)@(negedge ck);rst=1;
    while(!$feof(fd)) begin
      ret=$fscanf(fd,"%h %h %d %d %d %d\n",xb_file,producer,k,sp,n,seed);
      if(ret==6)begin
        cases=cases+1;case_got=0;user_id=xb_file[17:16];epoch_id=16'(seed/16+7);
        pub=1;@(negedge ck);pub=0;pv=1;@(negedge ck);pv=0;repeat(7)@(negedge ck);
        for(j=0;j<n*8;j=j+1)begin
          sv=1;sa=producer+8*j;
          if(mut==1)sa=sa+65536;
          if(mut==2)sa=sa+64;
          if(mut==4 && (producer%65536==16384 || producer%65536==32768))sa=sa+48;
          if(mut==3)sa={8'd0,sa[15:0]};
          @(negedge ck);
        end
        sv=0;repeat(8)@(negedge ck);expected=expected+n;
        if(mut==5)begin pub=1;@(negedge ck);pub=0;end
        retire=1;@(negedge ck);retire=0;
      end
    end
    if(got!=expected || fault || stream_fault || xt_bad || guard_fault)errors=errors+1;
    $display("PROGRAMME_HELD_USER_JOIN cases=%0d got=%0d expected=%0d errors=%0d fault=%0d mut=%0d",cases,got,expected,errors,(fault|stream_fault|xt_bad|guard_fault),mut);
    if(errors)$fatal(1,"PROGRAMME_HELD_USER_JOIN_FAIL");
    $display("PROGRAMME_HELD_USER_JOIN_PASS");$finish;
  end
endmodule
