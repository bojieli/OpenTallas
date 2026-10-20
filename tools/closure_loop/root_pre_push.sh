#!/bin/sh
# ROOT-RULETAG 2026-10-19: pre-push check for pushes to refs/heads/main (installed as the shared .git/hooks/pre-push;
# ROOT agents may also run it by hand:  printf 'x HEAD_SHA refs/heads/main OLD_SHA\n' | tools/closure_loop/root_pre_push.sh).
# Runs tools/closure_loop/gate_rule_guard.py FROM THE PUSHED TIP (git show, python -I, temp dir) on TIP ^OLD:
# a commit changing a gate / daemon-overlay helper without a Gate-Rule trailer or RULE_COMMITS entry refuses the push.
# Then chains git-lfs pre-push (the hook this replaced).  OT_GATE_RULE_GUARD=off skips the guard (owner emergencies only).
remote="$1"
url="$2"
input=$(cat)
rc=0
if [ "${OT_GATE_RULE_GUARD:-}" != "off" ]; then
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/ot-grg.XXXXXX") || exit 2
  printf '%s\n' "$input" | while read -r lref lsha rref rsha; do
    [ "$rref" = "refs/heads/main" ] || continue
    case "$lsha" in 0000000000000000000000000000000000000000|"") continue;; esac
    base="$rsha"
    case "$rsha" in 0000000000000000000000000000000000000000|"") base="refs/remotes/origin/main";; esac
    git cat-file -e "$base^{commit}" 2>/dev/null || base="refs/remotes/origin/main"
    mkdir -p "$tmp/$lsha"
    if ! git show "$lsha:tools/closure_loop/gate_rule_guard.py" > "$tmp/$lsha/gate_rule_guard.py" 2>/dev/null ||
       ! git show "$lsha:tools/closure_loop/helper_overlay.py" > "$tmp/$lsha/helper_overlay.py" 2>/dev/null; then
      echo "root_pre_push: pushed tip $lsha has no gate_rule_guard.py; guard skipped" >&2
      continue
    fi
    python3 -I "$tmp/$lsha/gate_rule_guard.py" --repo "$(pwd)" --base "$base" --tip "$lsha" ||
      { echo "root_pre_push: push to main REFUSED by gate_rule_guard" >&2; exit 1; }
  done
  rc=$?
  rm -rf "$tmp"
fi
[ "$rc" -eq 0 ] || exit "$rc"
if command -v git-lfs >/dev/null 2>&1; then
  printf '%s\n' "$input" | git lfs pre-push "$remote" "$url"
else
  printf >&2 "\nThis repository is configured for Git LFS but 'git-lfs' was not found on your path.\n"; exit 2
fi
