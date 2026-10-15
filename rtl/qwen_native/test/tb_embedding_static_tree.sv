`timescale 1ns/1ps
// Minimal real-macro tree composition vehicle: two adjacent code banks and
// two scale banks. All-vocabulary leaf proof is a separate cohort run.
module tb_embedding_static_tree;
    reg clk=0;always #0.4166665 clk=~clk;
    reg rst_n=0,cv=0,sv=0;
    reg [11:0] cb=0,sb=0;
    reg [23:0] ca=0,sa=0;
    wire cq,sq,cf,sf;
    wire [23:0] cqa,sqa;
    wire [511:0] cd,sd;
    ot_qwen_embedding_static_tree #(.LEVEL(1),.BASE(0)) code(
        .clk(clk),.rst_n(rst_n),.i_v(cv),.i_bank(cb),.i_addr(ca),
        .o_v(cq),.o_addr(cqa),.o_data(cd),.fault(cf));
    ot_qwen_embedding_static_tree #(.LEVEL(1),.BASE(2374)) scale(
        .clk(clk),.rst_n(rst_n),.i_v(sv),.i_bank(sb),.i_addr(sa),
        .o_v(sq),.o_addr(sqa),.o_data(sd),.fault(sf));
    reg [511:0] expected0[0:4095],expected1[0:4095];
    reg [255:0] scales0[0:4095],scales1[0:4095];
    reg [6:0] cvp=0,svp=0;
    reg [23:0] cap[0:6],sap[0:6];
    integer j,checked=0,mut;
    string dir;
    reg [511:0] want;
    always @(posedge clk) begin
        cvp <= {cvp[5:0],cv};svp <= {svp[5:0],sv};
        cap[0]<=ca;sap[0]<=sa;
        for(j=1;j<7;j=j+1) begin cap[j]<=cap[j-1];sap[j]<=sap[j-1];end
        #0.01;
        if(rst_n) begin
            if(cq!==cvp[6] || sq!==svp[6]) $fatal(1,"fixed tree timing mismatch");
            if(cf||sf) $fatal(1,"unexpected static tree fault");
            if(cq) begin
                want=cap[6]<4096?expected0[cap[6]&4095]:expected1[cap[6]&4095];
                if(mut==1) want=want^1;
                if(cqa!==cap[6] || cd!==want) $fatal(1,"code mismatch addr=%0d",cap[6]);
                checked=checked+1;
            end
            if(sq) begin
                want=0;
                want[15:0]=sap[6]<65536?scales0[(sap[6]>>4)&4095][sap[6][3:0]*16+:16]
                                                  :scales1[(sap[6]>>4)&4095][sap[6][3:0]*16+:16];
                if(sqa!==sap[6] || sd!==want) $fatal(1,"scale mismatch addr=%0d",sap[6]);
                checked=checked+1;
            end
        end
    end
    task code_read(input integer a);
        begin @(negedge clk);cv=1;ca=a;cb=a>>12;
              @(negedge clk);cv=0;end
    endtask
    task scale_read(input integer a);
        begin @(negedge clk);sv=1;sa=a;sb=2374+(a>>16);
              @(negedge clk);sv=0;end
    endtask
    integer k;
    initial begin
        mut=0;void'($value$plusargs("MUT=%d",mut));
        if(!$value$plusargs("EXPECTED_DIR=%s",dir)) $fatal(1,"EXPECTED_DIR required");
        $readmemh({dir,"/qembed_code_b0.hex"},expected0);
        $readmemh({dir,"/qembed_code_b1.hex"},expected1);
        $readmemh({dir,"/qembed_scale_b0.hex"},scales0);
        $readmemh({dir,"/qembed_scale_b1.hex"},scales1);
        repeat(3) @(negedge clk);rst_n=1;
        // Full 4096-element rows on either side of token63/64 bank boundary.
        for(k=4032;k<4160;k=k+1) code_read(k);
        scale_read(0);scale_read(15);scale_read(16);scale_read(65535);scale_read(65536);
        repeat(10) @(negedge clk);
        if(checked!=133) $fatal(1,"missing responses %0d",checked);
        $display("PASS static tree real macro:128 code chunks+5 scale lanes, fixed6edge latency");$finish;
    end
endmodule
