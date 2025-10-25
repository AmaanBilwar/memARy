import os, shutil, datetime
from db.chroma_init.config import ChromaConfig

SNAP_DIR = './var/chroma-snapshots'

if __name__ == '__main__':
    cfg = ChromaConfig()
    ts = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    dst = os.path.join(SNAP_DIR, f'snapshot-{ts}')
    os.makedirs(SNAP_DIR, exist_ok=True)
    # Copy directory tree for simple filesystem snapshot
    shutil.copytree(cfg.persist_directory, dst, dirs_exist_ok=False)
    print('Snapshot created at', dst)
