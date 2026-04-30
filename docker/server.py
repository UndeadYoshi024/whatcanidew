"""
Tree Topology Heuristics — REST API
====================================
Three endpoints. Zero configuration. Run anywhere Docker runs.
Every routing decision is written to an append-only human-legible activity log.
Humans read the log. LLMs do not. Feed data forward manually.

docker build -t tree-topology-heuristics .
docker run -p 8000:8000 -v $(pwd)/logs:/app/logs tree-topology-heuristics

POST /distance   → shortest hop count between two nodes
POST /path       → shortest route with full node sequence
POST /nearest    → nearest reachable node from a candidate set
GET  /health     → liveness check

Graph format (all endpoints):
{
  "graph": {
    "node_id": {
      "connections": ["neighbor_id", ...],
      "weights": {"neighbor_id": 1.5, ...}
    }
  },
  "start": "node_id",
  "target": "node_id",
  "targets": ["node_id", ...],
  "caller": "your_system_name",
  "note": "optional human note for the log"
}

Activity log location: logs/routing_decisions.log
"""

import os
import dataclasses
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, List, Optional
from tree_topology_heuristics import TreeTopologyHeuristics, TreeNode
from logger import ActivityLog
from entry_point import route as dew_route
from intent_weight_synthesizer import IntentWeightSynthesizer, ConstraintProfile

app = FastAPI(title="Tree Topology Heuristics", version="1.0.0")
log = ActivityLog("logs/routing_decisions.log")

_log_path: str = os.getenv("DEW_LOG_PATH", "logs/routing_decisions.log")
_api_key: str  = os.getenv("DEW_API_KEY", "")
_synthesizer   = IntentWeightSynthesizer(api_key=_api_key, log=log)


class NodeInput(BaseModel):
    connections: List[str]
    weights: Optional[Dict[str, float]] = None


class DistanceRequest(BaseModel):
    graph: Dict[str, NodeInput]
    start: str
    target: str
    caller: str = "unknown"
    note: str = ""


class NearestRequest(BaseModel):
    graph: Dict[str, NodeInput]
    start: str
    targets: List[str]
    caller: str = "unknown"
    note: str = ""


class SynthesizeRequest(BaseModel):
    intent: str
    caller: str = "api"


class RouteRequest(BaseModel):
    intent: str
    graph: Dict[str, NodeInput]
    start: str
    target: str
    caller: str = "api"


def _build_graph(raw: Dict[str, NodeInput]) -> Dict[str, TreeNode]:
    return {
        k: TreeNode(id=k, connections=v.connections, weights=v.weights or {})
        for k, v in raw.items()
    }


@app.post("/distance")
def distance(req: DistanceRequest):
    graph = _build_graph(req.graph)
    result = TreeTopologyHeuristics.find_path(graph, req.start, req.target)
    log.write(
        start=req.start,
        target=req.target,
        distance=result.distance,
        path=result.path,
        caller=req.caller,
        note=req.note
    )
    return {"distance": result.distance}


@app.post("/path")
def path(req: DistanceRequest):
    graph = _build_graph(req.graph)
    result = TreeTopologyHeuristics.find_path(graph, req.start, req.target)
    log.write(
        start=req.start,
        target=req.target,
        distance=result.distance,
        path=result.path,
        caller=req.caller,
        note=req.note
    )
    return {"distance": result.distance, "path": result.path}


@app.post("/nearest")
def nearest(req: NearestRequest):
    graph = _build_graph(req.graph)
    result = TreeTopologyHeuristics.find_nearest(graph, req.start, req.targets)
    log.write_nearest(
        start=req.start,
        candidates=req.targets,
        nearest=result.target_id,
        distance=result.distance,
        path=result.path,
        caller=req.caller,
        note=req.note
    )
    return {"target_id": result.target_id, "distance": result.distance, "path": result.path}


@app.get("/health")
def health():
    return {"status": "ok", "log": str(log.filepath)}


@app.post("/synthesize")
def synthesize(req: SynthesizeRequest):
    profile = _synthesizer.synthesize(req.intent, caller=req.caller)
    return dataclasses.asdict(profile)


@app.post("/route")
def route(req: RouteRequest):
    graph = _build_graph(req.graph)
    result = dew_route(req.intent, graph, req.start, req.target, api_key=_api_key, log_path=_log_path)
    return dataclasses.asdict(result)
