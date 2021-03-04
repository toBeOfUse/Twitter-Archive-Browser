import "normalize.css";
import "./assets/css/index.css";
import React, { useEffect, useState, useRef } from "react";
import ReactDOM from "react-dom";
import {
  BrowserRouter as Router,
  Switch,
  Route,
  Redirect,
  useLocation,
} from "react-router-dom";
import { configureStore } from "@reduxjs/toolkit";
import { Provider, useDispatch } from "react-redux";
import produce from "immer";
import { ConversationList, ConversationInfo } from "./ConversationComps";
import { UserInfo } from "./UserComps";
import { GlobalStats } from "./GlobalStats";
import { MessagePage } from "./MessageComps";
import titles from "./routes.json";
import LoadingSpinner from "./LoadingSpinner";

const addToIDMap = (IDMap, items) => {
  return Object.assign({}, IDMap, ...items.map((i) => ({ [i.id]: i })));
};

const store = configureStore({
  reducer: {
    users: (state = {}, action) => {
      // note: redux stores ArchivedUserSummary objects, not the full user data that
      // is used by UserInfo in UserComps
      switch (action.type) {
        case "users/addUsers":
          return addToIDMap(state, action.payload);
        case "users/updateNickname":
          if (state[action.payload[0]]) {
            return {
              ...state,
              [action.payload[0]]: {
                ...state[action.payload[0]],
                nickname: action.payload[1],
              },
            };
          } else {
            return state;
          }
        default:
          return state;
      }
    },
    conversations: (state = {}, action) => {
      switch (action.type) {
        case "conversations/addConversations":
          return addToIDMap(state, action.payload);
        case "conversations/invalidateConversation":
          const { [action.payload]: value, ...newState } = state;
          return newState;
        case "conversations/updateNotes":
          if (state[action.payload[0]]) {
            return {
              ...state,
              [action.payload[0]]: {
                ...state[action.payload[0]],
                notes: action.payload[1],
              },
            };
          } else {
            return state;
          }
        default:
          return state;
      }
    },
    stats: (state = null, action) =>
      action.type == "stats/setStats" ? action.payload : state,
    pageState: produce((draft, action) => {
      switch (action.type) {
        case "pageState/save":
          Object.assign(draft, action.payload);
          break;
        case "pageState/markScrollPosUsed":
          console.log("obviating scroll pos for key", action.payload);
          draft[action.payload].scrollTop = null;
        /*
        possible optimization: keep an ordered list of location keys and if a push is
        detected while we're not at the end of the list, discard the key objects at
        the end of the list. like so:
        case "pageState/setKeyList":
          draft._keyList = action.payload;
        case "pageState/discardKeys":
          for (const key of action.payload) {
            delete draft[key];
          }
          */
      }
    }, {}),
    autoplay: (state = true, action) => {
      if (action.type == "autoplay/allowed") {
        return action.payload;
      }
      return state;
    },
  },
});

ReactDOM.render(
  <Provider store={store}>
    <App />
  </Provider>,
  document.getElementById("root")
);

function App() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [needAuth, setNeedAuth] = useState(false);
  const [warning, setWarning] = useState("");
  const passwordField = useRef(null);

  useEffect(() => {
    if (!loggedIn) {
      fetch("/api/authenticate", { method: "POST", body: "" }).then(
        (response) => {
          if (response.status == 403) {
            setNeedAuth(true);
          } else if (response.status == 200) {
            setLoggedIn(true);
          }
        }
      );
    }
  }, []);

  const dispatch = useDispatch();
  const fetchStats = () => {
    if (loggedIn) {
      fetch("/api/globalstats").then((r) =>
        r.json().then((result) => {
          dispatch({
            type: "stats/setStats",
            payload: result,
          });
        })
      );
    }
  };
  useEffect(fetchStats, [loggedIn]);

  const centeredDiv = {
    position: "absolute",
    top: "50%",
    left: "50%",
    transform: "translate(-50%,-50%)",
  };

  if (loggedIn) {
    return <RoutingTable />;
  } else if (needAuth) {
    const attemptAuth = () => {
      fetch("/api/authenticate", {
        method: "POST",
        body: passwordField.current.value,
      }).then((resp) => {
        if (resp.status == 200) {
          setLoggedIn(true);
        } else if (resp.status == 403) {
          passwordField.current.value = "";
          setWarning("incorrect password");
        }
      });
    };
    return (
      <div
        style={{
          border: "1px solid black",
          borderRadius: 5,
          padding: 10,
          ...centeredDiv,
        }}
      >
        <h1>Enter password:</h1>
        <input
          onKeyDown={(e) => e.key == "Enter" && attemptAuth()}
          ref={passwordField}
          type="password"
        />
        <button onClick={attemptAuth}>Log in</button>
        {warning && <p>{warning}</p>}
      </div>
    );
  } else {
    return <LoadingSpinner style={centeredDiv} />;
  }
}

function TitledRoute(props) {
  const location = useLocation();
  useEffect(() => {
    if (titles[location.pathname]) {
      document.title = titles[location.pathname];
    }
  }, [location.pathname]);
  return <Route {...props} />;
}

function RoutingTable() {
  return (
    <Router>
      <Switch>
        <Route path="/404">
          <h1>404 :(</h1>
        </Route>
        <Route path="*">
          <div className="contentPane">
            <Switch>
              <TitledRoute exact path="/">
                <Redirect to="/conversations" />
              </TitledRoute>
              <TitledRoute path="/conversations">
                <ConversationList />
              </TitledRoute>
              <Route path="/conversation/info/:id">
                <ConversationInfo />
              </Route>
              <Route path="/user/info/:id">
                <UserInfo />
              </Route>
              <Route
                path={[
                  "/:type/messages/:id/:message_id?",
                  "/messages/:message_id?",
                ]}
                render={(routeProps) => {
                  const queries = new URLSearchParams(
                    routeProps.location.search
                  );
                  const props = {
                    search: queries.get("search"),
                    type: routeProps.match.params.type,
                    id: routeProps.match.params.id,
                    startingPlace:
                      queries.get("start") ||
                      (routeProps.match.params.message_id ? "" : "beginning"),
                    message_id: routeProps.match.params.message_id,
                  };
                  return <MessagePage key={Date.now()} {...props} />;
                }}
              ></Route>
              <TitledRoute path="/stats">
                <GlobalStats />
              </TitledRoute>
              <Route path="*">
                <Redirect to="/404" />
              </Route>
            </Switch>
          </div>
        </Route>
      </Switch>
    </Router>
  );
}
