from typing import List

from sentence_transformers import SentenceTransformer

from auragraph.core.config import config
from auragraph.providers.embeddings.base import BaseEmbeddingProvider


def _check_torch_flavor() -> tuple[bool, str]:
    """
    Inspect the installed torch build to determine if it is CPU-only.
    Returns (has_cuda_support, version_string).

    CPU-only torch wheels always include '+cpu' in their version string:
      '2.10.0+cpu'  → CPU-only
      '2.2.0+cu121' → CUDA 12.1 capable
    """
    try:
        import torch

        version = torch.__version__
        has_cuda = "+cpu" not in version and torch.cuda.is_available()
        return has_cuda, version
    except ImportError:
        return False, "not installed"


def _resolve_device(requested: str) -> str:
    """
    Resolve the best available device based on the user's preference.

    Priority when "auto":
        CUDA (NVIDIA GPU) → MPS (Apple Silicon) → CPU

    Explicit overrides:
        "cpu"  → always use CPU (suppresses GPU warnings)
        "cuda" → force CUDA (logs a clear warning if unavailable)
        "mps"  → force Apple Silicon GPU

    Smart behavior:
        When "auto" is set but only a CPU-only torch build is found, the
        engine falls back to CPU AND prints an exact, copy-pasteable command
        for the user to enable GPU support — no crashes, no silent failures.
    """
    if requested == "cpu":
        print("[Embedder] ℹ️  CPU mode forced (AURA_DEVICE=cpu).")
        return "cpu"

    try:
        import torch

        # ── CUDA (NVIDIA) ────────────────────────────────────────────────────
        if requested in ("auto", "cuda"):
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                print(f"[Embedder] ✅ CUDA GPU detected: {gpu_name}")
                return "cuda"

            _, version = _check_torch_flavor()
            if "+cpu" in version:
                # CPU-only torch installed — guide the user to fix it
                print(f"\n[Embedder] ⚠️  CPU-only PyTorch detected (torch {version}).")
                print("[Embedder]    GPU acceleration is NOT available with this build.")
                print("[Embedder]")
                print("[Embedder]    ── To enable NVIDIA GPU: ──────────────────────────────────────")
                print("[Embedder]    pip install torch --index-url https://download.pytorch.org/whl/cu121")
                print("[Embedder]")
                print("[Embedder]    ── Or, if using this as an installed library: ──────────────────")
                print("[Embedder]    pip install auragraph-10d[cuda]")
                print("[Embedder]    ──────────────────────────────────────────────────────────────")
                print("[Embedder]    Falling back to CPU. Set AURA_DEVICE=cpu to suppress this warning.\n")
            elif requested == "cuda":
                # CUDA-build torch is installed but CUDA runtime unavailable
                print("[Embedder] ⚠️  AURA_DEVICE=cuda requested, but torch.cuda.is_available() == False.")
                print("[Embedder]    Check: NVIDIA drivers, CUDA toolkit, or GPU availability.")
                print("[Embedder]    Falling back to CPU.\n")

        # ── MPS (Apple Silicon) ───────────────────────────────────────────────
        if requested in ("auto", "mps"):
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                print("[Embedder] ✅ Apple Silicon GPU (MPS) detected.")
                return "mps"
            if requested == "mps":
                print("[Embedder] ⚠️  MPS requested but not available on this system.")
                print("[Embedder]    Falling back to CPU.\n")

    except ImportError:
        print("[Embedder] ⚠️  PyTorch is not installed. Embeddings will not be available.")
        print("[Embedder]    Install with: pip install auragraph-10d[embeddings]")

    return "cpu"


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """
    Semantic embedding provider using sentence-transformers/all-MiniLM-L6-v2.
    Produces 384-dimensional vectors.

    Device resolution order (AURA_DEVICE=auto, the default):
        CUDA (NVIDIA) → MPS (Apple Silicon) → CPU

    If a GPU build is desired but the current torch is CPU-only, the engine:
      • Falls back to CPU gracefully (no crash).
      • Prints a clear, copy-pasteable command to upgrade to a GPU build.

    Control via environment variable:
        AURA_DEVICE=auto    best available device (default)
        AURA_DEVICE=cpu     always CPU, suppresses GPU warnings
        AURA_DEVICE=cuda    force NVIDIA GPU
        AURA_DEVICE=mps     force Apple Silicon GPU

    Or pass --device <value> to the ingest_knowledge.py CLI script.

    Library users install GPU support via extras:
        pip install auragraph-10d[cuda]     NVIDIA GPU
        pip install auragraph-10d[mps]      Apple Silicon GPU
        pip install auragraph-10d[embeddings]  CPU-only (default)
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str | None = None):
        requested = device or config.AURA_DEVICE
        self.device = _resolve_device(requested)
        print(f"[Embedder] Device selected: {self.device.upper()} (requested: '{requested}')")
        self.model = SentenceTransformer(model_name, device=self.device)

    def embed_text(self, text: str) -> List[float]:
        """Embed a single string. Returns a list of 384 floats."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Batch encode for throughput — especially important on GPU where
        a single batched call is dramatically faster than many single calls.
        """
        embeddings = self.model.encode(texts, batch_size=64, convert_to_numpy=True, show_progress_bar=False)
        return embeddings.tolist()
