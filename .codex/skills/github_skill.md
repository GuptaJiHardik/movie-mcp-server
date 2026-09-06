---
name: github-feature-push
description: Publish completed changes from this workspace to the movie-mcp-server GitHub repository on a new feature branch. Use when the user asks to push or publish an implementation.
---

# GitHub Feature Push

Publish code to `https://github.com/GuptaJiHardik/movie-mcp-server` on a dedicated feature branch.

## Workflow

1. Inspect the implementation and repository state before changing Git state:
   - Run the relevant tests or checks.
   - Review `git status`, the current branch, configured remotes, and the diff.
   - Stop and report any failing checks, merge conflicts, or unrelated changes that make a safe commit unclear.

2. Choose a short feature name that describes the implementation:
   - Use lowercase kebab-case, such as `watchlist-sync` or `film-search`.
   - Keep it concise and omit words already implied by the `feature/` prefix.
   - Set the branch name to `feature/<feature-name>`.

3. Create and switch to the new branch with `git switch -c feature/<feature-name>`.
   - If that branch already exists locally, do not overwrite it; inspect it and either reuse it when it clearly belongs to the same work or choose another accurate short name.

4. Ensure the destination remote is correct:
   - The expected URL is `https://github.com/GuptaJiHardik/movie-mcp-server`.
   - If `origin` is absent, add it with `git remote add origin https://github.com/GuptaJiHardik/movie-mcp-server`.
   - If `origin` exists with a different URL, stop and tell the user instead of replacing it silently.

5. Commit only the implementation-related files:
   - Inspect untracked files and exclude secrets, credentials, local environment files, generated caches, and unrelated user work.
   - Stage explicit paths rather than using a broad command when unrelated changes are present.
   - Use a concise imperative commit message that describes the completed change.

6. Push the branch and establish upstream tracking:

   ```shell
   git push -u origin feature/<feature-name>
   ```

   Never force-push. If authentication, permissions, remote conflicts, or branch-protection rules block the push, preserve the local commit and report the exact blocker.

7. Report the branch name, commit hash, checks run, and push result. Include the GitHub branch or pull-request URL when one is available from the push output.
