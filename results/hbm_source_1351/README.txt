HBM source takeover 2026-10-27 13:51

Quarter control/meta geometry is a source-logical point model, extending geometry
71648c3daf / native source ef994fe770. No RTL/plan edits, added registers or cycles.
Actual C11 aligned H0/H1 pins remain unchanged. Quarter lot1816.992x2347.488;
tails x1581.12,y950.4 MX / y1209.6 R0. All key/query/sum/fault geometry remains
in results/codex_hbm_quarter_geometry on codex/hbm-quarter-geom-0915@71648c3daf.

The control model adds native qv/kv/kkv f/g and chunk captures, all2048 hid pin
paths, prdy/rdy1/rdy2/online, W-glue real scalar source FF dependencies, aux30
f/g, existing u_vlD104/keepD106/metaD123 storage, scalar b_w/e_bus controls to
actual tail pins, and actual tail outputs through ov/ok/os/ofl to score bits.
Geometry was rendered and viewed: independent control banks follow legal soft
streets and aux/meta occupy the central street. Source-logical identities are
not literal mapped cell names. Bare mapped source may merge/prune equivalent
FFs; ordinary production keep hooks, actual cell aliases, joint cell/PG/clock
packing, reset delivery and propagated TT/FF STA are still required. No G1,
route, die binding or sign-off acceptance is claimed.

Failed v2 (10 overreach/54 macro-interior anchors) is retained in runtime;
source placement corrected these without adding stages. Retired provisional
meta/keep proxy consumer edges had8 inconsistent actual-tail term coordinates;
final3 removes those obsolete edges and checks ALL endpoint identities for
coordinate consistency. Packing worker owns joint capacity/spreading.

Reproduce using immutable geometry data intel2:
python3 tools/hbm_b2/quarter_control_geometry.py --data \
 /srv/opentallas-scratch2/claude/codex-hbm-quarter-geom-0915 --out OUT

xq_common_clock.json separately records exact source common-phase ABI for
clk/clk_w/clk_s/clk_e/clk_c. The actual parent connects all5 to clk_eg; all
leaf sequential blocks are posedge. Five scalar pin names are preserved.
Leaf body equals pinned4d6f5439dc; no RTL clock collapse or phase change.
