#!/usr/bin/env python3
"""DIE-QC-97 11-11 ISLAND-VIEW (COORD ruling on POROUS-ALL-1 VIEW MISMATCH: align the plan view to the signed DB).

The signed routed DBs of the two qualified QC island cores, qfd_dv_s8x_vmr (vmrV1, signoff dfecc3725a27) and
qfd_dv_s8_crh_rp1 (rp1_fqc, signoff d31f69ad7728), carry four 12.2a1 island feedthrough pins (ft_ck_i -> ft_ck_o
through one BUFx16f ot_isl_ckft, ft_rst_i -> ft_rst_o through one BUFx4f ot_isl_rstft) that the plan's contract view
lacked.  Every other pin is identical in name, layer and position (MEASURED: signed LEF vs plan pins_file, 1509/998
pins, 0 moved, 0 layer changes, outline 250.56 x 216).

This event binds every plan instance of the two masters to that signed view through the existing ROOT-authorised
physical FT contract (tools/die_plan/core_ft_physical.py, physical/die_plan/qwen_compute/ft_physical_1106/):

    physical_ft          = {proof: <repo-relative ft_physical_1106/<vmr|crh>/proof.json>, proof_sha256,
                            unconsumed_outputs: [ft_ck_o, ft_rst_o]}
    native_port_adapter  = {merge: {}, cycles: 0, tie: {ft_ck_i: 1'b0, ft_rst_i: 1'b0}}

The QC die has no island clock/reset chain (no parent declares an ft_ net; the su8 rst3 neighbour has no ft pins), so
the parent ties the FT inputs to zero and leaves the FT outputs open, the form the ROOT-authorised interface allows.
pins_file stays: CF.load requires the plan pins to be exactly the qualified core pins (the four FT ports are added
from the proof's declaration, not from the plan pin table), and the event checks that the pins_file bytes equal the
proof's captured core_pins and that the proof's captured LEF/signoff are the signed DB.  No RTL, pin, origin, data or
pin cycle changes; every other type and top-level key stays byte-identical and the base serialization is kept.

    python3 -I tools/die_plan/qc_island_view_event.py BASE_PLAN OUT_PLAN EVENT_JSON   (from the repo root)
"""
import hashlib
import json
import sys
from pathlib import Path

FT = "physical/die_plan/qwen_compute/ft_physical_1106"
PLAN_DIR = "physical/die_plan/qwen_compute/plan_of_record"
# master -> (proof dir, signed DB identity: captured signoff.json sha256 prefix, captured LEF sha256 prefix)
CORES = {"qfd_dv_s8x_vmr": ("vmr", "vmrV1", "dfecc3725a27", "6dd379d21ce4"),
         "qfd_dv_s8_crh_rp1": ("crh", "rp1_fqc", "d31f69ad7728", "6c9e07fc3651")}
TAG = "DIE-QC-97 11-11 ISLAND-VIEW"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contract(module, root=Path(".")):
    """-> (physical_ft, native_port_adapter, proof record) for one master, checked against the signed identity"""
    short, view, so_sha, lef_sha = CORES[module]
    rel = f"{FT}/{short}/proof.json"
    proof = json.loads((root / rel).read_text())
    if proof.get("module") != module:
        raise ValueError(f"{rel}: proof is for {proof.get('module')}, not {module}")
    files = proof.get("files") or {}
    if not files.get("signoff", {}).get("sha256", "").startswith(so_sha):
        raise ValueError(f"{rel}: captured signoff is not the signed DB {view} {so_sha}")
    if not files.get("lef", {}).get("sha256", "").startswith(lef_sha):
        raise ValueError(f"{rel}: captured LEF is not the signed DB {view} LEF {lef_sha}")
    decl = json.loads((root / FT / short / files["declaration"]["path"]).read_text())
    ins = sorted(p["name"] for p in decl["ports"] if p["direction"] == "INPUT")
    outs = sorted(p["name"] for p in decl["ports"] if p["direction"] == "OUTPUT")
    if ins != ["ft_ck_i", "ft_rst_i"] or outs != ["ft_ck_o", "ft_rst_o"]:
        raise ValueError(f"{rel}: declared FT ports {ins} {outs} are not the island clock/reset pair")
    pft = {"proof": rel, "proof_sha256": sha(root / rel), "unconsumed_outputs": outs}
    npa = {"merge": {}, "cycles": 0, "tie": {n: "1'b0" for n in ins}}
    return pft, npa, proof


def apply(P, root=Path(".")):
    """-> (new plan, {type: [inst, ...]}); ValueError on a pins_file that is not the captured core pins, or on an
    entry that already carries a different FT contract / port adapter"""
    Q = json.loads(json.dumps(P))
    forms = {m: contract(m, root) for m in CORES}
    changes = {}
    for tn, t in Q["partition_types"].items():
        for c in t.get("hard_cores") or []:
            m = c.get("module")
            if m not in CORES:
                continue
            pft, npa, proof = forms[m]
            pins = root / PLAN_DIR / c["pins_file"]
            if sha(pins) != proof["files"]["core_pins"]["sha256"]:
                raise ValueError(f"{tn}/{c['inst']}: pins_file {c['pins_file']} is not the signed core pins")
            if [float(x) for x in c.get("outline_um") or []] != [float(x) for x in proof["outline_um"]]:
                raise ValueError(f"{tn}/{c['inst']}: outline {c.get('outline_um')} != signed {proof['outline_um']}")
            for k, v in (("physical_ft", pft), ("native_port_adapter", npa)):
                if k in c and c[k] != v:
                    raise ValueError(f"{tn}/{c['inst']}: has a different {k}")
            if c.get("physical_ft") == pft and c.get("native_port_adapter") == npa:
                continue
            short, view, so_sha, lef_sha = CORES[m]
            c["note"] = (c.get("note", "") + f" | {TAG}: signed view {view} (signoff {so_sha}, LEF {lef_sha}) "
                         f"via {FT}/{short}/proof.json; island FT ft_ck_i/ft_rst_i tied 1'b0, ft_ck_o/ft_rst_o open")
            c["physical_ft"] = pft
            c["native_port_adapter"] = npa
            changes.setdefault(tn, []).append(c["inst"])
    return Q, changes


def dumps_like(P, text):
    """re-serialise P in the style the input file used (compact / spaced / indent=1 / indent=2, newline or not)"""
    R = json.loads(text)
    for kw in (dict(separators=(",", ":")), dict(separators=(", ", ": ")), dict(indent=1), dict(indent=2)):
        s = json.dumps(R, **kw)
        if text in (s, s + "\n"):
            return json.dumps(P, **kw) + ("\n" if text.endswith("\n") else "")
    raise ValueError("unknown base plan serialization style")


def diff_keys(P, Q):
    """-> sorted list of changed top-level keys and partition types"""
    out = sorted(k for k in set(P) | set(Q) if k != "partition_types" and P.get(k) != Q.get(k))
    a, b = P["partition_types"], Q["partition_types"]
    return out + sorted(f"partition_types.{t}" for t in set(a) | set(b) if a.get(t) != b.get(t))


def main(argv):
    base, out, ev = argv[1:4]
    text = Path(base).read_text()
    P = json.loads(text)
    Q, changes = apply(P)
    Path(out).write_text(dumps_like(Q, text))
    ch = diff_keys(P, Q)
    if set(ch) != {f"partition_types.{t}" for t in changes}:
        raise SystemExit(f"tree diff {ch} differs from the event's types {sorted(changes)}")
    for t in changes:
        a, b = P["partition_types"][t], Q["partition_types"][t]
        if [k for k in set(a) | set(b) if a.get(k) != b.get(k)] != ["hard_cores"]:
            raise SystemExit(f"{t}: change outside hard_cores")
    record = dict(event=TAG, base=base, base_sha256=sha(base), out=out, out_sha256=sha(out),
                  cores={m: dict(view=v[1], signoff_sha12=v[2], lef_sha12=v[3], proof=f"{FT}/{v[0]}/proof.json",
                                 proof_sha256=sha(Path(FT) / v[0] / "proof.json")) for m, v in CORES.items()},
                  parents=changes, instances=sum(len(v) for v in changes.values()), tree_diff=ch,
                  eq=dict(rtl_change=False, data_cycles=0, pin_cycles=0, pins_moved=0, origins_moved=0,
                          note="FT inputs tied 1'b0 at the physical blackbox (kit_core_clocks.adapt_core_ports), "
                               "FT outputs unconsumed; logical core header and every existing connection unchanged"))
    Path(ev).write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(dict(parents=changes, instances=record["instances"], out_sha256=record["out_sha256"])))


if __name__ == "__main__":
    main(sys.argv)
