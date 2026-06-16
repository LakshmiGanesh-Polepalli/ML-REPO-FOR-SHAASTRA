"""
seed.py — Populate the events table with sample Shaastra events.
Run once: python seed.py
"""

from models import create_tables, SessionLocal, Event

SAMPLE_EVENTS = [
    # Day 1 — Jan 16
    dict(event_name="Inaugural Ceremony",      category="cultural",  venue="OAT",       day_number=1, start_time="09:00", end_time="11:00", registration_link=None),
    dict(event_name="Python for ML Workshop",  category="workshop",  venue="CLT",       day_number=1, start_time="11:30", end_time="13:30", registration_link="https://shaastra.org/reg/py-ml"),
    dict(event_name="HackerSpace – Hackathon", category="coding",    venue="SAC",       day_number=1, start_time="14:00", end_time="22:00", registration_link="https://shaastra.org/reg/hackspace"),
    dict(event_name="Robotics Demo Show",      category="lecture",   venue="Himalaya",  day_number=1, start_time="16:00", end_time="17:30", registration_link=None),

    # Day 2 — Jan 17
    dict(event_name="CTF – Capture the Flag",  category="coding",    venue="CLT",       day_number=2, start_time="09:00", end_time="18:00", registration_link="https://shaastra.org/reg/ctf"),
    dict(event_name="IoT & Embedded Systems",  category="workshop",  venue="SAC",       day_number=2, start_time="10:00", end_time="12:30", registration_link="https://shaastra.org/reg/iot"),
    dict(event_name="AI Ethics Panel",         category="lecture",   venue="OAT",       day_number=2, start_time="15:00", end_time="16:30", registration_link=None),
    dict(event_name="Battle of Bands",         category="cultural",  venue="OAT",       day_number=2, start_time="19:00", end_time="22:00", registration_link=None),

    # Day 3 — Jan 18
    dict(event_name="App Dev Bootcamp",        category="workshop",  venue="CLT",       day_number=3, start_time="09:00", end_time="13:00", registration_link="https://shaastra.org/reg/appdev"),
    dict(event_name="Competitive Programming", category="coding",    venue="Godavari",  day_number=3, start_time="10:00", end_time="14:00", registration_link="https://shaastra.org/reg/cp"),
    dict(event_name="Drone Racing League",     category="gaming",    venue="SAC",       day_number=3, start_time="14:30", end_time="17:00", registration_link="https://shaastra.org/reg/drone"),
    dict(event_name="Keynote: Future of Space",category="lecture",   venue="OAT",       day_number=3, start_time="17:30", end_time="19:00", registration_link=None),

    # Day 4 — Jan 19
    dict(event_name="Game Dev Jam",            category="gaming",    venue="CLT",       day_number=4, start_time="09:00", end_time="17:00", registration_link="https://shaastra.org/reg/gamedev"),
    dict(event_name="Blockchain Workshop",     category="workshop",  venue="Jamuna",    day_number=4, start_time="10:00", end_time="12:00", registration_link="https://shaastra.org/reg/blockchain"),
    dict(event_name="Closing Ceremony & Prize",category="cultural",  venue="OAT",       day_number=4, start_time="18:00", end_time="21:00", registration_link=None),
]


def seed():
    create_tables()
    db = SessionLocal()
    try:
        existing = db.query(Event).count()
        if existing > 0:
            print(f"DB already has {existing} events — skipping seed.")
            return
        for ev in SAMPLE_EVENTS:
            db.add(Event(**ev))
        db.commit()
        print(f"Seeded {len(SAMPLE_EVENTS)} events successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
