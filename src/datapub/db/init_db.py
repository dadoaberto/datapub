from .base import Base, engine


def init_db():
    Base.metadata.create_all(bind=engine)


def main():
    init_db()
    print("Database tables ensured.")


if __name__ == "__main__":
    main()

