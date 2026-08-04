# Contributing to Vortex (`vortex-ai`)

Thank you for your interest in contributing to **Vortex**! We welcome contributions from open-source developers, AI systems researchers, and infrastructure engineers.

---

## Code of Conduct

Vortex adheres to standard open-source community standards. Please maintain professional, constructive, and respectful interactions across issues, pull requests, and discussions.

---
## Development Setup

```bash
# Clone the repository
git clone https://github.com/Akgithub2028/vortex.git
cd vortex

# Initialize virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

## Running Tests & Formatting

Before opening a pull request, verify that all unit and integration tests pass and code coverage meets the project target **(Strict >90%)**:

```bash
# Run pytest with code coverage enforcement
make test-cov

# Format code
make format

# Run linter
make lint

# Run type-checking
make type-check
```

---

## Adding a New Model Provider

Vortex uses a unified `Gateway` pattern. To add a new LLM provider (e.g., Cohere, Mistral):

1. **Create Adapter**: Add a new file in `src/vortex/gateway/providers/` that implements the `BaseProvider` abstract base class.
2. **Implement Methods**: You must implement `chat_completion()` and handle provider-specific exceptions, translating them to `VortexError`.
3. **Registry**: Register your provider string (e.g., `mistral/mistral-large`) in the `ProviderRegistry` located in `src/vortex/gateway/router.py`.
4. **Mock Tests**: Ensure you mock the provider API in `tests/unit/gateway/` to verify fallback mechanisms work as expected without network calls.

---

## Submitting Pull Requests

1. Fork the repository and create a feature branch (`git checkout -b feature/my-feature`).
2. Add comprehensive unit tests for any new nodes, providers, or API endpoints.
3. Verify that `make test-cov` passes cleanly with >90% coverage.
4. Commit your changes (`git commit -m "feat(gateway): add custom mistral provider adapter"`).
5. Push to your fork and create a Pull Request detailing changes and verification steps.
