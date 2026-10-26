`timescale 1ns/1ps
`default_nettype none
module tb_hgi_hc_aperture_static;
    parameter integer MUT=0;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,begin_v=0,begin_bank=0,start=0,start_bank=0;
    reg [15:0] begin_epoch=77,start_epoch=77,start_base_sector=16'h2800;
    reg [31:0] fill_v=0,fill_bank=0;
    reg [191:0] fill_slot=0;
    reg [511:0] fill_epoch=0;
    reg [8191:0] fill_data=0;
    wire [1:0] block_ready;
    wire [2247:0] dq;
    wire busy,fault;
    ot_hbm_svc_static_vm_delivery delivery(.*);
    reg desc_v=0,desc_slot=0;
    reg [15:0] desc_source_base=16'h2800;
    reg [8:0] desc_position_base=0;
    wire [2223:0] ap;
    wire bridge_fault;
    ot_hgi_hc_aperture_bridge_static #(.MUT(MUT)) bridge(
        .clk(clk),.rst_n(rst_n),.desc_v(desc_v),.desc_source_base(desc_source_base),
        .desc_slot(desc_slot),.desc_position_base(desc_position_base),.dq(dq),.ap(ap),.fault(bridge_fault));
    wire [7:0] write_done;
    reg [7:0] read_v=0,read_slot=0;
    reg [55:0] read_row=0;
    wire [7:0] read_valid;
    wire [8191:0] raw_weight;
    wire aperture_fault;
    ot_hgi_hc_aperture_static memory(
        .clk(clk),.rst_n(rst_n),.ap(ap),.write_done(write_done),
        .read_v(read_v),.read_slot(read_slot),.read_row(read_row),
        .read_valid(read_valid),.raw_weight(raw_weight),.fault(aperture_fault));
    // Actual HSRC1 g_wq->wd timing: synchronous aperture SRAM output, followed
    // by the existing HC parent capture. These are distinct real registers.
    reg [8191:0] wd;
    reg [7:0] wd_valid;
    always @(posedge clk)wd<=raw_weight;
    always @(posedge clk or negedge rst_n)if(!rst_n)wd_valid<=0;else wd_valid<=read_valid;
    function automatic [31:0] weight(input integer slot,bank,row,lane);
        weight=32'h3f000000|32'(slot<<21)|32'(bank<<18)|32'(row<<10)|32'(lane<<5)|32'h15;
    endfunction
    function automatic [255:0] sector_payload(input integer slot,bank,row,quarter);
        for(integer lane=0;lane<8;lane=lane+1)sector_payload[lane*32+:32]=weight(slot,bank,row,quarter*8+lane);
    endfunction
    reg [7:0] expected_commit[0:2047];
    reg [8191:0] expected_wd=0;
    reg [7:0] expected_wd_valid=0;
    integer cycle=0,commits=0,raw_sectors=0,captured_sectors=0,landed=0;
    task tick;
        reg [8191:0] expected_raw;
        reg [7:0] input_read;
        begin
            @(posedge clk);
            input_read=read_v;expected_raw=0;
            if(rst_n)begin
                for(integer b=0;b<8;b=b+1)begin
                    // Store sample -> macrocommit at next edge, fixed.
                    expected_commit[cycle+1][b]=ap[b*278+277];
                    if(dq[b*281+280])landed=landed+1;
                    for(integer q=0;q<4;q=q+1)
                        expected_raw[b*1024+q*256+:256]=sector_payload(int'(read_slot[b]),b,int'(read_row[b*7+:7]),q);
                end
            end
            #2;
            if(rst_n)begin
                if(fault||bridge_fault||aperture_fault)$fatal(1,"aperture/source fault atcycle%0d",cycle);
                if(write_done!==expected_commit[cycle])$fatal(1,"fixed macrocommit mismatch cycle=%0d",cycle);
                if(read_valid!==input_read||wd_valid!==expected_wd_valid)$fatal(1,"g_wq ML2 valid mismatch");
                for(integer b=0;b<8;b=b+1)begin
                    if(write_done[b])commits=commits+1;
                    if(read_valid[b])begin
                        if(raw_weight[b*1024+:1024]!==expected_raw[b*1024+:1024])
                            $fatal(1,"actual aperture memory mismatch cycle=%0d bank=%0d got=%h expected=%h",cycle,b,raw_weight[b*1024+:32],expected_raw[b*1024+:32]);
                        raw_sectors=raw_sectors+4;
                    end
                    if(wd_valid[b])begin
                        if(wd[b*1024+:1024]!==expected_wd[b*1024+:1024])$fatal(1,"g_wq wd capture mismatch");
                        captured_sectors=captured_sectors+4;
                    end
                end
                expected_wd=expected_raw;expected_wd_valid=input_read;
            end
            cycle=cycle+1;@(negedge clk);
        end
    endtask
    initial begin
        for(integer i=0;i<2048;i=i+1)expected_commit[i]=0;
        tick();rst_n=1;
        // Two full4096-sector slots, each filled by two actual2048-sector
        // landing blocks. Both physical landing buffers and HC slots exercised.
        for(integer block=0;block<4;block=block+1)begin
            begin_v=1;begin_bank=1'(block%2);begin_epoch=16'(77+block);
            desc_v=1;desc_slot=1'(block/2);desc_position_base=9'((block%2)*256);
            tick();begin_v=0;desc_v=0;
            for(integer s=0;s<64;s=s+1)begin
                fill_v='1;fill_bank={32{1'(block%2)}};
                for(integer pc=0;pc<32;pc=pc+1)begin
                    fill_slot[pc*6+:6]=6'(s);fill_epoch[pc*16+:16]=16'(77+block);
                    fill_data[pc*256+:256]=sector_payload(block/2,pc%8,(block%2)*64+s,pc/8);
                end
                tick();
            end
            fill_v=0;
            if(!block_ready[block%2])$fatal(1,"missing PHY block admission");
            start=1;start_bank=1'(block%2);start_epoch=16'(77+block);
            tick();start=0;
            repeat(256)tick();repeat(7)tick();
            if(busy||commits!=(block+1)*2048)$fatal(1,"missing committed block sectors=%0d",commits);
        end
        read_v=8'hff;
        for(integer phase=0;phase<2;phase=phase+1)begin
            for(integer row=0;row<128;row=row+1)begin
                for(integer b=0;b<8;b=b+1)begin
                    read_slot[b]=1'((phase+b)%2);read_row[b*7+:7]=7'((row+b*7)%128);
                end
                tick();
            end
        end
        read_v=0;repeat(3)tick();
        if(commits!=8192||landed!=8192||raw_sectors!=8192||captured_sectors!=8192)$fatal(1,"incomplete aperture inventory");
        $display("HC_APERTURE_STATIC PASS slots=2 W=32 RMAX=128 PMAX=8 landing_macros=32 weight_macros=64 write_sectors=8192 readback_sectors=8192 captured_sectors=8192 sectors_per_cycle=8 g_wq_ML=2");
        $finish;
    end
endmodule
`default_nettype wire
