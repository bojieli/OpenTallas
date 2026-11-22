#!/usr/bin/env python3
"""S81 svc hi4 att split piece: memory fit on the kit RTL (OPUS-FIX-S81-SVC-R9 11-22, COORD-approved).

The J8 hi4 split (svc_hi_dsdv_svc_rs__t4 -> __t4 + __t4_att) puts the attention engine in the att piece, whose bound
module is svc_hi_dsdv_svc_rs__t4_att_part_bound.  The stock svc memory closure (kit_rtl_post.d/s81_svc_memory.sh)
selects s81p_svc_* bounds only, so the att piece kept ~601k soft staging/PMEM bits (over the 400k OpenROAD cap).
This step applies the proved hi4 fit (Codex R8/R9 hi4 pilot, prior_hi4_memory_fit + r9_fit_hi4_sources):
  * the two stage2 staging instances -> ot_hdc_v41x_attn_staging_fit #(SRAM_MACRO 1) (8 x ot_sram_1r1w_160x265),
  * the native PMEM + its payload / skid cone -> ot_t7_pmem_capture_v2 (4 x ot_sram_1r1w_256x256),
  * each ot_hdc_v41x_attn_tr_x hard core -> its signed physical_master variant (typed blackbox; LEF port ABI and
    clock contract checked against the plan view).
FAIL-CLOSED: every replaced cone is matched against an exact netlist witness; any difference (renamed net, other
port map, other parameters, a second instance) raises and the kit stage fails.  Nothing is patched by pattern.
Assets (children + SRAM blackboxes) are pinned files next to this tool.
usage: s81_svc_hi4_att_fit.py --kit-rtl OUT --plan PLAN --type TYPE [--src-tree DIR]   (exit 0 = applied or n/a)"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ATT = 'svc_hi_dsdv_svc_rs__t4_att'
BOUND = ATT + '_part_bound'
ASSETS = Path(__file__).resolve().parent / 's81_svc_hi4_att_fit'
ASSET_SHA = {
    'ot_hdc_v41x_attn_staging_fit.sv': '58395b3f9310',
    'ot_t7_pmem_capture_v2.sv': '131c60c4ca10',
    'ot_sram_1r1w_160x265_m1_r0c0_bb.v': '115a7888156f',
    'ot_sram_1r1w_256x256_m1_r0c0_bb.v': '64968898a08b',
}
PREFIX = 'w_u_rsv_u_att_u_a_'
ENGINE = PREFIX + 'u_eng_'
GENERATE = 'g_u_rsv_u_att_u_a_'
TR_LOGICAL = 'ot_hdc_v41x_attn_tr_x'
TR_REQUIRED = dict(TD=32, NL=4, DPT=8)


class FitError(Exception):
    pass


def sha(b):
    return hashlib.sha256(b).hexdigest()


def replace_stage(source):
    module = "ot_hdc_v41x_attn_staging #(.D(32), .NL(4), .SRAM_MACRO(1'b0), .TROWS(640)) "
    before = [module + f'u_u_rsv_u_att_u_a_u_eng_g_stage2_u_stage{i} (' for i in range(2)]
    for row in before:
        assert source.count(row)==1
        source = source.replace(row, row.replace('attn_staging', 'attn_staging_fit').replace("1'b0", "1'b1"), 1)
    return source

def replace_pmem(source):
    raw_inst = 'ot_bind_native_193c9bdc13b0c4251a5bbbc4 ' + GENERATE + 'pmem'
    original = next(line for line in source.splitlines() if raw_inst + ' (' in line)
    ports = dict(re.findall(r'\.(\w+)\((.*?)\)(?=,|\);)',original))
    expected = {
        'RD_ADDR':'{' + PREFIX + 'driver_pr_Q[8:0], ' + PREFIX + 'src_1651537f0099f5e8b296_Y[8:0]}',
        'RD_DATA':PREFIX+'pmem_RD_DATA',
        'WR_ADDR':PREFIX+'driver_pw_Q[8:0]',
        'WR_CLK':'clk',
        'WR_DATA':'w_u_rsv_u_att_src_a522b67e2f8d4c0856fd_Q[511:0]',
        'WR_EN':PREFIX+'src_0f96741361b34e41097a_Y[511:0]',
    }
    assert ports == expected
    pr = PREFIX + 'driver_pr_Q[8:0]'
    phase = PREFIX + '765_Y[1:0]'
    owner = PREFIX + '768_Y[0]'
    push = ENGINE + '111_Y[0]'
    wptr = ENGINE + 'driver_g_pskid_wp_Q[0]'
    skid_out = [ENGINE + f'driver_g_pskid_sk{i}_Q' for i in range(2)]
    skid_reg = [GENERATE + f'u_eng_driver_g_pskid_sk{i}_q' for i in range(2)]
    mux_0 = ENGINE + 'src_82dbfb880ff11832511c_Y'
    mux_1 = ENGINE + 'src_78b0a765f0fe2c615f5d_Y'
    payload = PREFIX + '785_Y'
    packed = PREFIX + 'src_fbec4fd5cfde05d7eac1_Y'
    second = PREFIX + 'src_5877571a652d7724a45d_Y'
    phase2 = PREFIX + 'src_64bef01d53623389636d_Y'
    select0 = ENGINE + 'src_bafb416dc3650d88b313_Y'
    select1 = ENGINE + 'src_b3fd49500983f7d3ad57_Y'
    not_wptr = ENGINE + 'src_9b63422bdfff6b0a1f85_Y'
    witness = [
        f"assign {PREFIX}src_1651537f0099f5e8b296_Y = {pr} + 9'b000000001;",
        f"assign {phase2} = {phase} == 2'b10;",
        f"assign {not_wptr} = !{wptr};",
        f"assign {select0} = {push} && {not_wptr}[0];",
        f"assign {select1} = {push} && {wptr};",
        f"assign {second} = {phase2}[0] ? {ports['RD_DATA']}[511:0] : {{512{{1'b1}}}};",
        f"assign {packed} = {owner} ? {{{second}[511:0], {ports['RD_DATA']}[1023:512]}} : {{1024{{1'b0}}}};",
        f"assign {payload} = {packed}[1023:0];",
        f"assign {mux_0} = {select0}[0] ? {payload}[1023:0] : {skid_out[0]}[1023:0];",
        f"assign {mux_1} = {select1}[0] ? {payload}[1023:0] : {skid_out[1]}[1023:0];",
    ]
    for i, mux in enumerate((mux_0, mux_1)):
        witness += [f"always @(posedge clk) {skid_reg[i]} <= {mux}[1023:0];",
                    f"assign {skid_out[i]} = {skid_reg[i]};"]
    assert all(s in source for s in witness), [s for s in witness if s not in source]
    cut = set((ports['RD_DATA'], payload, packed, second, mux_0, mux_1, *skid_reg))
    remove = re.compile(r'(^\s*(?:wire|assign) (?:\[.*?\] )?(?:' + '|'.join(cut-set(skid_reg)) + r')\b)|'
                        +r'\b(?:'+'|'.join(skid_reg)+r')\b', re.M)
    retained = '\n'.join(line for line in source.splitlines() if not remove.search(line))
    for n in cut - {ports['RD_DATA']}:
        assert not re.search(r'\b'+n+r'\b', retained)
    child = "\n".join([
        f'    ot_t7_pmem_capture_v2 {GENERATE}pmem_capture (',
        f"        .clk(clk), .pr({pr}), .wa({ports['WR_ADDR']}),",
        f'        .pstep({phase}), .owner({owner}), .push({push}), .wp({wptr}),',
        f"        .wd({ports['WR_DATA']}), .wm({ports['WR_EN']}),",
        f'        .slot0({skid_out[0]}[1023:0]), .slot1({skid_out[1]}[1023:0]));',
    ])
    seed = retained.replace(original, child, 1) + '\n'
    assert raw_inst not in seed and ports['RD_DATA'] not in seed
    assert len(re.findall(r'\bot_t7_pmem_capture_v2\b',seed)) == 1
    return seed


def typed_tr(source, typ, tree):
    """ot_hdc_v41x_attn_tr_x instances -> the signed physical_master variant of each plan hard core."""
    header = re.search(r'^module ' + TR_LOGICAL + r' #\(.*?^\);', (tree / 'rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv').read_text(),
                       re.M | re.S)
    if not header:
        raise FitError('no ' + TR_LOGICAL + ' header in rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv')
    signed = json.loads((tree / 'tools/die_plan/hard_core_built_params.json').read_text())
    assets = {}
    n = 0
    for row in typ.get('hard_cores', []):
        if row.get('module') != TR_LOGICAL:
            continue
        xoff = int(row['params']['XOFF'])
        current = f'u_u_rsv_u_att_u_a_u_eng_g_tr_{xoff // 8}_g_x_u_tr'
        variant = row['physical_master']
        required = dict(TR_REQUIRED, XOFF=xoff)
        hard = [a for a in signed['entries'] if a.get('lib_contains', '').endswith('/' + variant + '/')]
        if len(hard) != 1 or {k: int(v) for k, v in hard[0]['params'].items()} != required:
            raise FitError(f'{variant}: signed params differ from {required}')
        rex = re.compile(fr'(?m)^(\s*){TR_LOGICAL}(\s+#\((.*?)\)\s+{current}\s+\()')
        hits = rex.findall(source)
        if len(hits) != 1 or {k: int(v) for k, v in re.findall(r'\.(\w+)\((\d+)\)', hits[0][2])} != required:
            raise FitError(f'{current}: expected one {TR_LOGICAL} #{required} instance, found {len(hits)}')
        source = rex.sub(lambda m: m[1] + variant + m[2], source)
        typed = header[0].replace('module ' + TR_LOGICAL, 'module ' + variant, 1)
        for key, value in required.items():
            typed, c = re.subn(fr'(parameter integer {key}\s*=\s*)\d+', lambda m: m[1] + str(value), typed)
            if c != 1:
                raise FitError(f'{variant}: parameter {key} not found once in the typed header')
        expected = {}
        for direction, width, name in re.findall(r'^\s*(input|output)\s+wire\s+(?:\[([^:]+):0\]\s+)?(\w+)[,]?\s*$', typed, re.M):
            if not width:
                expected[name] = direction
                continue
            for key, value in required.items():
                width = re.sub(r'\b' + key + r'\b', str(value), width)
            if not re.fullmatch(r'[0-9*+\- ]+', width):
                raise FitError(f'{variant}: unresolved port width {width}')
            for i in range(eval(width, {'__builtins__': {}}) + 1):
                expected[f'{name}[{i}]'] = direction
        lef = tree / row['lef']
        actual = {p: d.lower() for p, d in re.findall(r'^\s*PIN\s+(\S+)\s*\n\s*DIRECTION\s+(INPUT|OUTPUT)\s*;', lef.read_text(), re.M)}
        if expected != actual:
            raise FitError(f'{variant}: RTL port ABI ({len(expected)}) differs from the signed LEF ({len(actual)})')
        contract = json.loads((lef.parent / 'clock_contract.json').read_text())
        if not contract.get('signed') or contract.get('view_lib_sha256') != sha((tree / row['lib']).read_bytes()):
            raise FitError(f'{variant}: clock contract not signed for this view lib')
        assets[variant + '_bb.v'] = ('(* blackbox *)\n' + typed + '\nendmodule\n').encode()
        n += 1
    if n != 4:
        raise FitError(f'expected 4 {TR_LOGICAL} hard cores in {ATT}, found {n}')
    return source, assets


def apply(out, plan, typ_name, tree):
    if not __debug__:
        raise FitError('run without -O: the netlist witnesses are assertions')
    out = Path(out)
    kj = out / 'kit_rtl.json'
    manifest = json.loads(kj.read_text())
    if manifest.get('bound_module') != BOUND:
        return dict(status='NOT_APPLICABLE', bound_module=manifest.get('bound_module'))
    if typ_name != ATT:
        raise FitError(f'bound {BOUND} under type {typ_name}')
    rec = out / 's81_svc_hi4_att_fit.json'
    if rec.exists():
        raise FitError('fit already applied (receipt exists): the kit RTL must come fresh from kit-rtl')
    bounds = [Path(x) for x in manifest['files'] if Path(x).stem == BOUND]
    if len(bounds) != 1 or bounds[0].resolve().parent != out.resolve():
        raise FitError('bound source is not exactly one file in the kit RTL dir')
    bound = bounds[0]
    before = bound.read_text()
    try:
        source = replace_pmem(replace_stage(before))
    except (AssertionError, StopIteration) as e:
        raise FitError(f'netlist differs from the proved hi4 att cone witness: {e!r}'[:2000])
    if before.split(');', 1)[0] != source.split(');', 1)[0]:
        raise FitError('module header changed')
    typ = json.loads(Path(plan).read_text())['partition_types'][ATT]
    source, typed = typed_tr(source, typ, Path(tree))
    assets = {}
    for f, want in ASSET_SHA.items():
        b = (ASSETS / f).read_bytes()
        if sha(b)[:12] != want:
            raise FitError(f'asset {f} sha {sha(b)[:12]} != pinned {want}')
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
        # the station/landing census must be unchanged by the fit (only the memory cones and tr masters move)
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import kit_topology as KT
        previous = json.loads(topo.read_text())
        check = KT.source_census(json.loads(Path(plan).read_text()), ATT, out)
        diff = [k for k in previous.keys() - {'source', 'source_sha256'} if previous[k] != check.get(k)]
        if check.get('problems') or diff:
            raise FitError(f'kit topology census changed by the fit: {diff} {check.get("problems")}'[:2000])
        topo.rename(out / 'kit_topology.before_hi4_att_fit.json')
        topo.write_text(json.dumps(check, indent=2) + '\n')
    r = dict(status='APPLIED', type=ATT, bound=str(bound), source_sha256_before=sha(before.encode()),
             source_sha256=sha(source.encode()), assets={f: sha(b) for f, b in assets.items()},
             macros=dict(staging_160x265=8, pmem_256x256=4, tr_variants=len(typed)))
    rec.write_text(json.dumps(r, indent=2) + '\n')
    return r


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--kit-rtl', required=True)
    ap.add_argument('--plan', required=True)
    ap.add_argument('--type', required=True)
    ap.add_argument('--src-tree', default='.')
    a = ap.parse_args(argv)
    try:
        r = apply(a.kit_rtl, a.plan, a.type, a.src_tree)
    except FitError as e:
        print('S81_SVC_HI4_ATT_FIT FAIL', e, file=sys.stderr)
        return 1
    print('S81_SVC_HI4_ATT_FIT', r['status'], r.get('source_sha256', r.get('bound_module')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
