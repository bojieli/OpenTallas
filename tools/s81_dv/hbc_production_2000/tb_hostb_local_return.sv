`timescale 1ns/1ps
// Bench for dsdv_hostb_stage_hbc: HOST-loaded HBC1 context -> first HBE header gated against it.
// Records are driven on the HFWD kind-6 ring at their static boot-counter dates (no handshakes).
module tb_hostb_local_return;
 reg ck=0,rst_n=0;always #0.5 ck=~ck;
 reg [1103:0] ring=0;
 reg [559:0] rec[0:15];integer nrec=0,idx=0,mode=0,cyc=0,writes=0,ctx_cyc=-1,write_cyc=-1,hdr_cyc=-1;
 reg [511:0] payload[0:0];reg [47:0] edge_at_hdr=0;
 integer returns=0;wire [3:0] return_fault;
 wire [76:0] status_host={1'b1,12'd0,64'h123456789abcdef0};
 wire [53:0] status_kd={1'b1,21'(mode==1?16755:16754),32'hdeadbeef};
 wire [1103:0] to_local,next_ro;wire [514:0] f_host;wire [52:0] ks;wire [2:0] ks_slot;wire [5:0] arm_mask;
 wire arm_commit,context_valid;wire [11:0] fault;wire [47:0] receiver_edge,boot_edge;wire [7:0] hbc_fault;
 dsdv_hostb_stage_hbc #(.ENABLE(1),.LOCAL_STAGE(1),.LOCAL_RANK(0),.PHASE_BOUND(1),.CLOCK_RESET_ID(64'h5381C7C0DE1021),
  .BOOT_HEADER_EDGE(48'd20),.BOOT_COMMIT_EDGE(48'd30),
  .RETURN_LOCAL(1),.RETURN_ARRIVAL_DEADLINE(48'd8100)) dut(.ck(ck),.rst_n(rst_n),.job_active(1'b0),.starter_armed(1'b0),
  .status_t_host(status_host),.status_t_kd(status_kd),

  .from_prev(ring),.local_ro(1104'd0),.return_ro(1104'd0),
  .to_local(to_local),.next_ro(next_ro),.f_host(f_host),.ks_descriptor(ks),.ks_slot(ks_slot),
  .fault(flt));
 // S81/PORTFIX-FLT 10-25: the unit's ports are one 1-bit sticky fault (flt); the former status ports are tapped
 wire flt;assign return_fault=dut.return_fault;assign arm_mask=dut.arm_mask;assign arm_commit=dut.arm_commit;assign fault=dut.stage_fault;
 assign context_valid=dut.context_valid;assign receiver_edge=dut.receiver_edge;assign boot_edge=dut.boot_edge;assign hbc_fault=dut.hbc_fault;
 string vec;
 initial begin
  if(!$value$plusargs("VEC=%s",vec))$fatal(1,"+VEC");
  if(!$value$plusargs("MODE=%d",mode))$fatal(1,"+MODE");
  $readmemh({vec,"/m0.memh"},rec);$readmemh({vec,"/payload.memh"},payload);
  for(nrec=0;nrec<16&&rec[nrec]!==560'bx;nrec++);
  repeat(3)@(posedge ck);rst_n=1;
 end
 // Host schedule: drive record i for the cycle whose capture edge sees boot_edge==date_i.
 always @(negedge ck)begin
  ring=0;
  if(rst_n&&idx<nrec&&boot_edge==rec[idx][559:512])begin
   ring[0]=1;ring[3:1]=3'd6;ring[532:21]=rec[idx][511:0];
   if(rec[idx][31:0]==32'h31454248&&hdr_cyc<0)begin hdr_cyc=cyc;edge_at_hdr=receiver_edge;end
   idx++;
  end
 end
 always @(posedge ck)if(rst_n)begin
  #0.01;cyc++;
  if(context_valid&&ctx_cyc<0)ctx_cyc=cyc;
  if(f_host[0])begin writes++;write_cyc=cyc;
   if(f_host[512:1]!==payload[0]||f_host[514:513]!==0)$fatal(1,"FAIL mode%0d f_host payload mismatch %h",mode,f_host[512:1]);end
  if(to_local[0])$fatal(1,"FAIL mode%0d HBC/HBE record leaked to ordinary ring at cyc%0d",mode,cyc);
  if(next_ro[0])begin
   if(next_ro[52:21]!=32'h31454248||next_ro[60:57]!=3)$fatal(1,"return header shape");
   if(next_ro[371:295]!==status_host||next_ro[425:372]!==status_kd)$fatal(1,"status payload altered");
   if(next_ro[230:183]!==48'd8100)$fatal(1,"upstream deadline authority changed");
   returns++;
  end
  if(boot_edge==48'd7000)begin
   if(flt!==((|fault)||(|hbc_fault)||(|return_fault)))$fatal(1,"FAIL 1-bit fault %b != sticky OR rf%h f%h hbc%h",flt,return_fault,fault,hbc_fault);
   if(mode==0)begin
    if(writes!=1||returns!=1||return_fault!=0||fault!=0||hbc_fault!=0)$fatal(1,"return positive failed returns%0d rf%h f%h",returns,return_fault,fault);
    $display("HBC_RETURN PASS actual sampled status/token + committed context -> one booked return; explicit upstream test deadline8100");
   end else begin
    if(returns!=0||return_fault==0)$fatal(1,"wrong KIT token not refused");
    $display("HBC_RETURN NEGATIVE CAUGHT wrong KIT token rf%h",return_fault);
   end
   $finish;
  end
 end
endmodule
