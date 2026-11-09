# FLEET-MESH-1 (lane FLEET-MESH-1, OWNER 11-09 02:3x "manage all the servers fully yourself")

2026-11-09 02:13 PST: full fleet ssh mesh is up. Every fleet host reaches every other one as ubuntu, with BatchMode, by short alias and by Cherry name. Matrix: 42/42 OK.

## Matrix (`ssh -n -o BatchMode=yes <alias> hostname`, row = from, column = to), run 2026-11-09 02:13 PST
| from \ to | intel2 | intel1 | epyc2 | epyc4 | epyc5 | epyc6 | epyc7 |
|---|---|---|---|---|---|---|---|
| intel2 | self | OK key-cardinal | OK dear-crayfish | OK aware-parakeet | OK devoted-wren | OK eager-sunfish | OK loved-redfish |
| intel1 | OK tolerant-swine | self | OK dear-crayfish | OK aware-parakeet | OK devoted-wren | OK eager-sunfish | OK loved-redfish |
| epyc2 | OK tolerant-swine | OK key-cardinal | self | OK aware-parakeet | OK devoted-wren | OK eager-sunfish | OK loved-redfish |
| epyc4 | OK tolerant-swine | OK key-cardinal | OK dear-crayfish | self | OK devoted-wren | OK eager-sunfish | OK loved-redfish |
| epyc5 | OK tolerant-swine | OK key-cardinal | OK dear-crayfish | OK aware-parakeet | self | OK eager-sunfish | OK loved-redfish |
| epyc6 | OK tolerant-swine | OK key-cardinal | OK dear-crayfish | OK aware-parakeet | OK devoted-wren | self | OK loved-redfish |
| epyc7 | OK tolerant-swine | OK key-cardinal | OK dear-crayfish | OK aware-parakeet | OK devoted-wren | OK eager-sunfish | self |

## What changed (append-only; first-edit backups are ~/.ssh/{authorized_keys,config}.bak-mesh-1109 on each host)
| host | authorized_keys lines | ~/.ssh/config lines |
|---|---|---|
| intel2 | 11 -> 11 | 47 -> 89 |
| intel1 | 5 -> 11 | 25 -> 85 |
| epyc2 | 5 -> 11 | 25 -> 85 |
| epyc4 | 7 -> 11 | 29 -> 89 |
| epyc5 | 11 -> 12 | 31 -> 91 |
| epyc6 | 11 -> 12 | 31 -> 91 |
| epyc7 | 10 -> 11 | 24 -> 84 |

- Keys: each host keeps its own ubuntu ~/.ssh/id_ed25519 (all 7 already had one, none created). Only the .pub lines were appended to the other hosts' authorized_keys. No private key was copied. agidock_ot is not used or referenced off localhost.
- Config: each host has one `# FLEET-MESH <alias>` block per peer, headed `Host <alias> <cherry-name>`, with HostName, User ubuntu, StrictHostKeyChecking accept-new, ServerAliveInterval 30 and ConnectTimeout 10. If that exact Host line was already present (for example intel2 "Host epyc5 devoted-wren"), the header is written as `Host <cherry-name> <alias>` so no line is duplicated. Earlier blocks still take precedence, and all of their HostNames matched.
- ControlMaster auto, ControlPath ~/.ssh/cm-%C and ControlPersist 10m are on the outgoing blocks of intel1, epyc2, epyc4, epyc5, epyc6 and epyc7. They are NOT on intel2 (the hub), because that would conflict with existing settings: sshd MaxSessions=10 on every host, and the hub holds 30 to 60+ concurrent ssh sessions per peer (63 to intel1 at 02:09). A multiplexed master would refuse the 11th session.
- No change to sshd_config, the firewall, localhost, AGIdock, owner VMs or the archive. No Cherry API calls.
- Re-running is a no-op (verified: all line counts unchanged).

## Tools (localhost ~/coord/tools)
- `fleet_mesh_add.sh <alias> <ip> [cherry-name] [mux yes|no]` adds a new host the same way. It needs `ssh <alias>` to work from localhost first (the ONBOARD lane adds the localhost block). It appends the row to fleet_hosts.tsv and then re-ensures keys and config blocks on every host. For epyc8: `~/coord/tools/fleet_mesh_add.sh epyc8 <ip> outgoing-giraffe`, then `fleet_mesh_matrix.sh`.
- `fleet_mesh_add.sh --all` re-ensures the whole table. `fleet_mesh_matrix.sh` prints this matrix.
- `fleet_hosts.tsv` is the fleet table: alias, Cherry name, IP, mux.

Note: ssh from a host to its own Cherry name (for example epyc7 -> loved-redfish) is not covered (Host key verification failed on the self entry). The mesh does not need it.
