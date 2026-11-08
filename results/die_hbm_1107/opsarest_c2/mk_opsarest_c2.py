#!/usr/bin/env python3
"""DIE-HBM-90-OPSA d44v plan event opsarest_c2_1107 (COORD 11-07 23:01 (4)(iii)): ot_hgi_sfu_opsa_rest takes the compact
signed form vC2, outline 250.56 x 64.8 (was 760.32 x 86.4), so the signed DB counts with no rebuild.

mk_opsarest_c2.py PLANDIR NEW_TABLE.json OPSA_CONN.json REPORT.json      (in place on PLANDIR = plan_of_record/d44v)

  NEW_TABLE.json  pins of the signed routed DB: intel1 hbm-hard-2/kits/opsaC2_mw100/run/results/asap7/
                  hbc_ot_hgi_sfu_opsa_rest/base/6_final.def (sha256 of 6_final.odb 76eb665c...) read with the coord
                  counter's own DEF reader (release_tree_plan.py REC_PINS_PY _read_def: centre of each pin's first
                  PORT shape), via opsarest_defpins.py
  OPSA_CONN.json  results/die_hbm_1105/form_split/p27/opstore_a.conn.json (per-bit nets of the part 27 split)

Placement: POR orient MX at ORIGIN (1131.84, 959.04) (8.64 lattice) inside the old slot: minimax of the real driver->sink links over a
R0/MX/MY/R180 x 4.32-lattice sweep (opsarest_sweep2.py); every reg-to-reg link <= 452.5 um (reach.py measured one-cycle
reach at 833 ps), so no cycle is added.  Parent changes,
both q_b113 and q_b113__physical_v1 (identical rows):
  * hard_cores row u_sfucore_Q_opstore_a__r: outline + pins_file;
  * clock tap u_sfucore_Q_opstore_a__r.clk + clock_entries.json entry: the signed clk pin (125.28, 32.4);
  * internal_stations launched by rest: from_um / to_um re-anchored on the new pins, a chain whose worst bit hop
    is > 405 um re-sited with the SAME register count (no cycle change);
  * group fault seams opsa_group0/1.flt -> group_fault_01: asserted <= 452.5 um (one cycle kept, fault 0).
Idempotence: asserts the POR rows, so it runs once on a plan carrying the POR opsa_rest rows (any other event on top
or below is fine if it does not touch these rows)."""
import gzip, hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import opsarest_lib as L

EID = 'opsarest_c2_1107'
NEW = 'cores/ot_hgi_sfu_opsa_rest__250.56x64.8__d44v_opsarest_c2.json'
TYPES = ('q_b113', 'q_b113__physical_v1')
RI = L.RI
ORIGIN = (float(os.environ.get('OPSA_X0', '1131.84')), float(os.environ.get('OPSA_Y0', '959.04')))   # chosen by opsarest_sweep (event: placement)
CLK_ENTRY = [125.28, 32.4]          # signed DB clk pin centre (125.304, 32.4) = entry + 0.024, same convention as POR (380.184 vs 380.16)
NOTE = (' | DIE-HBM-90-OPSA ' + EID + ': compact signed form vC2 250.56x64.8 (intel1 hbm-hard-2/resign/opsaC2_du, '
        'LOCAL_PASS_NEEDS_PARENT, LEC EQ), MX at the W end of the old 760.32x86.4 slot')
HALO = 4.32
CH_Y = (915.84, 933.12)             # rest <-> opsb_g0 channel lattice rows (y 907.2 .. 941.76, halo 4.32 kept)


def gzw(path, raw):
    with open(path, 'wb') as f:
        with gzip.GzipFile(fileobj=f, mode='wb', mtime=0, filename='') as g: g.write(raw)
    return hashlib.sha256(raw).hexdigest()


def dump(o): return (json.dumps(o) + '\n').encode()


def main():
    d, newt, oconn, rep_path = sys.argv[1:5]
    P = json.load(gzip.open(f'{d}/die_plan.json.gz'))
    cc = json.load(gzip.open(f'{d}/core_conns.json.gz'))
    por_tab = json.load(gzip.open(f'{d}/{L.OLD_TABLE}.gz'))
    new_tab = json.load(open(newt))
    assert len(new_tab) == len(por_tab) == 4336
    pl = {q['name']: q['layer'] for q in por_tab}
    assert set(pl) == {q['name'] for q in new_tab} and all(pl[q['name']] == q['layer'] for q in new_tab), 'pin names/layers differ'
    W_, H_ = L.NEW_WH
    assert all(0 <= q['x'] <= W_ and 0 <= q['y'] <= H_ for q in new_tab)
    clk = [q for q in new_tab if q['name'] == 'clk'][0]
    assert abs(clk['x'] - CLK_ENTRY[0] - 0.024) < 1e-6 and abs(clk['y'] - CLK_ENTRY[1]) < 1e-6, clk
    oc = json.load(open(oconn))
    x0, y0 = ORIGIN
    rep = dict(event=EID, placement=dict(orient='MX', origin_um=[x0, y0], outline_um=[W_, H_]), types={})
    for tn in TYPES:
        t = P['partition_types'][tn]
        rows = [h for h in t['hard_cores'] if h['inst'] == RI]
        assert len(rows) == 1
        h = rows[0]
        assert h['pins_file'] == L.OLD_TABLE and h['outline_um'] == [760.32, 86.4] and h['origin_um'] == list(L.SLOT['origin']) and h['orient'] == 'MX', h
        # measurement on the POR rows first (Ctx reads the POR plan state)
        C = L.Ctx(d, P, cc, oc, por_tab, new_tab, tn)
        pp = L.place(new_tab, 'MX', x0, y0, W_, H_)
        NB = (x0, y0, x0 + W_, y0 + H_)
        boxes = dict(C.boxes); boxes[RI] = NB
        def legal(pt):
            return all(not (b[0] - HALO < pt[0] < b[2] + HALO and b[1] - HALO < pt[1] < b[3] + HALO) for b in boxes.values())
        tr = dict(pins=[], out_box=[], in_box=[], sibling=[], stations=[], added=[])
        for n in sorted(pp):
            tr['pins'].append([n, [round(v, 3) for v in C.por[n]], [round(v, 3) for v in pp[n]], round(L.man(C.por[n], pp[n]), 3)])
        for nm, a, b in (('out_box', C.out_box(C.por), C.out_box(pp)), ('in_box', C.in_box(C.PB), C.in_box(NB)), ('sibling', C.sib(C.por), C.sib(pp))):
            for k in sorted(b):
                tr[nm].append([list(k), round(a.get(k, 0.0), 1), round(b[k], 1)])
        # --- station chains launched by rest: re-anchor, re-site (same count) when a worst-bit hop > REACH
        for i, e in enumerate(t['internal_stations']):
            if not e['launch'].startswith(RI + '.'):
                if e.get('capture') == RI:
                    cb = [n for n in pp if L.bus(n) in L.CAPMAP[e['launch'].split('.', 1)[1]]]
                    lr = e['regs_um'][-1]
                    a_ = max(L.man(lr, C.por[n]) for n in cb); b_ = max(L.man(lr, pp[n]) for n in cb)
                    assert b_ <= L.REACH, (i, e['conn'], b_)   # register sites kept
                    old_to = list(e['to_um'])
                    e['to_um'] = [round(min(max(lr[0], NB[0]), NB[2]), 3), round(min(max(lr[1], NB[1]), NB[3]), 3)]
                    if e['to_um'] != old_to:
                        e['note'] = e.get('note', '') + ' | DIE-HBM-90-OPSA ' + EID + ': to_um re-anchored on the compact rest box, sites kept'
                    tr['stations'].append(dict(i=i, conn=e['conn'], regs=len(e['regs_um']), kind='capture', last_reg_to_pins_por=round(a_, 1), last_reg_to_pins_new=round(b_, 1), to_um=[old_to, e['to_um']], changed=False))
                continue
            b = e['launch'].split('.', 1)[1]
            bits = sorted(n for n in pp if L.bus(n) == b)
            if e['bits'] == 1 and len(bits) > 1:
                bits = [min(bits, key=lambda n: L.man(C.por[n], e['from_um']))]
            cap = boxes[e['capture']]
            fr = [round(sum(pp[n][0] for n in bits) / len(bits), 3), round(sum(pp[n][1] for n in bits) / len(bits), 3)]
            to = [round(min(max(fr[0], cap[0]), cap[2]), 3), round(min(max(fr[1], cap[1]), cap[3]), 3)]
            def worst(regs, pts):
                h1 = max(L.man(pts[n], regs[0]) for n in bits)
                return max([h1] + [L.man(p, q) for p, q in zip(regs, regs[1:] + [to])])
            hp = worst(e['regs_um'], C.por)
            regs = e['regs_um']; changed = False
            if worst(regs, pp) > L.REACH:
                xs = sorted(pp[n][0] for n in bits); xm = L.lattice((xs[0] + xs[-1]) / 2)
                xm = min(max(xm, L.lattice(cap[0] + HALO + 4.32)), L.lattice(cap[2]))
                ys = list(CH_Y) if len(regs) == 2 else [CH_Y[1]]
                assert len(regs) in (1, 2)
                regs = [[xm, y] for y in ys]; changed = True
                assert all(legal(r) for r in regs), (i, regs)
            hn = worst(regs, pp)
            assert hn <= L.REACH, (i, e['conn'], hn)
            e['from_um'], e['to_um'], e['regs_um'] = fr, to, regs
            e['note'] = e.get('note', '') + ' | DIE-HBM-90-OPSA ' + EID + (': ends re-anchored on the compact pins, %d station(s) re-sited, count kept' % len(regs) if changed else ': ends re-anchored on the compact pins, sites kept')
            tr['stations'].append(dict(i=i, conn=e['conn'], regs=len(regs), kind='launch', worst_hop_por=round(hp, 1), worst_hop_new=round(hn, 1), changed=changed))
        # --- fault seams opsa_group0/1.flt -> rest group_fault_01[k] (direct wires, no station in POR): one cycle while the
        #     pin-to-pin length is <= the measured one-cycle reach (reach.MEASURED M4-M7 452.5 um, 833 ps TT); else +1 station
        for k, gi in ((0, 'u_sfucore_Q_opstore_a__g0'), (1, 'u_sfucore_Q_opstore_a__g1')):
            a, bpin = C.tab(gi)['flt'], pp['group_fault_01[%d]' % k]
            tr['fault_seams'] = tr.get('fault_seams', []) + [dict(conn=f'{gi}.flt|{RI}', pin='group_fault_01[%d]' % k,
                pin_to_pin_por=round(L.man(a, C.por['group_fault_01[%d]' % k]), 1), pin_to_pin_new=round(L.man(a, bpin), 1))]
            assert L.man(a, bpin) <= L.MEASURED_REACH, (gi, L.man(a, bpin))
        # --- core row + tap
        h['origin_um'] = [x0, y0]; h['outline_um'] = [W_, H_]; h['pins_file'] = NEW; h['note'] = h.get('note', '') + NOTE
        taps = [k for k in t['clock']['taps'] if k['name'] == RI + '.clk']
        assert len(taps) == 1 and taps[0]['xy'] == [1460.16, 984.96], taps
        tx, ty = L.orient('MX', W_, H_, *CLK_ENTRY)
        taps[0]['xy'] = [round(x0 + tx, 3), round(y0 + ty, 3)]
        taps[0]['note'] = taps[0].get('note', '') + ' | DIE-HBM-90-OPSA ' + EID + ': tap on the signed clk pin of the compact form'
        tr['tap'] = taps[0]['xy']
        rep['types'][tn] = tr
    ce = json.load(gzip.open(f'{d}/clock_entries.json.gz')); m = 0
    for tn in TYPES:
        e = ce[tn][RI]
        assert e['xy_um'] == [380.16, 43.2] and e['module'] == 'ot_hgi_sfu_opsa_rest'
        e['xy_um'] = list(CLK_ENTRY); e['island_um'] = [round(CLK_ENTRY[0] - 4.32, 3), round(CLK_ENTRY[1] - 4.32, 3), round(CLK_ENTRY[0] + 4.32, 3), round(CLK_ENTRY[1] + 4.32, 3)]
        e['source'] = e['source'] + ' | DIE-HBM-90-OPSA ' + EID + ': signed vC2 clk pin (125.304, 32.4) of the 250.56x64.8 form (not on the 4.32 y lattice: the signed site)'
        m += 1
    raw_t = dump(new_tab)
    ts = gzw(f'{d}/{NEW}.gz', raw_t)
    ps = gzw(f'{d}/die_plan.json.gz', dump(P))
    cs = gzw(f'{d}/clock_entries.json.gz', dump(ce))
    tsv = ('core\tsub_block\tport_or_bus\tdir\tadded_cycles\tnote\n'
           'ot_hgi_sfu_opsa_rest\t\t*\tport\t0\tDIE-HBM-90-OPSA ' + EID + ': compact signed form vC2 250.56x64.8; RTL = main '
           'rtl/hbm_accel/cores_split/reform_1105s/opstore/ot_hgi_sfu_opsa_rest.sv (sha256 3bb79349, byte-identical at build_commit '
           '7281ac2667; kit top renamed __fcore by the face shell); face shell in 1 / out 1 / reset relay 2 = the POR kit form; '
           'parent station counts kept; fault 0 (group fault seams opsa_group0/1.flt -> group_fault_01 stay one cycle: '
           'pin to pin <= 452.5 um measured reach)\n')
    os.makedirs(f'{d}/corelat', exist_ok=True)
    open(f'{d}/corelat/cycles_{EID}.tsv', 'w').write(tsv); ls = hashlib.sha256(tsv.encode()).hexdigest()
    t0 = rep['types']['q_b113']
    disp = [r[3] for r in t0['pins']]
    over = sorted({(tuple(k), round(v, 1)) for nm in ('out_box', 'in_box') for k, _, v in t0[nm] if v > L.REACH and nm == 'out_box'}
                  | {(tuple(k), round(v, 1)) for k, _, v in t0['in_box'] if v > L.REACH and k[0] == 'u_sfucore_Q_ctl__rest'})
    over += [((f['conn'], f['pin']), f['pin_to_pin_new']) for f in t0['fault_seams'] if f['pin_to_pin_new'] > L.REACH]
    assert all(v <= L.MEASURED_REACH for _, v in over)
    ev = {
        "schema": "opentallas.hbm_plan_event.v1", "event": EID, "plan": "d44v", "lane": "DIE-HBM-90-OPSA (under DIE-HBM-90)",
        "date": "2026-11-07",
        "approved": "COORD RULING 11-07 23:01 (4)(iii) + COUNT-AUDIT-2 22:54 (B)(3): PART event owed so the signed vC2 counts with no rebuild; COORD 11-07 13:12 batch after source + fault-cycle qualification",
        "what": [
            "ot_hgi_sfu_opsa_rest (u_sfucore_Q_opstore_a__r, q_b113 + q_b113__physical_v1): outline 760.32x86.4 -> 250.56x64.8, origin (1080, 941.76) -> (%.2f, %.2f), orient MX kept, inside the old slot" % (x0, y0),
            "table %s = the 4336 pins of the signed routed DB (6_final.def beside 6_final.odb sha256 76eb665c, read with release_tree_plan.py REC_PINS_PY _read_def); names and layers equal the POR table; pin move mean %.1f / max %.1f um in die coordinates" % (NEW, sum(disp) / len(disp), max(disp)),
            "clock tap %s.clk -> %s, clock_entries xy (380.16, 43.2) -> (125.28, 32.4) (signed clk pin 125.304, 32.4)" % (RI, t0['tap']),
            "internal_stations launched by rest (12 per type): from/to re-anchored on the compact pins, %d re-sited with the SAME register count; capture chains at rest (12): to_um re-anchored, sites kept" % sum(1 for x in t0['stations'] if x['changed']),
            "corelat/cycles_%s.tsv: 0 added cycles on every rest port, fault 0" % EID,
        ],
        "placement": "sweep R0/MX/MY/R180 x the 4.32 lattice of the old slot (opsarest_sweep2): minimax over the real driver->sink links (ctl_rest -> rest box, rest -> partner box (check.py R3-INTERNAL form), opsa_group0/1.flt -> group_fault_01 pin to pin); best %.1f um here; W end (1080, 941.76) puts opsa_group0.flt -> group_fault_01[0] at 505 um (> 452.5 measured one-cycle reach: would need a parent cycle in the wires-only split glue); centred puts 5 ctl_rest links at 420-478 um" % max(v for _, v in over) if over else "",
        "timing_833ps": {
            "model": "tools/die_plan/reach.py: measured one-cycle reach M4-M7 452.5 um (REACH-M89 relay to relay, TT 833.333 ps, unc 60 + skew 90; 0.76 ps/um planning constant x1.203), owner plan cap 405 um for local hops, repeaters <= 450 um",
            "links_over_405_within_452.5": [[list(k), v] for k, v in over],
            "station_hops_max": max(max(x.get('worst_hop_new', 0), x.get('last_reg_to_pins_new', 0)) for x in t0['stations']),
            "fault_seams": t0['fault_seams'],
            "verdict": "every reg-to-reg link of the moved pins <= 452.5 um: existing cycles meet 833 ps; no PIN CYCLE added, no compiler/token reschedule",
        },
        "fault_cycles": "0: same RTL as the POR row (part 27 opstore_a split, sha256 3bb79349), same face shell (in 1 / out 1 / relay 2), parent station counts unchanged, group fault seams stay one cycle; part 28/29 fault rows (u_engine fault +2 from operand groups 0,1) unchanged",
        "kept": ["origin of every other core", "station register counts (crossing_latency unchanged)", "760.32x86.4 table stays on disk, unused", "core_conns / core_macros (no opsa_rest row) unchanged"],
        "not_measured_here": "sink to sink spans of the type nets rest shares with opsa_group0/1 (rd_addr / rd_re / rd_src, driven by the type's soft logic / face buses, no plan station): report rows 'sibling' / 'in_box'; the type build times them",
        "signed_db": {"record": "intel1 /srv/opentallas-scratch2/claude/hbm-hard-2/resign/opsaC2_du (SIGNED, LOCAL_PASS_NEEDS_PARENT, flow-20261107-du-hbm)",
                      "routed_db": "intel1 .../hbm-hard-2/kits/opsaC2_mw100/run/results/asap7/hbc_ot_hgi_sfu_opsa_rest/base/6_final.odb sha256 76eb665c",
                      "rtl": "ot_hgi_sfu_opsa_rest.sv identical to main rtl/hbm_accel/cores_split/reform_1105s/opstore/ except module name __fcore",
                      "build_commit": "7281ac2667", "src_commit": "b1485eaa469"},
        "report": "results/die_hbm_1107/opsarest_c2/opsarest_c2_report.json",
        "replay": "python3 -I results/die_hbm_1107/opsarest_c2/mk_opsarest_c2.py physical/die_plan/hbm/plan_of_record/d44v results/die_hbm_1107/opsarest_c2/opsa_rest_vC2_pins.json results/die_hbm_1105/form_split/p27/opstore_a.conn.json results/die_hbm_1107/opsarest_c2/opsarest_c2_report.json",
    }
    raw_e = (json.dumps(ev, indent=1) + '\n').encode()
    open(f'{d}/{EID}_event.json', 'wb').write(raw_e); es = hashlib.sha256(raw_e).hexdigest()
    rd_ = open(f'{d}/README.md').read()
    assert EID not in rd_
    rd_ += ('\nEvent ' + EID + ' (DIE-HBM-90-OPSA 11-07, under DIE-HBM-90; COORD 23:01 (4)(iii)): ot_hgi_sfu_opsa_rest takes its signed compact form vC2 '
            '(intel1 hbm-hard-2/resign/opsaC2_du, build_commit 7281ac2667 = main RTL): outline 250.56x64.8, MX at (%.2f, %.2f) inside the old 760.32x86.4 slot '
            'in q_b113 / q_b113__physical_v1, table %s from the routed DEF, clock tap + clock_entries on the signed clk pin, rest station chains re-anchored '
            '(counts kept). Every moved reg-to-reg link <= 452.5 um (reach.py measured one-cycle reach at 833 ps); PIN CYCLES 0, fault cycles 0. '
            '%s_event.json, corelat/cycles_%s.tsv.\n') % (x0, y0, NEW, EID, EID)
    open(f'{d}/README.md', 'w').write(rd_); rs = hashlib.sha256(rd_.encode()).hexdigest()
    s = []
    for l in open(f'{d}/SHA256SUMS').read().splitlines():
        h, name = l.split(None, 1); name = name.strip()
        s.append({'die_plan.json': f'{ps}  {name}', 'clock_entries.json': f'{cs}  {name}', 'README.md': f'{rs}  {name}'}.get(name, l))
    s += [f'{ts}  {NEW}', f'{ls}  corelat/cycles_{EID}.tsv', f'{es}  {EID}_event.json']
    open(f'{d}/SHA256SUMS', 'w').write('\n'.join(s) + '\n')
    json.dump(rep, open(rep_path, 'w'), indent=0)
    print('OK', ts[:12], ps[:12], cs[:12], ls[:12], es[:12])


if __name__ == '__main__':
    main()
