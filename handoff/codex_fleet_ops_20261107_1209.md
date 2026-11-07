# Fleet operations — 2026-11-07 12:09 takeover

Scope: read-only fleet/cleanup coverage and allowed operational class repair. No deletions, deletion-chain restart, host rental/retirement, guard relaxation, merge, tag, or plan-of-record change. Only own unstarted jobs may be migrated; other jobs require the exact two-hour-flat/no-CPU rule and explicit identification. Continue until an explicit reset notice, not the expected13:02 wall time.

Live snapshot12:10:30 PST (actual per-host df, not a selected scratch-root summary):

| Host | AdmitGB | Waiters | Load/threads | Running | Root freeGB | Scratch2 freeGB | Readiness |
|---|---:|---:|---:|---:|---:|---:|---|
| epyc2 |26|50|121/128|62|182|133|Root near95% guard; avoid new copies to root. Existing queues mostly RAM-limited.|
| intel1 |119|1|121/112|58|191|227|Dedicated scratch and RAM available; already CPU busy, still below ordinary1.5x guard.|
| intel2/localhost |262|0|77/112|38|118|83|Best normal admission opportunity for small complete cohorts on scratch2; root below150 reserve, no scratch3 fallback.|
| epyc4 |−10|3|70/256|44|320|242|RAM invariant currently full; disk available.|
| epyc5 |5|96|67/128|66|104|116|Large queue, RAM reserved by active/fresh work; root has<20GB usable above100 reserve.|
| epyc6 |107|0|90/128|40|96|98|Good small/medium ordinary-job opportunity on scratch2; root below100 reserve.|

All six ot-heavy scripts match SHA25639c14ad125004f0ab725caf11cc47a9b5a0d51bf56945d774a99d76f928b5292 (live direct Docker accounting fix, now merged by Claude). E4/E5/E6 INV_PAST_PEAK_FACTOR=1 and INV_HEADROOM_GB=32. No factor was changed/rearmed. Earlier pause PIDs257421/1539245 are absent; no SIGCONT or assumption of continued pause/resume was made.

Current normal wrapper uses fleet/ac3b-6e11876faa2/ot-run, deployed09:29 with spill-capacity accounting and partial-backcopy repair. The separate ot-run-direct wrapper still points to legacy sched1-direct. Read current supported flags before new owned direct launches; direct eligibility and memory safeguards remain unchanged.

AUTOCLEAN-4 last state11:28: E2 root158→205GB under Claude's ruling,16 deletions/49.5GB, kept152GB; no deletion by Codex. It warned root consumption could erase the margin. Current182GB confirms the margin is shrinking. I2 scratch2 reclamation target100GB was spent; epyc6-moved-1106 stays held until an explicit current owner ruling, including five PROVISIONAL records. All prior deletion approvals are held during Codex watcher mode.

PRUNE-AUDIT-1 conclusions remain: old receipts do not prove identity; four lost cohorts are rebuild-on-demand, no live waiter then; restart required a fresh scan. No pruning/rebuild solely for audit was started. Old t36 kept_eco_cap removal was explicitly refused and never ran; do not repeat it.

Next: supply current I2/E6 opportunities to lane owners for their own eligible unstarted jobs; keep complete cohorts, proper ordinary-vs-die classification, existing caps/floors and host-side output capture. Watch E2 root and I2/E5/E6 disk margins. Read active cleanup processes only; do not restart cleanup.

12:14:35 PST update: normal admit E2/I1/I2/E4/E5/E6=3/114/286/18/27/152GB; waiters48/2/0/3/98/0. E6scratch2=97GB, I2=79GB, E5=111GB, E2root186GB/95%. No earlyoom killing events since12:09 returned by current journals, and no active cleanup/spill-sweep matches. Current normal backend --direct verified line1299; separate direct wrapper remains legacy. KV owns exact-old-waiter cancellation and ONE Wi rehome, retained64GB8t; fleet ops gave E6 normal placement advice, issued no signal or job launch.

12:15:26 PST actual admission reported by KV owner: ONE inherited Wi rehome admitted Intel2 direct, unit1809060-1794082526,64GB8t. Exact old E2waiter3332332 and I2frontend4178013 gone. KV now owns separately authorized flat-waiter cj recovery,5GB completecohort plus18MBtag, preserve64GB and verify disk aftercopy. No fleet-ops launch/signals. E5 nested48GB LEC waiter examples sent waveowner for current-row disposition; no stop inferred from idle wrapper alone.

Current policy / stale-checkpoint override
The earlier0802 checkpoint's critical E4 pauses are STALE. Claude's subsequent AUTOCLEAN/repair work resolved that state; fresh12:10 process checks found old cleanup257421 and backcopy1539245 ABSENT. No Codex resume or deletion restart was issued. Preserve current data; do not act on old PID records.

All EPYC4/5/6 INV_PAST_PEAK_FACTOR=1 and INV_HEADROOM_GB=32. The prior factor0 guard monitors are inactive after rollback; do not rearm them. Hard-invariant accounting, fresh reservations, caps, disk gates and current direct unused-booking accounting remain intact. The mainmerged direct Docker accounting fix is liveall6; no new scheduler source change is needed.

Disk: ordinary dedicated scratch floor50GB; true whole-die jobs additionally preserve60GB after declared disk need/reservations. Individual type/block PLACE must use its actual ordinary classification. Authorized root-backed scratch3 obeys root reserve150GB on E2/E4/I1/I2,100GB on E5/E6 plus20GB usable minimum; current I2/E5/E6 fallback does not qualify. E2root95% deserves restraint. Forward spill capacity margin60GB/backcopy10GB and partial-prefix repair are current normal wrapper features. No floor/cap override and no copy based merely on RAM fit.

Owner recovery status: KV owns ONE Wi rehome (admittedI2 direct12:15:26 unit1809060-1794082526,64GB8t) and root-authorized fo8cj recovery (old flat client canceled, remaining exactremote waiter confirmation/copy/launch pending at lastmessage). No duplicate launch by fleetops. E5 old nestedLEC waiter candidates sent waveowner for current-row mapping; no idle-shell inference used to stop jobs. No extra health polls unless a live admission/capacity problem warrants one.
