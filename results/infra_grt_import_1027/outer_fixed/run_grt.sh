#!/bin/bash
# Launch with ot-run; stage this out dir, kit, and the exact infrastructure ODB path.
D=$(cd $(dirname $0) && pwd); K=/srv/opentallas-scratch2/claude/codex-infra-grt-smoke-1027/kit; PRE=/srv/opentallas-scratch2/claude/codex-infra-grt-smoke-1027/pre
INFRA=/srv/opentallas-scratch2/claude/codex-infra-grt-smoke-1027/source.odb
docker run --rm --name dinfra-import-$(basename $D)-$$ --cpus=${CPUS:-16} --memory=${MEM:-8}g --memory-swap=${MEM:-8}g -e HUID=$(id -u) -e HGID=$(id -g) -e CPUS=${CPUS:-16} -v "$K:/work:ro" -v "$(readlink -f $K/abstracts):/work/abstracts:ro" -v "$PRE:/pre:ro" -v "$D:/out" -v "$INFRA:/infra/source.odb:ro" openroad/orfs:latest bash /out/run_import_inside.sh
