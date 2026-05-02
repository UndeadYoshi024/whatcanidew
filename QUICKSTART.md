DEW
Quick Start Guide
==================

What this dews
--------------
Finds the shortest path between any two points in any connected network.
Supply chains. Invoice workflows. Approval hierarchies. Org charts.
Skill trees. Document routing. Anything with nodes and connections.

Every decision is written to a plain text activity log.
Humans read the log. It never changes, only grows.


Pick your distro
----------------

OPTION 1 — Python (pip)
  Who it's for: Python developers, data scientists, analysts
  What you need: Python 3.8 or newer
  How to install:
    pip install dew
  How to use:
    from tree_topology_heuristics import TreeTopologyHeuristics, TreeNode
    graph = {
      "warehouse": TreeNode(id="warehouse", connections=["hub"]),
      "hub":       TreeNode(id="hub",       connections=["warehouse", "port"]),
      "port":      TreeNode(id="port",       connections=["hub"]),
    }
    result = TreeTopologyHeuristics.find_path(graph, "warehouse", "port")
    print(result.distance)  # 2
    print(result.path)      # ["warehouse", "hub", "port"]

OPTION 2 — JavaScript / TypeScript (npm)
  Who it's for: Web developers, Node.js applications
  What you need: Node.js
  How to install:
    npm install dewdrops
  How to use:
    import { TreeTopologyHeuristics } from 'dewdrops'
    const result = TreeTopologyHeuristics.findPath(graph, "warehouse", "port")

OPTION 3 — REST API (Docker)
  Who it's for: Any language, any system, universal
  What you need: Docker
  How to run:
    docker build -t dew -f docker/Dockerfile .
    docker run -p 8000:8000 -v $(pwd)/logs:/app/logs dew
  Endpoints:
    POST http://localhost:8000/path
    POST http://localhost:8000/distance
    POST http://localhost:8000/nearest
    GET  http://localhost:8000/health
  Example request:
    {
      "graph": {
        "warehouse": { "connections": ["hub"] },
        "hub":       { "connections": ["warehouse", "port"] },
        "port":      { "connections": ["hub"] }
      },
      "start": "warehouse",
      "target": "port",
      "caller": "my_system",
      "note": "daily shipment routing"
    }
  Example response:
    { "distance": 2, "path": ["warehouse", "hub", "port"] }

OPTION 4 — PostgreSQL
  Who it's for: Any team already running PostgreSQL
  What you need: PostgreSQL 12+ with PL/Python3u enabled
  How to install:
    psql -d your_database -f postgres/tree_topology_heuristics.sql
  How to use:
    SELECT tth_distance('{"warehouse":["hub"],"hub":["warehouse","port"],"port":["hub"]}', 'warehouse', 'port');
    -- returns: 2
    SELECT tth_path('{"warehouse":["hub"],"hub":["warehouse","port"],"port":["hub"]}', 'warehouse', 'port');
    -- returns: {warehouse,hub,port}


Intent-driven routing
---------------------
Express your intent in plain language. Dew parses it into a ConstraintProfile
and shapes the graph terrain before routing. No API call. No LLM. No network.
Pure keyword extraction — deterministic, auditable, instant.

  from entry_point import route

  result = route(
      user_intent="get there fast, avoid construction",
      graph=graph,
      start="warehouse",
      target="customer"
  )

Intent keywords Dew understands:
  Time-dominant:       fast, urgent, quick, asap, deadline
  Cost-dominant:       cheap, budget, cost, affordable, save
  Reliability-dominant: safe, reliable, consistent, stable, trusted
  Risk-averse:         risky, uncertain, dangerous, unpredictable
  Node constraints:    avoid <node>, prefer <node>, block <node>, never <node>

The same intent string never re-synthesizes — the profile is cached in memory
and persisted to disk. Restart the container. The profile is still there.

POST /synthesize — turn intent into a profile and inspect it.
  Example request:
    {
      "intent": "avoid congested hubs, prefer direct connections",
      "caller": "logistics_planner"
    }
  Example response:
    {
      "profile_name": "avoid_congested_hubs_prefer_direct_c",
      "intent_summary": "ambiguous intent — even distribution",
      "weights": { "time": 0.34, "cost": 0.33, "risk": 0.0, "reliability": 0.33, "distance": 0.0 },
      "constraints": { "avoid": ["congested"], "prefer": ["direct"], "hard_block": [] },
      "notes": "",
      "raw_intent": "avoid congested hubs, prefer direct connections"
    }

POST /route — full pipeline in one call: intent → weights → terrain → path → log entry.
  Example request:
    {
      "intent": "avoid congested hubs, prefer direct connections",
      "graph": {
        "warehouse": { "connections": ["hub", "port"] },
        "hub":       { "connections": ["warehouse", "port"] },
        "port":      { "connections": ["warehouse", "hub"] }
      },
      "start": "warehouse",
      "target": "port"
    }
  Example response:
    { "distance": 1, "path": ["warehouse", "port"] }


The activity log
----------------
Every routing decision is written to: logs/routing_decisions.log

Example entry:
  [2026-05-01 21:47:38 UTC] | FROM: warehouse | TO: port | DISTANCE: 2 | PATH: warehouse -> hub -> port | CALLER: entry_point

This file only grows. It is never modified. It is never deleted.
It is your audit trail. Compliance officers, auditors, and operations
managers can read it without any software.

When it gets large, rotate it manually:
  from logger import ActivityLog
  log = ActivityLog("logs/routing_decisions.log")
  log.rotate()  # archives current file, starts a fresh one


Support
-------
Questions: hello@whatcanidew.com
