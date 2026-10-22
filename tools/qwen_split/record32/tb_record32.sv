`timescale 1ns/1ps
module tb_record32;
parameter integer MUT=0;
reg ck=0;always #5 ck=~ck;
reg [5:0]rst_rn=0;
integer checks=0,begins=0,auths=0,commits=0,contexts=0,witnesses=0;
reg [0:0] auth_slot=0;
reg [0:0] context_slot=0;
reg [0:0] witness_slot=0;
reg [0:0] rx_v=0;
reg [547:0] rx_record=0;
reg [0:0] execution_active=0;
reg [151:0] program_obs2=0;
reg [68:0] descriptor_obs=0;
reg [1:0] cfg_image_ready=0;
reg [0:0] head_context_v=0;
reg [5:0] head_stage=0;
reg [17:0] head_token=0;
reg [17:0] head_position=0;
wire [0:0] begin_v;
wire [0:0] n_begin_v;
wire [0:0] auth_v;
wire [0:0] n_auth_v;
wire [15:0] begin_epoch;
wire [15:0] n_begin_epoch;
wire [15:0] auth_epoch;
wire [15:0] n_auth_epoch;
wire [10:0] expected_pw;
wire [10:0] n_expected_pw;
wire [3:0] expected_dw;
wire [3:0] n_expected_dw;
wire [63:0] auth_digest;
wire [63:0] n_auth_digest;
wire [0:0] program_ready;
wire [0:0] n_program_ready;
wire [0:0] installed_fusedcap;
wire [0:0] n_installed_fusedcap;
wire [0:0] commit_v;
wire [0:0] n_commit_v;
wire [15:0] program_epoch;
wire [15:0] n_program_epoch;
wire [63:0] program_digest;
wire [63:0] n_program_digest;
wire [0:0] host_epoch_valid;
wire [0:0] n_host_epoch_valid;
wire [15:0] host_epoch;
wire [15:0] n_host_epoch;
wire [58:0] host_tag;
wire [58:0] n_host_tag;
wire [1:0] host_gen;
wire [1:0] n_host_gen;
wire [0:0] tx_v;
wire [0:0] n_tx_v;
wire [0:0] tx_observed_v;
wire [0:0] n_tx_observed_v;
wire [547:0] tx_record;
wire [547:0] n_tx_record;
wire [0:0] fault;
wire [0:0] n_fault;
wire [53:0]rst_leaf;wire[35:0]source_copies;
assign rst_leaf[0]=rst_rn[5];
assign rst_leaf[1]=rst_rn[5];
assign rst_leaf[2]=rst_rn[5];
assign rst_leaf[3]=rst_rn[5];
assign rst_leaf[4]=rst_rn[5];
assign rst_leaf[5]=rst_rn[5];
assign rst_leaf[6]=rst_rn[5];
assign rst_leaf[7]=rst_rn[5];
assign rst_leaf[8]=rst_rn[3];
assign rst_leaf[9]=rst_rn[3];
assign rst_leaf[10]=rst_rn[3];
assign rst_leaf[11]=rst_rn[3];
assign rst_leaf[12]=rst_rn[3];
assign rst_leaf[13]=rst_rn[3];
assign rst_leaf[14]=rst_rn[3];
assign rst_leaf[15]=rst_rn[3];
assign rst_leaf[16]=rst_rn[0];
assign rst_leaf[17]=rst_rn[0];
assign rst_leaf[18]=rst_rn[0];
assign rst_leaf[19]=rst_rn[0];
assign rst_leaf[20]=rst_rn[0];
assign rst_leaf[21]=rst_rn[0];
assign rst_leaf[22]=rst_rn[0];
assign rst_leaf[23]=rst_rn[0];
assign rst_leaf[24]=rst_rn[0];
assign rst_leaf[25]=rst_rn[0];
assign rst_leaf[26]=rst_rn[4];
assign rst_leaf[27]=rst_rn[4];
assign rst_leaf[28]=rst_rn[4];
assign rst_leaf[29]=rst_rn[4];
assign rst_leaf[30]=rst_rn[4];
assign rst_leaf[31]=rst_rn[4];
assign rst_leaf[32]=rst_rn[1];
assign rst_leaf[33]=rst_rn[1];
assign rst_leaf[34]=rst_rn[1];
assign rst_leaf[35]=rst_rn[1];
assign rst_leaf[36]=rst_rn[1];
assign rst_leaf[37]=rst_rn[1];
assign rst_leaf[38]=rst_rn[1];
assign rst_leaf[39]=rst_rn[1];
assign rst_leaf[40]=rst_rn[1];
assign rst_leaf[41]=rst_rn[1];
assign rst_leaf[42]=rst_rn[1];
assign rst_leaf[43]=rst_rn[2];
assign rst_leaf[44]=rst_rn[2];
assign rst_leaf[45]=rst_rn[2];
assign rst_leaf[46]=rst_rn[2];
assign rst_leaf[47]=rst_rn[2];
assign rst_leaf[48]=rst_rn[2];
assign rst_leaf[49]=rst_rn[2];
assign rst_leaf[50]=rst_rn[2];
assign rst_leaf[51]=rst_rn[2];
assign rst_leaf[52]=rst_rn[2];
assign rst_leaf[53]=rst_rn[2];
assign source_copies[0]=execution_active;
assign source_copies[1]=auth_slot;
assign source_copies[2]=witness_slot;
assign source_copies[3]=witness_slot;
assign source_copies[4]=witness_slot;
assign source_copies[5]=witness_slot;
assign source_copies[6]=witness_slot;
assign source_copies[7]=witness_slot;
assign source_copies[8]=witness_slot;
assign source_copies[9]=witness_slot;
assign source_copies[10]=witness_slot;
assign source_copies[11]=witness_slot;
assign source_copies[12]=(MUT==1 ? ~descriptor_obs[68] : descriptor_obs[68]);
assign source_copies[13]=descriptor_obs[68];
assign source_copies[14]=descriptor_obs[68];
assign source_copies[15]=descriptor_obs[68];
assign source_copies[16]=descriptor_obs[68];
assign source_copies[17]=descriptor_obs[68];
assign source_copies[18]=descriptor_obs[68];
assign source_copies[19]=descriptor_obs[68];
assign source_copies[20]=descriptor_obs[68];
assign source_copies[21]=descriptor_obs[68];
assign source_copies[22]=context_slot;
assign source_copies[23]=context_slot;
assign source_copies[24]=auth_slot;
assign source_copies[25]=auth_slot;
assign source_copies[26]=descriptor_obs[68];
assign source_copies[27]=descriptor_obs[68];
assign source_copies[28]=auth_slot;
assign source_copies[29]=descriptor_obs[68];
assign source_copies[30]=program_obs2[75];
assign source_copies[31]=program_obs2[151];
assign source_copies[32]=auth_slot;
assign source_copies[33]=descriptor_obs[68];
assign source_copies[34]=auth_slot;
assign source_copies[35]=descriptor_obs[68];
qfd_sys_face_record_port #(.MU_HEAD(1)) gold(.ck(ck),.rst_rn(rst_rn),.auth_slot(auth_slot),.context_slot(context_slot),.witness_slot(witness_slot),.rx_v(rx_v),.rx_record(rx_record),.execution_active(execution_active),.program_obs2(program_obs2),.descriptor_obs(descriptor_obs),.cfg_image_ready(cfg_image_ready),.head_context_v(head_context_v),.head_stage(head_stage),.head_token(head_token),.head_position(head_position),.begin_v(begin_v),.auth_v(auth_v),.begin_epoch(begin_epoch),.auth_epoch(auth_epoch),.expected_pw(expected_pw),.expected_dw(expected_dw),.auth_digest(auth_digest),.program_ready(program_ready),.installed_fusedcap(installed_fusedcap),.commit_v(commit_v),.program_epoch(program_epoch),.program_digest(program_digest),.host_epoch_valid(host_epoch_valid),.host_epoch(host_epoch),.host_tag(host_tag),.host_gen(host_gen),.tx_v(tx_v),.tx_observed_v(tx_observed_v),.tx_record(tx_record),.fault(fault));
qfd_sys_face_record_port_n32 dut(.ck(ck),.auth_slot(auth_slot),.context_slot(context_slot),.witness_slot(witness_slot),.rx_v(rx_v),.rx_record(rx_record),.execution_active(execution_active),.program_obs2(program_obs2),.descriptor_obs(descriptor_obs),.cfg_image_ready(cfg_image_ready),.head_context_v(head_context_v),.head_stage(head_stage),.head_token(head_token),.head_position(head_position),.begin_v(n_begin_v),.auth_v(n_auth_v),.begin_epoch(n_begin_epoch),.auth_epoch(n_auth_epoch),.expected_pw(n_expected_pw),.expected_dw(n_expected_dw),.auth_digest(n_auth_digest),.program_ready(n_program_ready),.installed_fusedcap(n_installed_fusedcap),.commit_v(n_commit_v),.program_epoch(n_program_epoch),.program_digest(n_program_digest),.host_epoch_valid(n_host_epoch_valid),.host_epoch(n_host_epoch),.host_tag(n_host_tag),.host_gen(n_host_gen),.tx_v(n_tx_v),.tx_observed_v(n_tx_observed_v),.tx_record(n_tx_record),.fault(n_fault),.rst_leaf(rst_leaf),.source_copies(source_copies));
always @(posedge ck)begin #1;if({begin_v,auth_v,begin_epoch,auth_epoch,expected_pw,expected_dw,auth_digest,program_ready,installed_fusedcap,commit_v,program_epoch,program_digest,host_epoch_valid,host_epoch,host_tag,host_gen,tx_v,tx_observed_v,tx_record,fault}!=={n_begin_v,n_auth_v,n_begin_epoch,n_auth_epoch,n_expected_pw,n_expected_dw,n_auth_digest,n_program_ready,n_installed_fusedcap,n_commit_v,n_program_epoch,n_program_digest,n_host_epoch_valid,n_host_epoch,n_host_tag,n_host_gen,n_tx_v,n_tx_observed_v,n_tx_record,n_fault})begin $display("RECORD32_FAIL MUT=%0d t=%0t",MUT,$time);$fatal;end checks=checks+1;begins+=begin_v;auths+=auth_v;commits+=commit_v;contexts+=host_epoch_valid;witnesses+=tx_observed_v;end
task step;begin @(negedge ck);end endtask
function automatic[63:0]pwdata(input integer i);pwdata=(i==1023)?64'h5850463100001006:(64'h1234567800000000 ^ (64'(i)*64'h123456789));endfunction
function automatic[63:0]dwdata(input integer i);dwdata=64'h9876543212345600 ^ 64'(i);endfunction
function automatic[63:0]upd(input[63:0]d,input[63:0]data,input bit desc,input integer addr);upd={d[56:0],d[63:57]}^data^{53'd0,desc,10'(addr)};endfunction
reg[63:0]dig;reg[547:0]rec;integer i,j;
initial begin
repeat(3)step();rst_rn=6'b111111;step();
dig=64'h51484f5354505247;
for(i=0;i<1024;i++)dig=upd(dig,pwdata(i),0,i);
for(i=0;i<8;i++)dig=upd(dig,dwdata(i),1,i);
// BEGIN and AUTH cross the genuine opaque548 receiver, then independently observed writes.
rx_record={5'd0,4'd13,6'd63,16'h37,5'd0,495'd0,4'd8,11'd1024,2'd1};auth_slot=1;rx_v=1;step();auth_slot=0;rx_v=0;repeat(3)step();
rx_record={5'd0,4'd13,6'd63,16'h37,5'd0,446'd0,dig,2'd2};auth_slot=1;rx_v=1;step();auth_slot=0;rx_v=0;repeat(3)step();
cfg_image_ready=3;
for(i=0;i<1024;i++)begin program_obs2={{1'b1,1'b1,10'(i),pwdata(i)},{1'b1,1'b1,10'(i),pwdata(i)}};step();end
program_obs2=0;
for(i=0;i<8;i++)begin descriptor_obs={1'b1,1'b1,3'(i),dwdata(i)};step();end
descriptor_obs=0;repeat(10)step();
if(!program_ready||!installed_fusedcap||program_epoch!=16'h37||program_digest!=dig||fault)begin $display("BAD_PRODUCTION_PROGRAM_READY");$fatal;end
rx_record=0;rx_record[542:539]=12;rx_record[538:533]=63;rx_record[532:517]=16'h9;
rx_record[58:43]=16'h9;rx_record[36:19]=18'd123;rx_record[18:6]=13'd12;rx_record[60:59]=2;rx_record[61]=1;rx_record[77:62]=16'h37;rx_record[141:78]=dig;
context_slot=1;rx_v=1;step();context_slot=0;rx_v=0;repeat(3)step();
head_context_v=1;head_stage=1;head_token=123;head_position=12;step();head_context_v=0;
witness_slot=1;step();witness_slot=0;repeat(3)step();
if(!host_epoch_valid||fault)begin $display("BAD_PRODUCTION_CONTEXT");$fatal;end
// Independent faults, active restart, overlapping slot and reset after retained nonzero state.
for(j=0;j<8;j++)begin
rst_rn=0;repeat(2)step();rst_rn=63;step();
for(i=0;i<100;i++)begin
rx_record={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
auth_slot=1'($urandom);context_slot=1'($urandom);witness_slot=1'($urandom);rx_v=1'($urandom);execution_active=1'($urandom);program_obs2={$urandom,$urandom,$urandom,$urandom,$urandom};descriptor_obs={$urandom,$urandom,$urandom};step();end
end
if(begins<1||auths<1||commits<1||contexts<1||witnesses<1)$fatal;
$display("RECORD32_PASS checks=%0d begins=%0d auth=%0d commit=%0d context=%0d witness=%0d",checks,begins,auths,commits,contexts,witnesses);$finish;
end
endmodule

