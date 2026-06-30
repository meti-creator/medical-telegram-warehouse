import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

PG_HOST = os.getenv("PG_HOST")
PG_PORT = os.getenv("PG_PORT")
PG_DATABASE = os.getenv("PG_DATABASE")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")

# SQLAlchemy connection URL format:
# postgresql://user:password@host:port/database
DATABASE_URL = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"

# The "engine" manages a pool of actual connections to Postgres,
# reusing them efficiently rather than opening a brand new connection
# for every single request the API receives.
engine = create_engine(DATABASE_URL)

# SessionLocal is a factory for creating individual "sessions" -
# one session = one unit of work (e.g. one API request's worth of queries).
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    A dependency function FastAPI will call for every request that needs
    database access. It opens a session, hands it to the endpoint function,
    and guarantees the session gets closed afterward - even if the endpoint
    raises an error. This pattern (open -> yield -> close) is the standard
    way to manage per-request resources in FastAPI.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
