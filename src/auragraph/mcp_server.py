import asyncio
from typing import List

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from auragraph.core.engine import AuroraGraphEngine

# Initialize the FastMCP Server
mcp = FastMCP("auragraph_mcp")

# Instantiate our engine once per server lifecycle.
# In a true deployment, this might be loaded via @asynccontextmanager lifespan.
# However, engine instantiation here relies on config.py sync setup.
engine = AuroraGraphEngine()


class ParallelQueryInput(BaseModel):
    """Input model for performing multiple parallel queries against the Graph."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    queries: List[str] = Field(
        ...,
        description="A list of 1 to 5 strategic questions or keywords to query the graph in parallel.",
        min_items=1,
        max_items=5,
    )


@mcp.tool(
    name="auragraph_parallel_query",
    annotations={
        "title": "AuroraGraph Parallel Query Expansion",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def auragraph_parallel_query(params: ParallelQueryInput) -> str:
    """
    Execute multiple semantic queries simultaneously against the AuroraGraph engine.

    This tool takes a minimum of 1 and maximum of 5 query strings. It executes
    them concurrently using the backend LLM orchestrator and Tri-Modal Graph DB,
    and returns a combined Markdown report of all findings.

    Args:
        params (ParallelQueryInput): Validated input parameters containing:
            - queries (List[str]): List of query strings.

    Returns:
        str: A Markdown-formatted string containing the consolidated evidence
             and synthesized responses from all queries.
    """
    results = []

    # Run predictions in parallel threads so they don't block the async event loop
    async def _run_predict(query: str):
        # engine.predict is synchronous right now, so we run it in a thread
        return await asyncio.to_thread(engine.predict, query, stream=False)

    tasks = [_run_predict(q) for q in params.queries]
    predictions = await asyncio.gather(*tasks, return_exceptions=True)

    for i, (query, pred) in enumerate(zip(params.queries, predictions)):
        results.append(f"## Query {i + 1}: {query}\n")

        if isinstance(pred, Exception):
            results.append(f"**Error:** Failed to execute query. {str(pred)}\n")
            continue

        results.append("### Response\n")
        results.append(f"{pred.get('response', 'No response generated.')}\n")

        sources = pred.get("sources", [])
        if sources:
            results.append("\n### Sources & Evidence\n")
            for src in sources:
                results.append(f"- **{src['filename']}** (Page {src['page']})")
        else:
            results.append("\n*No direct evidence found for this query.*\n")

        results.append("\n---\n")

    return "\n".join(results)


if __name__ == "__main__":
    # Default to stdio transport for local agent piping or inspection
    mcp.run()
