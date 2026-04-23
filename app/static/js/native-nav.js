(function () {
  if (window.__APP_NATIVE_NAV_LOADED__) {
    return;
  }
  window.__APP_NATIVE_NAV_LOADED__ = true;
  const prefetchedDocs = new Map();
  const prefetchRequests = new Map();
  const MAX_PREFETCHED_PAGES = 12;

  function getCurrentAuthFingerprint(doc = document) {
    return doc.querySelector('meta[name="app-auth-fingerprint"]')?.getAttribute("content") || "anonymous";
  }

  function sameOriginUrl(href) {
    try {
      return new URL(href, window.location.href);
    } catch (_) {
      return null;
    }
  }

  function closestLinkFromEventTarget(target) {
    return target instanceof Element ? target.closest("a") : null;
  }

  function emitNavigationEvent(name) {
    window.dispatchEvent(new CustomEvent(name));
  }

  function runViewTransition(callback) {
    if (!document.startViewTransition) {
      callback();
      return;
    }

    const transition = document.startViewTransition(callback);
    transition.ready?.catch((error) => {
      if (error?.name !== "AbortError") {
        console.warn("View transition failed", error);
      }
    });
    transition.finished?.catch((error) => {
      if (error?.name !== "AbortError") {
        console.warn("View transition failed", error);
      }
    });
  }

  function isSoftNavigationBlocked(url) {
    if (!url) {
      return true;
    }

    const blockedExactPaths = new Set([
      "/auth/google/start",
      "/logout",
      "/sw.js",
      "/service-worker.js",
    ]);

    return blockedExactPaths.has(url.pathname);
  }

  function isPrefetchBlocked(url) {
    if (isSoftNavigationBlocked(url)) {
      return true;
    }

    return url.pathname.startsWith("/langue/");
  }

  function isSoftLink(link) {
    if (!link || link.target === "_blank" || link.hasAttribute("download") || link.dataset.nativeNav === "false") {
      return false;
    }

    if (link.closest(".instant-nav-zone") || link.dataset.instantNav === "true") {
      return false;
    }

    const href = link.getAttribute("href");
    if (!href || href.startsWith("#") || href.startsWith("javascript:")) {
      return false;
    }

    const url = sameOriginUrl(link.href);
    if (!url || url.origin !== window.location.origin) {
      return false;
    }

    if (isSoftNavigationBlocked(url)) {
      return false;
    }

    if (url.pathname === window.location.pathname && url.search === window.location.search && url.hash) {
      return false;
    }

    return true;
  }

  function isSoftGetForm(form) {
    if (!(form instanceof HTMLFormElement)) {
      return false;
    }

    const method = (form.method || "get").toLowerCase();
    if (method !== "get") {
      return false;
    }

    if (form.closest(".instant-nav-zone") || form.dataset.instantNav === "true" || form.dataset.nativeNav === "false") {
      return false;
    }

    const actionUrl = sameOriginUrl(form.action || window.location.href);
    if (!actionUrl || actionUrl.origin !== window.location.origin) {
      return false;
    }

    return true;
  }

  function isSoftPostForm(form) {
    if (!(form instanceof HTMLFormElement)) {
      return false;
    }

    const method = (form.method || "get").toLowerCase();
    if (method !== "post") {
      return false;
    }

    if (
      form.dataset.nativeNav === "false" ||
      form.dataset.instantNav === "true" ||
      form.closest(".instant-nav-zone") ||
      form.target === "_blank"
    ) {
      return false;
    }

    const actionUrl = sameOriginUrl(form.action || window.location.href);
    if (!actionUrl || actionUrl.origin !== window.location.origin) {
      return false;
    }

    if (actionUrl.pathname.endsWith("/complete")) {
      return false;
    }

    return true;
  }

  function trimPrefetchCache() {
    while (prefetchedDocs.size > MAX_PREFETCHED_PAGES) {
      const oldestKey = prefetchedDocs.keys().next().value;
      prefetchedDocs.delete(oldestKey);
    }
  }

  function cacheDocument(url, payload) {
    if (!url || !payload) {
      return;
    }
    prefetchedDocs.set(url.toString(), payload);
    trimPrefetchCache();
  }

  function collectHeadNodes(doc) {
    const start = doc.head.querySelector('meta[data-app-head-boundary="start"]');
    const end = doc.head.querySelector('meta[data-app-head-boundary="end"]');
    const nodes = [];

    if (!start || !end) {
      return nodes;
    }

    let current = start.nextSibling;
    while (current && current !== end) {
      const next = current.nextSibling;
      nodes.push(current);
      current = next;
    }
    return nodes;
  }

  function replaceHeadNodes(nextDoc) {
    const currentStart = document.head.querySelector('meta[data-app-head-boundary="start"]');
    const currentEnd = document.head.querySelector('meta[data-app-head-boundary="end"]');
    const nextStart = nextDoc.head.querySelector('meta[data-app-head-boundary="start"]');
    const nextEnd = nextDoc.head.querySelector('meta[data-app-head-boundary="end"]');

    if (!currentStart || !currentEnd || !nextStart || !nextEnd) {
      return;
    }

    let current = currentStart.nextSibling;
    while (current && current !== currentEnd) {
      const next = current.nextSibling;
      current.remove();
      current = next;
    }

    collectHeadNodes(nextDoc).forEach((node) => {
      currentEnd.parentNode.insertBefore(node.cloneNode(true), currentEnd);
    });
  }

  function replaceById(nextDoc, id) {
    const currentNode = document.getElementById(id);
    const nextNode = nextDoc.getElementById(id);
    if (!currentNode || !nextNode) {
      return false;
    }
    currentNode.replaceWith(nextNode.cloneNode(true));
    return true;
  }

  function updateScrollForUrl(url) {
    const hash = url.hash;
    if (hash) {
      const target = document.querySelector(hash);
      if (target) {
        const navbar = document.querySelector(".navbar-platform");
        const offset = (navbar ? navbar.offsetHeight : 72) + 16;
        const top = target.getBoundingClientRect().top + window.scrollY - offset;
        window.scrollTo({ top: Math.max(top, 0), behavior: "auto" });
        return;
      }
    }
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  function replaceShell(nextDoc) {
    const requiredIds = ["app-navbar", "app-flash-stack", "app-main"];
    const missing = requiredIds.some((id) => !nextDoc.getElementById(id));
    if (missing) {
      return false;
    }

    window.appRunCleanups?.();
    replaceHeadNodes(nextDoc);
    replaceById(nextDoc, "app-navbar");
    replaceById(nextDoc, "app-flash-stack");
    replaceById(nextDoc, "app-main");
    document.title = nextDoc.title;
    window.initDictionnaire?.();
    window.appRunPageInitializers?.(document.getElementById("app-main") || document);
    return true;
  }

  async function fetchDocument(url, options = {}) {
    const cacheKey = url.toString();
    const currentFingerprint = getCurrentAuthFingerprint();
    if (options.preferCache !== false && prefetchedDocs.has(cacheKey)) {
      const cachedPayload = prefetchedDocs.get(cacheKey);
      if (cachedPayload && cachedPayload.authFingerprint === currentFingerprint) {
        return cachedPayload;
      }
      prefetchedDocs.delete(cacheKey);
    }

    const response = await fetch(cacheKey, {
      headers: {
        Accept: "text/html,application/xhtml+xml",
        "X-App-Navigation": "shell",
      },
      credentials: "same-origin",
    });

    if (!response.ok) {
      throw new Error(`Navigation failed: ${response.status}`);
    }

    const html = await response.text();
    const parser = new DOMParser();
    const nextDoc = parser.parseFromString(html, "text/html");
    const payload = {
      nextDoc,
      response,
      finalUrl: sameOriginUrl(response.url) || url,
      authFingerprint: getCurrentAuthFingerprint(nextDoc),
    };

    cacheDocument(url, payload);
    if (payload.finalUrl.toString() !== cacheKey) {
      cacheDocument(payload.finalUrl, payload);
    }

    return payload;
  }

  function prefetchUrl(url) {
    if (!url || isPrefetchBlocked(url)) {
      return;
    }

    const cacheKey = url.toString();
    if (prefetchedDocs.has(cacheKey) || prefetchRequests.has(cacheKey)) {
      return;
    }

    const request = fetchDocument(url, { preferCache: false })
      .catch(() => {})
      .finally(() => {
        prefetchRequests.delete(cacheKey);
      });

    prefetchRequests.set(cacheKey, request);
  }

  async function performSoftNavigation(url, historyMode) {
    const parsedUrl = sameOriginUrl(url);
    if (!parsedUrl) {
      window.location.href = url;
      return;
    }

    emitNavigationEvent("app:navigation-start");
    document.body.classList.add("app-is-navigating");

    try {
      const { nextDoc, finalUrl } = await fetchDocument(parsedUrl);

      const applyReplace = () => {
        const replaced = replaceShell(nextDoc);
        if (!replaced) {
          emitNavigationEvent("app:navigation-stop");
          window.location.href = finalUrl.toString();
          return;
        }

        prefetchedDocs.clear();

        if (historyMode === "push") {
          window.history.pushState({ nativeNav: true }, "", finalUrl.toString());
        } else if (historyMode === "replace") {
          window.history.replaceState({ nativeNav: true }, "", finalUrl.toString());
        }

        updateScrollForUrl(finalUrl);
        document.body.classList.remove("app-is-navigating");
        emitNavigationEvent("app:navigation-stop");
      };

      runViewTransition(applyReplace);
    } catch (error) {
      document.body.classList.remove("app-is-navigating");
      emitNavigationEvent("app:navigation-stop");
      window.location.href = parsedUrl.toString();
    }
  }

  window.appSoftNavigate = function appSoftNavigate(url, options = {}) {
    const historyMode = options.replace ? "replace" : "push";
    return performSoftNavigation(url, historyMode);
  };

  function submitFormClassically(form, submitter) {
    form.dataset.nativeSubmitting = "true";
    if (submitter && typeof form.requestSubmit === "function") {
      form.requestSubmit(submitter);
    } else {
      form.submit();
    }
  }

  async function performSoftFormNavigation(form, submitter) {
    const actionUrl = sameOriginUrl(form.action || window.location.href);
    if (!actionUrl) {
      submitFormClassically(form, submitter);
      return;
    }

    const formData = new FormData(form);
    if (submitter && submitter.name) {
      formData.append(submitter.name, submitter.value);
    }

    emitNavigationEvent("app:navigation-start");
    document.body.classList.add("app-is-navigating");

    try {
      const response = await fetch(actionUrl.toString(), {
        method: "POST",
        body: formData,
        headers: {
          Accept: "text/html,application/xhtml+xml",
          "X-App-Navigation": "shell",
        },
        credentials: "same-origin",
      });

      const contentType = response.headers.get("content-type") || "";
      if (!contentType.includes("text/html")) {
        document.body.classList.remove("app-is-navigating");
        emitNavigationEvent("app:navigation-stop");
        submitFormClassically(form, submitter);
        return;
      }

      const html = await response.text();
      const parser = new DOMParser();
      const nextDoc = parser.parseFromString(html, "text/html");
      const finalUrl = sameOriginUrl(response.url) || actionUrl;

      const applyReplace = () => {
        const replaced = replaceShell(nextDoc);
        if (!replaced) {
          document.body.classList.remove("app-is-navigating");
          emitNavigationEvent("app:navigation-stop");
          submitFormClassically(form, submitter);
          return;
        }

        if (finalUrl.toString() === window.location.href) {
          window.history.replaceState({ nativeNav: true }, "", finalUrl.toString());
        } else {
          window.history.pushState({ nativeNav: true }, "", finalUrl.toString());
        }

        updateScrollForUrl(finalUrl);
        document.body.classList.remove("app-is-navigating");
        emitNavigationEvent("app:navigation-stop");
      };

      runViewTransition(applyReplace);
    } catch (error) {
      document.body.classList.remove("app-is-navigating");
      emitNavigationEvent("app:navigation-stop");
      submitFormClassically(form, submitter);
    }
  }

  document.addEventListener("click", (event) => {
    const link = closestLinkFromEventTarget(event.target);
    if (!isSoftLink(link)) {
      return;
    }

    event.preventDefault();
    window.appSoftNavigate(link.href);
  });

  document.addEventListener("mouseenter", (event) => {
    const link = closestLinkFromEventTarget(event.target);
    if (!isSoftLink(link)) {
      return;
    }
    prefetchUrl(sameOriginUrl(link.href));
  }, true);

  document.addEventListener("focusin", (event) => {
    const link = closestLinkFromEventTarget(event.target);
    if (!isSoftLink(link)) {
      return;
    }
    prefetchUrl(sameOriginUrl(link.href));
  });

  document.addEventListener("touchstart", (event) => {
    const link = closestLinkFromEventTarget(event.target);
    if (!isSoftLink(link)) {
      return;
    }
    prefetchUrl(sameOriginUrl(link.href));
  }, { passive: true });

  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (form.dataset.nativeSubmitting === "true") {
      delete form.dataset.nativeSubmitting;
      return;
    }
    if (event.defaultPrevented || !isSoftGetForm(form)) {
      return;
    }

    event.preventDefault();
    const actionUrl = sameOriginUrl(form.action || window.location.href);
    const params = new URLSearchParams();
    const formData = new FormData(form);
    for (const [key, value] of formData.entries()) {
      if (typeof value === "string" && value !== "") {
        params.append(key, value);
      }
    }
    actionUrl.search = params.toString();
    window.appSoftNavigate(actionUrl.toString());
  });

  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) {
      return;
    }

    if (form.dataset.nativeSubmitting === "true") {
      delete form.dataset.nativeSubmitting;
      return;
    }

    if (event.defaultPrevented || !isSoftPostForm(form)) {
      return;
    }

    event.preventDefault();
    performSoftFormNavigation(form, event.submitter || null);
  });

  window.addEventListener("popstate", () => {
    if (document.getElementById("vocab-filter-form")) {
      return;
    }
    window.appSoftNavigate(window.location.href, { replace: true });
  });
})();
