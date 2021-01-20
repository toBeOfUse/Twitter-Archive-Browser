create index convos_ids_idx on conversations(id);

create index convos_message_count_idx on conversations(type, number_of_messages);

create index convo_firsttime_idx on conversations (first_time);

create index convo_lasttime_idx on conversations (last_time);

create index users_by_messages on users (number_of_messages);

create index messages_convo_chronological_idx on messages (conversation, sent_time);

create index messages_user_chronological_idx on messages (sender, sent_time);

create index messages_chronological_idx on messages (sent_time);

create index reactions_by_message_chronological_idx on reactions (message, creation_time);

create index media_by_message_idx on media (message);

create index links_by_message_idx on links (message);

create index name_updates_convo_chronological_idx on name_updates (conversation, update_time);

create index participation_start_idx on participants (start_time);

create index participation_end_idx on participants (end_time);