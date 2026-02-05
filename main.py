import os
import psycopg

conn = psycopg.connect(
    host="127.0.0.1",
    port=5432,
    dbname="lang",
    user=os.environ.get("PSQL_USER", ""),
    password=os.environ.get("DB_PASSWORD", "")
)

def main(conn):
    try:
        with (conn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), current_user;")
                print(cur.fetchone())

                cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public';")
                print(cur.fetchall())

    except KeyError as e:
        raise SystemExit(e)

    except psycopg.Error as e:
        raise SystemExit(e)


if __name__ == "__main__":
    main(conn)