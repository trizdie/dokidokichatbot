/**
 * adapter.js — Bridges the frontend to the Python backend.
 *
 * This file intercepts fetch calls to the RapidAPI ChatGPT host
 * and re-routes them to our local Flask /api/chat endpoint.
 */
(function () {
  const API_HOST = "chatgpt53.p.rapidapi.com";
  const LOCAL_ENDPOINT = "/api/chat";

  const _originalFetch = window.fetch;

  window.fetch = function (url, init) {
    if (
      typeof url === "string" &&
      url.includes(API_HOST) &&
      init &&
      init.method === "POST"
    ) {
      let body;
      try {
        body = JSON.parse(init.body);
      } catch (_) {
        body = {};
      }

      return _originalFetch(LOCAL_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: body.messages || [{ role: "user", content: "" }],
        }),
      });
    }

    return _originalFetch.apply(this, arguments);
  };
})();
