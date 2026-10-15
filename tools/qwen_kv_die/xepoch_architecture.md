TP8 x-issue stream candidate: 32 cyclic roots and epoch replay
============================================================

This candidate replaces the single-snapshot protocol; it is not yet a
production ME/token proof or a physical release.

Source audit: ot_qwen_w12_matvec.sv consumes xbase+c*xcs+k*xks+j*xjs on each
active issue edge. ROM projections in hdc_program.me use xks=1,xjs=0 and
therefore repeat the same four x operands for all eight j slots of one k.
Native TP8 (3072 groups, TP8 shapes, emitter rtl_split policy):

 op    split   kc  rounds  issue edges  distinct quads/k  local cache bytes
 qkv      9     8    1          64            128               128
 o        8     2    3          48             64                32
 gu       7    32    1         256             32               512
 down     8     6    3         144             64                96
 head     9     8   25        1600            128               128

These are source-derived profiles, not measured native token cycles. Actual
emitted TP4 qF operands were read from EPYC1tb img_p1/L0-d0/program.hex and
show changing xks for every ME instruction and xjs!=0 on attention products.
Attention is on the near-HBM engines of the merged die; this cache cannot be
used for arbitrary xjs!=0 instructions without additional epoch scheduling.
No assertion that the full array's legal instruction space is covered.

VM source:32 fixed root streams,128 data bits each =4096 aggregate data bits.
Cyclic addressing root r, phase p => quad=32*p+r, masked by split replication.
SMAX9 needs4 phases per k; SMAX8 needs2; SMAX7 needs1. Each physical tile
uses root tile_id%32, selects its source phase from tile_id masked to split.
This root assignment does not depend on split. Root IDs must be attached to
the authoritative tile_id straps, currently missing in die generator output.

Native streaming schedule: launch each k's phases at k*8+p; example band
latency23 gives first data at23 and all four phases at26. Start tile issue
at27. Pingpong cache loads k+1 while all eight j slots consume k. Read lookup
returns data one edge later; core operand pipeline must align with this read
latency. Cache tags reject stale epochs and overwrite/read collisions.
Measured standalone issue-schedule bench:768 tiles,32 k epochs,8 j reads,
196608 replay edges,27-edge initial preparation, zero issue bubbles, and
stale-bank mutant rejected. The 23-edge path is a conservative test fixture,
not a measured routed VM path. Actual path padding and core IREG/ME_EXTRA
alignment remain to prove with the production matvec bench.

SMAX11 has16 phases with32 roots and cannot sustain a fresh k each8edges.
Full-preload mode (DEPTH64) demonstrates functional storage/replay for64
k epochs after1024 load edges;512 reads then replay with no issue bubbles.
That bounded fixture does not prove all legal i_k values or all xjs patterns.
The wider supported contract must be checked against immutable production
programs; widening to64/128 or fully parallel roots remains necessary if
those programs require continuous split>9 or j-varying operands. Do not
reduce SMAX or ignore unsupported legal issue streams to pass qualification.

Cache leaf: DEPTH2 approximately256 data+32 tag+2 valid+130 output/control
flops. DEPTH64 approximately8192 data+1024 tag+64 valid+130 output/control
flops, below15000 sinks, but no CTS evidence yet. Use a separate leaf rather
than adding9k flops to an already14k-flop ctl clock root. Parent stays wires
only. Core exposes local x read timing/epoch to cache and takes the response
through its memory alignment path. Reset invalidates every cache entry. Pulse clear before each new instruction
preload (before its first LOAD) to invalidate prior instruction entries;
clear suppresses both loading and reading on its edge. Epoch tags must travel
with the packet rather than being inferred from an unqualified local cycle.

Physical lower bounds for32 roots (exclude clock/reset/credit/epoch, tree):
  VM source data:4096bits; shared phase4+epoch16+valid adds21bits.
  Per root output:128data+phase4+epoch16+valid=149bits, total4768.
  Per root ready credit adds32bits against flow if implemented.
  Each half needs all32cyclic streams: sources may fork into W/E branches,
  giving64 physical half-root endpoints and8192data bits summed across the
  two branches. The source pin count is4096 only if the fork is on the die;
  two independent band output copies require8192pins.
  Tile load pins:128data+epoch16+valid=145bits.
  Cache lookup pins:epoch16+readvalid=17in, q128+qvalid+fault=130out.
At two48nm tracks per bit (96nm bit pitch),4096bits need393.216um along-face aggregate;
4768bits need457.728um (single layer). These are aggregate necessary bounds,
not legal face assignments. Each source root has24 tile consumers (12 per half) throughout
48columns x16rows; per-root fanout/relay register geometry and the existing
508bit instruction corridor must be planned before route. A total VM
boundary vector is not a license to add4768pins to one52um station master.

Performance release must measure native layer end to end. Even a27-edge
startup repeated over four ROM ops adds108 modeled edges; it cannot be
accepted solely by comparing a constituent to a guessed1170-cycle baseline.
Prefetch can hide this only if VM operands are already committed before
compute, with an exact producer/consumer chase proof. The next gate is full
matvec/cache lockstep, actual VM/die path depths, and native layer/tokens.
