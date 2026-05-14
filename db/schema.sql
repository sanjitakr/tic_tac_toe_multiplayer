CREATE TABLE users (
    uid        VARCHAR(50)  PRIMARY KEY,
    name       VARCHAR(255) NOT NULL,
    elo_rating INT          NOT NULL DEFAULT 1200,
    is_online  BOOLEAN      NOT NULL DEFAULT FALSE,
    wins       INT          NOT NULL DEFAULT 0,
    losses     INT          NOT NULL DEFAULT 0,
    draws      INT          NOT NULL DEFAULT 0
);


CREATE TABLE matches (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    winner_uid         VARCHAR(50)         NOT NULL,
    loser_uid          VARCHAR(50)         NOT NULL,
    result             ENUM('win', 'draw') NOT NULL,
    winner_elo_before  INT                 NOT NULL,
    loser_elo_before   INT                 NOT NULL,
    winner_elo_after   INT                 NOT NULL,
    loser_elo_after    INT                 NOT NULL,
    played_at          DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (winner_uid) REFERENCES users(uid),
    FOREIGN KEY (loser_uid)  REFERENCES users(uid)
);
