#!/usr/bin/env python3
"""Stimulus generator for tb_qwen_typed_witness_control (WTN1 finite FF controller).

Reads the concrete 1024-word PW image (witness PW400..438, digest 198f7708b478a667),
decodes the 13 sealed templates (114 typed SU witnesses), and emits a nominal
four-context overlapped schedule plus single-fault mutants. Source vehicle only.
"""
import argparse, json, os

DIGEST = 0x198f7708b478a667
EPOCH = 7
HDR = 0x57544e3101640340


def decode(words):
    recs = []
    for r in range(13):
        a, b, c = words[400 + 3 * r:403 + 3 * r]
        rw = a | (b << 64) | ((c & 63) << 128)
        assert (c >> 6) == ((HDR >> 6) if r == 0 else 0)
        base, pc, mask, idx = rw & 0x1fff, (rw >> 13) & 0x7f, (rw >> 22) & 0xfff, rw >> 130
        assert idx == r and (rw >> 20) & 3 == 0 and mask
        ev = [(base + ((rw >> (34 + 8 * s)) & 0xff), s, pc) for s in range(12) if mask >> s & 1]
        recs.append(dict(base=base, pc=pc, mask=mask, events=ev))
    return recs


def schedule(recs):
    dues = sorted(d for r in recs for d, _, _ in r["events"])
    offs = [0]
    while len(offs) < 4:
        o = offs[-1] + 1
        while True:
            used = {x + oo for oo in offs for x in dues}
            if not any(x + o in used for x in dues):
                break
            o += 1
        offs.append(o)
    return offs, max(dues)


def build(words, recs, mut=None):
    L = []  # (edge, kind, a, b, c, d, e)
    add = lambda t, k, a=0, b=0, c=0, d=0, e=0: L.append([t, k, a, b, c, d, e])
    dig, ep, fc = DIGEST, EPOCH, 1
    if mut == "digest":
        dig ^= 1
    if mut == "profile_epoch":
        ep = 8
    add(2, 2, dig >> 32, dig & 0xffffffff, ep, fc)
    w = list(words)
    if mut == "header":
        w[402] ^= 1 << 40
    if mut == "zero_mask":
        w[403 + 3 * 2] &= ~(0xfff << 22)
    if mut == "nonzero_pad":
        w[400] |= 1 << 20
    pws = list(range(1024))
    if mut == "skip_pw":
        pws.remove(410)
    if mut == "dup_pw":
        pws.insert(pws.index(406), 405)
    t = 10
    for i in pws:
        add(t, 0, i, w[i] >> 32, w[i] & 0xffffffff)
        if mut == "early_auth" and i == 420:
            add(t, 1, 1)
        t += 1
    add(1040, 1, 1)
    offs, last = schedule(recs)
    S0 = 1100
    if mut == "start_before_seal":
        S0 = 1000
    retire_edges = []
    sched = []  # (user, start, stage, epoch, retire_delay)
    for u in range(4):
        sched.append((u, S0 + offs[u], 1 + 9 * u, 0x100 + u, last + 10 + (20000 if u == 3 else 0)))
    r0 = sched[0][1] + sched[0][4]
    sched.append((0, r0 + 3, 5, 0x200, last + 10))  # context reuse after retirement
    for k, (u, s, st, epo, rd) in enumerate(sched):
        stg = st
        if mut == "bad_stage" and k == 1:
            stg = 37
        add(s, 3, u, stg, epo)
        if mut == "double_start" and k == 1:
            add(s + 50, 3, u, stg, epo)
        evs = sorted((d, sl, pc) for r in recs for d, sl, pc in r["events"])
        for j, (d, sl, pc) in enumerate(evs):
            eu, esl, epc, est, eep, et = u, sl, (u << 7) | pc, st, epo, s + d
            if k == 1 and j == 40:
                if mut == "missing":
                    continue
                if mut == "late":
                    et += 1
                if mut == "early":
                    et -= 1
                if mut == "wrong_user":
                    eu = (u + 1) & 3
                    epc = (eu << 7) | pc
                if mut == "wrong_slice":
                    esl = (sl + 1) % 12
                if mut == "wrong_stage":
                    est = st + 1
                if mut == "wrong_epoch":
                    eep = epo ^ 1
                if mut == "wrong_pidx":
                    epc ^= 1
                if mut == "duplicate":
                    add(et + 1 if et + 1 - s not in {x for x, _, _ in evs} else et + 2, 4, eu, esl, epc, est, eep)
                if mut == "observer_slice":
                    esl = 12
            add(et, 4, eu, esl, epc, est, eep)
        rt = s + rd
        if mut == "retire_early" and k == 1:
            rt = s + 3000
        add(rt, 5, u, 0 if (mut == "retire_no_mexpf" and k == 1) else 1)
        if mut == "stray_after_complete" and k == 1:
            add(s + last + 5, 4, u, 0, (u << 7), st, epo)
        retire_edges.append(rt)
    end = max(retire_edges) + 20
    if mut == "auth_drop_active":
        add(S0 + 200, 1, 0)
    if mut == "pw_while_active":
        add(S0 + 300, 0, 0, 0, 0)
    if mut == "auth_drop_idle":
        # Drop authentication while idle (between seal and first start), restore it:
        # the template must be invalidated, so the later start faults.
        add(1060, 1, 0)
        add(1070, 1, 1)
    add(end, 9)
    L.sort(key=lambda x: (x[0], x[1] == 9))
    return L, offs


MUTANTS = ["missing", "late", "early", "duplicate", "wrong_user", "wrong_slice", "wrong_stage",
           "wrong_epoch", "wrong_pidx", "retire_early", "retire_no_mexpf", "digest", "profile_epoch",
           "header", "zero_mask", "nonzero_pad", "skip_pw", "dup_pw", "early_auth", "auth_drop_active",
           "pw_while_active", "start_before_seal", "double_start", "bad_stage", "stray_after_complete",
           "auth_drop_idle", "observer_slice"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pw", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    words = [int(x, 16) for x in open(a.pw).read().split()]
    assert len(words) == 1024
    recs = decode(words)
    os.makedirs(a.out, exist_ok=True)
    meta = {"records": len(recs), "witnesses": sum(len(r["events"]) for r in recs), "mutants": MUTANTS}
    for m in [None] + MUTANTS:
        L, offs = build(words, recs, m)
        with open(os.path.join(a.out, f"stim_{m or 'nominal'}.txt"), "w") as f:
            for x in L:
                f.write("%d %d %x %x %x %x %x\n" % tuple(x))
    meta["user_offsets"] = offs
    meta["nominal_expect"] = {"completions": 13 * 5, "retired": 5, "starts": 5}
    json.dump(meta, open(os.path.join(a.out, "vectors.json"), "w"), indent=1)
    print("TWC_VECTORS", meta["witnesses"], "witnesses offsets", offs, "mutants", len(MUTANTS))


if __name__ == "__main__":
    main()
