# S81 real field partials into the physical gather root

The `--native-gather-root` field vehicle connects the actual ROM elements and
return tree to `ot_s81ph_ret_root_p`, the arithmetic root used by the physical
S81 gather. `EXTERNAL_ROOTS=1` removes the former final root from the field;
`tree_return` carries actual 66-bit `{error,data,tag,valid}` packets. No golden
partial or result is supplied to this connection.

Build with `tools/dsrom_1m_field.py build --qelem 10 --native-gather-root --work W`.
Existing `field_all.py` plans/images retain the released 1,792 binding and real
checkpoint weights. The component's operands are declared fixture inputs. Its
VM remains the field vehicle's ideal model. This component result does **not**
qualify native memory service, physical lane/CDC timing, a complete layer, or a
token. The new source cut enables that integration; it does not certify it.

Native-root runs supply an explicit seventh OPS column: compiled issue cycle
1. An unavailable reserved resource or a missed issue cycle fails the driver;
it never waits for readiness to move the scheduled issue. Completion is still
measured, to provide an input to the full static compiler schedule.

The four-state `tb_field_fault_tail.sv` test checks only fault fan-in wiring.
It neutralizes valid arithmetic fault sources and proves all unused forest bits
are driven at R=1,2,4. The former single-tail driver fails at R=2 and R=4.
Missing arithmetic children in that wiring test are intentional, and its PASS
is never arithmetic or native-completeness evidence.

## Remaining native integration

`tb_s81_die_layer` currently drives random field partials produced by
`gen_stim.phase`; its all-reduce inputs are independent partitions of the
reference output. It cannot become a native continuous layer by simply changing
one root file. The compiler must jointly allocate actual field destinations,
SU typed operands, HC operands, and collective inputs, and preserve real
producer ownership through scheduled VM accesses.

The actual capture writes 16 32-bit words per 512-bit row. For BF16 field
outputs it rounds to BF16 and widens back to `{bf16,16'b0}`. This agrees with the
SU FP32-shaped input rows; it is distinct from HC H landing's 32 packed BF16
values per row. Root/output permutations for bank-local capture must also be
applied when generating the production ROM images.

## Observed component evidence

All 21 L0/rank-0 field phases passed through the physical gather arithmetic
root: 2,608 full-shape region cases and 32,928 exact row words. Coverage is
6 FP8 phases (16,192 words), 3 BF16 phases (2,144 words), and 12 FP4 phases
(14,592 words). Every case issued at compiled cycle 1. The actual RTL
`CH_MUTANT_PD` forward-swap mutant failed all 6 a-projection words in region 0.
Empty programs, issue cycle 0, and a second issue scheduled before the first
phase completed all failed the driver explicitly.

For the same six-word a-projection image, the physical root writes at cycles
416..421 and becomes idle at 422, versus cycles 405..410 and idle 411 with the
historical root. That is 11 added cycles at this component boundary. It is
neither an end-to-end token-cost measurement nor a new accepted cost; the
compiler must check whether existing physical gather pricing already includes
these stages before accounting for them.

`cases.jsonl.gz` preserves every case's actual and expected words. `report.json`
records source/binary/input identities, the actual RTL mutant, negative driver
checks, coverage, and explicit qualification limits. The nominal R=1 binary
was compiled before the unused-fault-tail generalization; its R=1 fault driver
is logically identical. The final multi-region correction is independently
checked by the four-state test and its observed failing old-driver mutant.
