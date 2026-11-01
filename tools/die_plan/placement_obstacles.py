"""Physical content and split-core obstacles shared by G0 station checks and G2 probes."""

def probe_blockages(t, top="M7"):
    """Leaf obstructions of a partition probe.  A content leaf that the plan splits into planned hard cores
    (hard_cores[].inst == leaf inst, '<leaf inst>_*' or '<leaf inst>.<cut>', e.g. an over-cap bankq leaf -> 3 cores) is represented by
    those cores, not by the whole leaf outline: the space between the cores is glue / routing area of the partition.
    Every other content leaf with an outline is blocked as before."""
    cores = [h for h in t.get("hard_cores", []) if "origin_um" in h and "outline_um" in h]
    out, covered = [], set()
    for c in t.get("contents", []):
        if "origin_um" not in c or "outline_um" not in c:
            continue
        # split-core cuts are named '<leaf inst>_*' or '<leaf inst>.<cut>' (HBM u_hcb_Q7.<cut>, DIE-HBM-36 10-30)
        sub = [h for h in cores if h["inst"] == c["inst"] or h["inst"].startswith((c["inst"] + "_", c["inst"] + "."))]
        if sub:
            covered.update(h["inst"] for h in sub)
            out += [dict(h, obs_max=max(
                [L for L in (c.get("obs_max"), h.get("obs_max")) if L] or ["M5"],
                key=lambda L: int(L[1:]))) for h in sub]
        else:
            out.append(c)
    # KV-PLAN 10-25: a planned hard core that no content leaf names (e.g. KV head_eighth cores built from several
    # leaves) is still a hard obstruction of the partition; it used to be silently dropped (0 blockages -> optimistic
    # G2).  Its routing obstruction reaches the partition signal ceiling unless the core declares obs_max.
    for h in cores:
        if h["inst"] not in covered:
            out.append(dict(h, obs_max=h.get("obs_max", top)))
    return out

