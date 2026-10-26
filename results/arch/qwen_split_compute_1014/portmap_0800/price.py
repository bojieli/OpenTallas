import json, math, sys
d = json.load(open(sys.argv[1]))
I = {i['n']: i for i in d['insts']}
def c(n):
    i = I[n]; return (i['x'] + i['w'] / 2, i['y'] + i['h'] / 2)
PITCH = 490.0
def S(L):  # geometric stages: relays every 490 um + 1 register hop (pm_h_cycle_price method)
    return max(1, math.ceil(L / PITCH))
def dist(a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])
XC = 16487.0                      # die x centre (r2h5 extent 32,975 um)
mir = lambda p: (2 * XC - p[0], p[1])
# r2h5 positions (today) and owner layout (east column = mirror of west column)
PW = {k: c(f'sp_port_tiles_{k}') for k in range(3)}
PE_today = {k: c(f'sp_port_tiles_{k}_f1') for k in range(3)}
PE_own = {k: mir(PW[k]) for k in range(3)}
BL = {k: c(f'sp_band_lanes_{k}') for k in range(3)}
RS = {k: c(f'sp_res_ser_{k}') for k in range(3)}
LEAF_today = (c('tt_up4_leaf0')[0] + 130, c('tt_up4_leaf0')[1])
LEAF_centre = (XC, PW[1][1])
roots = {k: {'W': [], 'E': []} for k in range(3)}
for b in d['buses']:
    if b[0].startswith('bword_'):
        k = int(b[3][1].split('_')[3]); side = 'E' if b[3][1].endswith('_f1') else 'W'
        roots[k][side].append(c(b[3][0]))
def bmax(k, side, port): return max(S(dist(r, port)) for r in roots[k][side])
out = {}
def chain(name, red, res, cross_bits, cross_mm, notes):
    out[name] = dict(reduction_stages=red, result_stages=res, per_me_op=red + res,
                     cross_centre_bits=cross_bits, cross_centre_bit_mm=round(cross_bits * cross_mm / 1000.0, 1),
                     notes=notes)
# ---- today (r2h5): both port tiles west of VM
red = max(max(bmax(k, 'W', PW[k]), bmax(k, 'E', PE_today[k]) + S(dist(PE_today[k], PW[k])))
          + S(dist(PW[k], BL[k])) + S(dist(BL[k], LEAF_today)) for k in range(3))
res = S(dist(LEAF_today, BL[0])) + max(S(dist(BL[k], PW[k])) + 2 * S(dist(PW[k], PE_today[k])) + S(dist(PW[k], RS[k])) for k in range(3))
ebw = sum(514 * len(roots[k]['E']) for k in range(3))
chain('today_r2h5', red, res, ebw, (PE_today[0][0] - 12566) / 1000.0 if False else 0,
      'east bwords (12,336 b) run from the east array to k_f1 west of VM: they cross the centre column today')
out['today_r2h5']['cross_centre_bits'] = ebw
out['today_r2h5']['cross_centre_bit_mm'] = round(sum(514 * (20429 - PE_today[k][0]) / 1e6 * len(roots[k]['E']) for k in range(3)), 1)
# ---- option (a): k west, k_f1 east (mirror), 6,704 b pair link crosses
L_a = dist(PW[0], PE_own[0])
red = max(max(bmax(k, 'W', PW[k]), bmax(k, 'E', PE_own[k]) + S(L_a)) + S(dist(PW[k], BL[k])) + S(dist(BL[k], LEAF_today)) for k in range(3))
res = S(dist(LEAF_today, BL[0])) + max(S(dist(BL[k], PW[k])) + 2 * S(L_a) + S(dist(PW[k], RS[k])) for k in range(3))
chain('a_pair_split', red, res, 3 * 6704, L_a / 1000.0, 'pfrag 2050 + slab_rq 2213 + slab_am 52 (E->W) and slab_tc 341 + slab_ty 2048 (W->E), x3 pairs')
# ---- option (b-map): blocks re-assigned so bands 0 and 2 are one-sided, band 1 still split (no RTL)
chain('b0_remap_only', out['a_pair_split']['reduction_stages'], out['a_pair_split']['result_stages'], 6704, L_a / 1000.0,
      'bands 0/2 one-sided by ROM placement + bword netlist; band 1 pair still crosses and sets the per-op max (geometric, same as (a))')
# ---- option (b1): per-side half-band lanes, L10 in the WEST half lanes; E L9 partial (513 b) crosses
BLE = {k: mir(BL[k]) for k in range(3)}
L_bl = dist(BL[0], BLE[0])
red = max(max(bmax(k, 'W', PW[k]) + S(dist(PW[k], BL[k])), bmax(k, 'E', PE_own[k]) + S(dist(PE_own[k], BLE[k])) + S(L_bl))
          + S(dist(BL[k], LEAF_today)) for k in range(3))
res = S(dist(LEAF_today, BL[0])) + max(max(S(dist(BL[k], PW[k])) + S(dist(PW[k], RS[k])),
                                          S(dist(BLE[k], PE_own[k])) + S(dist(PE_own[k], mir(RS[k])))) for k in range(3))
chain('b1_half_lanes_L10_west', red, res, 3 * 513, L_bl / 1000.0, 'E half-band L9 word (16 lanes x 32 + valid) crosses to the W half for L10')
# ---- option (b2): per-side half-band lanes (L8,L9), tree top = ot_qfd_band_upper NB 6 NU 2 (L10+L11) in the centre
red = max(max(bmax(k, 'W', PW[k]) + S(dist(PW[k], BL[k])) + S(dist(BL[k], LEAF_centre)),
              bmax(k, 'E', PE_own[k]) + S(dist(PE_own[k], BLE[k])) + S(dist(BLE[k], LEAF_centre))) for k in range(3))
res = S(dist(LEAF_centre, BL[0])) + max(max(S(dist(BL[k], PW[k])) + S(dist(PW[k], RS[k])),
                                           S(dist(BLE[k], PE_own[k])) + S(dist(PE_own[k], mir(RS[k])))) for k in range(3))
chain('b2_half_lanes_upper_nb6', red, res, 0, 0.0, 'no west<->east link; W and E half-band L9 words (513 b each) end in the centre tree top')
base = out['today_r2h5']['per_me_op']
for k, v in out.items():
    v['delta_stages_per_me_op_vs_today'] = v['per_me_op'] - base
    v['delta_cycles_per_ar_token_vs_today'] = 217 * v['delta_stages_per_me_op_vs_today']
    v['delta_pct_of_249431'] = round(100.0 * v['delta_cycles_per_ar_token_vs_today'] / 249431, 2)
GEO=(dict(pair_link_um=L_a, half_lane_link_um=L_bl,
                      max_bword_um={k: {s: max(dist(r, (PW if s == 'W' else PE_own)[k]) for r in roots[k][s]) for s in 'WE'} for k in range(3)},
                      max_bword_um_today_E={k: max(dist(r, PE_today[k]) for r in roots[k]['E']) for k in range(3)},
                      ))
# ---- total port-subsystem bit*mm (all buses the remap touches), kbit*mm
VM = (XC, c('sp_vector_memory')[1]); TT = (XC, c('tt_ctlm')[1])
def bw_sum(portW, portE): return sum(514 * dist(r, portW[k]) for k in range(3) for r in roots[k]['W']) + sum(514 * dist(r, portE[k]) for k in range(3) for r in roots[k]['E'])
tot = {}
# today
t = bw_sum(PW, PE_today)
t += sum(6704 * dist(PW[k], PE_today[k]) + 8192 * dist(PW[k], BL[k]) + 4425 * dist(PW[k], RS[k]) + 513 * dist(BL[k], LEAF_today)
         + 551 * dist(RS[k], VM) + (341 + 104) * dist(PW[k], TT) for k in range(3)) + 1538 * dist(LEAF_today, BL[0])
tot['today_r2h5'] = t
# (a) (VM/TT centred, k west, k_f1 east)
t = bw_sum(PW, PE_own)
t += sum(6704 * dist(PW[k], PE_own[k]) + 8192 * dist(PW[k], BL[k]) + 4425 * dist(PW[k], RS[k]) + 513 * dist(BL[k], LEAF_today)
         + 551 * dist(RS[k], VM) + (341 + 104) * dist(PW[k], TT) for k in range(3)) + 1538 * dist(LEAF_today, BL[0])
tot['a_pair_split'] = t
def per_side(L10_west):
    t = bw_sum(PW, PE_own)
    for k in range(3):
        for P, B, R in ((PW[k], BL[k], RS[k]), (PE_own[k], BLE[k], mir(RS[k]))):
            t += 4096 * dist(P, B) + 2213 * dist(P, R) + 551 * dist(R, VM) + (341 + 52) * dist(P, TT)
        if L10_west:
            t += 513 * dist(BLE[k], BL[k]) + 513 * dist(BL[k], LEAF_today)
        else:
            t += 513 * dist(BL[k], LEAF_centre) + 513 * dist(BLE[k], LEAF_centre)
    t += 1538 * dist(LEAF_today if L10_west else LEAF_centre, BL[0])
    return t
tot['b1_half_lanes_L10_west'] = per_side(True)
tot['b2_half_lanes_upper_nb6'] = per_side(False)
tot['b0_remap_only'] = tot['a_pair_split'] - 2 * 6704 * (L_a - dist(PW[0], PE_today[0]))
for k, v in tot.items():
    out[k]['port_subsystem_kbit_mm'] = round(v / 1e6, 1)
GEO['units']='stages: ceil(manhattan_um/490) per bus (relay reach 490 um + 1 register hop, pm_h_cycle_price method); bit_mm in kbit*mm, instance centres'
print(json.dumps(dict(geometry=GEO, options=out), indent=1))
