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


def get_video(thread):
    cur = conn.cursor()
    cur.execute("SELECT thread, title, thumbnail FROM rdt_videos WHERE thread=%s", [thread])
    row = cur.fetchone()
    row = {"thread": row[0], "title": row[1], "thumbnail": row[2]}
    return row


def confirm_export(thread):
    cur = conn.cursor()
    cur.execute("UPDATE rdt_videos SET exported=TRUE WHERE thread=%s", [thread])
    conn.commit()


def config(key, value=None):
    cur = conn.cursor()
    if value is None:
        cur.execute("SELECT value FROM config WHERE name=%s", [key])
        rows = cur.fetchone()
        return rows[0]
    else:
        pass #TODO


