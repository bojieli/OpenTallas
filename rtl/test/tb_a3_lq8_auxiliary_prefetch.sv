`timescale 1ns/1ps
module tb_a3_lq8_auxiliary_prefetch;
    parameter integer DEPTH=8;
    parameter bit REGISTER_REQUESTS=0;
    localparam integer CW=$clog2(DEPTH+1);
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,clear=0,run=0,inject_stale=0,inject_early=0;
    reg [31:0] generation=7;
    integer accepted=0,sent=0,responded=0,consumed=0,ticks=0,peak=0;
    wire request_ready,service_valid,response_ready,response_mismatch,auxiliary_valid;
    wire request_valid=run && accepted<100;
    wire service_ready=ticks>DEPTH+2 && ticks%7!=2;
    wire response_valid=inject_stale || inject_early || (run && responded<sent && ticks>12 && ticks%5!=1);
    wire auxiliary_ready=run && ticks>24 && ticks%9<6;
    wire [31:0] service_generation,service_a,service_s,service_ws,service_w;
    wire [31:0] auxiliary_generation,auxiliary_a,auxiliary_s,auxiliary_ws,auxiliary_w;
    wire [63:0] auxiliary_a_data,auxiliary_ws_data;
    wire [31:0] auxiliary_s_data;
    wire [CW-1:0] occupied;
    ot_a3_lq8_auxiliary_prefetch #(.DEPTH(DEPTH),.REGISTER_REQUESTS(REGISTER_REQUESTS)) dut(
        .clk(clk),.rst_n(rst_n),.clear(clear),
        .request_valid(request_valid),.request_ready(request_ready),
        .request_generation(generation),.request_a(32'(accepted+10)),.request_s(32'(accepted+20)),
        .request_ws(32'(accepted+30)),.request_w(32'(accepted)),
        .service_valid(service_valid),.service_ready(service_ready),
        .service_generation(service_generation),.service_a(service_a),.service_s(service_s),.service_ws(service_ws),.service_w(service_w),
        .response_valid(response_valid),.response_ready(response_ready),.response_mismatch(response_mismatch),
        .response_generation(inject_stale?generation-1:generation),.response_w(32'(responded)),
        .response_a_data(64'(responded+40)),.response_s_data(32'(responded+50)),.response_ws_data(64'(responded+60)),
        .auxiliary_valid(auxiliary_valid),.auxiliary_ready(auxiliary_ready),
        .auxiliary_generation(auxiliary_generation),.auxiliary_a(auxiliary_a),.auxiliary_s(auxiliary_s),
        .auxiliary_ws(auxiliary_ws),.auxiliary_w(auxiliary_w),
        .auxiliary_a_data(auxiliary_a_data),.auxiliary_s_data(auxiliary_s_data),.auxiliary_ws_data(auxiliary_ws_data),.occupied(occupied));
    reg service_held=0;reg [159:0] held_request;
    wire [159:0] service_bundle={service_generation,service_a,service_s,service_ws,service_w};
    reg held=0;reg [319:0] held_bundle;
    wire [319:0] bundle={auxiliary_generation,auxiliary_a,auxiliary_s,auxiliary_ws,auxiliary_w,
        auxiliary_ws_data,auxiliary_s_data,auxiliary_a_data};
    always @(posedge clk)begin
        if(rst_n && !clear && run)begin
            ticks<=ticks+1;
            if(32'(occupied)>DEPTH || 32'(occupied)!=accepted-consumed || sent>accepted || responded>sent || consumed>responded)$fatal(1,"reservation accounting");
            if(32'(occupied)>peak)peak<=32'(occupied);
            if(held && (!auxiliary_valid || bundle!==held_bundle))$fatal(1,"held response changed");
            held<=auxiliary_valid && !auxiliary_ready;held_bundle<=bundle;
            if(REGISTER_REQUESTS && ticks==DEPTH+2 && occupied!=CW'(DEPTH))$fatal(1,"service stall blocked reservation");
            if(service_held && (!service_valid || service_bundle!==held_request))$fatal(1,"held service request changed");
            service_held<=service_valid && !service_ready;held_request<=service_bundle;
            if(request_valid && request_ready)accepted<=accepted+1;
            if(service_valid && service_ready)begin
                if(service_generation!=generation || service_w!=32'(sent) || service_a!=32'(sent+10) ||
                   service_s!=32'(sent+20) || service_ws!=32'(sent+30))$fatal(1,"service identity");
                sent<=sent+1;
            end
            if(response_valid && response_ready)responded<=responded+1;
            if(auxiliary_valid && auxiliary_ready)begin
                if(auxiliary_generation!=generation || auxiliary_w!=32'(consumed) ||
                   auxiliary_a!=32'(consumed+10) || auxiliary_s!=32'(consumed+20) || auxiliary_ws!=32'(consumed+30) ||
                   auxiliary_a_data!=64'(consumed+40) || auxiliary_s_data!=32'(consumed+50) || auxiliary_ws_data!=64'(consumed+60))
                    $fatal(1,"response data or order");
                consumed<=consumed+1;
            end
        end else begin held<=0;service_held<=0;end
    end
    task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
    initial begin
        tick();rst_n=1;run=1;
        wait(occupied==CW'(DEPTH));@(negedge clk);
        if(REGISTER_REQUESTS)begin
            inject_early=1;#1;
            if(sent!=0 || response_ready || !response_mismatch)$fatal(1,"undispatched response accepted");
            inject_early=0;
        end
        inject_stale=1;
        #1;if(response_ready || !response_mismatch)$fatal(1,"stale generation accepted");
        tick();inject_stale=0;
        wait(consumed==100);@(negedge clk);run=0;
        if(occupied!=0 || peak!=DEPTH)$fatal(1,"capacity not exercised");
        // Refill under a new operation, then clear while requests are pending.
        clear=1;tick();clear=0;generation=8;accepted=0;sent=0;responded=0;consumed=0;ticks=0;run=1;
        wait(occupied!=0);@(negedge clk);clear=1;run=0;tick();
        if(occupied!=0 || auxiliary_valid || service_valid)$fatal(1,"clear left credits");
        clear=0;inject_stale=1;#1;
        if(response_ready || !response_mismatch)$fatal(1,"orphan response accepted");
        tick();inject_stale=0;
        generation=9;accepted=0;sent=0;responded=0;consumed=0;ticks=0;run=1;
        wait(consumed==100);@(negedge clk);run=0;
        $display("PASS auxiliary prefetch depth=%0d words=200 peak=%0d",DEPTH,peak);$finish;
    end
    initial begin #100000;$fatal(1,"timeout");end
endmodule
