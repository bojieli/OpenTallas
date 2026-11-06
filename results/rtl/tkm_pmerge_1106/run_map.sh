#!/bin/bash
set -eu
docker run --rm --memory 4g --cpus 2 -u "$(id -u):$(id -g)" -v "$PWD:/work" openroad/orfs:asap7lock bash /work/map.sh
