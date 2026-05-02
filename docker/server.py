"""
Dew — REST API
==============
Zero configuration. Run anywhere Docker runs.
Every routing decision is written to an append-only human-legible activity log.
Humans read the log. It never changes, only grows.

docker build -t dew -f docker/Dockerfile .
docker run -p 8000:8000 -v $(pwd)/logs:/app/logs dew

POST /path       → shortest route with full node sequence
POST /distance   → shortest hop count between two nodes
POST /nearest    → nearest reachable node from a candidate set
POST /synthesize → intent string → ConstraintProfile (no LLM, no API call)
POST /route      → full pipeline: intent → weights → terrain → path → log
POST /load       → load graph from file or directory path
POST /route-stored → route on the stored graph
POST /path-stored  → path on the stored graph
POST /run        → cluster analysis on stored graph
POST /snapshot   → write .dew snapshot to logs/
GET  /log        → last 20 lines of activity log
POST /reorganize → aesthetic directory rename
GET  /health     → liveness check

Graph format (path, distance, nearest):
{
  "graph": {
    "node_id": {
      "connections": ["neighbor_id", ...],
      "weights": {"neighbor_id": 1.5, ...}
    }
  },
  "start": "node_id",
  "target": "node_id",
  "caller": "your_system_name",
  "note": "optional human note for the log"
}

Activity log location: logs/routing_decisions.log
"""

import os
import sys
import dataclasses
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pypi"))
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from tree_topology_heuristics import TreeTopologyHeuristics, TreeNode
from logger import ActivityLog
from entry_point import route as dew_route
from intent_weight_synthesizer import IntentWeightSynthesizer, ConstraintProfile
from repoe_adapter import build_graph as repoe_build_graph
import json as _json

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dir_reorganizer import reorganize as _reorganize_dir

app = FastAPI(title="Tree Topology Heuristics", version="1.0.0")
log = ActivityLog("logs/routing_decisions.log")

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@app.get("/")
def index():
    return FileResponse(os.path.join(_root, "index.html"))

_log_path: str = os.getenv("DEW_LOG_PATH", "logs/routing_decisions.log")
_synthesizer   = IntentWeightSynthesizer(log=log)

_stored_graph: Optional[Dict[str, TreeNode]] = None
_node_to_file: Dict[str, str] = {}


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


class LoadRequest(BaseModel):
    path: str


class StoredRouteRequest(BaseModel):
    intent: str
    start: str
    target: str
    caller: str = "ui"


class StoredPathRequest(BaseModel):
    start: str
    target: str
    caller: str = "ui"


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
    return {"status": "dew-ing fine", "log": str(log.filepath)}


@app.post("/synthesize")
def synthesize(req: SynthesizeRequest):
    profile = _synthesizer.synthesize(req.intent, caller=req.caller)
    return dataclasses.asdict(profile)


@app.post("/route")
def route(req: RouteRequest):
    graph = _build_graph(req.graph)
    result = dew_route(req.intent, graph, req.start, req.target, log_path=_log_path)
    return dataclasses.asdict(result)


@app.post("/load")
def load(req: LoadRequest):
    global _stored_graph, _node_to_file
    p = req.path
    if not os.path.exists(p):
        raise HTTPException(status_code=400, detail=f"Path does not exist: {p}")

    merged: Dict[str, TreeNode] = {}
    node_to_file: Dict[str, str] = {}

    if os.path.isdir(p):
        found = False
        for root, _, files in os.walk(p):
            for fname in files:
                if fname.endswith(".json") and fname != "dew.config.json":
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath) as f:
                            data = _json.load(f)
                        graph = repoe_build_graph(data)
                        for node_id in graph:
                            node_to_file[node_id] = fpath
                        merged.update(graph)
                        found = True
                    except Exception:
                        pass
        if not found:
            raise HTTPException(status_code=400, detail="No valid JSON files found in directory.")
    else:
        try:
            with open(p) as f:
                data = _json.load(f)
            merged = repoe_build_graph(data)
            for node_id in merged:
                node_to_file[node_id] = p
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to load file: {e}")

    _stored_graph = merged
    _node_to_file = node_to_file
    return {
        "nodes": len(_stored_graph),
        "edges": sum(len(n.connections) for n in _stored_graph.values()),
    }


@app.post("/route-stored")
def route_stored(req: StoredRouteRequest):
    if _stored_graph is None:
        raise HTTPException(status_code=400, detail="No graph loaded. Call /load first.")
    result = dew_route(req.intent, _stored_graph, req.start, req.target, log_path=_log_path)
    return dataclasses.asdict(result)


@app.post("/path-stored")
def path_stored(req: StoredPathRequest):
    if _stored_graph is None:
        raise HTTPException(status_code=400, detail="No graph loaded. Call /load first.")
    result = TreeTopologyHeuristics.find_path(_stored_graph, req.start, req.target)
    log.write(
        start=req.start,
        target=req.target,
        distance=result.distance,
        path=result.path,
        caller=req.caller,
    )
    return {"distance": result.distance, "path": result.path}


@app.post("/run")
def run():
    if _stored_graph is None:
        raise HTTPException(status_code=400, detail="No graph loaded. Call /load first.")
    from repoe_adapter import find_disconnected
    components = find_disconnected(_stored_graph)
    if not components:
        all_nodes = list(_stored_graph.keys())
        clusters = [{"hub": all_nodes[0] if all_nodes else None, "members": all_nodes}]
    else:
        clusters = []
        for component in components:
            hub = component[0]
            best_connections = -1
            for node_id in component:
                count = len(_stored_graph[node_id].connections)
                if count > best_connections:
                    best_connections = count
                    hub = node_id
            clusters.append({"hub": hub, "members": component})
    return {"clusters": clusters, "total_nodes": len(_stored_graph)}


@app.post("/snapshot")
def snapshot(req: dict):
    import json as _json2
    import datetime
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"logs/snapshot_{ts}.dew"
    os.makedirs("logs", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        _json2.dump({"schema_version": "1.0", "snapshot": req, "timestamp": ts}, f, indent=2)
    return {"path": path}


@app.get("/log")
def get_log():
    log_file = str(log.filepath)
    if not os.path.exists(log_file):
        return {"lines": []}
    with open(log_file) as f:
        lines = [line.rstrip("\n") for line in f.readlines()]
    non_empty = [line for line in lines if line.strip()]
    return {"lines": non_empty[-20:]}


class ReorganizeRequest(BaseModel):
    path: str


@app.post("/reorganize")
def reorganize(req: ReorganizeRequest):
    try:
        output_path = _reorganize_dir(req.path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    file_count = sum(1 for _, _, files in os.walk(output_path) for _ in files)
    return {"output_path": output_path, "files": file_count}
