# Orchestrator Note

## Status
Repo initialized and pushed to github.com/UndeadYoshi024/whatcanidew.

## Fixes Applied
- `docker/Dockerfile` COPY paths corrected — build context is repo root, not `docker/`
- `pypi/pyproject.toml` homepage URL updated to `https://github.com/UndeadYoshi024/whatcanidew`
- Build command must be run from repo root: `docker build -t tth -f docker/Dockerfile .`

## Still Needs Attention
- `npm/index.ts` imports from `./TreeTopologyHeuristics_final` — this file does not exist on disk. TS core is in a zip somewhere. Must be landed before npm distro is touchable.
- License is `TBD` in both `pypi/pyproject.toml` and `npm/package.json` — needs a real license before any distro ships. Hospital package needs perpetual free exception documented.
- `postgres/tree_topology_heuristics.sql` grants EXECUTE to PUBLIC — scope this to a specific role before hospital deployment.

## Next
Drop `TreeTopologyHeuristics_final.ts` into the repo and confirm target distro for hospital package.
