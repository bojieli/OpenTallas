# QE3-CTLM3: safe14a (safe12c geometry, FIFO SRAMs gone) / safe14b (W band +86.4 um: every block, region box and N/S pin x += 86.4)
import json, re, sys, shutil
from pathlib import Path
W = Path('/home/ubuntu/wt/qe3-ctlm3'); src = W/'physical/ref_tile/qfd_tt_ctlm_dv_safe12c'
area = float(sys.argv[1]) if len(sys.argv) > 1 else None
for tag, dx in (('safe14a', 0.0), ('safe14b', 86.4)):
    kd = W/f'physical/ref_tile/qfd_tt_ctlm_dv_{tag}'; kd.mkdir(exist_ok=True)
    s = json.loads((src/'spec.json').read_text())
    txt = json.dumps(s).replace('qfd_tt_ctlm_dv_safe12c', f'qfd_tt_ctlm_dv_{tag}').replace('rtl/qwen_dv/lp9e_rr', 'rtl/qwen_dv/lp9f_rr')
    s = json.loads(txt)
    s['macros'] = [m for m in s['macros'] if 'g_fifo' not in m['inst']]
    s['soft_root_macro_bindings'] = {k: v for k, v in s['soft_root_macro_bindings'].items() if 'g_fifo' not in k}
    if dx:
        s['outline']['w'] = round(s['outline']['w'] + dx, 3)
        for m in s['macros'] + s['children']:
            m['at'][0] = round(m['at'][0] + dx, 3)
        rr = s.get('reserved_rom_slots')
        if isinstance(rr, dict) and 'origins_um' in rr:
            rr['origins_um'] = [[round(o[0] + dx, 3), o[1]] for o in rr['origins_um']]
    purpose = (f"QE3-CTLM3 10-21 {tag}: Q.STA.TTC.4 RTL successor of safe12c (CTS reg->reg -897 / FIFO SRAM -780 / native_tok -721): "
               "lp9f_rr = CALREG 15 (FQREG flop ring + registered next head: FIFO SRAMs removed; STARTREG start pre-decode +1; "
               "ISSUEFLAT; NOUTREG native_tok/pos/lcv out regs) -> npl_rename -> replica_role_split. "
               + ("Same geometry as safe12c." if not dx else "W std band +86.4 um beside the calendar block (outline 864 x 734.4)."))
    s['job'].update(owner='QK-ELEM3/QE3-CTLM3', branch='claude/qe3-ctlm3-1021', tag=tag, purpose=purpose)
    s['structural_recut_status'] = purpose
    s['fill_reason'] = {k: (v.replace('6 SRAM', '2 SRAM') if isinstance(v, str) else v) for k, v in s['fill_reason'].items()} if isinstance(s.get('fill_reason'), dict) else s.get('fill_reason')
    if area: s['std_area_um2'] = area
    (kd/'spec.json').write_text(json.dumps(s, indent=1) + '\n')
    for f in ('lcr_dissolve_after_gpl.tcl', 'lp_cone_regions.tcl', 'assigned_pins.tcl'):
        t = (src/f).read_text()
        if dx and f == 'lp_cone_regions.tcl':
            def sh(m):
                xs = m.group(1).split()
                return '{' + ' '.join(str(round(float(v) + (dx if i % 2 == 0 and not (i == 0 and float(v) < 3) else 0), 3)) for i, v in enumerate(xs)) + '}'
            line = [l for l in t.split('\n') if l.startswith('set boxes')][0]
            new = re.sub(r'\{([0-9. ]+)\}', sh, line)
            t = t.replace(line, new + f'   ;# {tag}: x += {dx} (W std band; core box keeps x0 2.16)')
        if dx and f == 'assigned_pins.tcl':
            t = re.sub(r'^(ot_assigned_pin_exact \{[^}]*\} M\d [NS] )([0-9.]+)$', lambda m: f'{m.group(1)}{float(m.group(2)) + dx:.6f}', t, flags=re.M)
            t = f'# {tag} (QE3-CTLM3 10-21): outline +86.4 um on W, every N/S pin x += 86.4 (E/W pins keep their y)\n' + t
        (kd/f).write_text(t)
    print(tag, s['outline'], len(s['macros']))
