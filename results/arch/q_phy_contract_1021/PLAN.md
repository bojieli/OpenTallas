# PHY source contract and geometry plan

Source-only recovery; no source implementation, GEN, synthesis, physical audit, gate, route or adoption. Frozen diagnostic QDIAG manifest187fdf67026f7e707ecace89742b0ef272ef5cfb130a1c5092eff6854485b98c and terminal51f9b8dc3 remain failed/unchanged.

## Actual source versus missing qualification

* SerDes `ot_qfd_serdes_112g_x12_phy_s597` source LEF eb7bba3928fbc62ab8e5be449fcf1a56cbadcee47e82d1badc9b46a8008a7152 is **2320.056 x1563.570 um**, M4 VDD/VSS, FDI1199 signals on local west M4, input clk. JSON marks placement/connection/timing as an ASSUMED licensed-PHY abstract, FDI597 and223 one-way FDI cycles; no GDS, SI or bump map. It is not a measured hard PHY.
* Q UCIe `tp8_1013` source1fcc313e... has M4 PG and2091 signals but no lclk; `nface_tall_1017` source0b763c28... has M4 PG and2092 signals including actual lclk output, core-facing local north/M5. Both777.6square. nface JSON explicitly calls lclk an ASSUMED PHY-modeled boundary clock source **with no arcs**. Actual nface TTlib agrees: lclk is output without timing arcs; clk is input clock. Clock-source insertion and phase must follow the actual source clock law, not an identity alias to another PLL.
* K UCIe `ot_qkvd_ucie_x64_phy` sourcef4a2b22a7479ebcbca2a9dbe676e36b20d933d28ae13aff4b15f8b66c7280f66 DOES have genuine same-master M4 VDD/VSS source bytes. 777.6square, local north/M5 digital pins;1171 signals including clk/rst_n,1169 five-field FDI. Exact LEF is byte-identical at0ae42aa9c/92bccf726 (K owner also confirms aecb). This corrects the earlier absence claim; **access qualification and native clock insertion remain absent**. JSON/Liberty have no nativeR evidence. kv_native_phy.bind only binds ports/LEF and libraries() copies ETMs; it does not export insertion. The legacy missingR failure is therefore preserved, not solved by same-master PG bytes.
* Captured emitted case PHYs are synthetic M7/M8 PG. Source bytes cannot be claimed bound merely because a matching source file exists. Existing apply_case.py requires real M4-only VDD/VSS before its explicit ASSUMED access-column revision, and remains ASSUMED_UNQUALIFIED after application. It does not create M4 pins from M7/M8. Its HBM path targets qkd_hbm3e_phy_pc separately; actual ot_hbm3e_phy source is not an alias for Q/K masters.

## Exact legal geometry law

Every inspected source LEF declares `SYMMETRY X Y`, with no R90. Allowed mirrors and180-degree rotation preserve width and height. A90/270-degree rotation or diagonal mirror cannot be inferred from X/Y. SerDes captured outline1563.570x2320.056 is therefore not the oriented source macro under the declared symmetry.

For local source width W,height H, legal normalized rectangle transforms are:

| Orientation | Point mapping | Source-west FDI face | Source-north FDI face |
|---|---|---|---|
| Source reference N | (x,y) | W | N |
| MX | (x,H-y) | W | S |
| MY | (W-x,y) | E | N |
| R180 | (W-x,H-y) | E | S |

Transform each signal pin rectangle, PG rectangle, OBS and package keepout with the SAME mapping (take transformed min/max for rectangles); do not transpose only dimensions or relocate signal pins independently. Source N is a geometry reference, not permission to invent clock insertion R=0.

Captured place.tcl has io_serdes (0.162,15129.720,MX), io_serdes_1 (0.162,7541.370,N), io_serdes_2 (0.162,5095.980,N). Actual west FDI stays west for all three orientations. At these west-edge coordinates that is a concrete FDI-face placement concern; **package-facing legality cannot be concluded** because the abstract explicitly lacks a bump map/package-pin definition. Do not assume opposite-face package pins merely from the FDI label.

## Proposed source-owned construction, pending owner choices

1. The exact original GEN run has now been recovered and SHA-verified: run.sh4d7c31b3ed2aed3f8945577ee9728ce7f5beb9fc5f088b3eca9ee08ebe48a0bc sets OT_SPLIT_PHY_TALL=1 and OT_SPLIT_PHY_NFACE=1 explicitly; OT_SPLIT_UCIE_PHY_CLK defaults1. This establishes the missing two flags in the later physical diagnostic as a stage-selection omission. Bind one explicit source-profile bundle per exact master across port check, real-LEF binding, Liberty/model, PG and clock stages. The bundle must pin all hashes and fail on missing ports, outline or clock law. For Q UCIe the required actual lclk makes tp8 incompatible; choose the existing nface bundle explicitly, not an environment variable that changes only a blackbox header. Actual binder is tools/qwen_tp8/bind_real.py::find_view (lines150+): explicit OT_BIND_VIEW_SELECT views plus --view first, then ref_tile; nface only with OT_SPLIT_PHY_NFACE=1 and tall nested under OT_SPLIT_PHY_TALL=1; then die_masters, tp8_1013 and missing_phy/default. It never reads OT_PORT_BIND_UCIE_VIEW, which only changes the port-check header. Frozen diagnostic wrapper exports only OT_PORT_BIND_UCIE_VIEW=nface_tall, so full-source mismatch is explained. K physical/qwen_kv_die_phy is absent from fallback search; an exact explicit same-master profile is necessary. Existing CLI/selector can express this without a generic fallback alias, but original GEN flag/source identity must be recovered before applying any choice.
2. SerDes: further source recovery found the genuine independently published SAME-MASTER `nface_tall_1017/ot_qfd_serdes_112g_x12_phy_s597` bundle. LEF **4c62ffde575d234fef5ab6dde33f09b3ddda9f9ab8d7cc7501f5a60e75c4cc55**, **1563.570x2320.056**,1199 local-north/M5 signals, M4 VDD/VSS, X/Y symmetry, FDI597/latency223 unchanged. JSON explicitly calls this a TALL modeled-PHY source revision. This is exactly the captured outline and original GEN NFACE/TALL choice, **not a quarter-turn or alias of the base wide source**. The immediate source-consistent repair plan is to restore these exact original profile flags or explicit full-bundle selection in the later binding stage; no new geometry or source profile is needed to explain this refusal. Under the actual tall source, MX maps its north FDI face to south; N/MY keep north, R180 maps south. Transform its actual PG/OBS/pins together under these allowed mirrors. Package pads remain unmodeled; restoring source identity does not establish licensed package/bump legality or PG/clock qualification. A wide-slot redesign is unnecessary for this source-consistent correction.
3. K UCIe: bind the existing same-master source profile only after exact FDI/clock/source checks. Preserve nativeR as missing until the source owner supplies a legitimate modeled analog clock insertion/phase contract or measured source-bound evidence. Do not use0, another PHY's insertion, or a digital wrapper identity as a substitute.
4. Root must decide the explicit analog-model claim scope and package-facing assumptions. These are owner-level contract choices, not routine geometry edits. No source edits/gates in this packet; current diagnostic failures remain authoritative.

## Remaining bytes/contracts

* Real-binder precedence bytes and exact diagnostic wrapper are now sealed in selector_contracts.tgz. No implicit selection change was made. Original GEN run and its SHA256SUMS now recovered and verified; source flags explicitly NFACE=1/TALL=1. Only original selected profile restoration is supported, no arbitrary fallback.
* SerDes package pad/bump/keepout map or explicit source-owned modeled face reservation; valid90-degree source profile if a tall slot is required.
* Same-source PHY clock origin, insertion/phase and ETM interface law, including K nativeR and Q lclk no-arc modeled root semantics.
* Access-contract qualification after genuine source profile binding; full current die connectivity/short/obstruction/clock checks are NOTRUN here.

HBM owner confirms its ot_pdie_ucie_col/ucie_pma_gen TX/RX513-bit profile is distinct and cannot fill these gaps. Existing HBM PHY PG provenance examples are not permission to alias Q/K master interfaces.

## K-die scene distinction confirmed by K owner

Legacy c216 and captured main92 K-die scenes already import actual M4/clkM5 UCIe and native_phy.json records the actual source profiles. Their macro-block SHAs after normal case PG processing differ from whole raw LEF SHA by construction. The c216 missing-nativeR failure therefore occurs DESPITE correct M4 source import. This must remain separate from QDIAG captured synthetic M7/M8. K owner identity receipt: /home/ubuntu/scratch/codex-k-die-selector-1515/phy_profile_identity.json.

## Source recovery correction to initial geometry choice

The initial wide-eb7bba geometry analysis remains true for that source, but is not the selected original GEN profile. The separately published tall4c62ffde profile now resolves the outline mismatch without any invented90-degree allowance. `serdes_source_candidates.tgz` seals both north-wide76a5022b and north-tall4c62ffde source bundles. `original_gen_contracts.tgz` seals original run/gen/candidate scripts and their SHA256SUMS, all three verified locally as read-only text. The parent/source owner must authorize any new continuation; this packet still executes no GEN/bind/audit.

## Exact modeled Q UCIe phase law

The source nface model drives lclk from its own free-running `always #(LCLK_HALF_NS)` oscillator (default1GHz), with no identity assignment from clk. Its latency pipe and tx_up update on input clk; the lclk/clk relationship is not a physical insertion arc. TTlib supplies no lclk timing arcs. Captured clock_contract.json explicitly states clock_generation OPEN for real common-PLL/divider implementation and physical delivery, qualification=false. Preserve these distinctions; a modeled oscillator does not establish source insertion R or a checked phase relationship.

## Bounded K SerDes companion clock debt

Exact current92 K binder kv_native_phy.py covers BOTH K UCIe and base-master ot_qfd_serdes_112g_x12_phy. Its libraries() only copies ETMs; neither path exports native insertion metadata. Current92 base SerDes source JSON (FDI1043,223cycles,2320.056x1563.570) has no native/insertion entries and is a DIFFERENT master/interface from Q staticS597. Exact preserved legacy c216 dieclk/targets.json contains neither UCIe nor SerDes master entries. The actual failure encountered UCIe first; no later SerDes result is claimed. Both source clock contracts should be resolved together to avoid substituting an unsupported second unknown after the first. Files k_c216_targets.json, k_serdes_profile92.json and kv_native_phy92.py seal this existing readset; no execution/repair was run.
