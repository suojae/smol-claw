# Changelog

All notable changes to Smol Claw will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.2] - 2026-02-07

### Fixed
- 🚨 **Critical**: Fixed Discord bot parameter bug causing server crashes ([#13](https://github.com/suojae/smol-claw/pull/13))
  - `discord_bot` was incorrectly passed as positional argument, landing in `memory` parameter slot
  - This caused `AttributeError: 'DiscordBot' object has no attribute 'get_context'`
  - Now correctly passed as keyword argument: `discord_bot=discord_bot`
  - Fixes [#12](https://github.com/suojae/smol-claw/issues/12)

**Impact**: Server would crash immediately on startup when Discord bot was configured. This hotfix restores functionality.

## [0.0.1] - 2026-02-07

### Added
- 🦞 **Initial Release** - First stable version of Smol Claw!

#### Core Features
- Autonomous AI engine with 30-minute check intervals
- FastAPI web server with REST API endpoints
- Context collection (Git, TODO, calendar)
- Discord webhook integration for notifications

#### Memory Management 🧠
- SimpleMemory: JSON-based storage (zero dependencies)
- GuardrailMemory: Security-focused violation tracking
- Duplicate detection with 24-hour window
- Auto-summarization when exceeding 100 decisions
- Pattern learning from security violations

#### Security Protection 🛡️
- Pre-commit hooks for secrets detection
- CI/CD security checks in GitHub Actions
- 15+ sensitive pattern detection (API keys, passwords, tokens, etc.)
- `.env` file protection
- Comprehensive GUARDRAILS.md guide

#### Infrastructure
- GitHub Actions CI/CD pipeline
- Branch protection rules (main, develop)
- Test suite with pytest
- Quick start installation script (`quickstart.sh`)

#### Documentation
- README.md (English) and README.ko.md (Korean)
- CONTRIBUTING.md with commit conventions
- STRATEGY.md with competitive positioning
- GUARDRAILS.md with security best practices
- IMPROVEMENTS.md with roadmap

#### Developer Experience
- MIT License
- PR templates
- Code formatting with Black
- Linting with Flake8
- Cute crayfish branding 🦞

### Technical Stack
- Python 3.11+
- FastAPI 0.115.0
- discord.py 2.3.2
- python-dotenv 1.0.0
- aiohttp 3.10.0

### Installation
```bash
bash quickstart.sh
```

### What's Next (v0.0.2)
- Enhanced guardrails with command whitelist
- Plugin system for extensibility
- Web dashboard improvements
- Multi-LLM support (OpenAI, local models)

---

[0.0.1]: https://github.com/suojae/smol-claw/releases/tag/v0.0.1
