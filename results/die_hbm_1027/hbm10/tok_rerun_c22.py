"""DIE-HBM-10: the ONE tok/s rerun (COORD rulings DIE-HBM-10 ASK 2/3 + half-local default (a)): ds S2 (accepted_cost g25
rank0, 4,120 records), cost fn unchanged, plus
  (1) hop chains (12.16b(i)): the 17 links over 2 tree hops (ca/ca_split_h2.json chains) add (chain_lat - direct_lat)
      cycles; ambiguous (-1) latencies count as (hops + 1).  Each chained bus is mapped to the ds unit at its ends
      (plan partitions via c21_part_region.json): SM<->SU (L68/70/76/77/78/98/100/121/123), IDX/DMA<->io (L48/L53),
      SFU(SU)<->io/su (L106/L125), hub row b0xx->SU (L28/L36).  BOUND: every record of a unit pays the unit's worst
      added latency serially (no overlap, no per-bus selection);
  (2) half-local VM (default (a)): far half's 4 of 8 groups (f = 0.5 of the VM input bits) arrive over the xread link,
      LX = 15, Wx = 16 lanes x 256 b = 4096 b/cycle; scope 'sm' (SM matvec inputs; SU reductions pay LX once) and
      'all' (blanket bound); mode opt (streams under the op) / cons (serial in front of it).
ESTIMATE, model UNCHECKED.  usage (repo root): tok_rerun_c22.py CA_SPLIT_H2_JSON OUT_JSON"""
import sys, json, itertools
sys.path[:0] = ['tools', 'tools/throughput']
import accepted_cost as AC
from hgi_sim import timing as T
from hgi_sim import ds_native_timing as DT
caf, outf = sys.argv[1:3]
CH = {c["link"]: c for c in json.load(open(caf))["chains"]}
def lat(v, hops): return v if v is not None and v >= 0 else hops + 1
def add(link):
    c = CH[link]; h = len(c["path"]) - 1
    return max(0, lat(c["chain_lat_cycles"], h) - lat(c["direct_lat"], 1))
UNIT_LINKS = {"SM": ["T002~T007", "T002~T013", "T004~T009", "T004~T016", "T042~T050", "T042~T051", "T047~T052"],
              "SU": ["T002~T007", "T002~T013", "T004~T009", "T004~T016", "T042~T050", "T042~T051", "T047~T052",
                     "T019~T039", "T038~T049", "T043~T044", "T045~T046", "T025~T040", "T026~T041", "T031~T047", "T032~T048"],
              "IDX": ["T011~T019", "T018~T038"], "DMA": ["T011~T019", "T018~T038"]}
assert set(sum(UNIT_LINKS.values(), [])) == set(CH), set(CH) ^ set(sum(UNIT_LINKS.values(), []))
HOP = {u: max(add(l) for l in ls) for u, ls in UNIT_LINKS.items()}
# DATA-PATH form: the 27-b io<->SFU ctl buses (L106 20 b ctl / L125 7 b ctl, T019~T039 / T038~T049 / T043~T044 /
# T045~T046) are config/status (kind ctl), not per-record operands; their added latency is paid once per programme,
# not per record, so per-record SU latency is the worst SU DATA link (L28/L36 hub row -> SU, SU<->SM).
CTL = {"T019~T039", "T038~T049", "T043~T044", "T045~T046"}
HOP_DATA = {u: max(add(l) for l in ls if l not in CTL) for u, ls in UNIT_LINKS.items()}
res = AC.ROOT / 'results/arch/hgi_sim_20261010/g25_proof'
d, recs = DT.load(res / 'ds_rank0_program.json'); recs = T.rebuild_waits(recs)
rg = {}
for x in json.loads((res / 'ds_full.json').read_text())['results']:
    for s_ in x.get('row_gather') or []: rg[x['layer']] = s_
DT.apply_dyn_counts(recs, rg); cf = DT.NativeCost(d['ops'], recs, row_gather=rg)
def vm_in_bits(r, dyn, L):
    b = 0
    for k, ds in r.desc.items():
        if k == "O" or ds is None or ds.space != "VM": continue
        _, n, m, _, _ = T.eff(ds, dyn, L); b += n * m * 4 * 8
    return b
def run(hop=False, scope=None, Lx=15, Wx=4096, mode="opt", f=0.5, H=None):
    def g(r, dyn, L):
        c = cf(r, dyn, L); t = c[0]
        if hop: t += (H or HOP).get(r.unit, 0)
        if scope is not None:
            red = r.unit == "SU" and getattr(r, "sut", None) and r.sut.get("red")
            if scope == "sm" and r.unit != "SM":
                t += Lx if red else 0
            else:
                fb = f * vm_in_bits(r, dyn, L)
                if fb > 0:
                    t = t + Lx + fb / Wx if mode == "cons" else max(t, fb / Wx) + Lx
        return (t, c[1], c[2])
    return T.schedule(recs, DT.POS, 'S2', cost_fn=g)['total_cycles']
base = run()
out = dict(basis=__doc__.split("\n")[0], hop_added_cycles_per_unit=HOP, hop_added_cycles_per_unit_data_path=HOP_DATA,
           hop_links={l: dict(add=add(l), path_hops=len(c["path"]) - 1, bits=c["bits"]) for l, c in CH.items()},
           base_cycles=base, rows=[])
rows = [("hop data-path only", "data", None, "opt"), ("hop data-path + far sm opt (ESTIMATE OF RECORD)", "data", "sm", "opt"),
        ("hop data-path + far sm cons", "data", "sm", "cons"), ("hop only", True, None, "opt"), ("far sm opt", False, "sm", "opt"), ("far sm cons", False, "sm", "cons"),
        ("hop + far sm opt", True, "sm", "opt"), ("hop + far sm cons", True, "sm", "cons"),
        ("hop + far all opt (bound)", True, "all", "opt"), ("hop + far all cons (bound)", True, "all", "cons")]
for name, hop, scope, mode in rows:
    t = run(bool(hop), scope, 15, 4096, mode, H=HOP_DATA if hop == "data" else None)
    r = dict(case=name, cycles=t, cost_pct=round(100 * (t / base - 1), 2), tok_s_from_1906=round(1906 / (t / base), 1))
    out["rows"].append(r); print(r, flush=True)
json.dump(out, open(outf, "w"), indent=1)
