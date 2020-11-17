create table conversations (
    id text primary key,
    type text not null check(type in ("group", "individual")),
    join_time text,
    -- if we created the chat then this should be set to the first message's timestamp
    added_by integer -- if this is null then we created the chat
    /* if we created the chat then participant info might not be comprehensive (the data doesn't show the
     initial members in that case fsr) */
);

-- for searching
create unique index convo_id_idx on conversations (id);

-- for sorting
create unique index convo_starttime_idx on conversations (join_time);

create table users (
    id integer primary key,
    loaded_full_data integer check(loaded_full_data in (0, 1)),
    -- if false, handle and avatar will be null
    handle text,
    avatar blob,
    nickname text
);

create table messages (
    id integer primary key,
    sent_time text not null,
    sender integer not null,
    conversation text not null,
    content text,
    foreign key(sender) references users(id),
    foreign key(conversation) references conversations(id)
);

-- hopefully this will index queries using "where conversation=? order by sent_time"
create index convos_chronological_idx on messages (conversation, sent_time);

-- not actually sure if all the unindexed columns need to be listed out? probably tho
create virtual table messages_text_search using fts5(
    sent_time unindexed,
    sender unindexed,
    conversation unindexed,
    text,
    content = messages,
    content_rowid = id
);

-- messages don't get updated or deleted lol
create trigger message_add
after
insert on messages begin
insert into messages_text_search(rowid, text)
values(new.id, new.text);

end;

create table reactions (
    emotion text not null, -- laugh, wow, cry, heart, fire, thumbs up, thumbs down
    creation_time text,
    creator integer,
    messaged integer,
    foreign key(creator) references users(id),
    foreign key(message) references messasges(id)
);

create table media (
    id integer primary key,
    orig_url text not null, -- this breaks down into the three other fields (hopefully. i think)
    filename text not null,
    message integer not null,
    foreign key(message) references messages(id)
);

create table links (
    orig_url text not null,
    url_preview text not null,
    twitter_shortened_url text not null,
    message integer not null,
    foreign key(message) references messages(id)
);

create table name_updates (
    update_time text not null,
    initiator integer not null,
    new_name text not null,
    conversation_id text not null,
    foreign key(initiator) references users(id),
    foreign key(conversation_id) references conversations(id)
);

create table participation (
    participant integer not null,
    conversation text not null,
    -- can come from participant snapshots or participantsJoin events;
    -- if those aren't there then the user was there from the beginning of the chat
    start_time text,
    end_time text, -- if null they never left

)
