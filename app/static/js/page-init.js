(function () {
  if (window.__APP_PAGE_INIT_LOADED__) {
    return;
  }
  window.__APP_PAGE_INIT_LOADED__ = true;

  const cleanups = [];

  window.appRegisterCleanup = function appRegisterCleanup(fn) {
    if (typeof fn === "function") {
      cleanups.push(fn);
    }
  };

  window.appRunCleanups = function appRunCleanups() {
    while (cleanups.length) {
      const cleanup = cleanups.pop();
      try {
        cleanup();
      } catch (error) {
        console.warn("Cleanup error", error);
      }
    }
  };

  function initCourseListPage(root) {
    const grid = root.querySelector("#cours-grid");
    if (!grid || grid.dataset.pageInitDone === "true") {
      return;
    }

    grid.dataset.pageInitDone = "true";
    root.querySelectorAll("[data-filter]").forEach((button) => {
      button.addEventListener("click", () => {
        root.querySelectorAll("[data-filter]").forEach((item) => item.classList.remove("active"));
        button.classList.add("active");
        const filter = button.dataset.filter;
        root.querySelectorAll(".cours-card").forEach((card) => {
          card.style.display = filter === "all" || card.dataset.niveau === filter ? "" : "none";
        });
      });
    });
  }

  function initLoginPage(root) {
    const form = root.querySelector("#login-form");
    const submitButton = root.querySelector("#login-submit");
    const statusBox = root.querySelector("#login-status");

    if (!form || !submitButton || !statusBox || form.dataset.pageInitDone === "true") {
      return;
    }

    form.dataset.pageInitDone = "true";

    let loginAudioContext = null;

    function ensureLoginAudioContext() {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) {
        return null;
      }

      if (!loginAudioContext) {
        loginAudioContext = new AudioContextClass();
      }

      if (loginAudioContext.state === "suspended") {
        loginAudioContext.resume().catch(() => {});
      }

      return loginAudioContext;
    }

    function playLoginSuccessSound() {
      const context = ensureLoginAudioContext();
      if (!context) {
        return Promise.resolve();
      }

      const now = context.currentTime;
      const notes = [523.25, 659.25, 783.99];

      notes.forEach((frequency, index) => {
        const oscillator = context.createOscillator();
        const gain = context.createGain();
        oscillator.type = "sine";
        oscillator.frequency.setValueAtTime(frequency, now);
        gain.gain.setValueAtTime(0.0001, now);
        gain.gain.exponentialRampToValueAtTime(0.16, now + 0.03 + index * 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.38 + index * 0.03);
        oscillator.connect(gain);
        gain.connect(context.destination);
        oscillator.start(now + index * 0.04);
        oscillator.stop(now + 0.45 + index * 0.03);
      });

      return new Promise((resolve) => {
        window.setTimeout(resolve, 520);
      });
    }

    function showError(message) {
      statusBox.textContent = message;
      statusBox.classList.remove("d-none");
    }

    function hideError() {
      statusBox.textContent = "";
      statusBox.classList.add("d-none");
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      hideError();
      ensureLoginAudioContext();

      const originalText = submitButton.textContent;
      submitButton.disabled = true;
      submitButton.textContent = "Connexion...";

      try {
        const response = await fetch(form.action, {
          method: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
          },
          body: new FormData(form),
          credentials: "same-origin",
        });

        const data = await response.json();
        if (!response.ok || !data.success) {
          showError(data.message || "Identifiant ou mot de passe incorrect.");
          submitButton.disabled = false;
          submitButton.textContent = originalText;
          return;
        }

        await playLoginSuccessSound();
        if (window.appSoftNavigate) {
          window.appSoftNavigate(data.redirect_url || "/dashboard", { replace: true });
        } else {
          window.location.href = data.redirect_url || "/dashboard";
        }
      } catch (error) {
        showError("Une erreur reseau est survenue. Reessayez.");
        submitButton.disabled = false;
        submitButton.textContent = originalText;
      }
    });
  }

  function initQuizQuestionFormPage(root) {
    const typeSelect = root.querySelector("#type_exercice");
    const choicesSection = root.querySelector("#choices-section");
    if (!typeSelect || !choicesSection || typeSelect.dataset.pageInitDone === "true") {
      return;
    }

    typeSelect.dataset.pageInitDone = "true";

    function syncQuestionType() {
      const isFreeResponse = ["dictee", "speaking"].includes(typeSelect.value);
      choicesSection.style.display = isFreeResponse ? "none" : "";
      choicesSection.querySelectorAll('input[type="text"]').forEach((input) => {
        input.required = !isFreeResponse;
      });
      choicesSection.querySelectorAll('input[type="checkbox"]').forEach((input) => {
        if (isFreeResponse) {
          input.checked = false;
        }
      });
    }

    typeSelect.addEventListener("change", syncQuestionType);
    syncQuestionType();
  }

  function initLessonDetailPage(root) {
    root.querySelectorAll("[data-video-embed-url]").forEach((shell) => {
      if (shell.dataset.videoInitDone === "true") {
        return;
      }

      const button = shell.querySelector(".lesson-video-launch");
      if (!button) {
        return;
      }

      shell.dataset.videoInitDone = "true";
      const embedUrl = shell.dataset.videoEmbedUrl;
      const videoAutoplayUrl = shell.dataset.videoAutoplayUrl || embedUrl;
      const videoTitle = shell.dataset.videoTitle || "Video";

      const loadVideo = (src) => {
        const iframeSrc = src || embedUrl;
        if (!iframeSrc || shell.dataset.videoLoaded === "true") {
          return;
        }

        shell.dataset.videoLoaded = "true";
        const iframe = document.createElement("iframe");
        iframe.src = iframeSrc;
        iframe.title = videoTitle;
        iframe.className = "rounded-3";
        iframe.loading = "lazy";
        iframe.referrerPolicy = "strict-origin-when-cross-origin";
        iframe.allow =
          "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
        iframe.allowFullscreen = true;
        shell.replaceChildren(iframe);
      };

      button.addEventListener("click", () => loadVideo(videoAutoplayUrl));
      button.addEventListener(
        "touchend",
        (event) => {
          event.preventDefault();
          loadVideo(videoAutoplayUrl);
        },
        { passive: false },
      );
    });

    const form = root.querySelector("#quizForm");
    const feedback = root.querySelector("#quizFeedback");
    if (!form || !feedback || form.dataset.pageInitDone === "true") {
      return;
    }

    form.dataset.pageInitDone = "true";

    function renderDetails(result) {
      const rows = result.details
        .map(
          (detail) => `
            <div class="result-card ${detail.est_correct ? "correct" : "incorrect"}">
              <div class="fw-semibold mb-1">${detail.texte_question}</div>
              <div class="small mb-1">Votre reponse : ${detail.choix_selectionne}</div>
              <div class="small">Bonne reponse : ${detail.texte_bonne_reponse}</div>
            </div>
          `,
        )
        .join("");

      feedback.innerHTML = `
        <div class="alert alert-info">Score : <strong>${result.score_percent}%</strong> (${result.nb_correct}/${result.nb_total})</div>
        <div class="d-grid gap-3">${rows}</div>
      `;
    }

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const formData = new FormData(form);

      fetch(form.action, {
        method: "POST",
        body: formData,
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
      })
        .then((response) => response.json().then((data) => ({ ok: response.ok, data })))
        .then(({ ok, data }) => {
          if (!ok) {
            feedback.innerHTML = `<div class="alert alert-danger">${data.error || "Une erreur est survenue."}</div>`;
            return;
          }
          form.remove();
          renderDetails(data);
        })
        .catch(() => {
          feedback.innerHTML = '<div class="alert alert-danger">Impossible de soumettre le quiz.</div>';
        });
    });
  }

  function initTeacherDashboardPage(root) {
    const container = root instanceof HTMLElement ? root : document.getElementById("app-main");
    if (!container || !container.querySelector("[data-eleve][data-lecon]") || container.dataset.teacherDashboardInit === "true") {
      return;
    }

    container.dataset.teacherDashboardInit = "true";

    const source = new EventSource("/progression/stream");
    source.onmessage = function (event) {
      try {
        const data = JSON.parse(event.data);
        if (!Array.isArray(data)) {
          return;
        }

        data.forEach((item) => {
          const row = container.querySelector(`[data-eleve="${item.eleve_id}"][data-lecon="${item.lecon_id}"]`);
          if (row) {
            const title = row.textContent.split(":")[0].trim();
            row.textContent = `${title} : ${item.score !== null && item.score !== undefined ? item.score + "%" : "-"}`;
            row.classList.add("updated");
            window.setTimeout(() => row.classList.remove("updated"), 2000);
          }
        });
      } catch (error) {
        console.log("SSE parse error", error);
      }
    };
    source.onerror = function () {
      source.close();
    };

    window.appRegisterCleanup(() => {
      source.close();
    });
  }

  function updateStudentXpUi(data) {
    const updates = [
      { selector: "#navbar-xp [data-xp-value]", value: data.points },
      { selector: "[data-xp-points]", value: data.points },
      { selector: "[data-xp-streak]", value: data.streak },
      { selector: "[data-xp-lessons]", value: data.total_lecons_terminees },
    ];

    updates.forEach(({ selector, value }) => {
      if (value === undefined || value === null) {
        return;
      }
      document.querySelectorAll(selector).forEach((node) => {
        node.textContent = String(value);
      });
    });
  }

  function initStudentProgressPage(root) {
    if (typeof window.EventSource !== "function") {
      return;
    }

    const container = root && typeof root.querySelector === "function" ? root : document;
    const marker = container.querySelector('[data-progress-stream="xp"]');
    if (!marker || marker.dataset.progressStreamInit === "true") {
      return;
    }

    marker.dataset.progressStreamInit = "true";

    const source = new EventSource("/progression/stream");
    source.onmessage = function (event) {
      try {
        const data = JSON.parse(event.data);
        if (!data || Array.isArray(data) || typeof data !== "object") {
          return;
        }
        updateStudentXpUi(data);
      } catch (error) {
        console.log("SSE XP parse error", error);
      }
    };
    source.onerror = function () {
      source.close();
    };

    window.appRegisterCleanup(() => {
      source.close();
    });
  }

  function escapeHtmlValue(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function notificationIconClass(type) {
    if (type === "lesson_published") {
      return "bi-book";
    }
    if (type === "exercise_corrected") {
      return "bi-check-circle";
    }
    if (type === "badge_unlocked") {
      return "bi-award";
    }
    return "bi-alarm";
  }

  function notificationActionLabel(type) {
    if (type === "exercise_corrected") {
      return "Voir le résultat";
    }
    if (type === "lesson_published") {
      return "Ouvrir la leçon";
    }
    if (type === "badge_unlocked") {
      return "Voir les badges";
    }
    return "Ouvrir";
  }

  function renderNotificationPreviewItems(items) {
    if (!Array.isArray(items) || items.length === 0) {
      return `
        <div class="nav-notification-empty" data-notification-empty-state="true">
          <i class="bi bi-bell-slash"></i>
          <span>Aucune notification</span>
        </div>
      `;
    }

    return items.map((item) => `
      <a href="${escapeHtmlValue(item.open_url || item.cta_url || "/notifications/inbox")}" class="nav-notification-item ${item.is_read ? "" : "is-unread"}">
        <span class="nav-notification-item__icon"><i class="bi ${notificationIconClass(item.type)}"></i></span>
        <span class="nav-notification-item__body">
          <span class="nav-notification-item__title">${escapeHtmlValue(item.title)}</span>
          <span class="nav-notification-item__message">${escapeHtmlValue(item.message)}</span>
          <span class="nav-notification-item__time">${escapeHtmlValue(item.relative_time || "")}</span>
        </span>
      </a>
    `).join("");
  }

  function renderNotificationInboxItems(items) {
    if (!Array.isArray(items) || items.length === 0) {
      return `
        <div class="notification-empty">
          <i class="bi bi-bell-slash fs-1 d-block mb-2 opacity-25"></i>
          Aucune notification pour le moment.
        </div>
      `;
    }

    return items.map((item) => `
      <article class="notification-card ${item.is_read ? "" : "is-unread"}" data-notification-card="${escapeHtmlValue(item.id)}">
        <div class="notification-card__header">
          <div class="notification-card__meta">
            <span class="notification-card__icon"><i class="bi ${notificationIconClass(item.type)}"></i></span>
            <div>
              <div class="fw-semibold">${escapeHtmlValue(item.title)}</div>
              <div class="small text-muted">${escapeHtmlValue(item.relative_time || "")}</div>
            </div>
          </div>
          ${item.is_read ? "" : '<span class="notification-unread-pill">Nouveau</span>'}
        </div>
        <div class="notification-card__body">
          <p class="mb-2">${escapeHtmlValue(item.message)}</p>
          <a href="${escapeHtmlValue(item.open_url || item.cta_url || "/notifications/inbox")}" class="btn btn-sm btn-outline-platform">
            ${escapeHtmlValue(notificationActionLabel(item.type))}
          </a>
        </div>
      </article>
    `).join("");
  }

  function updateNotificationCounters(unreadCount) {
    document.querySelectorAll("[data-notification-count]").forEach((node) => {
      node.textContent = String(unreadCount);
      node.classList.toggle("is-hidden", unreadCount <= 0);
    });

    document.querySelectorAll('[data-notification-count-label="true"]').forEach((node) => {
      node.textContent = String(unreadCount);
    });
  }

  function initNotificationCenter(root) {
    const container = root.querySelector?.("[data-notification-center='true']") || document.querySelector("[data-notification-center='true']");
    const inboxList = root.querySelector?.("[data-notification-inbox-list='true']") || document.querySelector("[data-notification-inbox-list='true']");
    if (!container || container.dataset.notificationInitDone === "true") {
      return;
    }

    container.dataset.notificationInitDone = "true";

    const previewList = container.querySelector("[data-notification-preview-list='true']");
    const readAllUrl = container.dataset.notificationReadAllUrl || "/notifications/read-all";
    const streamUrl = container.dataset.notificationStreamUrl || "/notifications/stream";
    const streamEnabled = container.dataset.notificationStream === "1";

    function applyNotificationPayload(payload) {
      const unreadCount = Number(payload?.unread_count || 0);
      updateNotificationCounters(unreadCount);
      if (previewList) {
        previewList.innerHTML = renderNotificationPreviewItems(payload?.items || []);
      }
      if (inboxList) {
        inboxList.innerHTML = renderNotificationInboxItems(payload?.items || []);
      }
    }

    const markAllButtons = document.querySelectorAll("[data-mark-all-notifications='true']");
    markAllButtons.forEach((button) => {
      if (button.dataset.notificationBound === "true") {
        return;
      }
      button.dataset.notificationBound = "true";
      button.addEventListener("click", async () => {
        try {
          const response = await fetch(readAllUrl, {
            method: "POST",
            headers: {
              "X-CSRFToken": window.APP_CSRF_TOKEN || "",
            },
            credentials: "same-origin",
          });
          const data = await response.json();
          if (!response.ok || !data.success) {
            return;
          }
          updateNotificationCounters(data.unread_count || 0);
          document.querySelectorAll(".notification-card, .nav-notification-item").forEach((node) => {
            node.classList.remove("is-unread");
          });
          document.querySelectorAll(".notification-unread-pill").forEach((pill) => pill.remove());
        } catch (_) {
          // Ignore network errors and keep the existing UI state.
        }
      });
    });

    document.querySelectorAll("[data-enable-push-notifications='true']").forEach((button) => {
      if (button.dataset.pushPromptBound === "true") {
        return;
      }
      button.dataset.pushPromptBound = "true";
      button.addEventListener("click", async () => {
        if (typeof window.proposerNotifications !== "function") {
          return;
        }
        const originalLabel = button.innerHTML;
        button.disabled = true;
        try {
          const subscription = await window.proposerNotifications();
          if (subscription) {
            button.innerHTML = '<i class="bi bi-check2-circle me-2"></i>Push activé';
          } else {
            button.innerHTML = originalLabel;
          }
        } catch (_) {
          button.innerHTML = originalLabel;
        } finally {
          button.disabled = false;
        }
      });
    });

    if (!streamEnabled || typeof window.EventSource !== "function") {
      return;
    }

    const source = new EventSource(streamUrl);
    source.onmessage = function (event) {
      try {
        const data = JSON.parse(event.data);
        if (!data || typeof data !== "object") {
          return;
        }
        applyNotificationPayload(data);
      } catch (error) {
        console.log("Notification SSE parse error", error);
      }
    };
    source.onerror = function () {
      source.close();
    };

    window.appRegisterCleanup(() => {
      source.close();
    });
  }

  function initVocabAdminPage(root) {
    const filterForm = root.querySelector("#vocab-filter-form");
    if (!filterForm || filterForm.dataset.jsBound === "true") {
      return;
    }

    filterForm.dataset.jsBound = "true";

    const delay = Number(filterForm.dataset.autoSubmitDelay || 260);
    const searchInput = filterForm.querySelector('[data-auto-submit-input="true"]');
    const selectFields = filterForm.querySelectorAll('[data-auto-submit-select="true"]');
    const submitButton = filterForm.querySelector('[data-submit-button="true"]');
    const submitLabel = filterForm.querySelector('[data-submit-label="true"]');
    const submitIcon = filterForm.querySelector('[data-submit-icon="true"]');
    const resetLink = filterForm.querySelector('[data-vocab-reset-link="true"]');
    const adminPanel = root.querySelector(".vocab-admin-panel");
    let debounceTimer = null;
    let activeRequest = null;

    const getNavbarOffset = () => {
      const navbar = document.querySelector(".navbar-platform");
      return (navbar ? navbar.offsetHeight : 72) + 16;
    };

    const scrollToHashTarget = (hash) => {
      if (!hash) {
        return;
      }
      const target = document.querySelector(hash);
      if (!target) {
        return;
      }
      const top = target.getBoundingClientRect().top + window.scrollY - getNavbarOffset();
      window.scrollTo({ top: Math.max(top, 0), behavior: "auto" });
    };

    const setSubmittingState = (value) => {
      filterForm.classList.toggle("is-submitting", value);
      if (adminPanel) {
        adminPanel.classList.toggle("is-updating", value);
      }
      if (submitButton) {
        submitButton.disabled = value;
      }
      if (submitLabel) {
        submitLabel.textContent = value ? "Recherche..." : "Rechercher";
      }
      if (submitIcon) {
        submitIcon.classList.toggle("bi-search", !value);
        submitIcon.classList.toggle("bi-arrow-repeat", value);
        submitIcon.classList.toggle("spin", value);
      }
    };

    const syncFormFromUrl = (targetUrl) => {
      const params = targetUrl.searchParams;
      const qValue = params.get("q") || "";
      const niveauValue = (params.get("niveau") || "").toUpperCase();
      let pedagogiqueValue = params.get("pedagogique") || "";
      let traduitsValue = params.get("traduits") || "";

      if (!qValue && !niveauValue) {
        if (!params.has("pedagogique")) {
          pedagogiqueValue = "1";
        }
        if (!params.has("traduits")) {
          traduitsValue = "1";
        }
      }

      if (searchInput) {
        searchInput.value = qValue;
      }
      const niveauField = filterForm.querySelector('select[name="niveau"]');
      const pedagogiqueField = filterForm.querySelector('select[name="pedagogique"]');
      const traduitsField = filterForm.querySelector('select[name="traduits"]');
      if (niveauField) {
        niveauField.value = niveauValue;
      }
      if (pedagogiqueField) {
        pedagogiqueField.value = pedagogiqueValue;
      }
      if (traduitsField) {
        traduitsField.value = traduitsValue;
      }
    };

    const replaceResultsRegion = async (nextUrl, options = {}) => {
      const targetUrl = new URL(nextUrl, window.location.origin);
      targetUrl.hash = "";

      if (activeRequest) {
        activeRequest.abort();
      }

      const controller = new AbortController();
      activeRequest = controller;
      setSubmittingState(true);

      try {
        const response = await fetch(targetUrl.toString(), {
          headers: {
            "X-Requested-With": "XMLHttpRequest",
          },
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error("Fragment request failed");
        }

        const html = await response.text();
        const wrapper = document.createElement("div");
        wrapper.innerHTML = html.trim();
        const incomingRegion = wrapper.querySelector('[data-vocab-results-region="true"]');
        const currentRegion = document.querySelector('[data-vocab-results-region="true"]');

        if (!incomingRegion || !currentRegion) {
          window.location.href = nextUrl;
          return;
        }

        currentRegion.replaceWith(incomingRegion);
        syncFormFromUrl(targetUrl);

        if (options.pushState) {
          window.history.pushState({ vocabAjax: true }, "", nextUrl);
        } else {
          window.history.replaceState({ vocabAjax: true }, "", nextUrl);
        }

        if (options.hash) {
          scrollToHashTarget(options.hash);
        }
      } catch (error) {
        if (error.name !== "AbortError") {
          window.location.href = nextUrl;
        }
      } finally {
        if (activeRequest === controller) {
          activeRequest = null;
          setSubmittingState(false);
        }
      }
    };

    const submitFilters = () => {
      const nextUrl = new URL(filterForm.action, window.location.origin);
      const formData = new FormData(filterForm);
      nextUrl.search = "";
      for (const [key, value] of formData.entries()) {
        if (value) {
          nextUrl.searchParams.set(key, value);
        }
      }
      replaceResultsRegion(nextUrl.toString() + "#vocab-results");
    };

    selectFields.forEach((field) => {
      field.addEventListener("change", (event) => {
        event.preventDefault();
        submitFilters();
      });
    });

    if (searchInput) {
      searchInput.addEventListener("input", () => {
        window.clearTimeout(debounceTimer);
        debounceTimer = window.setTimeout(submitFilters, delay);
      });
    }

    filterForm.addEventListener("submit", (event) => {
      event.preventDefault();
      window.clearTimeout(debounceTimer);
      submitFilters();
    });

    if (resetLink) {
      resetLink.addEventListener("click", (event) => {
        event.preventDefault();
        window.clearTimeout(debounceTimer);
        replaceResultsRegion(resetLink.href + "#vocab-results");
      });
    }

    const paginationHandler = (event) => {
      const link = event.target.closest("#vocab-results-region .vocab-pagination-bar a");
      if (!link) {
        return;
      }
      event.preventDefault();
      replaceResultsRegion(link.href, {
        pushState: true,
        hash: new URL(link.href, window.location.origin).hash,
      });
    };

    document.addEventListener("click", paginationHandler);

    const popstateHandler = () => {
      if (!window.location.pathname.includes("/admin/vocabulaire")) {
        return;
      }
      replaceResultsRegion(window.location.href, {
        pushState: false,
        hash: window.location.hash,
      });
    };

    window.addEventListener("popstate", popstateHandler);
    syncFormFromUrl(new URL(window.location.href));

    window.appRegisterCleanup(() => {
      document.removeEventListener("click", paginationHandler);
      window.removeEventListener("popstate", popstateHandler);
      if (activeRequest) {
        activeRequest.abort();
      }
      window.clearTimeout(debounceTimer);
    });
  }

  window.appRunPageInitializers = function appRunPageInitializers(root = document) {
    initCourseListPage(root);
    initLoginPage(root);
    initQuizQuestionFormPage(root);
    initLessonDetailPage(root);
    initStudentProgressPage(root);
    initTeacherDashboardPage(root);
    initNotificationCenter(root);
    initVocabAdminPage(root);
  };
})();
