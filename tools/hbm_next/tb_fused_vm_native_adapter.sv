`timescale 1ns/1ps
`default_nettype none
module tb_fused_vm_native_adapter;
    reg rv,wv; reg [15:0] rs,ws; reg [255:0] wd; reg [256:0] nr;
    wire [17:0] rq; wire [281:0] wq; wire rr_v; wire [255:0] rr_d;
    ot_hnx_fused_vm_native_adapter dut(.fused_rq_v(rv),.fused_rq_sector(rs),.native_rq(rq),
        .fused_wq_v(wv),.fused_wq_sector(ws),.fused_wq_data(wd),.native_wq(wq),
        .native_rr(nr),.fused_rr_v(rr_v),.fused_rr_data(rr_d));
    integer i,j;
    initial begin
        rv=0;wv=0;rs=0;ws=0;wd=0;nr=0;
        for(i=0;i<1024;i=i+1) begin
            rv=i[0];wv=i[1];rs=(i<512)?16'h8000|i:i;ws=(i<512)?16'hffff-i:i;
            for(j=0;j<8;j=j+1)begin wd[j*32+:32]=$random;nr[j*32+:32]=$random;end
            if(i<256)begin wd=256'b1<<i;nr={i[0],256'b1<<(255-i)};end
            else nr[256]=i[2];
            #1;
            if(rq!=={rv,1'b0,rs})$fatal(1,"read sector/valid mismatch at %0d",i);
            if(wq!=={wv,1'b0,ws,wd,8'hff})$fatal(1,"write sector/data/mask mismatch at %0d",i);
            if(rr_v!==nr[256]||rr_d!==nr[255:0])$fatal(1,"read response mismatch at %0d",i);
        end
        $display("FUSED_VM_NATIVE_ADAPTER PASS vectors=1024 added_cycles=0 high_address=15 data_bits=256 mask=ff");
        $finish;
    end
endmodule
`default_nettype wire
