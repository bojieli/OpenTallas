DIE-KV-42 b64d6d012cb real-plan identity merge condition, CODEX 22:55.
CHECKED: KV event28w_c matching49 output type digests, same7 pre-existing no-space
errors (all56 types). HEAD frozen src25p23/23 types matchingdigests, no errors.
Actual HEAD has hd_serdes PHY supply region, whose bands are disjoint; all other
22 types have no PHY region. The old expectation that HEAD entirely lacks PHY was
inaccurate; its no-PHY types and its disjoint-PHY type both remain byte-identical.
This is OUTPUT type hash identity across per-type resize, not a new physical gate.
KV source: intel1 die-kv-42-1029/cmp_dp_{main,br}.txt (already finished on takeover).
HEAD source: intel2 die-head-34/src25p/source_{plan,sidecar}.json (copied read-only).
HEAD compare: old clock_landing_plan from b64^ vs b64 with identical dependencies;
no source edits in either lane's tree. Extra branch PHY print lines excluded from
comparison; they report regions only. bandcmp.py records exact method.
