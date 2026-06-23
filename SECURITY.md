# 4. Auth0_Application_Manager — SECURITY.md

```markdown
# Security Policy

## Project Security Scope

This repository contains scripts or tooling for managing Auth0 applications through the Auth0 Management API.

Because application management may involve client IDs, client secrets, callback URLs, grant types, API permissions, and tenant configuration, this repository must be handled as security-sensitive.

## Reporting a Security Issue

If you discover a security issue in this repository, do not open a public GitHub issue.

Report the issue privately to the repository owner or maintainer.

Please include:

- Repository name
- File or script affected
- Description of the issue
- Steps to reproduce, if applicable
- Whether Auth0 credentials, application secrets, Management API tokens, or tenant configuration may be exposed
- Recommended remediation, if known

## Sensitive Data That Must Not Be Committed

Do not commit:

- Auth0 client secrets
- Auth0 Management API client secrets
- Auth0 Management API access tokens
- Application secrets
- `.env` files
- Private keys
- Production tenant configuration
- Customer-specific application configuration
- Internal callback URLs unless explicitly approved
- Refresh tokens or access tokens

## Credential Handling

Auth0 credentials must not be hardcoded in source files.

Use environment variables, command-line prompts, or an approved secret manager for sensitive values.

Sensitive values include:

- `AUTH0_DOMAIN`
- `AUTH0_CLIENT_ID`
- `AUTH0_CLIENT_SECRET`
- `AUTH0_AUDIENCE`
- `AUTH0_MANAGEMENT_API_TOKEN`

Only placeholder values should appear in committed examples or documentation.

## Application Configuration Risks

Application configuration can be sensitive even if it is not a password.

Review before committing:

- Callback URLs
- Logout URLs
- Allowed web origins
- Grant types
- Application type
- API audience
- Signing algorithm
- Token lifetime settings
- Refresh token settings
- Allowed connections

Do not commit customer-specific or production configuration unless explicitly approved.

## If a Secret Is Accidentally Committed

If an Auth0 secret, token, credential, or sensitive application configuration is committed:

1. Treat the credential as compromised.
2. Rotate the exposed credential immediately in Auth0.
3. Remove the secret from the repository.
4. Review Git history for previous exposure.
5. Review Auth0 logs for suspicious Management API activity.
6. Confirm whether application settings were changed unexpectedly.
7. Notify the project owner or maintainer.

Redacting the file is not enough if a secret was already committed. The credential must be rotated.

## Secure Coding Expectations

Before committing changes:

- Do not hardcode secrets.
- Do not log tokens or client secrets.
- Use least-privilege Management API scopes.
- Validate input files before making Auth0 changes.
- Clearly document destructive operations.
- Include dry-run mode where possible.
- Document required Auth0 scopes and assumptions.
- Avoid storing full API responses if they include sensitive fields.

## Supported Use

This repository is intended for controlled Auth0 application management, training, and internal automation unless otherwise stated.

Security-sensitive changes should be reviewed before being merged.