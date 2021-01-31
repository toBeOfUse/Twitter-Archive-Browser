import "normalize.css";
import "./assets/css/index.css";
import React from "react";
import ReactDOM from "react-dom";
import {
  BrowserRouter as Router,
  NavLink,
  Switch,
  Route,
  Redirect,
} from "react-router-dom";
import { configureStore } from "@reduxjs/toolkit";
import { Provider } from "react-redux";
import produce from "immer";
import { ConversationList, ConversationInfo } from "./ConversationComps";
import { UserInfo } from "./UserComps";
import { GlobalStats } from "./GlobalStats";
import { MessagePage } from "./MessageComps";

const addToIDMap = (IDMap, items) => {
  return Object.assign({}, IDMap, ...items.map((i) => ({ [i.id]: i })));
};

const store = configureStore({
  reducer: {
    users: (state = {}, action) =>
      action.type == "users/addUsers"
        ? addToIDMap(state, action.payload)
        : state,
    conversations: (state = {}, action) =>
      action.type == "conversations/addConversations"
        ? addToIDMap(state, action.payload)
        : state,
    stats: (state = null, action) =>
      action.type == "stats/setStats" ? action.payload : state,
    pageState: produce((draft, action) => {
      switch (action.type) {
        case "pageState/save":
          Object.assign(draft, action.payload);
          break;
        case "pageState/markScrollPosUsed":
          console.log("obviating scroll top for key", action.payload);
          draft[action.payload].scrollTop = null;
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

fetch("/api/globalstats").then((r) =>
  r.json().then((result) => {
    store.dispatch({
      type: "stats/setStats",
      payload: result,
    });
  })
);

ReactDOM.render(
  <Provider store={store}>
    <RoutingTable />
  </Provider>,
  document.getElementById("root")
);

function RoutingTable() {
  return (
    <Router>
      <Switch>
        <Route path="/404">
          <h1>404 :(</h1>
        </Route>
        <Route path="*">
          <div className="leftPane">
            <NavLink
              to="/conversations"
              className="bigLink"
              activeClassName="activeBigLink"
            >
              Home
            </NavLink>
          </div>
          <div className="contentPane">
            <Switch>
              <Route exact path="/">
                <Redirect to="/conversations" />
              </Route>
              <Route path="/conversations">
                <ConversationList />
              </Route>
              <Route path="/conversation/info/:id">
                <ConversationInfo />
              </Route>
              <Route path="/user/info/:id">
                <UserInfo />
              </Route>
              <Route
                path={["/:type/messages/:id", "/messages"]}
                render={(routeProps) => {
                  const queries = new URLSearchParams(
                    routeProps.location.search
                  );
                  const props = {
                    search: queries.get("search"),
                    type: routeProps.match.params.type,
                    id: routeProps.match.params.id,
                    startingPlace: queries.get("start") || "beginning",
                  };
                  return <MessagePage key={Date.now()} {...props} />;
                }}
              ></Route>
              <Route path="/stats">
                <GlobalStats />
              </Route>
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
