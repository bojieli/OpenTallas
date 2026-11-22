"""goal_table: ONE table of kit goals for private-spec / run-item (kit_wave), the wave chain (CHAIN_STAGES, resolve_chain_goal) and run_kit.sh's stage resume
(gen_phys RUN_KIT).  FLOW-FLEET-R2 C1 11-22 (FABLE-FLOW-0600): three hand-typed goal vocabularies sent 18 private kits to DIED SETUP (rc 10, "FAIL_PREFLOOR stage resume:
goal finish unsupported").  Every goal either reaches sign-off or names where it stops (test_goal_table).  Stdlib only; no side effects."""

# name -> (signs_off, chain stages after place, stop / meaning)
GOALS = {
    "auto":   (True,  None,                          "the runner's own sign-off goal (autopilot.default_goal: run_kit.sh -> route)"),
    "route":  (True,  ("cts", "grt", "route"),       "sign-off: CTS, GRT, route, finish, abstract"),
    "finish": (True,  ("cts", "grt", "route", "finish"), "sign-off; on a stage resume run_kit.sh runs it as route"),
    "place":  (False, (),                            "stops at the placed checkpoint (no AUTO-GEOM chain)"),
    "geom":   (False, (),                            "stops after AUTO-GEOM"),
    "cts":    (False, ("cts",),                      "diagnostic: stops after CTS, never a sign-off"),
    "grt":    (False, ("cts", "grt"),                "diagnostic: stops after GRT, never a sign-off"),
}
NAMES = tuple(GOALS)                                   # = kit_wave.PRIVATE_GOALS (CLI choices, spec 'goal')
CHAIN_STAGES = {g: s for g, (_, s, _) in GOALS.items() if s}   # goals the wave stage chain drives
STAGE_GOALS = ("route", "finish", "cts", "grt")        # goals resolve_chain_goal keeps; anything else is the runner's default goal
SIGNOFF_GOALS = tuple(g for g, (so, _, _) in GOALS.items() if so and g != "auto")
RESUME_GOALS = ("floorplan", "place", "cts", "grt", "route")   # goals run_kit.sh accepts on an in-place stage resume (resume.json)
RESUME_ALIAS = {"finish": "route"}                     # a resume has no finish goal: route is the runner's sign-off goal (RESUME-GOAL-1122)


def resume_goal(goal):
    """the goal run_kit.sh runs on a stage resume, or '' when it cannot"""
    g = RESUME_ALIAS.get(goal, goal)
    return g if g in RESUME_GOALS else ""


def stop_of(goal):
    """'sign-off' or the named stop of a goal (every goal has one)"""
    so, _, why = GOALS[goal]
    return "sign-off" if so else why


def shell_resume(text):
    """RUN_KIT text with its two stage-resume goal lines (KWRS) written from this table: the alias lines and the accepted-goal case"""
    alias = "".join(f'  [ "$GOAL" = {a} ] && {{ echo "KWRS stage resume: goal {a} runs as {b} ({b} is this runner\'s sign-off goal; RESUME-GOAL-1122)"; GOAL={b}; }}  # KWRS\n'
                    for a, b in RESUME_ALIAS.items())
    case = f'  case "$GOAL" in {"|".join(RESUME_GOALS)}) ;; *) echo "FAIL_PREFLOOR stage resume: goal $GOAL unsupported" | tee -a "$K/FAIL_PREFLOOR"; exit 10;; esac  # KWRS\n'
    out, n = [], 0
    for ln in text.splitlines(True):
        if ln.startswith('  [ "$GOAL" = finish ] && { echo "KWRS stage resume:'):
            out.append(alias); n += 1
        elif ln.startswith('  case "$GOAL" in floorplan|place|cts|grt|route)'):
            out.append(case); n += 1
        else:
            out.append(ln)
    if n != 2:
        raise ValueError(f"goal_table.shell_resume: expected the 2 KWRS goal lines in run_kit.sh, found {n}")
    return "".join(out)
