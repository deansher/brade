# Plan for Improving Brade's Release Process

Brade and Dean are using this document to support their collaborative process. Brade is an AI software engineer collaborating with Dean through the Brade application. We are working together to enhance the Brade application's release process.

## Requirements

- Enable automated PyPI releases (currently disabled)
- Add release notes/changelog management
- Add release candidate testing
- Ensure version synchronization between PyPI and Docker releases
- Add automated testing of Docker images before pushing

## Current State Analysis

### PyPI Release Workflow (.github/workflows/release.yml)
- Currently disabled ("never" branch)
- Triggers on workflow_dispatch and version tags
- Uses Python build and twine for PyPI publishing

### Docker Release Workflow (.github/workflows/docker-release.yml)
- Builds multi-arch images (amd64, arm64)
- Pushes to DockerHub with appropriate tags
- TODO comment about adding automated testing

## Implementation Tasks

### ( ) Enable PyPI Release Workflow

- ( ) Update release.yml to trigger on main-brade branch
- ( ) Test PyPI credentials
- ( ) Document PyPI release process in CONTRIBUTING.md

### ( ) Add Release Notes Management

- ( ) Create CHANGELOG.md template
- ( ) Add release notes section to PR template
- ( ) Document changelog update process
- ( ) Automate changelog updates in release workflow

### ( ) Implement Release Candidate Process

- ( ) Define RC version numbering (e.g., v1.2.3-rc1)
- ( ) Add RC workflow for testing releases
- ( ) Create test matrix for RCs
- ( ) Document RC process

### ( ) Version Synchronization

- ( ) Add version check between PyPI and Docker releases
- ( ) Ensure consistent version numbers
- ( ) Document version numbering rules
- ( ) Add version validation to workflows

### ( ) Docker Image Testing

- ( ) Define Docker test matrix
- ( ) Add smoke tests for images
- ( ) Add feature verification tests
- ( ) Add security scanning
- ( ) Document Docker testing process

## Testing Strategy

### Unit Tests
- Test version validation
- Test changelog formatting
- Test RC numbering logic

### Integration Tests
- Test PyPI release process
- Test Docker build and push
- Test version synchronization
- Test release candidate workflow

### Manual Testing Checklist
- PyPI release verification
- Docker image verification
- Version consistency checks
- Documentation accuracy

## Implementation Strategy

We will implement these improvements incrementally:

1. First enable PyPI releases and add basic testing
2. Add changelog management
3. Implement RC process
4. Add version synchronization
5. Enhance Docker testing

For each phase:
1. Update workflows
2. Add tests
3. Update documentation
4. Manual verification
5. Release test cycle

## Findings and Notes

This section will be updated as we implement the improvements and discover additional requirements or issues.
