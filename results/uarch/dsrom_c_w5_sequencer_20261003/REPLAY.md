W5 ROM sequencer source milestone — candidate CLOSED, NOT ADOPTED

The owner requires at least 1% composed single-user gain. That gain cannot be
established from the selected sources: production calendar/debt binding,
off-rail leakage, switch/standby characterization, wake energy, inrush grants,
clock-region crossings and physical context remain unqualified. This candidate
is closed; it does not request another broad study or optimization validation.

`ot_dsrom_c_w5_core_v41x` is an isolated successor of the actual V4.1 core in
`source.json`. `tools/dsrom_c_w5_bind_sequencer.py` verifies the pinned SHA and
reverses every transformation to prove no unrelated engine/numerical edits.
The released core and die are unchanged. This successor is not installed in
the production die. All W5 implementation lives in the new W5 namespace.

The default W5_ENABLE_PG=0 preserves the original start, token, position and
entry paths, clock and arithmetic. Enabling it gates actual S_IDLE admission,
the acceptor's start and fault clearing. It retains a delayed start packet in
AON registers and counts every wait edge. A second start faults rather than
overwriting the packet. Parity protects pending state, payload, latency debit
and sticky fault. Faults halt the actual sequencer in S_COLL_HALT.

Control and Engram stay AON. Power/clock/isolation intents address the ROM
field group; they must never gate the sequencer/Engram or an HA service. The
low-phase latch clock gate is usable digital RTL, but physical ICG mapping and
CTS remain unqualified. The existing W5 isolation clamp must be instantiated
outside each switched field interface. This milestone does not fabricate a
power switch, analog ramp or droop guarantee. W_HBM=1 with W5 enabled faults
at elaboration/simulation: HA integration belongs to Claude. KV/HBM protection
and service controls are not changed by this ROM field admission component.

Sleep requires actual sequencer idle, all five units idle, window idle,
collective idle and all eight retained debt classes known and clear. The
production debt packet defines the classes: ingress, node queues/pipelines,
root queues/held entries, every adder stage, result/write/consumer visibility,
identity/CDC/ack/replay/link obligations. A missing known bit is live debt.
Debt inputs must stay live in retention/AON through power cycling; never
clear them on a field reset or tie known high on an unbound signal. The actual
W2 calendar and these production exports are not bound in this milestone.
No fixture topology stands in for production neighbors. Neighbor prewake is
the externally synchronized actual edge signal, not stage ID plus one.
RD64/ROOTD128 remain the qualified cost; rejected RD4 yields no free credit.

Use w5_start_ready to admit a pulse. Token/pos/entry are the start-latched
packet; all other existing core configuration inputs retain their original
stability contracts. rst_n is the cold AON/system reset, not a field reset.
Rail/relock loss while executing faults and halts, rather than treating wake
as restoration of lost work. Externally held debt must survive recovery.

Price w5_total_cycles (33-bit engine cycles + measured W5 wait cycles), not
the original engine-only cycles output. Convert with the actual sequencer
clock. No 1.2 GHz/0.9 GHz crossing or CDC credit is assumed. The new component
test measures zero added cycles for an already-ready start and eight for its
particular delayed-grant case; neither is a production latency guarantee.

The prebuild reservation was 106 FF bits; generic synthesis measures 105 FF
bits and 1026 generic cells including PG control and retained admission.
The existing source-pinned Liberty palette prices a conservative NAND/INV
construction at 623.20752 um2 and 13.376376816 uW SS on-rail leakage per
controller/admission instance. These are modeled allocations, not mapped
area, actual activity power, off-rail savings or contextual SS/FF evidence.
Clamp, switch, retained external debt, clock gate/CTS, CDC, routing, fanout,
PDN and SerDes costs remain outside that construction and prevent adoption.

Reproduce the generated source and model from this branch:

```sh
python3 tools/dsrom_c_w5_bind_sequencer.py
python3 tools/dsrom_c_w5_sequencer_price.py
iverilog -g2012 -s tb_dsrom_c_w5_seq_gate -o /tmp/w5-seq.vvp \
  rtl/v41rom/ot_dsrom_c_w5_pg.sv \
  rtl/v41rom/ot_dsrom_c_w5_seq_gate.sv rtl/test/tb_dsrom_c_w5_seq_gate.sv
vvp /tmp/w5-seq.vvp
```

The simulation checks admission, held metadata, wait debit, actual-busy
interface, live/unknown debt, default-off equivalence at that interface,
overflow, retained-state protection, rail-loss faults, glitch-free digital
clock pulses and Engram AON. It does not execute the full accelerator.
Actual core lint uses pinned rtl/hdc and rtl/proto from source.json's commit,
the real Engram package, fastfp, sfu, fpu and sk_arith source units, with
Verilator 5.050. Default ROM parameters are checked; no HA build is launched.
Earlier failed lint/tool invocations are retained, not overwritten. No
complete-token exactness, production latency or SS/FF closure is claimed.

Claude owns all HA0–HA10. Historical HBM-related references found during the
previous source intake are in the separate Claude handoff JSON; W5 builds
none of them. Clock-region composition must keep W5 waits and crossing/CTS
costs explicit and must not use this closed candidate as free gating credit.
