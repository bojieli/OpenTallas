#!/bin/bash
# Install the Verilator NBA-loop guard as the fleet's bin/verilator (idempotent; atomic swap).
#   install_verilator_nba_guard.sh [VERILATOR_ROOT]   (default ~/.local/opentallas-tools/verilator-5.050)
# The original perl front end becomes bin/verilator.real; bin/verilator runs it unchanged and then
# refuses (exit 86) any generated model with the in-place NBA-loop miscompile (tools/verilator_nba_guard.py).
# Source of truth is main; re-run after either guard file changes. Uninstall: mv bin/verilator.real bin/verilator.
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
root=${1:-$HOME/.local/opentallas-tools/verilator-5.050}
bin=$root/bin; share=$root/share/ot_nba_guard
[ -x "$bin/verilator_bin" ] || { echo "no Verilator install at $root" >&2; exit 2; }
mkdir -p "$share"
for f in verilator_nba_guard.py verilator_guarded.py; do install -m 0644 "$here/$f" "$share/$f.tmp"; mv -f "$share/$f.tmp" "$share/$f"; done
if [ ! -e "$bin/verilator.real" ]; then
  head -1 "$bin/verilator" | grep -q perl || { echo "bin/verilator is not the perl front end; refusing" >&2; exit 3; }
  cp -p "$bin/verilator" "$bin/verilator.real"
fi
cat > "$bin/verilator.guard.tmp" <<SHIM
#!/bin/sh
# OpenTallas NBA-loop guard shim (tools/fleet/install_verilator_nba_guard.sh). Real front end: verilator.real
OT_VERILATOR_REAL="$bin/verilator.real" exec python3 -I "$share/verilator_guarded.py" "\$@"
SHIM
chmod 0755 "$bin/verilator.guard.tmp"; mv -f "$bin/verilator.guard.tmp" "$bin/verilator"
sha=$(cat "$share/verilator_nba_guard.py" "$share/verilator_guarded.py" | sha256sum | cut -c1-16)
echo "installed NBA guard on $(hostname) root=$root guard_sha=$sha"
