Native PC mux floorplan proposal, 2026-10-09

The admitted EPYC1TB analytical gate passed: all 3,111 bits in the actual
20-group native mux ABI are assigned once, with no coincident face pins.
Controller-facing S pins and runtime-service source0 N pins reproduce the
measured dsfd_ctrl_pc / dsfd_svc_pc bit coordinates. Sources1/2 use W; source3
uses E. This CSV is a proposed pin plan, not a routed LEF or timing result.
The real ctrl_live producer is dsfd_ctrl_pc.co_w[0]; its buffered last segment
is still unmeasured. The input leaf hash is authoritative for its coordinate.

The 128 proposed 240x480um mux slots total 14.7456mm2 and include 1,769,472
protected queue bits before other state/logic. Adding the row increases each
shoreline band 488.64um. With the actual a651d5101 scan placement, the existing
field-edge slack 378um leaves 110.64um overlap per side, or 114.96um deficit
including 4.32um clearance. The 33x26mm outline is fixed; the recorded 229.92um
height-growth number diagnoses the deficit and is not an adopted remedy.

FIELD_MARGIN only bounds slot selection; it does not move the centered field
at unchanged frame count/heights. Keeping a 108um PQ field-to-band gap requires
437.28um total field-height reduction. A proposed 64.8um reduction in each of
seven channels recovers 453.6um without removing field frames or slots and
leaves 116.16um edge gap. It loses 1,350 horizontal tracks per layer in every
channel at 0.048um pitch. The ledger lists every current boundary object that
requires relocation. This candidate has neither a placement nor a routing
capacity pass and is not adopted. In particular, the last channel's generic
corridor falls from 153.36um to 88.56um. Native enlarged-head geometry needs its
own inventory and channel evaluation; scan figures do not validate it.

The latest historical hw_SW failure is explained by horizontal-first routing
from the spine into occupied field frames. The native proposal reserves a
vertical s14W path first and then a lane in the new mux row, before generic
hop placement. Historical anchors estimate 20.493mm length, 106 stations at
195um interior spacing/215um reach cap with 90um endpoint caps. Actual native
source/destination faces, corridor station feasibility, clock context, and
writeACK aggregation remain unbound. The long packet is 290 bits, plus reverse
credit 1 and trueACK count 8. Four local 341-bit source interfaces belong beside
the PC mux and are not the central HOST bus. Request/credit/ACK staging costs
at least 31,694 register bits. Eight initial HOST seats bound boot injection
to 8/(2*106+2)=0.03738 sectors/cycle before physical service/ACK latency. This
does not establish runtime performance or physical completion visibility.

Inputs: geometry source a651d5101 with immutable physical inputs fe365cd13;
native contract c60574a3c pinned to wrapper 3ba34f388; mux 2f179fc18; closed leaf
contents are SHA256 pinned in budget.json. No native die generation, RTL
change, place-and-route, STA relaxation, or substituted functional bus occurs.
All earlier failed geometry/STA receipts remain historical.

Remote evidence is retained under
/srv/opentallas-scratch/claude/s81-dies/host_corridor_geometry_a651d5101_v2.json
and native_pc_floorplan_budget_v{1,2} directories/logs on ot-epyc1tb.
V1 uses the old destination anchor in its rough route estimate; V2 supplies
the explicit spine-to-new-row polyline and channel ledger. Both are proposals.
The extraction script is tools/s81/patches/historical_host_geometry_a651d5101.py.
The standalone planner takes --geometry --contract --rtl --ctrl-lef --svc-lef
--output, refusing to overwrite an existing output directory. It was run via
/srv/opentallas-scratch/admit.sh 1GiB with python3 on EPYC1TB; both passes were
terminal exit 0. No local computation was launched.
