import sqlite3
import os
from collections import namedtuple

DirectoryItem = namedtuple('DirectoryItem',
                           ['id', 'name', 'is_dir', 'message_id', 'original_name', 'display_name', 'file_size', 'upload_time', 'mime_type'])

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
        # 转换为 namedtuple
        return [DirectoryItem(*row) for row in (dirs + files)]

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

    def get_all_files_recursive(self, dir_id):
        """返回指定目录及其所有子目录下的文件 (id, message_id, chat_id) 列表"""
        # 收集所有子目录 ID
        dirs_to_process = [dir_id]
        all_dirs = [dir_id]
        while dirs_to_process:
            current = dirs_to_process.pop()
            children = self.conn.execute(
                "SELECT id FROM directories WHERE parent_id=?", (current,)
            ).fetchall()
            for c in children:
                all_dirs.append(c[0])
                dirs_to_process.append(c[0])

        # 查询这些目录下的所有文件
        if not all_dirs:
            return []
        placeholders = ','.join('?' for _ in all_dirs)
        files = self.conn.execute(
            f"SELECT id, message_id, chat_id FROM files WHERE directory_id IN ({placeholders})",
            all_dirs
        ).fetchall()
        return files  # [(id, message_id, chat_id), ...]

    def delete_directory_recursive(self, dir_id):
        """递归删除目录及其所有子目录和文件（数据库操作）"""
        # 递归收集所有子目录
        dirs_to_delete = []

        def collect_dirs(did):
            dirs_to_delete.append(did)
            children = self.conn.execute(
                "SELECT id FROM directories WHERE parent_id=?", (did,)
            ).fetchall()
            for c in children:
                collect_dirs(c[0])

        collect_dirs(dir_id)

        # 删除这些目录下的所有文件
        placeholders = ','.join('?' for _ in dirs_to_delete)
        self.conn.execute(
            f"DELETE FROM files WHERE directory_id IN ({placeholders})",
            dirs_to_delete
        )
        # 删除目录（逆序删除避免子目录约束，但无外键，顺序任意）
        for did in reversed(dirs_to_delete):
            self.conn.execute("DELETE FROM directories WHERE id=?", (did,))
        self.conn.commit()

        # 在 DBManager 类中添加以下方法

    def search_files_by_name(self, keyword):
        """根据文件名搜索文件，返回包含完整路径的结果列表"""
        # 搜索 display_name 或 original_name 包含关键字的文件（不区分大小写）
        keyword = f"%{keyword}%"
        files = self.conn.execute(
            """SELECT f.id, f.file_id, f.message_id, f.chat_id, 
                      f.original_name, f.display_name, f.directory_id, 
                      f.file_size, f.upload_time, f.mime_type,
                      d.name as dir_name
               FROM files f
               LEFT JOIN directories d ON f.directory_id = d.id
               WHERE (f.display_name LIKE ? OR f.original_name LIKE ?)
               ORDER BY COALESCE(f.display_name, f.original_name) COLLATE NOCASE ASC""",
            (keyword, keyword)
        ).fetchall()

        results = []
        for row in files:
            file_id = row[0]
            dir_id = row[6]
            # 获取完整路径
            path_parts = self.get_path_to_directory(dir_id)
            path_str = self._build_path_string(path_parts)
            results.append({
                'id': file_id,
                'name': row[5] or row[4],  # display_name 优先
                'directory_id': dir_id,
                'full_path': path_str,
                'original_name': row[4],
                'display_name': row[5],
                'file_size': row[7],
                'upload_time': row[8],
                'mime_type': row[9]
            })
        return results

    def search_files_by_date_range(self, start_date, end_date):
        """根据上传时间范围搜索文件"""
        # start_date 和 end_date 格式为 'YYYY-MM-DD'
        files = self.conn.execute(
            """SELECT f.id, f.file_id, f.message_id, f.chat_id, 
                      f.original_name, f.display_name, f.directory_id, 
                      f.file_size, f.upload_time, f.mime_type
               FROM files f
               WHERE DATE(f.upload_time) >= ? AND DATE(f.upload_time) <= ?
               ORDER BY f.upload_time DESC""",
            (start_date, end_date)
        ).fetchall()

        results = []
        for row in files:
            dir_id = row[6]
            path_parts = self.get_path_to_directory(dir_id)
            path_str = self._build_path_string(path_parts)
            results.append({
                'id': row[0],
                'name': row[5] or row[4],
                'directory_id': dir_id,
                'full_path': path_str,
                'original_name': row[4],
                'display_name': row[5],
                'file_size': row[7],
                'upload_time': row[8],
                'mime_type': row[9]
            })
        return results

    def _build_path_string(self, path_parts):
        """将路径元组列表转换为字符串"""
        # path_parts: [(id, name), ...]
        parts = []
        for _, name in path_parts:
            if name != "根目录":
                parts.append(name)
        if not parts:
            return "/"
        return "/" + "/".join(parts)