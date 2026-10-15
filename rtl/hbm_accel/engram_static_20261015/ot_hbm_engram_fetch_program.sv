`timescale 1ps/1fs
// Target124, one source-owned Engram fetch programme per rank. Seven32b
// instructions/native256b SRAM word; CFG low224 meaningful, upper32 zero.
// TokenCID is an actual producer input, never embedded in a programme word.
// Descriptor rawedge ->130edge initialization guard -> globalC10 launch.
module ot_hbm_engram_fetch_program #(
    parameter[7:0]TARGET=8'd124,
    parameter integer FETCH_EDGES=18944,
    parameter integer MUT_OPCODE=0, MUT_DESC_TARGET=0
)(
    input wire clk_control,clk_mem,rst_n,
    input wire cfg_v,input wire[7:0]cfg_target,input wire[11:0]cfg_addr,input wire[255:0]cfg_data,
    input wire desc_v,input wire[9:0]desc_base,desc_limit,input wire[15:0]desc_loops,
    input wire launch_v,input wire token_v,input wire[16:0]token_cid,input wire token_first,
    input wire[7:0]home_done,home_fault,
    output reg configured,init_busy,busy,done,fault,
    output wire epoch_begin,hash_v,hash_first,fetch_start,output wire[16:0]hash_cid,
    output reg instruction_v,output reg[31:0]instruction,output reg[9:0]instruction_pc
);
    reg[7:0]descriptor_age;
    reg cv,dv,lv;reg token_vq,token_firstq;reg[16:0]token_cidq;reg[7:0]target_q;reg[11:0]address_q;reg[255:0]data_q;
    reg[9:0]base_q,limit_q;reg[15:0]loops_q;
    reg mem_we,mem_re;reg[6:0]write_row,read_row;
    reg[255:0]write_data,raw_q,current_word,next_word;
    wire[255:0]mem_data;
    reg[127:0]loaded;reg checking,check_bad;reg[6:0]scan,first_word,last_word,word_index;
    reg[9:0]base,limit,pc;reg[2:0]position;
    reg run,prefetch_valid,read_first,rp0,rp1,first0,first1;
    reg have_token,first_q,kernel_started,seen_epoch,seen_hash,program_done;reg[16:0]cid_q;reg[31:0]kernel_age;
    wire[3:0]op=instruction[3:0];
    assign epoch_begin=instruction_v && op==1;
    assign hash_v=instruction_v && op==2 && have_token;
    assign hash_first=first_q;assign hash_cid=cid_q;
    assign fetch_start=instruction_v && op==3;
    ot_sram_1r1w_128x256_m1_r2c2 programme(
        .clk(clk_mem),.r_ce_in(mem_re),.r_addr_in(read_row),.rd_out(mem_data),
        .w_ce_in(mem_we),.w_addr_in(write_row),.wd_in(write_data),.w_mask_in({256{1'b1}}),
        .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
    always @(posedge clk_control)begin
        token_vq<=token_v;token_firstq<=token_first;token_cidq<=token_cid;
        target_q<=cfg_target;address_q<=cfg_addr;data_q<=cfg_data;
        base_q<=desc_base;limit_q<=desc_limit;loops_q<=desc_loops;
        raw_q<=mem_data;
    end
    always @(posedge clk_control or negedge rst_n)begin
        if(!rst_n)begin
            descriptor_age<=0;cv<=0;dv<=0;lv<=0;configured<=0;init_busy<=0;busy<=0;done<=0;fault<=0;
            loaded<=0;checking<=0;check_bad<=0;scan<=0;first_word<=0;last_word<=0;word_index<=0;
            base<=0;limit<=0;pc<=0;position<=0;run<=0;prefetch_valid<=0;
            mem_we<=0;mem_re<=0;write_row<=0;read_row<=0;write_data<=0;
            rp0<=0;rp1<=0;read_first<=0;first0<=0;first1<=0;current_word<=0;next_word<=0;
            seen_epoch<=0;seen_hash<=0;program_done<=0;have_token<=0;first_q<=0;cid_q<=0;kernel_started<=0;kernel_age<=0;
            instruction_v<=0;instruction<=0;instruction_pc<=0;
        end else begin
            cv<=cfg_v;dv<=desc_v && (MUT_DESC_TARGET || cfg_target==TARGET);lv<=launch_v;
            if(desc_v && (MUT_DESC_TARGET || cfg_target==TARGET))descriptor_age<=0;else if(descriptor_age!=255)descriptor_age<=descriptor_age+1'b1;
            mem_we<=0;mem_re<=0;done<=0;program_done<=0;instruction_v<=0;instruction<=0;
            rp0<=mem_re;rp1<=rp0;first0<=read_first;first1<=first0;
            if(rp1)begin
                if(first1)begin current_word<=raw_q;run<=1;end
                else begin next_word<=raw_q;prefetch_valid<=1;end
            end
            if(checking)begin
                if(scan>=first_word && scan<=last_word && !loaded[scan])check_bad<=1;
                if(scan==127)begin
                    checking<=0;init_busy<=0;
                    if(check_bad || (scan>=first_word && scan<=last_word && !loaded[scan]))fault<=1;
                    else if(!fault)configured<=1;
                end else scan<=scan+1'b1;
            end
            if(cv && target_q==TARGET)begin
                if(busy || run || instruction_v || checking || lv || dv || fault || address_q>=128 || data_q[255:224]!=0 || loaded[address_q[6:0]])fault<=1;
                else begin mem_we<=1;write_row<=address_q[6:0];write_data<=data_q;loaded[address_q[6:0]]<=1;configured<=0;end
            end
            if(dv)begin
                configured<=0;
                if(busy || checking || run || cv || mem_we || fault)fault<=1;
                else if(loops_q==0 && base_q==0 && limit_q==0)begin
                    // Actual descriptor-carried deactivation for unrelated
                    // globalC10 launches; retained catalogue/hash context stays.
                    checking<=0;init_busy<=0;
                end else if(base_q>=limit_q || limit_q>896 || base_q%7!=0 || loops_q!=1)fault<=1;
                else begin base<=base_q;limit<=limit_q;first_word<=7'(base_q/7);last_word<=7'((limit_q-1)/7);checking<=1;init_busy<=1;check_bad<=0;scan<=0;end
            end
            if(lv && configured)begin
                if(!configured || init_busy || busy || run || fault || !token_vq || descriptor_age<130)fault<=1;
                else begin
                    busy<=1;seen_epoch<=0;seen_hash<=0;have_token<=1;cid_q<=token_cidq;first_q<=token_firstq;kernel_started<=0;kernel_age<=0;
                    pc<=base;position<=0;word_index<=first_word;prefetch_valid<=0;
                    mem_re<=1;read_row<=first_word;read_first<=1;
                end
            end
            if(run)begin
                instruction_v<=1;instruction_pc<=pc;
                instruction<=current_word[position*32+:32] ^ (MUT_OPCODE?32'd3:32'd0);
                pc<=pc+1'b1;
                if(position==2 && word_index<last_word)begin mem_re<=1;read_row<=word_index+1'b1;read_first<=0;end
                if(pc==limit-1'b1)begin run<=0;program_done<=1;end
                else if(position==6)begin
                    if(!prefetch_valid)fault<=1;
                    current_word<=next_word;prefetch_valid<=0;position<=0;word_index<=word_index+1'b1;
                end else position<=position+1'b1;
            end
            if(instruction_v)begin
                if(instruction[31:4]!=0 || op>3)fault<=1;
                if(op==1)begin if(seen_epoch || seen_hash)fault<=1;seen_epoch<=1;end
                if(op==2)begin if(!have_token || !seen_epoch)fault<=1;have_token<=0;seen_hash<=1;end
                if(op==3)begin if(kernel_started || !seen_hash)fault<=1;kernel_started<=1;kernel_age<=0;end
            end
            if(program_done && !kernel_started && !(instruction_v && op==3))begin fault<=1;busy<=0;end
            if(kernel_started)begin
                kernel_age<=kernel_age+1;
                if(kernel_age==FETCH_EDGES)begin
                    if(home_done!=8'hff || home_fault!=0)fault<=1;
                    done<=1;busy<=0;kernel_started<=0;
                end
            end
            if(home_fault!=0)fault<=1;
        end
    end
endmodule
