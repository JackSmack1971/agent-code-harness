---
paths:
  - "src/**/repository/**"
  - "src/**/git/**"
  - "src/**/workspace/**"
  - "src/**/acceptance/**"
  - "tests/**/*git*"
  - "tests/**/*worktree*"
---
# Git and Worktree Rules

- Mutating harness work never occurs directly in the user's active checkout.
- Capture repository identity and relevant dirty state before mutation.
- Materialize changes in an isolated worktree and verify its identity.
- Preserve the original checkout.
- Treat dirty/untracked data explicitly; never silently discard it.
- Default acceptance strategy is SQUASH; support CHERRY_PICK, topology-permitting FAST_FORWARD, and PATCH_ONLY where contracted.
- Destination drift, dirty destination state, and conflicts are never silently resolved.
- Never automatically rebase an already verified candidate onto externally changed destination state.
