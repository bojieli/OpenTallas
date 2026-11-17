#!/bin/bash
# Prospective HEI recipe: read-only signoff library receipt -> caller-owned staged receipt.
# Container scenes may leave a root-owned destination. Replace its directory entry atomically.
# Usage: bash hei_atomic_copy.sh SOURCE DESTINATION
set -euo pipefail
src=$1
dst=$2
tmp=$(mktemp "${dst}.tmp.XXXXXX")
trap 'rm -f -- "$tmp"' EXIT
cp --preserve=mode,timestamps -- "$src" "$tmp"
cmp -s -- "$src" "$tmp"
mv -fT -- "$tmp" "$dst"
trap - EXIT
printf 'HEI_ATOMIC_RECEIPT %s %s\n' "$(sha256sum -- "$dst" | cut -d' ' -f1)" "$dst"
