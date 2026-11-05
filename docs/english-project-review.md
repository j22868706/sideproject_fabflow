# English Documentation and Portfolio Review

This review prepares FabFlow for an English-speaking technical audience and U.S.
job applications. It translates and edits project documentation while preserving
measured results, implementation boundaries, and the distinction between historical
milestones and the current configuration.

## Changes

- Converted the remaining Chinese content in Kubernetes Days 1–27 to English.
  Repeated teaching notes were consolidated into technical explanations, acceptance
  evidence, and limits. Historical command/example blocks remain available in their
  original order, with translated comments and diagram labels where needed.
- Preserved original raw measurement and terminal artifacts. No simulation behavior,
  application interface, deployment manifest, or credential was changed.
- Renamed the workbook to
  [FabFlow_K8s_30_Day_Progress.xlsx](../FabFlow_K8s_30_Day_Progress.xlsx), translating
  sheet names, headings, plans, notes, status validation, conditional formatting,
  and formula sheet references. Planned dates, estimated hours, blank actual hours,
  and 26 completed lessons were retained. Day 27 is explicitly in progress because
  the timed demonstration rehearsal is pending; Days 28–30 remain not started.
- Updated README and portfolio entry points for the PostgreSQL/Kubernetes work.
  Corrected outdated blanket claims that results always reside in memory or that
  persistent storage is absent. Local Python defaults to memory; Compose/Kubernetes
  select PostgreSQL for completed results. Execution remains synchronous in both.
- Kept the MVP's historical Python 3.12 test/coverage results separate from the
  current Python 3.14.6 local test run. Source SHA tags do not imply reproducible
  image digests or distinct application content when tags share the same image ID.

## Verification

| Check | Result |
| --- | --- |
| Repository language scan | No remaining Chinese text or filenames in existing tracked and nonignored project files, including workbook XML and diagrams |
| Local document file links | 171 checked at the initial scan; no missing targets; later additions rechecked |
| Markdown heading anchors | No unresolved local heading links |
| Workbook | ZIP/XML integrity, translated formula references, validation/formatting text, schedule/estimate/hour preservation, and lesson status verified |
| Historical command blocks | Retained from existing translated milestone files; comments/labels translated without changing operational values |
| Kubernetes command examples | 103 shell blocks passed syntax checks; 16 Python snippets parsed, including shell-quoted examples |
| Ruff lint | Passed |
| Ruff format | 113 files already formatted |
| Full local tests | 184 passed, one upstream Starlette TestClient/HTTPX deprecation warning; Python 3.14.6 |
| Git diff whitespace check | Passed |

This review did not restart containers, modify the cluster, rerun browser acceptance,
publish the repository, or independently fetch remote CI. Language scanning covers
the current repository, including saved evidence, rather than rewriting Git history,
ignored local credentials, virtual environments, or generated browser artifacts.

## Recommended reading order

Start with the [README](../README.md) for execution and deployment entry points,
then the [portfolio](portfolio.md) for project outcomes and engineering decisions.
The [architecture and measurements report](k8s/day26-measurements-architecture.md)
links raw evidence and limits. The [demonstration guide](k8s/day27-readme-demo.md)
provides a presentation outline, verified operations, and troubleshooting.

The next learning step remains Day 27's timed presentation rehearsal. English
translation does not establish zero downtime, database HA, cluster-loss recovery,
production-scale performance, or completion of the remaining job-search lessons.
