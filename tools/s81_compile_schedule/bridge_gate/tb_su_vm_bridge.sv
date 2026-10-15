`timescale 1ps/1ps
module tb_su_vm_bridge;
    reg s=0,t=0,rst_n=0;
    initial begin #120;forever begin t=1;#15;t=0;#15;end end
    initial begin #120;forever begin s=1;#20;s=0;#20;end end
    initial #100 rst_n=1;
    reg [15:0] srqv=0,swv=0,trsv=0;
    reg [223:0] srqa=0,swa=0;
    reg [255:0] swm=0;
    reg [8191:0] swd=0,trsd=0;
    wire [15:0] trqv,twv,srsv,rf,pf,wf;
    wire [223:0]trqa,twa;wire [255:0]twm;wire [8191:0]twd,srsd;
    wire fault;
    ot_s81_su_vm_static_bridge dut(
        .ck_req_s({16{s}}),.ck_req_t({16{t}}),.ck_rsp_pad_t({16{t}}),.ck_rsp_t({16{t}}),.ck_rsp_s({16{s}}),.ck_wr_s({16{s}}),.ck_wr_t({16{t}}),
        .rst_req_s_n({16{rst_n}}),.rst_req_t_n({16{rst_n}}),.rst_rsp_pad_t_n({16{rst_n}}),.rst_rsp_t_n({16{rst_n}}),.rst_rsp_s_n({16{rst_n}}),.rst_wr_s_n({16{rst_n}}),.rst_wr_t_n({16{rst_n}}),
        .s_rq_v(srqv),.s_rq_row(srqa),.s_rs_v(srsv),.s_rs_data(srsd),
        .s_wq_v(swv),.s_wq_row(swa),.s_wq_mask(swm),.s_wq_data(swd),
        .t_rq_v(trqv),.t_rq_row(trqa),.t_rs_v(trsv),.t_rs_data(trsd),
        .t_wq_v(twv),.t_wq_row(twa),.t_wq_mask(twm),.t_wq_data(twd),
        .req_fault(rf),.rsp_fault(pf),.wr_fault(wf),.fault(fault));
    integer si=-1,ti=-1,p,l,origin,source_edge,reads=0,writes=0,responses=0;
    function automatic [13:0] address(input integer port,edge_id,input bit write_kind);
        address=14'(100+19*port+edge_id+400*write_kind);
    endfunction
    function automatic [15:0] mask(input integer port,edge_id);
        mask=16'hffff^(16'h1<<((port+edge_id)%16));
    endfunction
    function automatic [511:0] payload(input integer port,edge_id,input bit response_kind);
        integer lane;
        for(lane=0;lane<16;lane=lane+1)
            payload[32*lane+:32]=32'h5a000000^(32'(port)<<20)^(32'(edge_id)<<8)^32'(lane)^(response_kind?32'h00800000:0);
    endfunction
    always @(negedge s)begin
        srqv=(si+1>=3 && si+1<15)?16'hffff:0;swv=srqv;
        for(integer k=0;k<16;k=k+1)begin
            srqa[14*k+:14]=address(k,si+1,0);swa[14*k+:14]=address(k,si+1,1);
            swm[16*k+:16]=mask(k,si+1);swd[512*k+:512]=payload(k,si+1,0);
        end
    end
    // Declared external VM response stimulus. No memory or compute model is
    // hidden inside the DUT; actual128SRAM composition is a separate gate.
    always @(negedge t)begin
        trsv=(ti+1>=5 && ti+1<24 && (ti+1)%4!=0)?16'hffff:0;
        for(integer k=0;k<16;k=k+1)trsd[512*k+:512]=payload(k,ti+1,1);
    end
    always @(posedge t)begin
        ti=ti+1;
        #1;
        case(ti%4)
            2:origin=3*(ti/4);
            3:origin=3*(ti/4)+1;
            0:origin=3*(ti/4)-1;
            default:origin=-1;
        endcase
        if(trqv!==((origin>=3 && origin<15)?16'hffff:0))$fatal(1,"request phase/valid T=%0d origin=%0d got=%h",ti,origin,trqv);
        if(twv!==trqv)$fatal(1,"write phase/valid T=%0d",ti);
        for(integer k=0;k<16;k=k+1)begin
            if(trqv[k])begin
                if(trqa[14*k+:14]!==address(k,origin,0))$fatal(1,"request address T=%0d port=%0d",ti,k);
                reads=reads+1;
            end
            if(twv[k])begin
                if(twa[14*k+:14]!==address(k,origin,1) || twm[16*k+:16]!==mask(k,origin) || twd[512*k+:512]!==payload(k,origin,0))
                    $fatal(1,"write payload/address/mask T=%0d port=%0d",ti,k);
                writes=writes+1;
            end
        end
    end
    always @(posedge s)begin
        si=si+1;
        #1;
        source_edge=4*(si/3)+si%3-3;
        if(srsv!==((source_edge>=5 && source_edge<24 && source_edge%4!=0)?16'hffff:0))
            $fatal(1,"response fixed phase S=%0d R=%0d got=%h",si,source_edge,srsv);
        for(integer k=0;k<16;k=k+1)if(srsv[k])begin
            if(srsd[512*k+:512]!==payload(k,source_edge,1))$fatal(1,"response payload S=%0d port=%0d",si,k);
            responses=responses+1;
        end
        if(si>5 && fault)$fatal(1,"bridge phase fault S=%0d rq=%h wr=%h rsp=%h",si,rf,wf,pf);
    end
    initial begin
        #2500;
        if(reads!=192 || writes!=192 || responses!=240 || fault)$fatal(1,"coverage r=%0d w=%0d rsp=%0d fault=%b",reads,writes,responses,fault);
        $display("BRIDGE_PROTOCOL_PASS read=%0d write=%0d response=%0d all16ports/all3phases/full512bits",reads,writes,responses);
        $finish;
    end
endmodule
