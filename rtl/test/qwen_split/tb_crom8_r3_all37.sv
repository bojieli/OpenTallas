`timescale 1ns/1ps
// Expected-only checkpoint vectors observe actual R3/SRAM/CROM/return3.
// Exactly24independent declared clock roots driven in phase for this component.
// Fixed control contexts,400edgefill slots,E5 reads; no ready waits or reset
// between36layers+head across position cohorts0,8191,1.
module tb_crom8_r3_all37;
parameter integer NMAX = 15420;
parameter integer LEAD = 400;
parameter integer MUT = 0;
reg clk = 0, rst_n = 0; always #1 clk = ~clk;
reg[17:0] tpos=0;
reg [63:0] re = 0; reg [1535:0] addr = 0; reg [5:0] stage = 0; reg tok_start = 0;
wire [4095:0] q; wire [7:0] fault; wire [15:0] code; wire [7:0] resident; wire [47:0] resident_stage;
// ABI variant (join960): the same recorded reads enter through the SU ca0..7 packing
// {stage[5:0], crom_addr[191:0], crom_re[7:0]} of qfd_sp_su64_sfu_glue_entries and return on cq0..7 of the
// join's actual provider qfd_native_crom8_tp8 (separate crom/cbuf clock entries driven in phase here).
wire [205:0] ca [0:7]; wire [511:0] cq [0:7];
genvar g;
generate for (g = 0; g < 8; g = g + 1) begin : g_pack
    assign ca[g] = {stage, addr[192*g +: 192], re[8*g +: 8]};
    assign q[512*g +: 512] = cq[g];
end endgenerate
wire any_fault;wire [9:0] cbr[0:7];wire [143:0] resident_tpos;wire [7:0] group_fault;
qfd_native_crom8_r3_tp8 #(.CROM_MUT(MUT==1),.RETURN_MUT(MUT==2)) u_dut (.crom_ck({8{clk}}), .cbuf_ck({8{clk}}), .rst_n(rst_n),
    .return_ck({8{clk}}),
    .cbc0({tpos,tok_start,stage}), .cbc1({tpos,tok_start,stage}), .cbc2({tpos,tok_start,stage}), .cbc3({tpos,tok_start,stage}), .cbc4({tpos,tok_start,stage}), .cbc5({tpos,tok_start,stage}), .cbc6({tpos,tok_start,stage}), .cbc7({tpos,tok_start,stage}),
    .cbr0(cbr[0]), .cbr1(cbr[1]), .cbr2(cbr[2]), .cbr3(cbr[3]), .cbr4(cbr[4]), .cbr5(cbr[5]), .cbr6(cbr[6]), .cbr7(cbr[7]),
    .constants_resident_tpos(resident_tpos),.group_fault(group_fault),
    .ca0(ca[0]), .ca1(ca[1]), .ca2(ca[2]), .ca3(ca[3]), .ca4(ca[4]), .ca5(ca[5]), .ca6(ca[6]), .ca7(ca[7]),
    .cq0(cq[0]), .cq1(cq[1]), .cq2(cq[2]), .cq3(cq[3]), .cq4(cq[4]), .cq5(cq[5]), .cq6(cq[6]), .cq7(cq[7]),
    .constants_resident(resident), .constants_resident_stage(resident_stage), .crom_fault_code(code), .fault(any_fault));
assign fault = {7'd0, any_fault};
reg[63:0]hdr[0:NMAX-1],msk[0:NMAX-1],ex[0:64*NMAX-1];
reg[23:0]ad[0:64*NMAX-1];reg[63:0]ctx[0:110];
reg[1023:0]vdir;integer n,nc,i=0,l,h=0,ci=0,issued=0,errors=0,rd_faults=0,checked=0,starts=0;
longint cyc=0;longint due[0:NMAX-1];
initial begin
if(!$value$plusargs("V=%s",vdir)||!$value$plusargs("N=%d",n)||!$value$plusargs("NC=%d",nc)||n!=15420||nc!=111)$fatal(1,"invalid vector counts");
$readmemh({vdir,"/rd_hdr.hex"},hdr);$readmemh({vdir,"/rd_mask.hex"},msk);
$readmemh({vdir,"/rd_addr.hex"},ad);$readmemh({vdir,"/rd_exp.hex"},ex);$readmemh({vdir,"/contexts.hex"},ctx);
repeat(4)@(negedge clk);rst_n=1;repeat(12)@(negedge clk);
while(i<n||h<issued||ci<nc)begin
while(h<issued&&due[h]==cyc)begin
for(l=0;l<64;l=l+1)if(msk[h][l]&&q[64*l+:64]!==ex[64*h+l])begin
errors=errors+1;if(errors<12)$display("MISMATCH read=%0d stage=%0d lane=%0d addr=%0d got=%h expected=%h",h,hdr[h][5:0],l,ad[64*h+l],q[64*l+:64],ex[64*h+l]);
end
checked=checked+1;h=h+1;
end
tok_start=0;
if(ci<nc&&ctx[ci][63:32]==cyc)begin
stage=ctx[ci][5:0];tok_start=ctx[ci][6];tpos=ctx[ci][24:7];starts=starts+int'(tok_start);
$display("CONTEXT n=%0d cycle=%0d stage=%0d tpos=%0d tok_start=%0b",ci,cyc,stage,tpos,tok_start);ci=ci+1;
end
re=0;
if(i<n&&hdr[i][63:8]==cyc)begin
if(stage!==hdr[i][5:0])$fatal(1,"independent context/read stage mismatch");
if(!(resident==8'hff&&resident_stage=={8{stage}}&&resident_tpos=={8{tpos}}))begin
rd_faults=rd_faults+1;if(rd_faults<12)$display("RESIDENCY read=%0d stage=%0d tpos=%0d rdy=%h resident_stage=%h resident_tpos=%h",i,stage,tpos,resident,resident_stage,resident_tpos);
end
for(integer gi=0;gi<8;gi=gi+1)if(cbr[gi]!=={code[2*gi+:2],group_fault[gi],resident_stage[6*gi+:6],resident[gi]})begin errors=errors+1;$display("CBR packing mismatch group=%0d",gi);end
re=msk[i];for(l=0;l<64;l=l+1)addr[24*l+:24]=ad[64*i+l];
due[i]=cyc+5;issued=issued+1;i=i+1;
end else if(i<n&&hdr[i][63:8]<cyc)$fatal(1,"read schedule late");
@(negedge clk);cyc=cyc+1;
end
if(any_fault)begin errors=errors+1;$display("FAULT codes=%h",code);end
if(checked!=n||ci!=111||starts!=3)$fatal(1,"incomplete calendar reads=%0d contexts=%0d starts=%0d",checked,ci,starts);
if(errors||rd_faults)$display("FAIL crom_r3_all37 mut=%0d errors=%0d residency=%0d reads=%0d contexts=%0d tok_starts=%0d",MUT,errors,rd_faults,checked,ci,starts);
else $display("PASS crom_r3_all37 reads=%0d lanes=%0d contexts=%0d token_cohorts=%0d one_reset E5 R3_CROM_return3",checked,checked*64,ci,starts);
$finish;
end
endmodule
