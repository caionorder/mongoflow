# MongoFlow 🌊

Elegant MongoDB Object Document Mapper (ODM) for Python - with a fluent query builder that makes working with MongoDB a breeze! 🚀

## ✨ Features

- 🎯 **Intuitive Query Builder** - Fluent, chainable queries that feel natural
- ⚡ **High Performance** - Connection pooling, batch operations, and streaming
- 🔧 **Flexible** - Use as simple queries or full ODM with models
- 🎨 **Clean API** - Pythonic, fully typed, and well-documented
- 🚀 **Production Ready** - Battle-tested patterns with automatic retries
- 💾 **Smart Caching** - Optional Redis integration for blazing speed
- 🔄 **Async Support** - Full async/await support with Motor
- 📦 **Lightweight** - Minimal dependencies, maximum functionality

## 📦 Installation

```bash
# Basic installation
pip install mongoflow

# With all features
pip install mongoflow[all]

# With specific features
pip install mongoflow[cache]      # Redis caching
pip install mongoflow[validation] # Pydantic validation
pip install mongoflow[async]      # Async support
