#!/bin/bash
exec docker run --rm --user "$(id -u):$(id -g)" -v /home:/home -w "$PWD" -e TMPDIR=/home/ubuntu/s81-rowdecode-enrollment-20261004-r1/compiler-tmp --entrypoint /usr/bin/g++-11 ot-host:22.04 "$@"
