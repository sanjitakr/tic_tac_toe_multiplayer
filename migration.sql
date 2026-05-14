
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS elo_rating  INT     NOT NULL DEFAULT 1200,
    ADD COLUMN IF NOT EXISTS wins        INT     NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS losses      INT     NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS draws       INT     NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS is_online   BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS matches (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    winner_uid         VARCHAR(64)  NOT NULL,
    loser_uid          VARCHAR(64)  NOT NULL,
    result             ENUM('win', 'draw') NOT NULL,
    winner_elo_before  INT NOT NULL,
    loser_elo_before   INT NOT NULL,
    winner_elo_after   INT NOT NULL,
    loser_elo_after    INT NOT NULL,
    played_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (winner_uid) REFERENCES users(uid),
    FOREIGN KEY (loser_uid)  REFERENCES users(uid)
);