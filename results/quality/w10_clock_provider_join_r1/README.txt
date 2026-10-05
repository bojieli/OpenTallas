W10 clock accounting joined to Godel's actual W17 provider requirements

Provider4ad1baf66, actual runtime76ffc2aa0, clock source contract850d9c79b.
Ten immutable objects (requirements, contract and eight actual source files)
are hashed. Requirements' eight source hashes are independently checked.
Four current tops have zero PG-controller instances.

CFG/GO/BEAT/DRAIN have partial source signal identities, not qualified connected
hardware events. OUTPUTCREDIT and PREWAKE are unbound. All six event-provider
classes are incomplete, and all nine required model fields remain null.

Actual source cone:
  spine ready = st == S_IDLE is GO admission, not return/VM write ready;
  rows_left counts returned r_v, not acknowledged consumer completion;
  r_v drives registered w_we, but no r_ready/r_credit/w_ack/w_ready port exists;
  return quiet is runtime-only under V41_RT; the hardware branch ties it low;
  host RT_SKIP/pair_skip/node_skip only avoid software evaluation.
Neither arrival, write-enable, host quiet nor component PG PASS grants physical
root-stop or consumer-completion credit.
Persistent KV/state retention or its priced protocol is also required; stage
power/reset sequencing must not discard the current token's state.

Direct coordination acknowledged by Godel01a0f697-9bf5-7840-bd23-58a583e983fd:
Godel retains actual consumer ack or fixed-rate reservation/outstanding-write
and producer/router prewake ownership; Ram retains integer/model schedule join;
physical owner retains clock accounting; sole root reviewer owns spatial PG and
macro escape fit. No actual provider RTL change or duplicate waveform/build.

Root107 and gated3766 buffer accounting remains separate. Credited root-stop
cycles are0 while providers are incomplete; actual root-stop waveform and power
reduction remain null. This refuses unbound savings; it does not declare actual
full-token source-clock activity. Previous TT baseline/endpoint terms are not
added or subtracted again. Voltage, slew/load, physical phase, whole-token duty,
power, peak current and IR remain null; adoption/physical admission false.

Reproduction:
  python3 tools/w10_clock_provider_join.py --out /home/ubuntu/w10-provider-join.json
  cmp /home/ubuntu/w10-provider-join.json results/quality/w10_clock_provider_join_r1/join.json
  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q tests/test_w10_clock_provider_join.py

Five focused tests include fake-ready metadata, host skip/quiet/componentPASS,
signal-identity conflation and independently missing credit/prewake controls.
No RTL/source pins altered, no new hardware jobs or leases. Need model-priced
source-bound completion/prewake providers before RTL; full spatial PG/clock fit
before heavy admission; actual waveform/RC/rail/energy before power/IR signoff.
