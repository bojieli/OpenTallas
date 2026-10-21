# S81 slice result collection

VP source repair9d9ebd8ff / kit record9c376299f fixes the original unmapped
async-load ring bits. Existing MAIN and FALLBACK base benches PASS, POST
last writes63/65 cycles. Both r4 gates then stop at actual mapped native
admission, before floorplan: fanout failure remains. Summaries preserve
all violating drivers and hashes of full remotely retained reports.

FALLBACK: max65,126violations; k_hsv65, k_cfe/k_dswp/k_hsa0/k_dodd64,
bank mux33/34, reset33/35, wv_p47. MAIN summary retained separately.
Next repair needs smaller selector/enable groups (8bits), local reset/valid
copies and bank-local ring pointer decode. No unchanged layout retry.
Original09:27 missing-sparse-input failures and r3 unmapped75-cell failures
are retained. No route, submit or main merge was performed here.

XG duplicate pairs have identical per-kit file manifests, recorded in
collection.json. All four live clients were preserved. XFIN replacement
clients were live despite stale initial FAIL JSONs; do not infer liveness
from an old JSON without comparing current client/source snapshots.
