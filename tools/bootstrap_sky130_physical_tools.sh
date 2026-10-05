#!/usr/bin/env bash
set -euo pipefail

OT_REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OT_BUILD_ROOT=${OPENTALLAS_TOOL_BUILD_ROOT:-"${OT_REPO_ROOT}/.cache/physical-tool-build"}
OT_INSTALL_ROOT=${OPENTALLAS_TOOL_ROOT:-"${OT_REPO_ROOT}/.cache/physical-tools"}
OT_MAGIC_COMMIT=17ac06a24a952380ade3a7d33cd2f0c3943dfc12
OT_NETGEN_TAG=1.5.322
OT_NETGEN_COMMIT=5e48c4e8762d7b58e296b59392572633ba9b184d

mkdir -p "${OT_BUILD_ROOT}" "${OT_INSTALL_ROOT}"

if [[ ! -d "${OT_BUILD_ROOT}/magic/.git" ]]; then
    git clone --filter=blob:none https://github.com/RTimothyEdwards/magic.git "${OT_BUILD_ROOT}/magic"
fi
git -C "${OT_BUILD_ROOT}/magic" fetch origin "${OT_MAGIC_COMMIT}"
git -C "${OT_BUILD_ROOT}/magic" checkout --detach "${OT_MAGIC_COMMIT}"
(
    cd "${OT_BUILD_ROOT}/magic"
    ./configure --prefix="${OT_INSTALL_ROOT}/magic-${OT_MAGIC_COMMIT:0:7}"
    make -j"$(nproc)"
    make install
)

if [[ ! -d "${OT_BUILD_ROOT}/netgen/.git" ]]; then
    git clone --filter=blob:none https://github.com/RTimothyEdwards/netgen.git "${OT_BUILD_ROOT}/netgen"
fi
git -C "${OT_BUILD_ROOT}/netgen" fetch origin "refs/tags/${OT_NETGEN_TAG}"
git -C "${OT_BUILD_ROOT}/netgen" checkout --detach "${OT_NETGEN_COMMIT}"
(
    cd "${OT_BUILD_ROOT}/netgen"
    ./configure --prefix="${OT_INSTALL_ROOT}/netgen-${OT_NETGEN_TAG}"
    make -j"$(nproc)"
    make install
)

"${OT_INSTALL_ROOT}/magic-${OT_MAGIC_COMMIT:0:7}/bin/magic" --version
"${OT_INSTALL_ROOT}/netgen-${OT_NETGEN_TAG}/bin/netgen" -batch quit
