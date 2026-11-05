# Day 18: Image Build CI

Status: Core acceptance complete from learner-confirmed PR checks and supplied build
logs. Progress 18/30 (60%); actual hours unrecorded.

## Implementation and evidence

.github/workflows/ci.yml adds workflow_dispatch and an images job gated by
needs: [quality, containers]. Matrix targets api/dashboard use the Dockerfile
stages and full github.sha tags. Implementation commit: 4a61034 on
feat/k8s-deployment; [PR 1](https://github.com/j22868706/sideproject_fabflow/pull/1).
The learner confirmed quality, containers, images(api), and images(dashboard)
passed. API build logs and dashboard naming output showed full PR workflow SHA
45160aa86a58c4bdb4592d08addc655dc664e454, not source branch head 4a61034.
The assistant did not independently fetch remote checks/logs.

Initial context/node were kind-fabflow/Ready; fabflow-helm revision 3 deployed,
chart 0.1.0, API 2/2, dashboard/DB 1/1, all four Pods zero restarts, PVC Bound.
This lesson did not deploy images or rerun HTTP business workflows.

## Build-only scope

Images exist only on disposable GitHub Actions runners. No registry push, artifact
export, or deployment occurred; naming to docker.io/library is not Docker Hub
publication. Manual workflow_dispatch was added but not executed/verified; the
workflow must exist on the default branch for its manual entry point.
Day 19 needed an explicit image acquisition strategy and architecture compatibility
between CI and the local ARM64 node.

## Merge and main closeout

Documentation commit 8421b3d was pushed; the learner confirmed all four updated PR
checks passed with no conflicts, then merged PR 1. Terminal output showed local
main/origin/main at merge 0e16ef4, and the learner confirmed all four main CI jobs
passed. Main image logs/full tags were not supplied; the PR SHA is not assumed to
be the main image tag. No independent Actions run URL or logs were fetched.
At that point architecture/git checks were proposed and the learner requested
record synchronization before proceeding. [Day 19](day19-versioned-deployment.md)
later completed local versioned deployment and HTTP acceptance.

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```text
fabflow-api:45160aa86a58c4bdb4592d08addc655dc664e454
fabflow-dashboard:45160aa86a58c4bdb4592d08addc655dc664e454
```
