W10 source-bound actual-vector clock duty and baseline power reconciliation

Admission: HOLD. No RTL edits, hardware-model rebuild, floorplan, CTS or route.
625-row/S45 prior conditional candidate is unchanged; no density/clock relaxation.

Inputs: retained exact_r2 and golden_n4_r1 Verilator model objects and vectors
under /home/ubuntu/w10-w18-recovery/baseline_wake. Original model archives were
read-only. Only a private archive's generated main symbol was renamed so an
observer could reuse the original event scheduler and read root/leaf states.
capture.json binds original archives, runtime objects, generated headers,
Verilator input manifests, qualification receipts, observers and vector hashes.
Both qualification receipts' RTL hashes match b046de7f0; the isolated array
binding is included. No new arithmetic claim replaces the retained golden gate.
The fullgolden replay observed all 240 rows across 13 cases, zero row errors and
zero faults, with last-row cycles matching the retained case records. The reset
fixture retains its existing exact assertions and reproduces 20769 coverage
cycles/84 rows. Eight leaves are independently observed in that fixture; the
array simulator folds identical leaves. The independent fullmap gate retains
eight distinct wake FF/ICG cells; folding in simulation is not physical cloning.

Observed full-column BF16 XF8/N4/NB2/MTP6 schedule (root edges / each leaf edges):
router and compressor: e0 1710/1673, e1 1710/1484
whole WKV: e0/e1 1710/1673
indexer: e0/e1 554/517
Every full-column case contains 127 drain-only root cycles per element. Enabled
leaf counts exceed walker-busy counts by 132 in these fixtures. Root duty is 1
in each observed window. All eight leaves share wake, including unused-family
arithmetic leaves; operand inactivity cannot be assigned as clock inactivity.
All captured wake recurrences and ideal latch-phase checks pass. The first
initially-low reset edge starts before the simulator has latched reset wake;
its measured leaf edge is not invented or excluded from total duty. Reset-
deasserted fractions are reported separately. Sleep intervals are retained.

Only the four actual XF8 BF16 cases project onto the 3873-buffer ledger's nine
groups (107 always-clocked root, 3766 common-wake gated). XF4 Q cases and the
MTP1 reset fixture are protocol-only; no XF8 column charge is assigned to them.
The projection prices measured rising-cycle counts into capacitance-cycle and
sampled characterization cycle-equivalent coefficients, not supply power.
The 200um ICG output wire component is separately charged at 29.0852fF nominal
or 58.1704fF guarded per fully active cycle, with old-wire subtraction still null.

Quantitative baseline reconciliation: historical uarch PAIR_W has 83.28mW
clock floor at 1.087GHz from TT0.7V pair measurement. Its embedded tree includes
12.9mW internal, 10.8mW switching and 0.000889mW leakage, reported total23.7mW.
The raw report is pinned separately from the model constants. Switching is not
wire-only: it includes driven pins. Existing endpoints are not added twice.
Within-pair clock charges are already included in pair_power/field_clock_busy;
xnet_energy prices off-pair activation/partial wires and is a separate scope.
Do not subtract this different-context historical tree from a current fullgoal
candidate or add the whole candidate tree atop it. Matching old wire RC/clock
cell inventory/voltage/duty is absent, so wire-only baseline and delta stay null.

Remaining: product full-token scheduling/root duty; matching baseline wire/tree
accounting; actual operating voltage, slew/load interpolation and leakage;
legal simultaneous spatial CTS/PG/escape fit and phase/wake timing; extracted
edge waveform/package/PDN transfer and peak current/IR. Ideal simulation phase
does not qualify the seven-stage root/fourteen-stage gated clock hypothesis.

Replay (no simulator/model rebuild):
  python3 tools/w10_clock_duty_ledger.py --out /home/ubuntu/w10-duty-replay.json
  cmp /home/ubuntu/w10-duty-replay.json results/quality/w10_clock_duty_r1/ledger.json
Focused gate:
  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q tests/test_w10_clock_duty_ledger.py
Six tests include wake, latch-phase and leaf-divergence negative controls.

Optional observer reproduction requires the protected original model objects:
  python3 tools/w10_clock_duty_capture.py --work /home/ubuntu/unique-new-duty-capture
Runs one simulation thread and links observer code only, without Verilating.
Failed first observer link (original main collision) is preserved separately;
it is not a hardware or functional failure. Pinned originals remain unchanged.
