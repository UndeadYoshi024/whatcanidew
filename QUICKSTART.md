DEW
Quick Start Guide
==================

What this does
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
    from dew import TreeTopologyHeuristics, TreeNode
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
    psql -d your_database -f tree_topology_heuristics.sql
  How to use:
    SELECT tth_distance('{"warehouse":["hub"],"hub":["warehouse","port"],"port":["hub"]}', 'warehouse', 'port');
    -- returns: 2
    SELECT tth_path('{"warehouse":["hub"],"hub":["warehouse","port"],"port":["hub"]}', 'warehouse', 'port');
    -- returns: {warehouse,hub,port}

Intent-driven routing
---------------------
The user expresses intent in natural language. Dew calls the LLM once,
returns a ConstraintProfile, and writes it to the activity log.
The same intent never re-runs the LLM.

To use intent endpoints, pass DEW_API_KEY when running the container:
  docker run -p 8000:8000 -e DEW_API_KEY=your_key -v $(pwd)/logs:/app/logs tth

POST /synthesize — call this to turn intent into a profile.
  Example request:
    {
      "intent": "avoid congested hubs, prefer direct connections",
      "caller": "logistics_planner"
    }
  Example response:
    {
      "profile": {
        "prefer": ["direct"],
        "avoid": ["congested"],
        "hard_block": [],
        "weights": { "congested": 2.5 }
      },
      "cached": false
    }

POST /route — full pipeline in one call: intent → weights → terrain → path → log entry.
  The LLM runs once. After that it is just math.
  Example request:
    {
      "intent": "avoid congested hubs, prefer direct connections",
      "graph": {
        "warehouse": { "connections": ["hub", "port"] },
        "hub":       { "connections": ["warehouse", "port"] },
        "port":      { "connections": ["warehouse", "hub"] }
      },
      "start": "warehouse",
      "target": "port",
      "caller": "logistics_planner"
    }
  Example response:
    { "distance": 1, "path": ["warehouse", "port"] }

The activity log
----------------
Every routing decision is written to: logs/routing_decisions.log

Example entry:
  [2025-01-15 14:32:01 UTC] | FROM: warehouse | TO: port | DISTANCE: 2 | PATH: warehouse -> hub -> port | CALLER: invoice_router

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
