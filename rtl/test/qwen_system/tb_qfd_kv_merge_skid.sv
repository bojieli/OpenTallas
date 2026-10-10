`timescale 1ns/1ps
module tb_qfd_kv_merge_skid;
    parameter integer MUT=0;
    localparam integer D=8,FWD=42,RET=34,AW=7,DW=512,N=600;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0,request=0,tok_v=0;
    reg [AW-1:0] tok_addr;
    reg [DW-1:0] tok_data;
    wire [DW-1:0] tok_mask={{(DW-8){1'b0}},8'hff};
    wire grant,tfault,free_credit,rfault,drained,kvw_ce;
    wire [AW-1:0] kvw_addr;wire [DW-1:0]kvw_data,kvw_mask;
    reg [FWD-1:0]fv; reg [AW+DW-1:0]fd[0:FWD-1];
    reg [RET-1:0]rc;
    integer sent=0,seen=0,tokens=0,cy=0,i,errors=0;
    integer target=N,tn=0,fh,scan,offers[0:4095],ports[0:4095];
    reg [2047:0] trace_name;
    reg [DW-1:0] golden[0:127], actual[0:127];
    reg [DW-1:0] payload;
    wire [DW-1:0] land_mask={ {(DW-8){1'b1}},8'h00};
    ot_qfd_kv_credit_tx #(.DEPTH(D)) tx(.clk(clk),.rst_n(rst_n),.request(request),
        .credit_return(rc[RET-1]),.grant(grant),.fault(tfault));
    ot_qfd_kv_merge_skid #(.DEPTH(D),.AW(AW),.DW(DW),.MUT_CREDIT_EARLY(MUT)) dut(
        .clk(clk),.rst_n(rst_n),.land_v(fv[FWD-1]),
        .land_addr(fd[FWD-1][AW+DW-1:DW]),.land_data(fd[FWD-1][DW-1:0]),.land_mask(land_mask),
        .tok_v(tok_v),.tok_addr(tok_addr),.tok_data(tok_data),.tok_mask(tok_mask),
        .credit_free(free_credit),.kvw_ce(kvw_ce),.kvw_addr(kvw_addr),
        .kvw_data(kvw_data),.kvw_mask(kvw_mask),.fault(rfault),.drained(drained));
    always @(posedge clk) begin
        if(!rst_n)begin fv<=0;rc<=0;for(i=0;i<FWD;i=i+1)fd[i]<=0;end
        else begin
            fv<={fv[FWD-2:0],grant};rc<={rc[RET-2:0],free_credit};
            fd[0]<={AW'(sent%128),payload};
            for(i=1;i<FWD;i=i+1)fd[i]<=fd[i-1];
            if(grant) begin
                golden[sent%128]=(golden[sent%128]&~land_mask)|(payload&land_mask);
                sent=sent+1;
            end
            if(tok_v) begin golden[tok_addr]=(golden[tok_addr]&~tok_mask)|(tok_data&tok_mask);tokens=tokens+1;end
            #1;
            if(kvw_ce)begin
                actual[kvw_addr]=(actual[kvw_addr]&~kvw_mask)|(kvw_data&kvw_mask);
                if(kvw_mask==land_mask)seen=seen+1;
            end
        end
    end
    initial begin
        fv=0;rc=0;tok_addr=0;tok_data=0;payload=0;
        for(i=0;i<128;i=i+1)begin golden[i]=0;actual[i]=0;end
        if($value$plusargs("trace=%s",trace_name))begin
            fh=$fopen(trace_name,"r");if(!fh)$fatal(1,"cannot read measured trace vectors");
            while(!$feof(fh))begin
                scan=$fscanf(fh,"%d %d\n",offers[tn],ports[tn]);
                if(scan==2)tn=tn+1;
                if(tn==4096)$fatal(1,"trace vector capacity exceeded");
            end
            $fclose(fh);target=tn;if(target==0)$fatal(1,"empty trace");
        end
        repeat(4)@(negedge clk);rst_n=1;
        // A300-cycle token burst lets an early-credit mutant overfill the queue.
        for(cy=0;cy<18000;cy=cy+1)begin
            @(negedge clk);
            request=(sent<target) && (cy%7!=3) && ((tn==0)||(cy>=offers[sent]));
            payload={16{32'(sent*7919+31+(tn==0?0:ports[sent]))}};
            tok_v=(cy<300)||(cy%97<17);
            tok_addr=AW'(cy%128);tok_data={16{32'(cy*13+5)}};
            if(MUT!=0 && (rfault||tfault))begin
                $display("NEG_DETECTED credit-early fault at cycle%0d sent%0d seen%0d",cy,sent,seen);$finish;
            end
            if(MUT==0 && (rfault||tfault))$fatal(1,"fault legal sender credits");
            if(sent==target && seen==target && drained && fv==0 && rc==0) cy=18000;
        end
        @(negedge clk);request=0;tok_v=0;
        repeat(RET+FWD+16)@(negedge clk);
        if(MUT!=0)$fatal(1,"mutant survived");
        for(i=0;i<128;i=i+1)if(golden[i]!==actual[i])errors=errors+1;
        if(errors||sent!=target||seen!=target||!drained)$fatal(1,"mismatch%0d sent%0d seen%0d",errors,sent,seen);
        $display("PASS fullshape DW512 credit RTT78 sent%0d retired%0d token-writes%0d exact128words",sent,seen,tokens);
        // An unreserved arrival must fail closed rather than silently overwrite.
        rst_n=0;repeat(3)@(negedge clk);rst_n=1;
        force dut.land_v=1;force dut.tok_v=1;
        repeat(D+2)@(negedge clk);
        if(!rfault||kvw_ce)$fatal(1,"overflow did not fail closed");
        $display("PASS unreserved overflow suppresses releases");$finish;
    end
endmodule
