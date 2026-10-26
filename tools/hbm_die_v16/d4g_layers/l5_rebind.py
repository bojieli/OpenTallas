#!/usr/bin/env python3
"""H-D4G5/REBIND 10-18 (coordinator HANDOFF 0gd): GEN1 contract post-layer L5 -- netlist-only rebinds of closed / submitted
OWNERS-HBM successors whose RTL is on this branch.  No slot / geometry change here (those are SET 2, GEN2:
results/arch/hbm_die_d4g/gen2_rebind/slot_changes.json).

    l5_rebind.py IN_contract.json[.gz] OUT_contract.json --report R.json

Runs LAST in run_layers.py (after l4_idx_quad).  Every rebind is port-identical (the master's RTL port list equals the
instance's contract ports) or a pure renaming of the same bits; no edge gains or loses a bit, no input is tied:
  (a) hb_quant_NW  ot_hgi_qdq_host_static -> ot_hgi_qdq_host_split (OWNERS-HBM/QDQ claude/qdq-split-1018 1b0a71d6e: soft
      parent over the CLOSED tsplit ctl/rslice/wslice + LG + qw decoders; fleet lockstep m0 PASS, m1/m2 FAIL witnessed;
      the monolith is BLOCKED -- one CTS root cannot carry its SRAM).  Same ports and RL/WC/COMPACT.  Compiler: NW VM
      programme Quant read slot +1, write slot +5 (tools/hgi_static_quant_calendar.py).
  (b) fs_<q> (x4, N 8 SYNC_MASK 0)  ot_hbm_fault_leaf -> ot_hbm_fault_leaf_n8_s0 (SVC-SMALL claude/svc-small-1018: the thin
      per-parameter wrapper, submitted hdie_fault_leaf_w_n8_s0-hflw-n8s0-3e59abf7b).  fr_<q> / fcx_<q> are NOT rebound:
      the d4g layers widened them (fr_SE N9/0x30, fr_SW N11/0x120, fr_NW N9/0x50, fr_NE N10/0x50, fcx N6/0x3f), so the
      GEN0-parameter wrappers _n8_s40 / _n9_s40 / _n11_s100 do not match (SET 2: new wrappers owed by SVC-SMALL).
  (c) vmks_* (x16)  ot_hbm_svc_vm_kshare -> ot_hbm_svc_vm_kshare_splitstrap #(MUT 0, KRL1 1) (SVC-SMALL c9d7cd861: one SM
      identity strap per clock domain, KRL1 explicit-flop response ring); the identity strap sm[2:0] becomes sm_stream and
      sm_hbm with the same value.  Its pin-sized slot 432 x 388.8 is SET 2.
  (d) hb_vms_SW / hb_vms_NW  hfd_hgi_vms_static_{SW,NW}_glue -> hfd_hgi_vms_glue_{sw,nw}_t (VM-GLUE claude/vm-glue-1018
      6e62dbac4, tile-top equivalence PASS + mutants FAIL): clk_hub / clk_ring[1:0] / clk_replay -> one clk (same stream
      clock), bk_X[b*W +: W] -> b<b>_X, bank_status[18b +: 18] -> b<b>_status, bk_flt[b] -> b<b>_flt.  hb_vms_SE / _NE stay
      the NC 0 glue: the VM-GLUE E master hfd_hgi_vms_glue_e_t is the NC 1 {SE,NE}b glue (cq 338 / cr 274), which l4
      reverted (no IDX hub client) -> an NC 0 E tile is owed (SET 2).
  (e) su_prog  ot_hbm_su_programme_root_h -> ot_hbm_su_programme_root_h5 and pgp_<q>  ot_hbm_su_programme_pslice_q4 ->
      ot_hbm_su_programme_pslice_c5 (HBM-RTL5/pg pg_r5_binding.json; bench2 SU_PROGRAMME_ROOT5_GATE PASS + 6 mutants
      rejected, ot-epyc5 10-18 04:29).  Port-identical.  Compiler: start advance DEPTH + 6, outputs +2 edges, config image
      su_programme_compile.py --root5, reset wait >= 3 edges.
"""
import argparse, collections, json, sys
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import l3_vm_hc_coll as L3M  # noqa: E402

REGION = 'd4g_gen1_l5'
L3M.REGION = REGION
Q4 = ('SW', 'SE', 'NW', 'NE')
VMS_TILE = dict(SW='hfd_hgi_vms_glue_sw_t', NW='hfd_hgi_vms_glue_nw_t')
VMS_CLK = ('clk_hub', 'clk_ring', 'clk_replay')
# glue flat bus -> per-bank tile port suffix
VMS_BUS = dict(bk_xq='xq', bk_xq2='xq2', bk_xq_done='xq_done', bk_xq2_done='xq2_done', bk_eg='eg', bk_pq='pq', bk_pr='pr',
               bank_status='status', bk_flt='flt')


class L5(L3M.L3):
    def edge(self, src, snk, basis, clock='stream'):
        super().edge(src, snk, basis, clock)
        self.E[-1]['name'] = f'l5_{self.n:05d}'

    def same_ports(self, name, master, params):
        old = {p: (d['direction'], d['bits']) for p, d in self.I[name]['ports'].items()}
        new = {p: (d['direction'], d['bits']) for p, d in self.R.ports(master, params).items()}
        diff = {p: (old.get(p), new.get(p)) for p in set(old) | set(new) if old.get(p) != new.get(p)}
        return diff

    def rebind(self, name, master, params, note, allow=()):
        diff = self.same_ports(name, master, params)
        bad = {p: v for p, v in diff.items() if p not in allow}
        if bad:
            raise SystemExit(f'L5 {name} -> {master}: ports differ {bad}')
        self.remaster(name, master, params, note)

    def split_bus(self, inst, port, newport_of, width):
        """re-target every edge end on inst.port (flat bus, `width` bits per bank) to the per-bank port newport_of(b)"""
        out = []
        for e in self.E:
            side = 'sink' if e['sink'][:2] == [inst, port] else 'source' if e['source'][:2] == [inst, port] else None
            if not side:
                out.append(e); continue
            other = 'source' if side == 'sink' else 'sink'
            lo, hi = e[side][2], e[side][3]
            ol = e[other]
            b = lo // width
            pieces = []
            while lo < hi:
                b = lo // width
                y = min(hi, (b + 1) * width)
                pieces.append((lo, y, b))
                lo = y
            for k, (x, y, b) in enumerate(pieces):
                ne = json.loads(json.dumps(e))
                ne[side] = [inst, newport_of(b), x - b * width, y - b * width]
                ne[other] = [ol[0], ol[1], ol[2] + x - e[side][2], ol[2] + y - e[side][2]]
                ne['bits'] = y - x
                if len(pieces) > 1:
                    ne['name'] = f"{e['name']}__b{b}"
                ne['basis'] = (ne.get('basis') or '') + f' | {REGION}: {port} -> {newport_of(b)}'
                out.append(ne)
            self.log['bus_edges_split'] += 1
        self.E[:] = out


def run(c, rep):
    R = L3M.Rtl()
    l5 = L5(c, R)
    I = l5.I
    done = collections.OrderedDict()
    # (a) QDQ split
    i = I['hb_quant_NW']
    assert i['master'] == 'ot_hgi_qdq_host_static', i['master']
    l5.rebind('hb_quant_NW', 'ot_hgi_qdq_host_split', i['params'],
              'OWNERS-HBM/QDQ soft parent over the closed split leaves (claude/qdq-split-1018 1b0a71d6e); port-identical; '
              'NW VM programme rq +1 / wq,beat_done,record_done +5 edges')
    done['hb_quant_NW'] = 'ot_hgi_qdq_host_split'
    # (b) fs_<q> fault leaves N8/0x0
    for q in Q4:
        n = f'fs_{q}'
        p = I[n]['params']
        assert I[n]['master'] == 'ot_hbm_fault_leaf' and p.get('N') == 8 and p.get('SYNC_MASK') == "64'h0", (n, I[n]['master'], p)
        l5.rebind(n, 'ot_hbm_fault_leaf_n8_s0', {}, 'SVC-SMALL thin wrapper of ot_hbm_fault_leaf N 8 SYNC_MASK 0 (job hdie_fault_leaf_w_n8_s0)')
        done[n] = 'ot_hbm_fault_leaf_n8_s0'
    skipped = {n: dict(master=I[n]['master'], params=I[n]['params']) for n in sorted(I)
               if I[n]['master'] == 'ot_hbm_fault_leaf' and not n.startswith('fl_')}
    # (c) vm_kshare splitstrap
    ks = sorted(n for n in I if I[n]['master'] == 'ot_hbm_svc_vm_kshare')
    assert len(ks) == 16, ks
    for n in ks:
        prm = dict(I[n]['params'])
        assert prm == {'MUT': 0, 'KRL1': 1}, (n, prm)
        st = [s for s in l5.ST if s['inst'] == n and s['port'] == 'sm']
        assert len(st) == 1 and (st[0]['lo'], st[0]['hi']) == (0, 3), (n, st)
        l5.rebind(n, 'ot_hbm_svc_vm_kshare_splitstrap', prm,
                  'SVC-SMALL splitstrap (KRL1 explicit-flop ring; sm identity strap per clock domain)', allow=('sm', 'sm_stream', 'sm_hbm'))
        v = st[0]['value']
        l5.ST.remove(st[0])
        for port, dom in (('sm_stream', 'stream'), ('sm_hbm', 'hbm')):
            l5.strap(n, port, v, f'identity: SM of this instance ({dom}-domain copy of the former sm strap)')
        done[n] = 'ot_hbm_svc_vm_kshare_splitstrap'
    # (d) VM hub glue tiles SW / NW
    for q, tile in VMS_TILE.items():
        n = f'hb_vms_{q}'
        old = {p: d['bits'] for p, d in I[n]['ports'].items()}
        new = R.ports(tile, {})
        cks = [x for x in l5.CR if x['instance'] == n and x['port'] in VMS_CLK]
        assert len(cks) == 3 and len({tuple(x['source']) for x in cks}) == 1, cks
        assert not any(e['sink'][:2] == [n, p] for e in l5.E for p in VMS_CLK)
        for bus, suf in VMS_BUS.items():
            if bus not in old:
                continue
            w = old[bus] // 8
            assert w * 8 == old[bus] and new[f'b0_{suf}']['bits'] == w, (n, bus, old[bus], new.get(f'b0_{suf}'))
            l5.split_bus(n, bus, lambda b, suf=suf: f'b{b}_{suf}', w)
        keep = {p for p in old if p not in VMS_BUS and p not in VMS_CLK}
        for p in keep:
            assert new[p]['bits'] == old[p], (n, p, old[p], new[p])
        extra = set(new) - keep - {f'b{b}_{VMS_BUS[k]}' for k in VMS_BUS if k in old for b in range(8)} - {'clk'}
        assert not extra, (n, extra)
        l5.CR[:] = [x for x in l5.CR if not (x['instance'] == n and x['port'] in VMS_CLK)]
        l5.remaster(n, tile, {}, 'VM-GLUE hardened tile top (claude/vm-glue-1018 6e62dbac4): one clk, per-bank ports')
        l5.clock(n, 'clk', src=cks[0]['source'])
        done[n] = tile
    # (e) SU programme r5
    l5.rebind('su_prog', 'ot_hbm_su_programme_root_h5', {}, 'HBM-RTL5/pg root_h5 (SMACROS 4x320, SDLY 2, RRLY 1); bench2 PASS')
    done['su_prog'] = 'ot_hbm_su_programme_root_h5'
    for q in Q4:
        n = f'pgp_{q}'
        assert I[n]['master'] == 'ot_hbm_su_programme_pslice_q4', I[n]['master']
        l5.rebind(n, 'ot_hbm_su_programme_pslice_c5', {}, 'HBM-RTL5/pg per-column cluster (pghead r5 + pgcol_s r5 CLOSED, pgcol_l r5 SYNTH)')
        done[n] = 'ot_hbm_su_programme_pslice_c5'
    ex, bad = l5.finish()
    c['masters'] = dict(sorted(collections.Counter(v['master'] for v in I.values()).items()))
    rep.update(log=dict(l5.log), rebound=done, fault_leaves_not_rebound=skipped, exposed_inputs=ex, unlisted_exposed=bad,
               summary=c['summary'])
    return ex, bad, l5


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--report', required=True)
    a = ap.parse_args()
    c = L3M.ld(a.inp)
    rep = dict(schema='opentallas.hbm.d4g.gen1_l5_rebind.v1', region=REGION, inp=str(a.inp))
    notes = c.get('notes'); c['notes'] = {}
    ex, bad, l5 = run(c, rep)
    nl = c['notes']
    c['notes'] = notes + [dict(region=k, note=v) for k, v in nl.items()] if isinstance(notes, list) else dict(notes or {}, **nl)
    json.dump(c, open(a.out, 'w'), indent=None)
    Path(a.report).write_text(json.dumps(rep, indent=1, default=str))
    print('L5', json.dumps(dict(l5.log)), 'exposed', len(ex), 'bits', sum(x[2] for x in ex), 'unlisted', len(bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
