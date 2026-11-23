#!/usr/bin/env python3
"""S81 svc monolithic attention cones: staging + PMEM + tr_x memory fit on the kit RTL (FAM-S81-SVC-OWN 11-22).

Generalizes s81_svc_hi4_att_fit.py (OPUS-FIX-S81-SVC-R9, t4_att split piece) to the J7 monolithic svc bounds
s81p_svc_{hi,lo}_dsdv_svc_rs__tN_bound / s81p_svc_hi_dsdv_svc_pvso_entry__t1_bound whose attention engine sits under
generate prefix g_u_rsv_NN_u_u[_u]_att_.  The cone is the same; the net names differ (rsv number, source-hash names,
numbered nets), so every name is DERIVED from the bound by one structural pattern per witness line, and each pattern
must match exactly once with consistent cross references.  Anything else raises (fail closed), nothing patches by
pattern alone:
  * the two stage2 ot_hdc_v41x_attn_staging instances -> _fit #(SRAM_MACRO 1),
  * native PMEM (ot_bind_native_193c...) + payload/skid cone -> ot_t7_pmem_capture_v2,
  * each ot_hdc_v41x_attn_tr_x hard core -> its signed physical_master variant (typed blackbox).
The native land (4c805) and pvq (9c28, absent) are NOT touched: land stays soft (plan land/pvq rows are dropped
by the plan row set).  Assets are R9's pinned files (s81_svc_hi4_att_fit/).
usage: s81_svc_att_fit_all.py --kit-rtl OUT --plan PLAN --type TYPE [--src-tree DIR]   (exit 0 = applied or n/a)"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s81_svc_hi4_att_fit as R9          # pinned assets, FitError, typed_tr (name pattern taken from the instance)

TYPES = {
    'svc_hi_dsdv_svc_rs__t4': 's81p_svc_hi_dsdv_svc_rs__t4_bound',
    'svc_hi_dsdv_svc_rs__t5': 's81p_svc_hi_dsdv_svc_rs__t5_bound',
    'svc_lo_dsdv_svc_rs__t3': 's81p_svc_lo_dsdv_svc_rs__t3_bound',
    'svc_lo_dsdv_svc_rs__t6': 's81p_svc_lo_dsdv_svc_rs__t6_bound',
    'svc_hi_dsdv_svc_pvso_entry__t1': 's81p_svc_hi_dsdv_svc_pvso_entry__t1_bound',
}
FitError = R9.FitError
PM = 'ot_bind_native_193c9bdc13b0c4251a5bbbc4'
STAGE = "ot_hdc_v41x_attn_staging #(.D(32), .NL(4), .SRAM_MACRO(1'b0), .TROWS(640)) "


def one(rx, text, what, flags=re.M):
    hits = re.findall(rx, text, flags)
    if len(hits) != 1:
        raise AssertionError(f'{what}: {len(hits)} matches')
    return hits[0]


def names(source):
    """generate prefix G (g_u_rsv_NN_u_u[_u]_att_) from the single native PMEM instance"""
    g = one(r'^\s*' + PM + r' (g_u_rsv_\d+_u_u(?:_u)?_att_)pmem \(', source, 'pmem instance')
    return g, 'w_' + g[2:], 'w_' + g[2:] + 'u_eng_'


def replace_stage(source, G):
    inst = 'u_' + G[2:] + 'u_eng_g_stage2_u_stage%d ('
    for i in range(2):
        row = STAGE + inst % i
        assert source.count(row) == 1, row
        source = source.replace(row, row.replace('attn_staging', 'attn_staging_fit').replace("1'b0", "1'b1"), 1)
    return source


def replace_pmem(source):
    G, P, E = names(source)
    pm = P + 'pmem_RD_DATA'
    line = next(x for x in source.splitlines() if x.lstrip().startswith(PM + ' ' + G + 'pmem ('))
    ports = dict(re.findall(r'\.(\w+)\((.*?)\)(?=,|\);)', line))
    h = r'(\w+)'
    # RD_ADDR = {driver_pr, driver_pr + 1}, WR_ADDR = driver_pw, WR_DATA/WR_EN single nets
    m = re.fullmatch(r'\{' + re.escape(P) + r'driver_pr_Q\[8:0\], (' + re.escape(P) + r'src_\w+_Y)\[8:0\]\}', ports['RD_ADDR'])
    assert m
    pr, inc = P + 'driver_pr_Q[8:0]', m[1]
    assert ports['RD_DATA'] == pm and ports['WR_ADDR'] == P + 'driver_pw_Q[8:0]' and ports['WR_CLK'] == 'clk'
    assert re.fullmatch(r'w_u_rsv_\w*?src_\w+_Q\[511:0\]', ports['WR_DATA']) and re.fullmatch(re.escape(P) + r'src_\w+_Y\[511:0\]', ports['WR_EN'])
    assert set(ports) == {'RD_ADDR', 'RD_DATA', 'WR_ADDR', 'WR_CLK', 'WR_DATA', 'WR_EN'}
    assert source.count(f'assign {inc} = {pr} + 9\'b000000001;') == 1
    # packed / second / phase
    m = re.search(r'^\s*assign (' + re.escape(P) + r'src_\w+_Y) = (\S+)\[0\] \? \{(' + re.escape(P) + r'src_\w+_Y)\[511:0\], '
                  + re.escape(pm) + r"\[1023:512\]\} : \{1024\{1'b0\}\};", source, re.M)
    assert m and len(re.findall(re.escape(pm) + r'\[1023:512\]', source)) == 1
    packed, owner, second = m[1], m[2], m[3]
    m = re.search(r'^\s*assign ' + re.escape(second) + r' = (' + re.escape(P) + r'src_\w+_Y)\[0\] \? ' + re.escape(pm)
                  + r"\[511:0\] : \{512\{1'b1\}\};", source, re.M)
    assert m
    phase2 = m[1]
    m = re.search(r'^\s*assign ' + re.escape(phase2) + r" = (\S+_Y)\[1:0\] == 2'b10;", source, re.M)
    assert m
    phase = m[1] + '[1:0]'
    payload = one(r'^\s*assign (\S+_Y) = ' + re.escape(packed) + r'\[1023:0\];', source, 'payload')
    owner = owner + '[0]'
    wp = E + 'driver_g_pskid_wp_Q[0]'
    sk = [E + f'driver_g_pskid_sk{i}_Q' for i in range(2)]
    skreg = [G + f'u_eng_driver_g_pskid_sk{i}_q' for i in range(2)]
    # mux nets feed the skid regs
    mux = []
    for i in range(2):
        mux.append(one(r'^\s*always @\(posedge clk\) ' + re.escape(skreg[i]) + r' <= (\S+_Y)\[1023:0\];', source, f'skid{i} reg'))
    sel = []
    for i in range(2):
        sel.append(one(r'^\s*assign ' + re.escape(mux[i]) + r' = (\S+_Y)\[0\] \? ' + re.escape(payload)
                       + r'\[1023:0\] : ' + re.escape(sk[i]) + r'\[1023:0\];', source, f'mux{i}'))
    # two '!wptr' assigns exist (rp/wp next-state and select); pick the one that feeds select0
    push = one(r'^\s*assign ' + re.escape(sel[1]) + r' = (\S+_Y\[0\]) && ' + re.escape(wp) + r';', source, 'select1')
    m = re.search(r'^\s*assign ' + re.escape(sel[0]) + r' = ' + re.escape(push) + r' && (\S+_Y)\[0\];', source, re.M)
    assert m
    not_wptr = m[1]
    assert source.count(f'assign {not_wptr} = !{wp};') == 1
    cut = {pm, payload, packed, second, mux[0], mux[1], *skreg}
    remove = re.compile(r'(^\s*(?:wire|assign) (?:\[.*?\] )?(?:' + '|'.join(re.escape(x) for x in cut - set(skreg)) + r')\b)|\b(?:'
                        + '|'.join(re.escape(x) for x in skreg) + r')\b', re.M)
    retained = '\n'.join(l for l in source.splitlines() if not remove.search(l))
    for n in cut - {pm}:
        assert not re.search(r'\b' + re.escape(n) + r'\b', retained), n
    child = '\n'.join([
        f'    ot_t7_pmem_capture_v2 {G}pmem_capture (',
        f"        .clk(clk), .pr({pr}), .wa({ports['WR_ADDR']}),",
        f'        .pstep({phase}), .owner({owner}), .push({push}), .wp({wp}),',
        f"        .wd({ports['WR_DATA']}), .wm({ports['WR_EN']}),",
        f'        .slot0({sk[0]}[1023:0]), .slot1({sk[1]}[1023:0]));',
    ])
    seed = retained.replace(line, child, 1) + '\n'
    assert PM + ' ' + G not in seed and pm not in seed
    assert len(re.findall(r'\bot_t7_pmem_capture_v2\b', seed)) == 1
    return seed, G


def typed_tr(source, typ, tree, G):
    """R9 typed_tr with this type's engine prefix (its `current` name is hardcoded to the t4_att piece)"""
    old = R9.typed_tr.__code__
    src = R9.typed_tr
    # re-implement through R9's code path by temporarily presenting its expected instance name
    flat = 'u_' + G[2:] + 'u_eng_g_tr_'
    pat = 'u_u_rsv_u_att_u_a_u_eng_g_tr_'
    marker = 'tmp_rename'
    s2 = source.replace(flat, pat)
    s2, assets = src(s2, typ, tree)
    return s2.replace(pat, flat), assets


def apply(out, plan, typ_name, tree):
    if not __debug__:
        raise FitError('run without -O: the netlist witnesses are assertions')
    out = Path(out)
    kj = out / 'kit_rtl.json'
    manifest = json.loads(kj.read_text())
    bm = manifest.get('bound_module')
    if typ_name not in TYPES or bm != TYPES[typ_name]:
        return dict(status='NOT_APPLICABLE', bound_module=bm)
    rec = out / 's81_svc_att_fit_all.json'
    if rec.exists():
        raise FitError('fit already applied (receipt exists): the kit RTL must come fresh from kit-rtl')
    if (out / 'memory_closure.json').exists() and json.loads((out / 'memory_closure.json').read_text()).get('status') == 'APPLIED':
        return dict(status='NOT_APPLICABLE', bound_module=bm, why='stock memory closure applied')
    bounds = [Path(x) for x in manifest['files'] if Path(x).stem == bm]
    if len(bounds) != 1 or bounds[0].resolve().parent != out.resolve():
        raise FitError('bound source is not exactly one file in the kit RTL dir')
    bound = bounds[0]
    before = bound.read_text()
    try:
        G = names(before)[0]
        source, G = replace_pmem(replace_stage(before, G))
    except (AssertionError, StopIteration) as e:
        raise FitError(f'netlist differs from the proved att cone witness: {e!r}'[:2000])
    if before.split(');', 1)[0] != source.split(');', 1)[0]:
        raise FitError('module header changed')
    typ = json.loads(Path(plan).read_text())['partition_types'][typ_name]
    source, typed = typed_tr(source, typ, Path(tree), G)
    assets = {}
    for f, want in R9.ASSET_SHA.items():
        b = (R9.ASSETS / f).read_bytes()
        if R9.sha(b)[:12] != want:
            raise FitError(f'asset {f} sha {R9.sha(b)[:12]} != pinned {want}')
        assets[f] = b
    assets.update(typed)
    for f in assets:
        if (out / f).exists():
            raise FitError(f'{f} already in the kit RTL dir')
    for f, b in assets.items():
        (out / f).write_bytes(b)
    new = [str(out / f) for f in assets]
    kf = out / 'kit_rtl.f'
    kf.write_text(kf.read_text().rstrip() + '\n' + '\n'.join(new) + '\n')
    manifest['files'].extend(new)
    kj.write_text(json.dumps(manifest, indent=1) + '\n')
    bound.write_text(source)
    topo = out / 'kit_topology.json'
    if topo.exists():
        sys.path.insert(0, str(HERE))
        import kit_topology as KT
        previous = json.loads(topo.read_text())
        check = KT.source_census(json.loads(Path(plan).read_text()), typ_name, out)
        diff = [k for k in previous.keys() - {'source', 'source_sha256'} if previous[k] != check.get(k)]
        if check.get('problems') or diff:
            raise FitError(f'kit topology census changed by the fit: {diff} {check.get("problems")}'[:2000])
        topo.rename(out / 'kit_topology.before_att_fit_all.json')
        topo.write_text(json.dumps(check, indent=2) + '\n')
    r = dict(status='APPLIED', type=typ_name, bound=str(bound), source_sha256_before=R9.sha(before.encode()),
             source_sha256=R9.sha(source.encode()), assets={f: R9.sha(b) for f, b in assets.items()},
             macros=dict(staging_160x265=8, pmem_256x256=4, tr_variants=len(typed)))
    rec.write_text(json.dumps(r, indent=2) + '\n')
    return r


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--kit-rtl')
    ap.add_argument('--plan')
    ap.add_argument('--type')
    ap.add_argument('--src-tree', default='.')
    ap.add_argument('--witness-only', metavar='BOUND_SV', help='check the cone witnesses on a bound file, write nothing')
    a = ap.parse_args(argv)
    try:
        if a.witness_only:
            src = Path(a.witness_only).read_text()
            s, G = replace_pmem(replace_stage(src, names(src)[0]))
            print('S81_SVC_ATT_FIT_ALL WITNESS PASS', G, len(src), '->', len(s))
            return 0
        r = apply(a.kit_rtl, a.plan, a.type, a.src_tree)
    except (FitError, AssertionError, StopIteration) as e:
        print('S81_SVC_ATT_FIT_ALL FAIL', repr(e)[:1500], file=sys.stderr)
        return 1
    print('S81_SVC_ATT_FIT_ALL', r['status'], r.get('source_sha256', r.get('bound_module')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
