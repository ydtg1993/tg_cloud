import sqlite3
import os

class DBManager:
    def __init__(self, db_path="tgfiles.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()

    def get_items_in_directory(self, directory_id=0):
        dirs = self.conn.execute(
            "SELECT id, name, 1 AS is_dir, NULL AS message_id, NULL AS original_name, NULL AS display_name, NULL AS file_size, NULL AS upload_time, NULL AS mime_type "
            "FROM directories WHERE parent_id=? ORDER BY name",
            (directory_id,)
        ).fetchall()
        files = self.conn.execute(
            "SELECT id, NULL AS name, 0 AS is_dir, message_id, original_name, display_name, file_size, upload_time, mime_type "
            "FROM files WHERE directory_id=? ORDER BY display_name, original_name",
            (directory_id,)
        ).fetchall()
        return dirs + files

    def create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS directories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER DEFAULT 0,
                created_time DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT NOT NULL,
                message_id INTEGER,
                chat_id INTEGER NOT NULL,
                original_name TEXT,
                display_name TEXT,
                directory_id INTEGER DEFAULT 0,
                file_size INTEGER,
                mime_type TEXT,
                upload_time DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()

    def add_directory(self, name, parent_id=0):
        cur = self.conn.execute(
            "INSERT INTO directories (name, parent_id) VALUES (?, ?)",
            (name, parent_id)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_directories(self, parent_id=0):
        cur = self.conn.execute(
            "SELECT id, name FROM directories WHERE parent_id=? ORDER BY name",
            (parent_id,)
        )
        return cur.fetchall()

    def move_directory(self, dir_id, new_parent_id):
        self.conn.execute(
            "UPDATE directories SET parent_id=? WHERE id=?",
            (new_parent_id, dir_id)
        )
        self.conn.commit()

    def delete_directory(self, dir_id):
        self.conn.execute("UPDATE files SET directory_id=0 WHERE directory_id=?", (dir_id,))
        self.conn.execute("UPDATE directories SET parent_id=0 WHERE parent_id=?", (dir_id,))
        self.conn.execute("DELETE FROM directories WHERE id=?", (dir_id,))
        self.conn.commit()

    def rename_directory(self, dir_id, new_name):
        self.conn.execute("UPDATE directories SET name=? WHERE id=?", (new_name, dir_id))
        self.conn.commit()

    def add_file(self, file_id, message_id, chat_id, original_name, display_name, directory_id, file_size, mime_type):
        self.conn.execute(
            "INSERT INTO files (file_id, message_id, chat_id, original_name, display_name, directory_id, file_size, mime_type) VALUES (?,?,?,?,?,?,?,?)",
            (file_id, message_id, chat_id, original_name, display_name, directory_id, file_size, mime_type)
        )
        self.conn.commit()

    def get_files_in_directory(self, directory_id=0):
        cur = self.conn.execute(
            "SELECT id, file_id, message_id, original_name, display_name, file_size, upload_time, mime_type FROM files WHERE directory_id=? ORDER BY upload_time DESC",
            (directory_id,)
        )
        return cur.fetchall()

    def update_display_name(self, file_id, new_name):
        self.conn.execute("UPDATE files SET display_name=? WHERE id=?", (new_name, file_id))
        self.conn.commit()

    def move_file(self, file_id, new_directory_id):
        self.conn.execute("UPDATE files SET directory_id=? WHERE id=?", (new_directory_id, file_id))
        self.conn.commit()

    def delete_file(self, file_id):
        self.conn.execute("DELETE FROM files WHERE id=?", (file_id,))
        self.conn.commit()

    def get_file_by_id(self, local_id):
        cur = self.conn.execute("SELECT * FROM files WHERE id=?", (local_id,))
        return cur.fetchone()

    def get_path_to_directory(self, dir_id):
        """返回从根目录到指定目录的完整路径列表 [(id, name), ...]，包含虚拟根(id=0)"""
        path = [(0, "根目录")]
        if dir_id == 0:
            return path
        segments = []
        current = dir_id
        while current:
            row = self.conn.execute(
                "SELECT id, name, parent_id FROM directories WHERE id=?", (current,)
            ).fetchone()
            if not row:
                break
            segments.append((row[0], row[1]))
            current = row[2]  # parent_id
        # 反转并追加到根目录后面
        for seg in reversed(segments):
            path.append(seg)
        return path