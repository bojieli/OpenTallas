# Shared experiment register

Claude, Codex and their workers use the same durable register for experiments.
The register answers what a job is for, who owns it and whether its design is
still relevant. It does not establish numerical, timing or physical
qualification, schedule resources or stop processes.

The live file is `/home/ubuntu/opentallas-monitor/experiments.json`. Use
`/home/ubuntu/opentallas-monitor/experiment.py` to register, update or list entries.
The editor locks updates and appends lifecycle history to
`experiment-events.jsonl`; do not edit the JSON directly. The
[Fleet monitor](https://rtx-pro-files.01.me/fleet/), using the existing access
login, shows the **Shared experiment register**. The local view is
`http://127.0.0.1:8765/`.

## Keep the entry small

Every entry contains only these fields:

| Field | Meaning |
|---|---|
| `name` | A stable name for the actual experiment, not each compiler child or poll. |
| `host` | The execution host. |
| `worktree` | The actual source worktree or experiment directory. |
| `owner` | The accountable owner; write `UNASSIGNED` when ownership is unresolved. |
| `purpose` | The concrete design question or result this experiment supplies. State unresolved relevance rather than guessing that an old job remains required. |
| `status` | The owner-maintained lifecycle or relevance state. |

PIDs, container identities, source revisions, commands, inputs, outputs and
resource observations stay in the process monitor and existing job logs or
launch receipts. They are not additional registry fields. Do not create a new
proof or sealing system to enroll an experiment. Existing source and evidence
requirements still apply to the experiment itself.

## Register once, before launch

Search the register first and reuse compatible live jobs or completed artifacts.
The same launch wrapper that invokes the current owner-approved host launcher
registers the new experiment before spawning it. Register queued work once too;
registration does not mean a child has started. Do not launch another copy when
an existing command is waiting.

```sh
python3 /home/ubuntu/opentallas-monitor/experiment.py list
python3 /home/ubuntu/opentallas-monitor/experiment.py register \
  --name "$experiment_name" --host "$host" --worktree "$worktree" \
  --owner "$owner" --purpose "$purpose" --status current
```

There is no execution-start update and no update for every poll, phase change or
CPU sample. Update only on completion, abandonment, handoff or a relevance
change. The tool accepts `--id` and obsolete metadata flags for in-flight
compatibility; new callers use `--name` and the simple fields only.

```sh
python3 /home/ubuntu/opentallas-monitor/experiment.py update \
  --name "$experiment_name" --owner "$receiving_owner" --status current
python3 /home/ubuntu/opentallas-monitor/experiment.py update \
  --name "$experiment_name" --status retired \
  --purpose "$original_purpose_and_actual_retirement_reason"
```

## Ownership and retirement

`current` means the experiment still serves its stated purpose. `unassigned`
requires an explicit receiving owner or retirement decision. `review-required`
means current-design relevance is unresolved. `superseded` identifies work
replaced by a successor; it does not by itself mean a process has stopped.
Terminal states such as `completed`, `failed`, `stopped` and `retired` describe an
actual disposition, with the outcome retained in the existing job evidence.

An agent leaving an assignment must explicitly hand over the live job to an
accepting owner or gracefully stop authorized work after dependency release.
Pass the real process/container identities, source and dirty paths, logs,
remaining consumers and next action directly to that owner. Update the register
for the handoff and post a concise line in the shared
`/tmp/claude-review-20261003/codex_notes.txt`. Do not leave an orphaned job under
an old owner name.

Review actual source, scripts, logs and consumers when deciding whether work is
obsolete. There is no automatic kill by age. A quiet compiler log can coexist
with active work, and CPU consumption alone does not prove useful progress.
Transient SSH failure is not terminal. A missing parent PID does not prove that
its children or container have drained. Confirm identities on the actual host;
keep process observations separate from registry lifecycle decisions.

Retire an explicitly abandoned or superseded experiment promptly once its
source and artifact consumers are released. Preserve unique changes in refs or
patches and retain logs, inputs and pass/failure evidence. Stop only the exact
job and a launcher that would requeue it, preferably gracefully; record any
necessary escalation in its existing receipt. Verify the group/container is
stopped before recording retirement. A superseded round may be retired without
claiming that it was a byte-identical qualification of its successor. A stopped
experiment is not PASS.

Keep worktrees and archives while actual consumers depend on them. Remove them
after dependency release and preservation of unique source/evidence. Owners
commit substantive source/result milestones, fetch `origin/main`, merge or
rebase their own worktree, validate and push main directly. Do not remerge
already-published work or create polling commits. Documentation changes still
regenerate the prose census, synchronize both untriaged-count annotations and
pass `make check-figures`.
