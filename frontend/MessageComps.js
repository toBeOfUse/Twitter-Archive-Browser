import React, { useState, useRef, useEffect, forwardRef } from "react";
import { useLocation, useHistory, Link } from "react-router-dom";
import {
  zStringToDateTime,
  zStringToDate,
  zStringDiffMinutes,
} from "./DateHandling";
import { SearchBar } from "./ConversationComps";
import LoadingSpinner from "./LoadingSpinner";
import { useDispatch, useSelector } from "react-redux";

function getTime(message) {
  if (message.schema == "Message") {
    return message.sent_time;
  } else if (message.schema == "NameUpdate") {
    return message.update_time;
  } else {
    return message.time;
  }
}

function getUserID(message) {
  return message?.sender || message?.initiator || message?.participant;
}

function MessagePage(props) {
  const location = useLocation();
  console.log(location);
  const history = useHistory();

  const { startingPlace } = props;

  const locationKey = location.key + location.search;

  const savedState = useSelector((state) => state.pageState[locationKey]);

  const DOMState = useRef({
    // dom elements to be observed
    messagesPane: null,
    topMessage: null,
    bottomMessage: null,
    signpostElement: null,
    highlightElement: null,
    // measurements that assist with scroll position preservation in restoreScroll
    prevSignpostPosition: -1,
    prevScrollTop: savedState?.scrollTop || 0,
    // used to store a cleanup function for the history listener that will be created
    // in this render
    prevSaveStateCleanup: null,
  }).current;

  const [messages, setMessages] = useState(savedState?.messages);
  const [hitTop, setHitTop] = useState(
    savedState?.hitTop ?? startingPlace == "beginning"
  );
  const [hitBottom, setHitBottom] = useState(
    savedState?.hitBottom ?? startingPlace == "end"
  );
  const [conversationName, setConversationName] = useState("");
  // loading could currently be converted to a ref/instance variable but it could
  // also be used in rendering to display a spinner in the future so idk
  let [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const name = useSelector((state) => {
    if (props.type == "conversation") {
      return state.conversations[props.id]?.name;
    } else if (props.type == "user") {
      return state.users[props.id]?.name;
    }
  });

  const getName = () => {
    if (name) {
      setConversationName(name);
    } else if (props.type == "conversation") {
      fetch("/api/conversation?id=" + props.id).then((r) =>
        r.json().then((j) => {
          dispatch({
            type: "conversations/addConversations",
            payload: [j],
          });
          setConversationName(j.name);
        })
      );
    } else if (props.type == "user") {
      fetch("/api/user?id=" + props.id).then((r) =>
        r.json().then((j) => {
          dispatch({
            type: "users/addUsers",
            payload: [j],
          });
          setConversationName(
            "from " + (j.nickname || j.display_name + " (@" + j.handle + ")")
          );
        })
      );
    } else {
      setConversationName("all messages");
    }
  };

  useEffect(getName, []);

  DOMState.prevSaveStateCleanup && DOMState.prevSaveStateCleanup();
  const saveState = (event, action) => {
    if ((action == "PUSH" || action == "POP" || event.type) && messages) {
      console.log("saving current state under key " + locationKey);
      console.log("event is ", action || event);
      dispatch({
        type: "pageState/save",
        payload: {
          [locationKey]: {
            messages,
            hitTop,
            hitBottom,
            scrollTop: DOMState.prevScrollTop,
          },
        },
      });
    }
    DOMState.prevSaveStateCleanup();
  };
  DOMState.prevSaveStateCleanup = history.listen(saveState);

  const restoreScroll = () => {
    // the strategy for maintaining the scroll position in the messages pane even as
    // its contents change wildly is as follows:  right before the messages inside
    // messagePane are updated via a call to setMessages, DOMState.signpostElement is
    // set to the DOM node of a message that is going to continue to exist after the
    // update and DOMState.prevSignpostPosition is set to its pre-update offsetTop
    // position. then, when the messages change, this effect is called, and we obtain
    // the element's updated position; the change in the signpost element's position
    // is then applied to the message pane's pre-update scroll position; therefore,
    // the scroll position remains the same relative to the messages that were
    // previously on the page and visible to the user.
    const currentPane = DOMState.messagesPane;
    console.log("restoring scroll position");
    console.log("it is currently", currentPane?.scrollTop);
    console.log("it used to be", DOMState.prevScrollTop);
    if (savedState?.scrollTop) {
      currentPane.scrollTop = savedState.scrollTop;
    } else if (currentPane) {
      currentPane.focus();
      if (DOMState.signpostElement) {
        console.log("signpost used to be at", DOMState.prevSignpostPosition);
        console.log("signpost is now at", DOMState.signpostElement.offsetTop);
        const delta =
          DOMState.signpostElement.offsetTop - DOMState.prevSignpostPosition;
        currentPane.scrollTop = DOMState.prevScrollTop + delta;
      } else {
        // if the signpost value is null, this is the first render
        const currentScrollHeight = currentPane.scrollHeight;
        // if this is the first load, we have to make sure that the messages
        // are scrolled to that are indicated by the startingPlace parameter.
        if (startingPlace == "end") {
          currentPane.scrollTop = currentScrollHeight;
        } else if (startingPlace == "beginning") {
          currentPane.scrollTop = 0;
        } else {
          if (DOMState.highlightElement) {
            const el = DOMState.highlightElement;
            currentPane.scrollTop =
              el.offsetTop - currentPane.offsetHeight / 2 + el.offsetHeight / 2;
          } else {
            currentPane.scrollTop =
              currentScrollHeight / 2 - currentPane.clientHeight / 2;
          }
        }
      }
    }
  };

  useEffect(restoreScroll, [messages]);

  const loadMore = (direction) => {
    if (loading) {
      return;
    }
    setLoading(true);
    // we need the change the captured value for "loading" to prevent staleness if a
    // single version of this function is called twice (once because it's passed to
    // useEffect and once because of it being used as a scroll event listener)
    loading = true;

    const url = "/api/messages?";
    const nextQueries = new URLSearchParams();

    if (props.type == "conversation") {
      nextQueries.set("conversation", props.id);
    } else if (props.type == "user") {
      nextQueries.set("byuser", props.id);
    }
    if (props.search) {
      nextQueries.set("search", props.search);
    }

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
        dispatch({
          type: "users/addUsers",
          payload: j.users,
        });
        let newMessages = null;
        if (direction == "start") {
          if (j.results.length) {
            newMessages = j.results;
          } else {
            setHitBottom(true);
            setHitTop(true);
          }
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
          console.log(
            "going " +
              direction +
              "; setting relevant signpost; then setting messages"
          );
          if (direction == "up") {
            DOMState.signpostElement = DOMState.topMessage;
            DOMState.prevSignpostPosition = DOMState.topMessage.offsetTop;
          } else if (direction == "down") {
            DOMState.signpostElement = DOMState.bottomMessage;
            DOMState.prevSignpostPosition = DOMState.bottomMessage.offsetTop;
          }
          setMessages(newMessages);
        }
        setLoading(false);
      })
    );
  };

  const scrollChecks = () => {
    const el = DOMState.messagesPane;
    const currentScrollTop = el.scrollTop;
    DOMState.prevScrollTop = currentScrollTop;
    if (loading) {
      return;
    }
    if (!messages && !(hitTop && hitBottom)) {
      loadMore("start");
    } else if (el.scrollHeight < el.parentElement.scrollHeight) {
      if (!hitTop) {
        loadMore("up");
      } else if (!hitBottom) {
        loadMore("down");
      }
    } else if (
      el.scrollTop + el.offsetHeight > el.scrollHeight - 200 &&
      !hitBottom
    ) {
      loadMore("down");
    } else if (el.scrollTop < 200 && !hitTop) {
      loadMore("up");
    }
  };

  useEffect(scrollChecks);

  const distributeRefs = (message) => {
    return (node) => {
      if (message.sent_time == startingPlace) {
        DOMState.highlightElement = node;
      }
      if (message.id == messages[0].id) {
        DOMState.topMessage = node;
      }
      if (message.id == messages[messages.length - 1].id) {
        DOMState.bottomMessage = node;
      }
    };
  };

  let renderedMessages = null;
  if (messages?.length) {
    let nextUser = getUserID(messages[0]);
    renderedMessages = [];
    for (let i = 0; i < messages.length; i++) {
      const message = messages[i];
      const user = nextUser;
      nextUser = getUserID(messages[i + 1]);
      renderedMessages.push(
        <ComplexMessage
          {...message}
          showContextLink={!!props.search}
          sameUserAsNext={
            nextUser &&
            user == nextUser &&
            zStringDiffMinutes(getTime(message), getTime(messages[i + 1])) < 2
          }
          highlight={message.sent_time == startingPlace}
          ref={distributeRefs(message)}
          key={message.id}
        />
      );
    }
  } else if (hitTop && hitBottom) {
    renderedMessages = <p>No messages found, sorry :(</p>;
  } else {
    renderedMessages = <LoadingSpinner />;
  }

  return (
    <>
      <div
        style={{
          margin: "20px 0",
          width: "100%",
          borderBottom: "1px solid black",
        }}
      >
        <h1 style={{ display: "inline", marginRight: 5 }}>
          Messages - {conversationName}
        </h1>
        <br />
        <Link
          replace
          to={
            location.pathname +
            "?start=beginning" +
            (props.search ? "&search=" + props.search : "")
          }
        >
          Zoom to top
        </Link>
        {" | "}
        <Link
          replace
          to={
            location.pathname +
            "?start=end" +
            (props.search ? "&search=" + props.search : "")
          }
        >
          Sink to bottom
        </Link>
      </div>
      <div
        ref={(n) => (DOMState.messagesPane = n)}
        onScroll={scrollChecks}
        id="messagesPane"
      >
        {renderedMessages}
      </div>
      <SearchBar baseURL={location.pathname} />
    </>
  );
}

function MediaItem(props) {
  if (props.media.type == "image") {
    return (
      <img
        className={props.className}
        style={props.style}
        src={props.media.src}
      />
    );
  } else if (props.media.type == "video") {
    return (
      <video
        controls
        className={props.className}
        style={props.style}
        src={props.media.src}
      />
    );
  } else if (props.media.type == "gif") {
    return (
      <video
        muted
        autoPlay
        loop
        className={props.className}
        src={props.media.src}
        style={props.style}
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
  const user = useSelector((state) => state.users[message.sender]);
  const mediaItems = message.media.map((i) => (
    <MediaItem media={i} key={i.id} className="smallMedia" />
  ));
  return (
    <>
      {mediaItems}
      <p style={{ textAlign: "center" }}>
        <span dangerouslySetInnerHTML={{ __html: el.innerHTML }}></span>
        {" - "}
        <Link to={"/user/info/" + user.id}>
          {(user.nickname || user.display_name) + ` (@${user.handle})`}
        </Link>
        {", " + zStringToDate(message.sent_time) + " "}
        <Link
          to={
            "/conversation/messages/" +
            message.conversation +
            "?start=" +
            message.sent_time
          }
        >
          (context)
        </Link>
      </p>
    </>
  );
}

const ComplexMessage = forwardRef(function FullMessage(message, ref) {
  let content;
  let alignment;
  const user = useSelector((state) => state.users[getUserID(message)]);
  const addedBy = useSelector((state) =>
    message.added_by ? state.users[message.added_by] : null
  );
  if (message.schema == "Message") {
    alignment = user.is_main_user ? "end" : "start";
    let textSection = null;
    if (message.html_content) {
      const el = document.createElement("p");
      el.innerHTML = message.html_content;
      for (const a of el.querySelectorAll("a")) {
        a.target = "_blank";
      }
      textSection = (
        <p
          className="messageText"
          style={{
            backgroundColor: message.highlight ? "#ff7878" : "#96d3ff",
            marginLeft: alignment == "end" ? "auto" : 0,
            maxWidth: "70%",
          }}
          dangerouslySetInnerHTML={{ __html: el.innerHTML }}
        />
      );
    }
    const mediaItems = message.media.map((i) => (
      <MediaItem
        media={i}
        key={i.id}
        className="smallMedia"
        style={alignment == "end" ? { marginLeft: "auto" } : null}
      />
    ));
    content = (
      <>
        {mediaItems}
        {textSection}
        {!message.sameUserAsNext ? (
          <>
            <span
              className="messageAttribution"
              style={alignment == "end" ? { marginLeft: "auto" } : null}
            >
              <Link to={"/user/info/" + user.id}>
                {(user.nickname || user.display_name) + ` (@${user.handle})`}
              </Link>
              {", " + zStringToDateTime(message.sent_time)}
            </span>
            {message.showContextLink ? (
              <Link
                to={
                  "/conversation/messages/" +
                  message.conversation +
                  "?start=" +
                  message.sent_time
                }
                className="messageAttribution"
                style={alignment == "end" ? { marginLeft: "auto" } : null}
              >
                (see in context)
              </Link>
            ) : null}
          </>
        ) : null}
      </>
    );
  } else if (message.schema == "NameUpdate") {
    alignment = "center";
    content = (
      <p style={{ textAlign: "center" }}>
        <Link to={"/user/info/" + user.id}>
          {user.nickname || `@${user.handle}`}
        </Link>{" "}
        changed the conversation's name to {message.new_name} (
        {zStringToDateTime(message.update_time)})
      </p>
    );
  } else if (message.schema == "ParticipantLeave") {
    alignment = "center";
    content = (
      <p style={{ textAlign: "center" }}>
        <Link to={"/user/info/" + user.id}>
          {user.nickname || `@${user.handle}`}
        </Link>{" "}
        left the conversation. ({zStringToDateTime(message.time)})
      </p>
    );
  } else if (message.schema == "ParticipantJoin") {
    alignment = "center";
    content = (
      <p style={{ textAlign: "center" }}>
        <Link to={"/user/info/" + user.id}>
          {user.nickname || `@${user.handle}`}
        </Link>{" "}
        was added to the conversation by{" "}
        <Link to={"/user/info/" + message.added_by}>
          {addedBy.nickname || `@${addedBy.handle}`}
        </Link>
        . ({zStringToDateTime(message.time)})
      </p>
    );
  }
  let containerClass = "messageContainer";
  if (message.schema == "Message" && !message.sameUserAsNext) {
    containerClass += " marginedMessage";
  }
  return (
    <div ref={ref} className={containerClass} style={{ alignItems: alignment }}>
      {content}
    </div>
  );
});

export { MessagePage, SimpleMessage };
