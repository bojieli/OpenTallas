#!/usr/bin/env python3
"""HBM-BIND-7 (HBM-035): exact parent cut of the actual hub collectives hb_coll_NE (ot_hfd_coll_q2_hard_v8g_s, NLINK 2,
VM_RT 3) and hb_coll_NW (ot_hfd_coll_q3_hard_v8x, NLINK 3, VM_RT 3) into the plan hard-core parts (opt-in compose input).

Input: the flat netlist of the spliced die (splice_coll.py: parents + u_body dissolved, coll engines as leaves), with
the two parents' interfaces retained (mkflat_coll.py).  Parts follow the plan split (physical/die_plan/hbm/cores/harden/
build_split_tops.py coll_q2_* / coll_q3_*), on the ACTUAL source members:
  reduce   u_body.u_reduce                                          -> u_hb_coll_Q_reduce__<keep>
  ring_ag  u_body.u_ring                                            -> u_hb_coll_Q_ring_ag__<keep>
  vm       u_body.u_vmasm + u_body.u_writer                         -> u_hb_coll_Q_vm__<keep>
  edge     NW only: u_body.g_link[0..2].u_link + u_body.g_q3.t192.u_arg -> u_hb_coll_Q_edge__<keep>
  body     every other cell of the parent (issuer, control, fj, qslots capture/out, upipe, NE links, parent glue)
           -> u_hb_coll_Q_body_n2__<keep> (NE) / u_hb_coll_Q_body_core__<keep> (NW)
The parts are an exact partition of the parent's flat cells (checked).  Members are unchanged cells; ports = the
boundary nets (a net with a terminal outside the member set or on a top port); tools/die_plan/bind_compose.py proves
terminal equality.  Port names: the die clock net -> clk, the parent reset net -> rst_n (the plan wavefront core reset
pin), a net on a parent port -> that port name and bit, else <member rel path>_<port> (sanitized, bit = terminal bit);
non-contiguous bit sets are split into contiguous ports.  No logic, cycle or constant changes.
Module names: the plan module; a part whose actual structure differs between the hubs while the plan uses one module
(reduce: NE = ot_hgi_coll_reduce_static_pr = the kit, NW = ot_hgi_coll_reduce_static) gets the suffix __nw_actual on
the hub that differs from the kit source.
usage: coll_parent_cutmap.py FLAT.pkl BASE_COMPOSE.json MAP.json OUT_COMPOSE.json OUT_MAP.json [--keep q0]"""
import argparse, collections, json, pickle, re, sys
from pathlib import Path

HUBS = {"hb_coll_NE": dict(part="NE_hub", body="u_hb_coll_Q_body_n2", mod=dict(
            reduce="ot_hfd_coll_q2_hard_v8g__reduce", ring_ag="ot_hfd_coll_q2_hard_v8g__ring_ag",
            vm="ot_hfd_coll_q2n2_vm_core", body="ot_hfd_coll_q2n2_body_core")),
        "hb_coll_NW": dict(part="NW_hub", body="u_hb_coll_Q_body_core", mod=dict(
            reduce="ot_hfd_coll_q2_hard_v8g__reduce", ring_ag="ot_hfd_coll_q2_hard_v8g__ring_ag",
            vm="ot_hfd_coll_q3_vm_core", edge="ot_hfd_coll_q3_edge_core", body="ot_hfd_coll_q3_body_core"))}
ROLES = dict(reduce=["u_body.u_reduce"], ring_ag=["u_body.u_ring"], vm=["u_body.u_vmasm", "u_body.u_writer"],
             edge=["u_body.g_link[0].u_link", "u_body.g_link[1].u_link", "u_body.g_link[2].u_link", "u_body.g_q3.t192.u_arg"])
# Per-hub identity constants exposed as input strap ports (bind_compose constant straps; declared as manifest straps):
# the ring's quarter id is tied at the parent (NE 2'b11, NW 2'b10); the plan ring_ag kit carries it as strap_qid[1:0].
STRAPS = {"ring_ag": [("u_body.u_ring", "qid", "strap_qid")]}
# Port-name prefixes follow the plan kit pin conventions (names only; bind matches by bit, not by name).
PREFIX = {"reduce": [("u_body.", "")], "ring_ag": [("u_body.", "")],
          "vm": [("u_body.u_vmasm", "vmasm"), ("u_body.u_writer", "writer")],
          "edge": [("u_body.g_link[0].u_link", "link0"), ("u_body.g_link[1].u_link", "link1"),
                   ("u_body.g_link[2].u_link", "link2"), ("u_body.g_q3.t192.u_arg", "arg")], "body": []}
RST_NAME = {"vm": "writer_rst_n", "edge": "arg_rst_n"}   # kit names; wavefront reset pins (reduce/ring_ag/body) stay rst_n
KIT_SOURCE = {"reduce": "hb_coll_NE"}     # the plan kit of a module shared by both hubs was cut from this hub's source


def sanitize(s):
    s = re.sub(r"[^A-Za-z0-9_]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s if re.match(r"[A-Za-z_]", s) else "p_" + s


def members_of(F, hub):
    cells = [c for c in F.cells if c.path.startswith(hub + ".")]
    byrel = {c.path[len(hub) + 1:]: c for c in cells}
    out = {}
    for role, rels in ROLES.items():
        if role == "edge" and hub != "hb_coll_NW":
            continue
        for r in rels:
            if r not in byrel or byrel[r].kind != "leaf":
                raise SystemExit(f"{hub}.{r}: missing leaf for role {role}")
        out[role] = [hub + "." + r for r in rels]
    used = {p for v in out.values() for p in v}
    out["body"] = sorted(c.path for c in cells if c.path not in used)
    allm = [p for v in out.values() for p in v]
    if sorted(allm) != sorted(c.path for c in cells) or len(set(allm)) != len(allm):
        raise SystemExit(f"{hub}: parts are not an exact partition of the parent cells")
    return out, {c.path: c for c in cells}


def cut(F, hub, role, members, byp, net_cells, topnets, pport, clk_net, rst_net):
    ms = set(members)
    net_terms = collections.defaultdict(list)
    for p in members:
        c = byp[p]
        for pn, bs in c.ports.items():
            for i, b in enumerate(bs):
                if isinstance(b, int):
                    net_terms[b].append((c.path, pn, i, c.dirs[pn], c.kind))
    boundary = [b for b in net_terms if (net_cells[b] - ms) or b in topnets]

    def key(t):
        return (t[4] != "leaf", t[3] != "output", t[0], t[1], t[2])
    lab = {}
    for b in boundary:
        if b == clk_net:
            lab[b] = ("clk", 0)
        elif b == rst_net:
            lab[b] = (RST_NAME.get(role, "rst_n"), 0)
        elif b in pport:
            lab[b] = sorted(pport[b])[0]
        else:
            t = sorted(net_terms[b], key=key)[0]
            rel = t[0][len(hub) + 1:]
            for a, z in PREFIX[role]:
                if rel.startswith(a):
                    rel = z + rel[len(a):]
                    break
            lab[b] = (sanitize(rel) + "_" + sanitize(t[1]), t[2])
    for b in boundary:
        if b != clk_net and b in [x for x in boundary if lab[x][0] == "clk" and x != clk_net]:
            raise SystemExit("clock label clash")
    groups = collections.defaultdict(dict)
    for b, (n, i) in lab.items():
        if i in groups[n]:
            raise SystemExit(f"{hub} {role}: duplicate label {n}[{i}]")
        groups[n][i] = b
    ports, labels = {}, {}
    for n, d in sorted(groups.items()):
        idx = sorted(d)
        runs, cur = [], [idx[0]]
        for i in idx[1:]:
            if i == cur[-1] + 1:
                cur.append(i)
            else:
                runs.append(cur); cur = [i]
        runs.append(cur)
        for r in runs:
            pn = n if len(runs) == 1 else f"{n}__b{r[0]}"
            if pn in ports:
                raise SystemExit(f"{hub} {role}: port name clash {pn}")
            bits, dirs = [], set()
            for i in r:
                b = d[i]
                dd = "output" if any(t[3] == "output" for t in net_terms[b]) else "input"
                dirs.add(dd)
                bits.append([dict(member=t[0], port=t[1], bit=t[2]) for t in net_terms[b] if t[3] == dd])
            if len(dirs) != 1:
                raise SystemExit(f"{hub} {role}: mixed directions on {pn}")
            ports[pn] = dict(dir=dirs.pop(), bits=bits, lo=r[0])
            labels[pn] = [d[i] for i in r]
    for rel, pn, name in STRAPS.get(role, []):
        c = byp[hub + "." + rel]
        bs = c.ports[pn]
        if not all(isinstance(b, str) and b in ("0", "1") for b in bs) or c.dirs[pn] != "input" or name in ports:
            raise SystemExit(f"{hub} {role}: strap {rel}.{pn} is not a tied input")
        ports[name] = dict(dir="input", bits=[[dict(member=c.path, port=pn, bit=i)] for i in range(len(bs))], lo=0)
        labels[name] = list(bs)
    if "rst_n" not in ports and role in ("reduce", "ring_ag", "body"):
        raise SystemExit(f"{hub} {role}: no rst_n boundary net (plan wavefront reset target)")
    return ports, labels, boundary


def signature(F, hub, members, byp, ports):
    strap = {(r, pn) for v in STRAPS.values() for r, pn, _ in v}
    consts = sorted((p[len(hub) + 1:], pn, i, b) for p in members for pn, bs in byp[p].ports.items()
                    for i, b in enumerate(bs) if isinstance(b, str) and (p[len(hub) + 1:], pn) not in strap)
    return json.dumps([consts, sorted((p[len(hub) + 1:], byp[p].module, sorted(getattr(byp[p], "params", {}).items()))
                              for p in members),
                       sorted((n, v["dir"], v["lo"], len(v["bits"])) for n, v in ports.items())], sort_keys=True, default=str)


def run(flat, base, mapf, out, outmap, keep="q0"):
    F = pickle.load(open(flat, "rb"))
    spec = json.loads(Path(base).read_text())
    M = json.loads(Path(mapf).read_text())
    used = {m for c in spec["cores"] for m in c["members"]}
    topnets = {b for _, bs in F.top_ports.values() for b in bs if isinstance(b, int)}
    net_cells = collections.defaultdict(set)
    for c in F.cells:
        for bs in c.ports.values():
            for b in bs:
                if isinstance(b, int):
                    net_cells[b].add(c.path)
    cores, report, sigs = [], [], {}
    for hub, H in HUBS.items():
        inst = F.instances[hub]
        pport = collections.defaultdict(list)
        iports = {pn: v["bits"] for pn, v in inst["ports"].items()}
        for pn, bs in iports.items():
            for i, b in enumerate(bs):
                if isinstance(b, int):
                    pport[b].append((pn, i))
        clks = {b for pn, bs in iports.items() if pn.startswith("clk") for b in bs if isinstance(b, int)}
        rsts = {b for b in iports.get("rst_n", []) if isinstance(b, int)}
        if len(clks) != 1 or len(rsts) != 1:
            raise SystemExit(f"{hub}: expected one clock net and one reset net, got {len(clks)} / {len(rsts)}")
        clk_net, rst_net = clks.pop(), rsts.pop()
        parts, byp = members_of(F, hub)
        if used & set(byp):
            raise SystemExit(f"{hub}: cells already members of a base core")
        for role, mem in parts.items():
            ports, labels, boundary = cut(F, hub, role, mem, byp, net_cells, topnets, pport, clk_net, rst_net)
            local = (H["body"] if role == "body" else f"u_hb_coll_Q_{role}") + f"__{keep}"
            ci = f"{hub}.__cut_{role}"
            if ci in M["parts"]:
                raise SystemExit(f"{ci} already mapped")
            M["parts"][ci] = [H["part"], local]
            sg = signature(F, hub, mem, byp, ports)
            core = dict(inst=ci, module=H["mod"][role], members=mem, ports={n: {k: v for k, v in p.items()} for n, p in ports.items()})
            sigs.setdefault(H["mod"][role], {})[hub] = (sg, core)
            cores.append(core)
            report.append(dict(inst=ci, plan_local=local, partition=H["part"], members=len(mem),
                               leaves=sorted(p[len(hub) + 1:] + " : " + byp[p].module for p in mem if byp[p].kind == "leaf"),
                               glue=dict(collections.Counter(byp[p].module for p in mem if byp[p].kind != "leaf")),
                               boundary_nets=len(boundary), pins=sum(len(v["bits"]) for v in ports.values()),
                               ports={n: [v["dir"], v["lo"], len(v["bits"])] for n, v in sorted(ports.items())}))
    variants = {}
    for mod, d in sigs.items():
        if len(d) == 2 and d["hb_coll_NE"][0] != d["hb_coll_NW"][0]:
            role = next(r for r, m in HUBS["hb_coll_NE"]["mod"].items() if m == mod)
            other = "hb_coll_NW" if KIT_SOURCE.get(role) == "hb_coll_NE" else "hb_coll_NE"
            d[other][1]["module"] = mod + "__" + other[-2:].lower() + "_actual"
            variants[mod] = dict(kit_source=KIT_SOURCE.get(role), variant=d[other][1]["module"], on=other)
    for r in report:
        r["module"] = next(c["module"] for c in cores if c["inst"] == r["inst"])
    spec["cores"] = spec["cores"] + cores
    Path(out).write_text(json.dumps(spec))
    Path(outmap).write_text(json.dumps(M))
    rep = dict(schema="hbm.bind7.coll_parent_cutmap.v1", keep=keep, cores=report, structure_variants=variants)
    Path(out).with_suffix(".coll_report.json").write_text(json.dumps(rep, indent=1))
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    for x in ("flat", "base", "map", "out", "outmap"):
        ap.add_argument(x)
    ap.add_argument("--keep", default="q0", choices=("q0", "q1"))
    ap.add_argument("--tools", default=str(Path(__file__).resolve().parents[2] / "tools" / "die_plan"))
    a = ap.parse_args(argv)
    sys.path.insert(0, a.tools)
    rep = run(a.flat, a.base, a.map, a.out, a.outmap, a.keep)
    for r in rep["cores"]:
        print(r["inst"], r["module"], r["plan_local"], "members", r["members"], "glue", r["glue"], "pins", r["pins"], "ports", len(r["ports"]))
    print("variants", rep["structure_variants"])


if __name__ == "__main__":
    main()
