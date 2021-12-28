import psycopg2
import credentials

conn = psycopg2.connect(
        user=credentials.Database.user, password=credentials.Database.pswd,
        database=credentials.Database.name, host=credentials.Database.host
)


def get_videos():
    cur = conn.cursor()
    cur.execute("""
        SELECT vid.thread, vid.title, vid.thumbnail, thr.title, vid.url
        FROM rdt_videos as vid
            JOIN rdt_threads as thr ON vid.thread = thr.id
        WHERE NOT exported
        ORDER BY thumbnail ASC
    """)
    rows = cur.fetchall()
    rows = [
        {"thread": r[0], "title": r[1], "thumbnail": r[2], "thread_title": r[3],
         "url": r[4]}
        for r in rows
    ]
    return rows


def confirm_video_upload(thread, url):
    cur = conn.cursor()
    cur.execute("""
        UPDATE rdt_videos
        SET url=%s
        WHERE thread=%s
    """, [url, thread])


def get_video(thread):
    cur = conn.cursor()
    cur.execute("""
            SELECT vid.thread, vid.title, vid.thumbnail, thr.title, vid.url
            FROM rdt_videos as vid
                JOIN rdt_threads as thr ON vid.thread = thr.id
            WHERE vid.thread=%s
    """, [thread])
    row = cur.fetchone()
    if not row:
        print(f"None for {thread}!")
        return
    row = {"thread": row[0], "title": row[1], "thumbnail": row[2], "thread_title": row[3], "url": row[4]}
    return row


def get_complete_videos():
    cur = conn.cursor()
    cur.execute("""
        SELECT thread, vid.title, vid.thumbnail, thr.title, vid.url
        FROM rdt_videos as vid
            JOIN rdt_threads as thr ON vid.thread = thr.id
        WHERE exported
            AND vid.thumbnail IS NOT NULL
            AND vid.title IS NOT NULL
            AND vid.url IS NULL
    """)
    rows = cur.fetchall()
    rows = [
        {"thread": r[0], "title": r[1], "thumbnail": r[2], "thread_title": r[3],
         "url": r[4]}
        for r in rows
    ]
    return rows


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
        cur.execute("UPDATE config SET value=%s WHERE name=%s", [value, key])
        conn.commit()


