# HEAD CTL first-fault diagnosis

The retained source narrows the historical fv01400 observation. CTL core drives
`dflt({4{lep_fault_i}})`, and its logic sets fv10 from that same `lep_fault_i`
through `lepf_q`, while fv12 ORs the link faults including dflt. These two bits
therefore need not represent independent LEP and mesh failures. The actual
partition passes `lep_fault_i_q | cland_up_fault` into that core input.

The retained full18 generator `/home/ubuntu/coord/tmp/phase_boot_full.py` checks
`cycles>400 && fv`. Its abort at401 is the first permitted observation, not the
measured time that the fault began. Reset, K or timeout conclusions cannot be
drawn from401. A future observer must trace the two upstream inputs from reset.

New finite diagnostic: five literal CTL local count-aligned rings, driven by the
retained1608-source-clock TT/FF profiles and all357 literal control cones, with
their actual K, writer FSTART and reader START+1 relay. All five reached ready1,
fault0 at both TT and FF. The same executable with K+4 at the testbench pins
faulted all five at both corners. No production K, clock, reset or guard changed.

Measured Intel2 unit2623823-1794062462 exit0: build143.863s, Verilator297.965MB,
TT3.256s/12MB and FF3.516s/12MB. Wrong-K control unit2768386-1794062710 exit0,
TT3.127s and FF2.903s. Only local count guards are measured. Payloads are zero
because count tags are independent of payload; actual upstream fault bits,
two direct FF fault-status inputs, LEP return, codecs and arithmetic are absent.
This does not reproduce or fix the historical full18 fault, prove its old source
cohort byte identity, or establish physical/source-phase/G5 qualification.

The next trace is actual `lep_fault_i_q`, `cland_up_fault`, the five propagated
fault-status bits and the two direct FF ctrl_i0/n_rx_i status faults from reset.
HEAD's physical owner independently found stale source/reset export descriptors
and owns their derived refresh. No duplicate reset/plan/RTL fix is made here.

Reproduce preparation with `tools/s81_dv/head_fault_1107/prepare.py --parent
<selected exact parent SV directory> --tt <retained profile_tt.json> --ff
<retained profile_ff.json> --out <fresh packet>`. The copied source readset and
profile hashes are in scope.json. Copy that parent's ot_dp_cells/start_stages
and its selected common ot_dp_clk_landing, ot_dp_clk_landing_ca, ot_meso_fifo
sources into the packet, then run `run.sh` through ot-run4GB2T. `run_mutant.sh`
uses the same executable. Retained inputs remain in the owned
`/srv/opentallas-scratch/claude/wt/codex-token-production-1107/head_frontier/parent`
and coordinator `tmp/codex-head-host-reset-origin-1106` profiles. This is a
source-bound diagnostic, not a release gate or new full-die vehicle.
