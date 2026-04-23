let currentIndex = 0;
let score = 0;
let xpGagne = 0;
const resultats = [];
let selectedChoix = null;
let completionResponse = null;

function t(key, fallback) {
  return (window.LESSON_I18N && window.LESSON_I18N[key]) || fallback;
}

function init() {
  if (!Array.isArray(QUESTIONS) || QUESTIONS.length === 0) {
    afficherFinLecon();
    return;
  }
  afficherQuestion(0);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function resolveMediaUrl(url) {
  if (!url) {
    return "";
  }
  if (/^(https?:|data:|blob:|\/)/i.test(url)) {
    return url;
  }
  return `/static/${String(url).replace(/^\/+/, "")}`;
}

function melanger(array) {
  const copie = [...array];
  for (let i = copie.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copie[i], copie[j]] = [copie[j], copie[i]];
  }
  return copie;
}

function hintForQuestionType(typeExercice) {
  if (typeExercice === "ecoute") {
    return t("listenHint", "Écoutez, puis choisissez la bonne réponse.");
  }
  if (typeExercice === "ordre_mots") {
    return t("orderHint", "Glissez ou touchez les mots pour reformer la phrase.");
  }
  if (typeExercice === "dictee") {
    return t("dictationHint", "Écoutez, écrivez, puis validez.");
  }
  return t("tapHint", "Touchez la bonne carte pour continuer.");
}

function renderQuestionCard(label, q, body) {
  return `
    <div class="question-card">
      <div class="question-meta-row">
        <div class="question-label">${escapeHtml(label)}</div>
        <div class="question-index">${escapeHtml(t("questionCount", "Question"))} ${currentIndex + 1}/${QUESTIONS.length}</div>
      </div>
      <div class="question-texte ${q.is_arabic ? "arabic" : ""}">${escapeHtml(q.texte)}</div>
      <div class="question-hint">${escapeHtml(hintForQuestionType(q.type_exercice))}</div>
      ${body}
    </div>
  `;
}

function renderChoices(q) {
  return q.choix.map((choix) => {
    const classes = ["choix-btn"];
    if (choix.is_arabic) {
      classes.push("arabic");
    }
    const audioArg = JSON.stringify(choix.audio_url || q.audio_url || "");
    return `
      <button
        class="${classes.join(" ")}"
        data-correct="${choix.est_correct}"
        onclick='selectionnerChoix(this, ${choix.id}, ${choix.est_correct}, ${audioArg})'
      >
        ${escapeHtml(choix.texte)}
      </button>
    `;
  }).join("");
}

function afficherQuestion(index) {
  const pct = QUESTIONS.length ? (index / QUESTIONS.length) * 100 : 100;
  document.getElementById("progress-fill").style.width = `${pct}%`;
  masquerFeedback();
  selectedChoix = null;

  const q = QUESTIONS[index];
  const zone = document.getElementById("exercise-zone");

  if (q.type_exercice === "ordre_mots") {
    zone.innerHTML = renderOrdreMots(q);
    initOrdreMots(q);
  } else if (q.type_exercice === "ecoute") {
    zone.innerHTML = renderEcoute(q);
  } else if (q.type_exercice === "dictee") {
    zone.innerHTML = renderDictee(q);
  } else if (q.type_exercice === "speaking") {
    zone.innerHTML = renderSpeaking(q);
  } else {
    zone.innerHTML = renderQCM(q);
  }
}

function renderQCM(q) {
  return renderQuestionCard(
    t("chooseAnswer", "Choisissez la bonne réponse"),
    q,
    `<div class="choix-grid">${renderChoices(q)}</div>`,
  );
}

function renderEcoute(q) {
  const audioUrl = q.audio_url || "";
  const audioButton = audioUrl
    ? `
      <button class="btn-audio" onclick='jouerAudio(${JSON.stringify(audioUrl)})'>
        <span class="audio-icon">🔊</span>
        <span>${escapeHtml(t("listenChoose", "Écoutez et choisissez"))}</span>
      </button>
    `
    : "";

  return renderQuestionCard(
    t("listenChoose", "Écoutez et choisissez"),
    q,
    `${audioButton}<div class="choix-grid">${renderChoices(q)}</div>`,
  );
}

function renderOrdreMots(q) {
  return renderQuestionCard(
    t("putInOrder", "Remettez les mots dans l'ordre"),
    q,
    `
      <div class="mots-cible" id="mots-cible" ondrop="dropMot(event)" ondragover="dragOverMot(event)" ondragleave="dragLeaveMot(event)"></div>
      <div class="mots-source" id="mots-source"></div>
    `,
  );
}

function renderDictee(q) {
  return renderQuestionCard(
    t("dictationPrompt", "Écoutez et écrivez ce que vous entendez"),
    q,
    `
      <button class="btn-audio" onclick='jouerAudio(${JSON.stringify(q.audio_url || "")})'>
        <span class="audio-icon">🔊</span>
        <span>${escapeHtml(t("listenWord", "Écouter le mot"))}</span>
      </button>
      <button class="btn-audio btn-audio-repeat" onclick='jouerAudio(${JSON.stringify(q.audio_url || "")})'>
        ↻ ${escapeHtml(t("repeat", "Répéter"))}
      </button>
      <div class="dictee-zone">
        <input
          type="text"
          id="dictee-input"
          class="dictee-input arabic-text"
          placeholder="${escapeHtml(t("writeHere", "Écrivez ici..."))}"
          dir="rtl"
          autocomplete="off"
          autocorrect="off"
          spellcheck="false"
        >
        <button id="btn-valider-dictee" class="btn-valider-dictee" onclick='validerDictee(${q.id}, ${JSON.stringify(q.bonne_reponse_texte || "")})'>
          ${escapeHtml(t("validate", "Valider"))}
        </button>
        <div id="dictee-correction" class="dictee-correction"></div>
      </div>
    `,
  );
}

function renderSpeaking(q) {
  const supported = "webkitSpeechRecognition" in window || "SpeechRecognition" in window;

  if (!supported) {
    return renderQuestionCard(
      t("speakingPrompt", "Prononcez cette phrase"),
      q,
      `
        <div class="speaking-not-supported">
          <span style="font-size:2rem">🎤</span>
          <p>${escapeHtml(t("speakingChromeOnly", "La reconnaissance vocale n'est disponible que sur Chrome. Essayez sur Chrome Android ou Chrome Desktop."))}</p>
          <button class="btn-skip" onclick="skipQuestion(${q.id})">
            ${escapeHtml(t("skipQuestion", "Passer cette question"))}
          </button>
        </div>
      `,
    );
  }

  return renderQuestionCard(
    t("speakingPrompt", "Prononcez cette phrase"),
    q,
    `
      <div class="speaking-texte arabic-text">${escapeHtml(q.texte)}</div>
      ${q.audio_url ? `
        <button class="btn-audio" onclick='jouerAudio(${JSON.stringify(q.audio_url)})'>
          🔊 ${escapeHtml(t("listenExample", "Écouter l'exemple"))}
        </button>
      ` : ""}
      <div class="speaking-zone" id="speaking-zone-${q.id}">
        <button
          class="btn-record"
          id="btn-record-${q.id}"
          onclick='demarrerEnregistrement(${q.id}, ${JSON.stringify(q.bonne_reponse_texte || q.texte || "")})'
        >
          <span class="record-icon">🎤</span>
          <span>${escapeHtml(t("pressToSpeak", "Appuyez pour parler"))}</span>
        </button>
        <div class="speaking-result" id="speaking-result-${q.id}" style="display:none"></div>
      </div>
    `,
  );
}

function initOrdreMots(q) {
  const source = document.getElementById("mots-source");
  if (!source) {
    return;
  }

  const correctWords = q.bonne_reponse_ordre || [];
  const distractors = q.choix
    .filter((choix) => !choix.est_correct)
    .flatMap((choix) => (choix.texte || "").split(/\s+/))
    .filter(Boolean);
  const words = melanger([...correctWords, ...distractors]);
  const isArabic = words.some((word) => /[\u0600-\u06FF]/.test(word));

  source.innerHTML = words.map((word, index) => `
    <button
      type="button"
      class="mot-chip ${isArabic ? "arabic" : ""}"
      draggable="true"
      ondragstart="dragStart(event, 'mot-${index}')"
      onclick='selectionnerMotOrdre("mot-${index}")'
      data-token="mot-${index}"
      data-mot="${escapeHtml(word)}"
    >
      ${escapeHtml(word)}
    </button>
  `).join("");
}

function trouverMotSource(token) {
  return document.querySelector(`.mots-source .mot-chip[data-token="${token}"]`);
}

function compterMotsCibles(q) {
  const expectedCount = (q.bonne_reponse_ordre || []).length;
  const currentCount = document.querySelectorAll(".mots-cible .mot-chip").length;
  if (expectedCount > 0 && currentCount === expectedCount) {
    validerOrdreMots(q);
  }
}

function ajouterMotOrdreDepuisSource(source) {
  if (!source || selectedChoix !== null || source.classList.contains("used")) {
    return;
  }

  const token = source.dataset.token;
  const mot = source.dataset.mot;
  const cible = document.getElementById("mots-cible");
  if (!cible) {
    return;
  }

  source.classList.add("used");
  source.classList.remove("dragging");

  const chip = document.createElement("button");
  chip.type = "button";
  chip.className = `mot-chip en-cible ${source.classList.contains("arabic") ? "arabic" : ""}`;
  chip.textContent = mot;
  chip.dataset.mot = mot;
  chip.dataset.token = token;
  chip.onclick = () => remettreMotOrdre(token);
  cible.appendChild(chip);

  compterMotsCibles(QUESTIONS[currentIndex]);
}

function selectionnerMotOrdre(token) {
  ajouterMotOrdreDepuisSource(trouverMotSource(token));
}

function dragStart(event, token) {
  event.dataTransfer.setData("text/plain", token);
  event.currentTarget.classList.add("dragging");
}

function dragOverMot(event) {
  event.preventDefault();
  event.currentTarget.classList.add("drag-over");
}

function dragLeaveMot(event) {
  event.currentTarget.classList.remove("drag-over");
}

function dropMot(event) {
  event.preventDefault();
  event.currentTarget.classList.remove("drag-over");
  const token = event.dataTransfer.getData("text/plain");
  ajouterMotOrdreDepuisSource(trouverMotSource(token));
}

function remettreMotOrdre(token) {
  if (selectedChoix !== null) {
    return;
  }
  const chip = document.querySelector(`.mots-cible .mot-chip[data-token="${token}"]`);
  const source = trouverMotSource(token);
  if (!chip || !source) {
    return;
  }
  chip.remove();
  source.classList.remove("used");
}

function validerOrdreMots(q) {
  if (selectedChoix !== null) {
    return;
  }
  const mots = [...document.querySelectorAll(".mots-cible .mot-chip")].map((chip) => chip.dataset.mot);
  const estCorrect = mots.join(" ") === (q.bonne_reponse_ordre || []).join(" ");
  const choixId = estCorrect ? q.correct_choice_id : (q.incorrect_choice_id || q.correct_choice_id || null);

  document.querySelectorAll(".mot-chip").forEach((chip) => {
    chip.style.pointerEvents = "none";
  });

  selectedChoix = { choixId, estCorrect };
  resultats.push({
    question_id: q.id,
    choix_id: choixId,
    correct: estCorrect,
  });

  if (estCorrect) {
    score += 1;
  }
  afficherFeedback(estCorrect, q.correction);
}

function normalizeArabic(value) {
  return String(value || "")
    .replace(/[\u064B-\u065F]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeArabicCompact(value) {
  return normalizeArabic(value).replace(/\s+/g, "");
}

function validerDictee(questionId, bonneReponse) {
  if (selectedChoix !== null) {
    return;
  }

  const input = document.getElementById("dictee-input");
  const correctionEl = document.getElementById("dictee-correction");
  const button = document.getElementById("btn-valider-dictee");
  const saisie = (input?.value || "").trim();
  if (!saisie) {
    return;
  }

  const estCorrect = normalizeArabic(saisie) === normalizeArabic(bonneReponse);
  if (input) {
    input.disabled = true;
    input.style.borderColor = estCorrect ? "var(--success)" : "var(--danger)";
  }
  if (button) {
    button.disabled = true;
  }

  if (!estCorrect && correctionEl) {
    correctionEl.textContent = `${t("goodAnswerPrefix", "Bonne réponse :")} ${bonneReponse}`;
    correctionEl.style.display = "block";
  }

  selectedChoix = { choixId: null, estCorrect };
  resultats.push({
    question_id: questionId,
    choix_id: null,
    correct: estCorrect,
    reponse_saisie: saisie,
  });

  if (estCorrect) {
    score += 1;
  }

  afficherFeedback(estCorrect, estCorrect ? "" : `${t("goodAnswerPrefix", "Bonne réponse :")} ${bonneReponse}`);
}

function jouerAudio(url) {
  const resolvedUrl = resolveMediaUrl(url);
  if (!resolvedUrl) {
    return;
  }
  const trigger = document.activeElement && document.activeElement.classList.contains("btn-audio")
    ? document.activeElement
    : null;
  if (trigger) {
    trigger.classList.add("is-playing");
  }
  const audio = new Audio(resolvedUrl);
  audio.addEventListener("ended", () => {
    if (trigger) {
      trigger.classList.remove("is-playing");
    }
  }, { once: true });
  audio.play().catch(() => {
    if (trigger) {
      trigger.classList.remove("is-playing");
    }
  });
}

function demarrerEnregistrement(questionId, attendu) {
  if (selectedChoix !== null) {
    return;
  }

  const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognitionClass) {
    alert(t("speechUnavailable", "Reconnaissance vocale indisponible sur ce navigateur."));
    return;
  }

  const recognition = new SpeechRecognitionClass();
  recognition.lang = "ar-SA";
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.maxAlternatives = 3;

  const btn = document.getElementById(`btn-record-${questionId}`);
  const resultBox = document.getElementById(`speaking-result-${questionId}`);
  if (btn) {
    btn.innerHTML = `<span class="record-icon recording">🔴</span><span>${escapeHtml(t("speakNow", "Parlez maintenant..."))}</span>`;
    btn.disabled = true;
  }

  recognition.onresult = (event) => {
    const transcriptions = Array.from(event.results[0] || []).map((result) => result.transcript || "").filter(Boolean);
    const meilleure = transcriptions[0] || "";
    const attenduNorm = normalizeArabicCompact(attendu);
    const correct = transcriptions.some((transcription) => {
      const normalized = normalizeArabicCompact(transcription);
      return normalized && (
        normalized === attenduNorm
        || attenduNorm.includes(normalized)
        || normalized.includes(attenduNorm)
      );
    });

    if (resultBox) {
      resultBox.style.display = "block";
      resultBox.innerHTML = `
        <div class="speaking-transcrit arabic-text">${escapeHtml(meilleure)}</div>
        <div class="speaking-score ${correct ? "correct" : "incorrect"}">
          ${correct ? "✓ " + escapeHtml(t("pronunciationGood", "Bonne prononciation !")) : "✗ " + escapeHtml(t("retry", "Réessayez"))}
        </div>
        ${!correct ? `
          <div class="speaking-attendu">
            <span class="small text-muted">${escapeHtml(t("expectedLabel", "Attendu :"))}</span>
            <span class="arabic-text">${escapeHtml(attendu)}</span>
          </div>
        ` : ""}
      `;
    }

    selectedChoix = { choixId: null, estCorrect: correct };
    resultats.push({
      question_id: questionId,
      choix_id: null,
      correct,
      reponse_saisie: meilleure,
    });

    if (correct) {
      score += 1;
    }

    afficherFeedback(
      correct,
      correct ? "" : `${t("youSaidPrefix", "Vous avez dit :")} ${meilleure}`,
    );
  };

  recognition.onerror = (event) => {
    if (btn) {
      btn.innerHTML = `<span class="record-icon">🎤</span><span>${escapeHtml(t("pressToSpeak", "Appuyez pour parler"))}</span>`;
      btn.disabled = false;
    }

    if (event.error === "no-speech") {
      alert(t("noSpeechDetected", "Aucune voix détectée. Réessayez."));
    } else if (event.error === "not-allowed") {
      alert(t("micDenied", "Accès au microphone refusé. Autorisez le micro dans les paramètres du navigateur."));
    } else {
      alert(t("speechUnavailable", "Reconnaissance vocale indisponible sur ce navigateur."));
    }
  };

  recognition.onend = () => {
    if (btn && selectedChoix === null) {
      btn.innerHTML = `<span class="record-icon">🎤</span><span>${escapeHtml(t("pressToSpeak", "Appuyez pour parler"))}</span>`;
      btn.disabled = false;
    }
  };

  recognition.start();
}

function skipQuestion(questionId) {
  if (selectedChoix !== null) {
    return;
  }
  selectedChoix = { choixId: null, estCorrect: false };
  resultats.push({
    question_id: questionId,
    choix_id: null,
    correct: false,
    reponse_saisie: "skipped",
  });
  questionSuivante();
}

function selectionnerChoix(element, choixId, estCorrect, audioUrl) {
  if (selectedChoix !== null) {
    return;
  }

  selectedChoix = { choixId, estCorrect, element };
  document.querySelectorAll(".choix-btn").forEach((button) => {
    button.disabled = true;
  });

  element.classList.add(estCorrect ? "correct" : "incorrect");
  if (!estCorrect) {
    document.querySelectorAll(".choix-btn").forEach((button) => {
      if (button.dataset.correct === "true") {
        button.classList.add("correct");
      }
    });
  }

  resultats.push({
    question_id: QUESTIONS[currentIndex].id,
    choix_id: choixId,
    correct: estCorrect,
  });

  if (audioUrl) {
    jouerAudio(audioUrl);
  }

  if (estCorrect) {
    score += 1;
  }

  afficherFeedback(estCorrect, QUESTIONS[currentIndex].correction);
}

function afficherFeedback(correct, texteCorrection) {
  const footer = document.getElementById("feedback-footer");
  footer.classList.remove("hidden", "correct", "incorrect");
  footer.classList.add(correct ? "correct" : "incorrect");

  document.getElementById("feedback-icon").textContent = correct ? "✓" : "✕";
  document.getElementById("feedback-text").innerHTML = correct
    ? `<strong>${escapeHtml(t("correct", "Correct !"))}</strong>`
    : `<strong>${escapeHtml(t("incorrect", "Pas tout à fait."))}</strong>${texteCorrection ? `<br>${escapeHtml(texteCorrection)}` : ""}`;

  if (correct) {
    xpGagne += 5;
    document.getElementById("xp-display").textContent = xpGagne;
  }
}

function masquerFeedback() {
  document.getElementById("feedback-footer").classList.add("hidden");
}

function questionSuivante() {
  currentIndex += 1;
  if (currentIndex >= QUESTIONS.length) {
    afficherFinLecon();
  } else {
    afficherQuestion(currentIndex);
  }
}

function afficherFinLecon() {
  const pct = QUESTIONS.length ? Math.round((score / QUESTIONS.length) * 100) : 0;
  document.getElementById("progress-fill").style.width = "100%";
  masquerFeedback();

  document.getElementById("exercise-zone").innerHTML = `
    <div id="fin-lecon">
      <div class="fin-emoji">${pct >= 70 ? "★" : "↺"}</div>
      <div class="fin-titre">${escapeHtml(pct >= 70 ? t("lessonDone", "Leçon terminée !") : t("keepGoing", "Continue comme ça !"))}</div>
      <div class="fin-xp" id="fin-xp-value">+${xpGagne} XP</div>
      <div class="fin-stats">
        <div class="fin-stat">
          <span class="valeur" style="color:var(--success)">${score}</span>
          <span class="label">${escapeHtml(t("correctCount", "Correctes"))}</span>
        </div>
        <div class="fin-stat">
          <span class="valeur" style="color:var(--danger)">${QUESTIONS.length - score}</span>
          <span class="label">${escapeHtml(t("errorCount", "Erreurs"))}</span>
        </div>
        <div class="fin-stat">
          <span class="valeur" style="color:var(--primary)">${pct}%</span>
          <span class="label">${escapeHtml(t("score", "Score"))}</span>
        </div>
      </div>
      <div id="fin-extra" class="fin-stats"></div>
      <div class="d-flex flex-column flex-sm-row gap-3 mt-2">
        <a href="${COURSES_URL}" class="btn-continuer-fin" id="btn-fin-principal">${escapeHtml(t("backToCourses", "Retour aux cours"))}</a>
        <a href="${COURSE_DETAIL_URL}" class="btn-secondaire-fin">${escapeHtml(t("viewCourse", "Voir le cours"))}</a>
      </div>
    </div>
  `;

  fetch(`/lecons/${LECON_ID}/complete`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": CSRF_TOKEN,
    },
    body: JSON.stringify({ resultats, score: pct / 100 }),
  })
    .then((response) => response.json().then((data) => ({ ok: response.ok, data })))
    .then(({ ok, data }) => {
      if (!ok) {
        return;
      }

      completionResponse = data;
      if (typeof data.xp_gagne === "number") {
        xpGagne = data.xp_gagne;
        document.getElementById("xp-display").textContent = xpGagne;
        const xpBadge = document.getElementById("fin-xp-value");
        if (xpBadge) {
          xpBadge.textContent = `+${data.xp_gagne} XP`;
        }
      }

      const finExtra = document.getElementById("fin-extra");
      if (finExtra) {
        finExtra.innerHTML = `
          <div class="fin-stat">
            <span class="valeur" style="color:var(--primary)">${data.total_xp ?? 0}</span>
            <span class="label">${escapeHtml(t("totalXp", "XP total"))}</span>
          </div>
          <div class="fin-stat">
            <span class="valeur" style="color:#ff9600">${data.streak ?? 0}</span>
            <span class="label">${escapeHtml(t("streak", "Série"))}</span>
          </div>
        `;
      }

      const principalButton = document.getElementById("btn-fin-principal");
      if (principalButton && data.next_lecon_id) {
        principalButton.href = `/lecons/${data.next_lecon_id}/start`;
        principalButton.textContent = t("nextLesson", "Leçon suivante");
      }

      if (data.total_lecons_terminees === 1 && window.proposerNotifications) {
        setTimeout(() => {
          window.proposerNotifications().catch(() => {});
        }, 2000);
      }
    })
    .catch(() => {});
}

function quitterLecon() {
  if (confirm(t("quitConfirm", "Quitter la leçon ? Ta progression sera perdue."))) {
    window.location.href = COURSES_URL;
  }
}

document.addEventListener("DOMContentLoaded", init);
