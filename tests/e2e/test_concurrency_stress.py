"""
High-concurrency stress test for Calyx MCP server.
Simulates 50 simultaneous agent requests to verify async lock correctness and thread safety.
"""
import pytest
import asyncio


@pytest.mark.asyncio
async def test_concurrent_tool_execution(server):
    async def worker(worker_id: int):
        # 1. Evaluate reflex
        await server.handle_request({
            "jsonrpc": "2.0",
            "id": worker_id * 10 + 1,
            "method": "tools/call",
            "params": {
                "name": "check_code_reflex",
                "arguments": {"code": f"def worker_code_{worker_id}(): return {worker_id}"}
            }
        })

        # 2. Remember outcome
        outcome = "success" if worker_id % 2 == 0 else "failure"
        err = f"Error in worker {worker_id}" if outcome == "failure" else None
        await server.handle_request({
            "jsonrpc": "2.0",
            "id": worker_id * 10 + 2,
            "method": "tools/call",
            "params": {
                "name": "remember_code_outcome",
                "arguments": {
                    "code": f"def worker_code_{worker_id}(): return {worker_id}",
                    "outcome": outcome,
                    "error_message": err
                }
            }
        })

        # 3. Query similarity
        await server.handle_request({
            "jsonrpc": "2.0",
            "id": worker_id * 10 + 3,
            "method": "tools/call",
            "params": {
                "name": "query_associative_memory",
                "arguments": {"query_code": f"def worker_code_{worker_id}(): return {worker_id}"}
            }
        })

    # Spawn 50 concurrent async workers
    tasks = [worker(i) for i in range(50)]
    await asyncio.gather(*tasks)

    # Verify final state metrics are coherent
    metrics_res = await server.handle_request({
        "jsonrpc": "2.0",
        "id": 9999,
        "method": "tools/call",
        "params": {
            "name": "inspect_memory_state",
            "arguments": {}
        }
    })
    assert "result" in metrics_res
    content_text = metrics_res["result"]["content"][0]["text"]
    assert '"total_memories_stored": 50' in content_text
