#!/bin/bash
# bg.sh <log> <cmd...>: start cmd detached (own session), immune to the ssh session ending
log=$1; shift
setsid "$@" > "$log" 2>&1 < /dev/null &
disown
echo started $! 
