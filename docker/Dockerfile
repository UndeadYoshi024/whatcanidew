FROM python:3.11-slim

WORKDIR /app

COPY pypi/tree_topology_heuristics.py .
COPY docker/server.py .
COPY logger.py .
COPY intent_weight_synthesizer.py .
COPY graph_weight_mapper.py .
COPY entry_point.py .

RUN pip install --no-cache-dir fastapi uvicorn anthropic

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
