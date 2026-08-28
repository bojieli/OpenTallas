#!/usr/bin/env bash
set -euo pipefail

OT_REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OT_PDK_DEST=${OPENTALLAS_PDK_ROOT:-"${OT_REPO_ROOT}/.cache/pdk-root"}
OT_PDK_RELEASE=f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7
OT_CIEL_VERSION=2.6.1
OT_DATA_SOURCE=static-web:https://fossi-foundation.github.io/ciel-releases

if ! command -v ciel >/dev/null 2>&1; then
    echo "ciel ${OT_CIEL_VERSION} is required; install the pinned version before running this bootstrap" >&2
    exit 2
fi

OT_CIEL_OBSERVED=$(ciel --version | awk '{print $NF}')
if [[ "${OT_CIEL_OBSERVED}" != "${OT_CIEL_VERSION}" ]]; then
    echo "ciel ${OT_CIEL_VERSION} required, found ${OT_CIEL_OBSERVED}" >&2
    exit 2
fi

mkdir -p "${OT_PDK_DEST}"
ciel enable \
    --data-source "${OT_DATA_SOURCE}" \
    --pdk-root "${OT_PDK_DEST}" \
    --pdk-family sky130 \
    --include-libraries sky130_fd_pr \
    "${OT_PDK_RELEASE}"

python3 "${OT_REPO_ROOT}/tools/verify_sky130_pdk.py" "${OT_PDK_DEST}/sky130A"
