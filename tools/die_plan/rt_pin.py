"""rt_pin: resolve rt/current to rt/<sha> ONCE and use that sha for a whole gate run (FLOW-NOADV-R3 11-20, COORD / FABLE-FLOW-1800).

KV D26 R3b's G0 / bind / LATCHECK gate ran for hours while rt/current moved 5 times (tools refreshes), so its steps mixed tool trees.
A gate script starts with   eval "$(python3 -I <rt>/tools/die_plan/rt_pin.py --export)"   and every later step (bind_rowcheck TOOLSTALE,
plan_gate_pre --ref-tools auto, publish_apply precheck, kit_flow_refresh) reads $OT_RT_CURRENT, which now names the sha directory.
python3 -I rt_pin.py prints the pinned path.  An explicit $OT_RT_CURRENT is kept (resolved to its real path)."""
import os
import sys

ROOTS = tuple(f"/srv/opentallas-scratch{n}/claude/rt" for n in ("2", "", "3"))


def resolve(env=None, roots=ROOTS):
    """the real path (rt/<sha>) of $OT_RT_CURRENT, else of the first rt/current that exists; None when there is none"""
    env = os.environ if env is None else env
    cands = [env.get("OT_RT_CURRENT")] + [os.path.join(r, "current") for r in roots]
    for c in cands:
        if c and os.path.isdir(os.path.join(c, "tools")):
            return os.path.realpath(c)
    return None


def pin(env=None, roots=ROOTS):
    """resolve once and write the real path back to $OT_RT_CURRENT so every child process and later call reuses it"""
    env = os.environ if env is None else env
    p = resolve(env, roots)
    if p:
        env["OT_RT_CURRENT"] = p
    return p


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    p = pin()
    if not p:
        sys.exit("rt_pin: no rt/current found")
    print(f"export OT_RT_CURRENT={p}" if argv == ["--export"] else p)


if __name__ == "__main__":
    main()
