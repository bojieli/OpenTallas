`timescale 1ns/1ps
// Four-PC local distribution leaf. Only independent programme descriptors
// select a destination; actual writer ports supply payload and context identity.
// Missing/incorrect words fault, never move the reserved expected slot.
// The full-mask/native constants are a source-pinned property of the actual
// qkd_kv_static_writer_native MUT0 master, checked against its real body in bench.
module qkd_static_writer_group #(
 parameter integer NATIVE_FULL_SECTOR=0, parameter integer MUT=0
)(
 input wire ck,rst_n,input wire [1:0] cfg_stack,input wire [2:0] cfg_group,
 input wire [1151:0] writer_es,input wire [19:0] writer_pc,input wire [1:0] writer_stack,
 input wire [58:0] writer_identity,input wire [1:0] writer_generation,
 input wire [3:0] programme_valid,input wire [19:0] programme_pc,input wire [1:0] programme_stack,
 input wire [58:0] programme_identity,input wire [1:0] programme_generation,input wire [28:0] programme_address,
 output wire [1151:0] pc_es,output wire [317:0] pc_context,
 output reg [3:0] pc_expected_valid,output reg [60:0] pc_expected_identity,
 output reg [28:0] pc_expected_address,output reg [19:0] pc_expected_pc,output reg [1:0] pc_expected_stack,
 output reg fault,output reg idle
);
 initial if(NATIVE_FULL_SECTOR!=1)$fatal(1,"requires proved actual native full-sector writer contract");
 (* keep *) reg rn;reg [1:0] stack_q;reg [2:0] group_q;
 always @(posedge ck)begin rn<=rst_n;stack_q<=cfg_stack;group_q<=cfg_group;end
 // Explicit pin capture before target/identity checks and local output flops.
 wire [1151:0] writer_es_p;
 (* keep *) reg [1147:0] writer_payload_p;
 (* keep *) reg [3:0] writer_valid_p;
 (* keep *) reg [19:0] writer_pc_p;
 (* keep *) reg [1:0] writer_stack_p;
 (* keep *) reg [58:0] writer_identity_p;
 (* keep *) reg [1:0] writer_generation_p;
 (* keep *) reg [3:0] programme_valid_p;
 (* keep *) reg [19:0] programme_pc_p;
 (* keep *) reg [1:0] programme_stack_p;
 (* keep *) reg [58:0] programme_identity_p;
 (* keep *) reg [1:0] programme_generation_p;
 (* keep *) reg [28:0] programme_address_p;
 always @(posedge ck)begin
  writer_pc_p<=writer_pc;
  writer_stack_p<=writer_stack;
  writer_identity_p<=writer_identity;
  writer_generation_p<=writer_generation;
  programme_pc_p<=programme_pc;
  programme_stack_p<=programme_stack;
  programme_identity_p<=programme_identity;
  programme_generation_p<=programme_generation;
  programme_address_p<=programme_address;
 end
 genvar pin_q;
 generate for(pin_q=0;pin_q<4;pin_q=pin_q+1)begin:g_input_pin
  always @(posedge ck)writer_payload_p[287*pin_q+:287]<=writer_es[288*pin_q+1+:287];
  assign writer_es_p[288*pin_q+:288]={writer_payload_p[287*pin_q+:287],writer_valid_p[pin_q]};
 end endgenerate
 always @(posedge ck or negedge rn)
  if(!rn)begin programme_valid_p<=0;writer_valid_p<=0;end
  else begin programme_valid_p<=programme_valid;writer_valid_p<={writer_es[864],writer_es[576],writer_es[288],writer_es[0]};end
 reg [60:0] actual_identity;reg native_slot;
 wire [255:0] full_mask={256{1'b1}} ^ ((MUT==4)?256'd1:256'd0);
 assign pc_context={native_slot,actual_identity,full_mask};
 wire [3:0] actual_v={writer_es_p[864],writer_es_p[576],writer_es_p[288],writer_es_p[0]};
 wire [3:0] selected;
 genvar q;
 generate for(q=0;q<4;q=q+1)begin:g_lane
  wire target=programme_stack_p==stack_q&&programme_pc_p[5*q+:5]=={group_q,2'(q)};
  wire wrong_target=writer_stack_p==stack_q&&writer_pc_p[5*q+:5]=={group_q,2'(q)};
  assign selected[q]=programme_valid_p[q]&&((MUT==2)?wrong_target:target);
  reg valid_q;reg [286:0] payload;
  always @(posedge ck)payload<=writer_es_p[288*((MUT==1)?(3-q):q)+1+:287];
  always @(posedge ck or negedge rn)if(!rn)valid_q<=0;else valid_q<=selected[q]&&writer_es_p[288*q];
  assign pc_es[288*q+:288]={payload,valid_q};
 end endgenerate
 // Observation only: raw pins, captured valids, and output valids must empty.
 always @(posedge ck or negedge rn)
  if(!rn)idle<=0;
  else idle<=!fault && !(|programme_valid) && !(|programme_valid_p) && !(|writer_valid_p) &&
   !(writer_es[0]||writer_es[288]||writer_es[576]||writer_es[864]) &&
   !(|pc_expected_valid) && !(pc_es[0]||pc_es[288]||pc_es[576]||pc_es[864]);
 integer j;
 always @(posedge ck)begin
  actual_identity<=(MUT==3)?{programme_identity_p,programme_generation_p}:{writer_identity_p,writer_generation_p};
  pc_expected_identity<={programme_identity_p,programme_generation_p};
  pc_expected_address<=programme_address_p;pc_expected_pc<=programme_pc_p;pc_expected_stack<=programme_stack_p;
 end
 always @(posedge ck or negedge rn)
  if(!rn)begin pc_expected_valid<=0;native_slot<=0;fault<=0;end
  else begin
   pc_expected_valid<=selected;native_slot<=|selected;
   if(actual_v!=programme_valid_p)fault<=1;
   if((|programme_valid_p)&&programme_valid_p!=4'hf)fault<=1;
   if(|selected)begin
    if({writer_identity_p,writer_generation_p}!={programme_identity_p,programme_generation_p}||writer_stack_p!=programme_stack_p)fault<=1;
    for(j=0;j<4;j=j+1)begin
     if(programme_pc_p[5*j+:5]!={programme_pc_p[4:2],2'(j)})fault<=1;
     if(writer_pc_p[5*j+:5]!=programme_pc_p[5*j+:5])fault<=1;
     if(writer_es_p[288*j]&&(!writer_es_p[288*j+287]||!writer_es_p[288*j+286]||
       {writer_es_p[288*j+257+:19],writer_es_p[288*j+281+:5],writer_es_p[288*j+276+:5]}!=programme_address_p))fault<=1;
    end
   end
  end
endmodule

// Controller-face ownership mux: native normal execution bypasses the legacy
// HOST runtime credit arbiter. native_mode is a real compiled parent signal;
// ownership_valid low is exceptional fault-stop, never a normal ready input.
// HOST response/credit/completion traffic is isolated during native ownership.
// Native completion/drain/fault observations remain directly wired to the root.
module qkd_static_writer_pc_mux(
 input wire ck,rst_n,input wire native_mode,ownership_valid,
 input wire [287:0] native_es,input wire [317:0] native_context,
 input wire native_expected_valid,input wire [60:0] native_expected_identity,
 input wire [28:0] native_expected_address,input wire [4:0] native_expected_pc,input wire [1:0] native_expected_stack,
 input wire [287:0] host_es,
 input wire [260:0] ctrl_er,input wire ctrl_completion_v,ctrl_completion_we,
 output wire [287:0] es,output wire [317:0] es_context,
 output reg es_expected_valid,output reg [60:0] es_expected_identity,
 output reg [28:0] es_expected_address,output reg [4:0] es_expected_pc,output reg [1:0] es_expected_stack,
 output reg [260:0] host_er,output reg host_completion_v,host_completion_we,
 output reg fault,output reg idle
);
 (* keep *) reg rn;reg mode_q,native_q;reg [60:0] identity_q;reg [255:0] mask_q;
 reg [286:0] es_data;reg es_valid;assign es={es_data,es_valid};
 always @(posedge ck)rn<=rst_n;
 assign es_context={native_q,identity_q,mask_q};
 // Includes real return activity; this never gates the fixed forward schedule.
 always @(posedge ck or negedge rn)
  if(!rn)idle<=0;
  else idle<=!fault && ownership_valid && native_mode==mode_q &&
   !native_es[0] && !native_expected_valid && !host_es[0] && !es_valid && !es_expected_valid &&
   !ctrl_er[0] && !ctrl_er[259] && !ctrl_er[260] && !ctrl_completion_v &&
   !host_er[0] && !host_er[259] && !host_er[260] && !host_completion_v;
 always @(posedge ck)begin
  es_data<=native_mode?native_es[287:1]:host_es[287:1];
  identity_q<=native_mode?native_context[316:256]:61'd0;mask_q<=native_mode?native_context[255:0]:256'd0;
  es_expected_identity<=native_expected_identity;es_expected_address<=native_expected_address;
  es_expected_pc<=native_expected_pc;es_expected_stack<=native_expected_stack;
 end
 always @(posedge ck or negedge rn)
  if(!rn)begin es_valid<=0;native_q<=0;es_expected_valid<=0;host_er<=0;host_completion_v<=0;host_completion_we<=0;mode_q<=0;fault<=0;end
  else begin
   mode_q<=native_mode;
   es_valid<=ownership_valid&&(native_mode?native_es[0]:host_es[0]);
   native_q<=ownership_valid&&native_mode&&native_context[317];
   es_expected_valid<=ownership_valid&&native_mode&&native_expected_valid;
   host_er<=(!native_mode&&ownership_valid)?ctrl_er:261'd0;
   host_completion_v<=!native_mode&&ownership_valid&&ctrl_completion_v;
   host_completion_we<=!native_mode&&ownership_valid&&ctrl_completion_we;
   if(ctrl_er[260] || (native_mode&&host_es[0]) || (!native_mode&&(native_es[0]||native_expected_valid)) ||
      (!ownership_valid&&((native_mode!=mode_q)||native_es[0]||host_es[0])) ||
      (native_q&&mask_q!={256{1'b1}}))fault<=1;
  end
endmodule

// Wires-only full-size composition: one independently compensated clock per
// four-PC distribution leaf and one per controller-face mux. No physical relay
// latency or placement is inferred from this source hierarchy.
module qkd_static_writer_distribution #(
 parameter integer NATIVE_FULL_SECTOR=0, parameter integer MUT=0
)(
 input wire [31:0] ck_group,input wire [127:0] ck_pc,input wire rst_n,
 input wire native_mode,ownership_valid,
 input wire [1151:0] writer_es,input wire [19:0] writer_pc,input wire [1:0] writer_stack,
 input wire [58:0] writer_identity,input wire [1:0] writer_generation,
 input wire [3:0] programme_valid,input wire [19:0] programme_pc,input wire [1:0] programme_stack,
 input wire [58:0] programme_identity,input wire [1:0] programme_generation,input wire [28:0] programme_address,
 input wire [36863:0] host_es,input wire [33407:0] ctrl_er,input wire [127:0] ctrl_completion_v,ctrl_completion_we,
 output wire [36863:0] es,output wire [40703:0] es_context,
 output wire [127:0] es_expected_valid,output wire [7807:0] es_expected_identity,
 output wire [3711:0] es_expected_address,output wire [639:0] es_expected_pc,output wire [255:0] es_expected_stack,
 output wire [33407:0] host_er,output wire [127:0] host_completion_v,host_completion_we,
 output wire [31:0] group_fault,output wire [127:0] pc_fault,
 output wire [31:0] idle_group,output wire [127:0] idle_pc
);
 genvar g,q;
 generate for(g=0;g<32;g=g+1)begin:g_group
  wire [1151:0] ge;wire [317:0] gc;wire [3:0] gv;wire [60:0] gi;wire [28:0] ga;wire [19:0] gp;wire [1:0] gs;
  qkd_static_writer_group #(.NATIVE_FULL_SECTOR(NATIVE_FULL_SECTOR),.MUT(MUT))u_group(
   .ck(ck_group[g]),.rst_n(rst_n),.cfg_stack(2'(g/8)),.cfg_group(3'(g%8)),
   .writer_es(writer_es),.writer_pc(writer_pc),.writer_stack(writer_stack),.writer_identity(writer_identity),.writer_generation(writer_generation),
   .programme_valid(programme_valid),.programme_pc(programme_pc),.programme_stack(programme_stack),.programme_identity(programme_identity),
   .programme_generation(programme_generation),.programme_address(programme_address),
   .pc_es(ge),.pc_context(gc),.pc_expected_valid(gv),.pc_expected_identity(gi),.pc_expected_address(ga),.pc_expected_pc(gp),.pc_expected_stack(gs),.fault(group_fault[g]),.idle(idle_group[g]));
  for(q=0;q<4;q=q+1)begin:g_pc
   localparam integer PC=4*g+q;
   qkd_static_writer_pc_mux u_mux(.ck(ck_pc[PC]),.rst_n(rst_n),.native_mode(native_mode),.ownership_valid(ownership_valid),
    .native_es(ge[288*q+:288]),.native_context(gc),.native_expected_valid(gv[q]),.native_expected_identity(gi),.native_expected_address(ga),.native_expected_pc(gp[5*q+:5]),.native_expected_stack(gs),
    .host_es(host_es[288*PC+:288]),.ctrl_er(ctrl_er[261*PC+:261]),.ctrl_completion_v(ctrl_completion_v[PC]),.ctrl_completion_we(ctrl_completion_we[PC]),
    .es(es[288*PC+:288]),.es_context(es_context[318*PC+:318]),.es_expected_valid(es_expected_valid[PC]),.es_expected_identity(es_expected_identity[61*PC+:61]),
    .es_expected_address(es_expected_address[29*PC+:29]),.es_expected_pc(es_expected_pc[5*PC+:5]),.es_expected_stack(es_expected_stack[2*PC+:2]),
    .host_er(host_er[261*PC+:261]),.host_completion_v(host_completion_v[PC]),.host_completion_we(host_completion_we[PC]),.fault(pc_fault[PC]),.idle(idle_pc[PC]));
  end
 end endgenerate
endmodule
