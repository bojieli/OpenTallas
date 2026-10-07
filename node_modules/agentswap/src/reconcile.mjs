/**
 * The three-way reconcile state machine. Pure logic over three canonical content
 * hashes: live settings, the active profile, and the last-applied baseline.
 *
 * Comparing only live vs profile can tell you they diverged but not WHICH side
 * changed — the common-ancestor baseline is the load-bearing extra bit.
 */

/**
 * @param {{ liveHash: string|null, profileHash: string|null, baselineHash: string|null }} hashes
 * @returns {{ state: string, canSave: boolean, canApply: boolean, needsChoice: boolean }}
 *   state ∈ no-baseline | in-sync | live-unsaved | profile-edited | converged | conflict
 */
export function reconcile({ liveHash, profileHash, baselineHash } = {}) {
  const live = liveHash ?? null
  const profile = profileHash ?? null
  const baseline = baselineHash ?? null

  // No trusted baseline → unknown, fail-closed. Direction is unknowable, so refuse
  // to silently overwrite a non-empty live that differs from the profile.
  if (baseline === null) {
    const needsChoice = live !== null && live !== profile
    return result('no-baseline', { needsChoice, canApply: !needsChoice })
  }

  const liveChanged = live !== baseline
  const profileChanged = profile !== baseline

  if (!liveChanged && !profileChanged) return result('in-sync', {})
  if (liveChanged && !profileChanged) return result('live-unsaved', { canSave: true })
  if (!liveChanged && profileChanged) return result('profile-edited', { canApply: true })
  if (live === profile) return result('converged', {})
  return result('conflict', { needsChoice: true })
}

function result(state, { canSave = false, canApply = false, needsChoice = false }) {
  return { state, canSave, canApply, needsChoice }
}
