`timescale 1ns/1ps
module tb_svc_qmem_capture;
    parameter integer NATIVE = 0;
    parameter integer MUTANT = 0;
    localparam integer H = 8;
    localparam integer W = 512;
    reg clk = 0;
    always #0.5 clk = ~clk;
    reg reset_n = 0;
    reg go = 0;
    reg phase = 0;
    reg run = 0;
    reg [9:0] rc = 0;
    reg [4:0] q_launch_count = H;
    wire launch = run && (NATIVE ? phase && q_launch_count < H : rc <= H);
    wire [3:0] read_addr = NATIVE ? 4'(q_launch_count) : 4'(rc - 1);
    wire [3:0] prefetch_addr = go ? 4'd0 : NATIVE ? 4'(q_launch_count) : 4'(rc);

    always @(posedge clk) begin
        if (!reset_n) begin
            phase <= 0;
            run <= 0;
            rc <= 0;
            q_launch_count <= H;
        end else begin
            phase <= !phase;
            if (go) begin
                run <= 1;
                rc <= 1;
                q_launch_count <= 0;
            end else if (run) begin
                rc <= rc + 1;
                if (NATIVE && launch) q_launch_count <= q_launch_count + 1;
            end
        end
    end

    reg we;
    reg [3:0] wa;
    reg [W-1:0] wd;
    wire [W-1:0] reference_data, prefetched;
    reg [W-1:0] captured;
    reg last_we;
    reg [3:0] last_wa;
    always @(posedge clk) begin
        captured <= prefetched;
        last_we <= we;
        last_wa <= wa;
    end

    dsdv_svc_mem_ar #(.W(W), .DEPTH(H), .AW(4), .SYNC(1)) reference (
        .clk(clk), .ra_n(read_addr), .we(we), .wa(wa), .wd(wd), .rd(reference_data));
    dsdv_svc_mem_ar #(.W(W), .DEPTH(H), .AW(4), .SYNC(0), .MUT(MUTANT)) prefetch (
        .clk(clk), .ra_n(prefetch_addr), .we(we), .wa(wa), .wd(wd), .rd(prefetched));

    integer checks = 0;
    integer collisions = 0;
    integer mismatches = 0;
    initial begin
        for (int i = 0; i < 4096; i++) begin
            @(negedge clk);
            reset_n = i >= 10 && (i % 701) > 2;
            go = reset_n && (i % 41 == 10);
            we = (i < H) || (i % 3 != 2);
            wa = i < H ? 4'(i) : i % 5 == 0 ? 4'(i % H) : prefetch_addr;
            for (int part = 0; part < W/16; part++)
                wd[16*part +: 16] = 16'((i+31)*(part+7));
            @(posedge clk);
            if (launch && !go && reset_n) begin
                checks++;
                if (last_we && last_wa == read_addr) collisions++;
                #0.01;
                if (captured !== reference_data) mismatches++;
            end
        end
        if (checks < 500 || collisions < 200 || ((mismatches != 0) != (MUTANT != 0)))
            $fatal(1, "Q capture native=%0d mutant=%0d checks=%0d collisions=%0d mismatches=%0d",
                NATIVE, MUTANT, checks, collisions, mismatches);
        $display("PASS Q capture native=%0d mutant=%0d checks=%0d collisions=%0d mismatches=%0d",
            NATIVE, MUTANT, checks, collisions, mismatches);
        $finish;
    end
endmodule
