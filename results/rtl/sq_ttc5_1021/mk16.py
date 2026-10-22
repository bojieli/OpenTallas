# SQ-TTC5 10-21: safe16a/b = safe15a/b with ONE design change: head child u_hr h16c (259.2 x 222.48, ck_head + raw
# ck_pm0/ck_pm1) -> CLOSED H16ZA ot_qfd_tt_ctlm_static_hr_safe32_native32_1r (345.6 x 302.4, single clock ck_head;
# record qfd_tt_head_static_h16za-h16za-4934271d7).  Same 49 ports, identical pin offsets from the macro origin.
# Geometry: enlarge, never squeeze: head keeps its origin and grows +86.4 E / +86.4 N; outline +86.4 x +86.4;
# everything at y >= 367.2 (OPROM row, ROM266, wtn, region boxes, E pins above 367.2) moves +86.4 in y; boxes
# ending at the old core E edge extend +86.4.  N/S pin x unchanged; E pins below 367.2 keep their y.
# Netlist rtl/qwen_dv/lp9f_rr_h16za = lp9f_rr with the u_hr module name swapped and .ck_pm0/.ck_pm1 removed.
# Then: python3 tools/ref_tile/ref_tile.py gen physical/ref_tile/qfd_tt_ctlm_dv_safe16{a,b}/spec.json
import json, re
from pathlib import Path
W = Path('/home/ubuntu/wt/sq-ttc5-s16')
D = 86.4
Y0 = 367.2
H16C = 'physical/ref_tile/qfd_tt_head_static_h16c/views/ot_qfd_tt_ctlm_static_hr'
H16ZA = 'physical/ref_tile/qfd_tt_head_static_h16za/views/ot_qfd_tt_ctlm_static_hr_safe32_native32_1r'
XP = {'physical/ref_tile/qfd_tt_head_static_h16c': 'physical/ref_tile/qfd_tt_head_static_h16za',
      'results/closure_loop/qfd_tt_head_static_h16c-h16c-ae6b0c59a': 'results/closure_loop/qfd_tt_head_static_h16za-h16za-4934271d7',
      'results/rtl/ref_tile/qfd_tt_head_static_h16c/qfd_tt_head_static_h16c-h16c-ae6b0c59a':
          'results/rtl/ref_tile/qfd_tt_head_static_h16za/qfd_tt_head_static_h16za-h16za-4934271d7'}
r3 = lambda v: round(v, 3)  # noqa: E731


def netlist():
    src = W / 'rtl/qwen_dv/lp9f_rr'
    dst = W / 'rtl/qwen_dv/lp9f_rr_h16za'
    dst.mkdir(exist_ok=True)
    t = (src / 'qfd_tt_ctlm_dv_np_lp.sv').read_text()
    a, b = 'ot_qfd_tt_ctlm_static_hr\n', '.ck_pm0(n_3140),.ck_pm1(n_3140),'
    assert t.count(a) == 1 and t.count(b) == 1
    (dst / 'qfd_tt_ctlm_dv_np_lp.sv').write_text(t.replace(a, 'ot_qfd_tt_ctlm_static_hr_safe32_native32_1r\n').replace(b, ''))
    (dst / 'qfd_tt_ctlm_dv_np_helpers.sv').write_bytes((src / 'qfd_tt_ctlm_dv_np_helpers.sv').read_bytes())


def kit(src, tag):
    sd = W / f'physical/ref_tile/qfd_tt_ctlm_dv_{src}'
    kd = W / f'physical/ref_tile/qfd_tt_ctlm_dv_{tag}'
    kd.mkdir(exist_ok=True)
    s = json.loads(json.dumps(json.loads((sd / 'spec.json').read_text())).replace(f'qfd_tt_ctlm_dv_{src}', f'qfd_tt_ctlm_dv_{tag}'))
    W0, H0 = s['outline']['w'], s['outline']['h']
    xe_old = r3(W0 - 2.16)                       # old core E edge (775.44 / 861.84)
    s['outline']['w'], s['outline']['h'] = r3(W0 + D), r3(H0 + D)
    s['sources'] = [p.replace('rtl/qwen_dv/lp9f_rr/', 'rtl/qwen_dv/lp9f_rr_h16za/') for p in s['sources']]
    assert sum('lp9f_rr_h16za' in p for p in s['sources']) == 2
    hr = [c for c in s['children'] if c['inst'] == 'u_hr']
    assert len(hr) == 1 and hr[0]['view'] == H16C
    hr[0]['view'] = H16ZA
    hx, hy = hr[0]['at']
    for m in s['macros'] + s['children']:
        if m['at'][1] >= Y0:
            m['at'][1] = r3(m['at'][1] + D)
    rr = s['reserved_rom_slots']
    rr['origins_um'] = [[o[0], r3(o[1] + D) if o[1] >= Y0 else o[1]] for o in rr['origins_um']]
    rr['child_gap_um'] = r3(rr['origins_um'][0][1] - (hy + 302.4))   # OPROM row -> H16ZA N face
    east = set(s['pins']['E'])
    for p, (lo, hi) in s['pin_ranges'].items():
        if p in east and lo > Y0:
            s['pin_ranges'][p] = [r3(lo + D), r3(hi + D)]
    xp = s['job']['extra_paths']
    assert all(k in xp for k in XP)
    s['job']['extra_paths'] = [XP.get(p, p) for p in xp] + ['rtl/qwen_dv/lp9f_rr_h16za']
    purpose = (f"SQ-TTC5 10-21 {tag}: {src} with ONE change: head child u_hr h16c (259.2 x 222.48; ck_head + raw ck_pm0/"
               "ck_pm1) -> CLOSED H16ZA ot_qfd_tt_ctlm_static_hr_safe32_native32_1r (345.6 x 302.4, single clock ck_head, "
               "record qfd_tt_head_static_h16za-h16za-4934271d7, boundary R 480.5 TT / 389.7 FF); same 49 ports, identical "
               "pin offsets.  Netlist rtl/qwen_dv/lp9f_rr_h16za (module swap, .ck_pm0/.ck_pm1 removed).  Enlarged, not "
               f"squeezed: head origin kept ({hx}, {hy}), outline {W0} x {H0} -> {s['outline']['w']} x {s['outline']['h']}, "
               "everything at y >= 367.2 (OPROM row, ROM266, wtn, region boxes, E pins emb_*) +86.4 in y, E-edge region "
               "boxes +86.4; N/S pin x and E pins below 367.2 unchanged.  Per-domain spine child_insertion boundary_record "
               "(wtn/ck 141.6, H16ZA ck_head 480.5).")
    s['job'].update(owner='STEWARD-QKb/SQ-TTC5', branch='claude/sq-ttc5-safe16-1021', tag=tag, purpose=purpose)
    s['structural_recut_status'] = purpose
    s['slot_change_request'] = (f"SQ-TTC5 {tag} 10-21: outline {W0} x {H0} -> {s['outline']['w']} x {s['outline']['h']} "
                                "(H16ZA head +86.4 E / +86.4 N; die GEN must re-slot): N-face pins keep x (move with the "
                                "face), S pins keep x, E pins keep y except emb_start/emb_token (y += 86.4 with the NE "
                                "block).  Prior: " + s['slot_change_request'])
    fill = s['fill_reason']['pin_bound']
    s['fill_reason']['pin_bound'] = (f"qfd_tt_ctlm_dv_{tag}: bounded netlist std ~12270 um2 + hard (2 SRAM + 3 OPROM + "
                                     "2 ROM266 + H16ZA 345.6x302.4 + wtn) / outline: low total fill by construction "
                                     "(enlarged for the bigger closed head, never squeezed); see gen fill WARN for the "
                                     "figure.  Prior: " + fill)
    s['clock_note_ctlmclk'] = (s['clock_note_ctlmclk'] + f" | {tag}: regions core x2.16-{r3(453.6 + (W0 - 777.6))} y129.6-"
                               f"{r3(H0 - 43.2 + D)} + OPROM row band y453.6-561.6 + ROM266 column; hr = H16ZA box y129.6-453.6 "
                               f"to x{r3(xe_old + D)} + NE strip.")
    (kd / 'spec.json').write_text(json.dumps(s, indent=1) + '\n')

    # lcr_dissolve: rename only
    (kd / 'lcr_dissolve_after_gpl.tcl').write_text((sd / 'lcr_dissolve_after_gpl.tcl').read_text()
                                                   .replace(f'qfd_tt_ctlm_dv_{src}', f'qfd_tt_ctlm_dv_{tag}'))
    # lp_cone_regions: y >= 367.2 += 86.4, x1 == old core E edge += 86.4, ry1 += 86.4
    t = (sd / 'lp_cone_regions.tcl').read_text().replace(f'qfd_tt_ctlm_dv_{src}', f'qfd_tt_ctlm_dv_{tag}')
    line = [ln for ln in t.split('\n') if ln.startswith('set boxes')]
    assert len(line) == 1
    line = line[0]

    def box(m):
        x0, y0, x1, y1 = map(float, m.group(1).split())
        y0 = r3(y0 + D) if y0 >= Y0 else y0
        y1 = r3(y1 + D) if y1 >= Y0 else y1
        x1 = r3(x1 + D) if abs(x1 - xe_old) < 1e-6 else x1
        return '{' + ' '.join(str(v) for v in (x0, y0, x1, y1)) + '}'
    new = re.sub(r'\{([0-9. ]+)\}', box, line.split('   ;#')[0])
    t = t.replace(line, f'# {tag} (SQ-TTC5 10-21): H16ZA head (345.6 x 302.4) at the same origin; y >= 367.2 += 86.4, '
                        f'E-edge boxes x1 += 86.4 (outline {s["outline"]["w"]} x {s["outline"]["h"]})\n' + new)
    ry_old = f'set ry0 129.6; set ry1 {r3(H0 - 43.2)}'
    assert t.count(ry_old) == 1
    t = t.replace(ry_old, f'set ry0 129.6; set ry1 {r3(H0 - 43.2 + D)}')
    (kd / 'lp_cone_regions.tcl').write_text(t)
    # assigned pins: E pins above 367.2 += 86.4 (emb_start / emb_token beside the raised NE block)
    t = (sd / 'assigned_pins.tcl').read_text()
    n = [0]

    def epin(m):
        y = float(m.group(2))
        if y <= Y0:
            return m.group(0)
        n[0] += 1
        return f'{m.group(1)}{y + D:.6f}'
    t = re.sub(r'^(ot_assigned_pin_exact \{[^}]*\} M\d E )([0-9.]+)$', epin, t, flags=re.M)
    t = (f'# {tag} (SQ-TTC5 10-21): H16ZA head; outline +86.4 x +86.4; E pins above y367.2 (emb_start/emb_token, '
         f'{n[0]} pins) y += 86.4; N/S x and the other E y unchanged\n') + t
    (kd / 'assigned_pins.tcl').write_text(t)
    print(tag, s['outline'], 'E pins moved', n[0], new)


netlist()
for src, tag in (('safe15a', 'safe16a'), ('safe15b', 'safe16b')):
    kit(src, tag)
