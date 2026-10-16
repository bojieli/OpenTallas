`timescale 1ns/1ps
`default_nettype none
// Actual mapped programme SRAM -> fixed QDQ beat issue -> actual decoder.
// Separate clock entries preserve the physical ability to deliver each phi-R;
// programme/engine clocks are same-domain, with matched interface phase.
// Programme format: valid0,op6:1,block14:7,src30:15,dst46:31,last47.
// The host writes canonical c7a1/PC-tagged words before launch. No normal ready,
// credit, memory-completion gate or shadow software-produced internal result.
// Shared host target decode/global launch and actual NW stations are external
// integration obligations; these explicit ports must not be tied away there.
module ot_hgi_qdq_program_static #(
    parameter integer RL=7, WC=4, MUT=0,IO_REGS=0,
    // LG=1: GEO-H four bank-pair LG port groups (ot_hgi_qdq_lg_port_group) between the engine and the VM
    // banks; adds exactly +2 read-return edges (rq,rr) and +1 write-commit edge (wq) to the fixed calendar.
    // LG=0 is the previous single-cluster boundary (unchanged behaviour).
    // LG=2: r2 groups (ot_hgi_qdq_lg_port_group_r2: capture register at the input pins + launch register at the
    // output pins) = +4 read-return edges and +2 write-commit edges over LG=0.
    parameter integer LG=0,
    parameter integer LGMUT=0, // bench only: 1 binds port groups 0/1 to each other's bank-pair write slice
    parameter integer TSPLIT=0, // 1: word-sliced transport leaves (control + NS read/write slices), zero added edges
    // LG port-group map (same form as ot_hbm_su_static_vm_ports): NPG groups = clk_lg roots; bank b belongs to group
    // BANK_GROUP[4b+:4]. NW/NE default = four bank pairs; SW/SE use NPG=5 with the H-DIE map (proposed 32'h43221100).
    parameter integer NPG=4,
    parameter [31:0] BANK_GROUP=32'h33221100
)(
    input wire clk_program,clk_transport,clk_dxl,clk_dbq,clk_daq,rst_n,
    input wire [NPG-1:0] clk_lg,
    input wire cfg_we,
    input wire [9:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire start_v,
    input wire [9:0] start_base,
    input wire [10:0] start_limit,
    input wire [15:0] start_loops,
    output wire program_active,program_done,
    output wire [8*17-1:0] rq,
    input wire [8*257-1:0] rr,
    output wire [8*281-1:0] wq,
    output wire beat_done,record_done,
    output wire fault
);
    wire [47:0] command;
    wire command_v,program_fault,engine_fault;
    wire [31:0] ordinal;
    ot_vms_calendar_static #(.W(48)) program_store(
        .clk(clk_program),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
        .calendar(command),.calendar_v(command_v),.ordinal(ordinal),
        .active(program_active),.done(program_done),.fault(program_fault));
    wire [8*17-1:0] rq_e; wire [8*257-1:0] rr_e; wire [8*281-1:0] wq_e;
    function automatic integer gcount(input integer g);
        gcount=0; for(integer b=0;b<8;b=b+1) if(BANK_GROUP[4*b+:4]==g) gcount=gcount+1;
    endfunction
    function automatic integer gmember(input integer g,input integer i);
        integer n; gmember=0; n=0;
        for(integer b=0;b<8;b=b+1) if(BANK_GROUP[4*b+:4]==g) begin if(n==i) gmember=b; n=n+1; end
    endfunction
    generate if(LG!=0) begin: lg_groups
        initial if(IO_REGS==0) $fatal(1,"LG port groups require the registered constant-bank transport (IO_REGS=1)");
        initial for(integer b=0;b<8;b=b+1) if(BANK_GROUP[4*b+:4]>=NPG) $fatal(1,"BANK_GROUP names a group >= NPG");
        for(genvar k=0;k<NPG;k=k+1) begin: g
            localparam integer N=gcount(k);
            localparam integer KW=(LGMUT==1&&k<2)?(k^1):k; // bench only: write slice bound to the partner group
            initial if(N<1 || gcount(KW)!=N) $fatal(1,"empty LG port group / mutant partner size differs");
            wire [N*17-1:0] rqi,rqo; wire [N*257-1:0] rri,rro; wire [N*281-1:0] wqi,wqo;
            for(genvar i=0;i<N;i=i+1) begin: bank
                assign rqi[i*17+:17]=rq_e[gmember(k,i)*17+:17];   assign rq[gmember(k,i)*17+:17]=rqo[i*17+:17];
                assign rri[i*257+:257]=rr[gmember(k,i)*257+:257]; assign rr_e[gmember(k,i)*257+:257]=rro[i*257+:257];
                assign wqi[i*281+:281]=wq_e[gmember(k,i)*281+:281]; assign wq[gmember(KW,i)*281+:281]=wqo[i*281+:281];
            end
            if(LG==2) begin: r2
            ot_hgi_qdq_lg_port_group_r2 #(.BANKS(N)) port_group(.clk(clk_lg[k]),.rst_n(rst_n),
                .rq_i(rqi),.rq_o(rqo),.rr_i(rri),.rr_o(rro),.wq_i(wqi),.wq_o(wqo));
            end else begin: r1
            ot_hgi_qdq_lg_port_group #(.BANKS(N)) port_group(.clk(clk_lg[k]),.rst_n(rst_n),
                .rq_i(rqi),.rq_o(rqo),.rr_i(rri),.rr_o(rro),.wq_i(wqi),.wq_o(wqo));
            end
        end
    end else begin: single_cluster
        assign rq=rq_e; assign rr_e=rr; assign wq=wq_e;
    end endgenerate
    ot_hgi_qdq_static #(.IO_REGS(IO_REGS),.RL(RL+(LG==2?4:LG!=0?2:0)),.WC(WC+(LG==2?2:LG!=0?1:0)),.MUT(MUT),.TSPLIT(TSPLIT)) engine(
        .clk_transport(clk_transport),.clk_dxl(clk_dxl),.clk_dbq(clk_dbq),.clk_daq(clk_daq),.rst_n(rst_n),.cmd_v(command_v&&command[0]),
        .cmd_op(command[6:1]),.cmd_block(command[14:7]),.cmd_src(command[30:15]),
        .cmd_dst(command[46:31]),.cmd_last(command[47]),
        .rq(rq_e),.rr(rr_e),.wq(wq_e),.beat_done(beat_done),.record_done(record_done),.fault(engine_fault));
    assign fault=program_fault|engine_fault;
endmodule
`default_nettype wire
