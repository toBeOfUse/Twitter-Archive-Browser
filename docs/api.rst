###################
API Documentation
###################

All API requests must contain an Authorization cookie obtained from /api/authenticate. All query string parameters are required unless otherwise indicated. Page numbers start at 1. User-sidecar requests (as labeled below) come in the form of objects with a "results" key pointing to the main payload of the request and a "users" key pointing to an object mapping user ids onto objects containing "id", "handle", "display_name", "nickname", and "avatar_url" fields. The standard way to display a user's name is "display name (@handle) | nickname if it exists".

Authorization
================

``GET /api/getpassword/:conversation_id``
------------------------------------------

Asks the server for a randomly generated password that will grant access to a specific conversation, which can be placed in sharable links to conversations and messages. The response type will just be text/plain. This endpoint can only be used by users who were authenticated via the master password.

``POST /api/authenticate``
-----------------------------

The body of this request should contain a password in plain text; an Authorization cookie will be set by the response (which has no body) which will enable future API requests to succeed. The password can either be the master password or one generated for a specific conversation by /api/getpassword/:conversation_id.

Get/Set Conversations Data
===========================

These endpoints return an object containing an array of up to 20 conversation objects pointed to by the key "conversations"; they have the same fields as the conversation database records documented in :ref:`setup.sql <sql_schema>` with the addition of:

* ``name`` - in an individual dm this will be the name of the other person; otherwise it will be the most recent custom group chat name or a list of (up to) the 10 most active participants, as available
* ``image_url`` - the url of the avatar of the other person, or, um, something else, as available.

Also, user IDs are represented as strings to make them JavaScript-safe.

``GET /api/conversations?first=[oldest|newest|mostused|mostusedbyme]&page=[1|2|3|...]&include=[group,individual]``
-------------------------------------------------------------------------------------------------------------------

Gets conversations sorted by time. If you specify first=oldest, the conversations with the oldest first message will be returned first; if you specify first=newest, the conversations with the most recent last message will be returned first; the other options sort by the number of messages or the number of messages sent by you (descending.) The include parameter should be a comma-delimited list of the conversation types that will be included in the results. This is a user-sidecar endpoint (the users are the other people in the individual dms and the person who added you to group dms that you didn't create.)

``GET /api/conversations/withuser?id=[user_id]``
-----------------------------------------------------

Gets the conversations that a specific user has appeared in, ordered by the number of messages they sent in that conversation in descending order. This is a user-sidecar endpoint.

``GET /api/conversation?id=[conversation_id]``
------------------------------------------------

Gets the database record for a specific conversation.

``GET /api/conversations/names?conversation=[conversation_id]&first=[oldest|newest]&page=[1|2|3...]``
------------------------------------------------------------------------------------------------------------

Gets all the names that a (group) conversation has ever had, sorted according to the ``first`` parameter. (Individual conversations cannot have custom names 🙁.) Each page contains 50 objects that correspond to name_updates database records. This is a user-sidecar endpoint. The user ids in the initiator field are presented as strings.

``POST /api/conversations/notes?id=[conversation_id]``
-------------------------------------------------------

Sets a conversation's "notes" field in the database to the plain text in the body of this request. This endpoint can only be used by clients who were authenticated via the master password.

Get Messages
===================

``GET /api/messages?``
-----------------------
Filter clause (optional): ``conversation=[conversation_id]|byuser=[user_id]``

Timezone clause: ``after=[timestamp]|before=[timestamp]|at=[timestamp]``

Search clause (optional): ``search=[query]``

The main endpoint for obtaining messages from the API. "Messages" here includes name updates and participant leaving and joining events; each object received will have a "type" field indicating which of these it is ("message", "join", "leave", "name_update"). Name update objects follow the name_updates database schema; the joining and leaving objects each have a "user_id" field pointing to a string user id and a "timestamp" field. This is a user-sidecar endpoint. Message IDs are presented as strings to make them JavaScript-safe. This endpoint returns 40 messages at a time; the name update and joining and leaving events are additional to that. Message/event objects are always sorted oldest to newest (ascending.)

Proper messages follow the database schema with the addition of a "media" field that contains media objects with a `type` field ("image", "video", or "gif") and a `url `field, a `reactions` array with reactions objects that follow the database reaction schema in the database, and an `html_contents` field that does not include media urls but includes other links as HTML <a> entities.

The filter clause is fairly self explanatory; pick either a conversation= or a byuser= parameter to send in. If it is omitted, any and all messages can come through. If displayed to an end user, conversation events will need to be presented with their conversation name to make things clear.

The timezone clause's first two options can be either "beginning" or "end" respectively, to retrieve messages from the very beginning or very end of the conversation; the "at" option will return the 20 messages from immediately before the timestamp and 20 messages after; if a message was sent at that exact timestamp, it will count as being before it. Events are included if they happened after the given timestamp but before the 40th message if the first option is used and vice versa for the second; for the third, only events that happened after the first returned message and before the last returned message are included. Don't overthink the logic of retrieving a complete set of messages and events as you move in either direction in time; if you want to retrieve messages from before the ones you currently have loaded, just use the before option with the oldest timestamp you have in the messages and events you have; if you want to populate messages from after, use the after option with the newest timestamp you have.

The search clause allows you to further filter message results by their contents. It takes a URL-encoded string containing words that will be searched for individually and quotation mark-surrounded phrases that will be searched for as a unit. Words that are searched for individually will use a "stemmed" index so that searches for "walk" will also match "walking", for example.

``GET /api/message?id=[message_id]``
---------------------------------------

Gets the database record for a specific message.

``GET /api/media/[conversation_id]/[message_id]/[filename]``
---------------------------------------------------------------

Retrieves a media item from the thing.

Get/Set User Data
===================

User objects contain the same data as their database records (documented :ref:`here <sql_schema>`) except that IDs are strings to make the data JavaScript-safe and the "avatar" and "avatar_extension" fields are replaced with a single "avatar_url" one (that corresponds to the avatar-retrieving endpoint below.) If a conversation query parameter is specified, user objects are joined with the participant record that links them to that conversation, which adds messages_sent, start_time, and end_time fields.

``GET /api/users?conversation=[conversation_id]&page=[1|2|3|...]``
----------------------------------------------------------------------

Retrieves an array of users sorted by the number of messages that they have sent. The conversation parameter is optional; if it's supplied, only users with messages in the specified conversation will be returned and they'll be ordered by the number of messages they sent in that conversation.

``GET /api/user?id=[user_id]``
--------------------------------

Gets the database record for a specific user.

``GET /api/userspresent?conversation=[conversation_id]&time=[timestamp]``
-----------------------------------------------------------------------------

Retrieves an array of users that were known to be present in a certain conversation at a certain time. This may be missing users that were added at the very beginning of a conversation that you created if they never gave any sign of their presence by sending a message or updating the conversation name or leaving; this information is simply left out of Twitter archives for unknown reasons.

``GET /api/avatar/[user_id][.optional_file_extension]``
--------------------------------------------------------

Retrieves a user's avatar as an image file. The exact type of image file will be specified in the Content-Type header and can also be part of the url (although that is Optional; the correct file will be returned regardless.)

``POST /api/users/nickname?id=[user_id]``
------------------------------------------

Sets the nickname field in the database for a user to the plain text in the body of this request. Nicknames have a character limit of 50 characters. Can only be used by users authenticated with the master password.

``POST /api/users/notes?id=[user_id]``
---------------------------------------

Sets the notes field for this user to the plain text in the body of this request. This endpoint can only be used by clients who were authenticated via the master password.
