#!/bin/bash
# ship.sh <host> <remote_dir> <path...> : copy repo-relative paths (files or dirs) from the cwd repo to host:remote_dir
# (tar over ssh; remote_dir is created).  Used to stage S81-SLICE bench sources on a fleet host before ot-run.
set -eu; H=$1; R=$2; shift 2
tar -czf - "$@" | ssh -o ConnectTimeout=20 $H "mkdir -p $R && tar -xzf - -C $R"
