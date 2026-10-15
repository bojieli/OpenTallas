import sys
sys.path.insert(0, '/home/ubuntu/wt/codex-capc-gate-replay-1013-pm/tools/ref_tile')
import pre_route_gate as G
# Header requires unlimited builds; qualification checks and CTS commands stay unchanged.
assert 'SYNTH_TIMEOUT={CAP}' in G.REMOTE_SH
G.REMOTE_SH = G.REMOTE_SH.replace('SYNTH_TIMEOUT={CAP}', 'SYNTH_TIMEOUT=unlimited')
raise SystemExit(G.main())
