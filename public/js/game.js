(function () {
  'use strict';

  const NUM_PARTS = 3;
  const TARGETS_PER_PART = 4;
  const TOP_K = 1000;
  const MAGIC = 0x5058;
  const VERSION = 1;

  const LS_KEY = 'proximot_state';
  const TODAY = new Date().toISOString().slice(0, 10);

  const $ = (id) => document.getElementById(id);
  const screen = (id) => {
    document.querySelectorAll('.screen').forEach((s) => s.classList.remove('active'));
    $(id).classList.add('active');
  };

  let words = [];
  let wordIndex = {};        // normalized → original word
  let wordIdxMap = {};       // normalized → index
  let allData = null;        // raw ArrayBuffer of today's .bin
  let dataView = null;
  let currentPart = 0;
  let attempts = 0;
  let history = [];          // [{word, scores: [int]}]
  let bestScores = [0, 0, 0, 0];
  let foundMask = 0;
  let targetWords = [null, null, null, null];
  let currentDetailTarget = -1;
  let stateLoaded = false;

  // ---------- Normalization ----------
  function normalize(w) {
    return w
      .toLowerCase()
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .replace(/\s+/g, '-')
      .replace(/[^a-z0-9-]/g, '');
  }

  // ---------- Binary decoder ----------

  function getPartOffset(data, part) {
    let offset = 4;
    for (let p = 0; p < part; p++) {
      offset += TARGETS_PER_PART * (2 + TOP_K * 4);
    }
    return offset;
  }

  function getTargetData(data, part, target) {
    const offset = getPartOffset(data, part) + target * (2 + TOP_K * 4);
    const targetIdx = data.getUint16(offset, true);
    const entries = [];
    for (let i = 0; i < TOP_K; i++) {
      const eo = offset + 2 + i * 4;
      entries.push({
        index: data.getUint16(eo, true),
        score: data.getUint16(eo + 2, true),
      });
    }
    return { targetIdx, entries };
  }

  function getScoreForTarget(part, target, wordIdx) {
    if (!dataView) return 0;
    const td = getTargetData(dataView, part, target);
    for (const e of td.entries) {
      if (e.index === wordIdx) {
        return e.score;
      }
    }
    return 0;
  }

  // ---------- Load data ----------
  async function loadData() {
    try {
      const [wordsResp, binResp] = await Promise.all([
        fetch('data/words.json'),
        fetch(`data/${TODAY}.bin`),
      ]);

      words = await wordsResp.json();
      wordIndex = {};
      wordIdxMap = {};
      for (let i = 0; i < words.length; i++) {
        const n = normalize(words[i]);
        wordIndex[n] = words[i];
        wordIdxMap[n] = i;
      }

      allData = await binResp.arrayBuffer();
      dataView = new DataView(allData);

      const magic = dataView.getUint16(0, true);
      const ver = dataView.getUint8(2);
      if (magic !== MAGIC || ver !== VERSION) {
        throw new Error('Format de fichier invalide');
      }

      return true;
    } catch (e) {
      console.error('Erreur chargement:', e);
      return false;
    }
  }

  // ---------- Persistence ----------
  function saveState() {
    const state = {
      date: TODAY,
      part: currentPart,
      attempts,
      history,
      bestScores,
      foundMask,
      targetWords,
    };
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(state));
    } catch (_) {}
  }

  function loadState() {
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (!raw) return false;
      const s = JSON.parse(raw);
      if (s.date !== TODAY) {
        localStorage.removeItem(LS_KEY);
        return false;
      }
      currentPart = s.part;
      attempts = s.attempts;
      history = s.history;
      bestScores = s.bestScores;
      foundMask = s.foundMask;
      targetWords = s.targetWords;
      stateLoaded = true;
      return true;
    } catch (_) {
      return false;
    }
  }

  // ---------- Render ----------
  function renderSlots() {
    const container = $('slots');
    container.innerHTML = '';
    for (let i = 0; i < TARGETS_PER_PART; i++) {
      const isFound = !!(foundMask & (1 << i));
      const best = bestScores[i] || 0;
      const barPct = Math.min(100, (best / 1000) * 100);
      const slot = document.createElement('div');
      slot.className = 'slot' + (isFound ? ' solved' : '');
      slot.dataset.target = i;
      slot.innerHTML = `
        <div class="slot-header">
          <span class="slot-number">Mot n°${i + 1}</span>
          ${isFound ? `<span class="slot-word">${targetWords[i] || '?'}</span>` : ''}
        </div>
        <div class="slot-scores">
          <span class="slot-best">🏆 ${best > 0 ? best + '‰' : '—'}</span>
        </div>
        <div class="slot-bar">
          <div class="slot-bar-fill" style="width:${barPct}%"></div>
        </div>`;
      slot.addEventListener('click', () => showDetail(i));
      container.appendChild(slot);
    }
  }

  function renderHistory() {
    const list = $('history-list');
    list.innerHTML = '';
    for (const h of history.slice().reverse()) {
      const item = document.createElement('div');
      item.className = 'history-item';
      let scoresHtml = '';
      for (let t = 0; t < TARGETS_PER_PART; t++) {
        const sc = h.scores[t] || 0;
        const cls = sc >= 1000 ? 'score-found' : sc >= 500 ? 'score-hot' : sc >= 200 ? 'score-warm' : sc >= 50 ? 'score-cool' : 'score-cold';
        scoresHtml += `<span class="score-pill ${cls}">${sc > 0 ? sc + '' : '—'}</span>`;
      }
      item.innerHTML = `<div class="history-word">${h.word}</div><div class="history-scores">${scoresHtml}</div>`;
      list.appendChild(item);
    }
  }

  function showInputBar(show) {
    $('input-bar').classList.toggle('hidden', !show);
  }

  function showModal() {
    $('modal-overlay').classList.remove('hidden');
    $('word-input').blur();
  }

  function renderAll() {
    renderSlots();
    renderHistory();
  }

  function showDetail(target) {
    currentDetailTarget = target;
    const isFound = !!(foundMask & (1 << target));
    $('detail-label').textContent = isFound
      ? `Mot n°${target + 1} : ${targetWords[target]}`
      : `Mot n°${target + 1}`;

    const container = $('detail-history');
    container.innerHTML = '';
    const ranked = [];
    for (const h of history) {
      const sc = h.scores[target] || 0;
      if (sc > 0) ranked.push({ word: h.word, score: sc });
    }
    ranked.sort((a, b) => b.score - a.score);

    if (ranked.length === 0) {
      container.innerHTML = '<div class="detail-item" style="color:var(--text2)">Aucun mot correspondant trouvé</div>';
    } else {
      ranked.forEach((r, i) => {
        const el = document.createElement('div');
        el.className = 'detail-item';
        const cls = r.score >= 1000 ? 'score-found' : r.score >= 500 ? 'score-hot' : r.score >= 200 ? 'score-warm' : r.score >= 50 ? 'score-cool' : 'score-cold';
        el.innerHTML = `
          <span class="detail-rank">#${i + 1}</span>
          <span class="detail-word">${r.word}</span>
          <span class="detail-score ${cls}">${r.score}‰</span>`;
        container.appendChild(el);
      });
    }
    screen('detail-screen');
    showInputBar(true);
  }

  // ---------- Game logic ----------
  function submitWord() {
    const raw = $('word-input').value.trim();
    if (!raw) return;
    const n = normalize(raw);
    if (n in wordIdxMap) {
      $('word-input').value = '';
      $('autocomplete').classList.add('hidden');
      makeGuess(n, wordIndex[n], wordIdxMap[n]);
    } else {
      $('word-input').value = '';
      $('autocomplete').classList.add('hidden');
      showModal();
    }
  }

  function makeGuess(normalized, originalWord, idx) {
    attempts++;
    const scores = [];
    for (let t = 0; t < TARGETS_PER_PART; t++) {
      const sc = getScoreForTarget(currentPart, t, idx);
      scores.push(sc);
      if (sc > bestScores[t]) {
        bestScores[t] = sc;
      }
      if (sc >= 1000 && !(foundMask & (1 << t))) {
        foundMask |= (1 << t);
        targetWords[t] = originalWord;
      }
    }
    history.push({ word: originalWord, scores });
    renderAll();
    saveState();
    if (currentDetailTarget >= 0 && $(`detail-screen`).classList.contains('active')) {
      showDetail(currentDetailTarget);
    }

    if (foundMask === (1 << TARGETS_PER_PART) - 1) {
      setTimeout(showPartComplete, 800);
    }
  }

  async function startPart(part) {
    currentPart = part;
    attempts = 0;
    history = [];
    bestScores = [0, 0, 0, 0];
    foundMask = 0;
    targetWords = [null, null, null, null];
    currentDetailTarget = -1;
    renderAll();
    saveState();
    screen('game-screen');
    showInputBar(true);
  }

  function showPartComplete() {
    const foundCount = history.filter(h => h.scores.some(s => s >= 1000)).length;
    const totalAttempts = history.length;

    $('complete-title').textContent = `Partie ${currentPart + 1} terminée !`;
    const results = $('complete-results');
    results.innerHTML = `
      <div class="complete-result">
        <span>Mots trouvés</span>
        <span>${TARGETS_PER_PART}/${TARGETS_PER_PART}</span>
      </div>
      <div class="complete-result">
        <span>Essais</span>
        <span>${totalAttempts}</span>
      </div>`;

    if (currentPart < NUM_PARTS - 1) {
      $('btn-next-part').classList.remove('hidden');
      $('btn-next-part').textContent = 'Nouvelle Partie';
      $('btn-next-part').onclick = () => startPart(currentPart + 1);
      $('btn-done').classList.add('hidden');
    } else {
      $('btn-next-part').classList.add('hidden');
      $('btn-done').classList.remove('hidden');
      $('btn-done').textContent = 'Reviens demain !';
      $('btn-done').onclick = () => { screen('rules-screen'); showInputBar(false); };
    }

    screen('part-complete-screen');
    showInputBar(false);
  }

  // ---------- Autocomplete ----------
  function updateAutocomplete() {
    const val = $('word-input').value.trim();
    const container = $('autocomplete');
    if (!val) {
      container.classList.add('hidden');
      return;
    }
    const n = normalize(val);
    if (n in wordIdxMap) {
      container.classList.add('hidden');
      return;
    }
    const matches = words.filter((w) => normalize(w).startsWith(n)).slice(0, 8);
    if (matches.length === 0) {
      container.classList.add('hidden');
      return;
    }
    container.innerHTML = matches
      .map((w) => `<div class="autocomplete-item">${w}</div>`)
      .join('');
    container.classList.remove('hidden');
    container.querySelectorAll('.autocomplete-item').forEach((el) => {
      el.addEventListener('click', () => {
        $('word-input').value = el.textContent;
        container.classList.add('hidden');
        $('btn-submit').disabled = false;
        $('word-input').focus();
      });
    });
  }

  // ---------- Init ----------
  async function init() {
    const ok = await loadData();
    if (!ok) {
      document.body.innerHTML = '<div class="loading" style="padding:60px;text-align:center">Impossible de charger les données. Reviens plus tard.</div>';
      return;
    }

    // Check if we have a saved game in progress
    if (loadState()) {
      await startPart(currentPart);
      return;
    }

    // Show rules screen
    screen('rules-screen');
    showInputBar(false);

    // Load recent days
    try {
      const idxResp = await fetch('data/index.json');
      const idx = await idxResp.json();
      const recent = idx.slice(-3).reverse();
      const list = $('recent-list');
      for (const entry of recent) {
        if (entry.date === TODAY) continue;
        try {
          const binResp = await fetch(`data/${entry.date}.bin`);
          const bin = await binResp.arrayBuffer();
          const dv = new DataView(bin);
          const allWords = [];
          for (let p = 0; p < NUM_PARTS; p++) {
            for (let t = 0; t < TARGETS_PER_PART; t++) {
              const td = getTargetData(dv, p, t);
              allWords.push(words[td.targetIdx]);
            }
          }
          const div = document.createElement('div');
          div.className = 'recent-day';
          const d = entry.date.slice(5);
          div.innerHTML = `<span class="date">${d}</span><span class="words">${allWords.join(', ')}</span>`;
          list.appendChild(div);
        } catch (_) {}
      }
    } catch (_) {}
  }

  // ---------- Event listeners ----------
  $('btn-play-top').addEventListener('click', () => startPart(0));
  $('btn-play-bottom').addEventListener('click', () => startPart(0));
  $('btn-submit').addEventListener('click', submitWord);
  $('btn-back').addEventListener('click', () => { currentDetailTarget = -1; renderAll(); screen('game-screen'); });
  $('btn-modal-close').addEventListener('click', () => { $('modal-overlay').classList.add('hidden'); $('word-input').focus(); });
  $('modal-overlay').addEventListener('click', (e) => { if (e.target === $('modal-overlay')) { $('modal-overlay').classList.add('hidden'); $('word-input').focus(); } });
  $('word-input').addEventListener('input', () => {
    $('btn-submit').disabled = !$('word-input').value.trim();
    updateAutocomplete();
  });
  $('word-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !$('btn-submit').disabled) {
      submitWord();
    }
    if (e.key === 'Escape') {
      $('autocomplete').classList.add('hidden');
    }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      const items = $('autocomplete').querySelectorAll('.autocomplete-item');
      if (items.length === 0) return;
      e.preventDefault();
      let idx = -1;
      items.forEach((el, i) => { if (el.classList.contains('selected')) idx = i; });
      items.forEach((el) => el.classList.remove('selected'));
      if (e.key === 'ArrowDown') idx = Math.min(idx + 1, items.length - 1);
      else idx = Math.max(idx - 1, 0);
      items[idx].classList.add('selected');
      $('word-input').value = items[idx].textContent;
    }
  });

  init();
})();
