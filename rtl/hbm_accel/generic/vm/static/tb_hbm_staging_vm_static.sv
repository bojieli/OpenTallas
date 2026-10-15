`timescale 1ns/1ps
`default_nettype none
// 32 actual 128x256 landing SRAMs -> eight actual static VM banks, each with
// three actual 1024x256 SECDED SRAMs. No memory/response substitute is present.
module tb_hbm_staging_vm_static;
    parameter integer RG=3,WG=1;
    parameter integer MUT=0; // 1: flip VM sector row bit after delivery
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
    reg [8*RG*17-1:0] rq=0;
    reg read_phase=0;
    wire [8*RG*257-1:0] rr;
    wire [7:0] dq_done;
    wire [8*18-1:0] vm_status;
    for(genvar b=0;b<8;b=b+1)begin:bank
        wire [280:0] bank_dq={dq[b*281+280],
            dq[b*281+264+:16]^(MUT==1?16'h0008:16'd0),dq[b*281+:264]};
        ot_vms_bank_static #(.RG(RG),.WG(WG)) vm(
            .clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd1),
            .rslot_v(read_phase),.rslot($clog2(RG+1)'(0)),.wslot_v(1'b1),.wslot($clog2(WG+5)'(WG+4)),
            .rq(rq[b*RG*17+:RG*17]),.rr(rr[b*RG*257+:RG*257]),
            .wq({WG*281{1'b0}}),.wq_done(),.dq(bank_dq),.dq_done(dq_done[b]),
            .kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),
            .xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(vm_status[b*18+:18]));
    end
    function automatic [255:0] payload(input integer pc,slot);
        payload={8{32'h17624611 ^ (32'(pc)<<12) ^ 32'(slot)}};
    endfunction
    reg [7:0] expected_commit[0:1023];
    reg expected_read[0:1023];
    reg [2047:0] expected_data[0:1023];
    integer cycle=0,delivered=0,commits=0,readbacks=0,read_ordinal=0;
    integer first_delivery=-1,last_delivery=-1,first_commit=-1,last_commit=-1;
    task tick;
        reg [7:0] input_v;
        begin
            // Sample exactly what the physical bank samples at this edge.
            @(posedge clk);
            input_v=0;
            if(rst_n)begin
                for(integer b=0;b<8;b=b+1)input_v[b]=dq[b*281+280];
                expected_commit[cycle+3]=input_v;
                if(input_v!=0)begin
                    if(input_v!=8'hff)$fatal(1,"partial eight-bank delivery");
                    for(integer b=0;b<8;b=b+1)begin
                        if(dq[b*281+264+:16]!==16'(16'h2800+delivered*8+b)||
                           dq[b*281+8+:256]!==payload((delivered%4)*8+b,delivered/4)||
                           dq[b*281+:8]!==8'hff)
                            $fatal(1,"landing delivery mismatch ordinal=%0d bank=%0d",delivered,b);
                    end
                    if(first_delivery<0)first_delivery=cycle;last_delivery=cycle;delivered=delivered+1;
                end
                if(read_phase)begin
                    expected_read[cycle+6]=1;
                    for(integer b=0;b<8;b=b+1)begin
                        if(rq[b*RG*17+:17]!=={1'b1,16'(16'h2800+read_ordinal*8+b)})$fatal(1,"read request sequence");
                        expected_data[cycle+6][b*256+:256]=payload((read_ordinal%4)*8+b,read_ordinal/4);
                    end
                    read_ordinal=read_ordinal+1;
                end
            end
            #2;
            if(rst_n)begin
                if(fault||vm_status!=0)$fatal(1,"staging/VM fault cycle=%0d landing=%b vm=%h",cycle,fault,vm_status);
                if(dq_done!==expected_commit[cycle])$fatal(1,"DMA commit latency mismatch cycle=%0d got=%h expected=%h",cycle,dq_done,expected_commit[cycle]);
                for(integer b=0;b<8;b=b+1)begin
                    if(dq_done[b])commits=commits+1;
                    if(rr[b*RG*257+256]!==expected_read[cycle])$fatal(1,"read return slot mismatch cycle=%0d bank=%0d",cycle,b);
                    for(integer lane=1;lane<RG;lane=lane+1)if(rr[b*RG*257+lane*257+256]!==0)$fatal(1,"unselected read lane response");
                    if(expected_read[cycle])begin
                        if(rr[b*RG*257+:256]!==expected_data[cycle][b*256+:256])
                            $fatal(1,"actual VM memory mismatch cycle=%0d bank=%0d got=%h expected=%h",cycle,b,rr[b*RG*257+:256],expected_data[cycle][b*256+:256]);
                        readbacks=readbacks+1;
                    end
                end
                if(dq_done!=0)begin if(first_commit<0)first_commit=cycle;last_commit=cycle;end
            end
            cycle=cycle+1;@(negedge clk);
        end
    endtask
    initial begin
        for(integer i=0;i<1024;i=i+1)begin expected_commit[i]=0;expected_read[i]=0;expected_data[i]=0;end
        tick();rst_n=1;begin_v=1;tick();begin_v=0;
        for(integer s=0;s<64;s=s+1)begin
            fill_v='1;
            for(integer pc=0;pc<32;pc=pc+1)begin
                fill_slot[pc*6+:6]=6'(s);fill_epoch[pc*16+:16]=77;
                fill_data[pc*256+:256]=payload(pc,s);
            end
            tick();
        end
        fill_v=0;
        if(block_ready!==2'b01||fault)$fatal(1,"block admission");
        start=1;tick();start=0;
        repeat(256)tick();repeat(10)tick();
        if(busy||delivered!=256||commits!=2048)$fatal(1,"block drain delivered=%0d commits=%0d",delivered,commits);
        if(last_delivery-first_delivery!=255||first_commit-first_delivery!=3||last_commit-last_delivery!=3)
            $fatal(1,"delivery/commit sustained schedule mismatch");
        // Read every written sector back through the real VM macro/SECDED path.
        // The oracle uses the original PHY pseudo-channel and slot, independent
        // of the connected dq address. Address mutation reaches this check.
        read_phase=1;
        for(integer ordinal=0;ordinal<256;ordinal=ordinal+1)begin
            for(integer b=0;b<8;b=b+1)rq[b*RG*17+:RG*17]={{(RG-1)*17{1'b0}},1'b1,16'(16'h2800+ordinal*8+b)};
            tick();
        end
        read_phase=0;rq=0;repeat(9)tick();
        if(readbacks!=2048||read_ordinal!=256)$fatal(1,"incomplete readback=%0d",readbacks);
        $display("HBM_STAGING_VM_STATIC PASS landing_macros=32 vm_macros=24 sectors=2048 issue_slots=256 banks_per_cycle=8 DMA_commit_edges=3 readback_sectors=%0d read_edges=6",readbacks);
        $finish;
    end
endmodule
`default_nettype wire
