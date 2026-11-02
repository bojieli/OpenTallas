# Filler mechanism passed; target integration and deployment remain held

This branch proposes adding `filler_placement` to the real-module strict guard.
The bounded native vehicle has passed; do not merge/deploy that admission
until its process integration and actual target scope are approved. The existing C++ module/ABI/source pins are unchanged.
Production scope remains the already qualified two resizer commands meanwhile.

The exact pinned ORFS fillcell script loads genuine `5_2_route.odb` and
`5_1_grt.sdc`, calls PRE_FILLCELL, native filler_placement/check_placement/area,
writes `5_3_fillcell.odb`, then calls POST_FILLCELL. This is the actual stock
fill stage; no CTS or fake stage alias is involved. Pinned native
FillerPlacement.cpp creates each filler through makeUniqueDbInst with
physical_only=true, which calls the already examined dbInst::create before
orientation/location/status/source flags are assigned. It performs no RC
estimate. PG must nevertheless be bound before later extraction/analysis.

Proposed exact owner integration, only inside an OWN new container after the
normal MM patch:

- Keep the selected R masters and append their matching L masters; family
  selection remains QC owner's independently reviewed source change.
- PRE_FILLCELL: source hardened helper, require strict1, native begin, then the
  entire original PRE hook. Input PG0 and loaded libraries/rules are mandatory.
- POST_FILLCELL: original POST then native end. Preserve all existing logical,
  clock, geometry and DRC gates; the two real M4 shorts remain separate defects.
- Use this packet's fillcell_driver.tcl plus runtime preparer with --stage
  fillcell before ordinary make. The wrapper preserves the complete post-MM
  stock body as fillcell.native_pg_original.tcl; any failure aborts before make.
- Independent saved 5_3 native audit0 is required; a stage write alone earns no
  release or DRC credit.

Native vehicle PREP: Intel2
/srv/opentallas-scratch2/claude/codex-pg-birth-fill-0312/{vehicle.tcl,run.sh}.
The active QC owner reviewed and cleared one isolated4GB1T experiment under
the original PG investigation scope. It ran on Intel1 with normal admission;
EPYC2 was correctly excluded below the50GB floor. No bypass or target run.
See NATIVE_RESULT.json and retained logs.

The fixture intentionally makes a disposable tiny two-row design from an OWN
Tnode PG0 copy solely to reuse actual R masters/rules. It deletes the original
cells/rows/blockages and gives the fixture an explicit40-site x2-row core; it
loads the exact QC L LEF and places one real R and L neighbor. No fixture output
is a project physical candidate or timing result. It exercises actual native
filler_placement in three independent processes:

1. R-only masters must reproduce the LVTN missing-family error.
2. R+L without callback must expose actual born physical-only filler PG opens.
3. R+L with candidate strict helper and real module must bind every birth;
   inactive-callback strict retry must refuse before execution.

Compare all actual filler/neighbor masters/poses/orient/status/source/physical
flags between2/3, then independently reread saved callback ODB for native PG0.
No RC/STA/GEN/PLACE/CTS/route or full target finish is run. No new C++ build.

Actual result:7 native fillers (4R+3L), control14 PG opens versus callback0;
callback creates7/bound14, saved fresh audit18/0. Paired all9 instance master/
pose/orient/status/source/getter records are byte-identical. Strict inactive
call refuses. Initial two harness failures are retained: Tcl catch returned
DPL-0050 rather than the printed LVTN diagnostic, and isPhysicalOnly() tests
module membership, so top-module fillers returnfalse despite native factory
physical_only=true. Corrected census uses actual new identities, explicit
master list and DIST source flags; the public getter remains in comparisons.
The valid missing-L negative was not rerun; only unfinished cases were resumed.
