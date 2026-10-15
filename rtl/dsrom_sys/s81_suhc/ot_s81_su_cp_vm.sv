`timescale 1ns/1ps
// CP kind14 descriptor bridge. Decoded descriptor words:0 output row,1 kv row,
//2 dimension count (must512),3 score row,4 group identity,5 {pool,slot}.
// Two real VM read ports fetch16 kv and16 scores at compiled cycles0,4,..124;
// fixed LVM return10,14,..134 is sliced into four4-dimension cache beats.
// Output four widenedBF16 words/cycle is assembled into32 complete512-bit rows.
// No ready, credits, demand arbitration or variable issue/retirement exists.
module ot_s81_su_cp_vm #(
    parameter integer LVM=10,WCOMMIT=1,MUT=0
) (
    input wire clk,ck_cp_ctl,
    input wire [1:0] ck_cp_mem,
    input wire [3:0] ck_cp_lane,
    input wire rst_n,start,
    input wire [511:0] descriptor,
    output wire [1:0] rq_v,
    output wire [27:0] rq_row,
    input wire [1:0] rs_v,
    input wire [1023:0] rs_d,
    output reg wq_v,
    output reg [13:0] wq_row,
    output reg [511:0] wq_d,
    output wire [15:0] wq_mask,
    output wire done,
    output wire fault,
    output wire [15:0] scheduled_cycles
);
    reg [13:0] kb,sb,ob;
    reg pool,run;
    reg [15:0] age;
    wire readslot=start || (run && age<128 && age[1:0]==0);
    wire [13:0] kbase=start?descriptor[32+:14]:kb;
    wire [13:0] sbase=start?descriptor[96+:14]:sb;
    wire [13:0] index=start?14'd0:{9'd0,age[6:2]};
    assign rq_v={2{readslot}};
    assign rq_row={sbase+index,kbase+index};
    wire inputslot=run && age>=LVM && age<LVM+128;
    wire [1:0] chunk=2'(age-LVM);
    wire response_slot=inputslot && chunk==0;
    reg [511:0] kvhold,schold;
    reg held_valid,bridge_fault;
    wire [511:0] kv=response_slot?rs_d[511:0]:kvhold;
    wire [511:0] sc=response_slot?rs_d[1023:512]:schold;
    wire [255:0] packet={sc[chunk*128+:128],kv[chunk*128+:128]};
    wire cv=inputslot && (response_slot?(&rs_v):held_valid);
    wire ov,core_done,core_fault,core_active;
    wire [127:0] od;
    ot_s81_su_cp_h #(.IN_CYCLE(LVM),.MUT(MUT)) u_cp (
        .ck_ctl(ck_cp_ctl),.ck_mem(ck_cp_mem),.ck_lane(ck_cp_lane),
        .rst_n(rst_n),.start(start),.slot_i(descriptor[160]),.pool_i(descriptor[161]),
        .group_i(descriptor[128+:32]),.i_v(cv),.i_d(packet),.o_v(ov),.o_d(od),
        .done(core_done),.fault(core_fault),.active(core_active),.scheduled_cycles(core_sched));
    // One pin register owns complete-row output and completion; final partial
    // data beat arrives before the fixed core retirement boundary.
    reg [1:0] opart;
    reg [4:0] orow;
    reg [511:0] assembly;
    localparam integer RETIRE_DELAY=(WCOMMIT>2)?WCOMMIT-1:1;
    wire [15:0] core_sched;
    assign scheduled_cycles=core_sched+RETIRE_DELAY;
    ot_hdc_delay #(.W(1),.D(RETIRE_DELAY),.RESET(1)) u_retire(clk,rst_n,core_done,done);
    assign fault=bridge_fault|core_fault;
    assign wq_mask=16'hffff;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n)begin
            run<=0;age<=0;held_valid<=0;bridge_fault<=0;
            wq_v<=0;opart<=0;orow<=0;pool<=0;
        end else begin
            wq_v<=0;
            if(start)begin
                if(run || descriptor[64+:32]!=512 || descriptor[32+:32]>16352 ||
                   descriptor[96+:32]>16352 || descriptor[0+:32]>16352 ||
                   descriptor[160+:32]>3) bridge_fault<=1;
                kb<=descriptor[32+:14];sb<=descriptor[96+:14];ob<=descriptor[0+:14];
                pool<=descriptor[161];run<=1;age<=1;opart<=0;orow<=0;held_valid<=0;
            end else if(run)begin
                age<=age+1;
                if(rs_v!={2{response_slot}})bridge_fault<=1;
                if(response_slot)begin kvhold<=rs_d[511:0];schold<=rs_d[1023:512];held_valid<=&rs_v;end
                if(done)run<=0;
            end else if(|rs_v)bridge_fault<=1;
            if(ov)begin
                assembly[opart*128+:128]<=od;
                opart<=opart+1;
                if(opart==3)begin wq_v<=1;wq_row<=ob+orow;wq_d<={od,assembly[383:0]};orow<=orow+1;end
            end
        end
    end
endmodule
