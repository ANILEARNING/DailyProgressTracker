# utils/git_sync.py
import pandas as pd
from db.models import ENGINE
import git
import os

EXPORT_PATH = "data_exports"
CSV_FILE = os.path.join(EXPORT_PATH, "planner_items.csv")

def export_db_to_csv():
    # Ensure export folder exists
    os.makedirs(EXPORT_PATH, exist_ok=True)
    # read from SQLite
    df = pd.read_sql("SELECT * FROM planner_items", con=ENGINE)
    df.to_csv(CSV_FILE, index=False)
    return CSV_FILE

def git_commit_push(commit_msg="Auto-sync planner logs"):
    repo = git.Repo(".")
    repo.git.add(CSV_FILE)
    # allow committing when file is already staged/unchanged
    try:
        repo.index.commit(commit_msg)
    except Exception:
        # nothing to commit or other issue (ignore)
        pass
    # push if origin exists
    try:
        origin = repo.remote(name="origin")
        origin.push()
    except Exception:
        # remote may not be configured; ignore silently
        pass

def export_and_push(commit_msg="Auto-sync planner logs"):
    csv = export_db_to_csv()
    git_commit_push(commit_msg)
    return csv
