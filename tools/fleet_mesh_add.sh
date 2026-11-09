#!/usr/bin/env bash
# FLEET-MESH-1 2026-11-09: add (or re-ensure) a host in the full fleet ssh mesh.
# usage (on localhost):  fleet_mesh_add.sh <alias> <ip> [cherry-name] [mux yes|no]
#   needs `ssh <alias>` to work from localhost first (onboarding adds the localhost block).
#   Adds the row to fleet_hosts.tsv, then on EVERY fleet host (append-only, .bak-mesh-MMDD backup
#   before the first edit): authorized_keys gets every other host's ubuntu id_ed25519.pub,
#   ~/.ssh/config gets a "# FLEET-MESH <alias>" block per peer. No private key leaves its host.
#   `fleet_mesh_add.sh --all` re-ensures the whole table.  Matrix: fleet_mesh_matrix.sh
set -u
D=$(dirname "$(readlink -f "$0")"); T=$D/fleet_hosts.tsv
SSH="ssh -o ControlPath=none -o ConnectTimeout=10 -o BatchMode=yes"
if [ "${1:-}" != "--all" ]; then
  a=${1:?alias}; ip=${2:?ip}; name=${3:-}; mux=${4:-yes}
  [ -n "$name" ] || name=$(timeout 30 $SSH -n "$a" hostname) || { echo "cannot reach $a from localhost"; exit 1; }
  awk -F'\t' -v a="$a" '$1==a{f=1} END{exit !f}' "$T" || printf '%s\t%s\t%s\t%s\n' "$a" "$name" "$ip" "$mux" >> "$T"
fi
mapfile -t ROWS < <(grep -v '^#' "$T" | grep .)
KEYS=""; rc=0
for r in "${ROWS[@]}"; do
  IFS=$'\t' read -r a n i m <<<"$r"
  k=$(timeout 60 $SSH -n "$a" 'set -e; umask 077; mkdir -p ~/.ssh
    if [ ! -f ~/.ssh/id_ed25519 ]; then ssh-keygen -q -t ed25519 -N "" -C "ubuntu@$(hostname)" -f ~/.ssh/id_ed25519 </dev/null; fi
    [ -f ~/.ssh/id_ed25519.pub ] || ssh-keygen -y -f ~/.ssh/id_ed25519 > ~/.ssh/id_ed25519.pub
    head -1 ~/.ssh/id_ed25519.pub') || { echo "KEY FAIL $a"; rc=1; continue; }
  case "$k" in ssh-ed25519\ *) KEYS+="$k"$'\n';; *) echo "BAD PUB $a"; rc=1;; esac
done
BAK=.bak-mesh-$(date +%m%d); NOW=$(date '+%Y-%m-%d %H:%M %Z')
for r in "${ROWS[@]}"; do
  IFS=$'\t' read -r self n i mux <<<"$r"
  PEERS=$(printf '%s\n' "${ROWS[@]}" | awk -F'\t' -v s="$self" '$1!=s')
  { printf 'SELF=%q BAK=%q NOW=%q MUX=%q\n' "$self" "$BAK" "$NOW" "$mux"
    printf 'KEYS=%q\nPEERS=%q\n' "$KEYS" "$PEERS"
    cat <<'REMOTE'
set -u; umask 077; cd ~/.ssh || exit 1
touch authorized_keys config; chmod 600 authorized_keys config
nl(){ [ -s "$1" ] && [ -n "$(tail -c1 "$1")" ] && echo >> "$1"; true; }
bk(){ [ -e "$1$BAK" ] || cp -p "$1" "$1$BAK"; }
ak0=$(wc -l < authorized_keys); cf0=$(wc -l < config)
while read -r k; do [ -n "$k" ] || continue
  b=$(echo "$k" | awk '{print $2}'); grep -qF "$b" authorized_keys && continue
  bk authorized_keys; nl authorized_keys; echo "$k" >> authorized_keys; done <<<"$KEYS"
while IFS=$'\t' read -r pa pn pi pm; do [ -n "$pa" ] || continue
  grep -qxF "# FLEET-MESH $pa" config && continue
  h="Host $pa $pn"; grep -qxF "$h" config && h="Host $pn $pa"
  bk config; nl config
  { echo "# FLEET-MESH $pa"; echo "$h"; echo "    HostName $pi"; echo "    User ubuntu"
    echo "    StrictHostKeyChecking accept-new"; echo "    ServerAliveInterval 30"; echo "    ConnectTimeout 10"
    if [ "$MUX" = yes ]; then echo "    ControlMaster auto"; echo "    ControlPath ~/.ssh/cm-%C"; echo "    ControlPersist 10m"; fi
  } >> config
  g=$(ssh -G "$pa" 2>/dev/null | awk '$1=="hostname"{print $2}'); [ "$g" = "$pi" ] || echo "WARN $SELF: $pa resolves to $g (earlier block), want $pi"
done <<<"$PEERS"
echo "$SELF authorized_keys $ak0->$(wc -l < authorized_keys) config $cf0->$(wc -l < config)"
REMOTE
  } | timeout 90 $SSH "$self" bash -s || { echo "APPLY FAIL $self"; rc=1; }
done
exit $rc
