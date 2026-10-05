`timescale 1ns/1ps
module f_route_mask;
    (* gclk *) reg clk;
    reg rst_n = 1'b0;
    reg f_past_valid = 1'b0;
    (* anyseq *) reg route_valid;
    (* anyseq *) reg ctx_ready;
    (* anyseq *) reg [2:0] id0_raw, id1_raw, id2_raw;
    (* anyseq *) reg [15:0] txn_raw;
    reg [223:0] route_record;

    wire route_ready, ctx_valid, ctx_poison;
    wire [3:0] ctx_mask;
    wire [15:0] ctx_transaction_id, ctx_duplicate_slots;
    wire [7:0] ctx_epoch_id;
    wire [6:0] ctx_layer_id;
    wire [4:0] ctx_top_k_count;
    wire bad_crc_seen, bad_field_seen;
    wire push = route_valid && route_ready;
    wire pop = ctx_valid && ctx_ready;

    wire [9:0] id0 = route_record[0 +: 10];
    wire [9:0] id1 = route_record[10 +: 10];
    wire [9:0] id2 = route_record[20 +: 10];
    wire id0_valid = (id0 < 4);
    wire id1_valid = (id1 < 4);
    wire id2_valid = (id2 < 4);
    wire exp_poison = !id0_valid || !id1_valid || !id2_valid;
    wire dup1 = id1_valid && id0_valid && (id1 == id0);
    wire dup2 = id2_valid && ((id0_valid && (id2 == id0)) ||
                              (id1_valid && (id2 == id1)));
    wire [3:0] exp_mask = {
        ((id0 == 3) && id0_valid) || ((id1 == 3) && id1_valid) || ((id2 == 3) && id2_valid),
        ((id0 == 2) && id0_valid) || ((id1 == 2) && id1_valid) || ((id2 == 2) && id2_valid),
        ((id0 == 1) && id0_valid) || ((id1 == 1) && id1_valid) || ((id2 == 1) && id2_valid),
        ((id0 == 0) && id0_valid) || ((id1 == 0) && id1_valid) || ((id2 == 0) && id2_valid)
    };
    wire [15:0] exp_dup = {13'b0, dup2, dup1, 1'b0};

    reg [3:0] model_mask0, model_mask1;
    reg [15:0] model_dup0, model_dup1;
    reg model_poison0, model_poison1;
    reg [15:0] model_txn0, model_txn1;
    reg model_wr, model_rd;
    reg [1:0] model_count;

    always @* begin
        route_record = 224'b0;
        route_record[0 +: 10] = {7'b0,id0_raw};
        route_record[10 +: 10] = {7'b0,id1_raw};
        route_record[20 +: 10] = {7'b0,id2_raw};
        route_record[160 +: 16] = txn_raw;
        route_record[191 +: 5] = 5'd3;
    end

    ot_route_mask #(
        .NUM_EXPERTS(4), .TOP_K(3), .EXPERT_ID_W(10),
        .FIFO_DEPTH(2), .CHECK_CRC(0)
    ) dut (
        .clk(clk), .rst_n(rst_n), .route_valid(route_valid),
        .route_ready(route_ready), .route_record(route_record),
        .ctx_valid(ctx_valid), .ctx_ready(ctx_ready), .ctx_mask(ctx_mask),
        .ctx_transaction_id(ctx_transaction_id), .ctx_epoch_id(ctx_epoch_id),
        .ctx_layer_id(ctx_layer_id), .ctx_top_k_count(ctx_top_k_count),
        .ctx_poison(ctx_poison), .ctx_duplicate_slots(ctx_duplicate_slots),
        .bad_crc_seen(bad_crc_seen), .bad_field_seen(bad_field_seen)
    );

    always @(posedge clk) begin
        f_past_valid <= 1'b1;
        rst_n <= 1'b1;
        // This harness exhausts the three active IDs.  CRC traversal is checked
        // independently by known-answer and fault tests.
        if (!rst_n) begin
            model_mask0 <= 0;
            model_mask1 <= 0;
            model_dup0 <= 0;
            model_dup1 <= 0;
            model_poison0 <= 0;
            model_poison1 <= 0;
            model_txn0 <= 0;
            model_txn1 <= 0;
            model_wr <= 0;
            model_rd <= 0;
            model_count <= 0;
        end else begin
            if (f_past_valid && $past(rst_n && route_valid && !route_ready)) begin
                assume(route_valid);
                assume(id0_raw == $past(id0_raw));
                assume(id1_raw == $past(id1_raw));
                assume(id2_raw == $past(id2_raw));
                assume(txn_raw == $past(txn_raw));
            end
            assert(model_count <= 2);
            assert(ctx_valid == (model_count != 0));
            assert(route_ready == ((model_count < 2) || (ctx_valid && ctx_ready)));
            assert(!bad_crc_seen);
            if (ctx_valid) begin
                assert(ctx_mask == (model_rd ? model_mask1 : model_mask0));
                assert(ctx_duplicate_slots == (model_rd ? model_dup1 : model_dup0));
                assert(ctx_poison == (model_rd ? model_poison1 : model_poison0));
                assert(ctx_transaction_id == (model_rd ? model_txn1 : model_txn0));
                assert(ctx_top_k_count == 5'd3);
            end
            if (f_past_valid && $past(rst_n && push && exp_poison))
                assert(bad_field_seen);
            if (f_past_valid && $past(bad_field_seen))
                assert(bad_field_seen);
            if (push) begin
                if (model_wr) begin
                    model_mask1 <= exp_mask;
                    model_dup1 <= exp_dup;
                    model_poison1 <= exp_poison;
                    model_txn1 <= route_record[160 +: 16];
                end else begin
                    model_mask0 <= exp_mask;
                    model_dup0 <= exp_dup;
                    model_poison0 <= exp_poison;
                    model_txn0 <= route_record[160 +: 16];
                end
                model_wr <= ~model_wr;
            end
            if (pop)
                model_rd <= ~model_rd;
            case ({push,pop})
                2'b10: model_count <= model_count + 1'b1;
                2'b01: model_count <= model_count - 1'b1;
                default: model_count <= model_count;
            endcase
            cover(push && dup1 && !exp_poison);
            cover(push && exp_poison);
            cover(model_count == 2 && push && pop);
        end
    end
endmodule
