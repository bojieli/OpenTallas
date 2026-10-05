`timescale 1ns/1ps
module tb_v41x_coll_pairwise #(parameter BAD_TAG = 0);
    localparam N=4, FW=32, TAGW=8, PW=FW+3+TAGW;
    reg clk=0, rst_n=0;
    always #5 clk=~clk;
    reg [3:0] offered=0;
    reg [3:0] mode=0;
    reg [7:0] tag[0:3];
    wire [3:0] in_ready, tx_ready_dummy;
    wire [N*N-1:0] tx_valid;
    wire [N*PW-1:0] tx_rec;
    wire [2*N*N-1:0] cr_out;
    wire [N-1:0] out_valid,out_last,out_err,fault;
    wire [N*FW-1:0] out_data;
    wire [N*2-1:0] out_rank;
    integer cycle=0, got=0;
    genvar s,t;
    generate for(s=0;s<N;s=s+1) begin : die
        wire [N-1:0] rv;
        wire [N*PW-1:0] rr;
        wire [2*N-1:0] ci;
        for(t=0;t<N;t=t+1) begin : link
            if(s==t) begin
                assign rv[t]=1'b0;
                assign rr[t*PW+:PW]=0;
                assign ci[2*t+:2]=0;
            end else begin
                assign rv[t]=tx_valid[t*N+s];
                assign rr[t*PW+:PW]=tx_rec[t*PW+:PW];
                assign ci[2*t+:2]=cr_out[2*(t*N+s)+:2];
            end
        end
        ot_rom_oneshot_die_px #(.N(4),.RANK(s),.LANES(1),.TAGW(TAGW),
          .DEPTH(16),.RELAY(0),.PAIRWISE(1),.ADD_LAT(3)) dut (
          .clk(clk),.rst_n(rst_n),.in_valid(!offered[s] && cycle>=20+4*s),
          .in_ready(in_ready[s]),.in_data(s==0?32'h60ad78ec:s==1?32'h40400000:s==2?32'he0ad78ec:32'h40800000),
          .in_last(1'b1),.in_mode(1'b0),.in_tag(tag[s]),
          .tx_valid(tx_valid[s*N+:N]),.tx_rec(tx_rec[s*PW+:PW]),.tx_ready(4'b1111),.cr_in(ci),
          .rx_valid(rv),.rx_rec(rr),.cr_out(cr_out[2*s*N+:2*N]),
          .rl_tx_valid(),.rl_tx_rec(),.rl_rx_valid(4'b0),.rl_rx_rec({N*PW{1'b0}}),
          .out_valid(out_valid[s]),.out_data(out_data[s*FW+:FW]),.out_last(out_last[s]),
          .out_rank(out_rank[s*2+:2]),.out_err(out_err[s]),.fault(fault[s]),.fault_code());
        always @(posedge clk) if(rst_n && !offered[s] && cycle>=20+4*s && in_ready[s]) offered[s]<=1;
        always @(posedge clk) if(out_valid[s]) begin
            if(!BAD_TAG && (out_data[s*FW+:FW] !== 32'h00000000 || !out_last[s] || out_err[s]))
                $fatal(1,"rank %0d pairwise got %h last %b err %b",s,out_data[s*FW+:FW],out_last[s],out_err[s]);
            got=got+1;
        end
    end endgenerate
    initial begin
        for(integer j=0;j<4;j=j+1) tag[j]=(BAD_TAG && j==3)?8'd8:8'd7;
        repeat(5) @(posedge clk); rst_n=1;
        wait(got==4);
        repeat(3) @(posedge clk);
        if (BAD_TAG) begin
            if (fault !== 4'b1111) $fatal(1,"expected all tag faults, got %b",fault);
            $display("PAIRWISE_PASS skewed_four_rank tag_mismatch_fault");
        end else begin
            if(|fault) $fatal(1,"fault %b",fault);
            $display("PAIRWISE_PASS skewed_four_rank exact 0x00000000 linear_would_be_4");
        end
        $finish;
    end
    always @(posedge clk) begin cycle<=cycle+1; if(cycle>200) $fatal(1,"timeout got=%0d",got); end
endmodule
