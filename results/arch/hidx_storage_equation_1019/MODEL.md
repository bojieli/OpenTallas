# HIDX coupon 4: exact storage projection, MODEL only

Immutable source `5af00a1ab`, index RTL SHA256
`35633c534dbe6236bbbc9074af1e3cf0eb07a2d7e5e6d3b3bee75d0e7652fabf`.
No production RTL, compiler calendar, physical macro, Liberty or gate changes.

The original native `ot_sram_1r1w_64x512_m1_r2c2` is **single-clock OLD**.
Its one posedge process samples `rd_out <= word_read(ra)` before invoking
blocking `word_write(wa,wd,mask)`. Disabled reads hold the previous output;
disabled writes leave all cells unchanged. SRAM has no reset input.
`sram_gen.py` at the same source supports `ports="1r1w"` and generates this
same ordered process for 32x64. The `ports="1r1w2c"` option instead has
separate read/write processes with blocking writes and explicitly relies on
the FIFO avoiding same-slot collisions. Tying its clocks does not establish OLD.

## Exact equations for every source execution

For logical bank b in0..7, source lines397–400 define:

```
f = s4_f0                      // seven bits: total[9:3] sampled
k = (b - f[2:0]) mod8           // three-bit subtraction
fr = zero_extend_8(f) + k       // eight bits, maximum134
we = s4_v && (k < s4_nf)        // nf is four bits
wa = {0, fr[7:3]}
re = em5 && (b/4 == grp5[0])
ra = {000, grp5[3:1]}
```

Thus wa<32 unconditionally, ra<=7. In fact banks0..6 can write exactly
rows0..16, bank7 exactly0..15 over arbitrary source-register states and
enable values. “32 reachable write addresses” in the previous MODEL was
inaccurate: 32 is a conservative capacity. **No further capacity reduction
is proposed.** `equations.json` records exhaustive f,b,nf enumeration.
The registered wa_r preserves the leading zero at every sampling edge;
before its first assignment it is uninitialized, but reset holds we_r=0.
Asynchronous reset at an edge still preserves the same original enable
semantics; this projection changes neither reset nor enables.

No legal-program assumption, selected_count<=512 assumption, fault-free
control assumption or no-wrap assumption is used. Total is ten-bit modulo
arithmetic; overflow sets sticky fault but does not suppress SRAM writes.
Even arbitrary f/nf values have the same bound. Clear/reset do not erase
SRAM contents. An already registered write can commit on the reset edge in
the original; the projection must do the same, never add reset gating.

For each bank wd[0:287]=wd_r, wd[288:511]=0; mask[0:511]=1.
All read consumers use only low288 bits: flit formatting and local emit
selection never reference rd[288:511]. Row/column repair enable and address
ports are hardwired zero. Therefore normal execution has identity repair
mapping. Ignoring upper224 does not assume their initial contents are zero.
Upper224 are unobservable and are not read as fault state or metadata.

## State relation and inductive proof

Relate original M64x512 and five candidate M32x64 slices by
`C[s][a][j] = M[a][64*s+j]` for a<32 and64*s+j<288.
Relate their registered read outputs on these same bits. Other original
rows, upper bits, spare cells, and candidate pad bits are unconstrained.
At an edge, read takes pre-edge related cells if re, otherwise related
previous q; write then replaces the same related bit if we and mask.
Every other related cell holds. This establishes the relation for any
input sequence by induction, including collisions, wrap, fault_c=1,
clear/write/read overlap and reset. The independently coded Boolean
transition check exhausts128 cases (old/data/mask/we/re/same/held-q).
Equal simulation-zero initialization establishes its base; arbitrary
silicon startup requires related arbitrary initial low288 state, rather
than an invented guaranteed zero. Read q is compared after the first
enabled read; neither macro initializes q.

This is a source-equation proof, not a machine formal theorem about the
complete indexer. Numerical primitive comparison uses the actual immutable
original Verilog and five behavioral models emitted by its exact generator.
Directed alias/bit287/OLD/disabled-read witnesses precede2000 randomized
read/write edges. Four causal mutants drop address bit4, drop useful bit287,
return NEW on collision, and read while disabled. Full288-bit useful
payload preservation includes slot7's id bits, not merely scores.

## Explicit proof limits

Physical `OT_MEM_FAULTS` injection equivalence is **REFUSED**. Fault mappings
can alias removed rows or couple an upper224 cell to a useful low288 cell;
the smaller store cannot reproduce every such physical injected fault.
The sticky indexer fault output and illegal functional input behavior are
covered by the projection; arbitrary injected physical fault universes are
different. Nonzero repair settings are likewise outside this source-bound
proof, since this top hardwires them disabled. No ECC removal is proposed.
No four-state uninitialized-control equivalence claim is made before reset.

## Real storage options, pending physical qualification

*40 banks*: five32x64 genuine single-clock1R1W OLD slices per logical bank;
one read and one write per slice per edge, exact same enables and addresses,
288 useful plus32 padding bits per logical word. 81920 physical capacity
bits;40 native clock contacts. No external read mux, depth selector, extra
edge or bypass required for function. Its pad write values are zero.

*80 banks*: retain full64 address capacity using two32-row halves and five
width slices per logical bank;163840 capacity bits,80 single-clock clock
contacts. Write-half decode and read-half selection must use the correct
sampled address. Read-half FF updates only on enabled reads, preserving
disabled q; both halves' OLD semantics remain mandatory. This is a MODEL
option; no full80-bank RTL implementation is claimed here. A dual-clock
variant would have80/160 clock contacts respectively and fails this OLD
qualification unless a separate exact collision implementation is proved.

The generator-produced slice is a **behavioral source-equation artifact**,
never a replacement physical macro or production proxy. Current SC2 still
has no accepted Liberty/min-CQ contract; current dual-clock behavior is
not adopted. Area, physical contacts/PG/OBS, real clock capacitance,
setup/hold/earliest CQ, access timing, parent fit and clock-region costs
remain NULL. No macro swap, resynthesis or route is authorized by this proof.
