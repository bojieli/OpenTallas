# PC native post-only continuation

The native fresh-process route and finish completed. Original-to-final clock guard passes 4261 nets / 48012 instances with zero changes. The original post call exited 2 before signoff because its manually assembled capsule contained a new runner calling `lec_async.sh check-synth` and an old helper supporting only start/wait/finish. Actual pin audit passes 4133/4133, SDC lint passes; no proof was started or credited.

The fresh Intel1 capsule copies the complete native outputs, retains the old helper and aborted watcher/logs, and pins the matching canonical helper from source c7abb4874. This is a post-only API correction: no physical input, checkpoint, RTL, source SDC or netlist edit; no SYNTH, P&R or repair rerun. Own final-netlist proof remains separately required. The normal post runner and signoff decide physical qualification.
