`timescale 1ns/1ps
module tb_window_column_halfwrite;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0;
    reg [31:0] row_we=0;
    reg [127:0] write_data=0;
    reg read_v=0;
    reg [4:0] read_addr=0;
    wire [127:0] reference, candidate, default_path;
    ot_dsrom_window_column #(.WIDTH(128)) original
        (.clk(clk),.rst_n(rst_n),.row_we(row_we),.write_data(write_data),
         .read_v(read_v),.read_addr(read_addr),.read_data(reference));
    ot_dsrom_window_column_halfwrite_distributed #(.HALFWRITE(1)) dut
        (.clk(clk),.rst_n(rst_n),.row_we(row_we),.write_data(write_data),
         .read_v(read_v),.read_addr(read_addr),.read_data(candidate));
    ot_dsrom_window_column_halfwrite_distributed defdut
        (.clk(clk),.rst_n(rst_n),.row_we(row_we),.write_data(write_data),
         .read_v(read_v),.read_addr(read_addr),.read_data(default_path));
    integer checks=0, collisions=0, reset_writes=0;
    reg [31:0] rng=32'h13973bea;
    always @(posedge clk) begin
        if(read_v && row_we[read_addr]) collisions=collisions+1;
        if(!rst_n && |row_we) reset_writes=reset_writes+1;
        #1;
        if(reference !== candidate || reference !== default_path)
            $fatal(1,"COLUMN_HALFWRITE_MISMATCH check=%0d ref=%h got=%h",checks,reference,candidate);
        checks=checks+1;
    end
    task tick;
        begin
            // Drive after falling-edge commit, not in a simulator race with it.
            @(negedge clk); #1;
            rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
            write_data={rng,~rng,rng+32'd1,rng^32'h2abc2719};
        end
    endtask
    initial begin
        repeat(2) tick(); rst_n=1;
        for(integer i=0;i<32;i=i+1) begin row_we=32'b1<<i;tick();end
        row_we=0;read_v=1;
        for(integer i=0;i<32;i=i+1) begin read_addr=5'(i);tick();end
        for(integer i=0;i<3000;i=i+1) begin
            read_addr=rng[4:0];read_v=rng[5];
            row_we=rng[6] ? 32'b1<<read_addr : rng;
            if(i==700 || i==1700) rst_n=0;
            if(i==704 || i==1704) rst_n=1;
            tick();
        end
        row_we=0;read_v=0;repeat(4) tick();
        if(checks<3000 || collisions<300 || reset_writes<4) $fatal(1,"coverage missing");
        $display("PASS COLUMN_HALFWRITE checks=%0d collisions=%0d reset_writes=%0d added_cycles=0",checks,collisions,reset_writes);
        $finish;
    end
endmodule
