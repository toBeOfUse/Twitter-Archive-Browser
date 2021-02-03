import React, { useEffect, useState, useRef } from "react";
import PropTypes from "prop-types";

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
  // these two are passed down to the top-level dom element
  className: PropTypes.string,
  id: PropTypes.string,
};

export default function ScrollyPane(props) {
  const contentPane = useRef(null);
  const [page, setPage] = useState(1);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

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
        el.scrollTop + el.offsetHeight > el.scrollHeight - 30) &&
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
