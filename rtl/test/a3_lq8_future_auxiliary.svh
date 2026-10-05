    // External backing service model; the cursor and response queue are RTL.
    wire aux_valid,aux_ready,identity_mismatch;
    wire [31:0] aux_a,aux_s,aux_ws,aux_generation,aux_w;
    wire [63:0] aux_a_data,aux_ws_data;
    wire [31:0] aux_s_data;
    reg cursor_started=0;
    wire future_valid,future_ready;
    wire [31:0] future_generation,future_a,future_s,future_ws,future_w;
    reg admission_sent=0;
    wire admission_ready,record_valid,geometry_error;
    wire cursor_start=record_valid && !geometry_error && operand_request && !cursor_started;
    wire [31:0] record_stream_words;
    wire [31:0] record_generation,record_a,record_s,record_ws,record_w;
    wire [15:0] record_rows,record_cols,depth_words,record_rpb,record_cpa,record_cpb,record_bwa,record_bwb;
    ot_a3_lq8_operand_admission #(.LANES(LANES)) admission(
        .clk(clk),.rst_n(runtime_reset_n),.clear(1'b0),
        .command_valid(runtime_active && !admission_sent),.command_ready(admission_ready),
        .cfg_generation(generation),.cfg_rows(cfg_rows),.cfg_cols(cfg_cols),.cfg_depth(cfg_depth),
        .cfg_group(cfg_group),.cfg_scale_a(cfg_scale_a),.cfg_scale_b(cfg_scale_b),
        .cfg_block_a(cfg_block_a),.cfg_block_b(cfg_block_b),.cfg_block_rows_a(cfg_block_rows_a),
        .cfg_a_base(cfg_a_base),.cfg_s_base(cfg_scale_a_base),.cfg_ws_base(cfg_ws_base),.cfg_w_base(cfg_w_base),
        .record_valid(record_valid),.record_ready(cursor_start),.geometry_error(geometry_error),.stream_words(record_stream_words),
        .generation(record_generation),.a_base(record_a),.s_base(record_s),.ws_base(record_ws),.w_base(record_w),
        .rows(record_rows),.local_cols(record_cols),.depth_words(depth_words),.rows_per_scale_a(record_rpb),
        .scale_stride_a(record_cpa),.scale_stride_b(record_cpb),
        .groups_per_scale_a(record_bwa),.groups_per_scale_b(record_bwb));
    ot_a3_lq8_operand_cursor #(.INTERLEAVE(ADDER_STAGES)) cursor(
        .clk(clk),.rst_n(runtime_reset_n),.clear(1'b0),
        .start(cursor_start),
        .cfg_generation(record_generation),.cfg_rows(record_rows),.cfg_local_cols(record_cols),
        .cfg_depth_words(depth_words),.cfg_rows_per_scale_a(record_rpb),
        .cfg_scale_stride_a(record_cpa),.cfg_scale_stride_b(record_cpb),
        .cfg_groups_per_scale_a(record_bwa),.cfg_groups_per_scale_b(record_bwb),
        .cfg_a_base(record_a),.cfg_s_base(record_s),.cfg_ws_base(record_ws),.cfg_w_base(record_w),
        .request_valid(future_valid),.request_ready(future_ready),
        .generation(future_generation),.a_address(future_a),.s_address(future_s),
        .ws_address(future_ws),.w_address(future_w),.last(),.active(),.invalid_geometry());
    wire service_valid,service_ready,response_ready,response_mismatch;
    wire [31:0] service_generation,service_a,service_s,service_ws,service_w;
    reg response_valid=0,response_pending=0;
    reg [2:0] response_delay=0;
    reg [31:0] response_generation=0,response_w=0,response_s_data=0;
    reg [63:0] response_a_data=0,response_ws_data=0;
    wire [$clog2(AUXILIARY_DEPTH+1)-1:0] auxiliary_occupied;
    assign service_ready=!response_pending && !response_valid;
    ot_a3_lq8_auxiliary_prefetch #(.DEPTH(AUXILIARY_DEPTH)) auxiliary_queue(
        .clk(clk),.rst_n(runtime_reset_n),.clear(1'b0),
        .request_valid(future_valid),.request_ready(future_ready),
        .request_generation(future_generation),.request_a(future_a),.request_s(future_s),
        .request_ws(future_ws),.request_w(future_w),
        .service_valid(service_valid),.service_ready(service_ready),
        .service_generation(service_generation),.service_a(service_a),.service_s(service_s),
        .service_ws(service_ws),.service_w(service_w),
        .response_valid(response_valid),.response_ready(response_ready),.response_mismatch(response_mismatch),
        .response_generation(response_generation),.response_w(response_w),
        .response_a_data(response_a_data),.response_s_data(response_s_data),.response_ws_data(response_ws_data),
        .auxiliary_valid(aux_valid),.auxiliary_ready(aux_ready),
        .auxiliary_generation(aux_generation),.auxiliary_a(aux_a),.auxiliary_s(aux_s),
        .auxiliary_ws(aux_ws),.auxiliary_w(aux_w),
        .auxiliary_a_data(aux_a_data),.auxiliary_s_data(aux_s_data),.auxiliary_ws_data(aux_ws_data),
        .occupied(auxiliary_occupied));
    integer auxiliary_requests=0,auxiliary_max_occupied=0;
    always @(posedge clk)begin
        if(!runtime_reset_n)begin admission_sent<=0;cursor_started<=0;response_valid<=0;response_pending<=0;end
        else begin
            if(runtime_active && !admission_sent && admission_ready)admission_sent<=1;
            if(cursor_start)cursor_started<=1;
            if(record_valid && geometry_error && operand_request)$fatal(1,"admission geometry differs from LQ8");
            if(service_valid && service_ready)begin
                response_generation<=service_generation;response_w<=service_w;
                response_a_data<=m0_mem[service_a];
                response_s_data<=cfg_scale_a?m2_mem[service_s]:0;
                response_ws_data<=cfg_scale_b?ws_mem[service_ws]:0;
                response_delay<=service_w[2:0];response_pending<=1;
                auxiliary_requests<=auxiliary_requests+1;
            end
            if(response_pending)begin
                if(response_delay==0)begin response_pending<=0;response_valid<=1;end
                else response_delay<=response_delay-1'b1;
            end
            if(response_valid && response_ready)response_valid<=0;
            if(response_mismatch)$fatal(1,"auxiliary response identity mismatch");
            if(aux_ready && aux_w!=preview_w)$fatal(1,"future stream cursor mismatch");
            if(32'(auxiliary_occupied)>auxiliary_max_occupied)auxiliary_max_occupied<=32'(auxiliary_occupied);
        end
    end
    final $display("AUXILIARY requests=%0d max_reserved=%0d",auxiliary_requests,auxiliary_max_occupied);
