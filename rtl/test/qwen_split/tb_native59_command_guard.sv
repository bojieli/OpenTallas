`timescale 1ns/1ps
module tb_native59_command_guard;
    parameter integer MUT=0;
    `include "native380-test.svh"
    reg ck=0; always #1 ck=~ck;
    reg rst_n=0,command_valid=0,authority_valid=1,cap=1;
    reg [379:0] command=COMMAND;
    reg [15:0] epoch=16'hffed;
    reg [17:0] token=151935,position=8191;
    reg [5:0] stage=1;
    reg [58:0] tag;
    wire accepted,fault;wire [2:0] cause;
    wire [379:0] ac;wire [58:0] at;
    wire [23:0] xb,ob;wire [17:0] nout,k,np;
    wire [15:0] ne;wire [5:0] nl;
    qkd_native59_command_guard #(.MUT(MUT)) dut(
        .ck(ck),.rst_n(rst_n),.command_valid(command_valid),.command(command),.command_tag(tag),
        .fused_program_capability(cap),.authority_valid(authority_valid),.authority_epoch(epoch),
        .authority_token(token),.authority_position(position),.authority_stage(stage),
        .accepted(accepted),.accepted_command(ac),.accepted_tag(at),.native_xbase(xb),.native_obase(ob),
        .native_nout(nout),.native_k(k),.native_position(np),.native_epoch(ne),.native_layer(nl),
        .fault(fault),.fault_cause(cause));
    task reset;
        begin
            @(negedge ck);rst_n=0;command_valid=0;
            @(negedge ck);rst_n=1;
        end
    endtask
    task issue(input bit good,input [2:0] expected_cause);
        begin
            @(negedge ck);command_valid=1;
            @(posedge ck);#0.1;if(accepted)$fatal(1,"accepted before two capture edges");
            @(negedge ck);command_valid=0;
            @(posedge ck);#0.1;
            if(good) begin
                if(!accepted||fault||ac!==COMMAND||at!==tag||xb!=13696||ob!=3167||nout!=512||k!=128||
                   np!=position||ne!=epoch||nl!=stage-1)$fatal(1,"bad accepted command/context");
            end else if(accepted||!fault||cause!==expected_cause)$fatal(1,"fault check bypass cause=%b",cause);
            @(posedge ck);#0.1;if(accepted)$fatal(1,"accepted pulse stretched");
            if(!good&&!fault)$fatal(1,"fault not sticky");
        end
    endtask
    integer i;
    initial begin
        // All36 layers retain one actual token epoch; both sequence extremes.
        for(i=1;i<=36;i=i+1)begin
            stage=i;tag={epoch,stage,token,position[12:0],6'd0};reset;issue(1,0);
        end
        // Every actual descriptor bit, including otherwise ignored addresses,
        // must be preserved/checked, not only the native provider's five fields.
        for(i=0;i<380;i=i+1)begin
            command=COMMAND^(380'd1<<i);reset;issue(0,3'b001);
        end
        command=COMMAND;
        for(i=0;i<59;i=i+1)begin
            tag={epoch,stage,token,position[12:0],6'd0}^(59'd1<<i);reset;issue(0,3'b010);
        end
        tag={epoch,stage,token,position[12:0],6'd0};
        authority_valid=0;reset;issue(0,3'b010);authority_valid=1;
        cap=0;reset;issue(0,3'b100);cap=1;
        position=8192;tag={epoch,stage,token,position[12:0],6'd0};reset;issue(0,3'b010);
        position=8191;token=151936;tag={epoch,stage,token,position[12:0],6'd0};reset;issue(0,3'b010);
        token=151935;stage=0;tag={epoch,stage,token,position[12:0],6'd0};reset;issue(0,3'b010);
        stage=37;tag={epoch,stage,token,position[12:0],6'd0};reset;issue(0,3'b010);
        $display("PASS native380 guard:36 layers,380 descriptor faults,59 identity faults,6 boundary faults");$finish;
    end
endmodule
