    wire operand_request,operand_issue,operand_credit;
    wire [31:0] preview_a,preview_s,preview_ws,preview_w;
    reg [31:0] generation=0,ticks=0;
    reg command_pending=0;
    wire command_ready,service_busy,geometry_error,protocol_error;
    wire clear_service=start_dut || dut_done;
    wire fetch_valid,fetch_ready,response_ready;
    wire [63:0] fetch_tag;
    wire [31:0] fetch_address;
    wire [9:0] fetch_words;
    reg backing_active=0;
    reg [63:0] backing_tag=0;
    reg [31:0] backing_address=0;
    reg [9:0] backing_words=0,backing_index=0;
    wire backing_valid=backing_active && ticks[2:0]!=0;
    assign fetch_ready=!backing_active && ticks[1:0]!=0;
    wire aux_request_valid,aux_request_ready,aux_response_ready,scale_a,scale_b;
    wire [31:0] request_generation,request_a,request_s,request_ws,request_w;
    reg aux_valid=0,aux_pending=0;
    reg [2:0] delay_left=0;
    reg [31:0] response_generation=0,response_w=0,response_s=0;
    reg [63:0] response_a=0,response_ws=0;
    assign aux_request_ready=!aux_pending && !aux_valid;
    ot_a3_lq8_runtime_operands #(.INTERLEAVE(ADDER_STAGES),.AUXILIARY_DEPTH(AUXILIARY_DEPTH)) runtime_service(
        .clk(clk),.rst_n(rst_n),.clear(clear_service),
        .command_valid(command_pending),.command_ready(command_ready),
        .cfg_generation(generation),.cfg_rows(cfg_rows),.cfg_cols(cfg_cols),.cfg_depth(cfg_depth),
        .cfg_group(cfg_group),.cfg_scale_a(cfg_scale_a),.cfg_scale_b(cfg_scale_b),
        .cfg_block_a(cfg_block_a),.cfg_block_b(cfg_block_b),.cfg_block_rows_a(cfg_block_rows_a),
        .cfg_a_base(cfg_a_base),.cfg_s_base(cfg_scale_a_base),.cfg_ws_base(cfg_ws_base),.cfg_w_base(cfg_w_base),
        .compute_admitted(operand_request),.operand_request(operand_request),.operand_issue(operand_issue),
        .operand_a(preview_a),.operand_s(preview_s),.operand_ws(preview_ws),.operand_w(preview_w),
        .operand_credit(operand_credit),.a_data(d_a_data),.s_data(d_s_data),.w_data(d_w_data),.ws_data(d_ws_data),
        .busy(service_busy),.geometry_error(geometry_error),.protocol_error(protocol_error),
        .weight_request_valid(fetch_valid),.weight_request_ready(fetch_ready),.weight_request_tag(fetch_tag),
        .weight_request_address(fetch_address),.weight_request_words(fetch_words),
        .weight_response_valid(backing_valid),.weight_response_ready(response_ready),
        .weight_response_tag(backing_tag),.weight_response_index(backing_index),
        .weight_response_data(w_mem[backing_address+{22'b0,backing_index}]),
        .auxiliary_request_valid(aux_request_valid),.auxiliary_request_ready(aux_request_ready),
        .auxiliary_request_generation(request_generation),.auxiliary_request_a(request_a),.auxiliary_request_s(request_s),
        .auxiliary_request_ws(request_ws),.auxiliary_request_w(request_w),.auxiliary_scale_a(scale_a),.auxiliary_scale_b(scale_b),
        .auxiliary_response_valid(aux_valid),.auxiliary_response_ready(aux_response_ready),
        .auxiliary_response_generation(response_generation),.auxiliary_response_w(response_w),
        .auxiliary_response_a_data(response_a),.auxiliary_response_s_data(response_s),.auxiliary_response_ws_data(response_ws));
    integer op_issues=0,op_tiles=0,total_issues=0,total_fills=0,total_tiles=0,refill_issues=0;
    reg prior_issue=0;
    reg [31:0] prior_a,prior_s,prior_ws,prior_w;
    always @(posedge clk)begin
        if(!rst_n)begin
            generation<=0;command_pending<=0;ticks<=0;backing_active<=0;aux_valid<=0;aux_pending<=0;prior_issue<=0;
        end else if(start_dut)begin
            generation<=generation+1'b1;command_pending<=1;ticks<=0;
            backing_active<=0;aux_valid<=0;aux_pending<=0;op_issues<=0;op_tiles<=0;prior_issue<=0;
        end else if(dut_done)begin
            command_pending<=0;backing_active<=0;aux_valid<=0;aux_pending<=0;prior_issue<=0;
            $display("RUNTIME_OP issues=%0d tiles=%0d cycles=%0d",op_issues,op_tiles,ticks);
        end else begin
            ticks<=ticks+1'b1;
            if(command_pending && command_ready)command_pending<=0;
            if(fetch_valid && fetch_ready)begin
                backing_active<=1;backing_tag<=fetch_tag;backing_address<=fetch_address;
                backing_words<=fetch_words;backing_index<=0;
            end
            if(backing_valid && response_ready)begin
                total_fills<=total_fills+1;
                if(backing_index==backing_words-1'b1)backing_active<=0;
                else backing_index<=backing_index+1'b1;
            end
            if(aux_request_valid && aux_request_ready)begin
                response_generation<=request_generation;response_w<=request_w;
                response_a<=m0_mem[request_a];response_s<=scale_a?m2_mem[request_s]:0;
                response_ws<=scale_b?ws_mem[request_ws]:0;
                aux_pending<=1;delay_left<=request_w[2:0];
            end
            if(aux_pending)begin
                if(delay_left==0)begin aux_pending<=0;aux_valid<=1;end
                else delay_left<=delay_left-1'b1;
            end
            if(aux_valid && aux_response_ready)aux_valid<=0;
            if(runtime_service.tile_valid && runtime_service.tile_ready)begin total_tiles<=total_tiles+1;op_tiles<=op_tiles+1;end
            if(operand_issue)begin
                if(!operand_credit)$fatal(1,"unreserved issue");
                total_issues<=total_issues+1;op_issues<=op_issues+1;
                if(backing_valid && response_ready)refill_issues<=refill_issues+1;
            end
            if(protocol_error || (geometry_error && operand_request))$fatal(1,"runtime service fault");
            if(prior_issue && (!d_w_en || d_w_addr!=prior_w || d_a_addr!=prior_a ||
                (cfg_scale_a && d_s_addr!=prior_s) || (cfg_scale_b && d_ws_addr!=prior_ws)))$fatal(1,"preview timing mismatch");
            prior_issue<=operand_issue;prior_a<=preview_a;prior_s<=preview_s;prior_ws<=preview_ws;prior_w<=preview_w;
        end
    end
    final begin
        if(total_issues==0 || total_tiles<2 || refill_issues==0)$fatal(1,"runtime path not exercised");
        $display("RUNTIME issues=%0d fills=%0d tiles=%0d refill_issue_overlap=%0d",total_issues,total_fills,total_tiles,refill_issues);
    end
