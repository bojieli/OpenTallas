Current tload protocol profiles at 833ps (2026-11-01)

Source bodies are unchanged CURRENT b1a2125433d0ace1b6027f726fe53d1000cad241:
qfd_dv_slice_tload, qfd_dv_table_rom_loader and actual qfd_dv_vm.
Both profiles use real aligned-v2 ROM/SRAM functional models. No new source
parameter, REGISTERED_JOIN parameter, TABLE_USER_RELOC or RTL default is added.

                       VM first/last commit after request    stream delay
CAPTURE_STAGE0/LOCAL_JOIN0          +5 / +92                     0
CAPTURE_STAGE1/LOCAL_JOIN1          +6 / +93                     0
1/1 + metadata Option-A boundary   +8 / +95                     2

The last row adds one register on every input and output and two pure
reset-copy registers, exactly as the supplied port-latency contract states.
It is a timing-contract wrapper, NOT proof that an archived physical view
matches the current source. Physical Option A therefore needs TWO boundary
edges beyond the measured body1/1 delta, plus its separate reset+2 contract.
Compared with the current0/0 body: +3 table edges, +2 stream edges.

Each profile checks 352 exact write edges (stages1/2, users0/1), 1500 actual
VM readbacks including retained user data and shared-head sentinel. The
ROM capture metadata mutant and request phase mutant both fail slot0.
Request edge, output-visible edge and actual VM write-sampling edge are
recorded separately in the logs and receipt; output visibility is one edge
before VM commit. All functional profiles and both controls passed their
expected gates; ot-run unit2305340 exit0 on epyc2.

Fixture: committed NONEMPTY compact table manifest from ns4 source
b8e6c6f863fcda1c73be9211a0a47528e3b82055, 12672 valid/nonzero payload rows.
An independent inverse of physical ROM mask indexing builds the oracle.
This qualifies the loader/join/VM mechanism only. It does NOT qualify the
selected current programme: the inspected 59P table_s0 masks were all zero.
The archived programme_store_fixture.py is fixture code, not adopted logic.

Replay from repo root (run through ot-run, 8GB/2threads):
  bash rtl/test/qwen_dv/run_tload_profiles_1131.sh OUTDIR
