-- tree_topology_heuristics PostgreSQL extension
-- Requires: PL/Python3u (plpython3u)
-- Install: psql -f tree_topology_heuristics.sql
-- Usage:
--   SELECT tth_distance('{"a":["b","c"],"b":["a","d"],"c":["a","d"],"d":["b","c"]}', 'a', 'd');
--   SELECT tth_path('{"a":["b","c"],"b":["a","d"],"c":["a","d"],"d":["b","c"]}', 'a', 'd');

-- ── Distance function ─────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION tth_distance(
    graph_json TEXT,
    start_node TEXT,
    target_node TEXT
) RETURNS FLOAT
LANGUAGE plpython3u
AS $$
import json
from collections import deque

graph_raw = json.loads(graph_json)

if start_node not in graph_raw or target_node not in graph_raw:
    return -1
if start_node == target_node:
    return 0

# BFS
queue = deque([start_node])
visited = {start_node}
dist = {start_node: 0}

while queue:
    current = queue.popleft()
    current_dist = dist[current]
    for neighbor in graph_raw.get(current, []):
        if neighbor in visited:
            continue
        visited.add(neighbor)
        dist[neighbor] = current_dist + 1
        if neighbor == target_node:
            return current_dist + 1
        queue.append(neighbor)

return -1
$$;

-- ── Path function ─────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION tth_path(
    graph_json TEXT,
    start_node TEXT,
    target_node TEXT
) RETURNS TEXT[]
LANGUAGE plpython3u
AS $$
import json
from collections import deque

graph_raw = json.loads(graph_json)

if start_node not in graph_raw or target_node not in graph_raw:
    return None
if start_node == target_node:
    return [start_node]

queue = deque([start_node])
visited = {start_node}
parents = {start_node: None}

while queue:
    current = queue.popleft()
    for neighbor in graph_raw.get(current, []):
        if neighbor in visited:
            continue
        visited.add(neighbor)
        parents[neighbor] = current
        if neighbor == target_node:
            path = []
            node = target_node
            while node is not None:
                path.append(node)
                node = parents[node]
            path.reverse()
            return path
        queue.append(neighbor)

return None
$$;

-- ── Grant public access ───────────────────────────────────────────────────────

GRANT EXECUTE ON FUNCTION tth_distance(TEXT, TEXT, TEXT) TO PUBLIC;
GRANT EXECUTE ON FUNCTION tth_path(TEXT, TEXT, TEXT) TO PUBLIC;
