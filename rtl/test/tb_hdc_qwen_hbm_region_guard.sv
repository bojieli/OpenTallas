`timescale 1ns/1ps
module tb_hdc_qwen_hbm_region_guard;
    localparam NPC=128, NC=6, AW=32, FLAT=NPC*NC;
    reg clk=0,rst_n=0,bind_region=0,head_mode=0;
    always #5 clk=~clk;
    reg [5:0] layer=35;
    reg [8:0] user_id=1;
    wire region_valid,region_fault;
    wire [AW-1:0] layer_code_base,layer_scale_base,qk_norm_base;
    wire [AW-1:0] post_tp_base,packed_kv_base,head_code_base;
    wire [AW-1:0] head_scale_base,head_norm_base,embed_code_base,embed_scale_base;
    ot_hdc_qwen_hbm_regions u_regions (.valid(region_valid),.fault(region_fault),.*);
    reg [NPC*NC-1:0] in_req_v=0,in_req_we=0;
    reg [NPC*NC*AW-1:0] in_req_addr=0;
    reg [NPC*NC-1:0] out_req_rdy='1;
    wire [NPC*NC-1:0] out_req_v,in_req_rdy;
    wire fault;
    ot_hdc_qwen_hbm_region_guard u_guard (.*);
    integer checks=0, lane;
    task automatic probe(input integer owner,input [AW-1:0] addr,
                         input bit write_op,input bit should_pass);
        begin
            in_req_v=0;in_req_we=0;in_req_addr=0;
            lane=(addr[6:0]*NC)+owner;
            in_req_v[lane]=1;
            in_req_we[lane]=write_op;
            in_req_addr[lane*AW +: AW]=addr;
            #1;
            if (out_req_v[lane] !== should_pass ||
                in_req_rdy[lane] !== should_pass ||
                (|(out_req_v & ~(FLAT'(1)<<lane))))
                $fatal(1,"region guard owner=%0d addr=%0d write=%0d expected=%0d",
                       owner,addr,write_op,should_pass);
            checks=checks+1;
        end
    endtask
    initial begin
        repeat(2) @(negedge clk);rst_n=1;bind_region=1;
        @(negedge clk);bind_region=0;
        if (!region_valid || region_fault) $fatal(1,"stage/user bind failed");
        probe(0,layer_code_base+3047423,0,1);
        probe(0,layer_scale_base+1535,0,1);
        probe(0,layer_code_base+3047424,0,0);
        probe(1,qk_norm_base+639,0,1);
        probe(1,qk_norm_base+640,0,0);
        probe(2,post_tp_base+2047,0,1);
        probe(2,post_tp_base+2048,0,0);
        probe(3,embed_code_base+19447807,0,1);
        probe(3,embed_scale_base+9599,0,1);
        probe(3,embed_scale_base+9600,0,0);
        probe(4,head_norm_base+1023,0,1);
        probe(4,head_norm_base+1024,0,0);
        probe(5,packed_kv_base+262143,1,1);
        probe(5,packed_kv_base+262144,1,0);
        probe(0,layer_code_base,1,0);
        head_mode=1;
        probe(0,head_code_base+9732095,0,1);
        probe(0,head_scale_base+4751,0,1);
        probe(0,layer_code_base,0,0);
        in_req_v=0;
        @(negedge clk);
        if (!fault || region_fault) $fatal(1,"bad region did not latch local fault");
        $display("PASS Qwen HBM region guard checks=%0d layer=35 user=1",checks);
        $finish;
    end
endmodule
