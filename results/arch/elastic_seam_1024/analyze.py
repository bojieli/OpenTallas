#!/usr/bin/env python3
"""ELASTIC lane (owner opt-in experiment 2026-10-24 07:35): latency-insensitive (valid + receive FIFO + credit) seams vs
R8 bus-coherent landing pads on the Qwen compute die.  Analytical sizing (AGENTS.md design method step 1).

Vehicles (both read from git, source-pinned):
  P5 = bound_r8: plan claude/qc-p5-tie-1023 @e3f313354 + physical/die_plan/qwen_compute/bind/bound_r8/bus_groups.json.gz
  P6 = main plan physical/die_plan/qwen_compute/die_plan.json + r8/bus_groups.json (QC-P6-R8 1f5b9bee38)
Pads are recomputed with tools/die_plan/r8.solve (same classes / offsets as the committed tables).

Per padded member m (sink bits W, pad p, bound depth d = cycles from source leaf to sink landing):
  pad cost      = p * W register stages                         (ot_dp_dly, reset-less, no enable)
  elastic cost  = D * W FIFO entries + control, D = max(ceil(u*p), ceil(u*(2d+2)), 1) at duty u (words/cycle):
                  Little: a word that waits p cycles for its slowest partner occupies an entry p cycles; credit
                  loop: full rate needs RTT = d (fwd) + d (credit return) + 2 (enq/deq, credit register) entries.
                  control per lane: valid + credit bit per relay stage (2*d), ptrs + count (3*log2 D + 1),
                  send credit counter (log2 D + 1).
  area per entry from cal/run_cal.sh (yosys 0.68, ASAP7 RVT SS, abc -D 833): pad 0.3353 um^2/bit-stage,
  elastic receive FIFO 0.523-0.537 um^2/bit-entry (enable + read mux).
Token latency: a padded member lands at its class maximum offset = the arrival of the slowest member it is joined with
(same bus) or locked to (replica set); an elastic consumer must wait for the same slowest member, so worst-case
arrival is unchanged and the elastic gain is 0 cycles (+1 cycle per crossing with a registered FIFO, 0 with bypass).
"""
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/die_plan"))
import r8  # noqa: E402
import schema as S  # noqa: E402

OUT = Path(__file__).resolve().parent
PAD_UM2 = 21.46176 / 64           # cal pad_W64_D1
CAL = json.loads((OUT / "cal/cal_area.json").read_text())
ERX_UM2 = {int(k): v for k, v in CAL["erx_um2_per_bit_entry"].items()}
DIE_UM2 = None


def git_json(rev_path):
    return json.loads(subprocess.check_output(["git", "-C", str(ROOT), "show", rev_path]))


def erx_per_bit(D):
    ks = sorted(ERX_UM2)
    k = min(ks, key=lambda x: abs(x - D))
    return ERX_UM2[k]


def ctl_flops(d, D):
    a = max(1, math.ceil(math.log2(max(D, 2))))
    return 2 * d + 3 * a + 1 + a + 1


def elastic_depth(p, d, u):
    return max(math.ceil(u * p), math.ceil(u * (2 * d + 2)), 1)


def analyse(name, raw, bg):
    mem, used = r8.solve(bg, raw)
    sm = r8.summary(bg, mem, used)
    L = raw["latency"]["lanes"]
    lanes = {l["id"]: l for l in raw["lanes"]}
    ports = {q["id"]: q for q in raw["ports"]}
    nb = r8.nbits
    W, H = raw["die"]["outline_um"]
    # classes: drivers (max offset) vs padded members
    cls = defaultdict(list)
    for m in mem:
        cls[m["cls"]].append(m)
    driver_bits = Counter()
    for ms in cls.values():
        offs = [m["bound"] - m["asbuilt"] for m in ms]
        mx = max(offs)
        if any(m["pad"] for m in ms):
            for m, o in zip(ms, offs):
                if o == mx:
                    driver_bits[m["lane"]] += nb(m["sink_bits"])
    # per lane aggregates
    agg = defaultdict(lambda: dict(bits=0, pad_flops=0, pads=Counter(), bound=set(), members=0))
    for m in mem:
        a = agg[m["lane"]]
        b = nb(m["sink_bits"])
        a["bits"] += b
        a["pad_flops"] += b * m["pad"]
        a["pads"][m["pad"]] += b
        a["bound"].add(m["bound"])
        a["members"] += 1

    def lane_row(lid):
        l = lanes.get(lid)
        a = agg.get(lid, dict(bits=0, pad_flops=0, pads=Counter(), bound=set(), members=0))
        return dict(lane=lid, hops=len(l["ports"]) if l else None, width=ports[l["ports"][0]]["width"] if l else None,
                    cycles=L.get(lid, {}).get("cycles"), stations=L.get(lid, {}).get("stations"),
                    member_bits=a["bits"], member_bound_depths=sorted(a["bound"]), pad_flops=a["pad_flops"],
                    pad_hist_bits={str(k): v for k, v in sorted(a["pads"].items())},
                    driver_bits=driver_bits.get(lid, 0))
    longest = sorted(L, key=lambda k: (-L[k]["cycles"], k))[:24]
    most_padded = sorted(agg, key=lambda k: -agg[k]["pad_flops"])[:24]
    # pad flops by lane length
    by_len = Counter()
    for lid, a in agg.items():
        by_len[L.get(lid, {}).get("cycles", -1)] += a["pad_flops"]
    # elastic sizing per padded member at duty u
    res = {}
    for u in (1.0, 0.5, 0.25, 0.125, 1 / 16, 1 / 32):
        pad_a = el_a = 0.0
        win_lanes = defaultdict(lambda: [0.0, 0.0])
        for m in mem:
            if not m["pad"]:
                continue
            b = nb(m["sink_bits"])
            d = m["bound"]
            D = elastic_depth(m["pad"], d, u)
            pa = m["pad"] * b * PAD_UM2
            ea = D * b * erx_per_bit(D) + ctl_flops(d, D) * PAD_UM2
            pad_a += pa
            el_a += ea
            win_lanes[m["lane"]][0] += pa
            win_lanes[m["lane"]][1] += ea
        wins = {k: v for k, v in win_lanes.items() if v[1] < v[0]}
        res[f"{u:g}"] = dict(pad_um2=round(pad_a), elastic_um2=round(el_a), ratio=round(el_a / pad_a, 3),
                             lanes_padded=len(win_lanes), lanes_elastic_smaller=len(wins),
                             saving_um2_if_only_winners=round(sum(v[0] - v[1] for v in wins.values())))
    # per lane break-even duty (largest u at which elastic area < pad area on that lane)
    be = {}
    for lid in most_padded[:24]:
        ms = [m for m in mem if m["lane"] == lid and m["pad"]]
        best = None
        for u in (1.0, 0.5, 1 / 3, 0.25, 0.2, 1 / 6, 0.125, 0.1, 1 / 16, 1 / 32):
            pa = sum(m["pad"] * nb(m["sink_bits"]) * PAD_UM2 for m in ms)
            ea = sum(elastic_depth(m["pad"], m["bound"], u) * nb(m["sink_bits"]) * erx_per_bit(
                elastic_depth(m["pad"], m["bound"], u)) + ctl_flops(m["bound"], 1) * PAD_UM2 for m in ms)
            if ea < pa:
                best = u
                break
        be[lid] = best
    # replica vs bus-group origin of pads: does the padded member's own landing group need it?
    own = 0
    groups = defaultdict(list)
    for m in mem:
        groups[(m["sink"], m["src_part"])].append(m)
    for ms in groups.values():
        gmax = max(m["bound"] - m["asbuilt"] for m in ms)
        for m in ms:
            own += min(m["pad"], gmax - (m["bound"] - m["asbuilt"])) * nb(m["sink_bits"])
    return dict(
        vehicle=name, die_um=[W, H], r8_summary=sm,
        pad_area_um2=round(sm["pad_flops"] * PAD_UM2), die_area_mm2=round(W * H / 1e6, 1),
        pad_area_frac_of_die=sm["pad_flops"] * PAD_UM2 / (W * H),
        pad_flops_own_bus_group=own, pad_flops_replica_or_class_union=sm["pad_flops"] - own,
        pad_flops_by_lane_cycles={str(k): v for k, v in sorted(by_len.items()) if v},
        longest_lanes=[lane_row(k) for k in longest],
        most_padded_lanes=[lane_row(k) | dict(break_even_duty=be.get(k)) for k in most_padded],
        elastic_vs_pad_by_duty=res)


def main():
    p5 = git_json("e3f313354:physical/die_plan/qwen_compute/die_plan.json")
    import gzip
    bg5 = json.loads(gzip.decompress(subprocess.check_output(
        ["git", "-C", str(ROOT), "show", "HEAD:physical/die_plan/qwen_compute/bind/bound_r8/bus_groups.json.gz"])))
    p6 = git_json("HEAD:physical/die_plan/qwen_compute/die_plan.json")
    bg6 = git_json("HEAD:physical/die_plan/qwen_compute/r8/bus_groups.json")
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    out = dict(schema="opentallas.elastic_seam_sizing.v1", source_head=head,
               pad_um2_per_bit_stage=PAD_UM2, erx_um2_per_bit_entry=ERX_UM2,
               P5_bound_r8=analyse("P5 bound_r8 (plan e3f313354)", p5, bg5),
               P6_main=analyse("P6 main plan (QC-P6-R8 1f5b9bee38)", p6, bg6))
    (OUT / "sizing.json").write_text(json.dumps(out, indent=1) + "\n")
    for k in ("P5_bound_r8", "P6_main"):
        v = out[k]
        print(k, v["r8_summary"]["pad_flops"], "pad flops", v["pad_area_um2"], "um2",
              f"{100 * v['pad_area_frac_of_die']:.4f}% die", "own-group", v["pad_flops_own_bus_group"])
        for u, r in v["elastic_vs_pad_by_duty"].items():
            print("  duty", u, r)


if __name__ == "__main__":
    main()
