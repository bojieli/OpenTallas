#!/usr/bin/env python3
"""Measured power of the Qwen3-8B HBM accelerator's W12 tile element at the P8191 decode activity.

Chain (every step on a compute host; nothing here models activity):
  1. the TP4 HA8 vehicle (tools/qwen_hbmacc_rt_token_w12.py, the routed tile's parameters) runs one decode
     stage at P8191 with RT_TILE_TRACE: per fabric clock edge, die 0's listed tiles' input ports (pre-edge)
     and output ports (post-edge) -> tileNNNN.rec;
  2. `activity`: rtl/test/qwen_rom_runtime/qwen_tile_replay.cpp replays a record file on the Verilated tile
     (exit 3 on any output mismatch; a negative control flips one input bit and must mismatch), dumps the
     VCD through a FIFO into tools/signoff/vcd2saif (whole stage + fixed record windows), and maps the
     register toggles onto the routed flops (tools/signoff_analysis.map_rtl_saif_to_netlist: RTL-name
     matching, the documented method of docs/POWER_CLOCK_SIGNOFF.md);
  3. `power`: one OpenROAD session per corner on the routed tile (6_final.odb + 6_final.spef + 6_final.sdc,
     the corner's RVT liberty) reads each pin SAIF and emits OpenSTA's design power by group
     (sequential / combinational / clock x internal / switching / leakage);
  4. `compose` (run locally on the committed JSONs) builds the die power.

The replay covers clocked cycles only (the die's ME_IDLE_GATE holds the fabric clock while the engine idles),
so each SAIF is the tile's power WHILE CLOCKED, at the 0.833 ns period.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import signoff_analysis as SA  # noqa: E402

TOP = "ot_qwen_rom_tile_logic_w12"
VCD_SCOPE = f"TOP.{TOP}"


def replay(binary: Path, rec: Path, *plus: str) -> tuple[int, str]:
    p = subprocess.run([str(binary), str(rec), *plus], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def one_saif(binary: Path, vcd2saif: Path, rec: Path, out: Path, begin: int | None, end: int | None) -> dict:
    fifo = out.with_suffix(".fifo")
    if fifo.exists():
        fifo.unlink()
    os.mkfifo(fifo)
    conv = subprocess.Popen([str(vcd2saif), str(fifo), str(out), VCD_SCOPE, "auto"], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    plus = [f"+VCD={fifo}"] + ([f"+BEGIN={begin}"] if begin is not None else []) + ([f"+END={end}"] if end is not None else [])
    rc, text = replay(binary, rec, *plus)
    ctext = conv.communicate()[0]
    fifo.unlink()
    m = re.search(r"TILE_REPLAY .*", text)
    return {"rc": rc, "replay": m.group(0) if m else text[-400:], "vcd2saif_rc": conv.returncode, "vcd2saif": ctext[-300:]}


def map_one(args: tuple[str, str, str]) -> dict:
    rtl, netlist, out = args
    st = SA.map_rtl_saif_to_netlist(Path(rtl), Path(netlist), Path(out), top=TOP)
    return {"pin_saif": out, **{k: st[k] for k in ("rtl_records", "flops", "flops_matched", "ports", "ports_matched",
                                                   "flop_match_fraction", "unmatched_examples")}}


def cmd_activity(a) -> None:
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    rec = a.rec
    # exactness of the replay, its access counts, and the negative control
    rc, text = replay(a.replay, rec, f"+STATS={out / 'ports.txt'}")
    exact = re.search(r"records=(\d+) first_cyc=(\d+) last_cyc=(\d+) traced=\d+ mismatches=(\d+)", text)
    if rc != 0 or not exact or int(exact.group(4)) != 0:
        raise SystemExit(f"replay not exact (rc {rc}): {text[-600:]}")
    n = int(exact.group(1))
    rcn, textn = replay(a.replay, rec, f"+FLIP={min(n - 1, a.flip_at)}")
    neg = re.search(r"mismatches=(\d+)", textn)
    neg_ok = rcn == 3 and neg and int(neg.group(1)) > 0
    # ROM bank reads (rom_ce one-hot), KV reads, per record
    reads = {"rom_bank_reads": 0, "rom_reads_by_bank": {}, "kv_reads": 0}
    per_rec = []
    for line in (out / "ports.txt").read_text().splitlines()[1:]:
        r, cyc, ce, addr, kv = map(int, line.split())
        if ce:
            b = ce.bit_length() - 1
            reads["rom_bank_reads"] += 1
            reads["rom_reads_by_bank"][b] = reads["rom_reads_by_bank"].get(b, 0) + 1
        reads["kv_reads"] += kv
        per_rec.append((ce != 0, kv))
    windows = [("full", None, None)]
    w = a.window
    for k in range(0, n, w):
        if k + w <= n:
            windows.append((f"w{k:06d}", k, k + w))
    win_reads = {}
    for name, b, e in windows[1:]:
        win_reads[name] = {"rom": sum(c for c, _ in per_rec[b:e]), "kv": sum(k for _, k in per_rec[b:e])}
    saifs = {}
    for name, b, e in windows:
        rtl = out / f"rtl_{name}.saif"
        r = one_saif(a.replay, a.vcd2saif, rec, rtl, b, e)
        if r["rc"] != 0 or r["vcd2saif_rc"] != 0:
            raise SystemExit(f"{name}: {r}")
        saifs[name] = {"begin": b, "end": e, "rtl_saif": str(rtl), **r}
    jobs = [(saifs[nm]["rtl_saif"], str(a.netlist), str(out / f"pin_{nm}.saif")) for nm, *_ in windows]
    with ProcessPoolExecutor(a.procs) as ex:
        for (nm, *_), st in zip(windows, ex.map(map_one, jobs)):
            saifs[nm]["map"] = st
            Path(saifs[nm]["rtl_saif"]).unlink()
    res = {"rec": str(rec), "records": n, "first_cyc": int(exact.group(2)), "last_cyc": int(exact.group(3)),
           "replay_exact": True, "replay_mismatches": 0,
           "negative_control": {"flip_record": min(n - 1, a.flip_at), "rc": rcn, "detected": bool(neg_ok),
                                "line": (re.search(r"TILE_REPLAY .*", textn) or [textn[-200:]])[0]},
           "window_records": w, "reads": reads, "window_reads": win_reads, "saifs": saifs}
    (out / "activity.json").write_text(json.dumps(res, indent=1) + "\n")
    if not neg_ok:
        raise SystemExit("negative control NOT detected")
    print("activity", rec, n, "records", len(saifs), "saifs")


TCL_HEAD = r"""
proc emit {key value} { puts "SIGNOFF $key=$value" }
read_db $::so_odb
foreach lib $::so_libs { read_liberty $lib }
read_sdc $::so_sdc
read_spef $::so_spef
set_cmd_units -time ns -power W
proc dp {label} {
    set dp [sta::design_power [sta::cmd_scene]]
    set k 0
    foreach grp {total sequential combinational clock macro pad} {
        foreach part {internal switching leakage total} {
            emit $label.$grp.${part}_w [lindex $dp $k]
            incr k
        }
    }
}
emit corner.name $::so_corner
dp vectorless
"""


def cmd_power(a) -> None:
    res = SA.find_results_dir(a.results)
    saifs = [Path(s).resolve() for s in a.saif]
    labels = a.label or [s.parent.name + "/" + s.stem for s in saifs]
    lines = [f"set ::so_libs {SA.tcl_list(SA.corner_libs(a.corner))}",
             f"set ::so_odb /so_res/6_final.odb", f"set ::so_sdc /so_res/6_final.sdc",
             f"set ::so_spef /so_res/6_final.spef", f"set ::so_corner {a.corner}", TCL_HEAD]
    mounts = {str(res): "/so_res"}
    for i, (s, lab) in enumerate(zip(saifs, labels)):
        mounts[str(s.parent)] = mounts.get(str(s.parent), f"/so_saif{i}")
        lines.append(f"read_saif -scope {TOP} {mounts[str(s.parent)]}/{s.name}")
        if i == 0:
            lines.append("report_activity_annotation")
        lines.append(f"dp {{{lab}}}")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    text = SA.run_session("\n".join(lines) + "\n", mounts, a.out.with_suffix(".log"))
    vals = {}
    for m in re.finditer(r"^SIGNOFF (\S+?)=(\S+)$", text, re.M):
        vals[m.group(1)] = SA._num(m.group(2))
    ann = re.findall(r"^.*(?:annotated|unannotated|Annotated|Unannotated).*$", text, re.M)
    out = {"corner": a.corner, "results_dir": str(res), "saifs": dict(zip(labels, map(str, saifs))),
           "annotation_report": ann[:40], "values": vals}
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print("power", a.corner, len(vals), "values ->", a.out)


PORT_GROUPS = ("ib", "xl", "n_a", "n_b", "t_out", "n_y", "rom_rd", "kv_q")


def cmd_ports(a) -> None:
    """Toggle density (transitions per bit per clocked cycle) of the tile's bus ports in each stage's whole-stage
    pin SAIF: the activity the die-level broadcast, tree and fill wires carry."""
    out = {}
    pat = re.compile(r"^\s*\((\S+) \(T0 (\d+)\) \(T1 (\d+)\) \(TX (\d+)\) \(TC (\d+)\)\)")
    for act in a.act:
        d = json.loads(Path(act).read_text())
        saif = Path(d["saifs"]["full"]["map"]["pin_saif"])
        tc, bits = {g: 0 for g in PORT_GROUPS}, {g: 0 for g in PORT_GROUPS}
        with open(saif) as f:
            for line in f:
                if line.lstrip().startswith("(INSTANCE") and "(INSTANCE " + TOP not in line:
                    break
                m = pat.match(line)
                if m:
                    base = m.group(1).replace("\\", "").split("[", 1)[0]
                    if base in tc:
                        tc[base] += int(m.group(5)); bits[base] += 1
        n = d["records"]
        out[Path(act).parent.name] = {g: dict(bits=bits[g], toggles_per_bit_per_clocked_cycle=(tc[g] / bits[g] / n) if bits[g] else None)
                                      for g in PORT_GROUPS}
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("activity")
    s.add_argument("--replay", type=Path, required=True)
    s.add_argument("--vcd2saif", type=Path, required=True)
    s.add_argument("--rec", type=Path, required=True)
    s.add_argument("--netlist", type=Path, required=True, help="routed 6_final.v")
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--window", type=int, default=512, help="records per peak-search window")
    s.add_argument("--flip-at", type=int, default=200)
    s.add_argument("--procs", type=int, default=8)
    s = sub.add_parser("power")
    s.add_argument("--results", type=Path, required=True, help="kept ORFS workdir of the routed tile")
    s.add_argument("--corner", choices=sorted(SA.CORNERS), required=True)
    s.add_argument("--saif", nargs="+", default=[])
    s.add_argument("--label", nargs="*")
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("ports")
    s.add_argument("--act", nargs="+", required=True, help="activity.json files")
    s.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    {"activity": cmd_activity, "power": cmd_power, "ports": cmd_ports}[a.cmd](a)


if __name__ == "__main__":
    main()
