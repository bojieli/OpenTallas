`timescale 1ns/1ps
// Minimum native join: mask-ROM loader -> real mutable CROM/BTAB/PROG SRAMs.
// All four users remain resident; reload one user then re-read every resident
// user's image, including users whose previous layer must stay untouched.
module tb_qfd_dv_calendar_table_join #(parameter integer BTAB_COMPACT=1, LMUT=0, COLLIDE=0, EARLY=0);
    reg ck=0;always #5 ck=~ck;
    reg rst_n=0,start=0;reg[5:0]stage=1;reg[1:0]uid=0;
    reg pw_v=0,dw_v=0;reg[9:0]pw_addr=0;reg[2:0]dw_addr=0;reg[63:0]dw_data=0;
    wire load;wire[5:0]load_stage;wire[1:0]load_user;wire cal_fault,cal_ready;
    reg[9:0]preload_first[0:35];reg[63:0]dw_image[0:7];string dw_file,preload_file;
    qfd_dv_cmd_cal_mu #(.NU(4),.CTX_DW(1),.CALENDAR_ROM(1),.TABLE_ROM(1),
      .UVM_STRIDE(4096),.PIDX_STRIDE(128)) cal(.ck(ck),.rst_n(rst_n),
      .pw_v(pw_v),.pw_addr(pw_addr),.pw_data(64'd0),.dw_v(dw_v),.dw_addr(dw_addr),.dw_data(dw_data),
      .start(start),.stage(6'd1),.start_user(uid),.start_rng(1'b1),
      .start_first(preload_first[stage-1]),.start_cnt(10'd1),.table_load(load),
      .table_stage(load_stage),.table_user(load_user),.fault(cal_fault),.image_ready(cal_ready));
    wire we,busy,done,lfault;wire[1:0]kind;wire[23:0]addr;wire[1023:0]data;
    qfd_dv_table_rom_loader #(.BTAB_COMPACT(BTAB_COMPACT),.MUT(LMUT)) loader(.ck(ck),.rst_n(rst_n),.start(load),.stage(load_stage),.user_id(load_user),
        .other_table_write(1'b0),.tw_we(we),.tw_kind(kind),.tw_addr(addr),.tw_data(data),
        .busy(busy),.done(done),.fault(lfault));
    reg[7:0]cr_re=0;reg[191:0]cr_addr=0;wire[511:0]cr_q;
    reg bt_re=0,bs_re=0,p_re=0;reg[8:0]bt_word=0,p_idx=0;reg[23:0]bs_addr=0;
    wire[255:0]bt_q,bs_q;wire[456:0]p_q;wire vfault;
    reg head_we=0;reg[23:0]head_addr=72;reg[1023:0]head_data=0;
    qfd_dv_vm vm(.ck(ck),.rst_n(rst_n),
        .a_re(8'd0),.b_re(8'd0),.c_re(8'd0),.a_addr(192'd0),.b_addr(192'd0),.c_addr(192'd0),
        .a_q(),.b_q(),.c_q(),.cr_re(cr_re),.cr_addr(cr_addr),.cr_q(cr_q),
        .bs_re(bs_re),.bs_addr(bs_addr),.bs_q(bs_q),.bt_re(bt_re),.bt_word(bt_word),.bt_q(bt_q),
        .p_re(p_re),.p_idx(p_idx),.p_q(p_q),.su_we(8'd0),.su_waddr(192'd0),.su_wdata(256'd0),
        .w16_we(1'b0),.w16_addr(24'd0),.w16_data(512'd0),.w1_we(1'b0),.w1_addr(24'd0),.w1_data(32'd0),
        .tw_we(we|head_we),.tw_kind(head_we?2'd2:kind),.tw_addr(head_we?head_addr:addr),
        .tw_data(head_we?head_data:data),.fault(vfault));
    reg[1050:0]expected[0:12671];string exp_file;
    integer ledger;integer resident[0:3];integer st,u,r,k,h,l,ix,checks=0,cycles=0;
    reg[1050:0]word;reg[23:0]ra;reg[1:0]rk;
    function automatic[255:0] head_word(input integer wa);
        integer lane;begin
            for(lane=0;lane<16;lane=lane+1)head_word[16*lane+:16]=16'h6000+wa+lane;
        end
    endfunction
    task automatic check_record(input [1050:0]want);
        integer part,lane;reg[23:0]wa;reg[1:0]wk;
        begin
            wa=want[1050:1027];wk=want[1026:1025];
            if(want[1024])begin
                if(wk==3)for(part=0;part<2;part=part+1)begin
                    @(negedge ck);p_re=1;p_idx=2*wa+part;
                    repeat(2)@(posedge ck);#1;
                    if(p_q!==want[512*part+:457])$fatal(1,"TABLE_STORE_PROG_MISMATCH stage=%0d user=%0d addr=%0d",stage,uid,wa);
                    checks=checks+1;@(negedge ck);p_re=0;
                end
                else if(wk==2)for(part=0;part<4;part=part+1)begin
                    @(negedge ck);bt_re=1;bs_re=1;bt_word=wa+part;bs_addr=wa+part;
                    repeat(2)@(posedge ck);#1;
                    if(bt_q!==want[256*part+:256]||bs_q!==want[256*part+:256])
                        $fatal(1,"TABLE_STORE_BTAB_MISMATCH stage=%0d user=%0d addr=%0d",stage,uid,wa);
                    checks=checks+1;@(negedge ck);bt_re=0;bs_re=0;
                end
                else if(wk==1)for(part=0;part<2;part=part+1)begin
                    @(negedge ck);cr_re=8'hff;
                    for(lane=0;lane<8;lane=lane+1)cr_addr[24*lane+:24]=16*wa+8*part+lane;
                    repeat(2)@(posedge ck);#1;
                    for(lane=0;lane<8;lane=lane+1)
                        if(cr_q[64*lane+:64]!==want[64*(8*part+lane)+:64])
                            $fatal(1,"TABLE_STORE_CROM_MISMATCH stage=%0d user=%0d addr=%0d lane=%0d",stage,uid,wa,lane);
                    checks=checks+1;@(negedge ck);cr_re=0;
                end
            end
        end
    endtask
    always @(posedge ck)begin
        cycles=cycles+1;
        if(load)$fdisplay(ledger,"LOAD %0d %0d %0d",load_user,load_stage,cycles);
        #1;
        if(rst_n&&(lfault||vfault||cal_fault))$fatal(1,"TABLE_STORE_UNEXPECTED_FAULT loader=%0d vm=%0d",lfault,vfault);
    end
    initial begin
        ledger=$fopen("table_windows.trace","w");
        if(!$value$plusargs("EXPECTED=%s",exp_file))$fatal(1,"EXPECTED required");
        $readmemh(exp_file,expected);for(u=0;u<4;u=u+1)resident[u]=0;
        if(!$value$plusargs("DW=%s",dw_file)||!$value$plusargs("PRELOAD=%s",preload_file))$fatal(1,"calendar files required");
        $readmemh(dw_file,dw_image);$readmemh(preload_file,preload_first);
        repeat(4)@(negedge ck);rst_n=1;repeat(5)@(negedge ck);
        for(k=0;k<1024;k++)begin pw_v=1;pw_addr=k;@(negedge ck);end
        pw_v=0;
        for(k=0;k<8;k++)begin dw_v=1;dw_addr=k;dw_data=dw_image[k];@(negedge ck);end
        dw_v=0;repeat(20)@(negedge ck);
        if(!cal_ready)$fatal(1,"calendar seal failed");
        // Synthetic immutable head sentinel verifies the reserved common
        // region survives every user's decode-table reload. This is not a
        // claim that actual head weights/programme have been installed.
        if(BTAB_COMPACT!=0)begin
            for(k=72;k<272;k=k+4)begin
                @(negedge ck);head_we=1;head_addr=k;
                for(h=0;h<4;h=h+1)head_data[256*h+:256]=head_word(k+h);
            end
            @(negedge ck);head_we=0;repeat(3)@(negedge ck);
        end
        for(st=1;st<=36;st=st+1)for(u=0;u<4;u=u+1)begin
            @(negedge ck);stage=st;uid=u;start=1;
            @(negedge ck);start=0;
            // Fixed preload reservation, independent of done/busy.
            if(COLLIDE!=0 && st==1 && u==0)begin
                repeat(20)@(negedge ck);uid=1;start=1;
                @(negedge ck);start=0;
            end
            repeat(EARLY?10:103)@(negedge ck);
            if(EARLY)begin ix=(((st-1)*4)+u)*88+87;check_record(expected[ix]);end
            resident[u]=st;
            for(r=0;r<4;r=r+1)if(resident[r]!=0)begin
                $fdisplay(ledger,"FIRST %0d %0d %0d",r,resident[r],cycles+2);
                for(k=0;k<88;k=k+1)begin
                    ix=(((resident[r]-1)*4)+r)*88+k;check_record(expected[ix]);
                end
                $fdisplay(ledger,"LAST %0d %0d %0d",r,resident[r],cycles-1);
            end
            if(BTAB_COMPACT!=0)for(k=72;k<272;k=k+1)begin
                @(negedge ck);bt_re=1;bs_re=1;bt_word=k;bs_addr=k;
                repeat(2)@(posedge ck);#1;
                if(bt_q!==head_word(k)||bs_q!==head_word(k))$fatal(1,"SHARED_HEAD_TABLE_CLOBBER addr=%0d",k);
                checks=checks+1;@(negedge ck);bt_re=0;bs_re=0;
            end
        end
        $display("CALENDAR_TABLE_NATIVE_JOIN_PASS reads=%0d cycles=%0d target_read_age=2 all36 all4 retention shared_head_guard=%0d",checks,cycles,BTAB_COMPACT);
        $fclose(ledger);$finish;
    end
    // 144 installs, <=4*212 native reads/install at four edges/read, plus
    // 88 load slots and driver guards: < 600k edges for the largest slice.
    initial begin repeat(600000)@(posedge ck);$fatal(1,"TABLE_STORE_INVENTORY_PROGRESS");end
endmodule
