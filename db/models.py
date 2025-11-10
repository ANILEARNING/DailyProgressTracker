# db/models.py
from sqlalchemy import (
    create_engine, Column, Integer, String, Date, Float, Boolean, Text
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import date

Base = declarative_base()

class PlannerItem(Base):
    __tablename__ = "planner_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)  # e.g., Learning, Health, Spiritual, Content
    task_name = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    is_done = Column(Boolean, default=False)
    xp = Column(Integer, default=0)

# choose SQLite for quick local dev
ENGINE = create_engine("sqlite:///db/database.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, expire_on_commit=False)

def init_db():
    Base.metadata.create_all(bind=ENGINE)

if __name__ == "__main__":
    init_db()
    print("DB initialized")
