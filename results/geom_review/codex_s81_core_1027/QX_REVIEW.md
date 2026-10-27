# QXPQ C18 census review

Image qx_preplan.png VIEWED. Four 125.304x62.952 ROMs sit at mirrored west/east sites with 4.32um halos, 8.664um between same-side macros; ~208um clear middle logic region. Mirrored macro orientations face wide addresses/primary read ports into the logic region. North/south core signal bands remain at the plan positions. No macro wall crosses the central dataflow region. Clock latency is deliberately not claimed: this is a source/LEC/placement census only; the subsequent named-sink slice must replace the legacy clock structure before CTS/route.

Verdict PASS-COND for production-shape synthesis, strict LEC and placement only. No new RTL/cycles: current R17 lineage retains the already-adopted gb 737-pin go-capture/CGR8 source; the previous R13 census died in lint before synthesis, so it supplies no physical evidence. Actual placed reach/congestion/clock-island plan review remains required before CTS or route.
