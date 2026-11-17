# FAIL-ROUTE-1115 Codex takeover 2026-11-16 19:5x PST

Canonical source now coord/tools/fail_route.py, committed 5d08370454fd then c0c1ace3e6a5fe27d68ab96f31ceeb1d62941acd.
6 focused regressions pass (python3 -I ~/coord/tools/test_fail_route.py).
The original installed ~/.local/lib/fail-route/fail_route.py remains untouched.

Cause: recent family mentions chose KV-CLK-R2 after that lane reported clock checks, even though KV-R owns the design/packaging classes.
Fix: explicit live exact die+item COORD-ROUTED-OWNERS.tsv assignments win over mentions.
All class items must have a live explicit owner; conflicting explicit class owners route to COORD; missing/dead/prefix rows retain fallback.
18 exact KV-R assignments per r410 committed b363fe0c8312.
KV-R canonical ACK restores parsed liveness. Actual current classes now 4d377cd3aa(6), c21781975f(11), f5fa4d600f(1) -> KV-R.
Exact CODEX coordinator RESULT summaries are excluded; CODEX-TOKEN and other worker labels retain real failure routing.

Service switch approved by root: ~/.config/systemd/user/fail_route.service.d/20-coord-source.conf.
Same flock /tmp/fail-route.lock, timeout300, defaults and log; only source path changed.
daemon-reload; no live process killed or restarted. Existing timer stays active, next tick runs committed source.

Last-hour current live FAIL classes0 at19:5x; these 18 are older state re-escalations, not >=10 new failures.
No blanket hold created. KV worker owns actual fixes, no duplicate physical job launched.

M7PIN coverage: shared M7-stripe hypothesis refuted. n3 SIGNED, SPEPRD3 and EPC/he12 handled HEAD team.
DRT0206 named four-net force-rip A/B remains assigned HEAD; root/head notified to collect. No generic router change justified.

CLEAN-ALL: fleet team owns actual disk headroom; no cleanup duplicated here.
