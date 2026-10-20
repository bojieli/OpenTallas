Bounded reducer successor: concrete control/storage piece, arithmetic pending

Model committed b8321fb7d BEFORE RTL. New opt-in module
rtl/qwen_dv/s5/qfd_dv_s5_red_ring32.sv is independent of existing reducers.
It retains delay age D: data-copy edge + D-2 circular slots + output edge.
It rejects logical bank stores >2048bits, requires D3..51 and W1..283. This
is a reusable component, not a new qualified hard reducer master.

Why this structure: redb mapped ring pointer/control fanout exceeds32. Each
new eight-bit slice has a distinct kept onehot phase. A phase drives at most
8 write controls +8 read gates +1 next phase. Inputs capture once per16 bank
slots, using an existing delay edge, so each captured bit drives <=16 slots.
Balanced OR selection avoids a linear depth proportional to D. Phase resets
use the existing registered32-ary reset tree; each leaf serves<=32 phase bits.
All slice/capture modules retain hierarchy and unique parameter identity.

Fleet Verilator5.050: positive5shapes W283D6/W26D49/W32D42/W32D3/W1D7 PASS
across two reset epochs, >900 comparisons each. Actual age-bypass mutant FAIL
W32D3 cycle19. Both build/run logs committed. Reset propagation has two local
edges; outputs are meaningful after D fill edges plus local reset propagation.
No steady-state latency added; upstream valid must suppress startup outputs.

Fleet Yosys generic ABC mapped recursive primitive-pin census: W283D6,
W26D49,W32D42 all maximum32, zero violations. Clock ck is the only excluded
net; resets, enables, comb drivers and input nets are counted. Hierarchical
module port aliases are unified recursively, rather than counting only local
module connections. The JSON diagnostics include all violating nets.
This is a generic mapped census, NOT ASAP7 technology-mapped signoff. Mapped
netlists/logs remain in the manifest's fleet run directory; census/logs committed.

Safe checklist for THIS HELPER
1 Data input/output PASS source: direct input capture and output register.
  reset_i explicitly expects an already landed caller reset. Whole master pending.
2 Reach PENDING: no physical placement. Must stay<=405um.
3 Generic mapped fanout PASS <=32; ASAP7 native mapped census PENDING.
4 Balanced read structure exists; technology depth measurement PENDING.
5 Each logical bank<=2048b, ring instead of shift chain, capacity trap present.
6 Outline/area/pin density PENDING; no layout kit created.
7 Regional clock/hold/spread PENDING; no timing claims.
8 Data age unchangedD; local reset propagation+2 declared. No global adoption.

Arithmetic next step: reuse fixed generated qfd_dv_station_add_data_g (LAT7)
and qfd_dv_station_mul_data_g (LAT6), not arbitrary LAT padding. Existing
qfd_dv_station_math_g.sv preserves arithmetic bit/order and internal identities.
Baseline reducer LM3/LA3 -> LM6/LA7 costs +47 edges per reduction result:
3 squaring +7*4 csum8 steps +4*4 temporal tree. Replace EVERY aligned data,
max selection, tag, valid and fault path consistently; max bypass must have
same age as SUM. W26D49 is the new chain tag age; W32D42 is lane7 skew.
Before RTL adoption parent must supply critical reduction count per layer;
price =47*count edges/layer with exact overlap accounted. Current count unknown,
so arithmetic is a proposal and full reducer remains gate-blocked.

Next integration work: new separately named red core/master with bounded
arithmetic, consume reset leaves at<=32 actual pins, independently kept copies
of sq/max selects, then smallest age-aware exact reducer bench including II1
segments and specials. Run ASAP7 mapped all-driver census and storage/pin/reach
checks BEFORE the first layout gate. Do not bind current sc/red/scb/redb views.
