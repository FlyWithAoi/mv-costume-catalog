"use strict";

// ---- 設定 ----
const DATA_URL = "data/costumes.json";
const IMAGE_BASE = "images/costumes"; // + /{idol_slug}/{filename}

// 固定コード -> 日本語表示
const UNLOCK_LABELS = {
  unlocked: "解放済み",
  card_only: "カード所持のみ",
  card_missing: "カード未所持",
  not_purchased: "未購入",
};

const GROUP_LABELS = {
  common: "全員共通衣装",
  unit: "ユニット衣装",
  shuffle: "シャッフル衣装",
  cross: "クロススカウト衣装",
  solo: "個別衣装",
  anniversary: "周年衣装",
  shop: "ショップ衣装",
  other: "その他",
};

// ---- 状態 ----
let allCostumes = [];

// ---- DOM ----
const searchBox = document.getElementById("search-box");
const filterUnlock = document.getElementById("filter-unlock");
const filterRequestable = document.getElementById("filter-requestable");
const cardGrid = document.getElementById("card-grid");
const emptyMessage = document.getElementById("empty-message");
const resultCount = document.getElementById("result-count");
const modalOverlay = document.getElementById("modal-overlay");
const modalBody = document.getElementById("modal-body");
const modalClose = document.getElementById("modal-close");

// ---- ユーティリティ ----
function labelUnlock(code) {
  return UNLOCK_LABELS[code] || code || "不明";
}

function labelGroup(code) {
  return GROUP_LABELS[code] || code || "不明";
}

function imagePath(idolSlug, filename) {
  return `${IMAGE_BASE}/${idolSlug}/${filename}`;
}

// 画像読み込み失敗時のフォールバック（ファイル未配置でも壊れない）
function attachImageFallback(img, labelText) {
  img.addEventListener("error", () => {
    const ph = document.createElement("div");
    ph.className = img.className + " placeholder";
    ph.textContent = labelText || "画像なし";
    // 元のサイズ属性を引き継ぐため親に差し替え
    if (img.parentNode) {
      img.parentNode.replaceChild(ph, img);
    }
  });
}

// ---- 描画：カード ----
function createCard(c) {
  const card = document.createElement("div");
  card.className = "card";
  card.tabIndex = 0;
  card.setAttribute("role", "button");

  const top = document.createElement("div");
  top.className = "card-top";

  // アイコン
  if (c.images && c.images.icon) {
    const icon = document.createElement("img");
    icon.className = "card-icon";
    icon.loading = "lazy";
    icon.alt = c.costume_name;
    icon.src = imagePath(c.idol_slug, c.images.icon);
    attachImageFallback(icon, "アイコン\n準備中");
    top.appendChild(icon);
  } else {
    const ph = document.createElement("div");
    ph.className = "card-icon placeholder";
    ph.textContent = "アイコン\n準備中";
    top.appendChild(ph);
  }

  const heading = document.createElement("div");
  heading.className = "card-heading";

  const name = document.createElement("div");
  name.className = "card-costume-name";
  name.textContent = c.costume_name;

  const idol = document.createElement("div");
  idol.className = "card-idol";
  idol.textContent = `${c.idol}｜${c.unit}`;

  heading.appendChild(name);
  heading.appendChild(idol);
  top.appendChild(heading);
  card.appendChild(top);

  // メタ（バッジ）
  const meta = document.createElement("div");
  meta.className = "card-meta";

  const unlockBadge = document.createElement("span");
  unlockBadge.className = `badge unlock-${c.unlock_status}`;
  unlockBadge.textContent = labelUnlock(c.unlock_status);
  meta.appendChild(unlockBadge);

  const reqBadge = document.createElement("span");
  reqBadge.className = `badge ${c.requestable ? "req-yes" : "req-no"}`;
  reqBadge.textContent = c.requestable ? "リクエスト可" : "リクエスト不可";
  meta.appendChild(reqBadge);

  card.appendChild(meta);

  const open = () => openModal(c);
  card.addEventListener("click", open);
  card.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      open();
    }
  });

  return card;
}

// ---- フィルタリング ----
function getFiltered() {
  const q = searchBox.value.trim().toLowerCase();
  const unlock = filterUnlock.value;
  const onlyRequestable = filterRequestable.checked;

  return allCostumes.filter((c) => {
    if (onlyRequestable && !c.requestable) return false;
    if (unlock && c.unlock_status !== unlock) return false;

    if (q) {
      const haystack = [
        c.idol,
        c.unit,
        c.costume_name,
        ...(Array.isArray(c.tags) ? c.tags : []),
      ]
        .join(" ")
        .toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    return true;
  });
}

function render() {
  const list = getFiltered();
  cardGrid.innerHTML = "";

  if (list.length === 0) {
    emptyMessage.hidden = false;
  } else {
    emptyMessage.hidden = true;
    const frag = document.createDocumentFragment();
    list.forEach((c) => frag.appendChild(createCard(c)));
    cardGrid.appendChild(frag);
  }

  resultCount.textContent = `${list.length}件を表示中（全${allCostumes.length}件）`;
}

// ---- モーダル ----
function buildRequestText(c) {
  // 例: 渉：Caelum
  const shortName = c.idol.split(/\s+/).pop() || c.idol;
  return `${shortName}：${c.costume_name}`;
}

function openModal(c) {
  modalBody.innerHTML = "";

  const title = document.createElement("h2");
  title.id = "modal-title";
  title.textContent = c.costume_name;
  modalBody.appendChild(title);

  const idol = document.createElement("p");
  idol.className = "modal-idol";
  idol.textContent = `${c.idol}｜${c.unit}`;
  modalBody.appendChild(idol);

  // メタ
  const meta = document.createElement("div");
  meta.className = "modal-meta";
  [
    ["解放状態", labelUnlock(c.unlock_status)],
    ["衣装グループ", labelGroup(c.costume_group)],
    ["リクエスト", c.requestable ? "可" : "不可"],
  ].forEach(([k, v]) => {
    const b = document.createElement("span");
    b.className = "badge";
    b.textContent = `${k}：${v}`;
    meta.appendChild(b);
  });
  modalBody.appendChild(meta);

  // 画像
  const imgs = c.images || {};
  const hasFront = imgs.front != null;
  const hasBack = imgs.back != null;

  if (hasFront || hasBack) {
    const wrap = document.createElement("div");
    wrap.className = "modal-images";

    // アイコン（あれば）
    if (imgs.icon) {
      wrap.appendChild(makeImageBlock(c.idol_slug, imgs.icon, "ミニアイコン"));
    }
    if (hasFront) {
      wrap.appendChild(makeImageBlock(c.idol_slug, imgs.front, "正面"));
    }
    if (hasBack) {
      wrap.appendChild(makeImageBlock(c.idol_slug, imgs.back, "背面"));
    }
    modalBody.appendChild(wrap);
  } else {
    // アイコンだけは出す（あれば）。front/backがなくアイコン1枚だけの場合、
    // flexboxの伸長でアイコンが巨大化しないよう専用クラスで幅を固定する。
    if (imgs.icon) {
      const wrap = document.createElement("div");
      wrap.className = "modal-images icon-only";
      wrap.appendChild(makeImageBlock(c.idol_slug, imgs.icon, "ミニアイコン"));
      modalBody.appendChild(wrap);
    }
    const note = document.createElement("div");
    note.className = "no-image-note";
    note.textContent = "未所持・未解放のため着用画像はありません。";
    modalBody.appendChild(note);
  }

  // タグ
  if (Array.isArray(c.tags) && c.tags.length > 0) {
    const tags = document.createElement("div");
    tags.className = "modal-tags";
    c.tags.forEach((t) => {
      const span = document.createElement("span");
      span.className = "tag";
      span.textContent = t;
      tags.appendChild(span);
    });
    modalBody.appendChild(tags);
  }

  // 公開メモ
  if (c.note_public && c.note_public.trim() !== "") {
    const note = document.createElement("div");
    note.className = "modal-note";
    note.textContent = c.note_public;
    modalBody.appendChild(note);
  }

  // リクエスト文
  const reqSection = document.createElement("div");
  reqSection.className = "request-section";

  const reqLabel = document.createElement("div");
  reqLabel.textContent = "リクエスト文";
  reqSection.appendChild(reqLabel);

  const reqText = document.createElement("div");
  reqText.className = "request-text";
  const requestString = buildRequestText(c);
  reqText.textContent = requestString;
  reqSection.appendChild(reqText);

  const copyBtn = document.createElement("button");
  copyBtn.type = "button";
  copyBtn.className = "copy-btn";
  copyBtn.textContent = "リクエスト文をコピー";

  const status = document.createElement("span");
  status.className = "copy-status";
  status.setAttribute("aria-live", "polite");

  copyBtn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(requestString);
      status.textContent = "コピーしました！";
    } catch (err) {
      // 失敗時：手動コピーを促す（テキストは reqText で選択可能）
      status.textContent = "自動コピー失敗。上のテキストを選択してコピーしてください。";
      reqText.focus?.();
      selectText(reqText);
    }
    setTimeout(() => {
      status.textContent = "";
    }, 4000);
  });

  reqSection.appendChild(copyBtn);
  reqSection.appendChild(status);
  modalBody.appendChild(reqSection);

  modalOverlay.hidden = false;
  document.body.style.overflow = "hidden";
  modalClose.focus();
}

function makeImageBlock(idolSlug, filename, labelText) {
  const block = document.createElement("div");
  block.className = "modal-image-block";

  const img = document.createElement("img");
  img.loading = "lazy";
  img.alt = labelText;
  img.src = imagePath(idolSlug, filename);
  attachImageFallback(img, `${labelText}\n準備中`);
  block.appendChild(img);

  const label = document.createElement("div");
  label.className = "label";
  label.textContent = labelText;
  block.appendChild(label);

  return block;
}

function selectText(el) {
  const range = document.createRange();
  range.selectNodeContents(el);
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);
}

function closeModal() {
  modalOverlay.hidden = true;
  document.body.style.overflow = "";
}

modalClose.addEventListener("click", closeModal);
modalOverlay.addEventListener("click", (e) => {
  if (e.target === modalOverlay) closeModal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !modalOverlay.hidden) closeModal();
});

// ---- イベント ----
searchBox.addEventListener("input", render);
filterUnlock.addEventListener("change", render);
filterRequestable.addEventListener("change", render);

// ---- 初期化 ----
async function init() {
  // 念のため：初期表示ではモーダルを必ず非表示にする
  modalOverlay.hidden = true;
  document.body.style.overflow = "";

  try {
    const res = await fetch(DATA_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    allCostumes = Array.isArray(data.costumes) ? data.costumes : [];
  } catch (err) {
    cardGrid.innerHTML = "";
    emptyMessage.hidden = false;
    emptyMessage.textContent =
      "データの読み込みに失敗しました。ローカル確認は python -m http.server を使ってください（index.html を直接開くと fetch がブロックされます）。";
    resultCount.textContent = "";
    console.error("costumes.json の読み込みに失敗:", err);
    return;
  }
  render();
}

init();
