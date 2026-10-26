    // Behavioral runtime producer around synthesizable SRAM prefetch and join.
    // Large image arrays represent external backing storage, not on-chip capacity.
    localparam integer TILE_WORDS=32;
    reg runtime_active=0;
    reg [31:0] generation=0,fill_base=0,acquire_base=0,stream_end=0;
    reg fill_bank=0,acquire_bank=0,filling=0;
    reg [9:0] fill_index=0;
    reg [31:0] ticks=0;
    wire runtime_reset_n=rst_n && !start_dut && !dut_done;
    wire operand_request,operand_issue,operand_credit;
    wire [31:0] preview_a,preview_s,preview_ws,preview_w;
    wire reserve_ready,fill_ready,tile_ready,word_valid,word_ready;
    wire [127:0] word_data;
    wire [63:0] word_tag;
    wire [9:0] word_index;
    wire [9:0] fill_words=(stream_end-fill_base<TILE_WORDS)?10'(stream_end-fill_base):10'(TILE_WORDS);
    wire [9:0] acquire_words=(stream_end-acquire_base<TILE_WORDS)?10'(stream_end-acquire_base):10'(TILE_WORDS);
    wire reserve_valid=runtime_active && !filling && fill_base<stream_end &&
        (!SERIAL_REFILL || fill_base==cfg_w_base || preview_w>=fill_base);
    wire fill_valid=runtime_active && filling && ticks[2:0]!=0;
    wire tile_valid=runtime_active && acquire_base<stream_end;
    ot_a3_weight_tile_prefetch prefetch(
        .clk(clk),.rst_n(runtime_reset_n),
        .reserve_valid(reserve_valid),.reserve_bank(fill_bank),
        .reserve_tag({generation,fill_base}),.reserve_words(fill_words),.reserve_ready(reserve_ready),
        .fill_valid(fill_valid),.fill_bank(fill_bank),.fill_tag({generation,fill_base}),
        .fill_data(w_mem[fill_base+{22'b0,fill_index}]),.fill_ready(fill_ready),
        .cancel_valid(1'b0),.cancel_bank(1'b0),.cancel_tag(64'b0),.cancel_ready(),
        .tile_valid(tile_valid),.tile_bank(acquire_bank),.tile_retain(1'b0),
        .tile_tag({generation,acquire_base}),.tile_words(acquire_words),.tile_ready(tile_ready),
        .word_valid(word_valid),.word_ready(word_ready),.word_data(word_data),
        .word_tag(word_tag),.word_index(word_index),.word_last(),
        .tile_released(),.released_tag(),.ready_banks(),.active_banks(),.reserved_slots());
    reg aux_valid=0,aux_pending=0;
    reg [2:0] aux_delay=0;
    reg [31:0] aux_a=0,aux_s=0,aux_ws=0;
    reg [63:0] aux_a_data=0,aux_ws_data=0;
    reg [31:0] aux_s_data=0;
    wire aux_ready,identity_mismatch;
    ot_a3_lq8_operand_join joiner(
        .clk(clk),.rst_n(runtime_reset_n),.clear(1'b0),.generation(generation),
        .operand_request(operand_request),.operand_issue(operand_issue),
        .operand_a_addr(preview_a),.operand_s_addr(preview_s),
        .operand_ws_addr(preview_ws),.operand_w_addr(preview_w),
        .scale_a(cfg_scale_a),.scale_b(cfg_scale_b),.operand_credit(operand_credit),
        .identity_mismatch(identity_mismatch),
        .weight_valid(word_valid),.weight_ready(word_ready),.weight_generation(word_tag[63:32]),
        .weight_address(word_tag[31:0]+{22'b0,word_index}),.weight_data(word_data),
        .auxiliary_valid(aux_valid),.auxiliary_ready(aux_ready),.auxiliary_generation(generation),
        .auxiliary_a_addr(aux_a),.auxiliary_s_addr(aux_s),.auxiliary_ws_addr(aux_ws),
        .auxiliary_a_data(aux_a_data),.auxiliary_s_data(aux_s_data),.auxiliary_ws_data(aux_ws_data),
        .a_rd_data(d_a_data),.s_rd_data(d_s_data),.w_rd_data(d_w_data),.ws_rd_data(d_ws_data));
    integer refill_issues=0,total_issues=0,total_fills=0,total_tiles=0;
    integer op_issues=0,op_tiles=0;
    reg prior_issue=0;
    reg [31:0] prior_a,prior_s,prior_ws,prior_w;
    always @(posedge clk)begin
        if(!rst_n)begin
            runtime_active<=0;generation<=0;filling<=0;fill_index<=0;ticks<=0;
            aux_valid<=0;aux_pending<=0;prior_issue<=0;
        end else if(start_dut)begin
            runtime_active<=1;generation<=generation+1'b1;
            fill_base<=cfg_w_base;acquire_base<=cfg_w_base;
            stream_end<=cfg_w_base+32'(cfg_rows)*32'(cfg_cols/LANES)*
                ((32'(cfg_depth)+32'(cfg_group==0?1:cfg_group)-1)/32'(cfg_group==0?1:cfg_group));
            fill_bank<=0;acquire_bank<=0;filling<=0;fill_index<=0;ticks<=0;
            aux_valid<=0;aux_pending<=0;prior_issue<=0;op_issues<=0;op_tiles<=0;
        end else if(dut_done)begin
            runtime_active<=0;aux_valid<=0;aux_pending<=0;prior_issue<=0;
            $display("RUNTIME_OP issues=%0d tiles=%0d cycles=%0d",op_issues,op_tiles,ticks);
        end else if(runtime_active)begin
            ticks<=ticks+1'b1;
            if(reserve_valid && reserve_ready)begin filling<=1;fill_index<=0;end
            if(fill_valid && fill_ready)begin
                total_fills<=total_fills+1;
                if(fill_index==fill_words-1'b1)begin
                    filling<=0;fill_base<=fill_base+{22'b0,fill_words};fill_bank<=!fill_bank;
                end else fill_index<=fill_index+1'b1;
            end
            if(tile_valid && tile_ready)begin
                acquire_base<=acquire_base+{22'b0,acquire_words};acquire_bank<=!acquire_bank;
                total_tiles<=total_tiles+1;op_tiles<=op_tiles+1;
            end
            if(operand_request && !aux_valid && !aux_pending)begin
                aux_a<=preview_a;aux_s<=preview_s;aux_ws<=preview_ws;
                aux_a_data<=m0_mem[preview_a];
                aux_s_data<=cfg_scale_a?m2_mem[preview_s]:0;
                aux_ws_data<=cfg_scale_b?ws_mem[preview_ws]:0;
                // Same per-address service latency in serial/overlap runs.
                aux_pending<=1;aux_delay<=preview_w[2:0];
            end
            if(aux_pending)begin
                if(aux_delay==0)begin aux_pending<=0;aux_valid<=1;end
                else aux_delay<=aux_delay-1'b1;
            end
            if(aux_ready)aux_valid<=0;
            // A response for an issue that becomes faulted before consumption
            // is discarded at operation completion by runtime_reset_n.
            if(operand_issue)begin
                if(!operand_credit || !word_ready || !aux_ready)$fatal(1,"incomplete bundle issued");
                total_issues<=total_issues+1;op_issues<=op_issues+1;
                if(fill_valid && fill_ready)refill_issues<=refill_issues+1;
            end
            if(identity_mismatch)$fatal(1,"runtime operand identity mismatch");
            if(prior_issue && (!d_w_en || d_w_addr!=prior_w || d_a_addr!=prior_a ||
                (cfg_scale_a && d_s_addr!=prior_s) || (cfg_scale_b && d_ws_addr!=prior_ws)))
                $fatal(1,"preview disagrees with registered request");
            prior_issue<=operand_issue;
            prior_a<=preview_a;prior_s<=preview_s;prior_ws<=preview_ws;prior_w<=preview_w;
        end
    end
    final begin
        if(total_issues==0 || total_tiles<2 || (!SERIAL_REFILL && refill_issues==0))
            $fatal(1,"runtime integration not exercised");
        $display("RUNTIME issues=%0d fills=%0d tiles=%0d refill_issue_overlap=%0d serial=%0d",
            total_issues,total_fills,total_tiles,refill_issues,SERIAL_REFILL);
    end
