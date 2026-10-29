# Actual DMA station geometry and count preparation

Sixteen actual native edges map exactly to 2,192 physical pins: eight 17-bit requests and eight 257-bit responses. The authoritative native map places hb_dbk_NW at NW_hub/u_hb_dbk_Q__q1 and vmb_NWk at NW_hub/u_vmb_Qk. Native bit identity, pin presence, core orientation and track offsets are preserved. Actual pin-file ports are 136 request / 2,056 response bits at DMA and 17 / 257 at every bank: no missing or surplus physical pins. Old 137/258/2064 figures belong to stale station metadata, not the selected actual interface.

All sixteen centerline routes pass the 364.5um canonical reach, including every individual source/target bit. Maximum362.88um. Every station center lies outside all159 core bodies plus4.32um halos. Existing station_resite.route solves the interior chains; two explicit legal endpoint banks cover every exact bit pin and are included in all counts.

| Bank | Request stages | Return stages | RR_RT80 - intrinsic7 - request - return | Request padding bits (17b) | Response padding bits (257b) |
|---|---:|---:|---:|---:|---:|
|0|17|17|39|663|10023|
|1|20|20|33|561|8481|
|2|15|15|43|731|11051|
|3|16|16|41|697|10537|
|4|5|5|63|1071|16191|
|5|8|8|57|969|14649|
|6|3|3|67|1139|17219|
|7|6|6|61|1037|15677|

No padding choice is adopted. Request padding changes the memory-read sample date and requires a compiler write/version-window proof. Response padding preserves that date but requires a priced SRAM design at these >2kb per-bank capacities. Source pipeline/API and intrinsic7-cycle/RR_RT80 qualification belong to the HBM/coverage source owners.

native_station_recipes.json is explicit geometry/count input for that API. geometry/ retains every per-bit endpoint and exact station list. Physical FF body packing, channel/pin capacity, source RTL insertion, exactness, GRT, STA and token qualification remain NOT RUN here. There are24,660 proposed registered bits before any fixed-date padding.

Personally viewed native_dma_stations.png: station centers follow free streets between the retained cores; request and return paths share the lower streets and converge on q1 at the east. All eight banks and source/sink bit pin positions are shown. Signals can cross hard-core bodies on allowed upper layers; those line drawings are center-to-center guides, not detailed routing. Dense shared endpoint/station banks need actual per-bit FF packing and routing capacity before build. Verdict PASS for station-center geometry/count preparation only, HOLD physical adoption.

Completed solver: epyc2:/srv/opentallas-scratch2/claude/codex-dma-station-0848/geometry4, ot-run unit oth-ubuntu-3553301-1793289381 exit0. Inputs from c25c_d18 and authoritative codex-hbm-bind-0850 native edge/map files; hashes in input_hashes.json. Initial source-transfer attempts NOT RUN (missing new script due ambiguous FETCH_HEAD ref); geometry3 had a report-expression SyntaxError, corrected in e5ea850f3. Failures and their client logs remain in intel2 codex-support-dma-client-0848/route{,2,3,4}.otrun.log. No live physical job was touched.
