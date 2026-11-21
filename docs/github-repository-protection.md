# GitHub repository protection

The template copies repository files, but GitHub repository settings are not inherited when a new repository is created from this template. Configure protection separately for every project repository.

## Recommended default-branch rules

Create a branch ruleset targeting the default branch (normally `main`) with these settings:

- Require a pull request before merging.
- Require the **Repository quality and security** status check to pass.
- Require branches to be up to date before merging when the team can tolerate the additional merge queue friction.
- Require conversation resolution before merging.
- Block force pushes and branch deletion.
- Keep bypass actors to the minimum necessary; avoid broad administrator or GitHub App bypasses.

For a solo-maintained repository, requiring a pull request and successful CI while setting the required approval count to zero is a practical baseline. Add human approval requirements when another maintainer is available. An AI review is useful evidence, but it should not be represented as a human approval.

## Setup

1. Open the repository's **Settings**.
2. Go to **Rules → Rulesets** and create a branch ruleset, or use **Branches → Branch protection rules** if using the classic interface.
3. Target the default branch.
4. Enable the protections above.
5. Under required status checks, select the exact check context **Repository quality and security** after the workflow has completed at least once.
6. Save the ruleset and verify that a test pull request cannot merge while the required check is failing.

## Notes

- Rulesets and branch-protection settings are repository configuration, not files. They do not travel with this template.
- Keep the CI workflow's permissions read-only unless a job has a documented need for additional permissions.
- Do not require a status check name that does not exist in the repository; a mismatched required check can block all merges.
