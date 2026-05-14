import pymysql
from config import MYSQL_CONFIG

K = 32  # Elo K-factor

class MySQLDB:
    def __init__(self):
        self.conn = pymysql.connect(
            host=MYSQL_CONFIG["host"],
            user=MYSQL_CONFIG["user"],
            password=MYSQL_CONFIG["password"],
            database=MYSQL_CONFIG["database"],
            cursorclass=pymysql.cursors.DictCursor
        )

    def _ensure_connection(self):
        try:
            self.conn.ping(reconnect=True)
        except Exception:
            self.conn = pymysql.connect(
                host=MYSQL_CONFIG["host"],
                user=MYSQL_CONFIG["user"],
                password=MYSQL_CONFIG["password"],
                database=MYSQL_CONFIG["database"],
                cursorclass=pymysql.cursors.DictCursor
            )

    # ── User CRUD ─────────────────────────────────────────────────────────────

    def insert_user(self, uid, name):
        self._ensure_connection()
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users (uid, name)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE name = VALUES(name)
                """, (uid, name))
            self.conn.commit()
        except Exception as e:
            print(f"[MySQL ERROR] insert_user {uid}: {e}")

    def get_user_by_uid(self, uid):
        self._ensure_connection()
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE uid = %s", (uid,))
                return cursor.fetchone()
        except Exception as e:
            print(f"[MySQL ERROR] get_user_by_uid {uid}: {e}")
            return None

    def set_online_status(self, uid, status):
        self._ensure_connection()
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET is_online = %s WHERE uid = %s",
                    (status, uid)
                )
            self.conn.commit()
        except Exception as e:
            print(f"[MySQL ERROR] set_online_status {uid}: {e}")

    def get_online_users(self):
        self._ensure_connection()
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT uid, name FROM users WHERE is_online = TRUE")
                return cursor.fetchall()
        except Exception as e:
            print(f"[MySQL ERROR] get_online_users: {e}")
            return []

    # ── Leaderboard ───────────────────────────────────────────────────────────

    def get_leaderboard(self):
        """All players sorted by elo_rating descending."""
        self._ensure_connection()
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT uid, name, elo_rating,
                           wins, losses, draws,
                           (wins + losses + draws) AS total_games
                    FROM users
                    ORDER BY elo_rating DESC
                """)
                return cursor.fetchall()
        except Exception as e:
            print(f"[MySQL ERROR] get_leaderboard: {e}")
            return []

    # ── Elo ───────────────────────────────────────────────────────────────────

    def _expected(self, r_player, r_opponent):
        return 1.0 / (1.0 + 10 ** ((r_opponent - r_player) / 400))

    def update_elo_and_record(self, winner_uid, loser_uid, is_draw=False):
        """
        Fetch both players' current ratings, compute Elo using those
        (not the post-update values), then persist both in one transaction.
        Also records win/loss/draw tallies and inserts a match record.
        """
        self._ensure_connection()
        try:
            with self.conn.cursor() as cursor:
                # Fetch ratings atomically
                cursor.execute(
                    "SELECT uid, elo_rating FROM users WHERE uid IN (%s, %s)",
                    (winner_uid, loser_uid)
                )
                rows = {r["uid"]: r["elo_rating"] for r in cursor.fetchall()}

                r_w = rows.get(winner_uid, 1200)
                r_l = rows.get(loser_uid,  1200)

                e_w = self._expected(r_w, r_l)
                e_l = self._expected(r_l, r_w)

                if is_draw:
                    s_w, s_l = 0.5, 0.5
                else:
                    s_w, s_l = 1.0, 0.0

                new_r_w = round(r_w + K * (s_w - e_w))
                new_r_l = round(r_l + K * (s_l - e_l))

                if is_draw:
                    cursor.execute("""
                        UPDATE users
                        SET elo_rating = %s, draws = draws + 1
                        WHERE uid = %s
                    """, (new_r_w, winner_uid))
                    cursor.execute("""
                        UPDATE users
                        SET elo_rating = %s, draws = draws + 1
                        WHERE uid = %s
                    """, (new_r_l, loser_uid))
                else:
                    cursor.execute("""
                        UPDATE users
                        SET elo_rating = %s, wins = wins + 1
                        WHERE uid = %s
                    """, (new_r_w, winner_uid))
                    cursor.execute("""
                        UPDATE users
                        SET elo_rating = %s, losses = losses + 1
                        WHERE uid = %s
                    """, (new_r_l, loser_uid))

                # Insert match record
                result_str = "draw" if is_draw else "win"
                cursor.execute("""
                    INSERT INTO matches
                        (winner_uid, loser_uid, result,
                         winner_elo_before, loser_elo_before,
                         winner_elo_after,  loser_elo_after)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    winner_uid, loser_uid, result_str,
                    r_w, r_l, new_r_w, new_r_l
                ))

            self.conn.commit()
            print(f"[Elo] {winner_uid} {r_w}→{new_r_w}  |  {loser_uid} {r_l}→{new_r_l}  draw={is_draw}")
            return {"winner_new": new_r_w, "loser_new": new_r_l}

        except Exception as e:
            print(f"[MySQL ERROR] update_elo_and_record: {e}")
            return {}