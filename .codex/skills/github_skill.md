---
name: github-feature-delivery
description: Synchronize, publish, review, and merge completed feature work in the movie-mcp-server GitHub repository. Use when implementing or delivering a repository feature.
---

# GitHub Feature Delivery

Deliver code to `https://github.com/GuptaJiHardik/movie-mcp-server` through a dedicated feature branch and pull request into `main`.

## Workflow

1. Before editing, inspect `git status`, the current branch, configured remotes, and existing work. Do not discard or overwrite unrelated changes.

2. Verify the destination remote:
   - The expected URL is `https://github.com/GuptaJiHardik/movie-mcp-server`.
   - If `origin` is absent, add it. If it has a different URL, stop instead of replacing it silently.
   - Run `git fetch origin --prune` and confirm `origin/main` exists.
   - Confirm the repository shares history with `origin/main` using `git merge-base`. Never begin feature work from an unborn or unrelated local branch when the remote already has history.

3. Synchronize the base branch before creating a feature branch:
   - With a clean worktree, switch to local `main`. Create it to track `origin/main` if it does not exist.
   - Run `git pull --ff-only origin main`. Stop on divergence instead of creating an implicit merge commit.
   - If unfinished work prevents synchronization, preserve it explicitly before switching and restore it only onto a branch based on the updated `main`.

4. Choose a short feature name that describes the implementation:
   - Use lowercase kebab-case, such as `watchlist-sync` or `film-search`.
   - Keep it concise and omit words already implied by the `feature/` prefix.
   - Set the branch name to `feature/<feature-name>`.

5. Create the feature branch directly from the synchronized base:

   ```shell
   git switch -c feature/<feature-name> origin/main
   ```

   If the branch already exists locally, do not overwrite it. Reuse it only when it belongs to the same work and contains `origin/main` in its history.

6. Complete and verify the feature before committing:
   - Run the relevant focused checks and the full offline test suite.
   - Update `CODEX.md` and `.codex/plan/implementation.md` with progress and results.
   - Review `git status` and the diff. Stop on failing checks, unresolved conflicts, or unrelated changes that make a safe commit unclear.

7. Commit only implementation-related files:
   - Exclude secrets, credentials, local environment files, generated caches, and unrelated user work.
   - Stage explicit paths when unrelated changes are present.
   - Use a concise imperative commit message.

8. Before the initial push, fetch again and verify `origin/main` is an ancestor of the feature branch. If `main` advanced, merge `origin/main` into the unpushed branch, resolve deliberately, and rerun tests. Do not use `--allow-unrelated-histories` as a normal workflow.

9. Push and establish upstream tracking:

   ```shell
   git push -u origin feature/<feature-name>
   ```

   Never force-push. Preserve the local commit and report authentication, permission, remote, or branch-protection failures.

10. Create a pull request from `feature/<feature-name>` into `main` using available GitHub tooling or the GitHub API. Include a concise summary and the exact tests run.

11. Inspect mergeability and required checks. Merge only when the pull request is conflict-free and all required checks pass. Use squash merge unless repository policy requires another method. Never bypass branch protection or required reviews.

12. After GitHub reports a successful merge:
    - Run `git fetch origin --prune`.
    - Switch to local `main`, creating its tracking branch if necessary.
    - Run `git pull --ff-only origin main` and verify the merged commit is present.
    - Do not delete local or remote feature branches unless the user authorizes branch deletion.

13. Report the feature branch, commit hash, checks, pull-request URL, merge result, and synchronized `main` commit.

## Unrelated-History Recovery

If local work and `origin/main` have no merge base, stop the ordinary workflow and inspect both roots. Reconcile them once on the feature branch only when preserving both histories is clearly intended, using an explicit `--allow-unrelated-histories` merge and deliberate conflict resolution. Run the full tests afterward, then continue through a pull request. Never solve this condition with a force-push or by replacing remote `main`.
