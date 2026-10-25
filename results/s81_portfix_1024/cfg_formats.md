# S81 die-position config + unit fault: formats for the compiler / boot (S81/PORTFIX-CFG, 2026-10-25)

S81 DECISION 3 (D-CFG, option C2) and the eng / iqf part of DECISION 4. The die-position values used to be die-top
inputs: `eng.cfg_en`, `cfg_layer`, `cfg_rank[1:0]` and `iqf.uid[7:0]`. They differ per die in the array, so they
cannot be partition parameters. They are now boot-time host writes, which add 0 lanes and 0 cycles on the token
path. Each unit's `st[3:0]` is now a 1-bit sticky `fault`.

## Ports (die level)

| module | old | new |
|---|---|---|
| `dsdv_eng_rr` (and `dsdv_eng_rr_split`) | ck, rst_n, **cfg_en, cfg_layer, cfg_rank[1:0]**, f_ks[52:0], rco[42:0], pci[267:0], vi_s, vo_s, vi_n, vo_n [275:0], **st[3:0]** | ck, rst_n, f_ks[52:0], rco[42:0], pci[267:0], vi_s, vo_s, vi_n, vo_n [275:0], **fault** |
| `dsdv_idx_qf` | ck, rst, **uid[7:0]**, qs, ql, qr, qc0, qc1 [512:0], **st[3:0]** | ck, rst, qs, ql, qr, qc0, qc1 [512:0], **fault** (param MUT) |

The following are unchanged:
- The hard core `dsdv_eng_rr_e`. It keeps its cfg_* and st pins, and its pin table is unchanged.
- The inner `dsdv_eng_rr_c`.
- `dsdv_idx_bsplit` / `ot_s81sl_slice_iq` ports. Only the type route changes: type 11 now goes to iq.

## 1. eng: CTL "cfg" op on the column-6 V rung

eng's only rung inputs are `s_6S.vo -> vi_s` and `s_6N.vo -> vi_n`. The op is ONE V beat (kind 0, CTL), with the
seq_host / ot_s81sl_xr CTL payload `p = beat[21 +: 186]`:

| bits | field |
|---|---|
| beat[0] | 1 (valid) |
| beat[3:1] | 0 (kind CTL) |
| beat[8:4], [12:9], [20:13] | hops, src, x: ignored |
| p[15:0] = beat[36:21] | slice mask, **must be 0** (no slice acts on it) |
| p[16] = beat[37] | en (1 = Engram home die) |
| p[17] = beat[38] | layer |
| p[19:18] = beat[40:39] | rank |
| p[20] = beat[41] | op CFG = 1 |
| p[28:21] = beat[49:42] | destination unit uid = **0xE6**. This is a fixed RTL constant (`dsdv_eng_cfg` UID): the die has one Engram unit. The BK drain uses 0x5B. |
| p[185:29] | don't care |

The fields sit in p[28:16] because the BK drain layout (uid in p[7:0]) would set slice-mask bits. That layout cannot be
used on column 6, where the far slice would decode it.

**Tapped, not sunk.** The rung pass-through is inside the hard core (2 edges, unchanged). The soft `dsdv_eng_cfg` snoops
both vi pins through its own capture flops.

The beat therefore also reaches the far slice. Its rstop delivers V CTL to xr, which re-injects it on that tier line
both ways (as for every V CTL). Every slice then sees slice mask 0 and ignores it: no action and no xr fault. At boot
the compiler must keep free:
- that rung slot;
- the far slice's ci slot one cycle later;
- the tier-line slots.

XQ / XB continuation fragments are never decoded as headers. Cfg beats on vi_s and vi_n in one cycle are a fault, and
the vi_s one wins.

**Timing.** The register reaches the core's window former 3 edges after the beat's vi pin edge (capture, register,
core pin flop). Send it any time before the first f_ks start. Rewrites are allowed while no window is active.

**Delivery path (TOK-DS).** The beat must leave s_6S or s_6N on its V output.
- Column 6 has no CTL source. Today the only way a slice control plane (`ot_s81sl_xr`) puts a beat with a chosen
  header on V is its **send** path:
  1. A send config (CTL target 4) sets: `s_dir` V; `s_kind` 0; `s_mask` 0; `s_leaf` = {rank[0], layer, en};
     `s_row` = {uid 0xE6, op 1, rank[1]}. Send header: p[15:0] = s_mask, p[18:16] = s_leaf, p[28:19] = s_row.
  2. A leaf lo row-pair burst (any row, s_np + 1 pairs) fires the send.
  3. p[30:29] = s_np and p[31+] = the packed pairs, which eng ignores.
- The control traffic reaches s_6S / s_6N in-band: WN2/WN3 host -> s_0N_LP -> seqhost (0x13 CTL templates + V
  commands) -> s_4N / s_4S -> tier line CTL (slice mask bit of s_6N = sid 13 or s_6S = sid 12).
- The same 186-b payload is also a legal seq_host CTL template, if a later revision gives column 6 a direct CTL feed.

**If missing:**
- en stays 0. The die issues no Engram window (as a non-home die), so the Engram rows of a home die would be missing.
- To make that visible, an f_ks start before any cfg write raises the sticky `fault`. Every die, including non-home
  dies (en = 0), must receive its cfg op once after every reset.

## 2. iqf: CONFIG frame (type 11) on qs

This is one 513-b word {d[511:0], v} on the qs lane `idx__s_3S_C__iqf`:

| bits of d | field |
|---|---|
| [511:508] | 11 (CONFIG). Free in both the index set {4, 8, 10} and the svc q set {1, 2, 3, 7, 9, 12, 13, 14}. |
| [491:480] | len = 0 (header only) |
| [7:0] | uid: this die's rank-tree uid, as `lower_bk.idx_tree_frame` `uids[d]` |
| every other bit | 0 |

**Route.** The frame travels like the IDX_S / tree frames: s_3S xr send on band B, then `dsdv_idx_bsplit` (type 11 now
takes the index route), then the landed lane, then `dsdv_idx_qf.qs`.

**Consumed.** qf loads the uid register (reset 0) and sets its configured flag. The word goes to no output:
- not qr (reader chain);
- not qc0 / qc1 (a child die must not take its parent's uid).

Its stage-2 slot leaves those outputs idle. Their data bits are not cleared, which is harmless because every receiver
qualifies data with valid. A CONFIG frame with len != 0 is a bad frame: fault, and its payload words are consumed too.

**Timing.** Send it at least 3 edges before the first tree frame (type 10) of the die: uid register, then kept
compare copies. It can be sent any time between frames.

**If missing:** uid = 0, so the die would take the spec entry of uid 0 (the rank's die 0). A tree frame before any
CONFIG frame therefore raises the sticky `fault`.

## 3. fault (both units)

1-bit sticky, cleared by reset (wavefront leaf). The detailed codes are dropped.

| unit | fault = OR of |
|---|---|
| eng | the core's 4 sticky st conditions {xq, head, lookup (fault, st_bad), window} (one edge after st), f_ks start before cfg, dual cfg beat |
| iqf | the former st conditions {no-entry seen, bad frame (incl. a bad CONFIG frame), collision qs and ql}, tree frame before CONFIG |

## Boot sequence (per die, after the reset wavefront release, before the first token)

1. **iqf CONFIG frame** {11, len 0, uid}: seqhost CTL -> s_3S (send config dir B + the row-pair burst) -> bsplit ->
   `idx__s_3S_C__iqf` -> iqf.
2. **eng cfg op** {en, layer, rank} (en = 0 on non-home dies): seqhost CTL -> s_6S or s_6N send on V -> eng (tapped)
   -> the far slice (re-injected on its tier line with slice mask 0, ignored).
3. Then the first f_ks start / the first tree frame.

Benches (Verilator 5.050, epyc1): `rtl/dsrom_sys/s81_dv/eng/test/run_eng_cfg.sh`,
`rtl/dsrom_sys/s81_dv/idx/test/run_idx_qf.sh`, `tools/s81_dv/eng_rr/bench_rr_snapshot.sh` (base / cfg1 / cfg2 / sref),
`tools/s81_dv/eng_rr/bench_rr_split.sh`.
