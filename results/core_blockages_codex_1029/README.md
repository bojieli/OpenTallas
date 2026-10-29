Core hard-placement blockage census fix, 2026-10-29
=================================================

Actual BTAB detailed-placement failure DPL55 had32hard OpenDB placement
blockages absent from core_family_sites.tcl output and consequently absent
from the converter's row occupancy. The independent BTAB owner legalized
430planned cells with those exact obstacles; successor actualDPL0/CTS is
already passing and GRT is owned by that lane. No duplicate route launched.

Shared source now emits BLOCKAGE id x0 y0 x1 y1 (um) for hard placement
blockages only: isSoft=false and getMaxDensity=0. Soft/density blockages are
not promoted to hard obstacles. Converter read_sites stores these exact
rectangles and SiteMap reserves intersecting row/sites alongside fixed
cells. No macro halo, PG obstruction or route rule is added. Legacy files
without BLOCKAGE rows retain their former coordinates. Existing old cached
sites files must be preserved as history; generate a fresh census for new
planning work requiring the complete obstacles.

Read-only actual failedODB export ran via ot-run intel1, exit0/unit
oth-ubuntu-1170474-1793262068. ODB/source paths and comparison are retained
in comparison.json. Exported32hard rectangles match the independent lane's
actual_blockages.json exactly at1000DBU/um. Snapshot includes1220rows and
3454fixed cells. Remote own output intel1:
/srv/opentallas-scratch2/claude/codex-core-blockages-1029/{sites_actual.txt,census.log}.
No STA, placement or route repeated. Failed inputODB remains untouched.

39focused tests pass: test_core_plan_to_infra.py+test_core_family_slice.py.
New controls exercise exact boundary touching (no halo), body intersection,
malformed rectangle rejection, and a mutant dropping blockage records that
recreates a placement overlap. Existing row-fragment converter fix retained.
