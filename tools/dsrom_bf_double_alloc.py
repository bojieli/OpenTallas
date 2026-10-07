#!/usr/bin/env python3
"""DS ROM BF half-rate allocation (OWNER 2026-10-07: BF half-rate + more BF pairs; Claude bf-double).

Metadata-only ownership map, the S73/S81 allocator (tools/dsrom_s73_pair1.py) with two die flavours:

  BF stage   PBF pairs (default 2,304 = 18 a region, the f183.60 frame), exactly NBF_REG (4) BF pairs in every region,
             BF16-DEDICATED: the BF element runs at half rate (ot_s81_bf_native HALF=1), so no FP8 / FP4 plan may
             sit on a BF pair (a q phase would wait for it).  4 BF a region lets a 1,024-row wo_a group run as ONE
             phase (row split limit 256 x min BF a region = 1,024; today 768 -> rows0 + rows768 phases).
  q stage    PQ pairs (default 2,432 = 19 a region, the f183.60 return-strip limit 2n-1 <= 37 nodes), no BF pair.

Layer placement: a layer's dense (non-expert) matrices and its HE / CROM providers go on ONE BF stage (as today: one
die_stage for attention + router + shared); its routed experts fill that stage's remaining q pairs and then follow-on
stages.  A follow-on stage is opened as a BF stage when the layer's remaining experts AND the next layer's dense block
fit on it (no partially filled q stage before a BF stage), otherwise as a q stage.

    python3 tools/dsrom_bf_double_alloc.py --out results/uarch/dsrom_bf_double_binding_20261007/canonical
"""
import argparse, collections, copy, gzip, hashlib, json, math, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dsrom_full_owner_compiler as C
import dsrom_full_owner_closure as V
import dsrom_s73_pair1 as S73
import v41_rom_ksplit_bankmap as S

ROOT = Path(__file__).resolve().parents[1]
R = 128


class FlavourPool(S73.RaggedPool):
    """RaggedPool with an explicit flavour: 'bf' (nbf_reg BF16-dedicated BF pairs a region) or 'q' (no BF pair)."""

    def __init__(self, flavour, pairs, nbf_reg, dedicated=True):
        self.flavour = flavour
        self.pairs = self.np = pairs
        self.balance_raw = True
        self.bounds = [r * pairs // R for r in range(R + 1)]
        self.bf = set()
        self.byreg = {}
        for r in range(R):
            ps = list(range(self.bounds[r], self.bounds[r + 1]))
            if flavour == 'bf':
                n = len(ps)
                bs = sorted({ps[(2 * j + 1) * n // (2 * nbf_reg)] for j in range(nbf_reg)})
                assert len(bs) == nbf_reg, (r, bs)
                self.bf.update(bs)
            # BF16-dedicated (half-rate BF): q never on a BF pair; shared (full-rate BF): q on every pair, as S81
            self.byreg[(r, 'q')] = [p for p in ps if p not in self.bf] if dedicated else ps
            self.byreg[(r, 'bf16')] = [p for p in ps if p in self.bf]
        self.bfcount = len(self.bf)
        self.fill = dict.fromkeys(range(pairs), 0); self.raw = set(); self.phases = 0
        self.ecc_bits = 0; self.ecc_pairs = []

    def clone(self):
        x = super().clone(); x.__class__ = FlavourPool; x.flavour = self.flavour; return x

    KSPLIT = frozenset()        # BF16 aliases whose K split doubles (golden-aligned v41_rom_ksplit_bankmap.segments)

    def matrix(self, m, avoid=frozenset()):
        if m['format'] == 'bf16' and m['alias'].split('.rows')[0] in self.KSPLIT:
            orig = C.ordered_segments
            C.ordered_segments = lambda fmt, K: S.segments(K, 2 * len(orig(fmt, K)))
            try:
                return self._matrix(m, avoid)
            finally:
                C.ordered_segments = orig
        return self._matrix(m, avoid)

    def _matrix(self, m, avoid=frozenset()):
        """BF16: first try pairs outside `avoid` (the pairs of earlier matrices sharing this one's x), so the field
        emitter can run them as ONE phase (<= 8 BF16 words a round a pair); fall back to every BF pair."""
        if m['format'] != 'bf16' or not avoid:
            return super().matrix(m)
        keep = self.byreg
        t = self.clone()
        t.byreg = {k: ([p for p in v if p not in avoid] if k[1] == 'bf16' else v) for k, v in keep.items()}
        try:
            x = C.Pool.matrix(t, m)
        except C.CapacityError:
            return super().matrix(m)
        self.fill, self.phases, self.ecc_bits, self.ecc_pairs = t.fill, t.phases, t.ecc_bits, t.ecc_pairs
        return x


def x_group(alias):
    """matrices that read one x vector (tools/dsrom_1m_field.group_of): the a_proj BF16 sub-phases share attn_norm"""
    if alias.startswith('compressor.') or alias == 'indexer.weights_proj':
        return 'a_proj.bf16'
    if alias.startswith('wo_a.group'):
        return alias.split('.rows')[0]
    return alias.split('.rows')[0]


def split_rows(m, limit):
    out = []
    for first in range(0, m['rows'], limit):
        n = min(limit, m['rows'] - first); x = copy.deepcopy(m)
        if m['rows'] > limit:
            x.update(alias=m['alias'] + '.rows' + str(first), original_alias=m['alias'], row_offset=first, rows=n,
                     output_row_split_delivery_qualified=False)
            for s in x['rank_slices']:
                s['rows'] = [s['rows'][0] + first, s['rows'][0] + first + n]
        out.append([x])
    return out


def mapping(out, pbf=2304, pq=2432, nbf_reg=4, dedicated=True):
    headers = C.load_headers(ROOT / 'results/uarch/dsrom_fixed4096_owner_compiler_20261002/inputs/tensor_headers.jsonl.gz')
    decls = [C.declarations(headers, L) for L in range(40)]
    proto = FlavourPool('bf', pbf, nbf_reg, dedicated)
    qlim = 256 * min(len(proto.byreg[(r, 'q')]) for r in range(R))       # q rows a phase on a BF stage
    blim = 256 * nbf_reg
    pools, providers, homes, covered = [], [], {}, set()
    counts = collections.Counter(); layers = collections.defaultdict(set); failures = []
    intervals = collections.defaultdict(list); dense_stage = {}

    def blocks(L):
        groups, cs, he, _, names = decls[L]
        dense = []
        for m in groups[None]:
            dense += split_rows(m, blim if m['format'] == 'bf16' else qlim)
        experts = [ms for e, ms in groups.items() if e is not None]
        return dense, experts

    used = collections.defaultdict(set)      # (stage, layer, x group) -> BF pairs already holding that x's rows

    def place(pool, ms, stage):
        planned = []
        for m in ms:
            key = (stage, m['layer'], x_group(m['alias']))
            x = pool.matrix(m, frozenset(used[key]))
            x.update(stage=stage, compiled_NP=pool.np, die_flavour=pool.flavour,
                     ECC=dict(useful_bits=m['ECC']['useful_bits'], secded_bits=0, extra_sidecar_bits=0), ecc_bit_base=None)
            S73.check(x, pool); planned.append(x)
            if x['format'] == 'bf16':
                used[key].update(p for _, p, *_ in x['plans'])
        return planned

    def place_providers(pool, L, stage):
        _, cs, he, _, names = decls[L]
        hw = sum(x['rows'] * math.ceil(x['K'] / 64) for x in he)
        cw = math.ceil(sum(x['elements'] for x in cs) / 8)
        res = []
        for kind, ds, words, banks in [('HE', he, hw, 8), ('CROM', cs, cw, 1)]:
            res.append(dict(layer=L, stage=stage, kind=kind, declarations=ds,
                            **pool.raw_bankset([x['alias'] for x in ds], words, banks)))
        return res

    def try_all(pool, L, items, stage, with_providers, commit_ok=True):
        """place a list of blocks on a clone; returns (pool, provs, planned) or None"""
        t = pool.clone(); provs, planned = [], []
        snap = {k: set(v) for k, v in used.items()}
        try:
            if with_providers:
                provs = place_providers(t, L, stage)
            for ms in items:
                planned += place(t, ms, stage)
        except C.CapacityError:
            used.clear(); used.update(snap)
            return None
        if not commit_ok:
            used.clear(); used.update(snap)
        return t, provs, planned

    target = out / 'matrix_map.jsonl.gz'
    if target.exists():
        raise ValueError('Use a fresh attempt directory')
    with target.open('wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0) as z:
        def emit(L, planned):
            for m in planned:
                counts['declarations'] += 1; counts['placed'] += 1; layers[L].add(m['stage'])
                for _, p, _, n, _, a, w in m['plans']:
                    intervals[(m['stage'], p)].append((a, a + n * w))
                z.write((json.dumps(m, separators=(',', ':'), sort_keys=True) + '\n').encode())
        pend = []               # layers whose HE / CROM providers (complete empty q pairs) still need a home

        def flush_providers(s):
            nonlocal providers
            for L_ in list(pend):
                t = pools[s].clone()
                try:
                    provs = place_providers(t, L_, s)
                except C.CapacityError:
                    continue
                pools[s] = t; providers += provs; homes[L_] = s; pend.remove(L_)

        def new_stage(flav, flush=True):
            pools.append(FlavourPool(flav, pbf if flav == 'bf' else pq, nbf_reg, dedicated))
            if flush:
                flush_providers(len(pools) - 1)  # a fresh expert stage: the providers take complete empty pairs first

        for L in range(40):
            dense, experts = blocks(L)
            _, cs, he, _, names = decls[L]; covered.update(names)
            pend.append(L)
            # the layer's dense block on ONE BF stage: the current one if it is BF and fits, else a new one
            got = None
            if pools and pools[-1].flavour == 'bf':
                got = try_all(pools[-1], L, dense, len(pools) - 1, False)
            if got is None:
                new_stage('bf', flush=False)    # the dense block first (its row splits use every pair of a region)
                got = try_all(pools[-1], L, dense, len(pools) - 1, False)
                assert got is not None, f'layer {L}: dense block does not fit an empty BF stage'
            s = len(pools) - 1
            pools[s], _, planned = got
            dense_stage[L] = s; emit(L, planned)
            flush_providers(s)
            # experts: fill the current stage, then follow-on stages
            rest = list(experts)
            while rest:
                ms = rest[0]
                g = try_all(pools[-1], L, [ms], len(pools) - 1, False)
                if g is not None:
                    pools[-1], _, planned = g; emit(L, planned); rest.pop(0); continue
                # open a follow-on stage: BF if this layer's remaining experts + the next layer's dense block fit on it
                flav = 'q' if dedicated else 'bf'
                if dedicated and L + 1 < 40:
                    nd, _ = blocks(L + 1)
                    t = FlavourPool('bf', pbf, nbf_reg, dedicated)
                    g1 = try_all(t, L, rest, len(pools), False, commit_ok=False)
                    if g1 is not None and try_all(g1[0], L + 1, nd, len(pools), False, commit_ok=False) is not None:
                        flav = 'bf'
                new_stage(flav)
                g = try_all(pools[-1], L, [ms], len(pools) - 1, False)
                if g is None:
                    failures.append(dict(layer=L, aliases=[m['alias'] for m in ms], error='does not fit an empty stage'))
                    rest.pop(0); continue
                pools[-1], _, planned = g; emit(L, planned); rest.pop(0)
            print(json.dumps(dict(layer=L, dense_stage=dense_stage[L], last_stage=len(pools) - 1,
                                  flavours=''.join(p.flavour[0] for p in pools[dense_stage[L]:]))), flush=True)
        if pend:
            new_stage('q' if dedicated else 'bf')
        assert not pend, f'providers without a home: {pend}'
    for p in providers:
        for pair in p['pairs']:
            intervals[(p['stage'], pair)].append((0, 8192))
    for spans in intervals.values():
        spans.sort(); assert all(a[1] <= b[0] for a, b in zip(spans, spans[1:]))
    stages = len(pools)
    S73.save(out / 'providers.json', providers)
    S73.save(out / 'stage_map.json', dict(
        layer_matrix_stages={k: sorted(v) for k, v in layers.items()}, provider_homes=homes, dense_stage=dense_stage,
        stage_flavour=[p.flavour for p in pools],
        region_bounds_by_stage=[p.bounds for p in pools], BF_site_IDs_by_stage=[sorted(p.bf) for p in pools],
        region_bounds=proto.bounds, BF_site_IDs=sorted(proto.bf),
        rank_dies=[dict(stage=s, rank=r, die_id=4 * s + r) for s in range(stages) for r in range(4)],
        scan_layers=[2, 8, 14, 20, 24, 28, 32, 36], scan_service_homes={L: homes[L] for L in [2, 8, 14, 20, 24, 28, 32, 36]},
        scan_home_is_provisional_not_source_service_binding=True,
        PHW_required_by_stage=[(p.phases - 1).bit_length() for p in pools]))
    nbf = sum(p.flavour == 'bf' for p in pools)
    S73.save(out / 'inventory.json', dict(
        stages=stages, bf_stages=nbf, q_stages=stages - nbf, TP=4, layer_dies=4 * stages,
        pairs_bf_stage=pbf, pairs_q_stage=pq, bf_pairs_per_region_bf_stage=nbf_reg, BF_dedicated=dedicated,
        compiled_pairs_TP4=4 * sum(p.np for p in pools), BF_pairs_TP4=4 * sum(len(p.bf) for p in pools),
        q_row_split_limit_bf_stage=qlim, bf16_row_split_limit=blim, macros_per_pair=4, rows=4096, word_bits=274,
        ROM_ECC=False,
        occupied_pairs_per_stage=[sum(v > 0 for v in p.fill.values()) for p in pools],
        used_logical_words_per_stage=[sum(p.fill.values()) for p in pools],
        capacity_words_per_stage=[8192 * p.np for p in pools],
        bf16_words_on_bf_pairs=sum(p.fill[x] for p in pools for x in p.bf),
        physical_admission=False))
    git = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    res = dict(schema='opentallas.dsrom.bf-double.allocation.v1', tool='tools/dsrom_bf_double_alloc.py', source_pin=git,
               decision='OWNER 2026-10-07: BF half-rate + more BF pairs; BF16-dedicated BF pairs (q plans on BF pairs '
                        'would run at half rate); 4 BF a region on BF stages; q-only stages',
               ksplit_bf16_aliases=sorted(FlavourPool.KSPLIT), counts=dict(counts), failures=failures,
               decoder_matrix_capacity_PASS=not failures,
               stages=stages, bf_stages=nbf, q_stages=stages - nbf, layer_dies=4 * stages,
               all_numbers='MODEL_UNVALIDATED until the field phases are measured', adopted=False)
    S73.save(out / 'mapping_verdict.json', res)
    return res


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--pbf', type=int, default=2304); ap.add_argument('--pq', type=int, default=2432)
    ap.add_argument('--nbf-reg', type=int, default=4)
    ap.add_argument('--ksplit', default='', help='BF16 aliases (comma list) whose K split doubles, e.g. gate')
    ap.add_argument('--shared', action='store_true', help='full-rate BF (re-cut A): q plans may use BF pairs; one die flavour')
    a = ap.parse_args()
    FlavourPool.KSPLIT = frozenset(x for x in a.ksplit.split(',') if x)
    a.out.mkdir(parents=True, exist_ok=False)
    print(json.dumps(mapping(a.out, a.pbf, a.pq, a.nbf_reg, not a.shared), indent=1))


if __name__ == '__main__':
    main()
