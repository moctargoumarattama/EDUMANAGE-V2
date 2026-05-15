(function () {
  const NETWORK_BANNER_ID = "network-status-banner";
  const SW_MIGRATION_KEY = "app-sw-migration-v1";
  let onlineBannerTimeout = null;

  function getCookie(name) {
    const value = document.cookie.match(`(^|;) ?${name}=([^;]*)(;|$)`);
    return value ? value[2] : null;
  }

  function ensureNetworkBanner() {
    let banner = document.getElementById(NETWORK_BANNER_ID);
    if (banner) {
      return banner;
    }

    banner = document.createElement("div");
    banner.id = NETWORK_BANNER_ID;
    banner.className = "network-status-banner";
    banner.setAttribute("role", "status");
    banner.setAttribute("aria-live", "polite");
    document.body.appendChild(banner);
    return banner;
  }

  function hideNetworkBanner() {
    const banner = document.getElementById(NETWORK_BANNER_ID);
    if (!banner) {
      return;
    }
    banner.classList.remove("is-visible");
  }

  function showNetworkBanner(status) {
    const banner = ensureNetworkBanner();

    if (onlineBannerTimeout) {
      window.clearTimeout(onlineBannerTimeout);
      onlineBannerTimeout = null;
    }

    if (status === "offline") {
      banner.dataset.status = "offline";
      banner.innerHTML = "<span class=\"network-status-banner__icon\">●</span><span>Connexion perdue. Certaines pages resteront disponibles hors ligne.</span>";
      banner.classList.add("is-visible");
      document.body.classList.add("is-offline");
      return;
    }

    document.body.classList.remove("is-offline");
    banner.dataset.status = "online";
    banner.innerHTML = "<span class=\"network-status-banner__icon\">●</span><span>Connexion rétablie. Les données en direct sont de nouveau disponibles.</span>";
    banner.classList.add("is-visible");
    onlineBannerTimeout = window.setTimeout(() => {
      hideNetworkBanner();
    }, 2600);
  }

  function initNetworkBanner() {
    ensureNetworkBanner();

    if (!window.navigator.onLine) {
      showNetworkBanner("offline");
    }

    window.addEventListener("offline", () => showNetworkBanner("offline"));
    window.addEventListener("online", () => showNetworkBanner("online"));
  }

  function getCsrfToken() {
    return window.APP_CSRF_TOKEN
      || document.querySelector('meta[name="csrf-token"]')?.getAttribute("content")
      || getCookie("csrf_token");
  }

  function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; i += 1) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  async function registerArabicPWA() {
    if (!("serviceWorker" in navigator)) {
      return null;
    }

    try {
      await migrateLegacyServiceWorkersOnce();
      const swVersion = window.APP_ASSET_VERSION || "dev";
      const registration = await navigator.serviceWorker.register(
        `/sw.js?v=${encodeURIComponent(swVersion)}`,
        { updateViaCache: "none" }
      );

      try {
        await registration.update();
      } catch (_) {
        // Keep registration resilient even if update probing fails.
      }

      if (registration.waiting) {
        registration.waiting.postMessage({ type: "SKIP_WAITING" });
      }

      registration.addEventListener("updatefound", () => {
        const installingWorker = registration.installing;
        if (!installingWorker) {
          return;
        }
        installingWorker.addEventListener("statechange", () => {
          if (installingWorker.state === "installed" && navigator.serviceWorker.controller) {
            installingWorker.postMessage({ type: "SKIP_WAITING" });
          }
        });
      });

      return registration;
    } catch (error) {
      console.log("SW error", error);
      return null;
    }
  }

  async function migrateLegacyServiceWorkersOnce() {
    let migrationAlreadyDone = false;
    try {
      migrationAlreadyDone = window.localStorage.getItem(SW_MIGRATION_KEY) === "done";
    } catch (_) {
      migrationAlreadyDone = false;
    }

    if (migrationAlreadyDone) {
      return;
    }

    const registrations = await navigator.serviceWorker.getRegistrations();
    await Promise.all(registrations.map(async (registration) => {
      const scriptUrl = registration.active?.scriptURL
        || registration.waiting?.scriptURL
        || registration.installing?.scriptURL
        || "";
      if (scriptUrl.includes("/service-worker.js") || scriptUrl.includes("/static/service-worker.js")) {
        await registration.unregister();
      }
    }));

    try {
      window.localStorage.setItem(SW_MIGRATION_KEY, "done");
    } catch (_) {
      // Ignore storage failures and keep the migration best-effort.
    }
  }

  async function demanderNotifications() {
    if (!("PushManager" in window) || !("serviceWorker" in navigator) || !window.isSecureContext) {
      return null;
    }

    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
      return null;
    }

    const registration = await navigator.serviceWorker.ready;
    const response = await fetch("/notifications/vapid-public-key");
    const data = await response.json();
    if (!data.publicKey) {
      return null;
    }

    let subscription = await registration.pushManager.getSubscription();
    if (!subscription) {
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(data.publicKey)
      });
    }

    await fetch("/notifications/subscribe", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken()
      },
      body: JSON.stringify(subscription.toJSON ? subscription.toJSON() : subscription)
    });

    return subscription;
  }

  window.getCookie = getCookie;
  window.proposerNotifications = demanderNotifications;
  window.registerArabicPWA = registerArabicPWA;
  window.initNetworkBanner = initNetworkBanner;

  document.addEventListener("DOMContentLoaded", () => {
    initNetworkBanner();
    registerArabicPWA().then((registration) => {
      if (registration) {
        console.log("SW registered");
      }
    });
  });
}());
