const ALL_PORTALS = "全部系统";

const portals = [
  { name: ALL_PORTALS, description: "查看所有已接入系统入口" },
  { name: "运营端", description: "运营、数据、内容和日常协作系统" },
  { name: "采购端", description: "采购计划、供应商、合同和库存相关系统" },
  { name: "销售端", description: "客户、商机、订单和回款相关系统" },
  { name: "财务端", description: "费用、预算、结算和财务报表系统" },
  { name: "管理端", description: "组织、人事、权限和平台配置系统" }
];

let applications = [];
let currentUser = null;

const state = {
  portal: ALL_PORTALS,
  addingPortal: "运营端",
  editingAppId: null,
  isAdmin: false,
  query: ""
};

const addCurrentApp = document.querySelector("#addCurrentApp");
const appDialog = document.querySelector("#appDialog");
const appForm = document.querySelector("#appForm");
const appGrid = document.querySelector("#appGrid");
const appNameInput = document.querySelector("#appNameInput");
const appUrlInput = document.querySelector("#appUrlInput");
const cancelDialog = document.querySelector("#cancelDialog");
const closeDialog = document.querySelector("#closeDialog");
const currentPortalApps = document.querySelector("#currentPortalApps");
const dialogEyebrow = document.querySelector("#dialogEyebrow");
const dialogTitle = document.querySelector("#dialogTitle");
const pageTitle = document.querySelector("#pageTitle");
const portalAppCount = document.querySelector("#portalAppCount");
const portalCount = document.querySelector("#portalCount");
const portalDescription = document.querySelector("#portalDescription");
const portalNav = document.querySelector("#portalNav");
const searchInput = document.querySelector("#searchInput");
const sectionTitle = document.querySelector("#sectionTitle");
const saveAppButton = document.querySelector("#saveAppButton");
const totalApps = document.querySelector("#totalApps");
const currentUserName = document.querySelector("#currentUserName");
const userAvatar = document.querySelector("#userAvatar");

function isServedByHttp() {
  return location.protocol === "http:" || location.protocol === "https:";
}

function getCurrentUserName() {
  return currentUser?.name || "";
}

function getCurrentUserPayload() {
  return {
    name: currentUser?.name || "",
    openId: currentUser?.openId || "",
    unionId: currentUser?.unionId || "",
    email: currentUser?.email || "",
    mobile: currentUser?.mobile || ""
  };
}

function setCurrentUser(user) {
  currentUser = user;
  const name = user.name || "飞书用户";
  currentUserName.textContent = name;
  userAvatar.textContent = name.slice(0, 1);
}

function clearFeishuCodeFromUrl() {
  const url = new URL(location.href);
  url.searchParams.delete("code");
  url.searchParams.delete("state");
  history.replaceState({}, document.title, url.toString());
}

async function loadFeishuUser() {
  if (!isServedByHttp()) {
    currentUserName.textContent = "本地预览";
    render();
    return;
  }

  const url = new URL(location.href);
  const code = url.searchParams.get("code");
  const cachedUser = sessionStorage.getItem("feishu_user");

  if (cachedUser) {
    setCurrentUser(JSON.parse(cachedUser));
    await loadAdminPermission();
    return;
  }

  try {
    if (code) {
      currentUserName.textContent = "正在获取用户";
      const response = await fetch(`/api/feishu/me?code=${encodeURIComponent(code)}`);
      const payload = await response.json();

      if (!response.ok) throw new Error(payload.error || "获取用户失败");

      sessionStorage.setItem("feishu_user", JSON.stringify(payload));
      setCurrentUser(payload);
      clearFeishuCodeFromUrl();
      await loadAdminPermission();
      return;
    }

    const response = await fetch("/api/feishu/config");
    const payload = await response.json();

    if (!response.ok) {
      currentUserName.textContent = "未配置飞书";
      return;
    }

    location.href = payload.authUrl;
  } catch (error) {
    currentUserName.textContent = "获取用户失败";
    console.error(error);
  }
}

async function loadAdminPermission() {
  state.isAdmin = false;

  try {
    const response = await fetch("/api/me/permissions", {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify({ operator: getCurrentUserPayload() })
    });
    const payload = await response.json();

    if (!response.ok) throw new Error(payload.error || "读取权限失败");

    state.isAdmin = Boolean(payload.isAdmin);
  } catch (error) {
    state.isAdmin = false;
    console.error(error);
  } finally {
    render();
  }
}

async function loadApplications() {
  try {
    const response = await fetch("/api/apps");
    const payload = await response.json();

    if (!response.ok) throw new Error(payload.error || "读取应用失败");

    applications = payload.apps || [];
    render();
  } catch (error) {
    appGrid.innerHTML = `<div class="empty-state">读取应用失败：${error.message}</div>`;
    console.error(error);
  }
}

async function createApplication(app) {
  const response = await fetch("/api/apps", {
    method: "POST",
    headers: { "Content-Type": "application/json; charset=utf-8" },
    body: JSON.stringify({ ...app, operator: getCurrentUserPayload() })
  });
  const payload = await response.json();

  if (!response.ok) throw new Error(payload.error || "保存应用失败");

  return payload.app;
}

async function updateApplication(appId, app) {
  const response = await fetch(`/api/apps/${encodeURIComponent(appId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json; charset=utf-8" },
    body: JSON.stringify({ ...app, operator: getCurrentUserPayload() })
  });
  const payload = await response.json();

  if (!response.ok) throw new Error(payload.error || "更新应用失败");

  return payload.app;
}

async function deleteApplication(appId) {
  const response = await fetch(`/api/apps/${encodeURIComponent(appId)}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json; charset=utf-8" },
    body: JSON.stringify({ operator: getCurrentUserPayload() })
  });
  const payload = await response.json();

  if (!response.ok) throw new Error(payload.error || "删除应用失败");

  return payload;
}

async function openApplication(app) {
  const response = await fetch(app.url, {
    method: "POST",
    mode: "cors",
    headers: { "Content-Type": "application/json; charset=utf-8" },
    body: JSON.stringify({
      appId: app.id,
      appName: app.name,
      portal: app.portal,
      user: getCurrentUserPayload()
    })
  });

  const payload = await response.json();

  if (!response.ok) throw new Error(payload.error || "目标系统接口请求失败");
  if (!payload.redirectUrl) throw new Error("目标系统未返回 redirectUrl");

  window.open(payload.redirectUrl, "_blank", "noopener,noreferrer");
}

function normalizeUrl(url) {
  const trimmedUrl = url.trim();
  if (!trimmedUrl) return "";
  if (/^https?:\/\//i.test(trimmedUrl)) return trimmedUrl;
  return `https://${trimmedUrl}`;
}

function getPortalApps(portalName = state.portal) {
  if (portalName === ALL_PORTALS) return applications;
  return applications.filter((app) => app.portal === portalName);
}

function matchesQuery(app) {
  const query = state.query.trim().toLowerCase();
  if (!query) return true;
  return [app.name, app.url, app.portal].join(" ").toLowerCase().includes(query);
}

function getVisibleApps() {
  return getPortalApps().filter(matchesQuery);
}

function getCurrentPortal() {
  return portals.find((portal) => portal.name === state.portal) || portals[0];
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function openAddDialog(portalName) {
  if (!state.isAdmin) return;
  state.addingPortal = portalName === ALL_PORTALS ? "运营端" : portalName;
  state.editingAppId = null;
  dialogEyebrow.textContent = "新增应用";
  dialogTitle.textContent = `添加到${state.addingPortal}`;
  saveAppButton.textContent = "保存应用";
  appForm.reset();
  appDialog.showModal();
  appNameInput.focus();
}

function openEditDialog(app) {
  if (!state.isAdmin) return;
  state.addingPortal = app.portal;
  state.editingAppId = app.id;
  dialogEyebrow.textContent = "编辑应用";
  dialogTitle.textContent = `修改${app.portal}应用`;
  saveAppButton.textContent = "保存修改";
  appNameInput.value = app.name;
  appUrlInput.value = app.url;
  appDialog.showModal();
  appNameInput.focus();
  appNameInput.select();
}

function renderPortalNav() {
  portalNav.innerHTML = portals
    .map((portal) => {
      const count = getPortalApps(portal.name).length;
      const addButton =
        portal.name === ALL_PORTALS || !state.isAdmin
          ? ""
          : `<button class="add-portal-app" type="button" data-add-portal="${portal.name}" aria-label="添加到${portal.name}">+</button>`;

      return `
        <div class="nav-row ${portal.name === state.portal ? "active" : ""}">
          <button class="nav-item" type="button" data-portal="${portal.name}">
            <span>${portal.name}</span>
            <strong>${count}</strong>
          </button>
          ${addButton}
        </div>
      `;
    })
    .join("");
}

function renderApps() {
  const visibleApps = getVisibleApps();
  const portalApps = getPortalApps();
  const currentPortal = getCurrentPortal();

  totalApps.textContent = applications.length;
  currentPortalApps.textContent = portalApps.length;
  portalAppCount.textContent = portalApps.length;
  portalCount.textContent = portals.length - 1;
  portalDescription.textContent = currentPortal.description;
  pageTitle.textContent = state.portal === ALL_PORTALS ? "中控平台" : state.portal;
  sectionTitle.textContent = state.portal;
  addCurrentApp.textContent =
    state.portal === ALL_PORTALS ? "选择端口添加" : `添加到${state.portal}`;
  addCurrentApp.hidden = !state.isAdmin;
  addCurrentApp.disabled = !state.isAdmin || state.portal === ALL_PORTALS;

  if (visibleApps.length === 0) {
    const message =
      state.query.trim() === ""
        ? state.isAdmin
          ? "当前端还没有应用，点击左侧加号添加"
          : "当前端还没有应用"
        : "没有找到匹配的应用";
    appGrid.innerHTML = `<div class="empty-state">${message}</div>`;
    return;
  }

  appGrid.innerHTML = visibleApps
    .map(
      (app) => {
        const appId = escapeHtml(app.id);
        const appName = escapeHtml(app.name);
        const appUrl = escapeHtml(app.url);
        const appPortal = escapeHtml(app.portal);
        const initials = escapeHtml(app.initials || app.name.slice(0, 2));
        const appActions = state.isAdmin
          ? `
            <div class="app-actions" aria-label="应用管理">
              <button class="icon-button small" type="button" data-edit-app="${appId}" aria-label="编辑${appName}" title="编辑">✎</button>
              <button class="icon-button small danger" type="button" data-delete-app="${appId}" aria-label="删除${appName}" title="删除">×</button>
            </div>
          `
          : "";

        return `
        <article class="app-card" data-app-id="${appId}">
          <div class="app-topline">
            <span class="app-icon">${initials}</span>
            <span class="app-badge">${appPortal}</span>
          </div>
          <h3>${appName}</h3>
          <p>${appUrl}</p>
          <div class="app-footer">
            <button class="open-app-action" type="button" data-open-app="${appId}">
              <span>发送用户信息并打开</span>
              <span>↗</span>
            </button>
            ${appActions}
          </div>
        </article>
      `;
      }
    )
    .join("");
}

function render() {
  renderPortalNav();
  renderApps();
}

portalNav.addEventListener("click", (event) => {
  const addButton = event.target.closest("[data-add-portal]");
  if (addButton) {
    openAddDialog(addButton.dataset.addPortal);
    return;
  }

  const button = event.target.closest("[data-portal]");
  if (!button) return;

  state.portal = button.dataset.portal;
  render();
});

appGrid.addEventListener("click", async (event) => {
  const editButton = event.target.closest("[data-edit-app]");
  if (editButton) {
    if (!state.isAdmin) return;
    const app = applications.find((item) => String(item.id) === editButton.dataset.editApp);
    if (app) openEditDialog(app);
    return;
  }

  const deleteButton = event.target.closest("[data-delete-app]");
  if (deleteButton) {
    if (!state.isAdmin) return;
    const app = applications.find((item) => String(item.id) === deleteButton.dataset.deleteApp);
    if (!app) return;
    const confirmed = confirm(`确定删除「${app.name}」吗？删除后不会在工作台显示。`);
    if (!confirmed) return;

    deleteButton.disabled = true;
    try {
      await deleteApplication(app.id);
      applications = applications.filter((item) => item.id !== app.id);
      render();
    } catch (error) {
      alert(error.message);
      deleteButton.disabled = false;
    }
    return;
  }

  if (event.target.closest(".app-actions")) return;

  const card = event.target.closest("[data-app-id]");
  if (!card || card.classList.contains("opening")) return;

  const app = applications.find((item) => String(item.id) === card.dataset.appId);
  if (!app) return;

  card.classList.add("opening");
  try {
    await openApplication(app);
  } catch (error) {
    alert(error.message);
  } finally {
    card.classList.remove("opening");
  }
});

searchInput.addEventListener("input", (event) => {
  state.query = event.target.value;
  renderApps();
});

addCurrentApp.addEventListener("click", () => {
  if (!state.isAdmin || state.portal === ALL_PORTALS) return;
  openAddDialog(state.portal);
});

appForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.isAdmin) return;

  const name = appNameInput.value.trim();
  const url = normalizeUrl(appUrlInput.value);
  if (!name || !url) return;

  const submitButton = appForm.querySelector('[type="submit"]');
  submitButton.disabled = true;

  try {
    if (state.editingAppId) {
      const app = await updateApplication(state.editingAppId, { name, url });
      applications = applications.map((item) => (item.id === app.id ? app : item));
      state.portal = app.portal;
    } else {
      const app = await createApplication({
        name,
        url,
        portal: state.addingPortal,
        createdBy: getCurrentUserName()
      });

      applications = [...applications, app];
      state.portal = state.addingPortal;
    }

    state.query = "";
    searchInput.value = "";
    appDialog.close();
    state.editingAppId = null;
    render();
  } catch (error) {
    alert(error.message);
  } finally {
    submitButton.disabled = false;
  }
});

cancelDialog.addEventListener("click", () => appDialog.close());
closeDialog.addEventListener("click", () => appDialog.close());

render();
loadApplications();
loadFeishuUser();
