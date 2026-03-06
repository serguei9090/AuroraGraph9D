from typing import Optional

from fastapi import FastAPI
from prometheus_client import make_asgi_app
from pydantic import BaseModel

from auragraph.core.config import config
from auragraph.core.engine import AuroraGraphEngine

app = FastAPI(title="AuroraGraph 10D Service")

# Expose prometheus metrics at /metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Initialize engine instance globally for the server
engine = AuroraGraphEngine()


class QueryRequest(BaseModel):
    query: str
    stream: Optional[bool] = False


@app.post("/query")
async def query_endpoint(req: QueryRequest):
    """
    Standard HTTP endpoint for querying the 10D semantic graph.
    """
    prediction = engine.predict(req.query, stream=req.stream)

    # Simple JSON serialization (ignores generator if streaming is requested over raw HTTP)
    if req.stream:
        return {"error": "Streaming not supported via raw HTTP POST. Use standard predict."}

    return prediction


@app.get("/health")
async def health_check():
    return {"status": "healthy", "model": config.AURA_MODEL, "db": config.AURA_DB_PROVIDER}
