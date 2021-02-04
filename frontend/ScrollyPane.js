import React, { useEffect, useState, useRef } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import { useHistory, useLocation } from "react-router-dom";

ScrollyPane.propTypes = {
  // url that the ScrollyPane should make a request to when it needs to fetch more
  // items because of the user scrolling or because it is empty. as successive
  // requests are made, the page number (starting from 1) will simply be added to the
  // end of this url. requests to /api/whatever should therefore end with the query
  // parameter "?page=" and the correct value will be filled in
  url: PropTypes.string.isRequired,
  // function that will process the json-parsed response from url and will return an
  // array of objects that can be rendered in the pane; this array will be
  // concatenated with the existing array of objects, if that exists yet
  processItems: PropTypes.func.isRequired,
  // component type that will be rendered for each object fetched from url and
  // processed and returned by processItems, with the object unpacked so that each
  // key in it is a prop like <ItemShape {...item} />
  ItemShape: PropTypes.elementType.isRequired,
  // if this prop is passed, the pane's state is saved under the location key + "." +
  // this value in the pageState slice of the redux store and restored when this
  // location is revisited due to history navigation.
  saveHistoryState: PropTypes.string,
  // if this prop is passed, the pane's state is only restored from pageState if this
  // prop matches the currentKey saved in pageState. this is useful when a different
  // instance of the ScrollyPane is mounted depending on some state value in the
  // parent component; it means that a newly mounted instance of ScrollyPane will not
  // reload the state from the previous instance on that page, as long as
  // currentKey changes accordingly.
  currentKey: PropTypes.string,
  // these two are passed down to the top-level dom element
  className: PropTypes.string,
  id: PropTypes.string,
};

export default function ScrollyPane(props) {
  const contentPane = useRef(null);
  const historyListenerCleanup = useRef(null);
  const history = useHistory();
  const location = useLocation();
  const dispatch = useDispatch();

  const locationKey =
    props.saveHistoryState && location.key + "." + props.saveHistoryState;
  let savedState = useSelector((state) => {
    if (locationKey && state.pageState[locationKey]) {
      if (
        !props.currentKey ||
        state.pageState[locationKey].currentKey == props.currentKey
      ) {
        console.log("SP: reading page state from", locationKey);
        return state.pageState[locationKey];
      }
    } else {
      console.log("SP: did not find page state for", locationKey);
      return null;
    }
  });

  useEffect(() => {
    if (savedState && contentPane.current) {
      console.log("SP: restoring scroll position");
      contentPane.current.scrollTop = savedState.scrollTop;
    }
  }, [savedState, contentPane.current]);

  const [page, setPage] = useState(savedState?.page || 1);
  const [items, setItems] = useState(savedState?.items || []);
  const [loading, setLoading] = useState(false);

  if (props.saveHistoryState) {
    if (historyListenerCleanup.current) {
      historyListenerCleanup.current();
    }
    const saveState = (_newLocation, action) => {
      if (
        (action == "PUSH" || action == "POP") &&
        items.length &&
        contentPane.current
      ) {
        console.log("SP: saving state to", locationKey);
        console.log("SP: using sub-key", props.currentKey);
        dispatch({
          type: "pageState/save",
          payload: {
            [locationKey]: {
              items,
              page,
              scrollTop: contentPane.current.scrollTop,
              currentKey: props.currentKey,
            },
          },
        });
      }
      historyListenerCleanup.current();
    };
    historyListenerCleanup.current = history.listen(saveState);
  }

  let renderedItems;
  if (items.length) {
    renderedItems = items.map((item) => (
      <props.ItemShape key={item.id} {...item}></props.ItemShape>
    ));
  } else if (page != -1) {
    renderedItems = <p>loading...</p>;
  } else {
    renderedItems = <p>No items</p>;
  }

  const scrollCheck = () => {
    const el = contentPane.current;
    if (
      el &&
      (el.scrollHeight < el.parentElement.scrollHeight ||
        el.scrollTop + el.offsetHeight > el.scrollHeight - 100) &&
      page != -1 &&
      !loading
    ) {
      setLoading(true);

      fetch(props.url + page).then((r) =>
        r.json().then((j) => {
          const processedItems = props.processItems(j);
          setItems((oldItems) => oldItems.concat(processedItems));
          if (!processedItems.length) {
            setPage(-1);
          } else {
            setPage((prevPage) => (prevPage == -1 ? prevPage : prevPage + 1));
          }
          setLoading(false);
        })
      );
    }
  };

  useEffect(scrollCheck);

  return (
    <div
      className={props.className}
      id={props.id}
      onScroll={scrollCheck}
      ref={contentPane}
    >
      {renderedItems}
    </div>
  );
}
