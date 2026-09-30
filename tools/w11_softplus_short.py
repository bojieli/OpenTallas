#!/usr/bin/env python3
"""W11: the short sqrt(softplus) of the V4.1 stream unit's side pipe (serial-chain domain, 0.9 GHz).

rtl/hdc/v41x/ot_hdc_v41x_spshort.sv computes the same bits as ot_hdc_v41x_softplus (DEPTH 162) in
DEPTH 107: a fused Horner step (4 cycles, not 6), a short exp (33, not 49), a radix-4 square root
(16, not 31), a divider front that knows t in [0, 1], the x2 folded into its multiply and an
addition-only final add.  No rounding of the golden is removed or reordered.

This tool records the evidence (results/rtl/w11_softplus_short.json):
  * exactness, rtl/test/tb_w11_spshort.sv under Verilator:
      unit 0  new vs old softplus/sqrt(softplus) and fault, EVERY 32-bit input (256 partitions)
      unit 1  new vs old exp, every 32-bit input (64 partitions)
      unit 2  radix-4 vs radix-2 sqrt, every 32-bit input (16 partitions)
      unit 3  the Horner step (13 constants), mul_x2 and addpos2 against the two-operation chains
              on a sweep of every exponent pair near K plus biased random words (4 seeds)
  * the WC (SS setup / FF hold) 1.111 ns, 60/25 ps hardening of the new units and the old ones
    (run_abi3_physical via /tmp/claude-1000/w11s/jobs/harden_wc09.sh; the physical.json records).

    python3 tools/w11_softplus_short.py build DIR            # Verilator benches DIR/obj{0..3}/Vtb
    python3 tools/w11_softplus_short.py record --eq DIR... --u3 DIR --phys DIR
The partitions ran as `Vtb +N=<2^32/P> +LO=<k*2^32/P>`; the record lists every partition's line.
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/w11_softplus_short.json"
NEW = "rtl/hdc/v41x/ot_hdc_v41x_spshort.sv"
TB = "rtl/test/tb_w11_spshort.sv"
HARNESS = "rtl/test/hdc_v41_harness.cpp"
LIB = ["rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
       "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_fastfp.sv",
       "rtl/hdc/v41/ot_hdc_fsqrt.sv", "rtl/hdc/v41/ot_hdc_fdiv.sv", "rtl/hdc/v41x/ot_hdc_v41x_sfu.sv"]
PREFIX = "rtl/hdc/ot_hdc_prefix.sv"            # synthesised: keep-level Kogge-Stone
PREFIX_SIM = "rtl/test/ot_hdc_prefix_sim.sv"   # simulated: behavioural adds, proved equal per width
KSADD_WIDTHS = (8, 9, 12, 24, 26, 28, 31, 33, 48, 51)
INC_WIDTHS = (24, 28, 31)
PARTS = {0: 256, 1: 64, 2: 16}
UNIT_NAME = {0: "softplus_s vs ot_hdc_v41x_softplus (sp, r, fault)",
             1: "exp_s vs ot_hdc_v41x_exp (y, fault)",
             2: "fsqrt4 vs ot_hdc_fsqrt (y, fault)"}
# (new module, new depth, replaced chain, its depth)
DEPTHS = [("ot_hdc_v41x_softplus_s", 107, "ot_hdc_v41x_softplus", 162),
          ("ot_hdc_v41x_exp_s", 33, "ot_hdc_v41x_exp", 49),
          ("ot_hdc_hstep", 4, "ot_hdc_qmul -> ot_hdc_qadd", 6),
          ("ot_hdc_fsqrt4", 16, "ot_hdc_fsqrt", 31),
          ("ot_hdc_v41x_spdiv (from the exp's last Horner result)", 19,
           "exp exponent step + ot_hdc_qadd + ot_hdc_v41x_fdiv", 1 + 3 + 19),
          ("ot_hdc_fp32_mul_x2", 3, "ot_hdc_qmul -> ot_hdc_qmul(., 2)", 6),
          ("ot_hdc_addpos2", 2, "ot_hdc_qadd", 3)]
# softplus_s schedule: (step, cycles before, cycles after)
SCHEDULE = [("t = exp(-|x|) (to the last Horner result)", 48, 32),
            ("exponent step + RN(t + 2) + t / den", 1 + 3 + 19, 19),
            ("u2 = u*u", 3, 3), ("8 Horner steps", 48, 32), ("l = 2 RN(u p)", 6, 3),
            ("sp = max(x,0) + l", 3, 2), ("sqrt", 31, 16)]
HARD = {"sp_softplus_s": "ot_hdc_v41x_softplus_s", "sp_base": "ot_hdc_v41x_softplus",
        "sp_hstep": "ot_hdc_hstep", "sp_exp": "ot_hdc_v41x_exp_s", "sp_sqrt4": "ot_hdc_fsqrt4",
        "sp_sqrt_old": "ot_hdc_fsqrt", "sp_spdiv": "ot_hdc_v41x_spdiv", "sp_fdiv_old": "ot_hdc_v41x_fdiv",
        "sp_mulx2": "ot_hdc_fp32_mul_x2", "sp_addpos2": "ot_hdc_addpos2"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sources() -> dict:
    paths = sorted({NEW, TB, HARNESS, PREFIX, PREFIX_SIM, *LIB, "tools/w11_softplus_short.py"})
    return {p: sha(ROOT / p) for p in paths}


def build(out: Path, units=(0, 1, 2, 3), pcut=1):
    for u in units:
        cmd = ["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
               "-Wno-BLKSEQ", "-Wno-TIMESCALEMOD", f"-GUNIT={u}", f"-GPCUT={pcut}", "--top-module", "tb_w11_spshort",
               "--prefix", "Vtb", "-Mdir", str(out / f"obj{u}"),
               *[str(ROOT / p) for p in LIB + [PREFIX_SIM, NEW, TB, HARNESS]], "-CFLAGS", "-O1"]
        subprocess.run(cmd, check=True, capture_output=True)


def prove(work: Path):
    """SAT (yosys sat -prove) that ot_hdc_ksadd_k / ot_hdc_inc_k of rtl/hdc/ot_hdc_prefix.sv equal the
    behavioural adds of PREFIX_SIM at every width the short softplus uses."""
    work.mkdir(parents=True, exist_ok=True)
    res = {}
    cases = [("ot_hdc_ksadd_k", w) for w in KSADD_WIDTHS] + [("ot_hdc_inc_k", w) for w in INC_WIDTHS]
    for mod, w in cases:
        sim = (ROOT / PREFIX_SIM).read_text().replace("module ot_hdc_ksadd_k", "module sim_ksadd").replace(
            "module ot_hdc_inc_k", "module sim_inc")
        (work / "sim.sv").write_text(sim)
        if mod == "ot_hdc_ksadd_k":
            body = (f"module miter (input [{w-1}:0] a, input [{w-1}:0] b, input cin, output ok);\n"
                    f"  wire [{w-1}:0] s1, s2; wire c1, c2;\n"
                    f"  ot_hdc_ksadd_k #(.W({w})) u1 (.a(a), .b(b), .cin(cin), .s(s1), .cout(c1));\n"
                    f"  sim_ksadd #(.W({w})) u2 (.a(a), .b(b), .cin(cin), .s(s2), .cout(c2));\n"
                    f"  assign ok = (s1 == s2) && (c1 == c2);\nendmodule\n")
        else:
            body = (f"module miter (input [{w-1}:0] a, input inc, output ok);\n"
                    f"  wire [{w-1}:0] y1, y2; wire c1, c2;\n"
                    f"  ot_hdc_inc_k #(.W({w})) u1 (.a(a), .inc(inc), .y(y1), .co(c1));\n"
                    f"  sim_inc #(.W({w})) u2 (.a(a), .inc(inc), .y(y2), .co(c2));\n"
                    f"  assign ok = (y1 == y2) && (c1 == c2);\nendmodule\n")
        (work / "miter.sv").write_text(body)
        r = subprocess.run(["yosys", "-p", f"read_verilog -sv {ROOT / PREFIX} {work / 'sim.sv'} {work / 'miter.sv'}; "
                            "hierarchy -top miter; proc; flatten; opt_clean; sat -prove ok 1 -verify miter"],
                           capture_output=True, text=True)
        res[f"{mod} W={w}"] = "proved" if "SUCCESS!" in r.stdout and r.returncode == 0 else "FAILED"
    return res


LINE = re.compile(r"W11SP unit=(\d) lo=([0-9a-f]{8}) n=(\d+) err=(\d+) fault=(\d+)")


def exhaustive(dirs):
    """Every partition line of units 0-2 from the given log directories; checks full coverage."""
    got = {0: {}, 1: {}, 2: {}}
    for d in dirs:
        for f in sorted(Path(d).rglob("p*.log")):
            m = LINE.search(f.read_text())
            if m:
                u, lo, n, e, fl = int(m[1]), int(m[2], 16), int(m[3]), int(m[4]), int(m[5])
                got[u][lo] = dict(n=n, err=e, fault=fl)
    res = {}
    for u, parts in PARTS.items():
        step = (1 << 32) // parts
        los = sorted(got[u])
        complete = los == [k * step for k in range(parts)] and all(got[u][lo]["n"] == step for lo in los)
        res[UNIT_NAME[u]] = dict(
            inputs=sum(v["n"] for v in got[u].values()), partitions=len(los), partitions_expected=parts,
            every_32bit_input=complete, errors=sum(v["err"] for v in got[u].values()),
            refusals_both=sum(v["fault"] for v in got[u].values()),
            pass_=complete and sum(v["err"] for v in got[u].values()) == 0)
    return res


def random_units(d):
    """Unit 3 logs: per-constant Horner step counts, mul_x2 and addpos2."""
    hs, x2, ap, m4 = {}, dict(checked=0, errors=0), dict(checked=0, errors=0), dict(checked=0, errors=0)
    seeds = []
    for f in sorted(Path(d).glob("s*.log")):
        t = f.read_text()
        if "W11SP unit=3" not in t:
            continue
        seeds.append(f.stem)
        for m in re.finditer(r"W11SP hstep K=([0-9a-f]{8}) n=(\d+) err=(\d+) refused=(\d+) unjustified=(\d+)", t):
            h = hs.setdefault(m[1], dict(checked=0, errors=0, refused=0, unjustified_refusals=0))
            for k, v in zip(("checked", "errors", "refused", "unjustified_refusals"), map(int, m.groups()[1:])):
                h[k] += v
        for name, acc in (("mul_x2", x2), ("addpos2", ap), ("mul4", m4)):
            m = re.search(rf"W11SP {name} n=(\d+) err=(\d+)", t)
            acc["checked"] += int(m[1])
            acc["errors"] += int(m[2])
    ok = (all(h["errors"] == 0 and h["unjustified_refusals"] == 0 for h in hs.values())
          and x2["errors"] == 0 and ap["errors"] == 0 and m4["errors"] == 0 and len(hs) == 13)
    return dict(seeds=seeds, hstep_by_constant=hs, mul_x2_vs_qmul_qmul2=x2, addpos2_vs_qadd_same_sign=ap,
                mul_doubled0_vs_qmul=m4,
                hstep_checked_total=sum(h["checked"] for h in hs.values()), pass_=ok)


def physical(d):
    out = {}
    for name, top in HARD.items():
        p = Path(d) / name / "physical.json"
        if not p.exists():
            out[name] = dict(top=top, status="missing")
            continue
        r = json.loads(p.read_text())
        g = r.get("design", {})
        per = g.get("clock_period_ns")
        wns = g.get("setup_wns_ns")
        out[name] = dict(top=top, status=r.get("status"), closed=g.get("closed"), clock_period_ns=per,
                         setup_wns_ns=wns, hold_wns_ns=g.get("hold_wns_ns"), fmax_hz=g.get("fmax_hz"),
                         area_um2=g.get("area_um2"), clock_uncertainty_ns=g.get("clock_uncertainty_ns"),
                         clock_hold_uncertainty_ns=g.get("clock_hold_uncertainty_ns"),
                         corner=r.get("orfs_corner") or g.get("orfs_corner"))
    return out


def strip_comments(text: str) -> str:
    return "\n".join(line.split("//", 1)[0].rstrip() for line in text.splitlines() if line.split("//", 1)[0].strip())


def same_logic(commit: str) -> dict:
    """The evidence ran on `commit`; every file it used must differ from HEAD's at most in comments."""
    out = {}
    for p in [NEW, TB, PREFIX, PREFIX_SIM, *LIB]:
        old = subprocess.run(["git", "-C", str(ROOT), "show", f"{commit}:{p}"], capture_output=True, text=True).stdout
        a, b = strip_comments(old), strip_comments((ROOT / p).read_text())
        if a == b:
            out[p] = True
        elif b.startswith(a) and p == NEW:
            # only whole modules appended (the parameter-free hardening tops); nothing the evidence ran is changed
            added = re.findall(r"^module (\w+)", b[len(a):], re.M)
            out[p] = f"same, plus appended modules {added}" if added and not any(
                re.search(rf"\b{m}\b", a) for m in added) else False
        else:
            out[p] = False
    return out


def record(args):
    eq = exhaustive(args.eq)
    u3 = random_units(args.u3)
    ph = physical(args.phys)
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    proofs = prove(Path(args.u3) / "prefix_proofs")
    logic = same_logic(args.evidence_commit)
    ok = (all(v["pass_"] for v in eq.values()) and u3["pass_"] and all(v == "proved" for v in proofs.values())
          and all(bool(v) for v in logic.values()))
    rec = dict(
        schema="opentallas.w11-softplus-short.v1",
        status="pass" if ok else "fail",
        git_head=head,
        evidence_commit=args.evidence_commit,
        evidence_sources_equal_to_head_but_comments=logic,
        simulator="Verilator 4.038",
        clock_domain="serial chain, 0.9 GHz (1.111 ns) at SS setup / FF hold, 60/25 ps (AGENTS.md)",
        depth=dict(before=162, after=107, saved_cycles=55, saved_ns_at_0p9GHz=round(55 / 0.9, 1),
                   units=[dict(new=a, depth=b, replaces=c, replaced_depth=d) for a, b, c, d in DEPTHS],
                   schedule=[dict(step=s, before=b, after=a) for s, b, a in SCHEDULE]),
        model=dict(tools_arch_budget_v41_SFU_DEPTH_softplus_now=259,
                   stream_unit_side_pipe_before=162, stream_unit_side_pipe_after=107,
                   note="SFU_DEPTH['fastfp']['softplus'] is the side pipe's S depth: 107 with this unit "
                        "(162 as committed in ot_hdc_v41x_vec; 259 is the five-stage ot_hdc_softplus). "
                        "The unit is not yet wired into ot_hdc_v41x_vec (its S-stage depth list and "
                        "the campaign's SFU_DEPTH would change 162 -> 107)."),
        exactness=dict(exhaustive=eq, random_units=u3, prefix_adder_proofs=proofs,
                       prefix_adder_note="Simulated with rtl/test/ot_hdc_prefix_sim.sv (behavioural adds); "
                                         "synthesised with rtl/hdc/ot_hdc_prefix.sv; SAT-equal at every width used.",
                       runner="tb_w11_spshort UNIT=u: Vtb +N=2^32/P +LO=k*2^32/P for k < P "
                              "(unit 3: +N=16000000 +verilator+seed+s)"),
        physical=ph,
        physical_runner="/tmp/claude-1000/w11s/jobs/harden_wc09.sh <name> --top <top> --source ...: "
                        "run_abi3_physical --view asap7 --clock-period-ns 1.111 --clock-uncertainty-ns 0.06 "
                        "--clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --stages synth,pnr "
                        "(ADDER_MAP_FILE empty)",
        limitation=args.limitation,
        sources_sha256=sources(),
    )
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=False) + "\n")
    print(json.dumps(dict(status=rec["status"], depth=rec["depth"]["after"],
                          phys={k: (v.get("status"), v.get("fmax_hz")) for k, v in ph.items()}), indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    b = sp.add_parser("build")
    b.add_argument("dir", type=Path)
    r = sp.add_parser("record")
    r.add_argument("--eq", nargs="+", required=True)
    r.add_argument("--u3", required=True)
    r.add_argument("--phys", required=True)
    r.add_argument("--limitation", default="")
    r.add_argument("--evidence-commit", required=True, help="commit the benches and routes were built from")
    a = ap.parse_args()
    if a.cmd == "build":
        build(a.dir)
    else:
        record(a)


if __name__ == "__main__":
    sys.exit(main())
