`timescale 1ns/1ps
// Changed address hook only: actual nonzero/wrap addresses, refusal and OFF.
// The full production head-shape rejection is checked with the retained SM exe.
module tb_hbm_w2_changed_address_hook;
    reg active, bound, valid, row_ok;
    reg [6:0] delta, xa;
    reg [12:0] row;
    wire [6:0] on_xa, off_xa;
    wire on_fault, off_fault;
    integer base, r, group, checks=0;
    ot_hbm_accel_w2_address_hook #(.ENABLE(1)) on_hook (
        .pair_active(active),.pair_shape_bound(bound),.pair_delta(delta),
        .issue_v(valid),.issue_row_ok(row_ok),.virtual_row(row),
        .absolute_xa(xa),.selected_xa(on_xa),.fault(on_fault));
    ot_hbm_accel_w2_address_hook off_hook (
        .pair_active(active),.pair_shape_bound(bound),.pair_delta(delta),
        .issue_v(valid),.issue_row_ok(row_ok),.virtual_row(row),
        .absolute_xa(xa),.selected_xa(off_xa),.fault(off_fault));
    task check(input [6:0] want, input want_fault);
        begin
            #1;
            if(on_xa!==want || on_fault!==want_fault || off_xa!==xa || off_fault!==0)
                $fatal(1,"hook row=%0d xa=%0d got=%0d fault=%0d",row,xa,on_xa,on_fault);
            checks=checks+1;
        end
    endtask
    initial begin
        active=1;bound=1;valid=1;row_ok=1;delta=16;
        // Literal paired W2 bases 48/64, 80/96 and 112/0. No new payloads.
        for(base=48;base<=112;base=base+32)
            for(r=0;r<4;r=r+1) for(group=0;group<16;group=group+1) begin
                row=r;xa=base+group;
                check((r>=2)?((base+group+16)%128):((base+group)%128),0);
            end
        row=4;xa=112;check(0,1);
        row=2;bound=0;check(0,1);
        valid=0;check(0,0);
        valid=1;row_ok=0;check(0,0);
        row_ok=1;active=0;check(112,0);
        $display("PASS changed_hook checks=%0d defaultOFF nonzero wrap refusal",checks);
        $finish;
    end
endmodule
