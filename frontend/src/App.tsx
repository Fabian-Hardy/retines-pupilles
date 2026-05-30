const shellSections = [
  { label: "Accueil", state: "Actif" },
  { label: "Modules", state: "Prévu" },
  { label: "Paramètres", state: "Prévu" },
] as const;

function App() {
  return (
    <main className="app-shell">
      <aside className="sidebar" aria-label="Navigation principale">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            RP
          </span>
          <div>
            <p className="brand-kicker">Application interne</p>
            <h1>Rétines & Pupilles</h1>
          </div>
        </div>

        <nav className="nav-list" aria-label="Sections">
          {shellSections.map((section) => (
            <a
              aria-current={section.state === "Actif" ? "page" : undefined}
              className="nav-item"
              href="#"
              key={section.label}
            >
              <span>{section.label}</span>
              <small>{section.state}</small>
            </a>
          ))}
        </nav>
      </aside>

      <section className="workspace" aria-labelledby="shell-title">
        <header className="workspace-header">
          <div>
            <p className="eyebrow">TASK-012</p>
            <h2 id="shell-title">Socle frontend prêt</h2>
          </div>
          <span className="status-pill">React + TypeScript</span>
        </header>

        <section className="placeholder-panel" aria-label="Écran temporaire">
          <p className="panel-kicker">Rétines & Pupilles</p>
          <h3>Shell applicatif initialisé</h3>
          <p>
            La base Vite, React et TypeScript est en place pour accueillir les
            futurs écrans sans activer de parcours métier.
          </p>
        </section>
      </section>
    </main>
  );
}

export default App;
