# app.py
import streamlit as st
from db.models import init_db, SessionLocal, PlannerItem
from datetime import date, datetime
from utils.git_sync import export_and_push
import streamlit_authenticator as stauth
from typing import Optional
import pandas as pd

# initialize DB
init_db()
session_db = SessionLocal()

# ---------- Simple auth (local passwords hashed) ----------
names = ["Anish"]
usernames = ["anish"]
passwords = ["anishpass"]  # change in production
hashed_passwords = stauth.Hasher(passwords).generate()

credentials = {
    "usernames": {
        usernames[0]: {
            "name": names[0],
            "password": hashed_passwords[0]
        }
    }
}
authenticator = stauth.Authenticate(
    credentials,
    cookie_name="planner_cookie",
    key="some_random_key_please_change",
    cookie_expiry_days=30
)

name, auth_status, username = authenticator.login("Login", "main")

def sidebar_user_info():
    if auth_status:
        st.sidebar.write(f"**User:** {name}")
        authenticator.logout("Logout", "sidebar")
    else:
        st.sidebar.write("Please log in to use the planner.")

# ---------- Helpers ----------
def get_items(user: str, selected_category: Optional[str] = None, search: Optional[str] = None, for_date: Optional[date] = None):
    q = session_db.query(PlannerItem).filter(PlannerItem.user == user)
    if selected_category and selected_category != "All":
        q = q.filter(PlannerItem.category == selected_category)
    if for_date:
        q = q.filter(PlannerItem.date == for_date)
    if search:
        q = q.filter(PlannerItem.task_name.ilike(f"%{search}%"))
    return q.order_by(PlannerItem.date.desc(), PlannerItem.id.desc()).all()

def add_item(user: str, item_date: date, category: str, name: str, details: str, xp: int):
    item = PlannerItem(user=user, date=item_date, category=category, task_name=name, details=details, xp=xp)
    session_db.add(item)
    session_db.commit()
    return item

def update_item(item_id: int, **fields):
    item = session_db.query(PlannerItem).get(item_id)
    if not item:
        return None
    for k, v in fields.items():
        setattr(item, k, v)
    session_db.commit()
    return item

def delete_item(item_id: int):
    item = session_db.query(PlannerItem).get(item_id)
    if not item:
        return False
    session_db.delete(item)
    session_db.commit()
    return True

# ---------- UI ----------
st.set_page_config(page_title="Planner — Add / Modify", layout="wide")
st.title("🧾 Planner — Add & Modify Items")

sidebar_user_info()

if not auth_status:
    if auth_status is False:
        st.error("Username/password incorrect")
    st.stop()

# -- Top panel: Add new item form
with st.expander("➕ Add New Planner Item", expanded=True):
    col1, col2, col3 = st.columns([2,2,1])
    with col1:
        item_name = st.text_input("Task name", placeholder="e.g., Python practice / Drink 500ml water")
        category = st.selectbox("Category", ["Learning", "Health", "Spiritual", "Content", "Work", "Other"])
    with col2:
        item_date = st.date_input("Date", value=date.today())
        xp = st.number_input("XP", min_value=0, max_value=1000, value=10, step=5)
    with col3:
        details = st.text_area("Details (optional)", height=80)
        add_btn = st.button("Add Item ✅")

    if add_btn:
        if not item_name.strip():
            st.warning("Please provide a task name.")
        else:
            add_item(user=username, item_date=item_date, category=category, name=item_name.strip(), details=details.strip(), xp=int(xp))
            st.success(f"Added: {item_name}")
            st.experimental_rerun()

st.markdown("---")

# -- Filters and list
colf1, colf2, colf3, colf4 = st.columns([2,2,1,1])
with colf1:
    filter_cat = st.selectbox("Filter category", ["All", "Learning", "Health", "Spiritual", "Content", "Work", "Other"])
with colf2:
    filter_date = st.date_input("Filter date (optional)", value=None)
    # streamlit date_input cannot be None easily, so allow "Clear" checkbox:
    if st.checkbox("Clear date filter"):
        filter_date = None
with colf3:
    search_text = st.text_input("Search task name")
with colf4:
    show_done = st.checkbox("Show done items", value=True)

items = get_items(user=username, selected_category=filter_cat, search=search_text or None, for_date=filter_date)

# Present as dataframe with actions
if not items:
    st.info("No items found for the selected filters.")
else:
    # Convert to DataFrame for nicer display but we'll keep IDs for actions.
    df = pd.DataFrame([{
        "id": it.id,
        "date": it.date.isoformat(),
        "category": it.category,
        "task_name": it.task_name,
        "details": (it.details[:80] + "...") if it.details and len(it.details) > 80 else (it.details or ""),
        "done": it.is_done,
        "xp": it.xp
    } for it in items if (show_done or not it.is_done)])
    st.dataframe(df[["id","date","category","task_name","done","xp"]], use_container_width=True)

    # Create per-row controls
    st.markdown("### Manage Items")
    for it in items:
        if not show_done and it.is_done:
            continue
        with st.container():
            cols = st.columns([3,2,1,1,1])
            cols[0].markdown(f"**{it.task_name}**  \n_{it.category}_  •  {it.date.isoformat()}  \n{it.details or ''}")
            done_key = f"done-{it.id}"
            done_val = cols[1].checkbox("Done", value=it.is_done, key=done_key)
            xp_key = f"xp-{it.id}"
            xp_val = cols[2].number_input("XP", min_value=0, max_value=1000, value=int(it.xp or 0), key=xp_key)
            edit_btn = cols[3].button("Edit", key=f"edit-{it.id}")
            del_btn = cols[4].button("Delete", key=f"del-{it.id}")

            # handle done toggles / xp changes instantly
            if done_val != it.is_done or xp_val != it.xp:
                update_item(it.id, is_done=done_val, xp=int(xp_val))
                st.experimental_rerun()

            # Edit modal simulated by expanding section when edit clicked
            if edit_btn:
                with st.form(f"edit-form-{it.id}", clear_on_submit=False):
                    new_name = st.text_input("Task name", value=it.task_name)
                    new_cat = st.selectbox("Category", ["Learning", "Health", "Spiritual", "Content", "Work", "Other"], index=["Learning", "Health", "Spiritual", "Content", "Work", "Other"].index(it.category) if it.category in ["Learning","Health","Spiritual","Content","Work","Other"] else 5)
                    new_date = st.date_input("Date", value=it.date)
                    new_details = st.text_area("Details", value=it.details or "")
                    new_xp = st.number_input("XP", min_value=0, max_value=1000, value=int(it.xp or 0))
                    save = st.form_submit_button("Save changes")
                    if save:
                        update_item(it.id, task_name=new_name.strip(), category=new_cat, date=new_date, details=new_details.strip(), xp=int(new_xp))
                        st.success("Updated")
                        st.experimental_rerun()

            # Delete confirmation
            if del_btn:
                if st.confirm(f"Delete '{it.task_name}'? This cannot be undone."):
                    delete_item(it.id)
                    st.success("Deleted")
                    st.experimental_rerun()

st.markdown("---")
# Summary and sync
col_a, col_b = st.columns([3,1])
with col_a:
    total_xp = sum(i.xp for i in session_db.query(PlannerItem).filter(PlannerItem.user == username).all())
    st.metric("Total XP (all time)", f"{total_xp}")
    st.write("Quick stats:")
    st.write({
        "Total items": session_db.query(PlannerItem).filter(PlannerItem.user == username).count(),
        "Done": session_db.query(PlannerItem).filter(PlannerItem.user == username, PlannerItem.is_done == True).count()
    })
with col_b:
    if st.button("💾 Save & Sync to Git"):
        csv = export_and_push(commit_msg=f"Sync planner: {datetime.utcnow().isoformat()}Z")
        st.success(f"Exported to {csv} and attempted git push (if remote configured).")
