#!/bin/bash
# admission pass-through (the caller holds an ot-run / ot-heavy reservation): admit_pass.sh <GB> -- <command...>
shift; [ "${1:-}" = "--" ] && shift
exec "$@"
