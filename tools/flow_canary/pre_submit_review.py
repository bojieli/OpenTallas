"""Exact source-plan review for unattended native type canaries."""
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "autopilot"))
import plan_visual_review as PVR

TYPE_ROUTE = "bash {gen}/run_kit.sh {kit} route {mem} {cpus}"
VALUE = re.compile(r"[0-9]+(?:\.[0-9]+)?\Z")
BLOB = re.compile(r"[0-9a-f]{40,64}\Z")


def standard_recipe(spec):
    """Recognize generators whose plan and physical recipe can be sealed here."""
    die, item = spec.get("die"), spec.get("item")
    if (die not in PVR.DIES or spec.get("flow") != "type" or not item
            or spec.get("run") != TYPE_ROUTE or spec.get("kit") != "{gen}/{item}"
            or spec.get("gen_cwd", "{src}") != "{src}"
            or any(spec.get(key) for key in ("vars", "prep", "gen_env"))):
        raise ValueError("unsupported exact pre-submit plan recipe")
    plan = f"physical/die_plan/{die}/die_plan.json"
    args = shlex.split(spec["gen"])
    prefix = ["python3", "-I", "tools/die_plan/gen.py", "phys", plan, "--out", "{gen}",
              "--types", "{item}", "--rtl-root", "{src}"]
    flags = args[len(prefix):]
    if args[:len(prefix)] != prefix or len(flags) % 2 or any(
        flag not in ("--hold-ff-margin", "--max-wire-um") or not VALUE.fullmatch(value)
        for flag, value in zip(flags[::2], flags[1::2])
    ):
        raise ValueError("unsupported exact pre-submit plan recipe")
    return plan, args


def materialize_plan(repo, rev, rel, requests):
    """Export only the pinned plan blob. A waiting review needs no source checkout."""
    blob = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", f"{rev}:{rel}"],
                          check=True, text=True, capture_output=True, timeout=30).stdout.strip()
    if not BLOB.fullmatch(blob):
        raise ValueError("cannot identify pinned plan blob")
    final = requests / "plans" / f"{blob}.json"
    if final.is_file():
        return final
    final.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=final.parent, prefix=".plan-", delete=False) as stream:
        tmp = Path(stream.name)
        try:
            subprocess.run(["git", "-C", str(repo), "cat-file", "blob", blob], stdout=stream,
                           stderr=subprocess.PIPE, check=True, timeout=60)
            stream.flush()
            tmp.chmod(0o444)
            os.replace(tmp, final)
        finally:
            tmp.unlink(missing_ok=True)
    return final


def ledger():
    try:
        return PVR.read_ledger(os.environ.get("OT_HUB_NAME", "intel2"))
    except (OSError, ValueError, subprocess.SubprocessError):
        return ""


def hold(spec, source, revision, root, image, reviews, *, staged=False):
    """Return a launch hold, or empty if the exact plan and recipe were approved."""
    try:
        rel, args = standard_recipe(spec)
        requests = Path(root).resolve().parent / "plan_visual_requests"
        plan = Path(source) / rel if staged else materialize_plan(source, revision, rel, requests)
        # The image and generator invocation are part of the reviewed form. Source
        # revision labels are evidence, so a byte-identical copied plan/recipe can reuse review.
        candidate = PVR.request({"die": spec["die"], "item": spec["item"], "plan": str(plan),
                                 "gen_args": args + [f"canary_image={image}", f"canary_top={spec['top']}"]})
        verdict = PVR.verdict(reviews, candidate)
        if verdict == "GOOD":
            return ""
        request = requests / spec["die"] / "plan_visual_request.json"
        if not staged:
            # Preserve the pre-checkout immutable plan path in the review request.
            PVR.write_request(request, dict(candidate, source_revision=revision, source_plan=rel,
                                            generator=args, image=image, top=spec["top"]))
        return f"WAIT-PLAN-VISUAL: {verdict or 'missing'} for form {candidate['form_sha256']}; request {request}"
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        return f"WAIT-PLAN-VISUAL: {exc}"
