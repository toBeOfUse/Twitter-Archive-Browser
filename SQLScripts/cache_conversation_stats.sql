update conversations
set first_time = (
        select min(time)
        from (
                select sent_time as time
                from messages
                where conversation = conversations.id
                union
                select update_time
                from name_updates
                where conversation = conversations.id
                union
                select start_time
                from participants
                where conversation = conversations.id
                union
                select end_time
                from participants
                where conversation = conversations.id
            ) as t1
    )
where first_time is null;

update conversations
set last_time = (
        select max(time)
        from (
                select sent_time as time
                from messages
                where conversation = conversations.id
                union
                select update_time
                from name_updates
                where conversation = conversations.id
                union
                select start_time
                from participants
                where conversation = conversations.id
                union
                select end_time
                from participants
                where conversation = conversations.id
            ) as t1
    )
where last_time is null;

update conversations
set created_by_me = 0
where type = "individual"
    and (
        select sender
        from messages
        where conversation = conversations.id
        order by sent_time
        limit 1
    ) != (
        select id
        from me
        limit 1
    );

update conversations
set number_of_messages = (
        select count()
        from messages
        where conversation = conversations.id
    );

update conversations
set messages_from_you = (
        select count()
        from messages
        where conversation = conversations.id
            and sender = (
                select id
                from me
                limit 1
            )
    );

update conversations
set num_participants = (
        select count()
        from participants
        where participants.conversation = conversations.id
    );

update conversations
set num_name_updates = (
        select count()
        from name_updates
        where name_updates.conversation = conversations.id
    );

update participants
set start_time = (
        select first_time
        from conversations
        where conversations.id = participants.conversation
    )
where start_time is null;

update participants
set messages_sent = (
        select count()
        from messages
        where messages.conversation = participants.conversation
            and messages.sender = participants.participant
    );

update users
set number_of_messages = (
        select count()
        from messages
        where messages.sender = users.id
    );