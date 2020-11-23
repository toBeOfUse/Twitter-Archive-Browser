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
set created_by_me = 1
where type = "individual"
    and (
        select sender
        from messages
        where conversation = conversations.id
        order by sent_time
        limit 1
    ) = (
        select id
        from me
        limit 1
    );