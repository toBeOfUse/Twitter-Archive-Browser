"""
API Documentation
=================

All API requests must contain an Authorization cookie obtained from /api/authenticate. All query string parameters are required unless otherwise indicated. Page numbers start at 1. The standard way to display a user's name is "display name (@handle) | nickname if it exists". Because top-level JSON arrays constitute a security risk, arrays returned by these endpoints will be wrapped in an object with the key "results" pointing to the payload.

Messagelikes
------------

Messagelikes, represented here as objects that inherit from `ArchiveAccess.DBRead.MessageLike`, represent pieces of information that fit naturally in the flow of a conversation, including regular messages. Because messagelikes in any given conversation tend to reference the same users over and over again, it would be highly redundant for each of them to contain nested user objects; instead, they simply contain user ids, and when they are requested from the API, the top-level JSON object that is returned contains a "results" array and a "users" array, containing the requested serialized MessageLike objects and serialized `ArchiveAccess.DBRead.ArchivedUserSummary` objects, respectively.

Authorization
-------------

### `GET /api/getpassword/:conversation_id`

Asks the server for a randomly generated password that will grant access to a specific conversation, which can be placed in sharable links to conversations and messages. The response type will be text/plain. This endpoint can only be used by users who were authenticated via the master password.

### `POST /api/authenticate`

The body of this request should contain a password in plain text; an Authorization cookie will be set by the response (which has no body) which will enable future API requests to succeed. The password can either be the master password or one generated for a specific conversation by /api/getpassword/:conversation_id.

Get/Set Conversations Data
--------------------------

These endpoints return up to 20 serialized `ArchiveAccess.DBRead.Conversation` objects.

### `GET /api/conversations?first=[oldest|newest|mostused|mostusedbyme]&page=[1|2|3|...]&types=[group-individual]`

Gets conversations sorted by time. If you specify first=oldest, the conversations with the oldest first message will be returned first; if you specify first=newest, the conversations with the most recent last message will be returned first; the other options sort by the number of messages or the number of messages sent by you (descending.) The types parameter should be a dash-delimited list of the conversation types ("group" and "individual") that will be included in the results.

### `GET /api/conversations/withuser?id=[user_id]&page=[1|2|3]...`

Gets the conversations that a specific user has appeared in, ordered by the number of messages they sent in that conversation in descending order.

### `GET /api/conversation?id=[conversation_id]`

Gets the database record for a specific conversation.

### `GET /api/conversation/names?conversation=[conversation_id]&first=[oldest|newest]&page=[1|2|3...]`

Gets all the names that a (group) conversation has ever had, sorted according to the `first` parameter. (Individual conversations cannot have custom names 🙁.) Each page contains up to 50 serialized `ArchiveAccess.DBRead.NameUpdate` objects. Because name updates are messagelikes, they are enclosed in a "results" array and accompanied by a "users" array in the returned JSON object.

### `POST /api/conversation/notes?id=[conversation_id]`

Sets a conversation's "notes" field in the database to the plain text in the body of this request. This endpoint can only be used by clients who were authenticated via the master password.

Get Messages
------------

### `GET /api/messages?`

Filter clause (optional): `conversation=[conversation_id]|byuser=[user_id]`

Timezone clause: `after=[timestamp]|before=[timestamp]|at=[timestamp]`

Search clause (optional): `search=[query]`

The main endpoint for obtaining messages from the API. This endpoint's payload includes all messagelike objects; in other words, any that inherit from `ArchiveAccess.DBRead.MessageLike`. You can tell which type each object has by looking at the "schema" field in the serialized result, which contains the name of the original object's class. This endpoint returns 40 normal messages at a time; the name update and joining and leaving events are additional to that. Message/event objects are always sorted oldest to newest (ascending.)

Note that the html_contents field in normal messages contains links presented as HTML \<a> tags.

The filter clause is fairly self explanatory; pick either a conversation= or a byuser= parameter to send in. If it is omitted, any and all messages can come through, and if displayed to an end user, conversation events will need to be presented with their conversation name to make things clear.

The timezone clause's first two options can be either "beginning" or "end" respectively, to retrieve messages from the very beginning or very end of the conversation; the "at" option will return the 20 messages from immediately before the timestamp and 20 messages after; if a message was sent at that exact timestamp, it will count as being before it. Events are included if they happened after the given timestamp but before the 40th message if the first option is used and vice versa for the second; for the third, only events that happened after the first returned message and before the last returned message are included. The exception is when you are at the very beginning or very end of the conversation, in which case all the events before the first message/after the last message are returned. Don't overthink the logic of retrieving a complete set of messages and events as you move in either direction in time; if you want to retrieve messages from before the ones you currently have loaded, just use the before option with the oldest timestamp you have in the messages and events you have; if you want to populate messages from after, use the after option with the newest timestamp you have. You can tell your traversal is done when this endpoint returns 0 messages or messagelikes.

The search clause allows you to further filter message results by their contents. It takes a URL-encoded string containing words that will be searched for individually and quotation mark-surrounded phrases that will be searched for as a unit. Words that are searched for individually will use a "stemmed" index so that searches for "walk" will also match "walking", for example.

### `GET /api/message?id=[message_id]`

Gets the database record for a specific message; the message will still be contained in a "results" array alongside a "users" array.

### `GET /api/media/[group|individual]/[filename]`

Retrieves media from the folder in the Twitter archive where it is stored. Media objects returned with messages already include the /group/ or /individual/ components in their "file_path" fields, so to get a url to retrieve media based on those, just append their file_path to "/api/media".

Get/Set User Data
-----------------

This endpoint returns serialized `ArchiveAccess.DBRead.ArchivedUser` objects; 20 are returned per page.

### `GET /api/users?conversation=[conversation_id]&page=[1|2|3|...]`

Retrieves an array of users sorted by the number of messages that they have sent. The conversation parameter is optional; if it's supplied, only users with messages in the specified conversation will be returned they'll be ordered by the number of messages they sent in that conversation, and the `ArchiveAccess.DBRead.ArchivedParticipant` class will be used instead of the `ArchiveAccess.DBRead.ArchivedUser` class.

### `GET /api/user?id=[user_id]`

Gets the database record for a specific user.

### `GET /api/userspresent?conversation=[conversation_id]&time=[timestamp]` NOT IMPLEMENTED YET

Retrieves an array of users that were known to be present in a certain conversation at a certain time. This may be missing users that were added at the very beginning of a conversation that you created if they never gave any sign of their presence by sending a message or updating the conversation name or leaving; this information is simply left out of Twitter archives for unknown reasons.

### `GET /api/avatar/[user_id][.optional_file_extension]`

Retrieves a user's avatar as an image file. The exact type of image file will be specified in the Content-Type header and can also be part of the url (although that is Optional; the correct file will be returned regardless.)

### `POST /api/user/nickname?id=[user_id]`

Sets the nickname field in the database for a user to the plain text in the body of this request. Nicknames have a character limit of 50 characters. Can only be used by users authenticated with the master password.

### `POST /api/user/notes?id=[user_id]`

Sets the notes field for this user to the plain text in the body of this request. This endpoint can only be used by clients who were authenticated via the master password.

"""