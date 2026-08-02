# Network Policy

Only `scripts/release_skill.py` may use network access. It may push the current skill repository to its configured `github.com` origin and read the public `api.github.com` Release endpoint for the generated version tag. Arbitrary hosts, custom API endpoints, target-project artifacts and credentials are outside this boundary.
