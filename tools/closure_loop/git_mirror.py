"""Host-side git mirror for closure-loop source syncs (GITMIRROR, drive-1010 2026-10-10).

The legacy sync streams `git archive | gzip` (~373 MB) from the coordinator to every run; on the lossy
localhost -> ot-epyc3 path (190 ms RTT, 20-40 % loss, <200 KB/s up) one sync took ~30 min.  A host whose
hosts.json entry names a seeded bare mirror ("git_mirror", marker file CL_READY) instead:

  1. probe: the mirror is ready; optionally fetch the job's branch from the public upstream
     ("git_mirror_upstream", host -> GitHub, fast); report whether the pinned commit is already present;
  2. push: if absent, `git push <full>:refs/cl/<full>` over a fresh direct ssh connection (the caller holds the
     host's bulk lease) -- only objects the mirror lacks travel;
  3. extract: `git archive` on the host into a staging dir, verify (receipt jobs: archive sha256 and every
     required_files sha256 must equal the locally built receipt), then merge into {run}/src.  {run}/src is not
     touched until the staging tree is complete and verified, so a failure leaves it for the tar fallback.
  4. housekeep (detached, once a day): drop refs/cl/* older than KEEP_DAYS beyond the KEEP_MIN newest, gc --auto.

Every function here only builds commands / scripts; closure_loop.sync_source runs them and falls back to the
tar transfer on any failure.
"""
import re
import shlex

REF_PREFIX = "refs/cl/"
KEEP_DAYS = 14
KEEP_MIN = 20       # newest refs/cl/* always kept: push negotiation needs advertised tips the coordinator knows
READY_MARK = "CL_READY"
UPSTREAM_FETCH_S = 300
q = shlex.quote


def config(cfg):
    """(mirror path, upstream url or None) of a hosts.json entry, or None when the host has no mirror"""
    path = (cfg or {}).get("git_mirror")
    if not path or not str(path).startswith("/"):
        return None
    return str(path), (cfg.get("git_mirror_upstream") or None)


def probe_script(mirror, full, branch=None, upstream=None):
    """stdout MIRROR_READY when the mirror is seeded, then MIRROR_HAVE when it already holds full (ref pinned)"""
    m = q(mirror)
    s = [f"M={m}", f'test -f "$M"/{READY_MARK} && git --git-dir="$M" rev-parse --git-dir >/dev/null 2>&1 || exit 0',
         "echo MIRROR_READY"]
    if upstream and branch:
        ref = f"refs/heads/{branch}"
        s.append(f'GIT_TERMINAL_PROMPT=0 timeout {UPSTREAM_FETCH_S} git --git-dir="$M" fetch -q --no-tags '
                 f'{q(upstream)} {q("+" + ref + ":" + ref)} >/dev/null 2>&1 || echo MIRROR_UPSTREAM_FAIL')
    s.append(f'if git --git-dir="$M" cat-file -e {full}^{{commit}} 2>/dev/null; then '
             f'git --git-dir="$M" update-ref {REF_PREFIX}{full} {full} && echo MIRROR_HAVE; fi')
    return "\n".join(s) + "\n"


def push_command(repo, host, mirror, full, ssh_prefix, local=False):
    """(argv, env additions) pushing full to the mirror.  ssh_prefix is ssh_transport.direct_command(host) (its last
    element the host); git appends host + the receive-pack command itself.  Local hooks are off (the shared checkout's
    git-lfs pre-push would try to upload LFS objects to the mirror)."""
    argv = ["git", "-c", "core.hooksPath=/dev/null", "-C", str(repo), "push", "--progress", "--no-verify",
            mirror if local else f"ssh://{host}{mirror}", f"{full}:{REF_PREFIX}{full}"]
    if local:
        return argv, {}
    if not ssh_prefix or ssh_prefix[-1] != host:
        raise ValueError(f"unexpected ssh prefix for {host}: {ssh_prefix!r}")
    return argv, {"GIT_SSH_COMMAND": shlex.join(ssh_prefix[:-1]), "GIT_SSH_VARIANT": "ssh", "GIT_TERMINAL_PROMPT": "0"}


def pushed_objects(stderr):
    """objects written by a push (0 when it sent no pack)"""
    m = re.findall(r"Writing objects:\s+100% \((\d+)/\d+\)", stderr or "")
    return int(m[-1]) if m else 0


def extract_script(mirror, full, paths, run, receipt=None):
    """archive full from the mirror into a staging dir, verify, merge into {run}/src; prints GIT_MIRROR_EXTRACTED.
    receipt (source_archive.build_archive): the archive is built with --literal-pathspecs over receipt['paths'] and
    must hash to receipt['archive_sha256']; each required file must hash to its receipt pin (exit 3 on mismatch)."""
    if receipt is not None:
        if receipt.get("commit") != full:
            raise ValueError("receipt commit differs from the synced commit")
        paths = receipt["paths"]
    for p in paths:
        if "\n" in p or not p:
            raise ValueError(f"bad archive path {p!r}")
    lit = " --literal-pathspecs" if receipt is not None else ""
    s = ["set -euo pipefail", f"M={q(mirror)}", f"RUN={q(run)}", 'S="$RUN/.src-mirror.$$"', 'T="$S.tar"',
         "trap 'rm -rf \"$S\" \"$T\"' EXIT", 'rm -rf "$S"', 'mkdir -p "$S" "$RUN/src"',
         f'git{lit} --git-dir="$M" archive --format=tar {full} -- {" ".join(q(p) for p in paths)} > "$T"']
    if receipt is not None:
        s.append(f'got=$(sha256sum < "$T" | cut -d" " -f1); [ "$got" = {q(receipt["archive_sha256"])} ] || '
                 '{ echo "GIT_MIRROR_RECEIPT_MISMATCH archive $got" >&2; exit 3; }')
    s.append('tar -xf "$T" -C "$S"')
    if receipt is not None:
        pins = receipt.get("required_sha256") or {}
        if not pins:
            raise ValueError("receipt without required_sha256")
        lines = "".join(f"{h}  {p}\n" for p, h in sorted(pins.items()))
        s.append(f"( cd \"$S\" && sha256sum -c --quiet --strict ) <<'OT_PINS' || "
                 "{ echo GIT_MIRROR_RECEIPT_MISMATCH required_files >&2; exit 3; }\n" + lines + "OT_PINS")
    # src untouched until here; a fresh (empty) src is replaced by a rename, a resumed one gets the files copied over
    s.append('if [ -z "$(ls -A "$RUN/src")" ]; then rmdir "$RUN/src" && mv "$S" "$RUN/src"; '
             'else cp -a "$S/." "$RUN/src/"; fi')
    s.append("echo GIT_MIRROR_EXTRACTED")
    return "\n".join(s) + "\n"


def housekeep_script(mirror, keep_days=KEEP_DAYS, keep_min=KEEP_MIN):
    """at most once a day per mirror: delete refs/cl/* whose commit is older than keep_days (the keep_min newest
    stay), then gc --auto.  Unreferenced objects go with git's default prune expiry, so a concurrent archive of a
    just-dropped ref still finds its objects."""
    return "\n".join([
        f"M={q(mirror)}", 'exec 9>>"$M/CL_GC.lock"', "flock -n 9 || exit 0",
        '[ -n "$(find "$M/CL_GC_STAMP" -mmin -1440 2>/dev/null)" ] && exit 0', 'touch "$M/CL_GC_STAMP"',
        f"cut=$(( $(date +%s) - {int(keep_days)} * 86400 ))",
        f"git --git-dir=\"$M\" for-each-ref --sort=-committerdate --format='%(committerdate:unix) %(refname)' "
        f"{REF_PREFIX} | awk -v c=$cut -v k={int(keep_min)} 'NR>k && $1<c {{print \"delete \" $2}}' | "
        'git --git-dir="$M" update-ref --stdin',
        'git --git-dir="$M" gc --auto --quiet']) + "\n"


def detached(script):
    """remote command line running script in the background, detached from the ssh session"""
    return f"nohup setsid bash -c {q(script)} >/dev/null 2>&1 </dev/null &"
