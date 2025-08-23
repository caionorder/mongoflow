# Contributing to MongoFlow

First off, thank you for considering contributing to MongoFlow!

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples**
- **Include Python version, MongoFlow version, and MongoDB version**

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide a detailed description of the suggested enhancement**
- **Provide specific examples to demonstrate the enhancement**
- **Explain why this enhancement would be useful**

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code, add tests
3. Ensure the test suite passes
4. Make sure your code follows the existing style
5. Issue the pull request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/mongoflow.git
cd mongoflow

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
make lint

# Format code
make format
```
## Style Guide
- Follow PEP 8
- Use type hints where possible
- Write docstrings for all public functions
- Keep line length to 100 characters
- Use Black for formatting

## Testing

- Write tests for any new functionality
- Ensure all tests pass before submitting PR
- Aim for high test coverage

## License
By contributing, you agree that your contributions will be licensed under the MIT License.
