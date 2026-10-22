# Forwarded lane clock source: source fix proposal, not activated

The frozen generator's final clock-name pass selects `ck` before `ck_s`. A single FIRST landing has both: `ck_s` writes the source ring and `ck` reads it in the destination domain. Consequently 58 of the 154 frozen GEN0 lanes have a wrong **source clock label**. The actual clock wiring is not changed by this proposal.

`check.py` extracts and executes only the exact source helper AST, not the die generator. It reproduces all 154 original manifest rows, then checks 308 source/destination clock comparisons against the retained real GEN constructor ports. The proposed source function passes all 308; all data source-owner clocks also agree. Three FIRST data lanes share one clock already and keep their labels. The 58 exact affected lane IDs and old/proposed clocks are in `analysis.json`. The wrong-label set includes link slots/valid/payload, SYSFACE PW and embedding/status bundles, XPF/VM boundaries, collective return and native embedding code/scale ports; it is not limited to TT PW.

## Source ownership and construction

Frozen generator `tools/qwen_rom_fulldie_b3r2.py` at source0d4c:

- `_fwd_clock` (around4218) derives producer/receiver clocks from model clock-trunk endpoints, preferring the block's `ck`, then `clk`.
- Lane creation (around4295) records those initial clocks. Constructor kind selection (around4333) chooses `landh0` for a one-frame non-reset lane, `rlyh0` for the first frame of a longer lane, and `landh` for its final frame.
- Clock construction (around4376) attaches hop0 `ck` or FIRST `ck_s` to the source clock and records `ck_follow` ownership to the sender. Landing `ck` attaches to the destination clock and follows its receiver. Reset lanes use separate rlyr0/rlyrl cases.
- After final placement refile (around1144), `_gen16_clock_refile` honors those ownership relations. `_gen16_fwd_ck_names` then reconstructs the labels from final actual endpoint nets, but its `ck`-first lookup overwrites every cross-domain FIRST source label with the destination clock.

`generator.PROPOSAL.patch` is the smallest frozen-source fix: prefer `ck_s` if present, then `ck`. It does not edit generated annotations. No RTL, placement, clocks, resets, profile, programme or lane ages change.

## Current source divergence matters

Read-only observed `origin/main` was `aae57a4e3e0cccf45d98358e41fa8129b9abdaa8` at15:09 PT. It has **neither** `_gen16_fwd_ck_names` **nor** `_gen16_clock_refile`/`ck_follow`. The local `main` ref was stale and was not substituted for it. Full source snapshots and hashes are retained; no fetch/rebase or main write occurred.

Therefore the one-line frozen patch must not be blindly cherry-picked onto current main. `current_main.PROPOSAL.patch` is a separately scoped proposal: add a port-aware metadata finalizer after the existing final region pass. It explicitly selects FIRST source `ck_s`, ordinary hop0/reset `ck`, and landing destination `ck`; missing required clock pins and conflicting driver nets fail closed. `current_main_helper.PROPOSAL.py` exposes exactly that proposed helper for finite checks. This metadata-only proposal does **not** restore the absent GEN16 wiring ownership or certify that current main generates the same clock wiring as the frozen die. A future owner must select the coherent generator source first, then compare actual endpoint ownership before any GEN/build. Do not claim the current-main proposal repairs missing clock construction.

Finite fixtures cover FIRST distinct/equal clocks, multi-hop hop0, single reset, empty lanes, missing source, missing destination and conflicting source clock drivers. The old-source priority mutant causally produces destination as source and is rejected. No simulator, synthesis, OpenROAD or generator run occurred.

## Exact SYSFACE transport and immutable timing scope

Frozen actual `die.v` SHA256 is `7b1bdfc5fd26c2e6f17fe6aa5b1d68bd9e2fa05bc3ecf408b9f163eb600bbde7`, inherited from the retained producer binding packet77dc7db14. `fixture.json` contains actual constructors/ports and all unchanged lane rows, not hand-authored substitutes.

| Route | Actual source and clock pins | Declared model |
|---|---|---|
|TT PW75|SYSFACE `tt_pw` → `rly_sf_tt_pw_0`, qfd_landh0_75; `ck_s=n_clk_d2d`, `ck=n_clk_r54`|one FIRST landing, E1/K3|
|CALR DH187|SYSFACE `seq_dh` → `rly_dvw_sys_face_seq_dh_0`, qfd_rlyh0_187 `ck=n_clk_d2d` → `rly_dvw_sys_face_seq_dh_1`, qfd_landh_187 `ck=n_clk_r54`|one hop0 and one landing, E1/K3|

The TT manifest wrongly says `src_ck=clk_r54`; the DH manifest already says `clk_d2d`. Identical E1/K3 declarations do not establish equal transport age, native phase, or safe first use. These remain NULL. No K/E, station count, reset field, or destination clock changes in the frozen proposal. No multicycle waiver or timing credit is proposed.

Actual source reset remains `n_rst_d2d__fo2__r4__t24`; TT FIRST en/rs remain `n_rst_d2d__fo2__r4__t29` / `n_rst_seq_ctlm__t23`; DH hop0 en remains `n_rst_d2d__fo2__r4__t14`, DH landing rs remains `n_rst_seq_ctlm__t19`. CTLM reset remains `n_rst_seq_ctlm__t25`; its final relay's r55 clock is distinct from CTLM r54. Ring epochs, release, stopped-clock safety and first-use require actual observations, not this label repair.

## Minimum producer/control trace prerequisite before compile

Keep the selected 25-instruction programme and original four ME mismatches unchanged. Resolve actual L/E source ownership with the separate calendar producer contract owner; do not rename L_compiled to L or synthesize an E calendar. Pin the installed SYSFACE image and selected CALR files. First select a coherent generator source and apply the appropriate reviewed construction-derived metadata fix privately; this packet grants no activation.

The eventual smallest connected trace must observe actual SYSFACE ROM request/decode and complete PW valid/address/data launch, both original TT PW and DH bundles at each real hop/ring receipt, hard-head PW capture and CALR PW/DW capture, their actual clock edges and en/rs/reset epochs, real commit/auth withdrawal and first fixed start. Preserve source-generated events and all four current mismatches; no ready/done waiter may shift them. Every missing producer, calendar, native phase or first-use relationship keeps the graph unresolved. Inventory actual sources/resources before admission. No new compile or full die generator is authorized here.
