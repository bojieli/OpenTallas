// Exact d818 enabled mechanism, only module name changed.
module status_enabled_reference #(parameter integer DMUT=0) (
    input wire clk,rst_n,
    input wire [143:0] bank_status,
    input wire [2:0] hub_status,
    input wire ring_fault,       // same-piece fault (replay), flags stage as before
    input wire ring_fault_late,  // ring stop faults over a crossing: 2 face edges late = the flags1 stage
    output reg [18:0] vmstat
);
    // Register the complete status frame before arithmetic. This separates face-to-status reach from the adder;
    // the numeric and flag paths both gain one edge. Payload registers need no reset: sum_valid guards warmup.
    reg [143:0] bank_status_q;
    reg [2:0] hub_status_q;
    reg ring_fault_q, ring_fault_late_q;
    always @(posedge clk) begin
        bank_status_q<=bank_status; hub_status_q<=hub_status;
        ring_fault_q<=ring_fault; ring_fault_late_q<=ring_fault_late;
    end

    reg [16:0] pair_sum[0:3];
    reg [17:0] half_sum[0:1];
    reg [2:0] flags0,flags1;
    reg [2:0] sum_valid;
    wire [18:0] total={1'b0,half_sum[0]}+{1'b0,half_sum[1]};
    reg [2:0] flags;
    always @* begin
        flags={hub_status_q[2]|hub_status_q[0]|ring_fault_q|(DMUT==2 && ring_fault_late_q),hub_status_q[1],1'b0};
        for(integer b=0;b<8;b=b+1)begin
            flags[2]=flags[2]|bank_status_q[b*18+17];
            flags[0]=flags[0]|bank_status_q[b*18+16];
        end
    end
    always @(posedge clk)begin
        for(integer i=0;i<4;i=i+1)
            pair_sum[i]<={1'b0,bank_status_q[(i*2)*18+:16]}+{1'b0,bank_status_q[(i*2+1)*18+:16]};
        half_sum[0]<={1'b0,pair_sum[0]}+{1'b0,pair_sum[1]};
        half_sum[1]<={1'b0,pair_sum[2]}+{1'b0,pair_sum[3]};
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin flags0<=0;flags1<=0;sum_valid<=0;vmstat<=0;end
        else begin
            flags0<=flags;flags1<=flags0;sum_valid<={sum_valid[1:0],1'b1};
            vmstat<=sum_valid[2]?{flags1|{DMUT!=2 && ring_fault_late_q,2'b0},(|total[18:16])?16'hffff:total[15:0]}:19'd0;
        end
endmodule
