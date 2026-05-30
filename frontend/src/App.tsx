import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { SessionProvider, isAuthenticationError, useSession } from "./auth/session";

type AppRoute = {
  path: string;
  label: string;
  state: "Actif" | "Prévu";
  title: string;
  kicker: string;
  panelTitle: string;
  panelText: string;
};

type BrowserLocation = {
  pathname: string;
  search: string;
};

const privateRoutes = [
  {
    path: "/",
    label: "Accueil",
    state: "Actif",
    title: "Socle frontend prêt",
    kicker: "TASK-013",
    panelTitle: "Session applicative initialisée",
    panelText:
      "La base Vite, React et TypeScript est reliée à la session backend pour accueillir les futurs écrans authentifiés.",
  },
  {
    path: "/modules",
    label: "Modules",
    state: "Prévu",
    title: "Modules",
    kicker: "À venir",
    panelTitle: "Modules métier",
    panelText:
      "Cet espace reste réservé aux prochains parcours applicatifs authentifiés.",
  },
  {
    path: "/settings",
    label: "Paramètres",
    state: "Prévu",
    title: "Paramètres",
    kicker: "À venir",
    panelTitle: "Paramètres applicatifs",
    panelText:
      "Les réglages seront activés dans une tâche dédiée sans modifier le modèle de session.",
  },
] as const;

function normalizePathname(pathname: string): string {
  if (pathname === "") {
    return "/";
  }

  if (pathname.length > 1 && pathname.endsWith("/")) {
    return pathname.slice(0, -1);
  }

  return pathname;
}

function readBrowserLocation(): BrowserLocation {
  return {
    pathname: normalizePathname(window.location.pathname),
    search: window.location.search,
  };
}

function findPrivateRoute(pathname: string): AppRoute | null {
  return privateRoutes.find((route) => route.path === pathname) ?? null;
}

function isPrivatePath(pathname: string): boolean {
  return findPrivateRoute(pathname) !== null;
}

function createLoginPath(returnPath: string): string {
  return `/login?next=${encodeURIComponent(returnPath)}`;
}

function getSafeReturnPath(search: string): string {
  const params = new URLSearchParams(search);
  const returnPath = params.get("next");

  if (!returnPath || !returnPath.startsWith("/")) {
    return "/";
  }

  if (!isPrivatePath(normalizePathname(returnPath))) {
    return "/";
  }

  return normalizePathname(returnPath);
}

function useBrowserNavigation() {
  const [location, setLocation] = useState<BrowserLocation>(() => readBrowserLocation());

  useEffect(() => {
    function handlePopState(): void {
      setLocation(readBrowserLocation());
    }

    window.addEventListener("popstate", handlePopState);

    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, []);

  const navigate = useCallback((path: string, options?: { replace?: boolean }) => {
    const method = options?.replace === true ? "replaceState" : "pushState";

    window.history[method](null, "", path);
    setLocation(readBrowserLocation());
  }, []);

  return { location, navigate };
}

function App() {
  return (
    <SessionProvider>
      <AppRoutes />
    </SessionProvider>
  );
}

function AppRoutes() {
  const { status } = useSession();
  const { location, navigate } = useBrowserNavigation();
  const route = useMemo(() => findPrivateRoute(location.pathname), [location.pathname]);
  const isLoginRoute = location.pathname === "/login";

  useEffect(() => {
    if (status === "unauthenticated" && route !== null) {
      navigate(createLoginPath(location.pathname), { replace: true });
    }

    if (status === "authenticated" && isLoginRoute) {
      navigate(getSafeReturnPath(location.search), { replace: true });
    }
  }, [isLoginRoute, location.pathname, location.search, navigate, route, status]);

  if (status === "loading") {
    return <PublicState title="Session" message="Vérification de la session." />;
  }

  if (isLoginRoute) {
    if (status === "authenticated") {
      return <PublicState title="Session active" message="Redirection en cours." />;
    }

    return (
      <LoginScreen
        onAuthenticated={() => {
          navigate(getSafeReturnPath(location.search), { replace: true });
        }}
      />
    );
  }

  if (route === null) {
    return <PublicState title="Page introuvable" message="Cette route n'existe pas." />;
  }

  if (status === "unauthenticated") {
    return <PublicState title="Connexion requise" message="Redirection en cours." />;
  }

  return <AuthenticatedShell currentRoute={route} navigate={navigate} />;
}

function AuthenticatedShell({
  currentRoute,
  navigate,
}: {
  currentRoute: AppRoute;
  navigate: (path: string, options?: { replace?: boolean }) => void;
}) {
  const { logout, user } = useSession();

  const userLabel = user?.full_name ?? user?.email ?? "Session active";

  function handleLogout(): void {
    logout();
    navigate(createLoginPath(currentRoute.path), { replace: true });
  }

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
          {privateRoutes.map((section) => (
            <a
              aria-current={section.path === currentRoute.path ? "page" : undefined}
              className="nav-item"
              href={section.path}
              key={section.label}
              onClick={(event) => {
                event.preventDefault();
                navigate(section.path);
              }}
            >
              <span>{section.label}</span>
              <small>{section.state}</small>
            </a>
          ))}
        </nav>

        <div className="session-panel" aria-label="Session utilisateur">
          <p className="session-label">Connecté</p>
          <p className="session-user">{userLabel}</p>
          {user?.full_name ? <p className="session-email">{user.email}</p> : null}
          <button className="text-button" type="button" onClick={handleLogout}>
            Déconnexion
          </button>
        </div>
      </aside>

      <section className="workspace" aria-labelledby="shell-title">
        <header className="workspace-header">
          <div>
            <p className="eyebrow">{currentRoute.kicker}</p>
            <h2 id="shell-title">{currentRoute.title}</h2>
          </div>
          <span className="status-pill">React + TypeScript</span>
        </header>

        <section className="placeholder-panel" aria-label="Écran temporaire">
          <p className="panel-kicker">Rétines & Pupilles</p>
          <h3>{currentRoute.panelTitle}</h3>
          <p>{currentRoute.panelText}</p>
        </section>
      </section>
    </main>
  );
}

function LoginScreen({ onAuthenticated }: { onAuthenticated: () => void }) {
  const { login } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await login({ email, password });
      onAuthenticated();
    } catch (error) {
      setErrorMessage(
        isAuthenticationError(error)
          ? "Identifiants invalides ou session indisponible."
          : "Connexion impossible pour le moment.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="public-shell">
      <section className="login-panel" aria-labelledby="login-title">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            RP
          </span>
          <div>
            <p className="brand-kicker">Application interne</p>
            <h1>Rétines & Pupilles</h1>
          </div>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <div>
            <p className="eyebrow">Session</p>
            <h2 id="login-title">Connexion</h2>
          </div>

          <label>
            <span>Email</span>
            <input
              autoComplete="email"
              name="email"
              onChange={(event) => {
                setEmail(event.target.value);
              }}
              required
              type="email"
              value={email}
            />
          </label>

          <label>
            <span>Mot de passe</span>
            <input
              autoComplete="current-password"
              name="password"
              onChange={(event) => {
                setPassword(event.target.value);
              }}
              required
              type="password"
              value={password}
            />
          </label>

          {errorMessage ? (
            <p className="form-error" role="alert">
              {errorMessage}
            </p>
          ) : null}

          <button className="primary-button" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Connexion..." : "Se connecter"}
          </button>
        </form>
      </section>
    </main>
  );
}

function PublicState({ title, message }: { title: string; message: string }) {
  return (
    <main className="public-shell">
      <section className="public-panel" aria-live="polite">
        <p className="panel-kicker">Rétines & Pupilles</p>
        <h1>{title}</h1>
        <p>{message}</p>
      </section>
    </main>
  );
}

export default App;
