"""
Unit tests for Edge Cases, Input Invariants, Multi-Language & Large Codebase Resilience.
"""
import pytest
from calyx_mcp.hasher import FlyLSHHasher


@pytest.mark.asyncio
async def test_empty_and_whitespace_rejections(reflex_engine, memory):
    with pytest.raises(ValueError, match="non-empty string"):
        await reflex_engine.evaluate_reflex("")

    with pytest.raises(ValueError, match="non-empty string"):
        await reflex_engine.evaluate_reflex("   \n\t  ")


def test_massive_codebase_snippet_hashing(hasher):
    # Generate 150KB synthetic code snippet
    functions = [
        f"def fn_{i}(param_a: int, param_b: str) -> dict:\n    # Comment {i}\n    val = param_a * {i}\n    return {{'idx': {i}, 'res': val}}\n"
        for i in range(1200)
    ]
    huge_code = "\n".join(functions)
    assert len(huge_code) > 100_000

    rep = hasher.hash_code(huge_code)
    assert len(rep.active_indices) == hasher.config.active_k
    assert rep.sparsity < 0.06
    assert rep.binary_vector.shape == (2048,)


def test_multi_language_polyglot_determinism(hasher):
    snippets = [
        # Rust
        'fn handle_connection(mut stream: TcpStream) -> Result<(), io::Error> { let mut buffer = [0; 1024]; stream.read(&mut buffer)?; Ok(()) }',
        # TypeScript
        'export const fetchUserData = async (userId: string): Promise<User> => { const res = await fetch(`/api/users/${userId}`); return res.json(); };',
        # Go
        'func ServeHTTP(w http.ResponseWriter, r *http.Request) { fmt.Fprintf(w, "Hello, %s", r.URL.Path[1:]) }',
        # SQL
        'SELECT u.id, u.email, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id HAVING order_count > 5;',
        # JSON / Structured Data
        '{"name": "calyx", "version": "1.0.3", "dependencies": ["numpy>=1.21.0"], "active": true}'
    ]

    for code in snippets:
        rep1 = hasher.hash_code(code)
        rep2 = hasher.hash_code(code)
        assert (rep1.active_indices == rep2.active_indices).all()
        assert rep1.active_indices.shape == (102,)


def test_unicode_and_comments_resilience(hasher):
    code_with_unicode = (
        "# 🚀 Drosophila Mushroom Body Neural Reflex System\n"
        "# 日本語コメント: シナプス可塑性テスト\n"
        "def compute_delta(α: float, β: float) -> float:\n"
        "    return α * β + 3.14159\n"
    )
    rep = hasher.hash_code(code_with_unicode)
    assert len(rep.active_indices) == 102
