type NavItem = { label: string; icon: string };
type NavGroup = { label: string; items: NavItem[] };

const groups: NavGroup[] = [
  { label: "Workspace", items: [{ label: "Dashboard", icon: "dashboard" }] },
  {
    label: "Resource Operations",
    items: [
      { label: "Resource Monitoring", icon: "monitor" },
      { label: "Workloads", icon: "layers" },
      { label: "Predictions", icon: "chart" },
    ],
  },
  {
    label: "Agent Intelligence",
    items: [
      { label: "Agent Decisions", icon: "nodes" },
      { label: "Optimization", icon: "sliders" },
      { label: "Experiments", icon: "flask" },
      { label: "Decision Logs", icon: "list" },
    ],
  },
  { label: "System", items: [{ label: "Settings", icon: "settings" }] },
];

const paths: Record<string, string> = {
  dashboard: "M3 3h7v7H3z M14 3h7v7h-7z M14 14h7v7h-7z M3 14h7v7H3z",
  monitor: "M3 12h4l3-8 4 16 3-8h4",
  layers: "m12 3 9 5-9 5-9-5 9-5z M3 12l9 5 9-5 M3 16l9 5 9-5",
  chart: "M4 19V5 M4 19h17 M8 15l4-4 3 2 5-7",
  nodes: "M12 3v5 M5 8h14 M5 8v5 M19 8v5 M12 8v5 M5 13h14 M5 13v6 M12 13v6 M19 13v6",
  sliders: "M4 6h9 M17 6h3 M4 12h3 M11 12h9 M4 18h9 M17 18h3 M13 4v4 M9 10v4 M13 16v4",
  flask: "M9 3h6 M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3 M8 14h8",
  list: "M8 6h13 M8 12h13 M8 18h13 M3 6h.01 M3 12h.01 M3 18h.01",
  settings: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-1.7 2.9-.2-.1a1.7 1.7 0 0 0-1.9.1l-.2.1h-3.4l-.1-.2a1.7 1.7 0 0 0-1.5-1l-.2.1-2.9-1.7.1-.2a1.7 1.7 0 0 0-.1-1.9l-.1-.2v-3.4l.2-.1a1.7 1.7 0 0 0 1-1.5l-.1-.2 1.7-2.9.2.1a1.7 1.7 0 0 0 1.9-.1l.2-.1h3.4l.1.2a1.7 1.7 0 0 0 1.5 1l.2-.1 2.9 1.7-.1.2a1.7 1.7 0 0 0 .1 1.9l.1.2v3.4z",
};

function NavIcon({ name }: { name: string }) {
  return (
    <span className="nav-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24"><path d={paths[name]} /></svg>
    </span>
  );
}

export default function Sidebar({
  page,
  setPage,
}: {
  page: string;
  setPage: (value: string) => void;
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none">
            <path d="M12 3 4 7.5v9L12 21l8-4.5v-9L12 3Z" stroke="currentColor" strokeWidth="1.7" />
            <path d="m8 9.7 4-2.2 4 2.2v4.6l-4 2.2-4-2.2V9.7Z" stroke="currentColor" strokeWidth="1.5" />
            <path d="M12 7.5v9" stroke="currentColor" strokeWidth="1.3" />
          </svg>
        </div>
        <div className="brand-copy">
          <div className="brand-name">Agentic Resource</div>
          <div className="brand-name">Manager</div>
          <div className="brand-caption">CONTROL PLATFORM</div>
        </div>
      </div>

      <div className="sidebar-divider" />
      <nav className="sidebar-nav" aria-label="Main navigation">
        {groups.map((group) => (
          <div className="nav-group" key={group.label}>
            <div className="nav-group-label">{group.label}</div>
            <div className="nav-list">
              {group.items.map((item) => (
                <button
                  type="button"
                  key={item.label}
                  title={item.label}
                  aria-current={page === item.label ? "page" : undefined}
                  onClick={() => setPage(item.label)}
                  className={"nav-link" + (page === item.label ? " active" : "")}
                >
                  <NavIcon name={item.icon} />
                  <span className="nav-link-label">{item.label}</span>
                </button>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-footer-title">Environment</div>
        <div className="sidebar-footer-row">
          <span className="sidebar-dot" />
          <span className="sidebar-footer-copy">Local simulation active</span>
        </div>
      </div>
    </aside>
  );
}
