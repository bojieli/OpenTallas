This monitor watches only the explicitly pinned coordinator thread and its proven current descendants. It connects with `codex app-server proxy` to an existing app server. It reads no credential files and creates no agent threads.

The shipped action is a structured notification file. Optional coordinator notifications use supported `turn/steer` with an exact `expectedTurnId`. The coordinator must then call `followup_task` for the original failed child. **Direct starts are disabled:** the installed `turn/start` schema has no atomic idle-state precondition and can add input to an already active turn.

A notification requires an actual scoped `error` event with capacity code/text and `willRetry:false`, a matching terminal failed turn, current idle status, no pending queue/input/approval, no newer turn or success, an active or absent goal, and the original Codex coordinator lock generation. Quota, context, authorization and other failures are excluded. State is written atomically and fsynced before a notification attempt. Deduplication survives restarts; transport ambiguity never triggers an unguarded duplicate. Repeated capacity failures receive exponential delay with jitter and a four-notification cap per thread, reset only by a successful turn.

Launch the observer:

```bash
tools/codex_capacity_monitor/launch.sh ROOT_THREAD_UUID --socket VERIFIED_CONTROL_SOCKET
```

The default runtime directory is `/home/ubuntu/claude-takeover-20261007/capacity-monitor`; set `CAPACITY_MONITOR_STATE` to select another. `pid`, `state.json`, `events.jsonl`, `health.jsonl`, and `notification-*.json` provide handles and receipts. A `STOP` file exits the monitor through its own loop. The launcher uses a single-instance lock. It does not kill processes or restart the server.

`--subscribe-loaded` attaches only already loaded, direct-input-capable threads with no configuration overrides. Do not enable it until the real endpoint’s attachment behavior is verified. `--notify-coordinator` enables exact-turn guarded notification of an available active coordinator; unavailable or unsupported children remain in notification files. An idle failed root still requires a verified atomic continuation mechanism, which this version does not claim to provide.

Deployment limitation observed on 2026-10-14: CLI 0.162.1 supports the proxy, but its default `/home/ubuntu/.codex/app-server-control/app-server-control.sock` is absent. Read-only proxy and daemon-version probes failed before attachment. No alternative socket was guessed, and no server was started/restarted. The deployed observer consequently reports a blocked connection until a verified control endpoint is supplied; **automatic continuation is not operational yet**.

Protocol references: [official app-server documentation](https://developers.openai.com/codex/app-server/) and JSON schemas generated from the installed CLI with `codex app-server generate-json-schema --experimental`. `schema_receipt.json` records the local version, schema hashes, root ID, and connection limitation. Tests use fake RPC/failure events only; they inject no real failure and start no live inference turn.

```bash
python3 -m unittest discover -s tools/codex_capacity_monitor -p 'test_*.py'
```
