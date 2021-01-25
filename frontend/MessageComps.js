import React, { useState, useRef, useEffect, forwardRef } from "react";
import { useParams, useLocation } from "react-router-dom";
import { addToUserStore } from "./UserComps";
import { zStringToDateTime, zStringToDate } from "./DateHandling";
import { NavLink } from "react-router-dom";

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
  // TODO: convert to class; 8 refs is ridiculous
  const { type, id } = useParams();
  const queries = new URLSearchParams(useLocation().search);
  const search = queries.get("search");
  const startingPlace = queries.get("start") || "end";

  const messagesPane = useRef(null);
  const topMessage = useRef(null);
  const bottomMessage = useRef(null);
  const prevSignpost = useRef(null);

  const [messages, setMessages] = useState(null);
  const [users, setUsers] = useState({});
  const [hitTop, setHitTop] = useState(startingPlace == "beginning");
  const [hitBottom, setHitBottom] = useState(startingPlace == "end");
  let [loading, setLoading] = useState(false);

  const prevScrollHeight = useRef(0);
  const prevScrollTop = useRef(0);
  const lastLoadDirection = useRef("start");
  const signpostPositions = useRef([-1, -1]);

  const url = "/api/messages?";

  const nextQueries = new URLSearchParams();

  if (type == "conversation") {
    nextQueries.set("conversation", id);
  } else if (type == "user") {
    nextQueries.set("byuser", id);
  }

  if (search) {
    nextQueries.set("search", search);
  }

  const restoreScroll = () => {
    // the strategy for maintaining the scroll position in the messages pane even as
    // its contents change wildly is as follows: when the array of JSX objects for
    // the messages are created way down below, the first and last are designated
    // signposts and are given refs (topMessage and bottomMessages). whenever the
    // messages inside messagePane change (detected by seeing its scrollHeight
    // changing), we look at the previous bottom (if we've been loading messages
    // below our current ones) or top (if we've been loading messages above)
    // messages' dom elements to see how much they've moved. that relative change is
    // then applied to the previous scrollPos of the messages pane, and the current
    // scrollPos is set to the result.
    const currentPane = messagesPane.current;
    if (currentPane && topMessage.current && bottomMessage.current) {
      const currentScrollHeight = currentPane.scrollHeight;

      if (prevScrollHeight.current != currentScrollHeight) {
        if (lastLoadDirection.current == "up") {
          const delta =
            prevSignpost.current.offsetTop - signpostPositions.current[0];
          currentPane.scrollTop = prevScrollTop.current + delta;
        } else if (lastLoadDirection.current == "down") {
          const delta =
            prevSignpost.current.offsetTop - signpostPositions.current[1];
          currentPane.scrollTop = prevScrollTop.current + delta;
        } else if (lastLoadDirection.current == "start") {
          // if this is the first load, we have to make sure that the messages
          // are scrolled to that are indicated by the startingPlace parameter.
          if (startingPlace == "end") {
            currentPane.scrollTop = currentScrollHeight;
          } else if (startingPlace == "beginning") {
            currentPane.scrollTop = 0;
          } else {
            // this sets the scrolling position to the middle; TODO: come up
            // with a way to center the message closest to the startingPlace
            // timestamp
            currentPane.scrollTop =
              currentScrollHeight / 2 - messagesPane.current.clientHeight / 2;
          }
        }
        prevScrollHeight.current = currentScrollHeight;
      }

      signpostPositions.current = [
        topMessage.current.offsetTop,
        bottomMessage.current.offsetTop,
      ];
    }
  };

  useEffect(restoreScroll);

  const loadMore = (direction) => {
    if (loading) {
      return;
    }
    setLoading(true);
    // we need the change the captured value for "loading" to prevent staleness if a
    // single version of this function is called twice (once because it's passed to
    // useEffect and once because of it being used as a scroll event listener)
    loading = true;
    lastLoadDirection.current = direction;
    if (direction == "start") {
      if (startingPlace == "beginning") {
        nextQueries.set("after", "beginning");
      } else if (startingPlace == "end") {
        nextQueries.set("before", "end");
      } else {
        nextQueries.set("at", startingPlace);
      }
    } else if (direction == "down") {
      nextQueries.set("after", getTime(messages[messages.length - 1]));
    } else if (direction == "up") {
      nextQueries.set("before", getTime(messages[0]));
    }
    fetch(url + nextQueries.toString()).then((r) =>
      r.json().then((j) => {
        setUsers((oldUsers) => addToUserStore(oldUsers, j.users));
        let newMessages = null;
        if (direction == "start") {
          newMessages = j.results;
        } else if (direction == "down") {
          if (j.results.length) {
            newMessages = messages.concat(j.results);
          } else {
            setHitBottom(true);
          }
        } else if (direction == "up") {
          if (j.results.length) {
            newMessages = j.results.concat(messages);
          } else {
            setHitTop(true);
          }
        }
        if (newMessages) {
          const newLength = newMessages.length;
          if (newLength > 100) {
            if (direction == "down") {
              newMessages = newMessages.slice(newLength - 100, newLength);
              if (hitTop) {
                setHitTop(false);
              }
            } else if (direction == "up") {
              newMessages = newMessages.slice(0, 100);
              if (hitBottom) {
                setHitBottom(false);
              }
            }
          }
          if (direction == "up") {
            prevSignpost.current = topMessage.current;
          } else if (direction == "down") {
            prevSignpost.current = bottomMessage.current;
          }
          // TODO: obviously change when the message component does
          newMessages = newMessages.filter((v) => v.schema == "Message");
          setMessages(newMessages);
        }
        setLoading(false);
      })
    );
  };

  const scrollChecks = () => {
    const el = messagesPane.current;
    const currentScrollTop = el.scrollTop;
    prevScrollTop.current = currentScrollTop;
    if (loading) {
      return;
    }
    if (!messages) {
      loadMore("start");
    } else if (el.scrollHeight < el.parentElement.scrollHeight) {
      if (!hitTop) {
        loadMore("up");
      } else if (!hitBottom) {
        loadMore("down");
      }
    } else if (
      el.scrollTop + el.offsetHeight > el.scrollHeight - 100 &&
      !hitBottom
    ) {
      loadMore("down");
    } else if (el.scrollTop < 100 && !hitTop) {
      loadMore("up");
    }
  };

  useEffect(scrollChecks);

  let renderedMessages = null;
  if (messages?.length) {
    const signpost1 = (
      <ComplexMessage
        {...messages[0]}
        sender={users[messages[0].sender]}
        key={messages[0].id}
        ref={topMessage}
      />
    );
    const signpost2 = (
      <ComplexMessage
        {...messages[messages.length - 1]}
        sender={users[messages[messages.length - 1].sender]}
        key={messages[messages.length - 1].id}
        ref={bottomMessage}
      />
    );
    renderedMessages = [
      signpost1,
      ...messages
        .slice(1, messages.length - 1)
        .map((v) => (
          <ComplexMessage
            {...v}
            sender={users[v.sender]}
            key={v.id ? v.id : v.time}
          />
        )),
      signpost2,
    ];
  }

  return (
    <>
      <h1>Messages</h1>
      <div ref={messagesPane} onScroll={scrollChecks} id="messagesPane">
        {renderedMessages}
      </div>
    </>
  );
}

function MediaItem(props) {
  if (props.media.type == "image") {
    return <img className={props.className} src={props.media.src} />;
  } else if (props.media.type == "video") {
    return <video controls className={props.className} src={props.media.src} />;
  } else if (props.media.type == "gif") {
    return (
      <video
        muted
        autoPlay
        loop
        className={props.className}
        src={props.media.src}
      />
    );
  } else {
    console.error(
      "media item of type " + media.type + " received; type not recognized"
    );
    console.error(JSON.stringify(props.media, null, 2));
    return null;
  }
}

function SimpleMessage(message) {
  if (message.schema !== "Message") {
    return null;
  }
  const el = document.createElement("p");
  el.innerHTML = message.html_content;
  for (const a of el.querySelectorAll("a")) {
    a.target = "_blank";
  }
  const user = message.sender;
  const mediaItems = message.media.map((i) => (
    <MediaItem media={i} key={i.id} className="smallMedia" />
  ));
  return (
    <>
      {mediaItems}
      <p style={{ textAlign: "center" }}>
        <span dangerouslySetInnerHTML={{ __html: el.innerHTML }}></span>
        {" - "}
        <NavLink to={"/user/info/" + user.id}>
          {(user.nickname || user.display_name) + ` (@${user.handle})`}
        </NavLink>
        {", " + zStringToDate(message.sent_time)}
      </p>
    </>
  );
}

const ComplexMessage = forwardRef(function FullMessage(message, ref) {
  if (message.schema !== "Message") {
    return null;
  }
  const el = document.createElement("p");
  el.innerHTML = message.html_content;
  for (const a of el.querySelectorAll("a")) {
    a.target = "_blank";
  }
  const user = message.sender;
  const mediaItems = message.media.map((i) => (
    <MediaItem media={i} key={i.id} className="smallMedia" />
  ));
  return (
    <div
      ref={ref}
      style={{ display: "flex", flexDirection: "column", alignItems: "center" }}
    >
      {mediaItems}
      <p style={{ textAlign: "center" }}>
        <span dangerouslySetInnerHTML={{ __html: el.innerHTML }}></span>
        {" - "}
        <NavLink to={"/user/info/" + user.id}>
          {(user.nickname || user.display_name) + ` (@${user.handle})`}
        </NavLink>
        {", " + zStringToDate(message.sent_time)}
      </p>
    </div>
  );
});

export { MessagePage, SimpleMessage };
