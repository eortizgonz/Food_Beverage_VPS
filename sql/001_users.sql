CREATE TABLE IF NOT EXISTS public.users (
    id serial4 PRIMARY KEY,
    "name" varchar(120) NOT NULL,
    email varchar(255) NOT NULL,
    username varchar(80) NOT NULL,
    password_hash varchar(255) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT users_email_unique UNIQUE (email),
    CONSTRAINT users_username_unique UNIQUE (username)
);

CREATE INDEX IF NOT EXISTS users_email_lower_idx
    ON public.users (lower(email));

CREATE INDEX IF NOT EXISTS users_username_lower_idx
    ON public.users (lower(username));
