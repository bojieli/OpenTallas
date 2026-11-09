set -e
R=/srv/opentallas-scratch2/claude/kw35/repo
W=/srv/opentallas-scratch2/claude/kw36/wt_e
cd $R
if [ ! -d $W ]; then
  git worktree add -q --no-checkout -b claude/kw-fix-36-queue-src-1108 $W origin/main
  git -C $W sparse-checkout init --cone
  git -C $W sparse-checkout set tools physical/common_flow
  git -C $W checkout -q claude/kw-fix-36-queue-src-1108
fi
cd $W
python3 -I - <<'PY'
p="tools/autopilot/kit_wave.py"
s=open(p).read()
old='''        pinned = json.loads((Path(rec["dir"]) / "spec.json").read_text())
        src = pinned.get("queue_src") or ("main@" + pinned["src_sha"])
        if not pinned.get("queue_src") and not pinned.get("src_sha"):
            raise ValueError("launch spec has no source identity")
        retry = rec["item"] + "@" + str(rec["attempt"])
'''
new='''        pinned = json.loads((Path(rec["dir"]) / "spec.json").read_text())
        if not pinned.get("queue_src") and not pinned.get("src_sha"):
            raise ValueError("launch spec has no source identity")
        src = enqueue_src(AP, pinned, d)
        retry = rec["item"] + "@" + str(rec["attempt"])
'''
assert s.count(old)==1
s=s.replace(old,new)
old='''def enqueue_pass(AP, cfg, st, rec, notices):
'''
new='''# KW-FIX-36 11-08 (e): a kit generated from a composed source pins queue_src "a@s1+b@s2" (with or without spaces), which
# the queue refuses ("src must be branch@sha": hbm q_spb1, q_su01, q_su11__physical_v1, vsN2, sfu_programme_store_r10,
# kv3_io_cor).  The queue row needs ONE commit that is really the source, so a composition resolves to one only when
# that is provable; it is never guessed:
#   - die option queue_src_exact {composed queue_src: "branch@sha"}: the operator's published composition commit, or
#   - the spec's src_sha, when every part is an ancestor of it or changes only tools/autopilot/ (operational tools run
#     from the live autopilot checkout, not kit content; e.g. the providx fix on top of the HBM integration commit).
# Anything else stays a FLOW failure naming the part that is not in the commit.
SINGLE_SRC_RE = re.compile(r"^[A-Za-z0-9_./-]+@[0-9a-f]{7,40}$")      # autopilot.SRC_RE
COMPOSED_SRC_TOOL_PREFIX = "tools/autopilot/"
SRC_REFUSED = "enqueue rc 1: enqueue: REFUSED: src must be branch@sha"


def enqueue_src(AP, pinned, d):
    """the queue row's branch@sha for this launch spec (see above); ValueError when the source has no single commit"""
    qs = str(pinned.get("queue_src") or "").strip()
    if not qs:
        return "main@" + pinned["src_sha"]
    if SINGLE_SRC_RE.match(qs):
        return qs
    exact = (d.get("queue_src_exact") or {}).get(qs)
    if exact:
        if not SINGLE_SRC_RE.match(str(exact)):
            raise ValueError(f"queue_src_exact for {qs!r} is not branch@sha: {exact!r}")
        return str(exact)
    parts = [p for p in re.split(r"\\s*\\+\\s*", qs) if p]
    if len(parts) < 2 or not all(SINGLE_SRC_RE.match(p) for p in parts):
        raise ValueError(f"queue_src {qs!r} is neither branch@sha nor a composition a@sha+b@sha")
    sha = str(pinned.get("src_sha") or "")
    if not re.fullmatch(r"[0-9a-f]{7,40}", sha):
        raise ValueError(f"composed queue_src {qs!r} has no src_sha to resolve to")
    git = lambda *a: AP.sh(["git", "-C", str(AP.REPO), *a], timeout=120)
    if git("rev-parse", "-q", "--verify", sha + "^{commit}")[0]:
        raise ValueError(f"composed queue_src: src_sha {sha} is not a commit on the hub")
    for p in parts:
        psha = p.rsplit("@", 1)[1]
        if sha.startswith(psha) or psha.startswith(sha) or not git("merge-base", "--is-ancestor", psha, sha)[0]:
            continue
        rc, base, _ = git("merge-base", sha, psha)
        rc2, files, _ = git("diff", "--name-only", base.strip(), psha) if not rc and base.strip() else (1, "", "")
        names = files.split()
        if rc2 or not names or not all(n.startswith(COMPOSED_SRC_TOOL_PREFIX) for n in names):
            raise ValueError(f"composed queue_src: part {p} is not in src_sha {sha[:12]} and changes kit content; "
                             f"publish a composition commit and set die option queue_src_exact")
    label = next((p.rsplit("@", 1)[0] for p in parts if sha.startswith(p.rsplit("@", 1)[1])), "")
    if not label:
        rc, refs, _ = git("for-each-ref", "--contains", sha, "--count=1", "--format=%(refname:lstrip=3)", "refs/remotes/origin")
        label = refs.strip() if not rc and refs.strip() and refs.strip() != "HEAD" else parts[0].rsplit("@", 1)[0]
    return f"{label}@{sha}"


def enqueue_pass(AP, cfg, st, rec, notices):
'''
assert s.count(old)==1
s=s.replace(old,new)
old='''    n = 0
    for rec in (st.get("items") or {}).values():
        if not rec.get("kit") or not (rec.get("status") == "ROUTE-HELD" or
'''
new='''    n = 0
    for rec in (st.get("items") or {}).values():
        # KW-FIX-36 (e): the queue's grammar refusal was a tool bug, not a verdict on the kit: resend it through
        # enqueue_src.  A composition with no single commit then fails with its own reason and is not resent.
        if rec.get("kit") and rec.get("status") == "FAIL" and str(rec.get("reason") or "").startswith(SRC_REFUSED):
            rec.update(status="PASS", enqueue_pending=1, **{"class": ""}, updated=time.time())
        if not rec.get("kit") or not (rec.get("status") == "ROUTE-HELD" or
'''
assert s.count(old)==1
s=s.replace(old,new)
open(p,"w").write(s)
PY
sed -n 1,60p tools/autopilot/test_kit_wave_enqueue_retry.py | cut -c1-170
