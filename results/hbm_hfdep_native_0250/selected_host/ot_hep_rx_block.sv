module ot_hep_rx_block #(parameter integer MUT = 0) (
    input  wire          clk, rst_n,
    input  wire          arm_v,
    input  wire [6:0]    block_words,
    input  wire          phy_v,
    input  wire [611:0]  phy_flit,
    output wire          phy_ready,
    output wire          block_ready,
    input  wire          release_v,
    input  wire          slot_v,
    input  wire [5:0]    slot_index,
    output reg           pin_v,
    output wire [9:0]    pin_vr,         
    output reg  [611:0]  pin_flit,
    output reg           fault,
    output reg  [4:0]    fault_cause
);
    localparam integer SL = 64, NSL = 10;
    localparam [2:0] EMPTY = 0, FILL = 1, SEAL = 2, READY = 3, DRAIN = 4, FLUSH = 5;
    reg [2:0] state;
    reg [6:0] count, words, issued;
    reg seal_age;
    reg [1:0] flush_age;
    reg [5:0] ra;
    reg [1:0] vp;                        
    (* keep *) reg [NSL-1:0] vp2r;
    (* keep *) reg [NSL-1:0] pvr;
    wire accept = phy_v && phy_ready;
    wire [611:0] mem_data;
    wire issue = slot_v && state == DRAIN && issued < words && slot_index == issued[5:0];
    assign phy_ready = state == FILL && count < words && !fault;
    assign block_ready = (state == READY) || (MUT == 2 && state == FILL && count != 0);
    assign pin_vr = pvr;
    for (genvar b = 0; b < 2; b = b + 1) begin : g_mem
        ot_hep_rx_leaf #(.W(306), .MUT((MUT == 1 && b == 0) ? 1 : 0)) u_mem (
            .ck(clk), .we(accept), .wa(count[5:0]), .ra(ra),
            .din(phy_flit[b*306 +: 306]), .dout(mem_data[b*306 +: 306]));
    end
    integer j;
    always @(posedge clk)
        for (j = 0; j < 612; j = j + 1) if (vp2r[j / SL]) pin_flit[j] <= mem_data[j];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= EMPTY; count <= 0; words <= 0; issued <= 0; seal_age <= 0; flush_age <= 0;
            ra <= 0; vp <= 0; vp2r <= 0; pvr <= 0; pin_v <= 0; fault <= 0; fault_cause <= 0;
        end else begin
            vp <= {vp[0], issue};
            vp2r <= {NSL{vp[1]}};
            pvr <= vp2r; pin_v <= vp2r[0];
            if (issue) ra <= slot_index;
            if (arm_v && (state != EMPTY || block_words == 0 || block_words > 64)) begin fault <= 1; fault_cause[0] <= 1; end
            if (release_v && !block_ready) begin fault <= 1; fault_cause[1] <= 1; end
            if (slot_v && !issue) begin fault <= 1; fault_cause[2] <= 1; end
            if (arm_v && state == EMPTY && block_words >= 1 && block_words <= 64) begin
                state <= FILL; count <= 0; words <= block_words; issued <= 0;
            end
            if (accept) begin
                count <= count + 1'b1;
                if (count + 1'b1 == words) begin state <= SEAL; seal_age <= 0; end
            end
            if (state == SEAL) begin
                seal_age <= 1;
                if (seal_age) state <= READY;
            end
            if (release_v && block_ready) begin state <= DRAIN; issued <= 0; end
            if (issue) begin
                issued <= issued + 1'b1;
                if (issued + 1'b1 == words) begin state <= FLUSH; flush_age <= 0; end
            end
            if (state == FLUSH) begin
                flush_age <= flush_age + 1'b1;
                if (flush_age == 3) state <= EMPTY;
            end
        end
    end
endmodule
