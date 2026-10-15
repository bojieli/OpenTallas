`timescale 1ns/1ps
module tb_static_embed_return_chain;
    localparam N=32,B=100;
    reg ck=0;always #0.4166665 ck=~ck;
    reg rn=0;
    reg [N-1:0] cap=0,cv=0,xfer=0;
    reg [N*298-1:0] record=0;
    wire [(N+1)*299-1:0] chain;
    wire [N-1:0] fault;
    assign chain[N*299+:299]=0;
    genvar i;
    generate for(i=0;i<N;i=i+1) begin:g_hop
        qkd_embedding_static_return_hop hop(.ck(ck),.rst_n(rn),.capture_slot(cap[i]),.capture_v(cv[i]),
            .capture_record(record[i*298+:298]),.transfer_slot(xfer[i]),
            .upi(chain[(i+1)*299+:299]),.upo(chain[i*299+:299]),.fault(fault[i]));
    end endgenerate
    function automatic [297:0] payload(input integer pc);
        payload={16'd43,1'b0,pc[0],6'(pc>>1),18'd65536,
                 256'hfedcba9876543210_0123456789abcdef_aa55aa55cc33cc33_0f0f0f0ff0f0f0f0^256'(pc)};
    endfunction
    integer mode=0,t,p,count=0;
    initial begin
        void'($value$plusargs("MUT=%d",mode));
        for(t=0;t<170;t=t+1)begin
            @(negedge ck);
            if(t==2)rn=1;
            cap=0;cv=0;xfer=0;
            for(p=0;p<N;p=p+1) begin
                record[p*298+:298]=payload(p);
                if(t==5)begin cap[p]=1;cv[p]=!(mode==2&&p==17);end
                if(mode==3&&p==17&&t==10)begin cap[p]=1;cv[p]=1;end
                if(mode==4&&p==17)record[p*298+:298]^=1;
                if(t==B-p-1+((mode==1&&p==17)?1:0))xfer[p]=1;
            end
            @(posedge ck);#0.01;
            if(|fault)$fatal(1,"static return chain conflict/missing/overwrite");
            if(chain[0]!=(t>=B&&t<B+N))$fatal(1,"unexpected chain valid edge%0d",t);
            if(chain[0])begin
                if(chain[298:1]!==payload(t-B))$fatal(1,"actual retained record mismatch edge%0d",t);
                count=count+1;
            end
        end
        if(count!=N)$fatal(1,"incomplete train");
        $display("PASS full32PC static return chain:32real retained298bitrecords, 2edges/hop, contiguous root slots100..131 no-wait/no-priority");$finish;
    end
endmodule
