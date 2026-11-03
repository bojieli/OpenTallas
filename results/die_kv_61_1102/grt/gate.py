import json, sys
T = sys.argv[1]; j = json.load(open(T + '/die_sta_related.json')); g = j['summary']['die_clock_gate']
print('GATE', T, json.dumps(g))
for c in ('intra', 'seam'):
    s = j['summary'][c]
    print('CLASS', c, s.get('ff_hold_kit_contract_ps'), s.get('kit_contract_window_needed_ps'), s.get('kit_contract_verdict'))
