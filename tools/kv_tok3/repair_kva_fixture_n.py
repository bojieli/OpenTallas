#!/usr/bin/env python3
"""KV-TOK3 10-19: build the startup-repaired, N-step boot-word driver for kva_vehicle.sh vehicles (WSQK/P0/P1/...).

= the reviewed exact-G7 repair (repair_g7_fixture.repair, codex/kv-token-authority-monitor-1019 c54345a6b: authority-gated
sequencer/K/V/TX observation, source-owned retirement ledger, end-of-programme authority/identity checks), applied to the
SAME original driver (sha 668c9ade...), then made cut-generic: path count and V-path base come from the cut's generated
kva_auth_defs.svh (gen_kva_authority.py) instead of the G7 literals 18 / 10, and the includes name the N-step identity
adapter and the generated fault bind.  RTL, stimulus, gold, programme dates and deadlines are unchanged.
usage: repair_kva_fixture_n.py --driver ORIG.svh --out NEW.svh
"""
import argparse, hashlib, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from repair_g7_fixture import repair, replace_once
p = argparse.ArgumentParser(); p.add_argument('--driver', type=pathlib.Path, required=True); p.add_argument('--out', type=pathlib.Path, required=True)
a = p.parse_args()
s = repair(a.driver.read_text())
s = replace_once(s, '`include "kva_hier_refs.svh"   // MU-TOK-KV3: port nets of hier-block instances (no refs into a hier block)\n',
                 '`include "kva_hier_refs.svh"   // MU-TOK-KV3: port nets of hier-block instances (no refs into a hier block)\n'
                 '`include "kva_auth_defs.svh"   // KV-TOK3: authority path count / V base, generated per cut (gen_kva_authority.py)\n')
s = replace_once(s, "kva_authority_known[10+g]", "kva_authority_known[`KVA_AUTH_VBASE+g]")
s = replace_once(s, "for (int ai=0; ai<18; ai++)", "for (int ai=0; ai<`KVA_AUTH_N; ai++)")
s = replace_once(s, '`include "g7_identity_bind.svh"', '`include "kva_identity_bind_n.svh"')
s = replace_once(s, '`include "g7_fault_bind.svh"', '`include "kva_fault_bind.svh"')
a.out.write_text(s)
print('KVA_FIXTURE_N', hashlib.sha256(s.encode()).hexdigest())
