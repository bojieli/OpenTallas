"""HC_B2_SPEC cut check: the HC central control / Sinkhorn shell boundary added to the SPEC v0.7 die loads.

Reuses cuts_v07.py unchanged: the r25gqn_b2 die network (v9 ring 2,224 b, COLL star 4 x 2,130 b, HC x lanes
8 x 150 + 16 a quarter), its centre-to-centre segment counting and its track-capacity model (0.75 of the upper layer
over the whole cut, 0.75 of the lower layer + 0.5 of M4 / M5 in the channels only).  This script only ADDS buses (and,
for the centre placement, one block) and re-runs the same cuts plus a few extra lines through the HC quarters.

Widths are read from RTL (rtl/hbm_accel/generic/peers/ot_hgi_hc_unit.sv, SYS / QPAIR branch, W 32, SPL 4, HAW 35,
AW 16, RMAX 128) unless marked EST.  Nothing here is a price; cycle effects are counts to be measured.
"""
import sys, json, math, copy, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cuts_v07 as C

# ---- RTL widths (ot_hgi_hc_unit.sv line numbers in HC_B2_SPEC.md section 1)
W, SPL, HAW, AW, CWW, NVW, TG = 32, 4, 35, 16, 8, 6, 11
DESC = 1 + 1 + NVW + AW + AW                        # d_v, d_ss, d_nv, d_wa, d_xa = 40
CHAIN = DESC + W * 32 + 1                           # + sum 1,024 + f = 1,065
DB = HAW + SPL * HAW + SPL * CWW + SPL * AW + HAW   # c_base, c_soff, c_nwk, c_bnd, c_pbase = 306
CTL_DN_TILE = 3 + DB                                # + c_start, c_rel, c_pgo = 309
CTL_UP_TILE = 2                                     # t_rdy, t_flt
CTL_Q = 2 * (CTL_DN_TILE + CTL_UP_TILE)             # 622 a quarter, as the RTL drives it today
CTL_Q_SHARED = (DB - HAW) + 2 * HAW + 2 * 3 + 2 * CTL_UP_TILE   # 351: common geometry once, c_base and pulses a tile
RET = W * 32 + 1                                    # tile 7 -> HCP: sums + fault = 1,025 (o_* descriptor taps unused)
PARAM = 1 + TG + 2 + 256                            # HBM lane 0 response fork to the shell = 270
XS_EST = 50                                         # EST: x-stage command down (~48) + done / fault up (2), a quarter
RES_Q = 140 + 2 * 45 + 2 + 259 + 6                  # residual engine boundary, as given by the parent = 497
REC = 939 + 3                                       # cmdproc record + return (die model hgi_hc_cmd / hgi_hc_ret)
VMP = 338 + 274                                     # shell VM packet client vmq / vmr
XL_Q = 1216                                         # x lanes slice -> quarter (already in the v0.7 loads)
HBM_Q = 2 * SPL * (1 + HAW + 3 + TG) + 2 * SPL + 2 * SPL * (1 + TG + 2 + 256)   # hq 400 + rdy 8 + hr 2,160 = 2,568

REACH = 504.0                                       # um a stage at 833 ps, SS: 261 ps + 1.135 ps/um
ORDER = ('SW', 'NW', 'NE', 'SE')                    # chain order: banks (0,1) (2,3) (4,5) (6,7); one W-E crossing
SHELL_WH = (1000.0, 500.0)                          # EST shell outline (0.5 mm2); the real area is open
# today's unit constants (ot_hgi_hc_unit.sv 68-71, 116, 260)
XRLY, DRLY, SLM, SLA, TSOR, TTML, TTOR, TTIR = 4, 2, 8, 7, 1, 3, 1, 1
HOP = SLA + 1 + TSOR + TTOR + TTIR
SYS_LAT0 = 2 * DRLY + 1 + 7 * HOP + 3 + 2 + (TTML - 2) + SLM + SLA + TSOR + TTOR + TTIR

def stages(d): return int(math.ceil(d / REACH - 1e-9))
def rect(it): return (it.x, it.y, it.x + it.w, it.y + it.h)
def gap(a, b):
    """Manhattan distance between two boxes: the facing-edge gap on each axis (0 where they overlap)."""
    return max(a[0] - b[2], b[0] - a[2], 0) + max(a[1] - b[3], b[1] - a[3], 0)
def ctr(r): return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
def pt_gap(p, r):
    return max(r[0] - p[0], p[0] - r[2], 0) + max(r[1] - p[1], p[1] - r[3], 0)

def placements(I):
    q = {k: rect(I[f'hb_hc_{k}']) for k in ORDER}
    sw, nw = q['SW'], q['NW']
    return {
        # the freed old-VM site at the die centre (SPEC 1: 14,399-16,472 x 12,506-14,580)
        'P_C_centre': dict(xy=(15435.5 - SHELL_WH[0] / 2, 13543.0 - SHELL_WH[1] / 2), new_block=True, vm='hb_vms_NW'),
        # inside the SW quarter's slot (the die model's present assumption: record and vmq end at hb_hc_SW)
        'P_SW_colocated': dict(xy=(sw[2] - SHELL_WH[0], sw[3] - SHELL_WH[1]), new_block=False, vm=None),
        # in the channel between the SW and NW quarter slots, at their inner (E) end
        'P_W_between': dict(xy=(sw[2] - SHELL_WH[0], (sw[3] + nw[1]) / 2 - SHELL_WH[1] / 2), new_block=True, vm=None),
    }

def extra_cuts(c):
    out = C.hc_cuts(c)
    for xc in (11000, 19000, 20000, 20800): out[f'x{xc/1000:g}_hub'] = ('x', xc, 10000, 16000)
    out['hcW_y12.99'] = ('y', 12990, 8064, 11328)
    out['hcE_y12.99'] = ('y', 12990, 20793, 24057)
    return out

def buses(shell, vm, res_at):
    b = []
    for k in ORDER:
        b.append((f'hcs_ctl_{k}', 'hub', CTL_Q, [(shell, 't'), (f'hb_hc_{k}', 'f')]))
        b.append((f'hcs_xs_{k}', 'hub', XS_EST, [(shell, 't'), (f'hb_hc_{k}', 'f')]))
        b.append((f'hcs_res_{k}', 'hub', RES_Q, [(res_at, 't'), (f'hb_hc_{k}', 'f')]))
    b.append(('hcs_desc', 'hub', DESC, [(shell, 't'), (f'hb_hc_{ORDER[0]}', 'f')]))
    for a, z in zip(ORDER, ORDER[1:]): b.append((f'hcs_chain_{a}{z}', 'hub', CHAIN, [(f'hb_hc_{a}', 't'), (f'hb_hc_{z}', 'f')]))
    b.append(('hcs_ret', 'hub', RET, [(f'hb_hc_{ORDER[-1]}', 't'), (shell, 'f')]))
    b.append(('hcs_param', 'hub', PARAM, [(f'hb_hc_{ORDER[0]}', 't'), (shell, 'f')]))
    if vm:  # centre placement: the record and VM packet buses re-end at the shell (the old SW-ended ones stay counted)
        b.append(('hcs_rec', 'hub', REC, [('hb_cmdproc', 't'), (shell, 'f')]))
        b.append(('hcs_vmp', 'hub', VMP, [(shell, 't'), (vm, 'f')]))
    return b

def relay_table(I, srect):
    q = {k: rect(I[f'hb_hc_{k}']) for k in ORDER}
    sc = ctr(srect)
    ctl = {k: (round(pt_gap(sc, q[k])), stages(pt_gap(sc, q[k]))) for k in ORDER}
    hop = {f'{a}->{z}': (round(gap(q[a], q[z])), stages(gap(q[a], q[z]))) for a, z in zip(ORDER, ORDER[1:])}
    d_in, d_out = ctl[ORDER[0]][1], ctl[ORDER[-1]][1]
    inter = sum(v[1] for v in hop.values())
    xr = max(v[1] for v in ctl.values())
    eng = rect(I['hb_hc_eng'])
    res = {k: (round(gap(eng, q[k])), stages(gap(eng, q[k]))) for k in ORDER}
    cp = rect(I['hb_cmdproc'])
    return dict(ctl_um_stages=ctl, chain_hop_um_stages=hop, desc_in_stages=d_in, ret_out_stages=d_out,
                inter_quarter_stages=inter, xrly_max=xr,
                sys_lat_today=SYS_LAT0, sys_lat_b2=SYS_LAT0 - 2 * DRLY + d_in + d_out + inter,
                sys_lat_delta_per_row=d_in + d_out + inter - 2 * DRLY,
                rw_hold_today=2 * XRLY + 6, rw_hold_b2=2 * xr + 6, rw_hold_delta_per_row=2 * (xr - XRLY),
                param_roundtrip_delta=(ctl[ORDER[0]][1] - XRLY) + ctl[ORDER[0]][1],
                rec_um_stages=(round(pt_gap(sc, cp)), stages(pt_gap(sc, cp))),
                residual_um_stages=res,
                relay_flops=dict(ctl=CTL_Q * sum(v[1] for v in ctl.values()), chain=CHAIN * inter, desc=DESC * d_in,
                                 ret=RET * d_out, param=PARAM * d_in))

if __name__ == '__main__':
    m = C.model(1200, 16)
    I = {it.name: it for it in m['insts']}
    base_buses, base_insts = list(m['buses']), list(m['insts'])
    out = dict(widths=dict(DESC=DESC, CHAIN=CHAIN, DB=DB, CTL_DN_TILE=CTL_DN_TILE, CTL_UP_TILE=CTL_UP_TILE, CTL_Q=CTL_Q,
                           CTL_Q_SHARED=CTL_Q_SHARED, RET=RET, PARAM=PARAM, XS_EST=XS_EST, RES_Q=RES_Q, REC=REC, VMP=VMP,
                           XL_Q=XL_Q, HBM_Q=HBM_Q,
                           shell_quarter_side_rtl=4 * CTL_Q + DESC + RET + PARAM,
                           shell_quarter_side_b2=4 * (CTL_Q + XS_EST) + DESC + RET + PARAM,
                           centre_with_residual=4 * (CTL_Q + XS_EST + RES_Q) + DESC + RET + PARAM,
                           shell_all_ports=4 * (CTL_Q + XS_EST) + DESC + RET + PARAM + REC + VMP),
               order=ORDER, reach_um=REACH, shell_wh_est=SHELL_WH,
               quarter_slots={k: [round(v) for v in rect(I[f'hb_hc_{k}'])] for k in ORDER})
    # quarter face pin demand: one 0.048-um layer along the face (the convention of b2_functional_map.json's seam)
    qw, qh = 1356.48, 756.0
    ew = CHAIN + CTL_Q + XS_EST + RES_Q + XL_Q
    out['quarter_face'] = dict(ew_face_tracks=round(qh / 0.048), ns_face_tracks=round(qw / 0.048),
                               ew_bits_no_hbm=ew, ew_frac_no_hbm=round(ew / (qh / 0.048), 3),
                               ew_bits_with_hbm=ew + HBM_Q, ew_frac_with_hbm=round((ew + HBM_Q) / (qh / 0.048), 3),
                               ns_bits_chain=CHAIN, ns_frac_chain=round(CHAIN / (qw / 0.048), 3))
    base = C.run(m, extra_cuts)
    out['v07_base'] = {k: dict(bits=v['bits'], usable=v['usable'], util=v['util']) for k, v in base.items()}
    ART = ('y16_hub', 'X_centre_full', 'Y_centre_full')   # y16: the slice-body artifact of SPEC 6a, reported apart
    P = placements(I)
    cases = [(n, 'hb_hc_eng') for n in P] + [('P_C_centre', 'shell')]
    for name, res_at in cases:
        p = P[name]; tag = name + ('' if res_at == 'hb_hc_eng' else '+res_at_shell')
        sh = copy.copy(I['hb_hc_eng']); sh.name = 'hb_hc_shell'; sh.x, sh.y = p['xy']; sh.w, sh.h = SHELL_WH
        if not p['new_block']: sh.w, sh.h = 100.0, 100.0   # inside an existing slot: adds no blocked area
        m['insts'] = base_insts + [sh]
        m['buses'] = base_buses + buses('hb_hc_shell', p['vm'], 'hb_hc_shell' if res_at == 'shell' else res_at)
        r = C.run(m, extra_cuts)
        srect = (p['xy'][0], p['xy'][1], p['xy'][0] + SHELL_WH[0], p['xy'][1] + SHELL_WH[1])
        rows = {k: dict(bits=v['bits'], added=v['bits'] - base[k]['bits'], usable=v['usable'], util=v['util'],
                        util_base=base[k]['util']) for k, v in r.items()}
        ch = {k: v for k, v in rows.items() if k not in ART}
        wk = max(ch, key=lambda k: ch[k]['util']); wa = max(ch, key=lambda k: ch[k]['util'] - ch[k]['util_base'])
        out[tag] = dict(shell_xy=[round(v) for v in p['xy']], residual_centre=res_at, cuts=rows,
                        worst_channel_cut=[wk, ch[wk]['util'], ch[wk]['util_base']],
                        largest_increase=[wa, round(ch[wa]['util'] - ch[wa]['util_base'], 3), ch[wa]['util']],
                        y16_artifact=[rows['y16_hub']['util'], rows['y16_hub']['util_base']],
                        over_060=[k for k, v in ch.items() if v['util'] > 0.60],
                        over_055=[k for k, v in ch.items() if v['util'] > 0.55],
                        relays=relay_table(I, srect))
        print(f"== {tag}: worst {wk} {ch[wk]['util_base']:.3f} -> {ch[wk]['util']:.3f}; largest increase {wa} "
              f"+{ch[wa]['util'] - ch[wa]['util_base']:.3f} -> {ch[wa]['util']:.3f}; y16 {rows['y16_hub']['util']:.3f}")
        for k, v in rows.items():
            if v['added']: print(f"   {k:16s} +{v['added']:6d}  {v['util_base']:.3f} -> {v['util']:.3f}")
        rt = out[tag]['relays']
        print('   relays', json.dumps({k: rt[k] for k in ('ctl_um_stages', 'chain_hop_um_stages', 'sys_lat_b2',
                                                           'rw_hold_b2', 'rec_um_stages')}))
    print(json.dumps(out['widths'])); print(json.dumps(out['quarter_face']))
    json.dump(out, open(HERE / 'hc_central_cuts.json', 'w'), indent=1)
