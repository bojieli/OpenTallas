#!/usr/bin/env bash
set -euo pipefail

OT_REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OT_IHP_REPOSITORY=https://github.com/IHP-GmbH/IHP-Open-PDK.git
OT_IHP_RELEASE=v0.3.0
OT_IHP_COMMIT=5cccb161f7492697cfa52eb14dc03beb00bdca9e
OT_IHP_DEST=${OPENTALLAS_IHP_PDK_ROOT:-"${OT_REPO_ROOT}/.cache/ihp-open-pdk-v0.3.0"}

if [[ ! -e "${OT_IHP_DEST}" ]]; then
    git clone \
        --branch "${OT_IHP_RELEASE}" \
        --depth 1 \
        --filter=blob:none \
        --recurse-submodules \
        --shallow-submodules \
        "${OT_IHP_REPOSITORY}" \
        "${OT_IHP_DEST}"
elif [[ ! -d "${OT_IHP_DEST}/.git" ]]; then
    echo "IHP destination exists but is not a Git checkout: ${OT_IHP_DEST}" >&2
    exit 2
fi

OT_IHP_OBSERVED=$(git -C "${OT_IHP_DEST}" rev-parse HEAD)
if [[ "${OT_IHP_OBSERVED}" != "${OT_IHP_COMMIT}" ]]; then
    echo "IHP ${OT_IHP_COMMIT} required, found ${OT_IHP_OBSERVED}; refusing to replace the checkout" >&2
    exit 2
fi

git -C "${OT_IHP_DEST}" submodule update --init --recursive --depth 1
python3 "${OT_REPO_ROOT}/tools/verify_ihp_pdk.py" "${OT_IHP_DEST}"
