const STORAGE_KEY = "workstation_apps";
const ALL_PORTALS = "全部系统";

const portals = [
  {
    name: ALL_PORTALS,
    description: "查看所有已接入系统入口"
  },
  {
    name: "运营端",
    description: "运营、数据、内容和日常协作系统"
  },
  {
    name: "采购端",
    description: "采购计划、供应商、合同和库存相关系统"
  },
  {
    name: "销售端",
    description: "客户、商机、订单和回款相关系统"
  },
  {
    name: "财务端",
    description: "费用、预算、结算和财务报表系统"
  },
  {
    name: "管理端",
    description: "组织、人事、权限和平台配置系统"
  }
];

let applications = loadApplications();

const state = {
  portal: ALL_PORTALS,
  addingPortal: "运营端",
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
const dialogTitle = document.querySelector("#dialogTitle");
const pageTitle = document.querySelector("#pageTitle");
const portalAppCount = document.querySelector("#portalAppCount");
const portalCount = document.querySelector("#portalCount");
const portalDescription = document.querySelector("#portalDescription");
const portalNav = document.querySelector("#portalNav");
const searchInput = document.querySelector("#searchInput");
const sectionTitle = document.querySelector("#sectionTitle");
const totalApps = document.querySelector("#totalApps");
const currentUserName = document.querySelector("#currentUserName");
const userAvatar = document.querySelector("#userAvatar");

function isServedByHttp() {
  return location.protocol === "http:" || location.protocol === "https:";
}

function setCurrentUser(user) {
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
    return;
  }

  const url = new URL(location.href);
  const code = url.searchParams.get("code");
  const cachedUser = sessionStorage.getItem("feishu_user");

  if (cachedUser) {
    setCurrentUser(JSON.parse(cachedUser));
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

function loadApplications() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
  } catch {
    return [];
  }
}

function saveApplications() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(applications));
}

function normalizeUrl(url) {
  const trimmedUrl = url.trim();
  if (/^https?:\/\//i.test(trimmedUrl)) return trimmedUrl;
  return `https://${trimmedUrl}`;
}

function getAppInitials(name) {
  return name.trim().slice(0, 2).toUpperCase();
}

function createAppId() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
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

function openAddDialog(portalName) {
  state.addingPortal = portalName === ALL_PORTALS ? "运营端" : portalName;
  dialogTitle.textContent = `添加到${state.addingPortal}`;
  appForm.reset();
  appDialog.showModal();
  appNameInput.focus();
}

function renderPortalNav() {
  portalNav.innerHTML = portals
    .map((portal) => {
      const count = getPortalApps(portal.name).length;
      const addButton =
        portal.name === ALL_PORTALS
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
  const realPortalCount = portals.length - 1;

  totalApps.textContent = applications.length;
  currentPortalApps.textContent = portalApps.length;
  portalAppCount.textContent = portalApps.length;
  portalCount.textContent = realPortalCount;
  portalDescription.textContent = currentPortal.description;
  pageTitle.textContent = state.portal === ALL_PORTALS ? "中控平台" : state.portal;
  sectionTitle.textContent = state.portal;
  addCurrentApp.textContent =
    state.portal === ALL_PORTALS ? "选择端口添加" : `添加到${state.portal}`;
  addCurrentApp.disabled = state.portal === ALL_PORTALS;

  if (visibleApps.length === 0) {
    const message =
      state.query.trim() === ""
        ? "当前端还没有应用，点击左侧加号添加"
        : "没有找到匹配的应用";
    appGrid.innerHTML = `<div class="empty-state">${message}</div>`;
    return;
  }

  appGrid.innerHTML = visibleApps
    .map(
      (app) => `
        <a class="app-card" href="${app.url}" target="_blank" rel="noopener noreferrer">
          <div class="app-topline">
            <span class="app-icon">${app.initials}</span>
            <span class="app-badge">${app.portal}</span>
          </div>
          <h3>${app.name}</h3>
          <p>${app.url}</p>
          <div class="app-footer">
            <span>点击打开</span>
            <span>↗</span>
          </div>
        </a>
      `
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

searchInput.addEventListener("input", (event) => {
  state.query = event.target.value;
  renderApps();
});

addCurrentApp.addEventListener("click", () => {
  if (state.portal === ALL_PORTALS) return;
  openAddDialog(state.portal);
});

appForm.addEventListener("submit", (event) => {
  event.preventDefault();

  const name = appNameInput.value.trim();
  const url = normalizeUrl(appUrlInput.value);
  if (!name || !url) return;

  applications = [
    ...applications,
    {
      id: createAppId(),
      name,
      url,
      portal: state.addingPortal,
      initials: getAppInitials(name)
    }
  ];

  saveApplications();
  state.portal = state.addingPortal;
  state.query = "";
  searchInput.value = "";
  appDialog.close();
  render();
});

cancelDialog.addEventListener("click", () => appDialog.close());
closeDialog.addEventListener("click", () => appDialog.close());

render();
loadFeishuUser();
