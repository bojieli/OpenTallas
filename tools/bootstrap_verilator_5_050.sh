#!/usr/bin/env bash
set -euo pipefail

# Build the timed-SystemVerilog simulator used by the canonical fault campaign.
# The Ubuntu Verilator 4.x package cannot execute these timed benches, so the
# public source revision is pinned independently of the host package manager.
readonly OPENTALLAS_VERILATOR_VERSION="5.050"
readonly OPENTALLAS_VERILATOR_COMMIT="848d926ebd4addacacd294dc84e35d9d4ae8078c"
readonly OPENTALLAS_VERILATOR_REPOSITORY="https://github.com/verilator/verilator.git"

tool_base="${OPENTALLAS_TOOL_ROOT:-${HOME}/.local/opentallas-tools}"
install_prefix="${OPENTALLAS_VERILATOR_PREFIX:-${tool_base}/verilator-${OPENTALLAS_VERILATOR_VERSION}}"
build_jobs="${OPENTALLAS_BUILD_JOBS:-$(nproc)}"

missing_tools=()
for required_tool in autoconf bison flex g++ git help2man make perl python3; do
    if ! command -v "${required_tool}" >/dev/null 2>&1; then
        missing_tools+=("${required_tool}")
    fi
done
if (( ${#missing_tools[@]} != 0 )); then
    echo "missing Verilator build dependencies: ${missing_tools[*]}" >&2
    echo "install the corresponding public distribution packages and rerun" >&2
    exit 2
fi

build_root="$(mktemp -d /tmp/opentallas-verilator-XXXXXXXX)"
cleanup() {
    if [[ -n "${build_root:-}" && "${build_root}" == /tmp/opentallas-verilator-* ]]; then
        rm -rf -- "${build_root}"
    fi
}
trap cleanup EXIT

source_dir="${build_root}/verilator"
git init -q "${source_dir}"
git -C "${source_dir}" remote add origin "${OPENTALLAS_VERILATOR_REPOSITORY}"
git -C "${source_dir}" fetch -q --depth 1 origin "${OPENTALLAS_VERILATOR_COMMIT}"
git -C "${source_dir}" checkout -q --detach FETCH_HEAD

resolved_commit="$(git -C "${source_dir}" rev-parse HEAD)"
if [[ "${resolved_commit}" != "${OPENTALLAS_VERILATOR_COMMIT}" ]]; then
    echo "Verilator source identity mismatch: ${resolved_commit}" >&2
    exit 1
fi

unset VERILATOR_ROOT || true
(
    cd "${source_dir}"
    autoconf
    ./configure --prefix="${install_prefix}"
    make -j"${build_jobs}"
    make install
)

installed_binary="${install_prefix}/bin/verilator"
"${installed_binary}" --version
sha256sum "${installed_binary}"
echo "installed pinned Verilator at ${installed_binary}"
