module tb;
reg ck=0; always #5 ck=~ck;
reg  rst_n;
reg [4*288-1:0] es;
reg [19:0] dest_pc;
reg [1:0] dest_stack;
reg [58:0] identity;
reg [1:0] generation;
reg [3:0] expected_valid;
reg [19:0] expected_pc;
reg [1:0] expected_stack;
reg [58:0] expected_identity;
reg [1:0] expected_generation;
reg [28:0] expected_address;
reg  emb_start;
reg [17:0] emb_token;
reg [15:0] emb_epoch;
reg  cfg_we;
reg [7:0] cfg_addr;
reg [63:0] cfg_data;
reg [292:0] bw;
reg[5:0] caught=0;
for(genvar n=0;n<6;n++)begin:g
wire [783:0] g_h,p_h,m_h;
wire [783:0] g_h_e,p_h_e,m_h_e;
wire  g_fault,p_fault,m_fault;
qkd_kv_es_fan_root2_b_nc32 #(.MUT(n%3),.RCOPIES(n<3?1:4),.PH1C(n%2),.S32(1)) u_g (.ck(ck), .rst_n(rst_n), .es(es), .dest_pc(dest_pc), .dest_stack(dest_stack), .identity(identity), .generation(generation), .expected_valid(expected_valid), .expected_pc(expected_pc), .expected_stack(expected_stack), .expected_identity(expected_identity), .expected_generation(expected_generation), .expected_address(expected_address), .emb_start(emb_start), .emb_token(emb_token), .emb_epoch(emb_epoch), .cfg_we(cfg_we), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .bw(bw), .h(g_h), .h_e(g_h_e), .fault(g_fault));
qkd_kv_es_fan_root2_b_nc32_bpin #(.MUT(n%3),.RCOPIES(n<3?1:4),.PH1C(n%2),.S32(1)) u_p (.ck(ck), .rst_n(rst_n), .es(es), .dest_pc(dest_pc), .dest_stack(dest_stack), .identity(identity), .generation(generation), .expected_valid(expected_valid), .expected_pc(expected_pc), .expected_stack(expected_stack), .expected_identity(expected_identity), .expected_generation(expected_generation), .expected_address(expected_address), .emb_start(emb_start), .emb_token(emb_token), .emb_epoch(emb_epoch), .cfg_we(cfg_we), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .bw(bw), .h(p_h), .h_e(p_h_e), .fault(p_fault));
qkd_kv_es_fan_root2_b_nc32_bpin_mut #(.MUT(n%3),.RCOPIES(n<3?1:4),.PH1C(n%2),.S32(1)) u_m (.ck(ck), .rst_n(rst_n), .es(es), .dest_pc(dest_pc), .dest_stack(dest_stack), .identity(identity), .generation(generation), .expected_valid(expected_valid), .expected_pc(expected_pc), .expected_stack(expected_stack), .expected_identity(expected_identity), .expected_generation(expected_generation), .expected_address(expected_address), .emb_start(emb_start), .emb_token(emb_token), .emb_epoch(emb_epoch), .cfg_we(cfg_we), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .bw(bw), .h(m_h), .h_e(m_h_e), .fault(m_fault));
always @(negedge ck)if(rst_n)begin
assert({g_h,g_h_e,g_fault}=={p_h,p_h_e,p_fault})else $fatal(1,"BW_PIN_LOCKSTEP n=%0d",n);
if({g_h,g_h_e,g_fault}!={m_h,m_h_e,m_fault})caught[n]=1;
end
end
initial begin
rst_n=0;
es=0;
dest_pc=0;
dest_stack=0;
identity=0;
generation=0;
expected_valid=0;
expected_pc=0;
expected_stack=0;
expected_identity=0;
expected_generation=0;
expected_address=0;
emb_start=0;
emb_token=0;
emb_epoch=0;
cfg_we=0;
cfg_addr=0;
cfg_data=0;
bw=0;
repeat(4)@(negedge ck);rst_n=1;
for(int cycle=0;cycle<4096;cycle++)begin
for(int k=0;k<1152;k++) es[k]=1'($urandom);
dest_pc=20'($urandom);
dest_stack=2'($urandom);
for(int k=0;k<59;k++) identity[k]=1'($urandom);
generation=2'($urandom);
expected_valid=4'($urandom);
expected_pc=20'($urandom);
expected_stack=2'($urandom);
for(int k=0;k<59;k++) expected_identity[k]=1'($urandom);
expected_generation=2'($urandom);
expected_address=29'($urandom);
emb_start=1'($urandom);
emb_token=18'($urandom);
emb_epoch=16'($urandom);
cfg_we=1'($urandom);
cfg_addr=8'($urandom);
for(int k=0;k<64;k++) cfg_data[k]=1'($urandom);
for(int k=0;k<293;k++) bw[k]=1'($urandom);
if(cycle%16<8)begin expected_valid=0;es[0]=0;es[288]=0;es[576]=0;es[864]=0;bw[0]=cycle[0];end
else begin expected_valid=4'b0101;es[288]=1;bw[0]=1;end
@(negedge ck);
end
assert((caught&6'b101101)==6'b101101)else $fatal(1,"BW_PIN_MUTANT %b",caught);
$display("BW_PIN_LOCKSTEP PASS profiles6 cycles4096 outputs784x2+fault mutants4/4 cycles_added0");$finish;end endmodule
