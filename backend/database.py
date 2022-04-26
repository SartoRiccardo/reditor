import psycopg2
import credentials

conn = psycopg2.connect(
        user=credentials.Database.user, password=credentials.Database.pswd,
        database=credentials.Database.name, host=credentials.Database.host
)
conn.set_session(autocommit=True)


def get_videos(with_thumbnail=False, created=False):
    """
    Gets videos that haven't been exported. The ones that have a thumbnail are
    put at the top.
    :with_thumbnail: Excludes videos that don't have a thumbnail, if True
    """
    cur = conn.cursor()
    cur.execute(f"""
        SELECT vid.thread, vid.title, vid.thumbnail, thr.title, vid.url, vid.document_id
        FROM rdt_videos as vid
            JOIN rdt_threads as thr ON vid.thread = thr.id
        WHERE NOT exported
        {"AND thumbnail IS NOT NULL" if with_thumbnail else ""}
        {"AND document_id IS NOT NULL" if created else ""}
        ORDER BY thumbnail ASC
    """)
    rows = cur.fetchall()
    rows = [
        {"thread": r[0], "title": r[1], "thumbnail": r[2], "thread_title": r[3],
         "url": r[4], "document_id": r[5]}
        for r in rows
    ]
    return rows


def confirm_video_creation(thread_id, document_id):
    cur = conn.cursor()
    cur.execute("""
        UPDATE rdt_videos
        SET document_id=%s
        WHERE thread=%s
    """, [document_id, thread_id])


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
        if type(key) == list:
            return [config(k) for k in key]
        cur.execute("SELECT value FROM config WHERE name=%s", [key])
        rows = cur.fetchone()
        return rows[0] if rows else None
    else:
        cur.execute("UPDATE config SET value=%s WHERE name=%s", [value, key])
        conn.commit()


