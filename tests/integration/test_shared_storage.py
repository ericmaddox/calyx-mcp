"""Persistence regressions, including independent processes sharing a store."""
import asyncio
import multiprocessing
import numpy as np
import pytest

from calyx_mcp.config import StorageConfig
from calyx_mcp.memory import MushroomBodyMemory
from calyx_mcp.reflex import ReflexDecisionEngine


def _writer(directory, name, ready, start, results):
    async def record():
        memory = MushroomBodyMemory(storage_cfg=StorageConfig(storage_dir=directory))
        ready.put(name)
        if not start.wait(15):
            raise TimeoutError("writer was not released")
        result = await memory.remember(f"def {name}(): return 1", "success")
        results.put((name, result["status"]))
    try:
        asyncio.run(record())
    except Exception as error:
        results.put((name, repr(error)))


@pytest.mark.asyncio
class TestSharedStorage:
    @pytest.fixture(autouse=True)
    def storage(self, tmp_path):
        self.root = tmp_path
        self.config = StorageConfig(storage_dir=str(self.root))

    async def test_custom_weights_filename_round_trip(self):
        for filename in ["weights.bin", "weights", "weights.npz"]:
            config = StorageConfig(storage_dir=str(self.root / filename), weights_filename=filename)
            memory = MushroomBodyMemory(storage_cfg=config)
            result = await memory.remember("def alpha(): return 1", "success")
            assert result["status"] == "recorded"
            assert memory.weights_path.exists(), filename
            reloaded = MushroomBodyMemory(storage_cfg=config)
            np.testing.assert_array_equal(reloaded.weights, memory.weights)
            assert reloaded.records == memory.records
            assert list(memory.storage_dir.glob(".tmp_*")) == []

    async def test_wrong_weight_shapes_recover_to_vector(self):
        memory = MushroomBodyMemory(storage_cfg=self.config)
        for shape in [(memory.kenyon_dim, 2), (memory.kenyon_dim, 1), (memory.kenyon_dim - 1,), ()]:
            np.savez_compressed(memory.weights_path, weights=np.full(shape, 2.0))
            reloaded = MushroomBodyMemory(storage_cfg=self.config)
            assert reloaded.weights.shape == (memory.kenyon_dim,), shape
            np.testing.assert_array_equal(reloaded.weights, np.ones(memory.kenyon_dim))

    async def _assert_process_writes_survive(self, simultaneous):
        context = multiprocessing.get_context("spawn")
        ready, results = context.Queue(), context.Queue()
        starts = [context.Event(), context.Event()]
        processes = [context.Process(target=_writer, args=(str(self.root), name, ready, start, results))
                     for name, start in zip(["alpha", "beta"], starts)]
        try:
            for process in processes:
                process.start()
            assert {ready.get(timeout=20), ready.get(timeout=20)} == {"alpha", "beta"}
            # Both processes have loaded the empty store before either mutation.
            if simultaneous:
                for start in starts:
                    start.set()
                acknowledgments = [results.get(timeout=20), results.get(timeout=20)]
            else:
                acknowledgments = []
                for start in starts:
                    start.set()
                    acknowledgments.append(results.get(timeout=20))
            assert set(acknowledgments) == {("alpha", "recorded"), ("beta", "recorded")}
            for process in processes:
                process.join(timeout=20)
                assert process.exitcode == 0
            memory = MushroomBodyMemory(storage_cfg=self.config)
            assert {r["code_snippet"] for r in memory.records} == {
                "def alpha(): return 1", "def beta(): return 1"
            }
            assert [r["id"] for r in memory.records] == ["rec_1", "rec_2"]
            reference = MushroomBodyMemory(storage_cfg=StorageConfig(storage_dir=str(self.root / "reference")))
            for record in memory.records:
                await reference.remember(record["code_snippet"], "success")
            np.testing.assert_allclose(memory.weights, reference.weights)
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                if process.pid is not None:
                    process.join(timeout=5)
            ready.close()
            results.close()

    async def test_stale_processes_preserve_both_acknowledged_writes(self):
        await self._assert_process_writes_survive(simultaneous=False)

    async def test_simultaneous_processes_preserve_both_writes(self):
        await self._assert_process_writes_survive(simultaneous=True)

    async def test_existing_reader_observes_other_client_and_reset(self):
        first = MushroomBodyMemory(storage_cfg=self.config)
        second = MushroomBodyMemory(storage_cfg=self.config)
        code = "def alpha(): return 1"
        await first.remember(code, "failure")
        assert (await second.get_state_metrics())["total_memories_stored"] == 1
        outcome = await ReflexDecisionEngine(second).evaluate_reflex(code)
        assert outcome.status == "avoid"
        assert outcome.valence < 1.0
        reset = await second.reset()
        assert reset["backup_created"]
        with np.load(reset["backup_path"], allow_pickle=False) as backup:
            np.testing.assert_array_equal(backup["weights"], first.weights)
        assert await first.query_similarity(code) == []
        await first.remember("def gamma(): return 1", "success")
        reloaded = MushroomBodyMemory(storage_cfg=self.config)
        assert [r["code_snippet"] for r in reloaded.records] == ["def gamma(): return 1"]
