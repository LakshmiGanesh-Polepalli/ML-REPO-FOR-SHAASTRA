"""
models.py — SQLAlchemy ORM models for Shaastra event schedule.
"""

from sqlalchemy import Column, Integer, String, Time, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://shaastra:shaastra@localhost:5432/shaastra"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Event(Base):
    __tablename__ = "events"

    id                = Column(Integer, primary_key=True, index=True)
    event_name        = Column(String, nullable=False)
    category          = Column(String, nullable=False)   # workshop / coding / lecture / cultural / gaming
    venue             = Column(String, nullable=False)
    day_number        = Column(Integer, nullable=False)  # 1-4
    start_time        = Column(String, nullable=False)   # "HH:MM" string — simpler for display
    end_time          = Column(String, nullable=False)
    registration_link = Column(String, nullable=True)

    def to_dict(self):
        return {
            "id":                self.id,
            "event_name":        self.event_name,
            "category":          self.category,
            "venue":             self.venue,
            "day_number":        self.day_number,
            "start_time":        self.start_time,
            "end_time":          self.end_time,
            "registration_link": self.registration_link,
        }


def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
