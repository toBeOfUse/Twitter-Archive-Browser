import React, { useState, useRef, useEffect, forwardRef } from "react";
import { useLocation, useHistory, Link } from "react-router-dom";
import { addToUserStore } from "./UserComps";
import {
  zStringToDateTime,
  zStringToDate,
  zStringDiffMinutes,
} from "./DateHandling";
import { render } from "react-dom";

function getTime(message) {
  if (message.schema == "Message") {
    return message.sent_time;
  } else if (message.schema == "NameUpdate") {
    return message.update_time;
  } else {
    return message.time;
  }
}

function MessagePage(props) {
  const location = useLocation();
  const history = useHistory();

  const { startingPlace } = props;

  const locationKey =
    location.key + (props.search ? "&search=" + props.search : "");

  const savedState = JSON.parse(window.sessionStorage.getItem(locationKey));

  const DOMState = useRef({
    // dom elements to be observed
    messagesPane: null,
    topMessage: null,
    bottomMessage: null,
    signpostElement: null,
    // measurements that assist with scroll position preservation in restoreScroll
    prevSignpostPosition: -1,
    prevScrollTop: savedState?.scrollTop || 0,
    // used to store a history listener and a cleanup function for it that will be
    // created in this render
    prevSaveState: null,
    prevSaveStateCleanup: null,
  }).current;

  const [messages, setMessages] = useState(savedState?.messages);
  const [users, setUsers] = useState(savedState?.users || {});
  const [hitTop, setHitTop] = useState(
    savedState?.hitTop ?? startingPlace == "beginning"
  );
  const [hitBottom, setHitBottom] = useState(
    savedState?.hitBottom ?? startingPlace == "end"
  );
  // loading could currently be converted to a ref/instance variable but it could
  // also be used in rendering to display a spinner in the future so idk
  let [loading, setLoading] = useState(false);

  DOMState.prevSaveStateCleanup && DOMState.prevSaveStateCleanup();
  DOMState.prevSaveState &&
    window.removeEventListener("beforeunload", DOMState.prevSaveState);
  const saveState = (event, action) => {
    if ((action == "PUSH" || action == "POP" || event.type) && messages) {
      console.log("saving current state under key " + locationKey);
      window.sessionStorage.setItem(
        locationKey,
        JSON.stringify({
          messages,
          users,
          hitTop,
          hitBottom,
          scrollTop: messagesPane.scrollTop,
        })
      );
    }
    DOMState.prevSaveStateCleanup();
  };
  DOMState.prevSaveStateCleanup = history.listen(saveState);
  window.addEventListener("beforeunload", saveState);
  DOMState.prevSaveState = savedState;

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
      delete savedState.scrollTop;
      window.sessionStorage.setItem(locationKey, JSON.stringify(savedState));
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
          // this sets the scrolling position to the middle; TODO: come up
          // with a way to center the message closest to the startingPlace
          // timestamp
          currentPane.scrollTop =
            currentScrollHeight / 2 - currentPane.clientHeight / 2;
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
        setUsers((oldUsers) => addToUserStore(oldUsers, j.users));
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

  const getUser = (message) =>
    users[message.sender || message.initiator || message.participant];

  let renderedMessages = null;
  if (messages?.length) {
    let nextUser = messages.length > 1 ? getUser(messages[1]) : null;
    renderedMessages = [
      <ComplexMessage
        {...messages[0]}
        user={getUser(messages[0])}
        users={users}
        sameUserAsNext={
          nextUser &&
          getUser(messages[0]).id == nextUser.id &&
          zStringDiffMinutes(getTime(messages[0]), getTime(messages[1])) < 2
        }
        showContextLink={!!props.search}
        key={messages[0].id}
        ref={(n) => (DOMState.topMessage = n)}
      />,
    ];
    for (let i = 1; i < messages.length - 1; i++) {
      const v = messages[i];
      const user = nextUser;
      nextUser = getUser(messages[i + 1]);
      renderedMessages.push(
        <ComplexMessage
          {...v}
          user={user}
          users={users}
          showContextLink={!!props.search}
          sameUserAsNext={
            user.id == nextUser.id &&
            zStringDiffMinutes(getTime(v), getTime(messages[i + 1])) < 2
          }
          key={v.id}
        />
      );
    }
    if (renderedMessages.length > 1) {
      renderedMessages.push(
        <ComplexMessage
          {...messages[messages.length - 1]}
          showContextLink={!!props.search}
          user={getUser(messages[messages.length - 1])}
          users={users}
          key={messages[messages.length - 1].id}
          sameUserAsNext={false}
          ref={(n) => (DOMState.bottomMessage = n)}
        />
      );
    }
  } else if (hitTop && hitBottom) {
    renderedMessages = <p>No messages found, sorry :(</p>;
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
        <h1 style={{ display: "inline" }}>Messages</h1>{" "}
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
        <Link to={"/user/info/" + user.id}>
          {(user.nickname || user.display_name) + ` (@${user.handle})`}
        </Link>
        {", " + zStringToDate(message.sent_time)}
      </p>
    </>
  );
}

const ComplexMessage = forwardRef(function FullMessage(message, ref) {
  let content;
  let alignment;
  const user = message.user;
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
            backgroundColor: "#96d3ff",
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
          <span
            className="messageAttribution"
            style={alignment == "end" ? { marginLeft: "auto" } : null}
          >
            <Link to={"/user/info/" + user.id}>
              {(user.nickname || user.display_name) + ` (@${user.handle})`}
            </Link>
            {", " + zStringToDateTime(message.sent_time)}
            {message.showContextLink ? (
              <>
                <br />
                <Link
                  to={
                    "/conversation/messages/" +
                    message.conversation +
                    "?start=" +
                    message.sent_time
                  }
                >
                  (see in context)
                </Link>
              </>
            ) : null}
          </span>
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
    const added_by = message.users[message.added_by];
    content = (
      <p style={{ textAlign: "center" }}>
        <Link to={"/user/info/" + user.id}>
          {user.nickname || `@${user.handle}`}
        </Link>{" "}
        was added to the conversation by{" "}
        <Link to={"/user/info/" + message.added_by}>
          {added_by.nickname || `@${added_by.handle}`}
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
