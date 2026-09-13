"""
Fly-LSH Tokenizer & Sparse Projection Engine
Implements Calyx -> Kenyon Cell Winner-Take-All projection (Dasgupta et al., Science 2017)
"""

import ast
import re
import zlib
import numpy as np
from typing import List, Set, Tuple, Dict, Any, Optional
from dataclasses import dataclass
from .config import HasherConfig


@dataclass
class KenyonSparseRepresentation:
    """Represents a sparse active Kenyon Cell firing vector"""
    active_indices: np.ndarray   # Indices of active neurons (length k)
    dense_projection: np.ndarray # Intermediate projected vector (length D)
    binary_vector: np.ndarray    # Full binary vector {0, 1}^D
    source_tokens_count: int
    sparsity: float


class FlyLSHHasher:
    """
    Multi-language AST & token n-gram tokenizer with deterministic Fly-LSH projection
    """

    COMMON_SYNTAX_TOKENS: Set[str] = {
        "def", "return", "class", "function", "const", "let", "var", "import",
        "from", "if", "else", "elif", "for", "while", "try", "catch", "except",
        "public", "private", "fn", "struct", "impl", "package", "type", "interface",
        "true", "false", "none", "null", "self", "this"
    }

    def __init__(self, config: Optional[HasherConfig] = None):
        self.config = config or HasherConfig()
        self.dense_dim = self.config.dense_dim
        self.kenyon_cells = self.config.kenyon_cells
        self.active_k = self.config.active_k
        self.seed = self.config.seed

        # Generate deterministic random projection matrix M in {-1, 1}^(D x d)
        rng = np.random.RandomState(self.seed)
        self.projection_matrix = rng.choice([-1.0, 1.0], size=(self.kenyon_cells, self.dense_dim))

    def extract_features(self, code: str) -> np.ndarray:
        """
        Tokenize code using hybrid AST grammar + structural token extraction into a normalized d-dimensional vector.
        Guaranteed deterministic and resilient to any programming language or syntax.
        """
        tokens: List[Tuple[str, float]] = []

        # 1. Structural AST grammar normalization
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                node_type = type(node).__name__
                tokens.append((f"ast:{node_type}", 2.0))
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    tokens.append((f"fn:{node.name}", 3.0))
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        tokens.append((f"call:{node.func.id}", 2.5))
                    elif isinstance(node.func, ast.Attribute):
                        tokens.append((f"call_attr:{node.func.attr}", 2.5))
        except Exception:
            pass  # Fallback to lexical token stream for non-Python or broken syntax

        # 2. Universal Lexical & Identifier Extraction
        words = re.findall(r'[A-Za-z_][A-Za-z0-9_]*|==|!=|<=|>=|&&|\|\||->|\+=|-=', code)
        clean_words = []
        for w in words:
            w_lower = w.lower()
            clean_words.append(w_lower)
            if w_lower in self.COMMON_SYNTAX_TOKENS:
                tokens.append((f"kw:{w_lower}", 1.0))
            else:
                tokens.append((f"sym:{w_lower}", 1.5))

        # 3. Word Bigrams for structural syntax matching
        for i in range(len(clean_words) - 1):
            bigram = f"bi:{clean_words[i]}_{clean_words[i+1]}"
            tokens.append((bigram, 1.2))

        if not tokens:
            tokens = [("empty:code", 1.0)]

        # 4. Hash tokens deterministically into d-dimensional vector via CRC32
        dense_vec = np.zeros(self.dense_dim, dtype=np.float32)
        for tok_str, weight in tokens:
            h = zlib.crc32(tok_str.encode('utf-8'))
            bucket = h % self.dense_dim
            sign = 1.0 if (h // self.dense_dim) % 2 == 0 else -1.0
            dense_vec[bucket] += sign * weight

        # Normalize dense vector
        norm = np.linalg.norm(dense_vec)
        if norm > 1e-6:
            dense_vec /= norm

        return dense_vec

    def hash_code(self, code: str) -> KenyonSparseRepresentation:
        """
        Projects code features into the high-dimensional Kenyon Cell layer (D=2048)
        and applies Winner-Take-All (WTA) sparsity (top ~5% active bits).
        """
        dense_vec = self.extract_features(code)
        
        # Linear expansion projection: y = M * dense_vec
        projected = np.dot(self.projection_matrix, dense_vec)  # shape: (D,)

        # Winner-Take-All (Top-k activation)
        k = min(self.active_k, len(projected))
        top_k_indices = np.argpartition(projected, -k)[-k:]
        top_k_indices = np.sort(top_k_indices)

        # Create binary representation vector
        binary_vec = np.zeros(self.kenyon_cells, dtype=np.int8)
        binary_vec[top_k_indices] = 1

        sparsity = len(top_k_indices) / float(self.kenyon_cells)

        return KenyonSparseRepresentation(
            active_indices=top_k_indices,
            dense_projection=projected,
            binary_vector=binary_vec,
            source_tokens_count=len(code.split()),
            sparsity=sparsity
        )

    def calculate_hamming_similarity(self, rep_a: KenyonSparseRepresentation, rep_b: KenyonSparseRepresentation) -> float:
        """
        Calculates Kenyon cell overlap ratio between two representations.
        Returns value in [0.0, 1.0].
        """
        set_a = set(rep_a.active_indices.tolist())
        set_b = set(rep_b.active_indices.tolist())
        intersection = len(set_a.intersection(set_b))
        min_len = min(len(set_a), len(set_b))
        if min_len == 0:
            return 1.0
        return float(intersection) / float(min_len)
