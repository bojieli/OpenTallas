#!/usr/bin/env python3
"""QW-DIECLK2 10-19: landing list + price for the Qwen compute MU die (QW-GEN2 consumes landing_list.json).
  make_landing_list.py land_owed_rA_input.json > landing_list.json
Input = QW-DIECLK rA land_owed (446 cross-region instance links, 186,347 bits, dv2f18dh2 floorplan).
Landing component per link (CLOSED views, main): multi-bit buses -> ceil(bits/258) pairs of the CB16 narrow halves
qfd_c_land_w258_narrow (writer: 4-slot ring on the SENDER region root ck_s) + qfd_c_land_r258_narrow (reader on the
RECEIVER region root ck), 514-bit buses -> the 257 pair; <= 32 bits -> qfd_landh0_<w> 65x30 (hop-0 landing, ck_s/ck).
Latency: E = K = 2, +3 clock edges per landed crossing (same as the CB16 fabric LANDALL seams), static, no backpressure.
Placement: the landing sits at the RECEIVER's regional-parent boundary: for c_b16-bound buses inside the CB16 parent at
its receiving face (the parent already lands every internal seam with these halves); for dv_slice2-bound buses at the
slice face; ck_s is the sender's region clock forwarded with the bus (fixed latency)."""
import json, math, re, sys, collections
FF = {'w258': 1132, 'r258': 347, 'w257': 1128, 'r257': 346}
AREA_HALF = 64.8 * 129.6           # um2, every narrow half (W/R 257/258) outline
FF_SMALL_PER_BIT, AREA_SMALL = 6.0, 65 * 30 * 0.0729   # landh0_<w> 65x30 sites (0.054 x 0.27 um site = 0.01458 um2)
EDGES = 3
o = json.load(open(sys.argv[1]))
rows, tot = [], collections.Counter()
def fam(bus):
    return re.sub(r'_[EW]\d.*$', '', bus) if not bus.startswith('n_q3h_col') else 'n_q3h_col'
for d in o['detail']:
    b = d['bits']
    if b == 514:
        kit, n = '257', 2
    elif b > 32:
        kit, n = '258', math.ceil(b / 258)
    else:
        kit, n = f'landh0_{b}', 1
    if kit in ('257', '258'):
        ff = n * (FF['w' + kit] + FF['r' + kit]); area = 2 * n * AREA_HALF
        comp = f'{n} x (qfd_c_land_w{kit}_narrow + qfd_c_land_r{kit}_narrow)'
    else:
        ff = round(FF_SMALL_PER_BIT * b + 20); area = AREA_SMALL
        comp = f'qfd_landh0_{b} (65x30 family; widths without a closed view -> next closed width)'
    dst_kind = 'cb16_face' if d['dst_master'] == 'qfd_c_b16_dv' else 'slice_face'
    rows.append(dict(src=d['src'], src_master=d['src_master'], ck_s=d['src_root'], dst=d['dst'], dst_master=d['dst_master'],
                     ck=d['dst_root'], bus=d['bus'], family=fam(d['bus']), bits=b, landing=comp, place=dst_kind,
                     E=2, added_edges=EDGES, ff=ff, area_um2=round(area, 1)))
    tot['links'] += 1; tot['bits'] += b; tot['ff'] += ff; tot['area_um2'] += area
byfam = collections.defaultdict(lambda: collections.Counter())
for r in rows:
    f = byfam[(r['family'], r['src_master'], r['dst_master'])]
    f['links'] += 1; f['bits'] += r['bits']; f['ff'] += r['ff']; f['area_um2'] += r['area_um2']
fams = [dict(family=k[0], src_master=k[1], dst_master=k[2], **{x: round(y, 1) for x, y in v.items()})
        for k, v in sorted(byfam.items(), key=lambda kv: -kv[1]['bits'])]
# serial landed crossings on the per-layer token path (static schedule), worst case: broadcast slice->near->far (2),
# reduction far->near->slice (2), dv slice chain W5..W0|E0..E5 (11 hops) => 15 crossings x 3 edges
per_layer = dict(q3h_broadcast=2, rs_reduction=2, dv_chain_hops=11)
cyc_layer = EDGES * sum(per_layer.values())
out = dict(schema='opentallas.qwen_compute.landing_list.v1', source='QW-DIECLK rA land_owed (dv2f18dh2, bbe250fb5)',
           rule=__doc__.split('\n', 2)[2].strip(),
           totals=dict(links=tot['links'], bits=tot['bits'], ff=tot['ff'], area_mm2=round(tot['area_um2'] / 1e6, 3)),
           price=dict(serial_landings_per_layer=per_layer, added_cycles_per_layer=cyc_layer, layers=36,
                      added_cycles_per_token=cyc_layer * 36, added_us_per_token_at_1p2GHz=round(cyc_layer * 36 / 1200, 3),
                      note='worst case (every dv chain hop on the serial path); the compiler schedule takes +3 edges per landed crossing'),
           narrowing_options=[
               dict(name='NB1 near-cluster add', saves_links=24, saves_bits=24 * 514,
                    what='X_1 adds the far cluster rs_i into its own rs before exit (rs_o feedthrough + n_dv_rs_b dropped): '
                         'X_1 -> slice becomes ONE 514-b bus; exact ONLY if the slice computes rs_a + rs_b first (golden order) -- '
                         'reduction-order owner must confirm before RTL'),
               dict(name='NB2 co-root abutted slice pairs', saves_links=None, saves_bits=None,
                    what='dv chain hops between ABUTTED slices (0-um gap) cannot host a landing between them; land inside '
                         'the receiving slice face (slice is unclosed: top-down pin/landing assignment)')],
           families=fams, links=rows)
json.dump(out, sys.stdout, indent=1)
