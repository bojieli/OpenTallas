#!/usr/bin/env python3
"""DS-ROM wavefront x reuse chain: position-slotted SIDE staging (ot_rom_pkg_ctrl_wf_ps SIDE_PSL) at the 1M token.

Vehicle rtl/dsrom_sys/integration/tb_dsrom_pslot_reuse.sv: one consumer stage (controller WAVE=1 WIN=6 SOURCE=0
SIDE_IN=1, NW 21, VWA 15) receives the index-source layer's top-512 selection of each position as a SIDE message and
the hop as a HIDDEN message; the behavioural core (CORE_LAT cycles, labelled) reads the staged selection once per
reuse layer (3 reads a job) and compares it with the golden.

Positions: the FIRST job is position 1,048,575 with the REAL golden selection (reuse source L2 / L20 / L24 at the
1M reference token: the consumers' ctx_in.sel in /home/ubuntu/w17work/ref/ctx1048576_seed20260930, read 0/1/2 =
layer SRC+1/SRC+2/SRC+3, each checked against that layer's own record).  Later jobs 1,048,576 .. are STAND-INS
(labelled): no golden exists after the last position of the 1M context; each is 512 distinct ids <= its position,
seeded per position, sorted as the golden's.
Orders: `ahead` (the producer WIN-ahead worst case: every SIDE before the first HIDDEN) and `lead1` (SIDE q+1
before HIDDEN q); `relay`: the selection rides in the hop (no SIDE; per position by construction, as built).  Configurations: PSL = 3 (8 slots >= WIN) and PSL = 0 (as built, must fail), N = 2 and 6, plus
a fail-closed control `conflict` (SIDE for q and q+8 both outstanding: proto_fault expected).

    python3 tools/dsrom_pslot_reuse.py prep   --scratch DIR
    python3 tools/dsrom_pslot_reuse.py run    --scratch DIR [--jobs 8]
    python3 tools/dsrom_pslot_reuse.py record --scratch DIR --out results/rtl/dsrom_correctness_20261004/pslot_reuse.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
GOLD = Path("/home/ubuntu/w17work/ref/ctx1048576_seed20260930")
VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
TB = "rtl/dsrom_sys/integration/tb_dsrom_pslot_reuse.sv"
SRC = ["rtl/dsrom_sys/integration/ot_rom_side_pslot.sv", "rtl/dsrom_sys/integration/ot_rom_pkg_ctrl_wf_ps.sv"]
P_REAL = 1048575
FLIT, NW, SW, K = 512, 21, 32, 512
HDR = dict(DEST=0, SRC=8, TYPE=16, LEN=24, USER=32, POS=40)
HDR["ADDR"] = 40 + NW + NW + 32 + NW
SIDE_RXB = 512
SOURCES = (2, 20, 24)
CORE_LAT = 400


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def header(typ: int, ln: int, pos: int, addr: int = 0) -> int:
    h = 5 | (4 << HDR["SRC"]) | (typ << HDR["TYPE"]) | (ln << HDR["LEN"]) | (0 << HDR["USER"])
    h |= (pos & ((1 << NW) - 1)) << HDR["POS"]
    h |= (addr & 0xFFFF) << HDR["ADDR"]
    return h


def pack(ids) -> list[int]:
    ids = list(ids)
    assert len(ids) == K
    words = []
    for f in range(SW):
        w = 0
        for j in range(16):
            w |= (int(ids[16 * f + j]) & 0xFFFFFFFF) << (32 * j)
        words.append(w)
    return words


def standin(pos: int) -> list[int]:
    rng = np.random.default_rng([20261004, pos])
    return sorted(int(x) for x in rng.choice(pos + 1, K, replace=False))


def golden_sel(L: int) -> list[int]:
    j = json.loads((GOLD / f"ctx1048576_L{L:02d}.json").read_text())
    assert j["position"] == P_REAL and j["context"] == 1048576
    return [int(x) for x in j["ctx_in"]["sel"]]


def write_case(d: Path, name: str, src: int, njobs: int, order: str):
    pos = [P_REAL + k for k in range(njobs)]
    pay, exp, lab = {}, [], []
    for k, p in enumerate(pos):
        if p == P_REAL:
            reads = [golden_sel(src + 1 + r) for r in range(3)]
            pay[p] = reads[0]
            lab.append(dict(job=k, pos=p, data="REAL golden: producer L%d selection = L%d..L%d ctx_in.sel" %
                            (src, src + 1, src + 3), sel_sha256=hashlib.sha256(json.dumps(reads[0]).encode()).hexdigest(),
                            reads_identical_in_golden=reads[0] == reads[1] == reads[2]))
        else:
            reads = [standin(p)] * 3
            pay[p] = reads[0]
            lab.append(dict(job=k, pos=p, data="STAND-IN (labelled): seeded distinct ids <= pos, sorted"))
        for r in range(3):
            exp += pack(reads[r])
    side = {p: [(0, header(3, SW, p, SIDE_RXB))] + [(int(f == SW - 1), w) for f, w in enumerate(pack(pay[p]))]
            for p in pos}
    hid = {p: [(0, header(1, 1, p)), (1, int(("%08x" % p) * 16, 16))] for p in pos}
    msgs = []
    if order == "relay":                         # the hop carries the selection: header, marker, 32 words
        msgs = [[(0, header(1, 1 + SW, p)), (0, int(("%08x" % p) * 16, 16))] +
                [(int(f == SW - 1), w) for f, w in enumerate(pack(pay[p]))] for p in pos]
    elif order == "ahead":
        msgs = [side[p] for p in pos] + [hid[p] for p in pos]
    elif order == "lead1":
        msgs = [side[pos[0]]]
        for k, p in enumerate(pos):
            if k + 1 < len(pos):
                msgs.append(side[pos[k + 1]])
            msgs.append(hid[p])
    elif order == "conflict":
        bad = pos[0] + 8                          # same slot, next generation, while q's message is unconsumed
        sb = [(0, header(3, SW, bad, SIDE_RXB))] + [(int(f == SW - 1), w) for f, w in enumerate(pack(standin(bad)))]
        msgs = [side[pos[0]], sb, hid[pos[0]]]
    flits = [f for m in msgs for f in m]
    (d / f"{name}.stim").write_text("".join("%0129x\n" % ((l << FLIT) | w) for l, w in flits))
    (d / f"{name}.exp").write_text("".join("%0128x\n" % w for w in exp))
    return dict(name=name, src=src, njobs=njobs, order=order, positions=pos, flits=len(flits), jobs=lab,
                stim_sha256=sha(d / f"{name}.stim"), exp_sha256=sha(d / f"{name}.exp"))


CASES = [(f"L{s}_n{n}_{o}", s, n, o) for s in SOURCES for n in (2, 6) for o in ("ahead", "lead1", "relay")] + \
        [("L20_n2_conflict", 20, 2, "conflict")]


def cmd_prep(a):
    d = a.scratch.resolve()
    d.mkdir(parents=True, exist_ok=True)
    man = dict(gold=str(GOLD), golden_sha256={f"L{L:02d}": sha(GOLD / f"ctx1048576_L{L:02d}.json")
                                               for s in SOURCES for L in (s + 1, s + 2, s + 3)},
               cases=[write_case(d, *c) for c in CASES])
    (d / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(len(man["cases"]), "cases")


def build(d: Path, psl: int, nj: int, relay: int = 0) -> Path:
    obj = d / f"obj_psl{psl}_n{nj}" if not relay else d / f"obj_relay_n{nj}"
    exe = obj / "Vtb_dsrom_pslot_reuse"
    if not exe.exists():
        cmd = [str(VERILATOR), "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-O2",
               "--top-module", "tb_dsrom_pslot_reuse", "--Mdir", str(obj), "-j", "4",
               f"-GPSL={psl}", f"-GRELAY={relay}", f"-GNJOBS={nj}", f"-GCORE_LAT={CORE_LAT}"] + [str(ROOT / s) for s in SRC + [TB]]
        p = subprocess.run(cmd, capture_output=True, text=True)
        (d / f"build_{obj.name}.log").write_text(p.stdout + p.stderr)
        if p.returncode:
            raise RuntimeError(f"build failed psl{psl} n{nj}")
    return exe


def run_one(d: Path, case: dict, psl: int):
    relay = int(case["order"] == "relay")
    exe = build(d, psl, case["njobs"], relay)
    tag = f"{case['name']}_psl{psl}"
    p = subprocess.run([str(exe), f"+STIM={d / case['name']}.stim", f"+EXP={d / case['name']}.exp",
                        f"+P0={case['positions'][0]}"], capture_output=True, text=True, cwd=d)
    log = p.stdout + p.stderr
    (d / f"{tag}.log").write_text(log)
    reads = [dict(job=int(m[1]), pos=int(m[2]), read=int(m[3]), cycle=int(m[4]), slot_off=int(m[5]),
                  word_errors=int(m[6]))
             for m in re.finditer(r"READ job=(\d+) pos=(\d+) layer_read=(\d+) cycle=(\d+) slot_off=(\d+) "
                                  r"word_errors=(\d+)", log)]
    starts = [dict(job=int(m[1]), pos=int(m[2]), cycle=int(m[3]))
              for m in re.finditer(r"JOB (\d+) start pos=(\d+) user=\d+ cycle=(\d+)", log)]
    res = "PASS" if re.search(r"^PASS ", log, re.M) else ("FAIL_proto_fault" if "FAIL proto_fault" in log else "FAIL")
    return dict(case=case["name"], psl=psl, njobs=case["njobs"], order=case["order"], src=case["src"], result=res,
                word_errors=sum(r["word_errors"] for r in reads), reads=reads, starts=starts,
                tail=[l for l in log.splitlines() if l.startswith(("PASS", "FAIL", "E "))])


def cmd_run(a):
    d = a.scratch.resolve()
    man = json.loads((d / "manifest.json").read_text())
    for psl in (0, 3):
        for nj in (2, 6):
            build(d, psl, nj)
    for nj in (2, 6):
        build(d, 0, nj, 1)
    jobs = [(c, psl) for c in man["cases"] for psl in ((0,) if c["order"] == "relay" else (0, 3))]
    with ThreadPoolExecutor(a.jobs) as ex:
        runs = list(ex.map(lambda j: run_one(d, *j), jobs))
    (d / "runs.json").write_text(json.dumps(runs, indent=1) + "\n")
    for r in runs:
        print(f"{r['case']:22s} psl{r['psl']} {r['result']:16s} word_errors={r['word_errors']}")


def cmd_record(a):
    d = a.scratch.resolve()
    man = json.loads((d / "manifest.json").read_text())
    runs = json.loads((d / "runs.json").read_text())
    exp = {}
    for r in runs:
        if r["order"] == "relay":
            exp[(r["case"], r["psl"])] = "PASS"
        elif r["order"] == "conflict":
            exp[(r["case"], r["psl"])] = "FAIL_proto_fault" if r["psl"] == 3 else None
        else:
            exp[(r["case"], r["psl"])] = "PASS" if r["psl"] == 3 else "FAIL"
    checks = []
    for r in runs:
        e = exp[(r["case"], r["psl"])]
        checks.append(dict(case=r["case"], psl=r["psl"], expected=e, got=r["result"],
                           ok=(e is None) or r["result"] == e))
    ok = all(c["ok"] for c in checks)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    rec = dict(schema="opentallas.dsrom.pslot-reuse.v1", verdict="PASS" if ok else "FAIL", position=P_REAL,
               context=1048576, git_head=head, vehicle=__doc__.split("\n\n")[1], core_lat_cycles=CORE_LAT,
               unvalidated=["decode core: behavioural job of CORE_LAT cycles reading the staged selection 3 times "
                            "(the reuse layers' arithmetic is not in this vehicle; their selection input is)",
                            "positions after 1,048,575: stand-in selections (no golden after the last position of "
                            "the 1M context)",
                            "controller expected-position register preset to the first position (hierarchical)"],
               checks=checks, cases=man["cases"], golden=man["golden_sha256"], runs=runs,
               tool_version=subprocess.check_output([str(VERILATOR), "--version"], text=True).strip(),
               source_sha256={s: sha(ROOT / s) for s in SRC + [TB, "tools/dsrom_pslot_reuse.py"]})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(rec["verdict"])
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    for n in ("prep", "run", "record"):
        p = sp.add_parser(n)
        p.add_argument("--scratch", type=Path, required=True)
        if n == "run":
            p.add_argument("--jobs", type=int, default=8)
        if n == "record":
            p.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    return dict(prep=cmd_prep, run=cmd_run, record=cmd_record)[a.cmd](a) or 0


if __name__ == "__main__":
    raise SystemExit(main())
