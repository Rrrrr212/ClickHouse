# ClickHouse Repository Restructure Proposal

## Overview

This proposal outlines a structured reorganization of the ClickHouse repository to improve maintainability, clarity, and developer experience.

## 1. Documentation & Installation Separation

### Goal
Move installation scripts and related tools into a dedicated, self-contained module.

### Changes Made
```
tools/
└── installer/
    ├── README.md
    ├── config.sh
    ├── detect.sh
    └── install.sh
```

### Benefits
- **Modularity**: Installation tools are now independent and easier to maintain
- **Versioning**: Installer changes can be tracked separately from core code
- **Reusability**: Installer module can be shared or forked more easily
- **Testing**: Dedicated tests for installation logic
- **Documentation**: Clear, self-documenting structure

### Usage
```bash
# Quick install
curl https://clickhouse.com/ | sh

# Advanced usage
./tools/installer/install.sh --version 26.5.1.882
```

## 2. Community Configuration Modularization

### Goal
Centralize all community-related links, channels, and event information into a single, easily updatable configuration.

### Changes Made
```
.community/
├── config.json
└── tools/
    └── render_readme.py
```

### Benefits
- **Single Source of Truth**: All community links in one place
- **Easy Updates**: Change links without modifying README.md
- **Automation**: Can generate sections of README automatically
- **Localization**: Easier to add multi-language support
- **History**: Track community link changes separately

### Configuration Example
```json
{
  "channels": {
    "slack": "https://clickhouse.com/slack",
    "telegram": "https://telegram.me/clickhouse_en"
  },
  "release": {
    "current": "26.5",
    "call_url": "..."
  }
}
```

## 3. Release Process Scripting

### Goal
Automate the monthly release checklist and standardize the release process.

### Changes Made
```
tools/release/
├── README.md
├── config.yaml
├── checklist.yaml
└── release_manager.py
```

### Benefits
- **Consistency**: Standardized release process every time
- **Automation**: Reduce manual steps and human error
- **Audit Trail**: Track release progress and decisions
- **Speed**: Faster release cycles with pre-flight automation
- **Quality**: Ensure critical checks are not skipped

### Checklist Items
- ✅ CI Status Verification
- ✅ Documentation Updates
- ✅ Performance Test Results  
- ✅ Security Audit
- ✅ Release Notes Preparation
- ✅ Community Announcement

### Usage
```bash
# Start a new release
python3 tools/release/release_manager.py --type new --version 26.6

# Create a patch release
python3 tools/release/release_manager.py --type patch --version 26.5.2

# Run checks only
python3 tools/release/release_manager.py --checks-only
```

## Repository Structure After Changes

```
ClickHouse/
├── .community/              # Community configuration
│   ├── config.json
│   └── tools/
├── .github/                 # GitHub workflows (unchanged)
├── docs/                    # Documentation
│   └── development/
│       └── repo_restructure_proposal.md
├── programs/                # Core programs (unchanged)
├── tests/                   # Tests (unchanged)
├── tools/                   # New dedicated tools directory
│   ├── installer/
│   └── release/
└── utils/                   # Existing utilities (unchanged)
```

## Migration Plan

1. **Phase 1**: Adopt new directory structure (completed)
2. **Phase 2**: Update documentation references
3. **Phase 3**: Migrate existing installation scripts
4. **Phase 4**: Integrate release automation with CI/CD
5. **Phase 5**: Add automation for README generation

## Next Steps

- [ ] Review and finalize the proposal
- [ ] Implement CI/CD integration for new tools
- [ ] Write comprehensive tests for new modules
- [ ] Update developer documentation
- [ ] Train team on new workflow

## Conclusion

This restructuring improves the ClickHouse repository's organization by:

1. Separating concerns between core code, tools, and community configs
2. Automating repetitive tasks like releases and updates
3. Making the codebase more approachable for new contributors
4. Reducing the chance of human error in critical processes
5. Providing a clear path for future improvements

This approach maintains backward compatibility while laying the groundwork for a more maintainable and scalable repository structure.
