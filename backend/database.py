import psycopg2
import credentials

conn = psycopg2.connect(
        user=credentials.Database.user, password=credentials.Database.pswd,
        database=credentials.Database.name, host=credentials.Database.host
)


def get_videos():
    cur = conn.cursor()
    cur.execute("SELECT thread, title, thumbnail FROM rdt_videos WHERE NOT exported ORDER BY title ASC")
    rows = cur.fetchall()
    rows = [{"thread": r[0], "title": r[1], "thumbnail": r[2]} for r in rows]
    return rows


