# Shared experiment register

Claude, Codex and their workers use the same durable register for builds,
simulations and physical experiments. Each experiment has an accountable owner,
a current design purpose and an explicit disposition. The register prevents a
superseded campaign from continuing simply because its launcher is still alive.
It does not establish numerical, timing, physical or performance qualification.

The live register is `/home/ubuntu/opentallas-monitor/experiments.json`. Use
`/home/ubuntu/opentallas-monitor/experiment.py` to register, update or list entries;
the tool locks updates and appends history to `experiment-events.jsonl`. Do not
edit the JSON directly or rewrite historical outcomes. The repository document
defines the shared workflow; the live file holds changing process observations
and ownership, without requiring a source commit for each poll.

The [Fleet monitor](https://rtx-pro-files.01.me/fleet/) includes a **Shared
experiment register** table. It uses the existing access login. The local view is
`http://127.0.0.1:8765/`. Registered-PID observations in the monitor are separate
from the owner-written lifecycle: a process being absent, or a host being
unreachable, does not automatically change an experiment to terminal.

## Register and launch

Before launching, search the register for an existing experiment with the same
purpose and source. Reuse its live job or completed artifact when compatible.
Every new job uses a single launch wrapper that registers its experiment before
spawning, invokes the current owner-approved host launcher, and attaches the
actual host process identities after launch. Registration is part of that launch
path, not a separate proof campaign. A queued job also needs an entry; do not
register an intended command as an already-running child.

Record the following information, with durable references rather than copied
payloads or credentials:

| Information | Required record |
|---|---|
| Identity and placement | Unique experiment `id`, execution `host`, actual supervisor/child `pids`, and full container identity where applicable. Preserve process start identity in the launch receipt so PID reuse cannot authorize a stop. |
| Accountability | Named `owner`, target model and design family, purpose, and the next concrete source or runtime result. |
| Source | `design_revision`, pinned source SHA, branch/worktree, selected parameters and actual command. Preserve the source used by a live experiment. |
| Inputs and outputs | Input manifest and hashes, output/log directory, launch and terminal receipts, and any produced archive consumed by another job. |
| Composition | `depends_on` and `supersedes` experiment IDs, the actual consumer of a retained archive, and whether the experiment is a baseline, successor or diagnostic. |
| Lifecycle | Current status, reason for review or retirement, update time and last authoritative check. |

The current CLI accepts `--revision`, `--worktree`, `--purpose`, `--outputs`,
`--pids`, `--depends-on` and `--supersedes`. It has no separate input-manifest or
container flag: put those references in the durable launch receipt under the
output directory and identify that receipt in the purpose or reason. Keep the
register concise while retaining the exact command and identities in that
receipt. Empty dependency lists mean no dependency has been recorded; they do
not prove that a worktree or archive is safe to delete.

For example, run these from the coordinator host, substituting the actual
experiment values:

```sh
python3 /home/ubuntu/opentallas-monitor/experiment.py list
python3 /home/ubuntu/opentallas-monitor/experiment.py register \
  --id "$experiment_id" --host "$host" --owner "$owner" --target "$target" \
  --revision "$source_sha" --worktree "$worktree" \
  --purpose "$purpose_and_launch_receipt" --outputs "$output_dir"

# After the host launcher returns real process identities:
python3 /home/ubuntu/opentallas-monitor/experiment.py update \
  --id "$experiment_id" --status active --pids "$supervisor_pid" "$child_pid" \
  --checked
```

Use the actual host's current admission command. Registering an experiment does
not grant resources, change an admission policy or install a process cap. A
compatible successor still needs its own ID and source identity; it must not
relabel an older archive or erase a failed attempt.

## Lifecycle and ownership

| State | Owner action |
|---|---|
| `registered` / `waiting-memory` | The launch is enrolled or queued. Record the real waiting handle and dependency; do not launch another copy. |
| `active` | The named owner follows the existing job through its next actual result. Record phase changes and meaningful progress, not a new entry for every poll. |
| `unassigned` | Ownership has ended without an accepted successor. Identify a temporary coordinator and the preservation path; promptly arrange handoff or retirement. |
| `review-required` | Current-target relevance, source compatibility or progress is unresolved. Check the specific dependency and actual job; age alone is not a verdict. |
| `superseded` / `retirement-requested` | An explicit owner decision identifies a successor or abandoned design. Record the reason and successor, preserve unique changes/evidence, and retire when dependencies are released. This state alone does not mean the process has stopped. |
| Terminal: `completed`, `failed`, `stopped` or `retired` | Record the actual outcome, reason and receipt. Confirm the applicable process group or container is drained, including escaped children and any requeue launcher. Preserve failed verdicts. |

An agent ending its assignment must explicitly hand over the experiment to an
accepting owner, or gracefully stop authorized work after dependency release.
The handoff includes the source/worktree, dirty paths, actual handles, output
directory, dependency consumers and next action. Update the registry owner and
post the concrete handoff in the shared
`/tmp/claude-review-20261003/codex_notes.txt`. Leaving an orphaned process with an
old owner name is not a handoff.

## Review, retirement and publication

Aged-job review maps the actual command, container mounts, source revision,
script/corners, logs and CPU/log progress to the current design. Quiet compiler
or solver logs can coexist with active work. A transient SSH failure is an
unknown observation; verify the same host and process identity before reporting
terminal. A missing parent PID alone does not prove that its descendants have
drained. There is no automatic kill by age.

Once an experiment is explicitly abandoned or superseded and its consumers are
released, retire it promptly. Preserve unique source changes in lightweight
refs or patches, exact inputs/scripts, logs and pass/failure evidence. Stop only
the identified job and its requeue launcher; keep unrelated live jobs intact.
Prefer graceful termination and record any required escalation. Then verify
terminal process/container identities and update the register with the actual
reason. A superseded round can be retired without claiming that it was a
byte-identical test of its successor. Never call a stopped experiment PASS.

Keep live worktrees and archives while another experiment depends on them.
Delete them only after dependency release and preservation of unique evidence.
Source changes are committed at meaningful implementation/result milestones,
not for registration or polling ceremony. Each owner completes its source and
run, fetches `origin/main`, merges or rebases its own worktree, validates the
result, and pushes main directly. Do not remerge already-published work or ask
ROOT to relay commits. Post a concise result line with source SHA, actual
outcome, output path and next dependency in the shared notes. Documentation
changes still regenerate the prose census, synchronize both untriaged-count
annotations and pass `make check-figures`.
