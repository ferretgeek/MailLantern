"use strict";

const state = { token: "", messages: [], demo: false, busy: false };
const themes = new Set(["sky", "jade", "sunset", "graphite"]);
const $ = (selector) => document.querySelector(selector);
const elements = {
  gate: $("#access-gate"), accessForm: $("#access-form"), accessToken: $("#access-token"), gateError: $("#gate-error"),
  scanForm: $("#scan-form"), scanButton: $("#scan-button"), password: $("#app-password"), reveal: $("#reveal-password"),
  results: $("#results"), status: $("#status"), count: $("#result-count"), clear: $("#clear-results"),
  privacy: $("#privacy-toggle"), themeTrigger: $("#theme-trigger"), themeMenu: $("#theme-menu"), toast: $("#toast"),
  mode: $("#mode-label"), provider: $("#provider-label"), themeColor: $("meta[name='theme-color']"),
};

function readFragmentToken() {
  const params = new URLSearchParams(location.hash.slice(1));
  const token = params.get("token") || "";
  if (token) history.replaceState(null, "", location.pathname + location.search);
  return token;
}

function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${state.token}`);
  if (options.body) headers.set("Content-Type", "application/json");
  return fetch(path, { ...options, headers, credentials: "same-origin" }).then(async (response) => {
    const body = await response.json().catch(() => ({ error: "服务返回了无法识别的响应" }));
    if (!response.ok) throw new Error(body.error || `请求失败（${response.status}）`);
    return body;
  });
}

function applyTheme(theme) {
  const next = themes.has(theme) ? theme : "sky";
  document.documentElement.setAttribute("data-theme", next);
  try { localStorage.setItem("mail-lantern-theme", next); } catch { /* Theme persistence is optional. */ }
  elements.themeColor.setAttribute("content", next === "graphite" ? "#17191d" : next === "jade" ? "#eef9f3" : next === "sunset" ? "#fff5ed" : "#edf7ff");
  document.querySelectorAll("[data-theme-choice]").forEach((button) => {
    button.setAttribute("aria-checked", String(button.dataset.themeChoice === next));
  });
}

function toggleThemeMenu(force) {
  const open = typeof force === "boolean" ? force : elements.themeMenu.hidden;
  elements.themeMenu.hidden = !open;
  elements.themeTrigger.setAttribute("aria-expanded", String(open));
}

let toastTimer;
function toast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.add("is-visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => elements.toast.classList.remove("is-visible"), 2400);
}

function dateLabel(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "时间未知";
  const delta = Math.max(0, Date.now() - date.getTime());
  const minutes = Math.floor(delta / 60000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  return new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(date);
}

function messageCard(message, index) {
  const article = document.createElement("article");
  article.className = "message-card";
  article.style.setProperty("--delay", `${index * 55}ms`);

  const top = document.createElement("div"); top.className = "message-top";
  const label = document.createElement("span"); label.className = "code-label"; label.textContent = "验证码";
  const time = document.createElement("time"); time.dateTime = String(message.receivedAt || ""); time.textContent = dateLabel(message.receivedAt);
  top.append(label, time);

  const codeRow = document.createElement("div"); codeRow.className = "code-row";
  const code = document.createElement("strong"); code.className = "verification-code"; code.textContent = String(message.code || "—");
  const copy = document.createElement("button"); copy.type = "button"; copy.className = "copy-button"; copy.textContent = "复制";
  copy.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(String(message.code || "")); copy.textContent = "已复制"; toast("验证码已复制"); }
    catch { toast("复制失败，请手动选择验证码"); }
    setTimeout(() => { copy.textContent = "复制"; }, 1400);
  });
  codeRow.append(code, copy);

  const subject = document.createElement("h3"); subject.textContent = String(message.subject || "未命名验证邮件");
  const details = document.createElement("dl"); details.className = "message-details sensitive-result";
  [["来自", message.sender], ["送达", message.recipient]].forEach(([term, value]) => {
    const row = document.createElement("div"); const dt = document.createElement("dt"); const dd = document.createElement("dd");
    dt.textContent = term; dd.textContent = String(value || "未知"); row.append(dt, dd); details.append(row);
  });
  article.append(top, codeRow, subject, details);
  return article;
}

function renderMessages(messages) {
  state.messages = Array.isArray(messages) ? messages : [];
  elements.results.replaceChildren(...state.messages.map(messageCard));
  const hasMessages = state.messages.length > 0;
  elements.status.hidden = hasMessages;
  elements.status.className = hasMessages ? "status-card" : "status-card empty-state";
  if (!hasMessages) {
    elements.status.replaceChildren();
    const icon = document.createElement("span"); icon.className = "empty-lantern"; icon.setAttribute("aria-hidden", "true");
    const title = document.createElement("strong"); title.textContent = "没有找到验证码";
    const note = document.createElement("p"); note.textContent = "可以扩大时间范围，或确认目标收件地址是否正确。";
    elements.status.append(icon, title, note);
  }
  elements.count.textContent = hasMessages ? `${state.messages.length} 条结果` : "没有结果";
  elements.clear.disabled = !hasMessages;
}

function showLoading() {
  elements.status.hidden = false;
  elements.status.className = "status-card loading-state";
  const spinner = document.createElement("span"); spinner.className = "spinner"; spinner.setAttribute("aria-hidden", "true");
  const title = document.createElement("strong"); title.textContent = "正在沿着灯光寻找…";
  const note = document.createElement("p"); note.textContent = "只读查看指定范围内的最近邮件。";
  elements.status.replaceChildren(spinner, title, note);
  elements.results.replaceChildren(); elements.count.textContent = "扫描中"; elements.clear.disabled = true;
}

function showError(message) {
  elements.status.hidden = false; elements.status.className = "status-card error-state";
  const icon = document.createElement("span"); icon.className = "error-mark"; icon.textContent = "!";
  const title = document.createElement("strong"); title.textContent = "这次没有点亮";
  const note = document.createElement("p"); note.textContent = message;
  elements.status.replaceChildren(icon, title, note); elements.count.textContent = "扫描失败";
}

async function bootstrap() {
  try {
    const data = await api("/api/bootstrap");
    state.demo = Boolean(data.demo);
    elements.mode.textContent = state.demo ? "演示模式 · 全部为虚构数据" : "本地优先 · 只读连接";
    elements.provider.textContent = data.provider?.name || "iCloud Mail";
    elements.gate.hidden = true;
    if (state.demo) {
      document.body.classList.add("is-demo");
      renderMessages(data.messages || []);
      toast("已载入安全的演示数据");
    }
  } catch (error) {
    state.token = ""; elements.gate.hidden = false; elements.gateError.textContent = "令牌无效或服务不可用。";
  }
}

elements.accessForm.addEventListener("submit", (event) => {
  event.preventDefault(); state.token = elements.accessToken.value.trim(); elements.accessToken.value = ""; elements.gateError.textContent = ""; bootstrap();
});

elements.scanForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.busy) return;
  if (!elements.scanForm.reportValidity()) return;
  state.busy = true; elements.scanButton.disabled = true; elements.scanButton.classList.add("is-busy"); showLoading();
  const data = Object.fromEntries(new FormData(elements.scanForm));
  data.latest = Number(data.latest); data.sinceMinutes = Number(data.sinceMinutes);
  try { const result = await api("/api/scan", { method: "POST", body: JSON.stringify(data) }); renderMessages(result.messages); }
  catch (error) { showError(error instanceof Error ? error.message : "未知错误，请稍后重试。"); }
  finally { elements.password.value = ""; elements.password.type = "password"; elements.reveal.textContent = "显示"; state.busy = false; elements.scanButton.disabled = false; elements.scanButton.classList.remove("is-busy"); }
});

elements.reveal.addEventListener("click", () => {
  const reveal = elements.password.type === "password"; elements.password.type = reveal ? "text" : "password"; elements.reveal.textContent = reveal ? "隐藏" : "显示"; elements.reveal.setAttribute("aria-label", reveal ? "隐藏密码" : "显示密码");
});
elements.privacy.addEventListener("click", () => {
  const enabled = document.body.classList.toggle("is-private"); elements.privacy.setAttribute("aria-pressed", String(enabled)); toast(enabled ? "隐私遮罩已开启" : "隐私遮罩已关闭");
});
elements.clear.addEventListener("click", () => { state.messages = []; elements.results.replaceChildren(); elements.status.hidden = false; elements.count.textContent = "已清空"; elements.clear.disabled = true; });
elements.themeTrigger.addEventListener("click", () => toggleThemeMenu());
document.querySelectorAll("[data-theme-choice]").forEach((button) => {
  button.addEventListener("click", () => {
    const selected = button.getAttribute("data-theme-choice") || "sky";
    applyTheme(selected);
    toggleThemeMenu(false);
    toast(`已切换至${button.querySelector("span")?.textContent || "晴空"}主题`);
  });
});
document.addEventListener("click", (event) => { if (!event.target.closest(".theme-control")) toggleThemeMenu(false); });
document.addEventListener("keydown", (event) => { if (event.key === "Escape") toggleThemeMenu(false); });

let storedTheme = "sky";
try { storedTheme = localStorage.getItem("mail-lantern-theme") || "sky"; } catch { /* Use the default. */ }
applyTheme(storedTheme);
state.token = readFragmentToken();
if (state.token) bootstrap(); else { elements.gate.hidden = false; setTimeout(() => elements.accessToken.focus(), 0); }
