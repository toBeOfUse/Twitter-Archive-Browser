-- a one-row table to store the archive owner's account's id
create table me (id integer primary key);

create table conversations (
    id text primary key,
    type text not null check(type in ("group", "individual")),
    notes text,
    number_of_messages integer,
    messages_from_you integer,
    -- only usable for individual chats
    other_person integer unique,
    -- the below columns cache the times of the first and last message, name update,
    -- or participant joining or leaving times for the conversation
    first_time string,
    last_time string,
    -- more meaningful for group chats; just records the first message's sender for
    -- individual chats
    created_by_me integer check(created_by_me in (0, 1)) default 1,
    -- if we created the chat then this is null
    added_by integer,
    -- only meaningful for group chats
    num_participants integer,
    num_name_updates integer,
    /* if we created the chat then participant info might not be comprehensive (the
     data doesn't show the initial members in that case fsr) */
    foreign key(other_person) references users(id),
    foreign key(added_by) references users(id)
);

create table users (
    id integer primary key,
    number_of_messages integer,
    loaded_full_data integer check(loaded_full_data in (0, 1)),
    -- if false, the rest of these will be null (except maybe nickname and notes)
    handle text,
    display_name text,
    bio text,
    avatar blob,
    -- "jpg", "png", maybe "gif"; who needs mime types
    avatar_extension text,
    nickname text check(length(nickname) < 50),
    notes text
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

-- not actually sure if all the unindexed columns need to be listed out? probably tho
create virtual table messages_text_search using fts5(
    sent_time unindexed,
    sender unindexed,
    conversation unindexed,
    content,
    content = messages,
    content_rowid = id
);

-- messages don't get updated or deleted lol so other triggers aren't necessary
create trigger message_add
after
insert on messages begin
insert into messages_text_search(rowid, content)
values(
        new.id,
        -- adding tags with author ids into the indexed text allows for indexed text
        -- searching and indexed author searching to be done in a single query;
        -- query results will still have their content drawn from the messages table
        -- and will not include the tag
        new.content || " author_tag_" || new.sender
    );

end;

create table reactions (
    -- twitter gives reactions a specific id but letting sqlite use rowid should be
    -- fine
    emotion text not null,
    -- laugh, wow, cry, heart, fire, thumbs up, thumbs down
    creation_time text not null,
    creator integer not null,
    message integer not null,
    foreign key(creator) references users(id),
    foreign key(message) references messasges(id)
);

create table media (
    id integer primary key,
    -- orig_url breaks down into the other four fields (hopefully. i think)
    orig_url text not null,
    type string not null check(type in ("image", "video", "gif")),
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
    conversation text not null,
    foreign key(initiator) references users(id),
    foreign key(conversation) references conversations(id)
);

-- stores a record for each instance of a specific user being in a specific chat
create table participants (
    participant integer not null,
    conversation text not null,
    messages_sent integer,
    -- if equal to the conversation's first_time, they've been there since before we
    -- were
    start_time text,
    -- if null they never left,
    end_time text,
    -- null unless the user was added while we were already in the chat
    added_by integer,
    unique(participant, conversation),
    foreign key (added_by) references users(id)
);