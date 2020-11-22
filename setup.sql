-- a one-row table to store the archive owner's account's id
create table me (id integer primary key);

create table conversations (
    id text primary key,
    type text not null check(type in ("group", "individual")),
    notes text,
    other_person integer unique, -- just usable for individual chats
    -- the below columns cache the times of the first and last message, name update, or participant joining or
    -- leaving times for the conversation
    first_time string,
    last_time string,
    -- the below is pretty much just relevant for group chats
    created_by_me integer check(created_by_me in (0, 1)) default 1,
    added_by integer -- if we created the chat then this is null
    /* if we created the chat then participant info might not be comprehensive (the data doesn't show the
     initial members in that case fsr) */
);

create table users (
    id integer primary key,
    loaded_full_data integer check(loaded_full_data in (0, 1)),
    -- if false, the rest of these will be null (except maybe nickname and notes)
    handle text,
    display_name text,
    bio text,
    avatar blob,
    nickname text,
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

-- messages don't get updated or deleted lol
create trigger message_add after insert on messages
begin
    insert into messages_text_search(rowid, content) values(new.id, new.content);
end;

create table reactions (
    emotion text not null, -- laugh, wow, cry, heart, fire, thumbs up, thumbs down
    creation_time text not null,
    creator integer not null,
    message integer not null,
    foreign key(creator) references users(id),
    foreign key(message) references messasges(id)
    -- twitter also gives reactions a specific id but letting sqlite use rowid should be fine
);

create table media (
    id integer primary key,
    orig_url text not null, -- this breaks down into the other four fields (hopefully. i think)
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
    -- start_time should come from participant snapshots or participantsJoin events (if those aren't there then
    -- the user was there from the beginning of the chat and the chat was created by us and they have to be
    -- detected from the messages they send)
    start_time text, -- shouldn't be null at the end of transaction
    end_time text, -- if null they never left,
    added_by integer, -- null unless the user was added while we were already in the chat
    unique(participant, conversation),
    foreign key (added_by) references users(id)
);
