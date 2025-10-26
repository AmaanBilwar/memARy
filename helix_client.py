import helix

# Single, reusable Helix client for the application.
# Local instance configured via helix.toml (port 6969).
db = helix.Client(local=True, verbose=True)

def run_query(name: str, payload):
    """Convenience wrapper to execute a named Helix query with a payload."""
    return db.query(name, payload)


