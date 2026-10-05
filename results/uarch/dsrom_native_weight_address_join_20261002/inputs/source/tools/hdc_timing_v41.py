#!/usr/bin/env python3
"""Cycle model of the DeepSeek-V4.1 hardwired decode core, calibrated against its RTL.

Replays a V4.1 program (tools/hdc_program_v41.py) through a model of the
sequencer (in-order single issue; fetch/decode gap; skipped instructions;
per-instruction wait masks on unit drains) and the four units:

* ME  the matrix-vector engine: an element loop of tiles * k * IL cycles, then
      a fixed result latency to its drain;
* SU  the V4.1 stream unit: one vector of SU_LANES elements per cycle (one
      element per 8 cycles in SEQ reductions), the class depth (M1 multiply or
      divide, the SFU function), same-class overlap of consecutive ops, a chase
      (a vector waits for the in-flight count to fall below D), a class change
      only once drained, the reducer's tail and the segment tree;
* QE  the quantised engine: index read, activation blocks through the
      quantiser, alignment of the word stream to the block-dot lanes' free-
      running slot counter, tiles * nb * IL words, the lanes' latency;
* XU  SELECT (n elements in, k indices out), Sinkhorn, Engram hash and gather;
* HE  the hyper-connection projection engine: k * IL cycles (k the chunk
      length), then its latency and the chunk tree.

Constants are the RTL's (`K`); `--calibrate TRACE` fits them to a Verilator
issue trace (tb_hdc_core_v41 +TRACE) and reports every issue's error.  The
model needs only the program's shapes and the position, so it prices what the
RTL simulator reaches only slowly (long contexts), and design options:
`--sinkhorn-seq` (the simple sequential Sinkhorn instead of the routed
one-normalisation-per-step unit, ot_hdc_sinkhorn_mc).

Quantised weights in HBM (`simulate(q=QStream(...))`, `--q-hbm NPC`) adds the QE
weight streamer (rtl/hdc/hbm/ot_hdc_qstream.sv): the token's LINQ ops (those
whose predicate holds) are one stream of FP8 (17-sector) and packed FP4
(9-sector) words; word k is requested one a cycle when the window has room
(word k - win consumed) and, for a routed expert, not before its release
instruction has issued (plus the id read); the HBM serves sectors at the
calibrated rate and a word arrives `lat` cycles after its request at the
earliest.  A LINQ op issues once the first T = min(n, lead + n - floor(n *
rate / 256)) of its words have arrived, and its row phase consumes a word a
cycle.  Constants fitted to the RTL (tools/rtl_hdc_hbm_campaign.py).
"""
import argparse
import json
import re
from pathlib import Path

import hdc_isa_v41 as I

ROOT = Path(__file__).resolve().parents[1]
IL, W, G = I.INTERLEAVE, I.W_LANES, I.GROUPS

# RTL constants (cycles), fitted by `calibrate` jointly against the reduced vehicle's traces
# (stream-unit widths 4, 8, 16; before and after the K-splits and the overlap scheduling).
K = dict(
    gap=6,              # go -> next go of a following instruction (S_GO, FETCH, WAIT, CAP, DEC, ISSUE)
    skip=5,             # a skipped instruction (predicate / zero count): ISSUE -> FETCH ..
    me_start=2,         # go -> first element
    me_drain=29,        # last element -> idle seen by the sequencer
    me_next=0,          # last element -> a following op may be accepted
    su_start=1,
    su_base=28,         # emit -> retire with every stage, no M1 divide, no SFU (F0..F4, PRE, M1, M2, AD, E1, E2, RND)
    su_div=26,          # extra depth of an M1 divide (31 vs 5)
    su_stage=5,         # an unused M1 (no multiply or divide), M2, AD, E1 or E2 stage: skipped
    su_cls=5,           # a class change: last retire -> the new op accepted
    su_idle=7,          # last retire -> idle seen (no reduction)
    su_red=35,          # last retire -> idle seen, with a reduction
    su_tree=25,         # red_tree: the segment tree after the last segment sum
    su_tree_free=-1,    # red_tree: idle seen -> the unit accepts again
    su_chase=6,         # chase: the previous op's last emit + depth - D + this -> the first emit
    qe_start=-2,
    qe_idx=2,
    qe_load=16,         # after the nb block reads: the quantiser's latency and the state step
    qe_rows_lat=25,     # last word -> last result written -> idle seen
    qe_qdq_lat=20,      # QDQ: after the reads
    qe_phase0=-3,       # absolute-cycle offset of the lanes' slot counter
    xu_sel=47,          # SELECT: after the n reads, to the last index written (plus k)
    xu_sink=4,          # simple Sinkhorn: sink_cycles() + this
    sk_step=7,          # routed Sinkhorn: core cycles per unit step (ot_hdc_sinkhorn_mc STEP_CYC)
    xu_skmc=10,         # routed Sinkhorn: (2 ITERS + 1) steps + this          # Sinkhorn (simple unit): computed by sink_cycles() + this
    xu_ehash=18,
    xu_egather=5,
    he_start=-1,
    he_drain=32,        # last element -> the chunk tree -> the last word written -> idle seen
)
SFU_DEPTH = {I.SFU_NONE: 1, I.SFU_EXP: 92, I.SFU_RSQRT: 61, I.SFU_SQRT: 31, I.SFU_SIGM: 128, I.SFU_SILU: 128,
             I.SFU_SPSQRT: 259, I.SFU_EGATE: 161}


def sink_cycles(iters=20):
    """ot_hdc_sinkhorn_seq: per step, 3 (or 4) add phases of 4 issues and a
    divide phase of 16, each waiting for its results, and step 0's +eps phase."""
    add_phase = 4 + 5 + 2          # issue 4, the last result 5 later, count and switch
    div_phase = 16 + 31 + 2
    total = 1                      # accept -> phase S1
    for step in range(2 * iters):
        total += 3 * add_phase + (0 if step == 0 else add_phase) + div_phase
        if step == 0:
            total += 16 + 5 + 2
    return total + 2               # P_DONE, out_valid


# QE weights in HBM: sec_per_pc, the probed sectors (32 B) per cycle of one
# pseudo-channel; sec_cap, the most the QE stream takes in (its 17-sector words
# span up to 5 channels and go one request a cycle through an 8-word look-
# ahead) -- fitted with lat (request to arrival) and rel (a release
# instruction's issue to the routed expert's first word being fetchable: the
# walker reaching the entry, the id read) to the reduced vehicle's Verilator
# runs at 4, 16 and 32 pseudo-channels; c_ann, announce to issue.
# rate_sec_per_pc: the conservative per-channel rate behind the guaranteed
# rate (q_rate) the streamer is configured with.
QH = dict(npc=8, sec_per_pc=0.877, sec_cap=2.8, lat=80, c_ann=6, rel=120, lead=512, win=1024, margin=0.9,
          rate_sec_per_pc=0.30)
SPW8, SPW4 = 17, 9


def q_rate(q):
    """The QE streamer's guaranteed rate (FP8 words per cycle x 256)."""
    return min(256, int(256 * q["margin"] * q["npc"] * q["rate_sec_per_pc"] / SPW8))


class QStream:
    """Fluid model of the QE weight streamer over one token."""

    def __init__(self, q, prog, pos, rate=None):
        self.q = q
        self.s = min(q["npc"] * q["sec_per_pc"], q.get("sec_cap", 1e9))
        self.rate = q_rate(q) if rate is None else rate
        self.words = []                 # (spw, entry) per stream word
        self.ent = []                   # (first word, n, release group)
        grp = 0
        for f0 in prog:
            f = {name: f0.get(name, 0) for name, _ in I.FIELDS}
            if f["wrel"]:
                grp += 1
            if f["unit"] != I.UNIT_QE or f["qe_mode"] != I.QE_LINQ:
                continue
            if (f["pred"] == I.PRED_ODD and not pos & 1) or (f["pred"] == I.PRED_NZ and pos == 0):
                continue
            n = f["qe_tiles"] * f["qe_nb"] * IL
            self.ent.append((len(self.words), n, grp if f["qe_ind"] else 0))
            self.words.extend([SPW4 if f["qe_fp4"] else SPW8] * n)
        self.first_of = {e[0]: e for e in self.ent}
        self.r, self.a, self.c = [], [], []
        self.release_t = {}
        self.n_rel = 0
        self.nxt = 0
        self.stats = dict(ops=0, words=0, sectors=sum(self.words), wait_cycles=0)

    def release(self, t):
        self.n_rel += 1
        self.release_t[self.n_rel] = t

    def _req(self, k):
        q = self.q
        while len(self.r) <= k:
            j = len(self.r)
            t = self.r[-1] + 1 if j else 0.0
            if j >= q["win"]:
                t = max(t, self.c[j - q["win"]])
            e = self.first_of.get(j)
            if e and e[2]:
                t = max(t, self.release_t[e[2]] + q["rel"])
            a = t + q["lat"]
            if j:
                a = max(a, self.a[-1] + self.words[j] / self.s)
            self.r.append(t)
            self.a.append(a)

    def gate(self, t_ann):
        first, n, _ = self.ent[self.stats["ops"]]
        q = self.q
        T = min(n, q["lead"] + n - (n * self.rate) // 256)
        self._req(first + T - 1)
        return max(t_ann + q["c_ann"], self.a[first + T - 1]), n

    def consume(self, n, c0):
        self.c.extend(c0 + j for j in range(n))
        self.stats["ops"] += 1
        self.stats["words"] += n


def simulate(prog, pos, k=K, trace=False, sinkhorn_seq=False, t0=30, q=None, entry=0, nslot=1):
    """Cycles of one run of `prog` from `entry` to its END at position pos.
    Multi-token prediction (nslot > 1, tools/hdc_program_v41.py build_mtp): an
    instruction's DYN values and predicate take its slot's position pos +
    dslot; the DYN banks cost one cycle a slot at the start and at a DYN
    control step; a control step issues once its wait mask has drained; a QE
    LINQ op serving mx_m slots loads mx_m activations before its word stream
    (one weight stream for all of them); ME and HE ops with mx_m slots take
    their one-position time."""
    banks = [I.dyn_values(0, pos + j) for j in range(max(1, nslot))]
    dyn = banks[0]
    t = nslot - 1                             # sequencer: earliest next issue cycle (the DYN banks)
    free = {u: 0 for u in (1, 2, 3, 4, 5)}    # unit accepts a new op from here
    idle = {u: 0 for u in (1, 2, 3, 4, 5)}    # unit drained (as the sequencer sees it) at
    su_cls, su_last_retire, su_last_emit = None, 0, 0
    issues = []
    for n in range(entry, len(prog)):
        f0 = prog[n]
        f = {name: f0.get(name, 0) for name, _ in I.FIELDS}
        u = f["unit"]
        if u == I.UNIT_END and f["ctl"] == I.CTL_END:
            t = max([t] + list(idle.values())) + 1
            break
        if u == I.UNIT_CTL:                    # a control step: its wait mask, then the sequencer's own cycles
            ready = t
            for b in range(5):
                if f["wait"] >> b & 1:
                    ready = max(ready, idle[b + 1])
            issues.append((ready, n, u))
            t = ready + k["gap"] + {I.CTL_DYN: nslot, I.CTL_ACCEPT: 2}.get(f["ctl"], 0)
            continue
        dyn = banks[f["dslot"]] if nslot > 1 else banks[0]
        p = pos + (f["dslot"] if nslot > 1 else 0)
        skip = (f["pred"] == I.PRED_ODD and not p & 1) or (f["pred"] == I.PRED_NZ and p == 0)
        if u == I.UNIT_ME:
            cnt = [f["me_nout"] + dyn[f["me_d_nout"]], f["me_tiles"] + dyn[f["me_d_tiles"]],
                   f["me_k"] + dyn[f["me_d_k"]]]
            skip |= 0 in cnt
        elif u == I.UNIT_SU:
            no, ni = f["su_nout"] + dyn[f["su_d_nout"]], f["su_nin"] + dyn[f["su_d_nin"]]
            skip |= no == 0 or ni == 0
        elif u == I.UNIT_XU and f["xu_op"] == I.XU_SEL:
            skip |= f["xu_n"] + dyn[f["xu_d_n"]] == 0
        if skip:
            t += k["skip"]
            continue
        unit = u
        ready = t
        for b in range(5):
            if f["wait"] >> b & 1:
                ready = max(ready, idle[b + 1])
        go = max(ready, free[unit])
        if q is not None and unit == I.UNIT_QE and f["qe_mode"] == I.QE_LINQ:
            g, _ = q.gate(t)
            g = int(-(-g // 1))
            if g > go:
                q.stats["wait_cycles"] += g - go
                go = g
        if unit == I.UNIT_SU:
            stages = (f["m1"] not in (I.M1_BYP, I.M1_MAXB), f["m2"] != I.M2_BYP or f["qm"] != I.QM_OFF,
                      f["ad"] != I.AD_BYP, f["e1"] != I.E1_BYP, f["e2"] != I.E2_BYP)
            cls = (f["m1"] in (I.M1_DIVB, I.M1_DIVIMM), f["sfu"]) + stages
            if su_cls is not None and cls != su_cls:
                go = max(go, su_last_retire + k["su_cls"])
        if q is not None and f["wrel"]:
            q.release(go)
        issues.append((go, n, u))
        s = go + 1                                  # the unit accepts at the next edge
        if unit == I.UNIT_HE:
            e = f["he_k"] * IL
            free[unit] = s + k["he_start"] + e
            idle[unit] = s + k["he_start"] + e + k["he_drain"]
        elif unit == I.UNIT_ME:
            e = cnt[1] * cnt[2] * IL
            free[unit] = s + k["me_start"] + e - 1 + k["me_next"]
            idle[unit] = s + k["me_start"] + e + k["me_drain"]
        elif unit == I.UNIT_SU:
            vec = f.get("su_vec", 0)
            e = (no * -(-ni // I.SU_LANES) if vec == I.VEC_I else
                 -(-no // I.SU_LANES) * ni if vec == I.VEC_O else no * ni)
            step = 8 if f["red"] == I.RED_SEQ else 1
            depth = (k["su_base"] + (k["su_div"] if cls[0] else 0) + SFU_DEPTH[cls[1]] -
                     k["su_stage"] * sum(1 for used in cls[2:] if not used))
            first = s + k["su_start"]
            if f.get("su_chase", 0) and su_cls == cls:   # vector 0 waits for the in-flight count to fall below D
                first = max(first, su_last_emit + depth + k["su_chase"] - f["su_chase"])
            last_emit = first + step * (e - 1)
            su_last_emit = last_emit
            free[unit] = last_emit + 1
            su_last_retire = max(su_last_retire, last_emit + depth) if su_cls == cls else last_emit + depth
            su_cls = cls
            idle[unit] = max(idle[unit], su_last_retire + (k["su_red"] if f["red"] else k["su_idle"]))
            if f.get("red_tree"):             # the unit holds until the segment tree has written
                idle[unit] += k["su_tree"]
                free[unit] = idle[unit] + k["su_tree_free"]
        elif unit == I.UNIT_QE:
            c = s + k["qe_start"] + (k["qe_idx"] if f["qe_ind"] else 0) + f["qe_nb"] * max(1, f["mx_m"])
            if f["qe_mode"] == I.QE_LINQ:
                c += k["qe_load"]
                c += (4 - (c + t0 + k["qe_phase0"])) % IL          # wait for slot phase IL-4
                if q is not None:
                    q.consume(f["qe_tiles"] * f["qe_nb"] * IL, c)
                c += f["qe_tiles"] * f["qe_nb"] * IL
                done = c + k["qe_rows_lat"]
            else:
                done = c + k["qe_qdq_lat"]
            free[unit] = done
            idle[unit] = done + 1
        else:
            op = f["xu_op"]
            if op == I.XU_SEL:
                nn = f["xu_n"] + dyn[f["xu_d_n"]]
                kk = min(f["xu_k"] + dyn[f["xu_d_k"]], nn)
                done = s + nn + kk + k["xu_sel"]
            elif op == I.XU_SINK:
                done = s + (sink_cycles() + k["xu_sink"] if sinkhorn_seq else 41 * k["sk_step"] + k["xu_skmc"])
            elif op == I.XU_EHASH:
                done = s + k["xu_ehash"]
            else:
                done = s + 24 + k["xu_egather"]
            free[unit] = done
            idle[unit] = done + 1
        t = go + k["gap"]
    return (t, issues) if trace else t


def load_prog(img):
    words = [int(x, 16) for x in (Path(img) / "prog.hex").read_text().split()]
    return [I.decode(w) for w in words]


def parse_trace(text):
    return [(int(m.group(1)), int(m.group(2))) for m in re.finditer(r"ISSUE cyc=(\d+) pc=(\d+) unit=\d+", text)]


def errors(prog, pos, rtl, k):
    total, iss = simulate(prog, pos, k, trace=True)
    model = {n: g for g, n, _ in iss}
    err = [model[pc] - c for c, pc in rtl if pc in model]
    return total, err


def calibrate(prog, pos, rtl, cycles, keys=None, rounds=3):
    """Coordinate descent on integer constants: the sum of |issue error| plus the
    token's cycle error."""
    k = dict(K)
    # the long-latency constants first, so short ones do not absorb their error
    keys = keys or ["xu_sink", "xu_sel"] + [x for x in K if x not in ("gap", "xu_sink", "xu_sel")]

    def cost(kk):
        # local errors: each instruction's error relative to its predecessor's, so a
        # mistimed op counts once instead of shifting everything after it
        total, err = errors(prog, pos, rtl, kk)
        return sum(abs(b - a) for a, b in zip([0] + err, err)) + abs(total - cycles)

    best = cost(k)
    for _ in range(rounds):
        for key in keys:
            for d in (-512, -128, -32, -8, -4, -2, -1, 1, 2, 4, 8, 32, 128, 512):
                trial = dict(k, **{key: k[key] + d})
                c = cost(trial)
                if c < best:
                    best, k = c, trial
    return k, best


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("img", type=Path, help="image directory (tools/hdc_program_v41.py --out)")
    ap.add_argument("--pos", type=int, default=7)
    ap.add_argument("--calibrate", type=Path, help="Verilator +TRACE log of this image")
    ap.add_argument("--rtl-cycles", type=int)
    ap.add_argument("--sinkhorn-seq", action="store_true")
    a = ap.parse_args()
    prog = load_prog(a.img)
    if a.calibrate:
        rtl = parse_trace(a.calibrate.read_text())
        k, c = calibrate(prog, a.pos, rtl, a.rtl_cycles)
        total, err = errors(prog, a.pos, rtl, k)
        print(json.dumps(k))
        print(f"model {total} rtl {a.rtl_cycles} ({(total - a.rtl_cycles) / a.rtl_cycles:+.4%}); issue errors: "
              f"max |e| {max(map(abs, err))}, mean |e| {sum(map(abs, err)) / len(err):.1f}")
        return
    print(simulate(prog, a.pos, sinkhorn_seq=a.sinkhorn_seq))


if __name__ == "__main__":
    main()
