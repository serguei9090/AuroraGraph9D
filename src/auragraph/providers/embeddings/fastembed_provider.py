"""
FastEmbed Embedding Provider for AuroraGraph.
=============================================
Uses Qdrant's fastembed library backed by Rust + ONNX Runtime.

Advantages over PyTorch/sentence-transformers:
  - No PyTorch dependency (saves ~2 GB).
  - CUDA support works out-of-the-box on Windows — no custom index URLs.
  - 2–3x faster on CPU, comparable speed on GPU.
  - Tiny install: ~100 MB total.

GPU Install:
    pip install fastembed-gpu        # NVIDIA CUDA
    pip install fastembed            # CPU-only

Control via AURA_DEVICE env var or --device CLI flag.
"""

from typing import List

from auragraph.core.config import config
from auragraph.providers.embeddings.base import BaseEmbeddingProvider


def _check_fastembed_gpu() -> bool:
    """Returns True if fastembed-gpu (CUDA) is installed and available."""
    try:
        # fastembed-gpu exposes CUDAExecutionProvider in onnxruntime
        import onnxruntime as ort

        return "CUDAExecutionProvider" in ort.get_available_providers()
    except ImportError:
        return False


def _resolve_providers(requested: str) -> list[str]:
    """
    Determine the ONNX Runtime execution providers to use.

    fastembed accepts a list of ORT providers in priority order.
    Ref: https://onnxruntime.ai/docs/execution-providers/

    Returns a list like:
        ["CUDAExecutionProvider", "CPUExecutionProvider"]  # GPU preferred
        ["CPUExecutionProvider"]                           # CPU only
    """
    if requested == "cpu":
        print("[FastEmbed] ℹ️  CPU mode forced (AURA_DEVICE=cpu).")
        return ["CPUExecutionProvider"]

    cuda_available = _check_fastembed_gpu()

    if requested in ("auto", "cuda"):
        if cuda_available:
            print("[FastEmbed] ✅ CUDA available via fastembed-gpu (ONNX Runtime).")
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]

        # Not available — guide the user
        try:
            import fastembed  # noqa: F401

            print("\n[FastEmbed] ⚠️  CPU-only fastembed detected — GPU not available.")
            print("[FastEmbed]    To enable NVIDIA GPU acceleration:")
            print("[FastEmbed]    pip uninstall fastembed && pip install fastembed-gpu")
            print("[FastEmbed]    Or as a library: pip install auragraph-10d[cuda]")
            print("[FastEmbed]    Falling back to CPU. Set AURA_DEVICE=cpu to suppress.\n")
        except ImportError:
            print("\n[FastEmbed] ⚠️  fastembed is not installed.")
            print("[FastEmbed]    CPU:  pip install fastembed")
            print("[FastEmbed]    GPU:  pip install fastembed-gpu\n")

        if requested == "cuda":
            print("[FastEmbed] ⚠️  AURA_DEVICE=cuda was forced but GPU is not available.")

    if requested == "mps":
        # ONNX Runtime does not support Apple MPS yet — fall back to CoreML
        print("[FastEmbed] ℹ️  MPS requested. Trying CoreML provider (Apple Silicon).")
        return ["CoreMLExecutionProvider", "CPUExecutionProvider"]

    return ["CPUExecutionProvider"]


class FastEmbedProvider(BaseEmbeddingProvider):
    """
    Drop-in replacement for LocalEmbeddingProvider using Qdrant's fastembed.

    Backed by Rust + ONNX Runtime — no PyTorch required.
    CUDA just works on Windows with `pip install fastembed-gpu`.

    Model: BAAI/bge-small-en-v1.5 (384-dim, same dim as all-MiniLM-L6-v2)
    Options: https://qdrant.github.io/fastembed/examples/Supported_Models/
    """

    # Maps to the same 384-dim space as all-MiniLM-L6-v2 used by LocalEmbeddingProvider
    DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"

    def __init__(self, model_name: str | None = None, device: str | None = None):
        try:
            from fastembed import TextEmbedding
        except ImportError:
            raise RuntimeError(
                "fastembed is not installed. Run: pip install fastembed\nFor GPU: pip install fastembed-gpu"
            )

        requested = device or config.AURA_DEVICE
        providers = _resolve_providers(requested)
        self.device = "cuda" if "CUDAExecutionProvider" in providers else "cpu"

        model = model_name or self.DEFAULT_MODEL
        print(f"[FastEmbed] Loading model: {model}")

        # Pass providers to fastembed so it uses our resolved ONNX EP chain
        self.model = TextEmbedding(
            model_name=model,
            providers=providers,
        )
        print(f"[FastEmbed] Device: {self.device.upper()} (requested: '{requested}')")

    def embed_text(self, text: str) -> List[float]:
        """Embed a single string. Returns a 384-dim float list."""
        return next(self.model.embed([text])).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Batch encode — fastembed is already highly optimized for batching.
        This is the preferred path for ingestion.
        """
        return [e.tolist() for e in self.model.embed(texts)]
