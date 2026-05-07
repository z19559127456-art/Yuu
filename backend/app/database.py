"""
Database setup — SQLAlchemy engine, session factory, and init_db()
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import config

SQLALCHEMY_DATABASE_URL = f"sqlite:///{config.DATA_DIR / 'agent_messenger.db'}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """Create all tables and seed default data."""
    # Import all models so Base.metadata.create_all picks them up
    from app.models import (
        Agent, Conversation, Message, TaskRecord, MemorySummary,
        WebRecord, UIRecord, VisionRecord, Plan, SubTask,
        TaskExecution, SkillRecord, VectorMemoryEntry,
        GroupConversation, GroupParticipant, DiscussionRound, AuditLog,
    )

    Base.metadata.create_all(bind=engine)

    # Seed a default agent if none exist
    db = SessionLocal()
    try:
        if db.query(Agent).count() == 0:
            default_agent = Agent(
                name="默认助手",
                avatar="",
                system_prompt="你是一个有用的AI助手。",
                model_provider="openai",
                model_name="gpt-3.5-turbo",
                temperature=0.7,
            )
            db.add(default_agent)
            db.commit()
    finally:
        db.close()
