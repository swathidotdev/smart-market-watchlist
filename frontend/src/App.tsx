import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";
import { api, type HealthResponse, getToken, clearToken } from "./api/client";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { StockDetail } from "./pages/StockDetail";

function HealthCheck() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  useEffect(() => {
    api
      .health()
      .then((data) => {
        setHealth(data);
        setHealthError(null);
      })
      .catch((e: unknown) => {
        const message = e instanceof Error ? e.message : "Unknown error";
        setHealthError(message);
      });
  }, []);

  if (healthError) {
    return (
      <div className="health-alert err">
        Backend unreachable — {healthError}
      </div>
    );
  }

  if (!health) {
    return (
      <div className="health-alert muted">
        Checking backend…
      </div>
    );
  }

  return (
    <div className="health-alert ok">
      Backend reachable — {health.app} ({health.environment})
    </div>
  );
}

function DashboardPage() {
  const navigate = useNavigate();

  return (
    <Dashboard
      onStockSelect={(symbol) => navigate(`/stock/${symbol}`)}
    />
  );
}

function StockDetailPage() {
  const navigate = useNavigate();

  // Extract symbol from URL if available
  const params = new URLSearchParams(window.location.search);
  const symbolFromParams = params.get("symbol");

  // Try to get symbol from path
  const pathParts = window.location.pathname.split("/");
  const symbol = pathParts[2] || symbolFromParams || "UNKNOWN";

  return (
    <StockDetail
      symbol={symbol}
      onBack={() => navigate("/")}
    />
  );
}

function AppContent() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!getToken());

  const handleLogout = () => {
    clearToken();
    setIsAuthenticated(false);
  };

  if (!isAuthenticated) {
    return (
      <div className="app-wrapper">
        <Login onLoginSuccess={() => setIsAuthenticated(true)} />
      </div>
    );
  }

  return (
    <main className="shell">
      <header className="app-header">
        <div className="app-header__content">
          <h1 className="app-title">Smart Market Watchlist</h1>
          <button onClick={handleLogout} className="logout-btn">
            Sign out
          </button>
        </div>
      </header>
      <HealthCheck />
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/stock/:symbol" element={<StockDetailPage />} />
      </Routes>
    </main>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}

