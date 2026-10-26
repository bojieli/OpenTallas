`timescale 1ns/1ps
module tb_hgi_qdq_record_calendar #(parameter integer MUT=0);
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,cfg_we=0,start_v=0;
    reg [9:0] cfg_addr=0;reg [255:0] cfg_data=0;
    wire v,active,done,fault;wire [47:0] command;wire [31:0] cycle;
    ot_hgi_qdq_record_calendar #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .start_v(start_v),.start_base(10'd0),.start_limit(11'd8),.command_v(v),.command(command),.cycle(cycle),.active(active),.done(done),.fault(fault));
    integer f,fd,nrec,k,beat=0,record=0,seen=0,total=0,finish_seen=0;
    integer op[0:7],n[0:7],ab[0:7],ob[0:7],price[0:7],block_n[0:7],timestamp[0:7];
    reg [255:0] words[0:7];reg [47:0] expected;
    initial begin
        fd=$fopen("tools/hgi_unit_tput/vectors/qdqvec/recs.txt","r");void'($fscanf(fd,"%d",nrec));
        for(k=0;k<8;k++)begin
            void'($fscanf(fd,"%d %d %d %d %d %d",op[k],n[k],ab[k],ob[k],price[k],block_n[k]));
            ab[k]=ab[k]%65536;ob[k]=ob[k]%65536;
            timestamp[k]=k==0?8:timestamp[k-1]+n[k-1]/32+((k%2)?0:1000);
            words[k]=0;words[k][255:240]=16'hc7a1;words[k][233:224]=10'(k);
            words[k][93:0]={8'(block_n[k]),6'(op[k]),16'(ob[k]/8),16'(ab[k]/8),16'(n[k]/32),32'(timestamp[k])};
            total+=n[k]/32;
        end
        $fclose(fd);
        repeat(4) @(negedge clk);rst_n=1;repeat(4) @(negedge clk);
        for(k=0;k<8;k++)begin cfg_we=1;cfg_addr=10'(k);cfg_data=words[k];@(negedge clk);end
        cfg_we=0;repeat(4) @(negedge clk);start_v=1;@(negedge clk);start_v=0;
        repeat(4000)begin
            @(negedge clk);
            if(fault)$fatal(1,"record calendar fault cycle%0d",cycle);
            if(v)begin
                if(record>=8)$fatal(1,"extra command");
                expected={(beat==n[record]/32-1),16'(ob[record]/8+beat*4),16'(ab[record]/8+beat*4),8'(block_n[record]),6'(op[record]),1'b1};
                if(command!==expected || cycle!=timestamp[record]+beat+1)
                    $fatal(1,"record command/cycle mismatch record%0d beat%0d cycle%0d expectedcycle%0d",record,beat,cycle,timestamp[record]+beat+1);
                seen++;beat++;
                if(beat==n[record]/32)begin beat=0;record++;end
            end
            if(done)finish_seen++;
        end
        if(seen!=total || finish_seen!=1 || active)$fatal(1,"record accounting %0d/%0d done%0d active%b",seen,total,finish_seen,active);
        $display("PASS QUANT_RECORD_CALENDAR native_records=8 beats=%0d long_idle_cycles=3000 adjacent_records=4 mapped_programme_macros=1",seen);$finish;
    end
endmodule
