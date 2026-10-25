import json, subprocess, os, re
W = '/home/ubuntu/wt/core-hbm-1023'; H = '/home/ubuntu/scratch/core-hbm-1023'
D = '/srv/opentallas-scratch/claude/core-hbm-1023/kits_other'
R = json.load(open(W + '/physical/die_plan/hbm/cores/harden/recipes_other.json'))
cen = {}
for c in ('census_0ea1350db.json', 'census_3a7e22238.json'):
    for v in json.load(open(W + '/physical/die_plan/hbm/cores/harden/' + c))['types']:
        cen.setdefault(c, {})[(v['type_id'], v['pins_file'].split('/')[-1][:-5])] = v
closed = json.load(open(W + '/physical/die_plan/hbm/cores/harden/other_closed_views.json'))
plan = json.load(open(W + '/physical/die_plan/hbm/die_plan.json'))
notes = {}
for tn, t in plan['partition_types'].items():
    for c in t.get('hard_cores', []):
        notes.setdefault(c['module'], c.get('note', ''))
os.makedirs(H + '/other/res', exist_ok=True)
out = {}
for k, r in R.items():
    if k.startswith('_'): continue
    t, _, stem = k.partition('@')
    kit = t + ('-' + stem if stem else '')
    run_kit = kit if k != 'hfd_ep_static__434.72x371.52@hfd_ep_static__434.72x371.52' else 'hfd_ep_static__434.72x371.52-hfd_ep_static'
    res = {}
    for h in ('ot-epyc5', 'ot-epyc7', 'ot-epyc9', 'ot-gold2'):
        p = subprocess.run(['ssh', h, f'cd {D}/{run_kit} 2>/dev/null && cat pin_reg_audit.json && echo ===SEP=== && cat odb_stats.json'],
                           capture_output=True, text=True)
        if '===SEP===' in p.stdout and p.stdout.split('===SEP===')[1].strip():
            a, b = p.stdout.split('===SEP==='); res = dict(audit=json.loads(a), stats=json.loads(b), host=h); break
    fz = json.load(open(f'{H}/kits_other/{kit}/freeze.json'))
    w, hh = fz['outline_um']
    # census entry (P6 first)
    ce = None
    for c in ('census_3a7e22238.json', 'census_0ea1350db.json'):
        for (tid, ps), v in cen[c].items():
            if tid == t and (not stem or ps == stem):
                ce = ce or (c, v)
    e = dict(type_id=t, pins_file=fz['pins_file'], top=r['top'], params=r['params'], defines=r['defines'],
             macros=r['macros'], recipe_source=r['source'], source_commit=r['source_commit'],
             die_instances=ce[1]['die_instances'] if ce else None, census=ce[0] if ce else None,
             outline_um=[w, hh], plan_pins=fz['pins'], plan_note=notes.get(r['top'], ''))
    if not res:
        e['synth'] = 'NO RESULT'; out[k] = e; continue
    s, a = res['stats'], res['audit']
    mac_area = s['macros'].get('_area', 0.0)
    skip = set(fz['clocks'] + fz['resets'])
    ckre = re.compile(r'(clk|^ck_|_ck$|rck$|tck$|rst|^rstb)')
    skip |= {b for b in list(a['unreg_in_buses']) + list(a['unreg_out_buses']) if ckre.search(b)}
    ui = {b: n for b, n in a['unreg_in_buses'].items() if b not in skip}
    uo = {b: n for b, n in a['unreg_out_buses'].items() if b not in skip}
    e.update(synth='OK', synth_host=res['host'], kit_hash=fz['kit_hash'], synth_cells=s['cells'], ffs=s['ffs'],
             std_area_um2=s['std_area_um2'], macro_insts={m: n for m, n in s['macros'].items() if m != '_area'},
             macro_area_um2=round(mac_area, 1),
             fill_std_pct=round(100 * s['std_area_um2'] / (w * hh), 1),
             fill_std_plus_macro_pct=round(100 * (s['std_area_um2'] + mac_area) / (w * hh), 1),
             port_bits=s['port_bits'], port_bits_match_plan=s['port_bits'] == fz['pins'],
             pin_reg=dict(verdict='PASS' if not ui and not uo else 'FAIL', signal_bits=a['bits'], ok=a['ok'],
                          unreg_in=sum(ui.values()), unreg_out=sum(uo.values()), const_out=a['const_out'],
                          unconnected=a['unconnected'], unreg_in_buses=ui, unreg_out_buses=uo,
                          clock_reset_ports_ignored=sorted(skip & (set(a['unreg_in_buses']) | set(a['unreg_out_buses'])))),
             over_400k=s['cells'] > 400000,
             fill_flag=('HIGH (>60% std+macro at plan util 0.5)' if (s['std_area_um2'] + mac_area) / (w * hh) > 0.6 else
                        'LOW (<10%: outline oversized)' if (s['std_area_um2'] + mac_area) / (w * hh) < 0.10 else ''))
    cv = closed.get(k)
    if cv:
        e['closed_view'] = dict(lef=cv['lef'], lef_size=cv.get('lef_size'),
                                vs_plan_pins={f: v for f, v in cv['pins'].items()})
    out[k] = e
json.dump(dict(schema='opentallas.hbm.core_other_status.v1', by='CORE-HBM-OTHER 10-23',
               plan='claude/core-hbm-1023 die_plan.json (P6 3a7e22238)', kits='/home/ubuntu/scratch/core-hbm-1023/kits_other (remote ' + D + ')',
               method='ORFS synth only (asap7lock, SYNTH_HIERARCHICAL 0), odb_stats.py + pin_reg_audit.py on 1_synth.odb; clock/reset ports (freeze.json) excluded from the pin-reg verdict; fill = area / plan outline',
               types=out), open(W + '/physical/die_plan/hbm/cores/harden/other_status.json', 'w'), indent=1)
for k, e in out.items():
    if e.get('synth') != 'OK': print(f"{k[:58]:58s} NO RESULT"); continue
    p = e['pin_reg']
    print(f"{k[:58]:58s} {e['fill_flag'][:4]:4s} {e['synth_cells']:>7} {e['std_area_um2']:>9.0f} {e['fill_std_plus_macro_pct']:>5}% bits {e['port_bits']}/{e['plan_pins']} {p['verdict']} in{p['unreg_in']} out{p['unreg_out']} {list(p['unreg_in_buses'])[:4]}{list(p['unreg_out_buses'])[:3]}")
