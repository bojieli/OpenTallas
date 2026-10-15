S81 F11 CN / IK native arithmetic and shared KV integration
==========================================================

Implementation: d67d13758, following the owner requirements for all on-chip
hardware and fixed compiler scheduling. Production CN/IK reuse the actual64
existing KV norm/RoPE eight-lane engines; no second norm512 cluster is placed.
The `ot_s81_su_cn_ik` module itself is the arithmetic test composition, not a
second die master. The production joins are in `dsfd_sp_su_h`.

CN(kind12): GK gain set3,512 operands, norm512, RoPE last64, FP4 E4M3 block16.
It writes16 BF16 QDQ rows,16 original codes/scales rows, and16 PRE-RoPE norm rows
for the actual `cmp.wk` field producer. Norm data comes from the real registered
KVE scale operand. Descriptor word2 is norm_base; word3 is eps.
IK(kind13): GK gain set0, logical128 mapped to physical384..511 with zero prefix.
The dedicated canonical128-element reduction reads only those16 actual chunks
and divides by128, not512. It writes4 QDQ and4 raw-code/UE8M0 rows.
Raw rows retain original quant decisions; QDQ is never re-quantized to recreate
codes. Each raw row stores32 E2M1 nibbles in bits0..127; CN has two E4M3 scale
bytes at128 and136, IK has one UE8M0 byte at128 and zero byte at136.
All unused raw-row bits are explicitly written zero.

Evidence:
- Actual synthesizable RTL floating-point primitives, no DPI: CN512 QDQ512words
  plus16 raw blocks PASS; IK128 QDQ128words plus4 raw blocks PASS.
- Removed sine branch mutants FAIL59(CN) and52(IK) combined checks. See source-
  pinned result.json/result_mut.json and run logs in each native directory.
- Full-shape actual descriptor/control/VM interface composition with diagnostic
  DPI arithmetic: an18-job program covering existing classes, including T133, PASS2413rows;
  twelve-job KV/CN/IK gain-epoch interleave PASS162rows, no faults or early done.
  This diagnostic is explicitly NOT an all-RTL native full-layer receipt.
- Shared job measurement before adding the standalone-only raw observation
  port: GK66/67cycles, CN305cycles for48writes, IK304cycles for8writes. The
  interleave receipt records each actual start/done for the final shared RTL.

`su_gate.py` now validates a source-bound build cache before reusing a binary;
changed RTL or generated sources cannot be paired with a stale executable and
freshly computed hashes. Source changes during a build/run fail closed.

Remaining qualification:
- S-FUNC owns source-pinned real snapshot lowering and unified native allocation.
- S-DIE / native physical join owner assign norm export pins, new quant/norm
  writers, IK reduction children and their clock/reset roots. Old CLOSED views
  cannot represent the modified KVE/KVT interfaces or added arithmetic.
- Quant root sink counts/areas, assigned outlines, TT setup/FF hold/DRC, real
  SRAM service, compiled visibility cycles and end-to-end contention/cost remain
  unqualified. The analytical model intentionally marks route_admissible=false.
- Flat historical SU wrapper does not accept CN/IK. The production hierarchical
  implementation is the native target; no flat-reference substitution is allowed.
- CP, index query RoPE/quant, new-key state and candidate-final native paths are
  separate still-open operations with dedicated owners. They are not CN/IK aliases.

Explicit CN/IK leaf clock join
------------------------------
The production parent exposes39 scalar leaf entries through ck_cn[19:0],
ck_cnnw[15:0],ck_ikh[1:0],ck_ikr and matching reset entries when compiled with
OT_S81_NATIVE_LEAF_CLOCKS. Actual hardened boundary wrappers from be48e6985
replace the raw helper instances. Historical no-flag clocking is diagnostic.
The explicit-clock bench repeats the2413-row stress and162-row interleave with
identical cycles and zero faults/early completion. native_leaf_clock_build.json
binds that macro flag to the compiled source set; native_leaf_clocks.json is
the matching result. Arithmetic remains DPI in this interface composition;
physical phi-R delivery, pins and timing remain the die/physical owner gate.
