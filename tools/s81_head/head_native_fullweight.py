#!/usr/bin/env python3
"""TOK-ALL-14: HEAD die per-tile native vehicle on the REAL released head.weight (all active tiles of one rank).

Replaces the single 128-row fixture bundle (row0 21888) by every active hd_tile slot of the current HEAD die plan
(physical/die_plan/s81_head/die_plan.json id_straps strap_row0/strap_ten): each tile's bundle images are written
from the released DeepSeek-V4.1-Flash head.weight (shard 43) at the closed-view skew SK 11 and driven with the golden
final-norm x of the 1M token (ctx1048576_head.npz xf).  The generated native partition (ot_s81hd_tile_p ->
ot_s81hd_tile_native + real CV/ROM models + 40 FT pins) runs lockstep against the independent legacy reference tile;
each tile's emitted {row, FP32 bits} must equal the golden argmax of its 128 golden logits (lowest id on ties).

  gen    python3 -I tools/s81_head/head_native_fullweight.py gen  OUT [--rank 0] [--jobs N]
  build  python3 -I tools/s81_head/head_native_fullweight.py build NATIVE_DIR OUT [--jobs 8]
  run    python3 -I tools/s81_head/head_native_fullweight.py run  OUT [--jobs N]
Env: DSROM_1M_SNAP (snapshot dir with shard 43 + index), DSROM_1M_HEAD_REF (ctx1048576_head.npz).
"""
import argparse, hashlib, json, multiprocessing, os, re, subprocess, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "s81_head"))
PLAN = ROOT / "physical/die_plan/s81_head/die_plan.json"
ROWS_RANK_PLAN = 32384          # established HEAD row bases 0/32384/64768/97024
SK_CLOSED = 11                  # CUT 0x1ff + SPLIT9 (closed element views), as hd_reskew_images.py --to 11

_U = _X16 = _LOG = None


def tiles(rank=0):
    """(name, ROW0, TEN) of every hd_tile slot for RANK.  Rank 0 = the plan's own id_straps.  Ranks 1-3 come from the
    source row-map contract (head_row_map.build: rank sizes 253/253/252/252, bases 0/32384/64768/97024).  Every slot
    the map enables must carry the plan's ROW0 strap (fail-closed); TEN comes from the map, so ranks 2/3 leave slot
    tE5o10 dark (the plan holds only the rank-0 strap set, TEN=1 there).  TOK-HEAD-LAND-1."""
    d = json.loads(PLAN.read_text())
    plan = [(p['name'], p['id_straps']['strap_row0'], p['id_straps']['strap_ten'])
            for p in d['partitions'] if p['type'] == 'hd_tile']
    if rank == 0:
        return plan
    import head_row_map as RM
    m = {s['part']: (s['mask_params']['ROW0'], s['mask_params']['TEN']) for s in RM.build(PLAN)['ranks'][rank]['slots']}
    for n, r0, ten in plan:
        if m[n][1] and m[n][0] != r0:
            raise SystemExit(f'rank {rank}: row map ROW0 {m[n][0]} != plan strap {r0} on enabled slot {n}')
    return [(n, m[n][0], m[n][1]) for n, _, _ in plan]


def rank_base(rank):
    """controller row base of RANK = prefix sum of the row-map rank sizes (NOT rank * 32384: rank 3 is 97024)."""
    import head_row_map as RM
    return RM.build(PLAN)['ranks'][rank]['controller_row_base']


def _gen_one(args):
    name, row0, out = args
    import dsrom_1m_head as H
    H.SK = SK_CLOSED
    t = Path(out) / name; t.mkdir(parents=True, exist_ok=True)
    u = _U[row0:row0 + 128]
    for q in range(4):
        H.write_macro(H.skewed_image(u[32 * q:32 * q + 32, :4096].reshape(H.NW, 16)), t, f"ha{q}")
    perm = np.array([32 * (n % 4) + n // 4 for n in range(128)])
    H.write_macro(H.skewed_image(u[perm, 4096:].reshape(H.NW, 16)), t, "hb")
    for f in ("xa.hex", "xb.hex"):
        dst = t / f
        if not dst.exists(): os.symlink("../" + f, dst)
    lg = _LOG[row0:row0 + 128]
    b = int(np.argmax(lg))
    return name, dict(row0=row0, row=row0 + b, bits=f"{int(H.G.bits(lg[b:b+1])[0]):08x}")


def cmd_gen(a):
    global _U, _X16, _LOG
    import dsrom_1m_head as H
    H.setup_gate()
    xf, logits = H.golden_x()
    ck = H.Ckpt(H.SNAP)
    dt, sh, buf = ck.raw("head.weight")
    assert dt == "BF16" and sh == [129280, 5120], (dt, sh)
    rb = rank_base(a.rank)
    full = np.frombuffer(buf, dtype=np.uint16).reshape(sh)
    _U = np.zeros((ROWS_RANK_PLAN + 128, 5120), dtype=np.uint64)
    n = min(ROWS_RANK_PLAN + 128, 129280 - rb); _U[:n] = full[rb:rb + n]
    _LOG = np.full(ROWS_RANK_PLAN + 128, -np.inf, dtype=np.float32); _LOG[:n] = logits[rb:rb + n]
    x16 = (H.G.bits(xf).astype(np.uint32) >> 16).astype(np.uint64)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    sl = lambda xx, k: "".join("".join(f"{int(v):04x}" for v in xx[16 * i:16 * i + 16][::-1]) + "\n" for i in range(k))
    (out / "xa.hex").write_text(sl(x16[:4096], 256)); (out / "xb.hex").write_text(sl(x16[4096:], 64))
    act = [(nm, r0, str(out)) for nm, r0, ten in tiles(a.rank) if ten]
    with ProcessPoolExecutor(a.jobs, mp_context=multiprocessing.get_context('fork')) as ex:
        gold = dict(ex.map(_gen_one, act))
    rows_cov = sorted(g['row0'] for g in gold.values())
    assert rows_cov == list(range(0, 128 * len(rows_cov), 128)), "strap rows must tile the rank contiguously"
    best = max(gold.items(), key=lambda kv: (np.float32(np.uint32(int(kv[1]['bits'], 16)).view(np.float32)), -kv[1]['row']))
    meta = dict(rank=a.rank, row_base=rb, active_tiles=len(gold), inactive_tiles=len(tiles(a.rank)) - len(gold),
                rows=128 * len(gold), rank_argmax_local=best[1]['row'], rank_argmax_global=rb + best[1]['row'],
                rank_argmax_bits=best[1]['bits'], rank_argmax_tile=best[0],
                golden_global_argmax=int(np.argmax(logits)), sk=SK_CLOSED,
                checkpoint_header_sha256=ck.pins,
                head_npz_sha256=hashlib.sha256(Path(H.REF).read_bytes()).hexdigest(), tiles=gold)
    (out / "golden.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(json.dumps({k: v for k, v in meta.items() if k != 'tiles'}))


def cmd_build(a):
    """Same transformation as head_native_partition_miter.py, plus +ROW0/+EXP_ROW/+EXP_BITS plusargs."""
    out = Path(a.out); out.mkdir(parents=True, exist_ok=False)
    refs = []
    renames = ['ot_s81hd_elemA_cv', 'ot_s81hd_elemB_cv', 'ot_s81hd_bundle', 'ot_s81hd_tile', 'ot_s81hd_kreg', 'ot_s81hd_kregr']
    for stem in ['ot_s81hd_elem_cv', 'ot_s81hd_bundle', 'ot_s81hd_tile']:
        text = (ROOT / 'rtl/dsrom_sys/s81_head' / (stem + '.sv')).read_text()
        for nm in renames: text = re.sub(r'\b' + nm + r'\b', nm + '_reference', text)
        tgt = out / (stem + '_reference.sv'); tgt.write_text(text); refs.append(str(tgt))
    tb = (ROOT / 'rtl/dsrom_sys/s81_head/test/tb_head_partition_token.sv').read_text().replace('ot_s81hd_tile #', 'ot_s81hd_tile_reference #')
    ports = []
    for i in range(5):
        for j, n in enumerate(('ck0', 'ck1', 'mesh', 'rst')):
            k = 4 * i + j; ports += [f'.hci{i}_{n}_i(ft_drive[{k}])', f'.hci{i}_{n}_o(ft_out[{k}])']
    def sub(old, new):
        nonlocal tb
        assert tb.count(old) == 1, old
        tb = tb.replace(old, new)
    sub('integer mutant=0;wire[16:0]tile_row=17\'d21888+(mutant?17\'d128:17\'d0);',
        "integer mut_ft=0;reg[19:0]ft_pattern=20'h591c7;wire[19:0]ft_out;wire[19:0]ft_drive=ft_pattern^(mut_ft?20'd1:20'd0);integer ft_checks=0;\n"
        "always@(negedge ck)begin if(cyc>2)begin if(ft_out!==ft_pattern)$fatal(1,\"HEAD_NATIVE_FT mismatch\");ft_checks+=20;end ft_pattern<={ft_pattern[18:0],ft_pattern[19]^ft_pattern[16]};end\n"
        "integer mutant=0;integer row0_i=21888,exp_row_i=21946;reg[31:0]exp_bits=32'h4173a558;wire[16:0]ref_row0=row0_i[16:0];wire[16:0]tile_row=ref_row0+(mutant?17'd128:17'd0);")
    sub('dut(.clk(ck),', 'dut(' + ','.join(ports) + ',.clk(ck),')
    sub('.row0(17\'d21888)', '.row0(ref_row0)')
    sub("dout[531:515]!==17'd21946||dout[563:532]!==32'h4173a558", "dout[531:515]!==exp_row_i[16:0]||dout[563:532]!==exp_bits")
    sub(' if(!$value$plusargs("DIR=%s",dir))',
        ' if($value$plusargs("MUT_FT=%d",mut_ft))begin end\n if($value$plusargs("ROW0=%d",row0_i))begin end\n'
        ' if($value$plusargs("EXP_ROW=%d",exp_row_i))begin end\n if($value$plusargs("EXP_BITS=%h",exp_bits))begin end\n'
        ' if(!$value$plusargs("DIR=%s",dir))')
    sub('$display("HEAD_PARTITION_TOKEN PASS', '$display("HEAD_NATIVE_FT PASS checks%0d",ft_checks);\n $display("HEAD_PARTITION_TOKEN PASS row0 %0d',)
    tb = tb.replace('PASS row0 %0d rows128 dims5120 positions1 checks%0d added_boundary_cycles2",checks)',
                    'PASS row0 %0d rows128 dims5120 positions1 checks%0d added_boundary_cycles2",row0_i,checks)')
    (out / 'tb_native.sv').write_text(tb)
    native = Path(a.native)
    cmd = ['verilator', '--binary', '--timing', '-O1', '-Wno-fatal', '-Wno-WIDTH', '-Wno-TIMESCALEMOD', '--top-module',
           'tb_head_partition_token', '-f', str(native / 'native.f'), *refs, str(out / 'tb_native.sv'), '--Mdir', str(out / 'obj'),
           '--build-jobs', str(a.jobs), '-MAKEFLAGS', 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0']
    with (out / 'build.log').open('w') as f:
        subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, check=True, cwd=ROOT)
    print('BUILD OK', out / 'obj/Vtb_head_partition_token')


def _run_one(args):
    exe, img, name, g, extra, tag = args
    d = Path(img) / name
    log = Path(img).parent / 'logs' / f'{name}.{tag}.log'
    cmd = [exe, f'+DIR={d}', f'+OT_ROM_DIR={d}', f'+ROW0={g["row0"]}', f'+EXP_ROW={g["row"]}', f'+EXP_BITS={g["bits"]}', *extra]
    with log.open('w') as f:
        p = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
    txt = log.read_text()
    m = re.search(r'HEAD_PARTITION_RESULT row(\d+) bits([0-9a-f]+) go_to_result(\d+)', txt)
    c = re.search(r'checks(\d+) added', txt); ft = re.search(r'HEAD_NATIVE_FT PASS checks(\d+)', txt)
    return dict(tile=name, tag=tag, exit=p.returncode, row=int(m.group(1)) if m else None, bits=m.group(2) if m else None,
                go_to_result=int(m.group(3)) if m else None, checks=int(c.group(1)) if c else None,
                ft_checks=int(ft.group(1)) if ft else None, pass_line='HEAD_PARTITION_TOKEN PASS' in txt,
                fatal=(re.search(r'(HEAD_\w+ [^\n]*mismatch[^\n]*)', txt) or [None, None])[1] if p.returncode else None)


def cmd_run(a):
    out = Path(a.out); img = out / 'img'; (out / 'logs').mkdir(exist_ok=True)
    exe = str(Path(a.exe).resolve())
    gold = json.loads((img / 'golden.json').read_text())
    T = gold['tiles']
    jobs = [(exe, str(img), n, g, [], 'pos') for n, g in T.items()]
    names = sorted(T)
    gt = gold['rank_argmax_tile']; other = next(n for n in names if n != gt)
    # controls: wrong-ROM (gold tile driven with a neighbour's images, golden expectation unchanged), mut_row, mut_ft
    wr = dict(T[gt]); jobs_c = [(exe, str(img), other, dict(T[gt]), [], 'wrongrom'),
                                (exe, str(img), gt, T[gt], ['+MUT_ROW=1'], 'mutrow'),
                                (exe, str(img), gt, T[gt], ['+MUT_FT=1'], 'mutft')]
    with ProcessPoolExecutor(a.jobs, mp_context=multiprocessing.get_context('fork')) as ex:
        R = list(ex.map(_run_one, jobs + jobs_c))
    pos = [r for r in R if r['tag'] == 'pos']; ctl = [r for r in R if r['tag'] != 'pos']
    bad = [r for r in pos if not (r['exit'] == 0 and r['pass_line'] and r['row'] == T[r['tile']]['row'] and r['bits'] == T[r['tile']]['bits'])]
    ctl_ok = {r['tag']: (r['exit'] != 0 and not r['pass_line']) for r in ctl}
    g2r = sorted({r['go_to_result'] for r in pos})
    best = max(pos, key=lambda r: (np.uint32(int(r['bits'], 16)).view(np.float32), -r['row']))
    res = dict(verdict='PASS_ALL_ACTIVE_TILES' if not bad and all(ctl_ok.values()) else 'FAIL',
               rank=gold['rank'], active_tiles=len(pos), failed_tiles=[r['tile'] for r in bad][:20], n_failed=len(bad),
               rows_checked_via_argmax=128 * len(pos), go_to_result_cycles=g2r,
               lockstep_checks_total=sum(r['checks'] or 0 for r in pos), ft_scalar_checks_total=sum(r['ft_checks'] or 0 for r in pos),
               rtl_rank_argmax=dict(tile=best['tile'], local_row=best['row'], global_row=gold['row_base'] + best['row'], bits=best['bits']),
               golden_rank_argmax=dict(tile=gold['rank_argmax_tile'], global_row=gold['rank_argmax_global'], bits=gold['rank_argmax_bits']),
               controls=ctl_ok, control_detail=ctl, exe=exe, exe_sha256=hashlib.sha256(Path(exe).read_bytes()).hexdigest())
    res['rank_argmax_match'] = (res['rtl_rank_argmax']['global_row'] == res['golden_rank_argmax']['global_row']
                                and res['rtl_rank_argmax']['bits'] == res['golden_rank_argmax']['bits'])
    (out / 'per_tile.json').write_text(json.dumps(pos, indent=0) + '\n')
    (out / 'result.json').write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps({k: v for k, v in res.items() if k != 'control_detail'}))


ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
g = sp.add_parser('gen'); g.add_argument('out'); g.add_argument('--rank', type=int, default=0); g.add_argument('--jobs', type=int, default=16)
b = sp.add_parser('build'); b.add_argument('native'); b.add_argument('out'); b.add_argument('--jobs', type=int, default=8)
r = sp.add_parser('run'); r.add_argument('out'); r.add_argument('exe'); r.add_argument('--jobs', type=int, default=16)
a = ap.parse_args()
dict(gen=cmd_gen, build=cmd_build, run=cmd_run)[a.cmd](a)
