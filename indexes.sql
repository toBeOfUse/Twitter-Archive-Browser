-- hopefully this will index queries using "where conversation=? order by sent_time"
create index convos_chronological_idx on messages (conversation, sent_time);

create index reactions_by_message_idx on reactions (message);

create index media_by_message_idx on media (message);

create index links_by_message_idx on links (message);

create index name_updates_convo_chronological_idx on name_updates (conversation, update_time);

create index participation_start_idx on participants (start_time);
create index participation_end_idx on participants (end_time);