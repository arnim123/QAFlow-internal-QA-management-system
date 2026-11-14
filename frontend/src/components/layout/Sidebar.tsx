import { NavLink } from "react-router-dom";

const futureAreas = ["Queue", "Cycles", "Master cases", "Reports", "Settings"] as const;

function navClass(isActive: boolean) {
  return [
    "rounded-md px-3 py-2 text-sm",
    isActive ? "bg-sidebar-accent text-sidebar-accent-foreground" : "hover:bg-sidebar-accent",
  ].join(" ");
}

export function Sidebar() {
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground">
      <div className="px-4 py-5">
        <p className="text-sm font-semibold tracking-tight">QAFlow</p>
        <p className="text-xs text-muted-foreground">Main Fast Trade Technologies</p>
      </div>
      <nav className="flex flex-col gap-1 px-2" aria-label="Primary">
        <NavLink to="/" end className={({ isActive }) => navClass(isActive)}>
          Home
        </NavLink>
        <NavLink to="/templates" className={({ isActive }) => navClass(isActive)}>
          Templates
        </NavLink>
        {futureAreas.map((label) => (
          <span
            key={label}
            aria-disabled="true"
            className="cursor-not-allowed rounded-md px-3 py-2 text-sm text-muted-foreground"
          >
            {label}
          </span>
        ))}
      </nav>
    </aside>
  );
}
