#!/usr/bin/env python3
"""KV-P2 10-23: what blocks a fully bound GENERATED KV die (gen.py rtl with --rtl-root: every leaf port bound, no ties,
no undriven nets), measured on the as-built rtl6 die.v (bind/bitcon.py output) against die_plan v3.1.
    python3 bind/blockers.py BITCON PLAN > bind/blockers_v31.json"""
import collections, gzip, json, sys
bc = json.load(gzip.open(sys.argv[1])); plan = json.load(open(sys.argv[2]))
B = bc['blocks']
straps = collections.Counter((B[i], p) for i, p, _ in bc['leaf_inputs_undriven'])
aux = collections.Counter((B[x[0]], x[1], x[4] + '.' + x[5]) for x in bc['leaf_inputs_tied_via_pass'])
rly = sorted(n for n, m in B.items() if m == 'qkd_rlyi_258s')
bound = sum(1 for t in plan['partition_types'].values() for c in t['contents'] if c.get('bind'))
out = dict(
    plan_leaf_bindings=dict(contents_with_bind=bound, types_with_sources=sum(1 for t in plan['partition_types'].values() if t.get('sources')),
                            note='die_plan v3.1 (like v1-v3) declares NO leaf bindings: gen.py rtl stops at the first '
                                 'type (kv3_hg: bus o_ectl_Q_N_eN is not bound to any leaf port)'),
    straps_undriven_in_asbuilt=dict(bits=sum(straps.values()), ports=len(straps),
                                    by_port={f'{m}.{p}': n for (m, p), n in straps.most_common()},
                                    note='die.v nets with no driver (n_*__tie0, ID / chain-end straps) that the GEN '
                                         'die tie-cell pass (die_constant_cells.tcl) materialises as TIEHI/TIELO: '
                                         'ties by the owner rule -> leaf parameters (RTL rework) before a bound die'),
    landing_fault_inputs=dict(bits=sum(aux.values()), by=dict((f'{m}.{p}<-{s}', n) for (m, p, s), n in aux.items()),
                              note='fault-OR (qkd_hp_or2) inputs fed by qkd_landsh* landing-cell fault outputs; the plan '
                                   'replaces landing cells by stations, so these OR leaves lose their sources'),
    pv_trunk_mux_relays=dict(cells=len(rly), master='qkd_rlyi_258s', example=rly[:4],
                             note='b <= s ? y : a: the PV result T-chain select stages behind the 8 RH gathers; '
                                  'extract_asbuilt treated them as pass cells, so the plan has no instance for them'),
    clocks_without_plan_spine=['pll_hbm_WS', 'pll_hbm_WN', 'pll_hbm_ES', 'pll_hbm_EN', 'pll_phy', 'pll_host', 'pll_ingest',
                               'pll_fwd'],
    reset_root='host.die_rst_n drives 5,760 reset bits as built; the plan reset spine is sourced from @die rst_n',
    unused_leaf_output_bits=sum(bc['unused_leaf_output_bits'].values()))
print(json.dumps(out, indent=1))
