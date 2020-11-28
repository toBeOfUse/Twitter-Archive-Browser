#############################################################
A note on conversation and participant start and end times
#############################################################

Twitter provides thorough information on participants joining and leaving and being in conversations while you are there to see it except in the case that the conversation is one you started with participants that were there all along. This necessitates making some inferences to record the start and end of their presences.

participant logic by type of conversation
--------------------------------------------

#. simple dm conversation. both participants should be shown to join at the start of the conversation and not leave, but having the participants entries is only for tidiness' sake (the conversation records will have both particpants' ids and the timestamps involved are obvious.) the participants will be registered when the first message from their convo comes through; the conversation record will be updated to show it as starting at their first message when it's selected as having a null "join" time in cache_conversation_times; the participants' start_times will be set in cache_conversation_times when they're selected as having no start times.
#. group conversation that you were added to. the simplest case; all information on participants available through your slice of the conversation should be obvious from participantsJoin, participantsLeave, and joinConversation events (the latter contain snapshots listing the participants that were there before you.) (participants not seen to leave will have ``null`` as their time of leaving in the database.
#. group conversation that you created. this case requires participants to be detected from messages that they send, since there is no joinConversation event that provides a snapshot of the conversations' initial members; participantsJoin and participantsLeave events should be handled as in the above case, but then any participants that don't have a join_time timestamp at the end can be assumed to have "always been there" and their join_time timestamps should be set to their conversation's first_time.
