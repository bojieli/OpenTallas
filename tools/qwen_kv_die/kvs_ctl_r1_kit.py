#!/usr/bin/env python3
"""KDIE5-TV 10-22: kit qkd_kvs_ctl_r1 = the RELEASE KV die's qkd_kvs_ctl (module text of _k_mu_ba == _n32_pj, no RTL change)
at the relm frame 1123.176 x 172.776 (kvs14r-f9b69ebb3-relm case_kv/elements.lef).  STEWARD-QKc 10-22 decision (b):
M6 PIN-ONLY contacts on the W / E faces (2524 pins each on 172.776 um = 14.6 pins/um on one layer > the 12 b/um/layer hard
limit; M4 + M6 = 7.3 / um / layer).  This is a pin-density grant, not growth: outline, signal / PG cap (M5) unchanged.
Face order and bit order along every face = the frame's."""
import collections, hashlib, json, re, subprocess, sys
from pathlib import Path

WT = Path(sys.argv[1]); LEF = Path(sys.argv[2]); SRC_COMMIT = sys.argv[3]
sys.path.insert(0, str(WT / 'tools/hier_contract'))
import m6_pin_grant as M6

KIT = 'qkd_kvs_ctl_r1'; M = 'qkd_kvs_ctl'
TILE = 'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj.sv'
SOURCES = [
    'rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_half_root_b.sv',
    'rtl/qwen_sys/kv_bootage_20261019/qkd_kv_die_cfg_a.sv',
    'rtl/qwen_sys/mu_qwen_20261018/qkd_static_kv_ownership_calendar_mu.sv',
    'rtl/qwen_sys/mu_qwen_20261018/qkd_static_kv_boot_dispatch_mu.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_boot_cdc.sv',
    'rtl/qwen_sys/mu_qwen_20261018/qkd_kv_static_writer_native_mu.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_kv_ownership_obs.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_kv_cfault_tree.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_kv_native_programme.sv',
    'rtl/qwen_sys/mu_qwen_20261018/qkd_static_kv_layer_programme_mu.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_layer_programme.sv',
    'rtl/physical/ot_qkd_kv_static_writer_native.sv',
    'rtl/qwen_sys/mu_qwen_20261018/qkd_kv_mu_rowoff.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_kv_static_writer.sv',
    'rtl/lib/ot_rst_relay.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_boot_dispatch.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_ownership.sv',
    TILE]
P_NS = 0.096                      # M5 2-track pitch (N / S)
M4 = (0.012, 0.096)               # W / E: M4 track 0.012 + 0.048 k, every 2nd track
M6T = (0.016, 0.128)              # W / E: M6 track 0.016 + 0.064 k, every 2nd track
EDGE_LO, EDGE_HI = 2.16, None     # keep 2.16 um clear of the corners
STUB = 0.384                      # M6 contact depth (proven: qfd_xs_leaf_w130)
HELPER = 'physical/common_flow/assigned_pin_exact.tcl'


def frame():
    t = LEF.read_text()
    b = re.search(r'^MACRO ' + M + r'\n(.*?)^END ' + M + r'\n', t, re.S | re.M).group(1)
    W, H = map(float, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', b).groups())
    pins = []
    for blk in re.split(r'\n  PIN ', b)[1:]:
        name = blk.split('\n', 1)[0].strip()
        r = re.search(r'LAYER (\S+) ;\s+RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)', blk)
        x0, y0, x1, y1 = map(float, r.groups()[1:])
        f = 'W' if x0 < 0.5 else 'E' if x1 > W - 0.5 else 'S' if y0 < 0.5 else 'N' if y1 > H - 0.5 else 'I'
        pins.append((name, f, (y0 + y1) / 2 if f in 'WE' else (x0 + x1) / 2))
    return W, H, pins


def rtl_widths():
    t = (WT / TILE).read_text()
    hdr = re.search(r'^module ' + M + r' \((.*?)^\);', t, re.S | re.M).group(1)
    out = {}
    for m in re.finditer(r'(input|output)\s+wire\s+(?:\[(\d+):(\d+)\]\s+)?(\w+)', hdr):
        out[m.group(4)] = (int(m.group(2)) - int(m.group(3)) + 1) if m.group(2) else 1
    return out


def main():
    W, H, fpins = frame()
    widths = rtl_widths()
    # interior stand-in clock / reset drop (M8 at x 552) and ports the frame lacks (por_n: unconnected on the die;
    # kg: unread) -> N face at the drop's x
    fr = [(n, f, t) for n, f, t in fpins if f != 'I']
    have = {re.sub(r'\[\d+\]$', '', n) for n, f, t in fr}
    extra = [('ck', 551.0), ('rst_n', 552.0), ('por_n', 553.0), ('kg', 560.0)]
    for port, c in extra:
        if port in have:
            continue
        w = widths[port]
        fr += [(f'{port}[{i}]', 'N', c + i * 1e-4) for i in range(w)]
    assert {re.sub(r'\[\d+\]$', '', n) for n, _, _ in fr} == set(widths), sorted(set(widths) ^ {re.sub(r'\[\d+\]$', '', n) for n, _, _ in fr})

    def bt(n):                     # BTerm name: width-1 ports are scalars (ot_pin_regs wrapper e3919f90e)
        b = re.sub(r'\[\d+\]$', '', n)
        return b if widths[b] == 1 else n

    placed = {}                    # bterm -> (face, layer, coord)
    for f in 'NS':
        by = collections.defaultdict(list)
        for n, ff, t in fr:
            if ff == f:
                by[re.sub(r'\[\d+\]$', '', n)].append((t, n))
        groups = sorted((sum(t for t, _ in v) / len(v), k, sorted(v)) for k, v in by.items())
        prev = EDGE_LO - P_NS
        for c, port, v in groups:
            span = (len(v) - 1) * P_NS
            lo = max(c - span / 2, prev + P_NS)
            lo = round(round((lo - 0.012) / 0.048) * 0.048 + 0.012, 3)
            for i, (t, n) in enumerate(v):
                placed[bt(n)] = (f, 'M5', round(lo + i * P_NS, 3))
            prev = lo + span
            assert prev < W - EDGE_LO, (f, port, prev)
    hi = H - EDGE_LO
    slots = sorted([(round(M4[0] + M4[1] * k, 3), 'M4') for k in range(int(H / M4[1]) + 1) if EDGE_LO <= M4[0] + M4[1] * k <= hi] +
                   [(round(M6T[0] + M6T[1] * k, 3), 'M6') for k in range(int(H / M6T[1]) + 1) if EDGE_LO <= M6T[0] + M6T[1] * k <= hi])
    for f in 'WE':
        v = sorted((t, n) for n, ff, t in fr if ff == f)       # frame order along the face (bit order kept)
        assert len(v) <= len(slots), (f, len(v), len(slots))
        idx = [round(i * (len(slots) - 1) / (len(v) - 1)) for i in range(len(v))]
        assert len(set(idx)) == len(idx)
        for (t, n), i in zip(v, idx):
            y, L = slots[i]
            placed[bt(n)] = (f, L, y)
    # io_tcl = canonical helper + one exact assignment per BTerm
    io = f'physical/qkd_kvs_kits/{KIT}_io.tcl'
    lines = [f'# {KIT}: GENERATED by tools/qwen_kv_die/kvs_ctl_r1_kit.py (KDIE5-TV 10-22) from the relm frame MACRO {M}: face / bit order',
             '# = the frame; N/S M5 2-track; W/E M4 + M6 (pin-only M6 grant, pin density not growth) on alternating 2-track slots.']
    for n, (f, L, c) in sorted(placed.items()):
        lines.append(f'ot_assigned_pin_exact {{{n}}} {L} {f} {c:.6f}')
    (WT / io).write_text((WT / HELPER).read_text() + '\n'.join(lines) + '\n')
    pins = {f: [n for n, (ff, L, c) in sorted(placed.items(), key=lambda kv: kv[1][2]) if ff == f] for f in 'NSEW'}
    m6 = sorted((n, f, c) for n, (f, L, c) in placed.items() if L == 'M6')

    mu1 = json.loads(subprocess.run(['git', '-C', str(WT), 'show', 'HEAD:physical/ref_tile/qkd_kvs_ctl_mu1/spec.json'],
                                    capture_output=True, text=True, check=True).stdout)
    c32k = json.loads(subprocess.run(['git', '-C', str(WT), 'show', 'HEAD:physical/ref_tile/qkd_kvs_ctl_c32k/spec.json'],
                                     capture_output=True, text=True, check=True).stdout)
    why = ('KDIE5-TV 10-22 (STEWARD-QKc decision b): die-bindable kit of the release KV die qkd_kvs_ctl (relm f9b69ebb3; '
           'module text _k_mu_ba == _n32_pj, no RTL change) at the relm frame 1123.176 x 172.776.  W / E faces carry 2524 '
           'pins each on 172.776 um: M4 + pin-only M6 contacts (grant = pin density, not growth: outline and M5 cap '
           'unchanged).  Face / bit order = the frame; ck / rst_n (frame M8 interior drop at x 552) + por_n (unconnected on '
           'the relm die!) + kg (unread) on N at x ~552.  Pin registers off (die charges 0 face edges); 2-stage reset '
           'landing + kept copies, clock spine as the c32k gate (WARN, spread 29.8 / 25.8 ps).')
    s = dict(name=KIT, top=M, kind='tile', sources=SOURCES, params={}, clock_port='ck', reset_ports=['rst_n', 'por_n'],
             outline={'w': W, 'h': H, 'exact': True}, layer_cap='M5', macros=[], pins=pins, io_tcl=io,
             route=dict(pd=0.5, threads=8, peak_ram_gb=24, pin_h='M4 M6', pin_v='M5', pin_min_tracks=2, m5_pg_pitch=2.7,
                        hold_margin_ns=0.03, io_hold_margin_ns=0.03, macro_halo_um=5.4, period_ps=833),
             pin_access={'frac': 1.0, 'm6_stub_um': STUB}, recipe=3, pin_regs=mu1['pin_regs'], children=[], inter=[],
             keep_pin_regs=True, inhold=True, outhold=True, io_flop_at_pins={'cols': 4, 'allow_none': True},
             pin_reg_split=True, hold_pad={'cell': 'HB2xp67_ASAP7_75t_R'},
             reset_landing=c32k['reset_landing'], reset_relay_split=c32k['reset_relay_split'], clock='spine',
             orfs_vars=c32k['orfs_vars'], structural_change=why, purpose=why,
             safe_design_checklist=f'see physical/ref_tile/{KIT}/README.md')
    s['job'] = dict(owner='Claude:KDIE5-TV', branch='claude/kdie5-tv-1022', tag='r1', purpose=why,
                    extra_paths=['rtl', 'tools/qwen_kv_die', 'results/arch', 'results/rtl/qwen_kv_die/kdie5_tv_1022',
                                 'physical/qkd_kvs_kits'],
                    views_to=f'physical/ref_tile/{KIT}/views', record_to=f'results/rtl/ref_tile/{KIT}',
                    benches=[
                        dict(name='ctl_lockstep', cmd='bash tools/qwen_kv_die/kvs_tile_bench_relm.sh {RUN}/bench/ctl_m0 ctl 0',
                             expect='pass', threads=4, peak_ram_gb=8, needs=['verilator'],
                             pass_regex='^KVS_TILE PASS tile=ctl .* errors=0 mut=0', min_count_regex='checks=(\\d+)',
                             pass_witness='results/rtl/qwen_kv_die/kdie5_tv_1022/ctl_m0.log'),
                        dict(name='ctl_mut1', cmd='bash tools/qwen_kv_die/kvs_tile_bench_relm.sh {RUN}/bench/ctl_m1 ctl 1',
                             expect='fail', threads=4, peak_ram_gb=8, needs=['verilator'], pass_regex='^KVS_TILE PASS tile=ctl ',
                             fail_regex='^KVS_TILE FAIL tile=ctl .* mut=1 ',
                             fail_witness='results/rtl/qwen_kv_die/kdie5_tv_1022/ctl_m1.log'),
                        dict(name='ctl_mut2', cmd='bash tools/qwen_kv_die/kvs_tile_bench_relm.sh {RUN}/bench/ctl_m2 ctl 2',
                             expect='fail', threads=4, peak_ram_gb=8, needs=['verilator'], pass_regex='^KVS_TILE PASS tile=ctl ',
                             fail_regex='^KVS_TILE FAIL tile=ctl .* mut=2 ',
                             fail_witness='results/rtl/qwen_kv_die/kdie5_tv_1022/ctl_m2.log')])
    grant = dict(schema=M6.SCHEMA, master=M,
                 granted_by='STEWARD-QKc 2026-10-22 decision (b) MAIN (owner rule: M6 pin grants allowed when the tile does not grow)',
                 reason='Pin-density grant, NOT growth: the relm frame W / E faces carry 2524 pins each on 172.776 um (14.6 / um on '
                        'one layer > the 12 b/um/layer limit); M4 + M6 pin-only edge contacts = 7.3 / um / layer.  Outline 1123.176 x '
                        '172.776 and the M5 signal / PG cap unchanged; routed DEF / LEF M6 audit required.',
                 source_commit=SRC_COMMIT, source_spec_sha256=M6.spec_digest(s),
                 ports=[dict(name=n, face=f, span_um=[round(c - 0.032, 3), round(c + 0.032, 3)], max_depth_um=STUB,
                             max_area_um2=round(0.064 * STUB, 6)) for n, f, c in m6])
    M6.validate(grant, M)
    s['m6_pin_grant'] = grant
    d = WT / 'physical/ref_tile' / KIT
    d.mkdir(parents=True, exist_ok=True)
    (d / 'spec.json').write_text(json.dumps(s, indent=1) + '\n')
    (d / 'README.md').write_text(f'''# {KIT} (KDIE5-TV 10-22) -- release KV die qkd_kvs_ctl at the relm frame

{why}

**M6 grant = pin density, not growth.** W and E each carry 2524 pins (o_hroot_*S / *N 2 x 1118 + i_hroot 2 x 144) on a
172.776-um face: 14.6 pins/um on M4 alone exceeds the 12 b/um/layer FLOORPLAN_MARGIN limit (a 2-track M4 face holds 1800).
The pins alternate between 2-track M4 and 2-track M6 slots ({len(m6)} M6 contacts per kit, {STUB} um deep, PORT-only;
m6_pin_access stubs) = 7.3 pins/um/layer.  Outline, signal cap M5 and PG M5 are the frame's / the contract's.

SAFE checklist (pre-gate):
1 Pins: frame faces and bit order kept; pin registers OFF (the die static schedule charges 0 face edges; kv_tile_views
  refuses a view that adds them); reset landing 2 stages + kept copies (startup only, <= FACE_LAND_RST_BUDGET).
2 Reach: 1123-um wide tile; o_hroot W/E buses are member output flops (RTL); the gate textbook wire_reach decides.
3 Fanout: native census at the gate.  4 Depth: unchanged RTL.  5 Storage: flop tables (no macros in this RTL).
6 Floorplan: 6.5:1 frame (die slot, frozen); N 1.7 / S 0.1 pins/um; W/E 7.3 / um / layer with M6.
7 Clock: spine (c32k settings); pin-flop spread <= 80 TT+FF checked at the gate.  8 Schedule: static, +0 cycles.
Benches: kvs_tile_bench at the relm design point (tools/qwen_kv_die/kvs_tile_bench_relm.sh; the bench's kit tile text ==
the release module, checked): m0 PASS, m1 / m2 FAIL; m3 (child removed) is NOT detected by this bench (recorded, not used).
''')
    print(KIT, W, H, {f: len(v) for f, v in pins.items()}, 'M6', len(m6),
          'W layers', collections.Counter(L for n, (f, L, c) in placed.items() if f == 'W'))


main()
