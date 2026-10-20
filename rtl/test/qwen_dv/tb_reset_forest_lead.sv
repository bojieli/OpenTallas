`timescale 1ns/1ps
module tb_reset_forest_lead;
    reg ck=0, d=0;
    always #5 ck=~ck;
    genvar dep;
    generate for(dep=2;dep<=5;dep=dep+1) begin:g_depth
        wire [94:0] q,late;
        wire normal,normal_mut;
        reg [4:0] history=0;
        ot_pl_land_reset_forest_lead #(.DEPTH(dep),.LEAVES(95),.ROOT_LOADS(3)) dut(
            .ck(ck),.d(d),.q(q),.scalar_q(normal));
        ot_pl_land_reset_forest_lead #(.DEPTH(dep),.LEAVES(95),.ROOT_LOADS(3),.LATE(1)) mutant(
            .ck(ck),.d(d),.q(late),.scalar_q(normal_mut));
        reg [94:0] rq;
        always @(posedge ck) begin
            history<={history[3:0],d};
            rq<=q;
            #1;
            if($time>70) begin
                if(q!={95{history[dep-2]}}) $fatal(1,"LEAD_AGE depth=%0d",dep);
                if(normal!==history[dep-1] || rq!={95{history[dep-1]}})
                    $fatal(1,"SCALAR_RING_RESET_AGE depth=%0d",dep);
                if(late!={95{history[dep-1]}} || normal_mut!==normal)
                    $fatal(1,"MUTANT_LATE_AGE depth=%0d",dep);
            end
        end
    end endgenerate
    initial begin
        // Initial reset, first-token release and arbitrary repeated mid-run reset.
        repeat(300) begin @(negedge ck); d=$random; end
        $display("RESET_FOREST_LEAD_DEPTH2_TO5_RESET_AGE_PASS");
        $finish;
    end
endmodule
