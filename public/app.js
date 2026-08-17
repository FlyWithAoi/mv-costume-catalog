"use strict";

// ---- 設定 ----
const DATA_URL = "data/costumes.json";
const IDOLS_URL = "data/idols.json";
const UNITS_URL = "data/units.json";
const OFFICES_URL = "data/offices.json";
const IMAGE_BASE = "images/costumes"; // + /{idol_slug}/{filename}

// 固定コード -> 日本語表示
const UNLOCK_LABELS = {
  unlocked: "解放済み",
  locked: "解放条件未達",
  not_purchased: "未購入",
  card_missing: "カード未所持",
};

const GROUP_LABELS = {
  common: "全員共通衣装",
  unit: "ユニット衣装",
  shuffle: "シャッフル衣装",
  cross: "クロススカウト衣装",
  solo: "個別衣装",
  anniversary: "周年衣装",
  shop: "ショップ衣装",
  exchange: "交換・ショップ衣装",
  campaign: "記念・キャンペーン衣装",
  other: "その他",
};

// ---- canonical sort ----
function canonicalCostumeCompare(a, b, idols) {
  const idolOrder = (costume) => {
    const value = idols[costume.idol_slug]?.sort_order;
    return Number.isInteger(value) ? value : Number.MAX_SAFE_INTEGER;
  };
  const slotOrder = (costume) => (
    Number.isInteger(costume.slot_order) && costume.slot_order > 0
      ? costume.slot_order
      : Number.MAX_SAFE_INTEGER
  );

  const idolDiff = idolOrder(a) - idolOrder(b);
  if (idolDiff !== 0) return idolDiff;

  const slotDiff = slotOrder(a) - slotOrder(b);
  if (slotDiff !== 0) return slotDiff;

  const aId = typeof a.id === "string" ? a.id : "";
  const bId = typeof b.id === "string" ? b.id : "";
  if (aId < bId) return -1;
  if (aId > bId) return 1;
  return 0;
}

function sortCostumesCanonical(costumes, idols) {
  costumes.sort((a, b) => canonicalCostumeCompare(a, b, idols));
}

// ---- 連動フィルタ用のマスタ処理 ----
function canonicalMasterCompare(a, b) {
  const aOrder = Number.isInteger(a?.sort_order) ? a.sort_order : Number.MAX_SAFE_INTEGER;
  const bOrder = Number.isInteger(b?.sort_order) ? b.sort_order : Number.MAX_SAFE_INTEGER;
  if (aOrder !== bOrder) return aOrder - bOrder;

  const aSlug = typeof a?.slug === "string" ? a.slug : "";
  const bSlug = typeof b?.slug === "string" ? b.slug : "";
  if (aSlug < bSlug) return -1;
  if (aSlug > bSlug) return 1;
  return 0;
}

function sortMastersCanonical(items) {
  return items.slice().sort(canonicalMasterCompare);
}

// offices.json から idol / unit の所属事務所を逆引きする。
// Double Face のような兼任ユニットがあっても、idol の所属事務所は idol_slugs を正とする。
function buildOfficeIndex(offices) {
  const officesBySlug = {};
  const officeByIdolSlug = {};
  const officeByUnitSlug = {};
  const duplicateIdolSlugs = [];
  const duplicateUnitSlugs = [];

  offices.forEach((office) => {
    if (!office || !office.slug) return;
    officesBySlug[office.slug] = office;

    const idolSlugs = Array.isArray(office.idol_slugs) ? office.idol_slugs : [];
    idolSlugs.forEach((idolSlug) => {
      if (officeByIdolSlug[idolSlug]) duplicateIdolSlugs.push(idolSlug);
      officeByIdolSlug[idolSlug] = office.slug;
    });

    const unitSlugs = Array.isArray(office.unit_slugs) ? office.unit_slugs : [];
    unitSlugs.forEach((unitSlug) => {
      if (officeByUnitSlug[unitSlug]) duplicateUnitSlugs.push(unitSlug);
      officeByUnitSlug[unitSlug] = office.slug;
    });
  });

  return {
    officesBySlug,
    officeByIdolSlug,
    officeByUnitSlug,
    duplicateIdolSlugs,
    duplicateUnitSlugs,
  };
}

// 現在の事務所・ユニット・idol選択から、選べる候補と安全に保持できる選択を求める。
function resolveLinkedFilterOptions({
  offices,
  idols,
  unitsBySlug,
  officeByIdolSlug,
  officeByUnitSlug,
  officeSlug,
  unitSlug,
  idolSlug,
}) {
  const knownOffice = offices.some((office) => office.slug === officeSlug);
  const resolvedOfficeSlug = knownOffice ? officeSlug : "";
  const unitOptions = sortMastersCanonical(Object.values(unitsBySlug).filter((unit) => (
    !resolvedOfficeSlug || officeByUnitSlug[unit.slug] === resolvedOfficeSlug
  )));
  const resolvedUnitSlug = unitOptions.some((unit) => unit.slug === unitSlug)
    ? unitSlug
    : "";
  const unitMembers = resolvedUnitSlug
    ? new Set(unitsBySlug[resolvedUnitSlug]?.member_slugs || [])
    : null;
  const idolOptions = sortMastersCanonical(idols.filter((idol) => (
    (!resolvedOfficeSlug || officeByIdolSlug[idol.slug] === resolvedOfficeSlug)
    && (!unitMembers || unitMembers.has(idol.slug))
  )));
  const resolvedIdolSlug = idolOptions.some((idol) => idol.slug === idolSlug)
    ? idolSlug
    : "";

  return {
    officeSlug: resolvedOfficeSlug,
    unitSlug: resolvedUnitSlug,
    idolSlug: resolvedIdolSlug,
    unitOptions,
    idolOptions,
  };
}

function matchesCatalogIdentityFilters(costume, {
  officeSlug,
  unitMembers,
  idolSlug,
  officeByIdolSlug,
}) {
  if (officeSlug && officeByIdolSlug[costume.idol_slug] !== officeSlug) return false;
  if (unitMembers && !unitMembers.includes(costume.idol_slug)) return false;
  if (idolSlug && costume.idol_slug !== idolSlug) return false;
  return true;
}

// ---- 状態 ----
let allCostumes = [];
// slug -> アイドルマスタ（idols.json）
let idolBySlug = {};
// slug -> ユニットマスタ（units.json）
let unitsBySlug = {};
// idol_slug -> 所属ユニット配列（units.json の member_slugs から逆引き）
let unitsByMemberSlug = {};
// slug -> 事務所マスタ（offices.json）
let officesBySlug = {};
// idol_slug / unit_slug -> 所属事務所slug（offices.json から逆引き）
let officeByIdolSlug = {};
let officeByUnitSlug = {};
let allIdols = [];

// ---- DOM ----
const searchBox = document.getElementById("search-box");
const filterOffice = document.getElementById("filter-office");
const filterUnit = document.getElementById("filter-unit");
const filterIdol = document.getElementById("filter-idol");
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

// 検索用の正規化。入力側・データ側の両方に必ず同じ関数を通すこと。
// NFKC で全角/半角・互換文字をそろえ、小文字化し、空白と検索の邪魔になる記号を除去する。
// これにより「日々樹 渉」==「日々樹渉」、「Ra*bits」==「rabits」、
// 「Special for Princess!」==「specialforprincess」が別名なしでも一致する。
function normalizeForSearch(str) {
  if (str == null) return "";
  return String(str)
    .normalize("NFKC")
    .toLowerCase()
    // ASCII の記号・空白（* ! - _ / . , など）をまとめて除去
    .replace(/[\s!-/:-@[-`{-~]/g, "")
    // 日本語などの記号（中黒・読点・句点・各種括弧・波ダッシュ・ハイフン類）
    .replace(/[・、。，．「」『』【】〔〕〈〉《》（）〜～‐‑‒–—―]/g, "");
}

// idol_slug -> 表示用アイドル名。未登録なら壊さずフォールバック表示。
function idolName(idolSlug) {
  const idol = idolBySlug[idolSlug];
  return idol ? idol.name : "不明なアイドル";
}

// idol_slug -> 所属ユニット名（複数所属は「・」区切り）。未所属なら空文字。
function unitLabelForIdol(idolSlug) {
  const units = unitsByMemberSlug[idolSlug] || [];
  return units.map((u) => u.name).join("・");
}

// カード・モーダル共通の「アイドル名｜ユニット名」表示文字列。
function idolUnitLabel(idolSlug) {
  const name = idolName(idolSlug);
  const unitLabel = unitLabelForIdol(idolSlug);
  return unitLabel ? `${name}｜${unitLabel}` : name;
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
  idol.textContent = idolUnitLabel(c.idol_slug);

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
  const q = normalizeForSearch(searchBox.value);
  const officeSlug = filterOffice.value;
  const unitSlug = filterUnit.value;
  const idolSlug = filterIdol.value;
  const unlock = filterUnlock.value;
  const onlyRequestable = filterRequestable.checked;

  // 選択中ユニットの所属メンバー一覧（未選択なら null = 絞り込みなし）
  let unitMembers = null;
  if (unitSlug) {
    const unit = unitsBySlug[unitSlug];
    if (unit) {
      unitMembers = Array.isArray(unit.member_slugs) ? unit.member_slugs : [];
    } else {
      // 不明なslug：ページは壊さず0件扱い
      console.warn(`ユニットslug "${unitSlug}" が units.json に見つかりません。`);
      unitMembers = [];
    }
  }

  return allCostumes.filter((c) => {
    if (!matchesCatalogIdentityFilters(c, {
      officeSlug,
      unitMembers,
      idolSlug,
      officeByIdolSlug,
    })) return false;
    if (onlyRequestable && !c.requestable) return false;
    if (unlock && c.unlock_status !== unlock) return false;

    // _search は init 時に事前構築した正規化済み検索文字列
    if (q && !(c._search || "").includes(q)) return false;
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

  resultCount.textContent = `表示：${list.length.toLocaleString("ja-JP")}件 / 登録：${allCostumes.length.toLocaleString("ja-JP")}件`;
}

// ---- モーダル ----
function buildRequestText(c) {
  // 例: 渉：Caelum（表示名の末尾トークンを短縮名として使う）
  const full = idolName(c.idol_slug);
  const shortName = full.split(/\s+/).pop() || full;
  return `${shortName}：${c.costume_name}`;
}

function openModal(c) {
  modalBody.innerHTML = "";

  const purpose = document.createElement("p");
  purpose.className = "modal-purpose";
  purpose.textContent = "配信リクエスト用 衣装確認";
  modalBody.appendChild(purpose);

  const title = document.createElement("h2");
  title.id = "modal-title";
  title.textContent = c.costume_name;
  modalBody.appendChild(title);

  const idol = document.createElement("p");
  idol.className = "modal-idol";
  idol.textContent = idolUnitLabel(c.idol_slug);
  modalBody.appendChild(idol);

  // メタ
  const meta = document.createElement("div");
  meta.className = "modal-meta";
  [
    ["所持状況", labelUnlock(c.unlock_status)],
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
      wrap.appendChild(makeImageBlock(c.idol_slug, imgs.icon, "ミニアイコン", "icon"));
    }
    if (hasFront) {
      wrap.appendChild(makeImageBlock(c.idol_slug, imgs.front, "正面", "body"));
    }
    if (hasBack) {
      wrap.appendChild(makeImageBlock(c.idol_slug, imgs.back, "背面", "body"));
    }
    modalBody.appendChild(wrap);
  } else {
    // アイコンだけは出す（あれば）。固定上限で識別用サイズを維持する。
    if (imgs.icon) {
      const wrap = document.createElement("div");
      wrap.className = "modal-images";
      wrap.appendChild(makeImageBlock(c.idol_slug, imgs.icon, "ミニアイコン", "icon"));
      modalBody.appendChild(wrap);
    }
    const note = document.createElement("div");
    note.className = "no-image-note";
    note.textContent = `${labelUnlock(c.unlock_status)}のため着用画像はありません。`;
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

function makeImageBlock(idolSlug, filename, labelText, imageType) {
  const block = document.createElement("div");
  block.className = `modal-image-block modal-image-${imageType}`;

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
filterOffice.addEventListener("change", () => {
  syncLinkedFilterOptions();
  render();
});
filterUnit.addEventListener("change", () => {
  syncLinkedFilterOptions();
  render();
});
filterIdol.addEventListener("change", render);
filterUnlock.addEventListener("change", render);
filterRequestable.addEventListener("change", render);

// ---- 初期化 ----
async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status} (${url})`);
  return res.json();
}

// idols.json / units.json / offices.json から lookup 用マップを構築する。
function buildMaps(idolsData, unitsData, officesData) {
  idolBySlug = {};
  unitsBySlug = {};
  unitsByMemberSlug = {};
  officesBySlug = {};
  officeByIdolSlug = {};
  officeByUnitSlug = {};

  allIdols = Array.isArray(idolsData.idols) ? idolsData.idols : [];
  allIdols.forEach((idol) => {
    if (idol && idol.slug) idolBySlug[idol.slug] = idol;
  });

  const units = Array.isArray(unitsData.units) ? unitsData.units : [];
  units.forEach((unit) => {
    if (!unit || !unit.slug) return;
    unitsBySlug[unit.slug] = unit;
    const members = Array.isArray(unit.member_slugs) ? unit.member_slugs : [];
    members.forEach((memberSlug) => {
      if (!unitsByMemberSlug[memberSlug]) unitsByMemberSlug[memberSlug] = [];
      unitsByMemberSlug[memberSlug].push(unit);
    });
  });

  const offices = Array.isArray(officesData.offices) ? officesData.offices : [];
  const officeIndex = buildOfficeIndex(offices);
  officesBySlug = officeIndex.officesBySlug;
  officeByIdolSlug = officeIndex.officeByIdolSlug;
  officeByUnitSlug = officeIndex.officeByUnitSlug;

  if (officeIndex.duplicateIdolSlugs.length > 0) {
    console.warn("offices.json の idol_slug が複数事務所に登録されています:", officeIndex.duplicateIdolSlugs);
  }
  if (officeIndex.duplicateUnitSlugs.length > 0) {
    console.warn("offices.json の unit_slug が複数事務所に登録されています:", officeIndex.duplicateUnitSlugs);
  }
}

// 公開UIで利用者が確認できる文字列だけから、正規化済み検索文字列を作る。
function buildCostumeSearchText(c, idol, units) {
  const parts = [
    c.costume_name,
    c.note_public,
  ];
  if (Array.isArray(c.tags)) parts.push(...c.tags);
  if (idol) parts.push(idol.name);
  units.forEach((u) => parts.push(u.name));

  // 各パートを個別に正規化してから空白で連結する。
  // 正規化後の検索クエリには空白が含まれないため、空白は安全な区切り文字になる。
  return parts.map(normalizeForSearch).join(" ");
}

// 各衣装レコードに、正規化済みの検索文字列 _search を1回だけ事前構築する。
function buildSearchIndex() {
  allCostumes.forEach((c) => {
    const idol = idolBySlug[c.idol_slug];
    const units = unitsByMemberSlug[c.idol_slug] || [];
    c._search = buildCostumeSearchText(c, idol, units);
  });
}

function replaceSelectOptions(select, options, allLabel) {
  const previousValue = select.value;
  select.replaceChildren();

  const allOption = document.createElement("option");
  allOption.value = "";
  allOption.textContent = allLabel;
  select.appendChild(allOption);

  options.forEach((item) => {
    const opt = document.createElement("option");
    opt.value = item.slug;
    opt.textContent = item.name;
    select.appendChild(opt);
  });

  select.value = options.some((item) => item.slug === previousValue)
    ? previousValue
    : "";
}

function buildOfficeOptions() {
  replaceSelectOptions(
    filterOffice,
    sortMastersCanonical(Object.values(officesBySlug)),
    "すべての事務所"
  );
}

function syncLinkedFilterOptions() {
  const linked = resolveLinkedFilterOptions({
    offices: Object.values(officesBySlug),
    idols: allIdols,
    unitsBySlug,
    officeByIdolSlug,
    officeByUnitSlug,
    officeSlug: filterOffice.value,
    unitSlug: filterUnit.value,
    idolSlug: filterIdol.value,
  });

  filterOffice.value = linked.officeSlug;
  replaceSelectOptions(filterUnit, linked.unitOptions, "すべてのユニット");
  filterUnit.value = linked.unitSlug;
  replaceSelectOptions(filterIdol, linked.idolOptions, "すべてのアイドル");
  filterIdol.value = linked.idolSlug;
}

// costumes.json の idol_slug が idols.json に無い場合は警告（ページは壊さない）。
function warnUnknownSlugs() {
  allCostumes.forEach((c) => {
    if (!idolBySlug[c.idol_slug]) {
      console.warn(
        `costumes.json の idol_slug "${c.idol_slug}" が idols.json に見つかりません（表示は「不明なアイドル」になります）。`
      );
    }
  });

  Object.keys(idolBySlug).forEach((idolSlug) => {
    if (!officeByIdolSlug[idolSlug]) {
      console.warn(`idols.json の idol_slug "${idolSlug}" が offices.json に見つかりません。`);
    }
  });
  Object.keys(unitsBySlug).forEach((unitSlug) => {
    if (!officeByUnitSlug[unitSlug]) {
      console.warn(`units.json の unit_slug "${unitSlug}" が offices.json に見つかりません。`);
    }
  });
}

async function init() {
  // 念のため：初期表示ではモーダルを必ず非表示にする
  modalOverlay.hidden = true;
  document.body.style.overflow = "";

  try {
    const [costumesData, idolsData, unitsData, officesData] = await Promise.all([
      fetchJson(DATA_URL),
      fetchJson(IDOLS_URL),
      fetchJson(UNITS_URL),
      fetchJson(OFFICES_URL),
    ]);
    allCostumes = Array.isArray(costumesData.costumes) ? costumesData.costumes : [];
    buildMaps(idolsData, unitsData, officesData);
    sortCostumesCanonical(allCostumes, idolBySlug);
    buildOfficeOptions();
    syncLinkedFilterOptions();
    warnUnknownSlugs();
    buildSearchIndex();
  } catch (err) {
    cardGrid.innerHTML = "";
    emptyMessage.hidden = false;
    emptyMessage.textContent =
      "データの読み込みに失敗しました。ローカル確認は python -m http.server を使ってください（index.html を直接開くと fetch がブロックされます）。";
    resultCount.textContent = "";
    console.error("データ（costumes/idols/units）の読み込みに失敗:", err);
    return;
  }
  render();
}

init();
