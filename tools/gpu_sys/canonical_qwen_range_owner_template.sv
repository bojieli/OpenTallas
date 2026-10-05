`timescale 1ps/1ps
// Default-off FUNCTIONAL component. Source clocks preserved; loaded SS/FF unknown.
// Cold POR alone initializes words. Warm reset quarantines retained source debt.
module ot_gpu_qwen_native_range_owner #(parameter bit ENABLE=0,
 parameter integer SM_INDEX=0)(
 input wire clk,por_n,warm_reset,
 input wire session_begin_valid,input wire [63:0] session_begin_id,
 input wire allcopies_fenced,reverse_fenced,ingress_quiet,
 output wire session_begin_ready,
 input wire claim_valid,claim_initial,input wire [238:0] claim_tuple,
 input wire [54:0] claim_owner, output wire claim_ready,
 output wire [2:0] claim_row,
 // Source INPUT association is explicit, distinct from output_version in tuple.
 input wire bind_valid,input wire [238:0] bind_tuple,input wire [6:0] bind_mask,
 output wire bind_ready,
 output wire issued_input_live,issued_input_started,
 output wire inputs_bound_valid,output wire [238:0] inputs_bound_tuple,
 output wire [6:0] inputs_bound_mask,input wire inputs_bound_ready,
 input wire go_accepted,input wire [238:0] go_tuple,
 input wire [10:0] next_source_PC,output wire row_barrier_ready,
 output wire [31:0] expected_output_page_mask,
 input wire page_ack_valid,input wire [54:0] page_ack_owner,
 output wire page_ack_ready,
 output wire rf_range_ack_valid,output wire [238:0] rf_range_ack_tuple,
 output wire [54:0] rf_range_ack_owner,output wire [31:0] rf_range_ack_page_mask,
 input wire rf_range_ack_ready,
 input wire producer_visible_valid,input wire [238:0] producer_visible_tuple,
 output wire producer_visible_ready,
 input wire publish_valid,input wire [238:0] publish_tuple,
 input wire [54:0] publish_owner,input wire [31:0] publish_page_mask,
 output wire publish_ready,
 input wire input_terminal_valid,input wire [238:0] input_terminal_tuple,
 input wire [6:0] input_terminal_mask,output wire input_terminal_ready,
 input wire input_reverse_valid,input wire [238:0] input_reverse_tuple,
 input wire [6:0] input_reverse_mask,output wire input_reverse_ready,
 input wire frame_retire_valid,input wire [238:0] frame_retire_tuple,
 input wire [54:0] frame_retire_owner,output wire frame_retire_ready,
 input wire source_native_retire_valid,input wire [63:0] source_native_retire_session,
 input wire [10:0] source_native_retire_version,input wire [54:0] source_native_retire_owner,
 output wire source_native_retire_ready,
 input wire query_valid,query_write,input wire [238:0] query_tuple,
 input wire [10:0] query_version,input wire [8:0] query_slot,output wire query_ready,
 output wire query_result_valid,input wire query_result_ready,
 output wire [238:0] query_result_tuple,output wire [45:0] query_result_owner,
 output wire [8:0] query_result_slot,output wire source_owner_retained,
 output wire fault,output wire [6:0] live_rows,output wire [6:0] published_rows,
 output wire [6:0] consumer_rows,output wire [63:0] held_session
);
 @DECLARATIONS@
 @SOURCE_META@
 localparam integer RB=@R_BITS@,GB=@G_BITS@,BB=@B_BITS@,QB=@Q_BITS@;
 wire [RB-1:0] r[0:6]; reg [RB-1:0] rn[0:6];
 wire [GB-1:0] g;reg [GB-1:0] gn;
 wire [BB-1:0] b;reg [BB-1:0] bn;
 wire [QB-1:0] q;reg [QB-1:0] qn;
 wire [6:0] rc,rd,re;wire gc,gd,ge,bc,bd,be,qc,qd,qe;
 genvar z;
 generate for(z=0;z<7;z=z+1)begin:rows
  ot_gpu_qwen_source_record #(.BITS(RB),.INDEX(SM_INDEX),.BASE(z*14),.KIND(0)) record(
   .clk(clk),.por_n(por_n),.write_enable(active),.next_data(rn[z]),
   .data(r[z]),.clean(rc[z]),.bad(rd[z]),.repairing(re[z]));
  assign live_rows[z]=r[z][R_LIVE];assign published_rows[z]=r[z][R_PUBLISHED];
  assign consumer_rows[z]=r[z][R_CONSUMER_LIVE];
 end endgenerate
 ot_gpu_qwen_source_record #(.BITS(GB),.INDEX(SM_INDEX),.BASE(98),.KIND(1)) globals(
 .clk(clk),.por_n(por_n),.write_enable(gc),.next_data(gn),.data(g),.clean(gc),.bad(gd),.repairing(ge));
 ot_gpu_qwen_source_record #(.BITS(BB),.INDEX(SM_INDEX),.BASE(100),.KIND(2)) binding(
 .clk(clk),.por_n(por_n),.write_enable(active),.next_data(bn),.data(b),.clean(bc),.bad(bd),.repairing(be));
 ot_gpu_qwen_source_record #(.BITS(QB),.INDEX(SM_INDEX),.BASE(106),.KIND(3)) query(
 .clk(clk),.por_n(por_n),.write_enable(active),.next_data(qn),.data(q),.clean(qc),.bad(qd),.repairing(qe));
 wire all_clean=(&rc)&&gc&&bc&&qc;
 wire any_bad=(|rd)||gd||bd||qd;
 wire base_active=ENABLE&&por_n&&!warm_reset&&all_clean&&!g[G_FAULT]&&!g[G_QUARANTINE]&&g[G_SESSION_LIVE];
 wire active=base_active&&!unexpected;
 assign fault=ENABLE&&(any_bad||g[G_FAULT]||g[G_QUARANTINE]);
 assign held_session=g[G_SESSION +:64];
 function automatic [31:0] page_mask(input [238:0] t);
  integer n;begin n=t[9:0]-{1'b0,t[18:10]};
   if(n<1||n>32)page_mask=0;else page_mask=32'hffffffff>>(32-n);
  end
 endfunction
 function automatic local_tuple(input [238:0] t);
 begin local_tuple=t[238:175]==g[G_SESSION +:64]&&t[174:164]<1737&&
  t[35]==(SM_INDEX/32)&&t[34:30]==(SM_INDEX%32)&&page_mask(t)!=0;end
 endfunction
 // All matches are computed from CURRENT coded records, separate from next state.
 integer i,j;integer empty_row,claim_match,bind_output_row,output_row,ack_row,visible_row,pub_row,retire_row,release_row,query_row,aggregate_row;
 reg [48:0] cm;reg [11:0] ec;
 reg bind_legal,barrier_ok,release_legal,query_legal,claim_legal;
 reg [31:0] ack_mask;reg [238:0] t;
 always @* begin
  empty_row=-1;claim_match=-1;bind_output_row=-1;output_row=-1;ack_row=-1;visible_row=-1;
  pub_row=-1;retire_row=-1;release_row=-1;query_row=-1;aggregate_row=-1;
  barrier_ok=1;bind_legal=bind_tuple[238:175]==g[G_SESSION +:64]&&bind_tuple[174:164]<1737&&page_mask(bind_tuple)!=0;query_legal=0;release_legal=0;
  cm=source_meta(claim_tuple[29:19]);ec=0;ack_mask=0;t=0;
  for(i=0;i<7;i=i+1)begin
   if(!r[i][R_LIVE]&&empty_row<0)empty_row=i;
   if(r[i][R_LIVE])begin
    t=r[i][R_PRODUCER_TUPLE +:239];
    if(r[i][R_SOURCE_VERSION +:11]==claim_tuple[29:19])claim_match=i;
    if(t==b[B_TUPLE +:239])output_row=i;
    if(t==bind_tuple&&!r[i][R_PRODUCER_STARTED])bind_output_row=i;
    if(page_ack_owner[54:9]==r[i][R_OWNER55+9 +:46]&&
       page_ack_owner[8:0]>=t[18:10]&&{1'b0,page_ack_owner[8:0]}<t[9:0])ack_row=i;
    if(t==producer_visible_tuple)visible_row=i;
    if(t==publish_tuple&&r[i][R_OWNER55 +:55]==publish_owner)pub_row=i;
    if(t==frame_retire_tuple&&r[i][R_OWNER55 +:55]==frame_retire_owner)retire_row=i;
    if(r[i][R_SOURCE_VERSION +:11]==source_native_retire_version&&r[i][R_OWNER55 +:55]==source_native_retire_owner)release_row=i;
    if(r[i][R_SOURCE_VERSION +:11]==query_version)query_row=i;
    if(r[i][R_ACK_BITMAP +:32]==page_mask(t)&&r[i][R_PRODUCER_STARTED]&&!r[i][R_ACK_DELIVERED]&&aggregate_row<0)aggregate_row=i;
    if(r[i][R_RETIRE_PC +:11]<next_source_PC)barrier_ok=0;
   end
   if(bind_mask[i])begin
    ec=expected_consumer(r[i][R_SOURCE_VERSION +:11],r[i][R_CONSUMER_ORDINAL +:9]);
    if(!r[i][R_LIVE]||!r[i][R_PUBLISHED]||!r[i][R_PRODUCER_FRAME_RETIRED]||r[i][R_CONSUMER_LIVE]||
       !ec[11]||ec[10:0]!=bind_tuple[174:164])bind_legal=0;
   end
  end
  claim_legal=local_tuple(claim_tuple)&&cm[48]&&cm[47]==claim_initial&&
   cm[46:38]==claim_tuple[18:10]&&cm[37:31]==(claim_tuple[9:0]-{1'b0,claim_tuple[18:10]})&&
   (claim_initial||cm[30:20]==claim_tuple[174:164])&&claim_owner[8:0]==claim_tuple[18:10];
  if(local_tuple(bind_tuple)&&bind_output_row<0)bind_legal=0;
  if(release_row>=0)release_legal=source_native_retire_session==g[G_SESSION +:64]&&
   r[release_row][R_PUBLISHED]&&r[release_row][R_PRODUCER_FRAME_RETIRED]&&!r[release_row][R_CONSUMER_LIVE]&&
   r[release_row][R_CONSUMER_ORDINAL +:9]==r[release_row][R_CONSUMER_COUNT +:9]&&!q[Q_LIVE]&&!b[B_LIVE];
  if(query_row>=0)begin
   t=r[query_row][R_PRODUCER_TUPLE +:239];
   query_legal=query_slot>=t[18:10]&&{1'b0,query_slot}<t[9:0]&&
    ((query_write&&r[query_row][R_PRODUCER_STARTED]&&!r[query_row][R_PUBLISHED]&&query_tuple==t)||
     (!query_write&&r[query_row][R_PUBLISHED]&&r[query_row][R_CONSUMER_LIVE]&&b[B_GO]&&
      query_tuple==r[query_row][R_CONSUMER_TUPLE +:239]));
  end
 end
 wire terminal_match=b[B_LIVE]&&b[B_GO]&&input_terminal_tuple==b[B_TUPLE +:239]&&input_terminal_mask==b[B_MASK +:7]&&!b[B_TERMINAL];
 wire reverse_match=b[B_LIVE]&&b[B_GO]&&input_reverse_tuple==b[B_TUPLE +:239]&&input_reverse_mask==b[B_MASK +:7]&&!b[B_REVERSE];
 wire go_match=barrier_ok&&next_source_PC==go_tuple[174:164]&&inputs_bound_ready&&b[B_LIVE]&&!b[B_GO]&&go_tuple==b[B_TUPLE +:239]&&(!local_tuple(b[B_TUPLE +:239])||output_row>=0);
 wire unexpected=base_active&&(
  (claim_valid&&(!claim_legal||claim_match>=0))||
  (bind_valid&&!b[B_LIVE]&&!bind_legal)||
  (go_accepted&&!go_match)||
  (page_ack_valid&&(ack_row<0||(ack_row>=0&&(!r[ack_row][R_PRODUCER_STARTED]||r[ack_row][R_PUBLISHED]))))||
  (producer_visible_valid&&(visible_row<0||(visible_row>=0&&(!r[visible_row][R_PRODUCER_STARTED]||r[visible_row][R_PRODUCER_VISIBLE]))))||
  (input_terminal_valid&&!terminal_match)||(input_reverse_valid&&!reverse_match));
 assign session_begin_ready=ENABLE&&por_n&&!warm_reset&&all_clean&&!any_bad&&!g[G_FAULT]&&
  live_rows==0&&!b[B_LIVE]&&!q[Q_LIVE]&&allcopies_fenced&&reverse_fenced&&ingress_quiet;
 assign claim_ready=active&&claim_legal&&claim_match<0&&empty_row>=0&&!b[B_LIVE]&&!q[Q_LIVE];
 assign claim_row=empty_row<0?3'd0:empty_row;
 assign bind_ready=active&&!b[B_LIVE]&&!q[Q_LIVE]&&bind_legal;
 assign issued_input_live=all_clean&&b[B_LIVE];assign issued_input_started=all_clean&&b[B_GO];
 assign inputs_bound_valid=active&&b[B_LIVE]&&!b[B_GO];
 assign inputs_bound_tuple=b[B_TUPLE +:239];assign inputs_bound_mask=b[B_MASK +:7];
 assign row_barrier_ready=active&&barrier_ok;
 assign expected_output_page_mask=page_mask(b[B_TUPLE +:239]);
 assign page_ack_ready=active&&ack_row>=0;
 assign rf_range_ack_valid=active&&aggregate_row>=0;
 assign rf_range_ack_tuple=aggregate_row>=0?r[aggregate_row][R_PRODUCER_TUPLE +:239]:0;
 assign rf_range_ack_owner=aggregate_row>=0?r[aggregate_row][R_OWNER55 +:55]:0;
 assign rf_range_ack_page_mask=aggregate_row>=0?r[aggregate_row][R_ACK_BITMAP +:32]:0;
 assign producer_visible_ready=active&&visible_row>=0;
 assign publish_ready=active&&pub_row>=0&&r[pub_row][R_PRODUCER_VISIBLE]&&r[pub_row][R_ACK_DELIVERED]&&
  !r[pub_row][R_PUBLISHED]&&publish_page_mask==page_mask(publish_tuple)&&r[pub_row][R_ACK_BITMAP +:32]==publish_page_mask;
 assign input_terminal_ready=active&&terminal_match;
 assign input_reverse_ready=active&&reverse_match;
 assign frame_retire_ready=active&&(!local_tuple(frame_retire_tuple)||(retire_row>=0&&r[retire_row][R_PUBLISHED]&&!r[retire_row][R_PRODUCER_FRAME_RETIRED]))&&b[B_LIVE]&&b[B_TERMINAL]&&b[B_REVERSE]&&frame_retire_tuple==b[B_TUPLE +:239]&&!q[Q_LIVE]&&!query_valid;
 assign source_native_retire_ready=active&&release_legal&&!bind_valid&&!query_valid&&!claim_valid;
 assign query_ready=active&&!q[Q_LIVE]&&query_legal;
 assign query_result_valid=active&&q[Q_LIVE]&&q[Q_RESULT]&&source_owner_retained;
 assign query_result_tuple=q[Q_TUPLE +:239];assign query_result_owner=q[Q_OWNER46 +:46];assign query_result_slot=q[Q_SLOT +:9];
 wire [2:0] qr=q[Q_ROW +:3];
 assign source_owner_retained=all_clean&&q[Q_LIVE]&&qr<7&&r[qr][R_LIVE]&&
  r[qr][R_OWNER55+9 +:46]==q[Q_OWNER46 +:46]&&
  ((q[Q_ROLE]&&q[Q_TUPLE +:239]==r[qr][R_PRODUCER_TUPLE +:239])||
   (!q[Q_ROLE]&&r[qr][R_CONSUMER_LIVE]&&q[Q_TUPLE +:239]==r[qr][R_CONSUMER_TUPLE +:239]));
 integer n;
 always @* begin
  gn=g;bn=b;qn=q;for(n=0;n<7;n=n+1)rn[n]=r[n];
  if(ENABLE&&gc&&por_n)begin
   if(warm_reset)gn[G_QUARANTINE]=1;
   if(any_bad||unexpected)gn[G_FAULT]=1;
   if(session_begin_valid&&session_begin_ready)begin gn=0;gn[G_SESSION_LIVE]=1;gn[G_SESSION +:64]=session_begin_id;end
  end
  if(active)begin
   if(claim_valid&&claim_ready)begin
    rn[empty_row]=0;rn[empty_row][R_LIVE]=1;
    rn[empty_row][R_PRODUCER_TUPLE +:239]=claim_tuple;rn[empty_row][R_OWNER55 +:55]=claim_owner;
    rn[empty_row][R_SOURCE_VERSION +:11]=claim_tuple[29:19];
    rn[empty_row][R_RETIRE_PC +:11]=cm[19:9];rn[empty_row][R_CONSUMER_COUNT +:9]=cm[8:0];
   end
   if(bind_valid&&bind_ready)begin
    bn=0;bn[B_LIVE]=1;bn[B_TUPLE +:239]=bind_tuple;bn[B_MASK +:7]=bind_mask;
    for(n=0;n<7;n=n+1)if(bind_mask[n])begin
     rn[n][R_CONSUMER_LIVE]=1;rn[n][R_CONSUMER_TUPLE +:239]=bind_tuple;
     rn[n][R_CONSUMER_TERMINAL]=0;rn[n][R_CONSUMER_REVERSE]=0;
    end
   end
   if(go_accepted&&go_match)begin bn[B_GO]=1;if(output_row>=0)rn[output_row][R_PRODUCER_STARTED]=1;end
   if(page_ack_valid&&page_ack_ready)rn[ack_row][R_ACK_BITMAP+(page_ack_owner[8:0]-r[ack_row][R_PRODUCER_TUPLE+10 +:9])]=1;
   if(rf_range_ack_valid&&rf_range_ack_ready)rn[aggregate_row][R_ACK_DELIVERED]=1;
   if(producer_visible_valid&&producer_visible_ready)rn[visible_row][R_PRODUCER_VISIBLE]=1;
   if(publish_valid&&publish_ready)rn[pub_row][R_PUBLISHED]=1;
   if(input_terminal_valid&&input_terminal_ready)begin
    bn[B_TERMINAL]=1;for(n=0;n<7;n=n+1)if(b[B_MASK+n])rn[n][R_CONSUMER_TERMINAL]=1;
   end
   if(input_reverse_valid&&input_reverse_ready)begin
    bn[B_REVERSE]=1;for(n=0;n<7;n=n+1)if(b[B_MASK+n])rn[n][R_CONSUMER_REVERSE]=1;
   end
   if(frame_retire_valid&&frame_retire_ready)begin
    if(retire_row>=0)rn[retire_row][R_PRODUCER_FRAME_RETIRED]=1;
    for(n=0;n<7;n=n+1)if(b[B_MASK+n])begin
     rn[n][R_CONSUMER_LIVE]=0;rn[n][R_CONSUMER_ORDINAL +:9]=r[n][R_CONSUMER_ORDINAL +:9]+1'b1;
    end
    bn=0;
   end
   if(source_native_retire_valid&&source_native_retire_ready)rn[release_row]=0;
   if(query_valid&&query_ready)begin
    qn=0;qn[Q_LIVE]=1;qn[Q_ROLE]=query_write;qn[Q_TUPLE +:239]=query_tuple;
    qn[Q_ROW +:3]=query_row;qn[Q_SLOT +:9]=query_slot;
    qn[Q_OWNER46 +:46]=r[query_row][R_OWNER55+9 +:46];
   end
   if(q[Q_LIVE]&&!q[Q_RESULT])begin
    if(q[Q_PHASE +:3]==3)qn[Q_RESULT]=1;else qn[Q_PHASE +:3]=q[Q_PHASE +:3]+1'b1;
   end
   if(query_result_valid&&query_result_ready)qn=0;
  end
 end
 initial if(SM_INDEX<0||SM_INDEX>=64)$fatal(1,"SM namespace");
endmodule

// All mutable words are sealed full72 physical bits, including padding.
// Separate encoder/decoder instances avoid next-state/current-status feedback.
// CE is never released: current-word scrub wins before any normal operation.
module ot_gpu_qwen_source_record #(parameter integer BITS=44,INDEX=0,BASE=0,KIND=0)(
 input wire clk,por_n,write_enable,input wire [BITS-1:0] next_data,
 output wire [BITS-1:0] data,output wire clean,bad,repairing);
 localparam integer WORDS=(BITS+43)/44;
 reg [WORDS*72-1:0] coded;
 wire [WORDS-1:0] ok,due,ce;
 genvar w;
 generate for(w=0;w<WORDS;w=w+1)begin:words
  localparam integer PAY=(BITS-w*44<44)?BITS-w*44:44;
  wire [43:0] payload={{(44-PAY){1'b0}},next_data[w*44 +:PAY]};
  wire [43:0] decoded;wire [71:0] enc,zero_enc,fixed;
  wire seal,pad,unc;
  ot_w2_sealed_secded72 #(.PC_ID(INDEX),.WORD_INDEX(BASE+w),.WORD_KIND(KIND),.PAYLOAD_BITS(PAY)) decoder(
   .payload(44'b0),.current_word(coded[w*72 +:72]),.release_clean(ok[w]),
   .correctable(ce[w]),.uncorrectable(unc),.seal_ok(seal),.padding_ok(pad),.repaired_payload(decoded),.repaired_word(fixed));
  ot_w2_sealed_secded72 #(.PC_ID(INDEX),.WORD_INDEX(BASE+w),.WORD_KIND(KIND),.PAYLOAD_BITS(PAY)) encoder(
   .payload(payload),.current_word(72'b0),.encoded_word(enc));
  ot_w2_sealed_secded72 #(.PC_ID(INDEX),.WORD_INDEX(BASE+w),.WORD_KIND(KIND),.PAYLOAD_BITS(PAY)) reset_encoder(
   .payload(44'b0),.current_word(72'b0),.encoded_word(zero_enc));
  assign due[w]=unc||!seal||!pad;assign data[w*44 +:PAY]=decoded[0 +:PAY];
  always @(posedge clk or negedge por_n)begin
   if(!por_n)coded[w*72 +:72]<=zero_enc;
   else if(ce[w]&&!due[w])coded[w*72 +:72]<=fixed;
   else if(write_enable&&clean)coded[w*72 +:72]<=enc;
  end
 end endgenerate
 assign clean=&ok;assign bad=|due;assign repairing=|ce;
endmodule
