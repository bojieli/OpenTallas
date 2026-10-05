#!/usr/bin/env bash
set -euo pipefail

OT_REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OT_TOOL_ROOT=${OPENTALLAS_TOOL_ROOT:-"${OT_REPO_ROOT}/.cache/ihp-model-tools"}
OT_SOURCE_ROOT=${OPENTALLAS_TOOL_SOURCE_ROOT:-"${OT_TOOL_ROOT}/sources"}
OT_BUILD_ROOT=${OPENTALLAS_TOOL_BUILD_ROOT:-"${OT_TOOL_ROOT}/build"}

OT_NGSPICE_URL=https://sourceforge.net/projects/ngspice/files/ng-spice-rework/old-releases/43/ngspice-43.tar.gz/download
OT_NGSPICE_SHA=14dd6a6f08531f2051c13ae63790a45708bd43f3e77886a6a84898c297b13699
OT_NGSPICE_ARCHIVE=${OT_SOURCE_ROOT}/ngspice-43.tar.gz
OT_NGSPICE_PREFIX=${OT_TOOL_ROOT}/ngspice-43-osdi

OT_LLVM_URL=https://openva.fra1.cdn.digitaloceanspaces.com/llvm-15.0.7-x86_64-unknown-linux-gnu.tar.zst
OT_LLVM_SHA=fec7009230510cbc9e745a7e2e1f51eb74b7dc7c2682760f338a87d7aa48820a
OT_LLVM_ARCHIVE=${OT_SOURCE_ROOT}/llvm-15.0.7-x86_64-unknown-linux-gnu.tar.zst
OT_LLVM_PREFIX=${OT_TOOL_ROOT}/llvm-15.0.7-openvaf

OT_OPENVAF_REPOSITORY=https://github.com/pascalkuthe/OpenVAF.git
OT_OPENVAF_TAG=OpenVAF-v23.5.0
OT_OPENVAF_COMMIT=d4079e776f4b54b23e158b7857c4e238e5cacd05
OT_OPENVAF_SOURCE=${OT_BUILD_ROOT}/openvaf-23.5.0
OT_OPENVAF_PREFIX=${OT_TOOL_ROOT}/openvaf-23.5.0-target-cpu-fix
OT_OPENVAF_PATCH=${OT_REPO_ROOT}/tools/patches/openvaf-23.5.0-target-cpu.patch

for OT_REQUIRED_COMMAND in curl git make sha256sum tar zstd rustup; do
    if ! command -v "${OT_REQUIRED_COMMAND}" >/dev/null 2>&1; then
        echo "required command is missing: ${OT_REQUIRED_COMMAND}" >&2
        exit 2
    fi
done

mkdir -p "${OT_SOURCE_ROOT}" "${OT_BUILD_ROOT}" "${OT_TOOL_ROOT}"

download_and_verify() {
    local OT_URL=$1
    local OT_OUTPUT=$2
    local OT_EXPECTED_SHA=$3
    if [[ ! -f "${OT_OUTPUT}" ]]; then
        curl --fail --location --retry 3 --output "${OT_OUTPUT}.part" "${OT_URL}"
        mv "${OT_OUTPUT}.part" "${OT_OUTPUT}"
    fi
    local OT_OBSERVED_SHA
    OT_OBSERVED_SHA=$(sha256sum "${OT_OUTPUT}" | awk '{print $1}')
    if [[ "${OT_OBSERVED_SHA}" != "${OT_EXPECTED_SHA}" ]]; then
        echo "archive hash mismatch for ${OT_OUTPUT}: ${OT_OBSERVED_SHA}" >&2
        exit 2
    fi
}

download_and_verify "${OT_NGSPICE_URL}" "${OT_NGSPICE_ARCHIVE}" "${OT_NGSPICE_SHA}"
if [[ ! -x "${OT_NGSPICE_PREFIX}/bin/ngspice" ]]; then
    OT_NGSPICE_UNPACK=$(mktemp -d)
    tar -xzf "${OT_NGSPICE_ARCHIVE}" -C "${OT_NGSPICE_UNPACK}"
    (
        cd "${OT_NGSPICE_UNPACK}/ngspice-43"
        ./configure \
            --prefix="${OT_NGSPICE_PREFIX}" \
            --enable-osdi \
            --with-x=no \
            --with-readline=yes
        make -j"$(nproc)"
        make install
    )
fi
OT_NGSPICE_BINARY_SHA=$(sha256sum "${OT_NGSPICE_PREFIX}/bin/ngspice" | awk '{print $1}')
if [[ "${OT_NGSPICE_BINARY_SHA}" != "ae32c8d9862d2b8611e133a7bf055dd6b1c5c760a208728456987b1eadd1f2d0" ]]; then
    echo "ngspice executable identity differs from the governed build: ${OT_NGSPICE_BINARY_SHA}" >&2
    exit 2
fi

download_and_verify "${OT_LLVM_URL}" "${OT_LLVM_ARCHIVE}" "${OT_LLVM_SHA}"
if [[ ! -x "${OT_LLVM_PREFIX}/bin/llvm-config" ]]; then
    OT_LLVM_UNPACK=$(mktemp -d)
    zstd --long=31 --decompress --stdout "${OT_LLVM_ARCHIVE}" | tar -xf - -C "${OT_LLVM_UNPACK}"
    mv "${OT_LLVM_UNPACK}/LLVM" "${OT_LLVM_PREFIX}"
fi

OT_CLANG_DRIVER=${OPENTALLAS_CLANG_15:-/usr/lib/llvm-15/bin/clang}
OT_LLD_DRIVER=${OPENTALLAS_LLD_15:-/usr/lib/llvm-15/bin/ld.lld}
if [[ ! -x "${OT_CLANG_DRIVER}" || ! -x "${OT_LLD_DRIVER}" ]]; then
    echo "matching Clang/LLD 15 drivers are required; set OPENTALLAS_CLANG_15 and OPENTALLAS_LLD_15" >&2
    exit 2
fi
if [[ "$(sha256sum "${OT_CLANG_DRIVER}" | awk '{print $1}')" != "22f8651e4eba296325daed391a432b11c3db82d8166da127ccb43b4f6f229e18" ]]; then
    echo "Clang 15 driver hash differs from the governed host tool" >&2
    exit 2
fi
if [[ "$(sha256sum "${OT_LLD_DRIVER}" | awk '{print $1}')" != "382a6b6fce4424a6bf4ec18b25ea37c8d606eaf7cfbea8c14396ade0500b9486" ]]; then
    echo "LLD 15 driver hash differs from the governed host tool" >&2
    exit 2
fi

OT_HOST_DRIVER_ROOT=${OT_TOOL_ROOT}/openvaf-build-host-llvm-15.0.7/bin
mkdir -p "${OT_HOST_DRIVER_ROOT}"
if [[ ! -e "${OT_HOST_DRIVER_ROOT}/clang-cl" ]]; then
    ln -s "${OT_CLANG_DRIVER}" "${OT_HOST_DRIVER_ROOT}/clang-cl"
fi
if [[ ! -e "${OT_HOST_DRIVER_ROOT}/ld.lld" ]]; then
    ln -s "${OT_LLD_DRIVER}" "${OT_HOST_DRIVER_ROOT}/ld.lld"
fi

if [[ ! -d "${OT_OPENVAF_SOURCE}/.git" ]]; then
    git clone --branch "${OT_OPENVAF_TAG}" --depth 1 "${OT_OPENVAF_REPOSITORY}" "${OT_OPENVAF_SOURCE}"
fi
OT_OPENVAF_OBSERVED=$(git -C "${OT_OPENVAF_SOURCE}" rev-parse HEAD)
if [[ "${OT_OPENVAF_OBSERVED}" != "${OT_OPENVAF_COMMIT}" ]]; then
    echo "OpenVAF source commit mismatch: ${OT_OPENVAF_OBSERVED}" >&2
    exit 2
fi
if git -C "${OT_OPENVAF_SOURCE}" apply --check "${OT_OPENVAF_PATCH}" >/dev/null 2>&1; then
    git -C "${OT_OPENVAF_SOURCE}" apply "${OT_OPENVAF_PATCH}"
elif ! git -C "${OT_OPENVAF_SOURCE}" apply --reverse --check "${OT_OPENVAF_PATCH}" >/dev/null 2>&1; then
    echo "OpenVAF source tree is neither pristine nor patched exactly as governed" >&2
    exit 2
fi

rustup toolchain install 1.64.0 --profile minimal
(
    cd "${OT_OPENVAF_SOURCE}"
    env \
        PATH="${OT_HOST_DRIVER_ROOT}:/usr/lib/llvm-15/bin:${PATH}" \
        LLVM_CONFIG="${OT_LLVM_PREFIX}/bin/llvm-config" \
        cargo +1.64.0 build --release --bin openvaf
)
mkdir -p "${OT_OPENVAF_PREFIX}/bin"
install -m 0755 "${OT_OPENVAF_SOURCE}/target/release/openvaf" "${OT_OPENVAF_PREFIX}/bin/openvaf"
OT_OPENVAF_BINARY_SHA=$(sha256sum "${OT_OPENVAF_PREFIX}/bin/openvaf" | awk '{print $1}')
if [[ "${OT_OPENVAF_BINARY_SHA}" != "1b4417e5faad179e3a3abe7eb6ef03f23f95edeb31bf2c5167ca74082a0c3fb3" ]]; then
    echo "patched OpenVAF executable identity differs from the governed build: ${OT_OPENVAF_BINARY_SHA}" >&2
    exit 2
fi

"${OT_NGSPICE_PREFIX}/bin/ngspice" --version
"${OT_OPENVAF_PREFIX}/bin/openvaf" --version
