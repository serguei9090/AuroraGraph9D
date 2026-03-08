# Publishing AuroraGraph to PyPI

This guide outlines the exact, step-by-step process required to build and publish the **AuroraGraph** library leveraging `uv` and `maturin` (for our Rust extension).

---

## 1. Prerequisites

You must have the following tools installed and configured:
1. **Rust toolchain**: `rustup` installed.
2. **uv**: `astral-sh/uv` installed.
3. **Maturin**: Should be installed in the development environment (`uv sync --group dev`).
4. **PyPI Account**: A valid account on [PyPI](https://pypi.org/) and optionally a PyPI API Token configured.

## 2. Pre-Flight Checks

Before publishing, always ensure you have a clean slate and all tests pass.

```bash
# 1. Sync and update the lockfile safely
uv sync --all-extras

# 2. Format and Lint the codebase (enforced by Lefthook)
uv run ruff check --fix src/
uv run ruff format src/

# 3. Build the Rust extension in development mode
uv run maturin develop

# 4. Run your test suite
uv run pytest tests/
```

## 3. Version Bump

Update the version number to reflect your new release. You must update this in **two** places:

1. `pyproject.toml`
```toml
[project]
name = "auragraph"
version = "0.1.2"  # <-- Update here
```

2. `src/auragraph/__init__.py`
```python
__version__ = "0.1.2" # <-- Update here
```

*Optionally: update the `CHANGELOG.md` with release notes.*

## 4. Setting up PyPI OIDC (Trusted Publisher)

The absolute best and most modern way to publish to PyPI is using a **Trusted Publisher over OIDC** via GitHub Actions. Since AuroraGraph contains Rust extensions, you absolutely need to use GitHub Actions so that Windows, macOS, and Linux wheels are compiled individually without you having to build them manually on three different computers!

**What you need to do on PyPI.org:**
1. Navigate to: `Account settings > Publishing > Add a new pending publisher`
2. Fill out the form exactly like this:
   - **PyPI Project Name:** `auragraph` (or whatever you intend to claim if someone took it)
   - **Owner:** Your exact GitHub username (`serguei9090`) or organization.
   - **Repository name:** Your repo name (`AuroraGraph`).
   - **Workflow name:** `publish.yml` (this points to `.github/workflows/publish.yml`).
   - **Environment name:** `pypi` (optional, but highly recommended).

Click **Add**. You never need to generate an API token or password! PyPI will securely authenticate GitHub Actions anytime your repository attempts an upload.

## 5. Publishing to PyPI via GitHub Actions

I have already created the GitHub Action workflow for you at `.github/workflows/publish.yml`. It uses the official `maturin-action` to compile the Rust binary across Linux, macOS, and Windows simultaneously.

To instantly trigger the build and publish your library to PyPI, simply **create a Git Tag** matching `v*` and push it to GitHub:

```bash
git add .
git commit -m "chore: release version 0.1.2"
git push

# Create the release tag and push it
git tag v0.1.2
git push origin v0.1.2
```

Once pushed, go to the **Actions** tab on your GitHub repository. You will see the matrix spinning up 3 environments (Ubuntu, macOS, Windows) to build the Rust `.pyd`/`.so` interfaces. After it compiles, it securely downloads an OIDC token from PyPI and uploads all the cross-platform wheels!

## 6. Verify the Release

After a successful upload, go to a completely **new directory** to test the live package:

```bash
mkdir test_publish && cd test_publish

# Initialize a clean python environment
uv init
# Add your newly published package!
uv add auragraph[kuzu,fastembed,ollama]

# Test it
uv run python -c "from auragraph import AuroraGraphEngine; print(AuroraGraphEngine())"
```

Congratulations, the new version is live! 🚀
