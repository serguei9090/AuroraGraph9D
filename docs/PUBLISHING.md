# AuroraGraph: PyPI Publishing Roadmap 📦

This guide outlines the steps required to transform the AuroraGraph codebase into a publishable Python library on PyPI.

---

## 🏗️ 1. Project Restructuring

To be a compliant Python package, we need to strictly separate the application logic from the library logic.

### Structural Goal:
```bash
auragraph/
├── src/
│   └── auragraph/
│       ├── __init__.py
│       ├── core/
│       ├── db/
│       └── providers/
├── src-rust/
│   ├── Cargo.toml
│   └── src/lib.rs
├── pyproject.toml
└── README.md
```

---

## ⚙️ 2. Maturin & PyO3 Configuration

Since we have a Rust core, we use **Maturin** to build and publish the wheel.

### Step-by-Step Configuration:

1.  **Update `pyproject.toml`**:
    Ensure the `[build-system]` and `[project]` sections are correctly configured for Maturin.
    ```toml
    [build-system]
    requires = ["maturin>=1.0,<2.0"]
    build-backend = "maturin"

    [project]
    name = "auragraph"
    dynamic = ["version"]
    description = "Deterministic Knowledge Graph RAG with Rust Core"
    dependencies = [
        "prometheus-client>=0.20.0",
        "fastapi>=0.110.0",
        "kuzu>=0.3.0",
        "neo4j>=5.0.0"
    ]
    ```

2.  **Configure `Cargo.toml`**:
    Ensure `crate-type = ["cdylib"]` is set for Python bindings.

---

## 🚀 3. CI/CD Workflow (GitHub Actions)

To publish safely, use a GitHub Action that builds wheels for all platforms (Windows, Linux, macOS).

### Sample `.github/workflows/PyPI.yml`:
```yaml
name: Publish to PyPI
on:
  push:
    tags: ['v*']

jobs:
  build_wheels:
    name: Build wheels on ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: PyO3/maturin-action@v1
        with:
          command: build
          args: --release --out dist
      - name: Upload wheels
        uses: actions/upload-artifact@v4
        with:
          name: wheels-${{ matrix.os }}
          path: dist

  publish:
    name: Publish to PyPI
    needs: [build_wheels]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          path: dist
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
```

---

## 🏁 4. Final Checklist

- [ ] **Versioning**: Ensure `__init__.py` or `pyproject.toml` handles dynamic versioning correctly.
- [ ] **Exclusions**: Ensure `.gitignore` and `MANIFEST.in` exclude local `.db` files and environment variables.
- [ ] **Docs**: All library methods should have Google-style docstrings for `pydoc` generation.
- [ ] **Tests**: 80%+ coverage on the core retrieval logic.

Once complete, run:
```bash
uv run maturin publish
```
