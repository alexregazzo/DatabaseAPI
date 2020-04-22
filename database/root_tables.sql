CREATE TABLE IF NOT EXISTS user
(
    user_id       integer not null primary key,
    user_fullname text    not null,
    user_email    text    not null unique,
    user_active   integer not null default 1 check (user_active in (0, 1)),
    user_password text    not null,
    user_creation text    not null
);

CREATE TABLE IF NOT EXISTS token
(
    token_id                         integer not null primary key autoincrement,
    user_id                          integer not null,
    token_token                      text unique,
    token_database_name              text    not null,
    token_creation                   text    not null,
    token_active                     integer not null default 0 check (token_active in (0, 1)),
    token_activation_code            text    not null default '',
    token_activation_code_expiration text    not null default '',
    foreign key (user_id) references user (user_id)
);

CREATE TABLE IF NOT EXISTS use
(
    use_id       integer primary key autoincrement,
    token_id     integer not null,
    use_data     text    not null,
    use_creation text    not null,
    foreign key (token_id) references token (token_id)
)
