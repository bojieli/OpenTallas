#!/usr/bin/env python3
"""BUS-GEAR-1 (2026-11-12, DIE-S81-87 ask for ready12b): S81 x feed 2:1 die integration.

Rewrites the logical die top (physical/die_plan/s81/bind/inputs/die_b178.v) and the as-built frame models
(physical/die_plan/s81/bind/models/s81_asb_models.sv) for the geared x feed (rtl/dsrom_sys/s81_dv/xgear/):

  slices   every slice instance with an xc port: the xc port drives a new wire <slice>_xcw; a glue instance
           u_xg_<slice> (ot_s81_xc_gear_tx, lane clocks = the slice's ck_xc, reset = the slice's rst_n) drives the
           original xc concatenation with every x lane at 139 b; xc groups that carry no x lane (nc) are GEN 0
  stations every st_x_* station dsfd_dvrlyh_276_<dir> -> dsfd_dvrlyh_139_<dir>; x lane wires 276 -> 139 b
  frames   col_h<9|10>_l4_lp_asb_<x|nx> -> ..._<x|nx>g (x / xo 1104 -> 556 b: ot_s81_xframe_gear lands the beats in
           front of u_r0 and forwards them on xo through the frame's 2 x -> xo stages; u_r0's own xo is left open)
  pf_xo    frame-to-frame abutted xo wires 1104 -> 556 b

Fail-closed: every x lane wire / station / frame / slice group is accounted for (counts printed and checked against
the netlist), nothing else in the netlist changes.  The as-built JSON gets the new netlist, the gear sources, the new
frame models in `dissolve`, and map parts u_xg_<slice> -> <slice partition of the slice instance>.

usage: xgear_die.py DIE_IN.v MODELS_IN.sv ASBUILT_IN.json OUT_DIR
       (writes OUT_DIR/die_b178_xg.v, OUT_DIR/s81_asb_xgear_models.sv, OUT_DIR/asbuilt_xg.json, OUT_DIR/xgear_report.json)
"""
import json, re, sys
from pathlib import Path

LW, BL = 276, 139
XNAME = re.compile(r'^(w_x_f_\w+_l[0-3]_(src|dst)|r_x_f_\w+_l[0-3]_\d+)$')


def die_rewrite(s, rep):
    out = []
    n_decl = n_pf = n_st = n_fr = n_sl = 0
    sl_glue = []
    lines = s.split('\n')
    # lane clock index of every slice x lane, from the hop-0 forwarded-clock gates
    ck_of = {}
    for m in re.finditer(r'ICGx4_ASAP7_75t_R fwd_x_f_(\w+?)_l([0-3]) \(\.CLK\((u_s_\w+?)_ck_xc\[(\d+)\]\)', s):
        ck_of[(m.group(1), int(m.group(2)))] = (m.group(3), int(m.group(4)))
    for ln in lines:
        m = re.match(r'^(\s*)wire \[275:0\] (.*);(.*)$', ln)
        if m and all(XNAME.match(x.strip()) for x in m.group(2).split(',')):
            ln = '%swire [%d:0] %s;%s' % (m.group(1), BL - 1, m.group(2), m.group(3)); n_decl += 1
        elif m and any(XNAME.match(x.strip()) for x in m.group(2).split(',')):
            raise SystemExit('mixed x / non-x wire declaration: ' + ln[:200])
        m = re.match(r'^(\s*)wire \[1103:0\] (pf_xo_\w+);(.*)$', ln)
        if m:
            ln = '%swire [%d:0] %s;%s' % (m.group(1), 4 * BL - 1, m.group(2), m.group(3)); n_pf += 1
        m = re.match(r'^(\s*)dsfd_dvrlyh_276_(NS|SN|EW|WE) (st_x_f_\w+) \(', ln)
        if m:
            ln = ln.replace('dsfd_dvrlyh_276_%s %s' % (m.group(2), m.group(3)), 'dsfd_dvrlyh_%d_%s %s' % (BL, m.group(2), m.group(3)), 1)
            n_st += 1
        m = re.match(r'^(\s*)(col_h(?:9|10)_l4_lp_asb_(?:x|nx)) (#\(.*?\) )?(u_f_\w+) \(', ln)
        if m:
            ln = ln.replace(m.group(2) + ' ', m.group(2) + 'g ', 1); n_fr += 1
        # x lane slices [275:0] -> [138:0] in concatenations
        ln = re.sub(r'\b(w_x_f_\w+?_l[0-3]_(?:src|dst))\[275:0\]', r'\1[%d:0]' % (BL - 1), ln)
        if '.xc(' in ln and re.match(r'^\s*ot_s81sl_slice_\w+ ', ln):
            mi = re.match(r'^(\s*)(ot_s81sl_slice_\w+) (#\(.*?\) )?(u_s_\w+) \(', ln)
            inst = mi.group(4)
            mx = re.search(r'\.xc\(\{([^}]*)\}\)', ln)
            items = [x.strip() for x in mx.group(1).split(',')]
            # groups of 4 x 276 (one x lane group) or one 1104-b nc wire; MSB first
            groups, i = [], 0
            while i < len(items):
                it = items[i]
                mm = re.match(r'^(w_x_f_(\w+?)_l3_src)\[%d:0\]$' % (BL - 1), it)
                if mm:
                    f = mm.group(2)
                    want = ['w_x_f_%s_l%d_src[%d:0]' % (f, k, BL - 1) for k in (3, 2, 1, 0)]
                    if items[i:i + 4] != want:
                        raise SystemExit('slice %s: x group %s not 4 lanes l3..l0' % (inst, f))
                    groups.append(('x', f)); i += 4
                elif re.match(r'^%s_xc_nc\d+\[1103:0\]$' % inst, it):
                    groups.append(('nc', it.split('[')[0])); i += 1
                else:
                    raise SystemExit('slice %s: unexpected xc item %s' % (inst, it))
            ng = len(groups)
            gl = list(reversed(groups))          # gl[g] = group g (LSB first)
            gen = ''.join('1' if k == 'x' else '0' for k, _ in groups)   # MSB first = group ng-1 .. 0
            cks = []
            for g, (k, f) in enumerate(gl):
                for l in range(4):
                    if k == 'x':
                        sl, idx = ck_of[(f, l)]
                        if sl != inst or idx != 4 * g + l:
                            raise SystemExit('slice %s group %d lane %d: forwarded clock %s[%d]' % (inst, g, l, sl, idx))
                    cks.append('%s_ck_xc[%d]' % (inst, 4 * g + l))
            rst = re.search(r'\.rst_n\(([^)]*)\)', ln).group(1)
            xb = []
            for k, f in groups:
                if k == 'x':
                    xb += ['w_x_f_%s_l%d_src[%d:0]' % (f, l, BL - 1) for l in (3, 2, 1, 0)]
                else:
                    xb.append('%s_xb[%d:0]' % (f, 4 * BL - 1))
            ln = ln.replace(mx.group(0), '.xc(%s_xcw)' % inst, 1)
            glue = ['  wire [%d:0] %s_xcw;   // BUS-GEAR-1: slice xc -> u_xg_%s (ot_s81_xc_gear_tx)' % (ng * 4 * LW - 1, inst, inst)]
            glue += ['  wire [%d:0] %s_xb;' % (4 * BL - 1, f) for k, f in groups if k == 'nc']
            glue.append("  ot_s81_xc_gear_tx #(.NG(%d), .GEN(%d'b%s)) u_xg_%s (.ck({%s}), .rst_n(%s), .xc(%s_xcw), .xb({%s}));"
                        % (ng, ng, gen, inst, ', '.join(reversed(cks)), rst, inst, ', '.join(xb)))
            sl_glue.append(dict(inst=inst, groups=[k + ':' + f for k, f in groups]))
            out.extend(glue)
            n_sl += 1
        out.append(ln)
    t = '\n'.join(out)
    left = re.findall(r'\b(?:w_x_f_\w+?_l[0-3]_(?:src|dst)|r_x_f_\w+)\[275:0\]', t)
    if left:
        raise SystemExit('x lane 276-b slices left: %s' % left[:3])
    rep.update(x_wire_decl_lines=n_decl, pf_xo=n_pf, stations=n_st, frames=n_fr, slices=n_sl, slice_glue=sl_glue,
               lane_clocks=len(ck_of))
    return t


def models_rewrite(s, rep):
    out = ['`timescale 1ns/1ps',
           '// GENERATED by physical/die_plan/s81/bind/xgear_die.py (BUS-GEAR-1) from s81_asb_models.sv: geared as-built',
           '// frames.  x / xo carry 4 x 139-b beat lanes; ot_s81_xframe_gear lands the word in front of u_r0 (x_i0) and',
           '// forwards the beats on xo through FW = 2 stages (the frame\'s own x -> xo stages); u_r0.xo_o0 stays open.']
    n = 0
    for m in re.finditer(r'(// GENERATED[^\n]*\n)?module (col_h(?:9|10)_l4_lp_asb_(x|nx)) (#\(.*?\)) \((.*?)\nendmodule', s, re.S):
        name, kind, par, body = m.group(2), m.group(3), m.group(4), m.group(5)
        b = body.replace('input  wire [1103:0] x,', 'input  wire [%d:0] x,' % (4 * BL - 1))
        b = b.replace('output wire [1103:0] xo,', 'output wire [%d:0] xo,' % (4 * BL - 1))
        if kind == 'x':
            if '.x_i0(x), .xo_o0(xo)' not in b:
                raise SystemExit(name + ': u_r0 x/xo binding not found')
            b = b.replace('.x_i0(x), .xo_o0(xo)', '.x_i0(x_land), .xo_o0(xo_open)')
            glue = ('    wire [1103:0] x_land;\n    /* verilator lint_off UNUSEDSIGNAL */\n    wire [1103:0] xo_open;   '
                    '// the band\'s word forward is not used (beats are forwarded)\n    /* verilator lint_on UNUSEDSIGNAL */\n'
                    '    ot_s81_xframe_gear #(.FW(2)) u_xg (.ck(ck_r0), .rst_n(rst_n), .xb_i(x), .x_o(x_land), .xb_o(xo));\n')
        else:
            if '.x_i0(x),' not in b:
                raise SystemExit(name + ': u_r0 x binding not found')
            b = b.replace('.x_i0(x),', '.x_i0(x_land),')
            glue = ('    wire [1103:0] x_land;\n    /* verilator lint_off PINCONNECTEMPTY */\n'
                    '    ot_s81_xframe_gear #(.FW(0)) u_xg (.ck(ck_r0), .rst_n(rst_n), .xb_i(x), .x_o(x_land), .xb_o());\n'
                    '    /* verilator lint_on PINCONNECTEMPTY */\n')
        i = b.index(');\n') + 3
        b = b[:i] + glue + b[i:]
        out.append('module %sg %s (%s\nendmodule\n' % (name, par, b))
        n += 1
    rep['frame_models'] = n
    if n != 4:
        raise SystemExit('expected 4 frame models, got %d' % n)
    return '\n'.join(out)


def main():
    die_in, mod_in, ab_in, od = sys.argv[1:5]
    od = Path(od); od.mkdir(parents=True, exist_ok=True)
    rep = {}
    t = die_rewrite(Path(die_in).read_text(), rep)
    (od / 'die_b178_xg.v').write_text(t)
    (od / 's81_asb_xgear_models.sv').write_text(models_rewrite(Path(mod_in).read_text(), rep))
    ab = json.loads(Path(ab_in).read_text())
    rep['asbuilt_in'] = ab_in
    ab['netlist'] = ['physical/die_plan/s81/bind/inputs/die_b178_xg.v']
    ab['netlist_note'] = (ab.get('netlist_note', '') + ' | BUS-GEAR-1 11-12: die_b178_xg.v = die_b178.v with the x feed '
                          'geared 2:1 (xgear_die.py)').strip(' |')
    add = ['rtl/common/ot_bus_gear.sv', 'rtl/dsrom_sys/s81_dv/xgear/ot_s81_xlane_gear.sv',
           'rtl/dsrom_sys/s81_dv/xgear/ot_s81_xgear_die.sv', 'physical/die_plan/s81/bind/models/s81_asb_xgear_models.sv']
    ab['files'] = list(ab['files']) + [f for f in add if f not in ab['files']]
    ab['dissolve'] = list(ab['dissolve']) + [m + 'g' for m in ('col_h9_l4_lp_asb_x', 'col_h9_l4_lp_asb_nx',
                                                                 'col_h10_l4_lp_asb_x', 'col_h10_l4_lp_asb_nx')
                                             if m + 'g' not in ab['dissolve']]
    mf = json.loads(Path(ab['map_file']).read_text()) if ab.get('map_file') else {}
    parts = dict(mf.get('parts', {})); parts.update(ab.get('map', {}).get('parts', {}))
    mp = dict(ab.get('map', {})); mp.setdefault('parts', {})
    for g in rep['slice_glue']:
        part = parts.get(g['inst'])
        if not part:
            raise SystemExit('no map partition for ' + g['inst'])
        mp['parts']['u_xg_' + g['inst']] = part
    ab['map'] = mp
    (od / 'asbuilt_xg.json').write_text(json.dumps(ab, indent=1))
    (od / 'xgear_report.json').write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k != 'slice_glue'}))


if __name__ == '__main__':
    main()
