# CTRL native32 terminal gate / CLAUDE BACK seal

Frozen source808c23b00, ownWT codex-s81-ctrl-coll-pickup-1019; terminal
013001 ep5 gate **WARN, zero FAIL**, trial GRT overflow0/M3max12.89%.
This is NOT a submitted/closed view. No REVIEW.json or submit was written.
Both actual PNGs were personally viewed; critical decision is S81 lead/ROOT's.

1. Registered pins: source32PC exactPASS + RD3972/KRDY1011/PACK5910 causal
   witnesses in native32_witness. New native physical pin geometry2492/2492
   ontrack, zero outside/missing. Post-route functional boundary audit owed.
2. Reach: planned2468 native SRAM payload legs max302.739/0>405 after
   responseR180, actual PHY19904bit seam max149.134. The in-hand partial native
   GRT endpoint audit now identifies SEVEN reset FF->FF Manhattan distances
   >405 (max411.439, hrbank q0 -> PC1 u_wd sgray RESETN). These are concrete
   placement counterexamples even though the audit is incomplete for macro
   bus pins. Full actual endpoint/routed reach **NOT QUALIFIED**.
3. Fanout: source mapped2956FF/4SRAM max31/0>32 proof preexists. The new MAIN
   census on raw post-GRT write_verilog is **UNQUALIFIED FAIL**:13,699 missing
   physical-only TAPCELL Liberty-role errors and only two reported over32
   drivers, clk146/ckh96 (clock-tree/root classification unresolved in this
   diagnostic). This must not be called data fanout failure or admission PASS.
   Raw report and exact tool commands preserved; proper pre-floorplan actual
   source-Liberty census remains needed. No data32 waiver.
4. Depth: gate textbook293.4ps/2956FF; actual TT placement path classes
   macro->reg285.4ps, reg->reg291.5ps, in->reg293.5ps positive slack. Diagnostic
   setup WNS285.44ps/hold10.07ps. No final routed signoff claim.
5. Storage:4 real16x340 wide-pitch SRAMs, unchanged logical FIFOdepth8;
   +216 control/reset FF per tile/+3456 per16tile die, no data edges. Native
   source storage contract unchanged; >2kb payload stores are SRAM.
6. Geometry **HOLD**: actual531.25x324 aspect1.64,4macros2x2; requestR0 bboxes
   (86.4,172.8)..(200.88,273.51),(345.6,172.8)..(460.08,273.51).
   ResponseR180 bboxes start(86.4,43.218),(345.6,43.218), endY143.928.
   These are +0.018um Y track-alignment offsets from requested43.2, not all
   literal43.2 origins. Native pins are ontrack. Actual signal/clock PORT
   counts are N1246 overx4.545..526.716 (~2.39/um), S1245 over4.545..526.725
   (~2.38/um), W1 y162.012. Legacy preflight S1321 demand is not actual count.
   PNG density shows TWO thin N/S face bands plus scattered low density;
   no single continuous central standard-cell band. Overallfill28.1%, std
   area~1236um2/stdplaceabledensity1.1%. README pin-bound98% width alone does
   not qualify the one-band/lowfill/literal-origin requirements.
7. Actual dualroot clock PASS at CTS: clk boundary1245 sinks TT59.1/FF62.2ps;
   ckh boundary1302 TT35.2/FF38.6. Both <=80, no largest-root waiver. Insertion
   >300 is guidance only and still needs actual parent compensation/binding.
8. Schedule:0 added steady data edges; reset PCR+1/FIFO+1 release edges and
   +216FF/tile explicitly priced. Geometry/reach/PG and full signoff outstanding.

## Read-only post-GRT artifact limits

The saved5_1_grt.odb was never mutated. dump.tcl writes grt.v plus every native
signal ITerm averageXY/BTerm center and all instance bboxes. `terms.tsv.gz`
and `instances.tsv.gz` retain exact coordinates. PG dump reports59644 bound,
18158 unbound contacts at GRT; no final6 PG/rail/escape qualification.

`reach.py` is an UNQUALIFIED analysis prototype, not a production gate hook.
It follows unrestricted combinational cones to FF/SRAM/PORT endpoints using
actual Liberty cell roles. It currently lacks indexed-to-inherited bus role
fallback, so4112 macro bus role errors omit their payload endpoints; it must
be fixed and rerun before a complete reach PASS. Its 9723 existing endpoint
pairs include seven correctly joined FF-reset pairs above405; those partial
counterexamples are preserved in post_grt_unqualified_summary.json. Distances
are Manhattan endpoint lower bounds, never routed detour qualification.
The raw full native/reach JSONs are compressed and retained with their errors.

STOP on CLAUDE BACK: all own gate/scout/audit clients terminal; no new launch,
merge or submission. Existing Claude jobs untouched. Final narrow evidence
commit is on own branch only; root must not merge its older broad tool-sync
ancestry7be2c6292 wholesale.
