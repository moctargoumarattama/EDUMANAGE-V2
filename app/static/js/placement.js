let currentIndex = 0;
let score = 0;
const resultats = [];
let selectedChoix = null;

function t(key, fallback) {
  return (window.PLACEMENT_I18N && window.PLACEMENT_I18N[key]) || fallback;
}

function init() {
  if (!Array.isArray(QUESTIONS) || QUESTIONS.length === 0) {
    afficherFinTest();
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

function melanger(array) {
  const copie = [...array];
  for (let i = copie.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copie[i], copie[j]] = [copie[j], copie[i]];
  }
  return copie;
}

function afficherQuestion(index) {
  const pct = QUESTIONS.length ? (index / QUESTIONS.length) * 100 : 100;
  document.getElementById("progress-fill").style.width = `${pct}%`;
  masquerFeedback();
  selectedChoix = null;

  const q = QUESTIONS[index];
  const zone = document.getElementById("exercise-zone");

  if (q.type_exercice === "choisir_image") {
    zone.innerHTML = renderChoisirImage(q);
  } else if (q.type_exercice === "ordre_mots") {
    zone.innerHTML = renderOrdreMots(q);
    initOrdreMots(q);
  } else {
    zone.innerHTML = renderQCM(q);
  }
}

function renderQuestionHeader(label, q) {
  const media = q.audio_url
    ? `
      <button class="btn-audio" onclick='jouerAudio(${JSON.stringify(q.audio_url)})'>
        <span class="audio-icon">🔊</span>
        <span>${escapeHtml(t("listen", "Écouter"))}</span>
      </button>
    `
    : q.image_url
      ? `<img src="${escapeHtml(q.image_url)}" alt="Illustration" class="img-fluid rounded-4 shadow-sm mb-4" style="max-height:220px;object-fit:cover;">`
      : "";

  return `
    <div class="question-label">${escapeHtml(label)}</div>
    <div class="question-texte ${q.is_arabic ? "arabic" : ""}">${escapeHtml(q.texte)}</div>
    ${media}
  `;
}

function renderQCM(q) {
  const choices = q.choix.map((choix) => {
    const classes = ["choix-btn"];
    if (choix.is_arabic) {
      classes.push("arabic");
    }
    return `
      <button
        class="${classes.join(" ")}"
        data-correct="${choix.est_correct}"
        onclick="selectionnerChoix(this, ${q.id}, ${choix.id}, ${choix.est_correct})"
      >
        ${escapeHtml(choix.texte)}
      </button>
    `;
  }).join("");

  return `
    ${renderQuestionHeader(t("chooseAnswer", "Choisissez la bonne réponse"), q)}
    <div class="choix-grid">${choices}</div>
  `;
}

function renderChoisirImage(q) {
  const choices = q.choix.map((choix) => `
    <div
      class="image-choix"
      data-correct="${choix.est_correct}"
      onclick="selectionnerImage(this, ${q.id}, ${choix.id}, ${choix.est_correct})"
    >
      ${choix.image_url ? `<img src="${escapeHtml(choix.image_url)}" alt="${escapeHtml(choix.texte || "Choix")}">` : ""}
      <span class="${choix.is_arabic ? "arabic" : ""}">${escapeHtml(choix.texte || "")}</span>
    </div>
  `).join("");

  return `
    ${renderQuestionHeader(t("chooseImage", "Choisissez la bonne image"), q)}
    <div class="image-grid">${choices}</div>
  `;
}

function renderOrdreMots(q) {
  return `
    ${renderQuestionHeader(t("putInOrder", "Remettez les mots dans l'ordre"), q)}
    <div class="mots-cible" id="mots-cible" ondrop="dropMot(event)" ondragover="dragOverMot(event)" ondragleave="dragLeaveMot(event)"></div>
    <div class="mots-source" id="mots-source"></div>
  `;
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
      onclick='selectionnerMotOrdre("mot-${index}")'
      ondragstart='dragStart(event, "mot-${index}")'
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
  const correct = mots.join(" ") === (q.bonne_reponse_ordre || []).join(" ");
  const choixId = correct ? q.correct_choice_id : (q.incorrect_choice_id || q.correct_choice_id);

  document.querySelectorAll(".mot-chip").forEach((chip) => {
    chip.style.pointerEvents = "none";
  });

  selectedChoix = { questionId: q.id, choixId, estCorrect: correct };
  enregistrerResultat(q.id, choixId, correct);
  afficherFeedback(correct, correct ? t("rightStructure", "Bonne structure.") : t("wrongForm", "La structure attendue est différente."));
}

function selectionnerChoix(element, questionId, choixId, estCorrect) {
  if (selectedChoix !== null) {
    return;
  }

  selectedChoix = { questionId, choixId, estCorrect };
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

  enregistrerResultat(questionId, choixId, estCorrect);
  afficherFeedback(estCorrect, estCorrect ? t("rightStructure", "Bien joué.") : t("wrongForm", "Pas tout à fait."));
}

function selectionnerImage(element, questionId, choixId, estCorrect) {
  if (selectedChoix !== null) {
    return;
  }

  selectedChoix = { questionId, choixId, estCorrect };
  document.querySelectorAll(".image-choix").forEach((card) => {
    card.style.pointerEvents = "none";
  });

  element.classList.add("selected", estCorrect ? "correct" : "incorrect");
  if (!estCorrect) {
    document.querySelectorAll(".image-choix").forEach((card) => {
      if (card.dataset.correct === "true") {
        card.classList.add("correct");
      }
    });
  }

  enregistrerResultat(questionId, choixId, estCorrect);
  afficherFeedback(estCorrect, estCorrect ? t("rightImage", "Bonne image.") : t("wrongImage", "La bonne image est maintenant surlignée."));
}

function enregistrerResultat(questionId, choixId, estCorrect) {
  resultats.push({ question_id: questionId, choix_id: choixId });
  if (estCorrect) {
    score += 1;
  }
}

function afficherFeedback(correct, message) {
  const footer = document.getElementById("feedback-footer");
  footer.classList.remove("hidden", "correct", "incorrect");
  footer.classList.add(correct ? "correct" : "incorrect");
  document.getElementById("feedback-icon").textContent = correct ? "✅" : "❌";
  document.getElementById("feedback-text").innerHTML = correct
    ? `<strong>${escapeHtml(t("correct", "Correct."))}</strong><br>${escapeHtml(message || "")}`
    : `<strong>${escapeHtml(t("continueText", "Continue."))}</strong><br>${escapeHtml(message || "")}`;
}

function masquerFeedback() {
  document.getElementById("feedback-footer").classList.add("hidden");
}

function questionSuivante() {
  currentIndex += 1;
  if (currentIndex >= QUESTIONS.length) {
    afficherFinTest();
  } else {
    afficherQuestion(currentIndex);
  }
}

function afficherFinTest() {
  const pct = QUESTIONS.length ? Math.round((score / QUESTIONS.length) * 100) : 0;
  document.getElementById("progress-fill").style.width = "100%";
  masquerFeedback();

  document.getElementById("exercise-zone").innerHTML = `
    <div id="fin-lecon">
      <div class="fin-emoji">🧭</div>
      <div class="fin-titre">${escapeHtml(t("analyzing", "Analyse du niveau en cours..."))}</div>
      <div class="fin-xp">${escapeHtml(t("provisionalScore", "Score provisoire"))} : ${pct}%</div>
    </div>
  `;

  fetch(PLACEMENT_COMPLETE_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": CSRF_TOKEN,
    },
    body: JSON.stringify({ resultats }),
  })
    .then((response) => response.json().then((data) => ({ ok: response.ok, data })))
    .then(({ ok, data }) => {
      if (!ok) {
        throw new Error(data.error || "Erreur");
      }

      const levelClass = data.niveau === "A2" ? "badge-A2" : "badge-A1";
      const levelTheme = data.niveau === "A2" ? "var(--primary)" : "var(--secondary)";
      const nbCorrect = Math.round((data.score || 0) * QUESTIONS.length);
      document.getElementById("exercise-zone").innerHTML = `
        <div id="fin-lecon">
          <div class="fin-emoji">${data.niveau === "A2" ? "🌟" : "📘"}</div>
          <div class="fin-titre">${escapeHtml(data.message || "")}</div>
          <div class="fin-xp" style="color:${levelTheme};border-color:${levelTheme};background:#f8f7ff;">
            ${escapeHtml(t("assignedLevel", "Niveau assigné"))} :
            <span class="badge-niveau ${levelClass} ms-2">${escapeHtml(data.niveau)}</span>
          </div>
          <div class="fin-stats">
            <div class="fin-stat">
              <span class="valeur" style="color:var(--success)">${nbCorrect}</span>
              <span class="label">${escapeHtml(t("correctCount", "Correctes"))}</span>
            </div>
            <div class="fin-stat">
              <span class="valeur" style="color:var(--danger)">${QUESTIONS.length - nbCorrect}</span>
              <span class="label">${escapeHtml(t("errorCount", "Erreurs"))}</span>
            </div>
            <div class="fin-stat">
              <span class="valeur" style="color:var(--primary)">${Math.round((data.score || 0) * 100)}%</span>
              <span class="label">${escapeHtml(t("score", "Score"))}</span>
            </div>
          </div>
          <a href="${COURSES_URL}" class="btn-continuer-fin">${escapeHtml(t("startLearning", "Commencer l'apprentissage"))}</a>
        </div>
      `;
    })
    .catch((error) => {
      document.getElementById("exercise-zone").innerHTML = `
        <div id="fin-lecon">
          <div class="fin-emoji">⚠️</div>
          <div class="fin-titre">${escapeHtml(t("saveErrorTitle", "Le test n'a pas pu être enregistré"))}</div>
          <div class="fin-xp">${escapeHtml(error.message)}</div>
          <a href="${COURSES_URL}" class="btn-continuer-fin">${escapeHtml(t("backToCourses", "Retour aux cours"))}</a>
        </div>
      `;
    });
}

function quitterPlacement() {
  if (confirm(t("quitConfirm", "Quitter le test de niveau ? Vos réponses ne seront pas conservées."))) {
    window.location.href = COURSES_URL;
  }
}

function jouerAudio(url) {
  if (!url) {
    return;
  }
  const audio = new Audio(url);
  audio.play().catch(() => {});
}

document.addEventListener("DOMContentLoaded", init);
