# KV CTL mu2 native audit, 2026-10-19

The CLOSED record `65eda958f` is historical evidence. It does not qualify the current multi-user KV control tile. Import its 29 record files only; preserve canonical source and tools. No production source, view binding, route or geometry was changed by this audit.

## Independent result

The source-pinned route is `claude/kv-ctl-1019@9105d74edde715ab586cd2c40dcbc16d6fb95b80`, job `qkd_kvs_ctl_mu2-mu2-9105d74ed`, EPYC8 `/srv/opentallas-scratch/claude/closure-loop/qkd_kvs_ctl_mu2-mu2-9105d74ed`. Routed TT setup +24.38 ps, FF hold +8.88 ps, DRC 0 pass the timing/DRC rule; SS -295.24 ps is sensitivity only.

A fresh current-tool native audit of the exact recorded ETMs and insertion file FAILS. Fleet unit `oth-ubuntu-1712437-1792428741`, unpinned ot-run, completed exit 1. Native launch is 252.9 ps at `o_hroot_ES[175]` (97 outputs exceed 220 ps); capture is 213.8 ps at `boot__boot_image_target[1]` (48 inputs exceed 190 ps); there are zero combinational I/O pins. Actual routed SPEF boundary clock spread is TT 121.8 ps and FF 109.3 ps, each above 80 ps. Reference means are TT 513.6 ps and FF 421.5 ps; insertion magnitude alone is not a rejection. These are intrinsic native results; no current parent compensation is claimed.

`native.json` is the unmodified fresh audit output. Tools were taken from the audit branch based on current origin/main. The remote scratch root is `/srv/opentallas-scratch/claude/codex-kv-ctl-native-1019`; immutable original run files were read only.

## Source and schedule mismatch

`source_contract.json` extracts exact top-instance module names and parameters from mu2, current GEN7, mu4_safe and current main. Mu2 uses single-context `qkd_static_kv_boot_dispatch(SRQ=2)`, `qkd_static_kv_layer_programme`, and `qkd_static_kv_ownership_calendar(PIPE=1)`. Current GEN7 uses all three `_mu` successors with MU=1. The ownership successor permits overlapping token-window re-arms; mu2's single-window behavior cannot substitute for it.

Mu2 pin registers add one clock on every input/output crossing. Its two-stage reset landing has no distributed reset-copy declaration. SRQ=2 adds two setup-ready clocks and PIPE=1 requires one extra quiet clock before ownership enter/leave. Mu4_safe has a different registered guard, four retained halt copies, and reset-copy structure; its additional guard observation clock must be priced independently. No ages are normalized to make these sources agree.

The original source's preliminary `cl/fplint/route.a1/textbook_lint.json` is preserved verbatim. It reports reset loads 2063/756/409 and a source phase register with 1033 loads, plus 29,677 flops and 18,171 um² standard-cell area. This is a preliminary mapped snapshot, not a final buffer-collapsed routed fanout census. A new exact final census would be required before qualifying this source. Clock-root sink count by itself is not a rejection.

## Actual parent geometry

GEN7 `4db097403` at EPYC5 `/srv/opentallas-scratch/claude/qwen-kvsys/kvs14r-4db097403-codexmub` correctly reports CTL ASSUMED, with no committed closed view considered at its source snapshot. Its actual `case_kv/elements.lef` master is **1123.176 x 172.776 um**, and `place.tcl` places `kvs_ctl` at **(6176.736, 26092.800), R0**. The routed mu2 view is **475.2 x 475.2 um**. It exceeds the available frame height by 302.424 um, so direct replacement fails the slot contract. Rotation also fails that height. No coordinate rebinding or overlap-free placement was claimed.

## Focused integration proposal

1. Keep mu2 as a record-only historical route. Do not alias it to the current MU source, overwrite the current generator, or export it as a qualified native release view.
2. Preserve the live `e00f75155` mu4_safe gate at EPYC5 `ref_gate/qkd_kvs_ctl_mu4_safe-20261019-080131`; collect that exact original writer when terminal. No duplicate gate was launched.
3. For the production successor, first reconcile exact MU wrappers and SAFE guard/reset parameters with the generator and source contract. Require retained mapped control/reset fanout, local clock ownership and measured TT/FF spread, and native launch/capture against the actual neighboring boundary.
4. Model and review an actual parent slot for the production tile before replacing the 172.776 um frame. Rebuild native pin coordinates, parent geometry and clock/reset graph from that source; prove <=405 um physical wires or explicit landed hops, no overlaps, and real pin access.
5. Re-derive every changed control crossing, reset-release age, quiet-window guard and compiled calendar from actual instance/bit paths; rerun effective-age/phase and strict native bind. No blanket data-path masks, timing uncertainty changes, or new SS threshold.

The actionable next step is original mu4 collection plus a fresh physical-source/parent-layout owner. This audit introduces no RTL variant or unreviewed geometry.
