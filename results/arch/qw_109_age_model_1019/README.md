# Qwen 109 effective-age review model

MODEL ONLY, no schedule recompile or die GRT admission. Exact source snapshots are inherited from 7cda48173; the original die bytes and raw 637-bus digest are unchanged. All 109 historical effective-age differences remain FAIL.

The 109 buses occupy 23 source/destination families: 75 current ideal ages rise by one, 27 fall by one, and seven fall by four. Historical n>1 records used E and omitted the landing output FF; historical n=1 records treated K as age even though K includes the reset calendar offset. This explains the numerical differences but does not establish functional publication, hard-child composition, or native clock phase.

`ledger.json` records each actual source/destination port, all ordered instances, exact E/K/G/R0 and landing output FF, source publication evidence, and unresolved fields. A backward bit walk verifies each relay chain and its raw count. All clocked source hop-0 gates and final landing clocks match their actual top-level source/destination root connections. Metadata `src_ck` is not used as actual root proof: some rows label it with the receiver root.

67 source publications have direct static NBA/PR/wrapped-register evidence. The other 42 retain UNKNOWN: five external straps, one SRAM native read arc, and 36 child or combinational output cones. Every native phase, production consumer first-use, hard-boundary origin proof and adoptable effective age remains NULL. The hard source and destination FFs are excluded from the relay age; landing `o` is included once.

| Family | Buses | Historical → current ideal age |
|---|---:|---|
| bump_die_ps -> io_collective | 1 | 3 -> 4 (1) |
| bump_fwd_epoch -> d2d_rom | 1 | 2 -> 3 (1) |
| bump_fwd_epoch -> sys_face | 1 | 3 -> 4 (1) |
| bump_pkg_s0 -> io_collective | 1 | 3 -> 4 (1) |
| bump_pkg_s1 -> io_collective | 1 | 3 -> 4 (1) |
| d2d_rom -> sys_face | 9 | 2 -> 3 (9) |
| dvs_W5 -> io_collective | 9 | 2 -> 3 (5), 6 -> 2 (4) |
| dvs_W5 -> native59 | 1 | 19 -> 20 (1) |
| dvs_W5 -> tt_ctlm | 2 | 16 -> 17 (2) |
| embed_prov -> native59 | 2 | 2 -> 3 (1), 1 -> 2 (1) |
| embed_prov -> sys_face | 1 | 1 -> 2 (1) |
| io_collective -> dvs_W5 | 5 | 6 -> 2 (3), 1 -> 2 (2) |
| io_collective -> sys_face | 3 | 19 -> 20 (2), 18 -> 19 (1) |
| native59 -> dvs_W5 | 1 | 19 -> 20 (1) |
| native59 -> embed_prov | 1 | 1 -> 2 (1) |
| native59 -> sys_face | 1 | 1 -> 2 (1) |
| sys_face -> d2d_rom | 24 | 3 -> 4 (16), 2 -> 3 (8) |
| sys_face -> embed_prov | 15 | 1 -> 2 (1), 3 -> 2 (14) |
| sys_face -> mu_dhobs | 1 | 2 -> 3 (1) |
| sys_face -> native59 | 11 | 3 -> 2 (11) |
| sys_face -> tt_ctlm | 5 | 1 -> 2 (3), 3 -> 2 (2) |
| tt_ctlm -> dvs_W5 | 3 | 18 -> 19 (1), 19 -> 20 (1), 12 -> 13 (1) |
| tt_ctlm -> sys_face | 10 | 1 -> 2 (10) |

Representative mechanism scope approved by LEAD-QW under ROOT's source-proof direction: SYSFACE→native/provider single-frame publication; grouped SYSFACE→D2D status; slice↔collective command/return and AR; provider code/scale; CTLM↔slice long forwarded chain. No hardware changes are proposed (area delta zero); token delta is NULL until actual consumer programme/profile/native phase composition.

`make_mechanisms.py` copies exact original register blocks with source/extract hashes, and the bench drives their internal predecessor pins explicitly. These are source register cones, not complete hardened parents. The collective return control remains a labelled synthetic publication control because its actual multi-root output cone is unresolved. CTLM HR covers only the original 73-bit low register cone; the 380-bit hard-head command origin remains unproven. No invalid payload masking is used. The original lane and clock-gate modules are unchanged. Declared reset epochs and ideal common roots exercise the E/K mechanism; physical phase remains unknown.

Bounded fleet benches are terminal on ot-epyc8:/srv/opentallas-scratch/claude/qw-109-age-model-1019 (units1680041,1699097,1700994,1701449). Verilator5.050 exact source/lane evidence:

- Five ideal representative source-pin mechanisms PASS512 comparisons each over two resets. Collective return uses the explicitly synthetic publication control; its source cone is not qualified.
- Full original embedding provider, preload face, core store and historical 64x512 SRAM model PASS two lanes1024 comparisons,1152 source-data gold checks,1608 fault checks over two resets. Every code row and scale are explicitly loaded before reads; checks do not rely on SRAM power-up zeroes. Wrong K and extra source stage fail both lanes causally.
- Wrong K, an extra source register, and half-edge source publication each fail all five previously passing representative cases. These are per-case causal failures even though the combined baseline retains the separate HR failure.
- CTLM HR low73 is a preserved baseline FAIL512/512: source age16 is observed where the current E+1 export claims20 (first observation t1413, N26/E19/K6/G1333/R01266). This is an ideal-root mechanism failure, not a measured production native-phase verdict.

The model also finds nine declared D4 lanes with E_sta6/7, outside the documented D−1=3 residual window: W5 ag/ss/dd, collective cmd_free/fault/shared_fault, native59 dr_o, CTLM cmd/hr. Their widths total1757bits. `evidence.json` preserves each exact lane and result. A D8 proposal is not a free depth change: four extra slots alone cost7028 payload bits, the three broad lanes need SRAM under the indexed-storage rule, K becomes4bits/mod16, and physical wrappers/calendars/metadata/read latency and reset epochs must change coherently. No such change is implemented here. Native phase/source ownership must determine whether these lanes are replaced, repriced or otherwise structurally redesigned.

All historical109 failures, the new HR failure, syntax integration failure and causal mutants are preserved in `receipts/`. Wrapper script exit0 only means its receipt loop finished; semantic verdicts in `evidence.json` read each case/log. Source and receipt hashes are in `sha256.json`. No die synthesis, GRT, STA, GEN or schedule compile was launched.

Release hold: preserve production MU header C9 versus actual bound C10 separately. F16 profile, exact TXDP, programme/header source hashes and consumer first-use calendars must match before any later reviewed compile. This packet grants no source exception, false path, data MCP or payload waiver.
