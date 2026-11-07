# HEAD CTL first-fault diagnosis

The retained source narrows the historical fv01400 observation. CTL core drives
`dflt({4{lep_fault_i}})`, and its logic sets fv10 from that same `lep_fault_i`
through `lepf_q`, while fv12 ORs the link faults including dflt. These two bits
therefore need not represent independent LEP and mesh failures. The actual
partition passes `lep_fault_i_q | cland_up_fault` into that core input.

The subsequent one-hop25-ring frontier on CTL/SP0/CTL_nstrip/LEP found a real
FF failure: TT25/25 clear, FF21/25 clear. SP0 ad_i/bd_i/hd_i/x_i, all driven
from CTL with K26 and reader START+5 relays, fail the lower opposite-edge guard.
Read-only observation of the unchanged compiled model gives first-count times:

| Corner | Reader count0 (ps) | Writer count0 (ps) | Lag R-W+26*833 (ps) |
|---|---:|---:|---:|
| TT | 229701.746 | 250342.585 | 1017.161 |
| FF | 228407.675 | 249810.593 | 255.082 |

FF lag is below the416.5ps guard. Its armed failure has valid1/lap1/lower0/upper1
and timeout counter40, so this is a lower-window failure, not missing data or
a ready timeout. No K, reset or clock was changed. SP1-to-SP0's four other
rings, K47, pass. These are functional observations under the retained
phase/internal-budget model, not routed STA slack or proof of the old TT fault.
The HEAD owner has the measured source/phase/cohort issue; no manual K fix was
made. Nominal25-ring unit3001753 and read-only observer unit3300559 both ended0.
The observer's first attempt failed to find verilated.h because of an include
prefix error; that failure remains and only the observer was relinked.

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
