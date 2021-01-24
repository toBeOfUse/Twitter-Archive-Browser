import React, { useState, useRef, useEffect } from "react";
import { useParams, useLocation } from "react-router-dom";
import { addToUserStore } from "./UserComps";
import { zStringToDateTime } from "./DateHandling";

function getTime(message) {
    if (message.schema == "Message") {
        return message.sent_time;
    } else if (message.schema == "NameUpdate") {
        return message.update_time;
    } else {
        return message.time;
    }
}

function MessagePage() {
    const { type, id } = useParams();
    const queries = new URLSearchParams(useLocation().search);
    const search = queries.get("search");
    const startingPlace = queries.get("start");

    const messagesPane = useRef(null);

    const [messages, setMessages] = useState(null);
    const [users, setUsers] = useState({});
    const [hitTop, setHitTop] = useState(false);
    const [hitBottom, setHitBottom] = useState(false);
    const [loading, setLoading] = useState(false);

    const [prevScrollHeight, setPrevScrollHeight] = useState(0);
    const [prevScrollTop, setPrevScrollTop] = useState(0);
    const [lastLoadDirection, setLastLoadDirection] = useState("start");

    if (messagesPane.current) {

        const currentScrollHeight = messagesPane.current.scrollHeight;
        const currentScrollTop = messagesPane.current.scrollTop;

        if (prevScrollHeight != currentScrollHeight) {
            if (lastLoadDirection == "up") {
                messagesPane.current.scrollTop = prevScrollTop + (currentScrollHeight - prevScrollHeight);
            } else if (lastLoadDirection == "down") {
                messagesPane.current.scrollTop = prevScrollTop;
            } else if (lastLoadDirection == "start") {
                if (!startingPlace || startingPlace == "end") {
                    messagesPane.current.scrollTop = currentScrollHeight - messagesPane.current.offsetHeight;
                } else if (startingPlace == "beginning") {
                    messagesPane.current.scrollTop = 0;
                }
                // this needs to be different if start is at a specific timestamp;
                // then, we need to find that message and scroll to it and highlight
                // it? maybe? 
            }
        }

        if (currentScrollHeight != prevScrollHeight) {
            setPrevScrollHeight(currentScrollHeight);
        }
        if (currentScrollTop != prevScrollTop) {
            setPrevScrollTop(currentScrollTop);
        }
    }

    const url = "/api/messages?"

    const nextQueries = new URLSearchParams();

    if (type == "conversation") {
        nextQueries.set("conversation", id);
    } else if (type == "user") {
        nextQueries.set("byuser", id);
    }

    if (search) {
        nextQueries.set("search", search);
    }

    const loadMore = direction => {
        setLastLoadDirection(direction);
        if (direction == "start") {
            if (startingPlace == "beginning") {
                nextQueries.set("after", "beginning");
            } else if (startingPlace == "end" || !startingPlace) {
                nextQueries.set("before", "end");
            } else {
                nextQueries.set("at", startingPlace);
            }
        } else if (direction == "down") {
            nextQueries.set("after", getTime(messages[messages.length - 1]));
        } else if (direction == "up") {
            nextQueries.set("before", getTime(messages[0]));
        }
        setLoading(true);
        fetch(url + nextQueries.toString()).then(r => r.json().then(j => {
            if (direction == "start") {
                setMessages(j.results);
            } else if (direction == "down") {
                if (j.results.length) {
                    setMessages(oldMessages => oldMessages.concat(j.results));
                } else {
                    setHitBottom(true);
                }
            } else if (direction == "up") {
                if (j.results.length) {
                    setMessages(oldMessages => j.results.concat(oldMessages));
                } else {
                    setHitTop(true);
                }
            }
            setUsers(oldUsers => addToUserStore(oldUsers, j.users));
            setLoading(false);
        }));
    }

    const checkMessages = () => {
        if (loading) {
            return;
        }
        const el = messagesPane.current;
        if (!messages) {
            loadMore("start");
        } else if (el.scrollHeight < el.parentElement.scrollHeight) {
            if (!hitTop) {
                loadMore("up");
            } else if (!hitBottom) {
                loadMore("down")
            }
        } else if (el.scrollTop + el.offsetHeight > el.scrollHeight - 30 && !hitBottom) {
            loadMore("down");
        } else if (el.scrollTop < 30 && !hitTop) {
            loadMore("up");
        }
    }

    useEffect(checkMessages);

    return <>
        <h1>Messages</h1>
        <div ref={messagesPane} onScroll={checkMessages} id="messagesPane">
            {messages && messages.map(v => {
                const innerHtml = v.html_content +
                    " - @" + users[v.sender]?.handle + ", " +
                    zStringToDateTime(v.sent_time);
                return <p
                    style={{ textAlign: "center" }}
                    key={v.id}
                    dangerouslySetInnerHTML={{ __html: innerHtml }}
                ></p>
            })}
        </div>
    </>
}

export {
    MessagePage
}