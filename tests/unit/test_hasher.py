"""
Unit tests for Fly-LSH Tokenizer and Kenyon Cell Sparse Projection
"""
import pytest
import numpy as np
from calyx_mcp.hasher import FlyLSHHasher


def test_top_k_sparsity_invariants(hasher):
    code = "def add(a, b): return a + b"
    rep = hasher.hash_code(code)
    
    # 1. Total dimensions must be D=2048
    assert len(rep.binary_vector) == hasher.kenyon_cells
    
    # 2. Active bits count must equal active_k (102, ~5%)
    assert len(rep.active_indices) == hasher.active_k
    assert np.sum(rep.binary_vector) == hasher.active_k
    assert 0.045 <= rep.sparsity <= 0.055


def test_hashing_determinism(hasher):
    code = """async def fetch_user(user_id: int):
    return await db.query(user_id)"""
    rep1 = hasher.hash_code(code)
    rep2 = hasher.hash_code(code)
    
    assert np.array_equal(rep1.active_indices, rep2.active_indices)
    assert np.array_equal(rep1.binary_vector, rep2.binary_vector)


def test_multi_language_and_malformed_syntax_resilience(hasher):
    # TypeScript
    ts_code = "const calculateTax = (price: number): number => price * 0.2;"
    rep_ts = hasher.hash_code(ts_code)
    assert len(rep_ts.active_indices) == hasher.active_k

    # Rust
    rust_code = """fn main() {
    println!("Hello, world!");
}"""
    rep_rust = hasher.hash_code(rust_code)
    assert len(rep_rust.active_indices) == hasher.active_k

    # Malformed incomplete syntax (e.g. user typing)
    broken_code = "def foo(: while return"
    rep_broken = hasher.hash_code(broken_code)
    assert len(rep_broken.active_indices) == hasher.active_k


def test_semantic_hamming_proximity(hasher):
    code_a = """def process_order(order_id):
    validate(order_id)
    return db.save(order_id)"""

    # Code B: identical structure, slightly renamed variable
    code_b = """def process_order(item_id):
    validate(item_id)
    return db.save(item_id)"""

    # Code C: completely unrelated logic
    code_c = """class TextureRenderer:
    def render_gl_triangles(self, vbo):
        pass"""

    rep_a = hasher.hash_code(code_a)
    rep_b = hasher.hash_code(code_b)
    rep_c = hasher.hash_code(code_c)

    sim_ab = hasher.calculate_hamming_similarity(rep_a, rep_b)
    sim_ac = hasher.calculate_hamming_similarity(rep_a, rep_c)

    # Similar code must have high overlap (> 50%), unrelated must have near-zero overlap (< 25%)
    assert sim_ab > 0.50
    assert sim_ac < 0.25


def test_hasher_config_honored():
    from calyx_mcp.config import HasherConfig

    custom_cfg = HasherConfig(
        dense_dim=512,
        kenyon_cells=1024,
        active_k=50,
        seed=1337,
        ngram_min=2,
        ngram_max=3,
    )
    custom_hasher = FlyLSHHasher(config=custom_cfg)

    assert custom_hasher.dense_dim == 512
    assert custom_hasher.kenyon_cells == 1024
    assert custom_hasher.active_k == 50
    assert custom_hasher.seed == 1337
    assert custom_hasher.projection_matrix.shape == (1024, 512)

    code = "def sample(x): return x + 1"
    rep = custom_hasher.hash_code(code)
    assert len(rep.binary_vector) == 1024
    assert len(rep.active_indices) == 50

