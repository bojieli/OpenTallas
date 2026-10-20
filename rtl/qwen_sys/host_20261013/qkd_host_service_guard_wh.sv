// KV-RETIRE 10-19: qkd_host_service_guard with WARM-RESET HISTORY retained in the POR domain.
//
// Hole (codex/kv-host-health-producers-1019 afee37b56, facts lane service[22]): a warm host_rst_n resets the fault
// producers AND the guard's fm/fs/sticky history, while POR-domain state (retained requests / contexts, peer epochs,
// lifecycle) survives.  After the warm reset the guard is clean, so a context that was live -- or a die that had raised
// health -- before the reset could be re-admitted as healthy.  Owner 10-19 09:39: continuous sticky health stays live,
// is never cleared or masked, and later health blocks subsequent admission.
//
// Repair (wrapper; the closed guard is instantiated unchanged):
//   * a POR-domain shadow (ASYNC_REG pm/ps on the raw sources, plus the guard's registered diag_raw / abort) records
//     whether health was raised up to the last edge before the warm reset; it stops updating while host_rst_n is low;
//   * on the first edge with host_rst_n low, warm_lost <= history | retained_ctx (a POR-retained context was live);
//   * warm_lost is POR-only state: it vetoes the guard outputs exactly where `bad` does (abort, guarded_tk[88], status
//     bad / ready bits, service_ready) from the first edge of the warm reset, with no added edge on any output (one OR /
//     AND gate after the guard's output flops and the warm_lost flop);
//   * it clears ONLY on POR or on recovery_certified (the host recovery_clear, which the native endpoint honours only
//     after the global KV / VM / collective / host drains with no owned context) while no POR-retained context is live
//     and host_rst_n is high.  A recovery that the endpoint refuses raises its protocol_fault, which the guard observes
//     as ordinary sticky health.
// The veto never gates or clears a fault source; it only adds health.  Static: no ready / credit / wait.
// WH_MUT (bench negative controls): 1 = legacy (warm reset forgets history: warm_lost never set); 2 = retained_ctx
// ignored; 3 = recovery clears even while a retained context is live.
module qkd_host_service_guard_wh #(parameter SETTLE=4,MUT=0,WH_MUT=0)(
 input wire ck_guard,rst_n,por_n,input wire[24:0]raw_faults,
 input wire retained_ctx,recovery_certified,
 input wire[2:0]die_id,input wire[7:0]physical_faults,transport_faults,
 input wire accepted_ing_v,input wire[1:0]accepted_ing_cls,
 input wire[15:0]accepted_ing_header,input wire done_v,input wire[63:0]done_d,
 input wire boot_barrier_v,input wire[31:0]boot_barrier_target,
 input wire begin_v,input wire[15:0]begin_epoch,
 input wire pending_advertised,input wire[15:0]pending_epoch,
 input wire[92:0]local_tk,
 output wire[92:0]guarded_tk,output wire abort,service_ready,
 output wire[15:0]service_epoch,output wire[25:0]diag_raw,
 output wire[31:0]status,output wire[3:0]groups,
 output wire[7:0]physical_diag,transport_diag,
 input wire service_protocol_fault,
 output reg warm_lost
);
 wire[92:0]g_tk;wire g_abort,g_ready;wire[25:0]g_diag;wire[31:0]g_status;
 qkd_host_service_guard #(.SETTLE(SETTLE),.MUT(MUT)) u_guard(
  .ck_guard(ck_guard),.rst_n(rst_n),.raw_faults(raw_faults),.die_id(die_id),.physical_faults(physical_faults),
  .transport_faults(transport_faults),.accepted_ing_v(accepted_ing_v),.accepted_ing_cls(accepted_ing_cls),
  .accepted_ing_header(accepted_ing_header),.done_v(done_v),.done_d(done_d),.boot_barrier_v(boot_barrier_v),
  .boot_barrier_target(boot_barrier_target),.begin_v(begin_v),.begin_epoch(begin_epoch),
  .pending_advertised(pending_advertised),.pending_epoch(pending_epoch),.local_tk(local_tk),
  .guarded_tk(g_tk),.abort(g_abort),.service_ready(g_ready),.service_epoch(service_epoch),.diag_raw(g_diag),
  .status(g_status),.groups(groups),.physical_diag(physical_diag),.transport_diag(transport_diag),
  .service_protocol_fault(service_protocol_fault));
 (* ASYNC_REG="TRUE" *)reg pm,ps;reg hist;
 always @(posedge ck_guard or negedge por_n)
  if(!por_n)begin pm<=0;ps<=0;hist<=0;warm_lost<=0;end
  else if(rst_n)begin
   pm<=|raw_faults;ps<=pm;hist<=pm|ps|(|g_diag)|g_abort;
   if(recovery_certified&&(WH_MUT==3||!retained_ctx))warm_lost<=0;
  end else begin
   if(WH_MUT!=1&&(hist|pm|ps|(retained_ctx&&WH_MUT!=2)))warm_lost<=1;
   pm<=0;ps<=0;hist<=0;
  end
 assign abort=g_abort|warm_lost;
 assign service_ready=g_ready&&!warm_lost;
 assign guarded_tk={g_tk[92:89],g_tk[88]|warm_lost,g_tk[87:0]};
 // status = {mc, quiet, fc, 2'b0, wait_advert, open, protocol|internal, bad, service_ready, clean}
 assign status={g_status[31:3],g_status[2]|warm_lost,g_status[1]&&!warm_lost,g_status[0]};
 assign diag_raw=g_diag;
endmodule
