// Default-off actual coded owner collector, not a host ready/grant table.
module ot_gpu_qwen_native_aperture_collector #(parameter integer ENABLE=0,ACTOR_INDEX=0)(
 input wire clk,por_n,warm_reset,
 input wire issuer_held_valid,issuer_held_fault,
 input wire [238:0] issuer_held_tuple,input wire [54:0] issuer_held_owner,
 // MUST be independent source-descriptor hardware, never cmd_* authority ties.
 input wire profile_valid,input wire [238:0] profile_tuple,
 input wire [10:0] profile_PC,input wire [63:0] profile_sequence,
 input wire [255:0] profile_shape,input wire [3:0] profile_present,profile_double,
 input wire profile_result_double,
 // OWNED source-RPC producer load, not an alias of cmd_*.
 input wire cursor_load_valid,output wire cursor_load_ready,
 input wire [238:0] cursor_load_tuple,input wire [54:0] cursor_load_owner,
 input wire [63:0] cursor_load_sequence,
 input wire [7:0] cursor_load_descriptor,input wire [2:0] cursor_load_operands,
 input wire [7:0] cursor_load_types,input wire [3:0] cursor_load_signed_i8,
 input wire [31:0] cursor_load_counts,input wire [3:0] cursor_load_vector_mask,
 input wire [3:0] cursor_load_template,input wire [5:0] cursor_load_step,
 input wire [1:0] cursor_load_substep,input wire [3:0] cursor_load_scalars,input wire [7:0] cursor_load_tail,
 output wire source_cursor_valid,source_cursor_advance_valid,input wire source_cursor_advance_ready,
 output wire [7:0] source_descriptor,source_types,source_tail,
 output wire [2:0] source_operands,output wire [3:0] source_signed_i8_mask,source_vector_mask,source_template,source_scalars,
 output wire [31:0] source_counts,output wire [5:0] source_ordered_step,output wire [1:0] source_substep,
 input wire frame_accept,input wire [238:0] frame_tuple,input wire [54:0] frame_owner,
 input wire terminal_accept,input wire [238:0] terminal_tuple,input wire [54:0] terminal_owner,input wire [63:0] terminal_sequence,
 input wire begin_valid,output wire begin_ready,
 input wire capture_valid,output wire capture_ready,
 input wire [2:0] capture_aperture,input wire [5:0] capture_bank,
 input wire [17:0] capture_slots,input wire [10:0] capture_version,
 input wire capture_workspace,
 // Selected ACTUAL source bank Q seat, not caller identity echoes.
 input wire [63:0] query_valid,query_retained,query_write,query_workspace,bank_fault,
 input wire [64*239-1:0] query_tuple,
 input wire [64*9-1:0] query_slot,input wire [64*46-1:0] query_owner,
 input wire [64*11-1:0] query_version,
 input wire [64*9-1:0] query_first,input wire [64*10-1:0] query_end,
 // CURRENT coded source leases: these survive Q seat consumption.
 output wire [5*239-1:0] lease_tuple,output wire [5*11-1:0] lease_version,
 output wire [5*18-1:0] lease_slots,output wire [5*46-1:0] lease_owner,
 output wire [29:0] lease_bank,output wire [4:0] lease_workspace,lease_write,lease_double,
 // Real CURRENT coded-bank B scope. Claim and source-retire paths cannot
 // mutate row identity while B.live; query captured row/version/bounds first.
 input wire [63:0] bank_scope_valid,bank_scope_writable,bank_scope_workspace,
 input wire [64*239-1:0] bank_scope_tuple,input wire [64*55-1:0] bank_scope_owner,
 // Actual accepted W4 both-mirror ACK tap. Identity must match captured lease.
 input wire [63:0] ack_accept,input wire [64*9-1:0] ack_slot,
 input wire [64*46-1:0] ack_owner,
 input wire visibility_valid,input wire [238:0] visibility_tuple,
 input wire [54:0] visibility_owner,input wire [63:0] visibility_sequence,
 input wire reverse_accept,input wire [238:0] reverse_tuple,
 input wire [54:0] reverse_owner,input wire [63:0] reverse_sequence,
 input wire controller_idle,selected_routes_drained,
 // Actual controller's protected-current counters; slot alone cannot name bank.
 input wire [1:0] read_operand,input wire read_page,write_page,
 output wire read_route_valid,write_route_valid,
 output wire [5:0] read_bank,write_bank,
 output wire [8:0] read_slot,write_slot,output wire [45:0] read_owner,write_owner,
 output wire authority_valid,output wire [238:0] authority_tuple,
 output wire [54:0] authority_owner,output wire [10:0] authority_PC,
 output wire [63:0] authority_sequence,output wire [255:0] authority_shape_sha,
 output wire [71:0] authority_source_slots,output wire [183:0] authority_source_owners,
 output wire [17:0] authority_result_slots,output wire [45:0] authority_result_owner,
 output wire [23:0] authority_source_banks,output wire [5:0] authority_result_bank,
 output wire [3:0] source_owner_held,output wire result_owner_held,output wire output_visible,
 output wire fault,output wire context_live
);
  localparam integer C_LIVE=0;
 localparam integer C_FAULT=1;
 localparam integer C_QUARANTINE=2;
 localparam integer C_TUPLE=3;
 localparam integer C_OWNER=242;
 localparam integer C_PC=297;
 localparam integer C_SEQUENCE=308;
 localparam integer C_SHAPE=372;
 localparam integer C_PRESENT=628;
 localparam integer C_DOUBLE=632;
 localparam integer C_RESULT_DOUBLE=636;
 localparam integer C_CAPTURED=637;
 localparam integer C_SLOTS=642;
 localparam integer C_OWNERS=732;
 localparam integer C_BANKS=962;
 localparam integer C_VERSIONS=992;
 localparam integer C_WORKSPACE=1047;
 localparam integer C_STAGE_ACK=1052;
 localparam integer C_RESULT_ACK=1060;
 localparam integer C_VISIBLE=1062;
 localparam integer C_CURSOR_LIVE=1063;
 localparam integer C_CURSOR_PRIOR=1064;
 localparam integer C_TERMINAL=1065;
 localparam integer C_ADVANCE_PENDING=1066;
 localparam integer C_SOURCE_DESCRIPTOR=1067;
 localparam integer C_SOURCE_OPERANDS=1075;
 localparam integer C_SOURCE_TYPES=1078;
 localparam integer C_SOURCE_SIGNED_I8=1086;
 localparam integer C_SOURCE_COUNTS=1090;
 localparam integer C_SOURCE_VECTOR_MASK=1122;
 localparam integer C_SOURCE_TEMPLATE=1126;
 localparam integer C_SOURCE_STEP=1130;
 localparam integer C_SOURCE_SUBSTEP=1136;
 localparam integer C_SOURCE_SCALARS=1138;
 localparam integer C_SOURCE_TAIL=1142;
 wire [1150-1:0] c;reg [1150-1:0] next_c;
 wire clean,bad,repairing;
 wire external_scope=issuer_held_valid&&!issuer_held_fault&&issuer_held_tuple==c[C_TUPLE +:239]&&issuer_held_owner==c[C_OWNER +:55];
 wire active=ENABLE!=0&&por_n&&!warm_reset&&clean&&!bad&&!c[C_FAULT]&&!c[C_QUARANTINE]&&!issuer_held_fault;
 ot_gpu_qwen_banked_manifest_source_record #(.BITS(1150),.INDEX(ACTOR_INDEX),.BASE(700),.KIND(4)) u_record(
  .clk(clk),.por_n(por_n),.write_enable(ENABLE!=0&&clean&&!bad),.next_data(next_c),
  .data(c),.clean(clean),.bad(bad),.repairing(repairing));
 assign fault=ENABLE!=0&&(bad||c[C_FAULT]||c[C_QUARANTINE]||issuer_held_fault);
 assign context_live=clean&&c[C_LIVE];
 assign source_cursor_valid=active&&external_scope&&c[C_CURSOR_LIVE]&&!c[C_ADVANCE_PENDING];
 assign source_cursor_advance_valid=active&&external_scope&&c[C_LIVE]&&c[C_TERMINAL]&&c[C_ADVANCE_PENDING]&&controller_idle&&selected_routes_drained;
 assign source_descriptor=c[C_SOURCE_DESCRIPTOR +:8];assign source_operands=c[C_SOURCE_OPERANDS +:3];
 assign source_types=c[C_SOURCE_TYPES +:8];assign source_signed_i8_mask=c[C_SOURCE_SIGNED_I8 +:4];
 assign source_counts=c[C_SOURCE_COUNTS +:32];assign source_vector_mask=c[C_SOURCE_VECTOR_MASK +:4];
 assign source_template=c[C_SOURCE_TEMPLATE +:4];assign source_ordered_step=c[C_SOURCE_STEP +:6];
 assign source_substep=c[C_SOURCE_SUBSTEP +:2];assign source_scalars=c[C_SOURCE_SCALARS +:4];assign source_tail=c[C_SOURCE_TAIL +:8];
 // Source-key structural checks are independent of cmd_*; the immutable
 // profile additionally checks the literal descriptor and logical output.
 wire [3:0] load_present=(4'h1<<cursor_load_operands)-1'b1;
 wire [3:0] load_lane_legal;
 genvar key_lane;generate for(key_lane=0;key_lane<4;key_lane=key_lane+1)begin:key_checks
  wire [7:0] count=cursor_load_counts[key_lane*8 +:8];
  assign load_lane_legal[key_lane]=load_present[key_lane]?
   (count>=1&&count<=128&&cursor_load_scalars[key_lane]==(count==1)&&
    cursor_load_tail[key_lane*2 +:2]==count[1:0]&&
    (!cursor_load_signed_i8[key_lane]||cursor_load_types[key_lane*2 +:2]==3)):
   (count==0&&!cursor_load_vector_mask[key_lane]&&!cursor_load_scalars[key_lane]&&
    !cursor_load_signed_i8[key_lane]&&cursor_load_types[key_lane*2 +:2]==0&&cursor_load_tail[key_lane*2 +:2]==0);
 end endgenerate
 assign cursor_load_ready=active&&!c[C_LIVE]&&!c[C_CURSOR_LIVE]&&!c[C_ADVANCE_PENDING]&&controller_idle&&selected_routes_drained&&
  issuer_held_valid&&cursor_load_tuple==issuer_held_tuple&&cursor_load_owner==issuer_held_owner&&
  cursor_load_tuple[174:164]<1737&&cursor_load_tuple[35:30]==ACTOR_INDEX&&cursor_load_operands>=1&&cursor_load_operands<=4&&
  cursor_load_descriptor<116&&cursor_load_template<13&&cursor_load_substep<3&&(&load_lane_legal)&&!frame_accept&&
  (!c[C_CURSOR_PRIOR]||(cursor_load_tuple==c[C_TUPLE +:239]&&cursor_load_owner==c[C_OWNER +:55]&&cursor_load_sequence!=c[C_SEQUENCE +:64]));
 assign begin_ready=active&&source_cursor_valid&&!c[C_LIVE]&&controller_idle&&selected_routes_drained&&profile_valid&&issuer_held_valid&&
  profile_tuple==c[C_TUPLE +:239]&&profile_sequence==c[C_SEQUENCE +:64]&&
  profile_present==((4'h1<<c[C_SOURCE_OPERANDS +:3])-1'b1)&&profile_tuple==issuer_held_tuple&&profile_PC==profile_tuple[174:164]&&profile_PC<1737&&
  profile_tuple[35:30]==ACTOR_INDEX&&(profile_double&~profile_present)==0;
 wire [2:0] a=capture_aperture;
 wire wanted=(a<4&&c[C_PRESENT+a])||a==4;
 wire double_page=a==4?c[C_RESULT_DOUBLE]:(a<4?c[C_DOUBLE+a]:1'b0);
 wire pair_bounds=capture_slots[8:0]>=query_first[capture_bank*9 +:9]&&
  {1'b0,capture_slots[8:0]}<query_end[capture_bank*10 +:10]&&
  capture_slots[17:9]>=query_first[capture_bank*9 +:9]&&
  {1'b0,capture_slots[17:9]}<query_end[capture_bank*10 +:10];
 wire qmatch=a<5&&query_valid[capture_bank]&&query_retained[capture_bank]&&!bank_fault[capture_bank]&&
  query_tuple[capture_bank*239 +:239]==c[C_TUPLE +:239]&&query_slot[capture_bank*9 +:9]==capture_slots[8:0]&&
  query_version[capture_bank*11 +:11]==capture_version&&query_workspace[capture_bank]==capture_workspace&&
  (a==4?query_write[capture_bank]:(capture_workspace?query_write[capture_bank]:!query_write[capture_bank]));
 assign capture_ready=active&&c[C_LIVE]&&external_scope&&wanted&&!c[C_CAPTURED+a]&&qmatch&&pair_bounds&&
  (double_page?capture_slots[17:9]!=capture_slots[8:0]:capture_slots[17:9]==capture_slots[8:0]);
 assign authority_tuple=c[C_TUPLE +:239];assign authority_owner=c[C_OWNER +:55];
 assign authority_PC=c[C_PC +:11];assign authority_sequence=c[C_SEQUENCE +:64];assign authority_shape_sha=c[C_SHAPE +:256];
 assign authority_source_slots=c[C_SLOTS +:72];assign authority_source_owners=c[C_OWNERS +:184];
 assign authority_result_slots=c[C_SLOTS+72 +:18];assign authority_result_owner=c[C_OWNERS+184 +:46];
 assign authority_source_banks=c[C_BANKS +:24];assign authority_result_bank=c[C_BANKS+24 +:6];
 assign lease_slots=c[C_SLOTS +:90];assign lease_owner=c[C_OWNERS +:230];assign lease_bank=c[C_BANKS +:30];
 assign lease_version=c[C_VERSIONS +:55];assign lease_workspace=c[C_WORKSPACE +:5];
 assign lease_write={1'b1,c[C_WORKSPACE +:4]};assign lease_double={c[C_RESULT_DOUBLE],c[C_DOUBLE +:4]};
 wire [4:0] lease_held;
 genvar g;generate for(g=0;g<5;g=g+1)begin:views
  wire [5:0] selected_bank=c[C_BANKS+g*6 +:6];
  wire selected_scope=bank_scope_valid[selected_bank]&&!bank_fault[selected_bank]&&
   bank_scope_tuple[selected_bank*239 +:239]==c[C_TUPLE +:239]&&
   bank_scope_owner[selected_bank*55 +:55]==c[C_OWNER +:55];
  assign lease_held[g]=selected_scope&&(c[C_WORKSPACE+g]?bank_scope_workspace[selected_bank]:
   (g==4?bank_scope_writable[selected_bank]:1'b1));
  assign lease_tuple[g*239 +:239]=c[C_TUPLE +:239];
  if(g<4)begin
   wire staged=!c[C_WORKSPACE+g]||(c[C_STAGE_ACK+2*g]&&(!c[C_DOUBLE+g]||c[C_STAGE_ACK+2*g+1]));
   assign source_owner_held[g]=active&&external_scope&&c[C_LIVE]&&c[C_CAPTURED+g]&&lease_held[g]&&staged;
  end
 end endgenerate
 assign result_owner_held=active&&external_scope&&c[C_LIVE]&&c[C_CAPTURED+4]&&lease_held[4];
 wire complete=((source_owner_held&c[C_PRESENT +:4])==c[C_PRESENT +:4])&&result_owner_held;
 assign authority_valid=active&&external_scope&&c[C_LIVE]&&complete;
 assign output_visible=authority_valid&&c[C_VISIBLE]&&c[C_RESULT_ACK]&&(!c[C_RESULT_DOUBLE]||c[C_RESULT_ACK+1]);
 assign read_bank=c[C_BANKS+read_operand*6 +:6];assign write_bank=c[C_BANKS+24 +:6];
 assign read_slot=c[C_SLOTS+read_operand*18+read_page*9 +:9];assign write_slot=c[C_SLOTS+72+write_page*9 +:9];
 assign read_owner=c[C_OWNERS+read_operand*46 +:46];assign write_owner=c[C_OWNERS+184 +:46];
 assign read_route_valid=authority_valid&&source_owner_held[read_operand]&&c[C_PRESENT+read_operand]&&(!read_page||c[C_DOUBLE+read_operand]);
 assign write_route_valid=authority_valid&&result_owner_held&&(!write_page||c[C_RESULT_DOUBLE]);
 integer i,j;reg conflict;reg [8:0] s0,s1,t0,t1;reg [5:0] ib;
 always @*begin
  next_c=c;conflict=0;s0=capture_slots[8:0];s1=capture_slots[17:9];t0=0;t1=0;ib=0;
  // Distinct inputs may intentionally alias a READ-only source. Writable
  // workspace/result apertures never overlap any other captured aperture.
  for(i=0;i<5;i=i+1)if(c[C_CAPTURED+i]&&c[C_BANKS+i*6 +:6]==capture_bank)begin
   t0=c[C_SLOTS+i*18 +:9];t1=c[C_SLOTS+i*18+9 +:9];
   if((a==4||i==4||capture_workspace||c[C_WORKSPACE+i])&&
      (s0==t0||s0==t1||s1==t0||s1==t1))conflict=1;
  end
  if(clean&&!bad&&ENABLE!=0)begin
   if(warm_reset||issuer_held_fault)next_c[C_QUARANTINE]=1;
   if(c[C_LIVE]&&!external_scope)next_c[C_FAULT]=1;
   if(cursor_load_valid&&cursor_load_ready)begin
    next_c=0;next_c[C_CURSOR_LIVE]=1;next_c[C_CURSOR_PRIOR]=1;
    next_c[C_TUPLE +:239]=cursor_load_tuple;next_c[C_OWNER +:55]=cursor_load_owner;next_c[C_PC +:11]=cursor_load_tuple[174:164];next_c[C_SEQUENCE +:64]=cursor_load_sequence;
    next_c[C_SOURCE_DESCRIPTOR +:8]=cursor_load_descriptor;next_c[C_SOURCE_OPERANDS +:3]=cursor_load_operands;
    next_c[C_SOURCE_TYPES +:8]=cursor_load_types;next_c[C_SOURCE_SIGNED_I8 +:4]=cursor_load_signed_i8;
    next_c[C_SOURCE_COUNTS +:32]=cursor_load_counts;next_c[C_SOURCE_VECTOR_MASK +:4]=cursor_load_vector_mask;
    next_c[C_SOURCE_TEMPLATE +:4]=cursor_load_template;next_c[C_SOURCE_STEP +:6]=cursor_load_step;next_c[C_SOURCE_SUBSTEP +:2]=cursor_load_substep;
    next_c[C_SOURCE_SCALARS +:4]=cursor_load_scalars;next_c[C_SOURCE_TAIL +:8]=cursor_load_tail;
   end
   if(begin_valid&&begin_ready)begin
    next_c[C_LIVE]=1;next_c[C_TUPLE +:239]=profile_tuple;next_c[C_OWNER +:55]=issuer_held_owner;
    next_c[C_PC +:11]=profile_PC;next_c[C_SEQUENCE +:64]=profile_sequence;next_c[C_SHAPE +:256]=profile_shape;
    next_c[C_PRESENT +:4]=profile_present;next_c[C_DOUBLE +:4]=profile_double;next_c[C_RESULT_DOUBLE]=profile_result_double;
   end
   if(capture_valid&&active&&c[C_LIVE]&&
    (!wanted||(a<5&&c[C_CAPTURED+a])||(query_valid[capture_bank]&&(!qmatch||!pair_bounds||conflict))))next_c[C_FAULT]=1;
   if(capture_valid&&capture_ready)begin
    if(conflict)next_c[C_FAULT]=1;
    else begin
     next_c[C_CAPTURED+a]=1;next_c[C_SLOTS+a*18 +:18]=capture_slots;
     next_c[C_OWNERS+a*46 +:46]=query_owner[capture_bank*46 +:46];
     next_c[C_BANKS+a*6 +:6]=capture_bank;next_c[C_VERSIONS+a*11 +:11]=capture_version;next_c[C_WORKSPACE+a]=capture_workspace;
    end
   end
   if(active&&c[C_LIVE]&&external_scope)begin
    for(i=0;i<5;i=i+1)if(c[C_CAPTURED+i])begin
     ib=c[C_BANKS+i*6 +:6];
     if(bank_fault[ib])next_c[C_FAULT]=1;
     if(ack_accept[ib]&&ack_owner[ib*46 +:46]==c[C_OWNERS+i*46 +:46])begin
      for(j=0;j<2;j=j+1)if((j==0||(i==4?c[C_RESULT_DOUBLE]:c[C_DOUBLE+i]))&&
       ack_slot[ib*9 +:9]==c[C_SLOTS+i*18+j*9 +:9])begin
       if(i==4)next_c[C_RESULT_ACK+j]=1;
       else if(c[C_WORKSPACE+i])next_c[C_STAGE_ACK+i*2+j]=1;
      end
     end
    end
    if(visibility_valid&&visibility_tuple==c[C_TUPLE +:239]&&visibility_owner==c[C_OWNER +:55]&&visibility_sequence==c[C_SEQUENCE +:64])next_c[C_VISIBLE]=1;
    if(terminal_accept)begin
     if(terminal_tuple==c[C_TUPLE +:239]&&terminal_owner==c[C_OWNER +:55]&&terminal_sequence==c[C_SEQUENCE +:64]&&output_visible&&!c[C_TERMINAL])next_c[C_TERMINAL]=1;
     else next_c[C_FAULT]=1;
    end
    if(reverse_accept)begin
     if(reverse_tuple==c[C_TUPLE +:239]&&reverse_owner==c[C_OWNER +:55]&&reverse_sequence==c[C_SEQUENCE +:64]&&
      output_visible&&c[C_TERMINAL]&&!c[C_ADVANCE_PENDING]&&selected_routes_drained)next_c[C_ADVANCE_PENDING]=1;
     else next_c[C_FAULT]=1;
    end
   end
  end
  if(active&&source_cursor_advance_valid&&source_cursor_advance_ready&&controller_idle&&selected_routes_drained)begin
   next_c[C_LIVE]=0;next_c[C_CURSOR_LIVE]=0;next_c[C_ADVANCE_PENDING]=0;
  end
  if(active&&frame_accept)begin
   if(!c[C_LIVE]&&!c[C_CURSOR_LIVE]&&!c[C_ADVANCE_PENDING]&&frame_tuple==c[C_TUPLE +:239]&&frame_owner==c[C_OWNER +:55])next_c=0;
   else next_c[C_FAULT]=1;
  end
 end
 initial if(ACTOR_INDEX<0||ACTOR_INDEX>=64)$fatal(1,"native actor namespace");
endmodule
