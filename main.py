import os
import psycopg
from widget.raw_to_temp import raw_to_temp_csv
from widget.ram_to_permanent import ram_to_permanent_csv
from previous_data.d1 import data

def main(conn, data, temp_csv_file_path, permanent_csv_route, sql):
    try:
        df = raw_to_temp_csv(temp_csv_file_path, data)
        print("DONE, raw -> df & temp.csv")

        df_to_tuple = df[['word', 'pronunciation', 'lang', 'mastery_level', 'definition', 'sentences']].itertuples(index=False, name=None)
        with (conn) as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, df_to_tuple)
                conn.commit()
        print("DONE, psql inserted")

        ram_to_permanent_csv(df, permanent_csv_route)
        print("DONE, stored to permanent.csv")

    except KeyError as e:
        raise SystemExit(e)

    except psycopg.Error as e:
        raise SystemExit(e)
    finally:
        cur.close()
        conn.close()

# ====================================================================================================================================
conn = psycopg.connect(
    host="127.0.0.1",
    port=5432,
    dbname="lang",
    user=os.environ.get("PSQL_USER", ""),
    password=os.environ.get("DB_PASSWORD", "")
)

sql = """
    INSERT INTO voc_t (word, pronunciation, lang, mastery_level, definition, sentences)
    VALUES (%s, %s, %s, %s, %s, %s)
    """

if __name__ == "__main__":
    main(conn, data, 'temp.csv', 'previous_data/permanent.csv', sql)




                # cur.execute("SELECT current_database(), current_user;")
                # print(cur.fetchone())

                # cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public';")
                # print(cur.fetchall())

                # with open(csv_file_path, 'r', encoding='utf-8') as f:
                #     with cur.copy(sql) as copy:
                #         copy.write(f.read())