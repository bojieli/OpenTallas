import json, sys
V, f = sys.argv[1:]
d = json.load(open(f))
tot = 0
for k, v in sorted(d['masters'].items()):
    if k.startswith(('qkd_host_root', 'qkd_d2d_cal', 'qkd_d2d_static')):
        print(V, k, v['verdict'], 'open', v['output_open'], 'unconn', list(v['input_unconnected'])[:6], 'w', v['width_mismatch'] if isinstance(v['width_mismatch'], int) else list(v['width_mismatch'])[:4],
              'notinrtl', list(v['die_port_not_in_rtl'])[:4])
    tot += len(v.get('output_open', []))
obs = [p for k, v in d['masters'].items() for p in v.get('output_open', [])
       if (k, p) in {('qkd_d2d_cal_seq_pin_bc4', x) for x in ('adm_done', 'cal_ready', 'running', 'layer')} | {('qkd_d2d_static', 'recovery_cycles')}]
print(V, 'OBSX-target opens', len(obs), obs, '| total OUTPUT_OPEN ports', tot, '| verdict', d['verdict'],
      '| unread nets', len(d.get('unread_nets', [])), 'undriven', len(d.get('undriven_nets', [])))
